#!/usr/bin/env python3
"""Build a compact program guide for the TV's own channel list.

Guide data comes from two public TV guides:
  1. SBB/EON (epg.sbb.rs), the TV's own cable provider, so it covers nearly every channel;
  2. mts.rs, for anything SBB doesn't list.
Channels are matched to the TV's channel list by normalized name, and the next 24 hours
are written to epg.json, which server.py serves to the app. Run it a few times a day
(see lg-remote-epg.timer).

Usage:
  epg.py                      fetch the guides, write epg.json
  epg.py --coverage           print which TV channels have no guide
  epg.py --cache DIR          read tvch.xml, mts_<page>.json, sbb_channels.json and
                              sbb_epg*.json from DIR instead of fetching (testing)
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
TV_IP = "192.168.1.60"
KEY_FILE = os.path.join(HERE, "pairing_key.txt")
OUT = os.path.join(HERE, "epg.json")
WINDOW_BEFORE = 3600          # keep the show that started up to an hour ago
WINDOW_AFTER = 24 * 3600      # and everything starting in the next 24 hours
CHANNELS_CACHE = os.path.join(HERE, "tv_channels.json")
MTS_URL = ("https://mts.rs/hybris/ecommerce/b2c/v1/products/search?sort=pozicija-rastuce"
           "&searchQueryContext=CHANNEL_PROGRAM"
           "&query=:pozicija-rastuce:tip-kanala-radio:TV%20kanali:channelProgramDates:{date}"
           "&pageSize=50&currentPage={page}")
DESCRIPTION_LIMIT = 400

# SBB's public EPG (what epg.sbb.rs shows). The page gets an anonymous token with the web
# client ID built into its code; put that "Basic ..." header value in sbb_client.txt (not
# committed). Without it only the mts.rs guide is used. Community 1 / language 404 is SBB Serbia.
SBB_API = "https://api-web.ug-be.cdn.united.cloud"
SBB_IMAGES = "https://images-web.ug-be.cdn.united.cloud"
SBB_CLIENT_FILE = os.path.join(HERE, "sbb_client.txt")
SBB_COMMUNITY = {"communityId": 1, "languageId": 404}
SBB_BATCH = 10                # channels per guide request; the API rejects 20

# Words that differ between the TV's names and the guide's names without changing the channel.
NOISE = {"hd", "tv", "televizija", "television", "channel", "kanal", "sd", "4k", "uhd"}
# Hand-made links for names normalization can't reconcile: TV name -> guide name.
SBB_ALIASES = {
    "RTL Televizija": "RTL HR HD (RS)",
    "Viasat Kino": "Viasat Kino (RS) exTV1000",
    "CineStarPrem 1": "CineStar Premiere 1 HD (RS)",
    "CineStarPrem 2": "CineStar Premiere 2 HD (RS)",
    "CineStarComedy": "CineStar Comedy & Family HD",
    "Arena 1x2": "Arena Sport 1X2 HD (RS)",
    "Crime & Invest": "Crime & Investigation (RS)",
    "Trace Sport HD": "Trace Sport Stars HD (RS)",
    "RTL Cro World": "RTL Croatia World",
    "Pannon": "Pannon RTV",
    "TV Pancevo": "RTV Pančevo",
    "1+1 Int": "1+1 International (RS)",
    "TVE Int": "TVE (RS)",
    "Romania Int": "Romania International",
    "Grand 2": "Grand narodna televizija 2 (RS)",
    "Info kanal": "SBB Info kanal",
}
MTS_ALIASES = {
    "Pink": "TV Pink",
    "Epic Drama HD": "Viasat Epic Drama",
    "Arena 1x2": "Arena Sport 1x2",
    "Fast&Fun Box HD": "Fast & Fun",
    "Nick Jr": "Nickelodeon Junior",
    "BabyTV": "Baby TV",
    "Da Vinci": "Da Vinci Learning",
    "Crime & Invest": "Crime and Investigation",
    "Travel HD": "TravelXP",
    "RTL Cro World": "RTL Croatia World",
    "Pannon": "Panon TV",
    "TV Kragujevac": "RTV Kragujevac",
    "Nis TV": "NIŠtv",
    "Sandzak TV": "TV Sandžak",
    "Pink Sci-fi": "Pink Sci-Fi & Fantasy",
    "FREEДOM": "Freedom",
    "Rai Uno": "Rai 1",
}


def norm(name):
    s = re.sub(r"\([^)]*\)", " ", html.unescape(name))   # "N1 HD (RS)" -> "N1 HD"
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ").replace("+", " plus ")
    words = [w for w in re.split(r"[^a-z0-9]+", s) if w and w not in NOISE]
    return "".join(words)


def tv_get(target):
    # curl, not urllib: same transport as server.py, which matters on the Mac (Local Network privacy).
    return subprocess.run(
        ["curl", "-s", "-m", "8", "-A", "UDAP/2.0", f"http://{TV_IP}:8080/udap/api/data?target={target}"],
        capture_output=True, text=True,
    ).stdout


def tv_hello():
    if not os.path.exists(KEY_FILE):
        return
    key = open(KEY_FILE).read().strip()
    body = ('<?xml version="1.0" encoding="utf-8"?><envelope><api type="pairing"><name>hello</name>'
            f'<value>{key}</value><port>8080</port></api></envelope>')
    subprocess.run(["curl", "-s", "-m", "4", "-o", "/dev/null", "-A", "UDAP/2.0",
                    "-H", "Content-Type: text/xml; charset=utf-8", "-X", "POST", "--data-binary", body,
                    f"http://{TV_IP}:8080/udap/api/pairing"], capture_output=True)


def parse_tv_channels(xml):
    channels = []
    for block in re.findall(r"<data>(.*?)</data>", xml, re.S):
        num = re.search(r"<displayMajor>(\d+)</displayMajor>", block)
        name = re.search(r"<chname>(.*?)</chname>", block)
        if num and name:
            channels.append({"num": int(num.group(1)), "name": html.unescape(name.group(1)).strip()})
    return channels


def tv_channels(cache_dir=None):
    """The TV's channel list; falls back to the last saved copy when the TV is off."""
    if cache_dir:
        return parse_tv_channels(open(os.path.join(cache_dir, "tvch.xml")).read())
    tv_hello()
    channels = parse_tv_channels(tv_get("channel_list"))
    if channels:
        json.dump(channels, open(CHANNELS_CACHE, "w"), ensure_ascii=False)
    elif os.path.exists(CHANNELS_CACHE):
        channels = json.load(open(CHANNELS_CACHE))
    return channels


def fetch_json(url, headers=None, data=None):
    req = urllib.request.Request(url, data=data, headers={"Accept": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def match(channels, names, aliases):
    """{TV channel name: guide name} for the TV channels found among the guide's names."""
    by_norm = {}
    for name in names:
        by_norm.setdefault(norm(name), name)
    found = {}
    for ch in channels:
        name = by_norm.get(norm(aliases.get(ch["name"], ch["name"])))
        if name:
            found[ch["name"]] = name
    return found


def sbb_time(s):
    return int(dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f%z").timestamp())


def sbb_image(images):
    by_size = {i.get("size"): i["path"] for i in images or [] if i.get("path")}
    path = by_size.get("STB_FHD") or by_size.get("S") or by_size.get("M")
    return SBB_IMAGES + path if path else None


def sbb_compact(e):
    item = {"t": (e.get("title") or "").strip(), "s": sbb_time(e["startTime"]), "e": sbb_time(e["endTime"])}
    desc = (e.get("shortDescription") or "").strip()
    if desc:
        item["d"] = desc[:DESCRIPTION_LIMIT] + ("…" if len(desc) > DESCRIPTION_LIMIT else "")
    img = sbb_image(e.get("images"))
    if img:
        item["i"] = img
    return item


def sbb_guide(channels, cache_dir=None):
    """{TV channel name: [programs]} from SBB's public EPG."""
    if cache_dir:
        sbb_channels = json.load(open(os.path.join(cache_dir, "sbb_channels.json")))
        events = {}
        for f in sorted(os.listdir(cache_dir)):
            if re.fullmatch(r"sbb_epg\d*\.json", f):
                events.update(json.load(open(os.path.join(cache_dir, f))))
    else:
        if not os.path.exists(SBB_CLIENT_FILE):
            raise RuntimeError("no sbb_client.txt, skipping SBB")
        client = open(SBB_CLIENT_FILE).read().strip()
        token = fetch_json(f"{SBB_API}/oauth/token?grant_type=client_credentials",
                           headers={"Authorization": client}, data=b"")["access_token"]
        auth = {"Authorization": f"Bearer {token}"}
        q = urllib.parse.urlencode({"channelType": "TV", **SBB_COMMUNITY})
        sbb_channels = fetch_json(f"{SBB_API}/v1/public/channels?{q}", headers=auth)
        events = None

    ids = {c["name"]: c["id"] for c in sbb_channels}
    matched = match(channels, ids, SBB_ALIASES)
    if events is None:
        start = dt.datetime.now().astimezone().replace(hour=0, minute=0, second=0, microsecond=0)
        times = {"fromTime": start.isoformat(), "toTime": (start + dt.timedelta(days=2)).isoformat()}
        wanted = sorted({ids[n] for n in matched.values()})
        batches = [wanted[i:i + SBB_BATCH] for i in range(0, len(wanted), SBB_BATCH)]

        def fetch(batch):
            q = urllib.parse.urlencode({**times, **SBB_COMMUNITY, "cid": ",".join(map(str, batch))})
            try:
                return fetch_json(f"{SBB_API}/v1/public/events/epg?{q}", headers=auth)
            except urllib.error.HTTPError:
                if len(batch) == 1:
                    return {}
                # One bad channel fails the whole batch; split it so the others still come through.
                merged = {}
                for cid in batch:
                    merged.update(fetch([cid]))
                return merged

        events = {}
        with ThreadPoolExecutor(3) as ex:
            for part in ex.map(fetch, batches):
                events.update(part)
    return {tv: [sbb_compact(e) for e in events.get(str(ids[name]), [])] for tv, name in matched.items()}


def mts_guide(channels, cache_dir=None):
    """{TV channel name: [programs]} from the mts.rs guide, today and tomorrow."""
    today = dt.date.today()
    days = [today] if cache_dir else [today, today + dt.timedelta(days=1)]
    guide = {}
    for d in days:
        for name, programs in mts_day(d.isoformat(), cache_dir).items():
            guide.setdefault(name, []).extend(programs)
    matched = match(channels, guide, MTS_ALIASES)
    return {tv: [compact(p) for p in guide[name]] for tv, name in matched.items()}


def mts_day(date, cache_dir=None):
    """All channels' programs for one day: {guide channel name: [programs]}."""
    if cache_dir:
        pages = [json.load(open(os.path.join(cache_dir, f)))
                 for f in sorted(os.listdir(cache_dir)) if re.fullmatch(r"mts_\d+\.json", f)]
    else:
        first = fetch_json(MTS_URL.format(date=date, page=0))
        total = first.get("pagination", {}).get("totalPages", 1)
        with ThreadPoolExecutor(4) as ex:
            rest = list(ex.map(lambda p: fetch_json(MTS_URL.format(date=date, page=p)), range(1, total)))
        pages = [first] + rest
    day = {}
    for page in pages:
        for ch in page.get("products", []):
            day.setdefault(ch["name"], []).extend(ch.get("programs") or [])
    return day


def compact(p):
    item = {
        "t": p.get("title", "").strip(),
        "s": int(dt.datetime.fromisoformat(p["start"].replace("Z", "+00:00")).timestamp()),
        "e": int(dt.datetime.fromisoformat(p["end"].replace("Z", "+00:00")).timestamp()),
    }
    if p.get("category"):
        item["c"] = p["category"]
    desc = (p.get("description") or "").strip()
    if desc:
        item["d"] = desc[:DESCRIPTION_LIMIT] + ("…" if len(desc) > DESCRIPTION_LIMIT else "")
    img = (p.get("picture") or {}).get("url")
    if img:
        item["i"] = img
    return item


def build(cache_dir=None):
    channels = tv_channels(cache_dir)
    sources = []
    for name, fn in (("sbb", sbb_guide), ("mts", mts_guide)):
        try:
            sources.append(fn(channels, cache_dir))
        except Exception as e:   # one guide being down shouldn't take the other with it
            print(f"{name} guide failed: {e}", file=sys.stderr)
            sources.append({})

    now = dt.datetime.now().timestamp()
    out, missing = [], []
    for ch in channels:
        entry = {"num": ch["num"], "name": ch["name"]}
        for guide in sources:
            seen, progs = set(), []
            for item in sorted(guide.get(ch["name"], []), key=lambda p: p["s"]):
                if item["s"] in seen or not item["t"]:
                    continue
                seen.add(item["s"])
                if cache_dir or (item["e"] > now - WINDOW_BEFORE and item["s"] < now + WINDOW_AFTER):
                    progs.append(item)
            if progs:
                entry["p"] = progs
                break
        else:
            missing.append(ch)
        out.append(entry)
    return out, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coverage", action="store_true")
    ap.add_argument("--cache")
    args = ap.parse_args()

    channels, missing = build(args.cache)
    if args.coverage:
        print(f"{len(channels) - len(missing)}/{len(channels)} TV channels have a guide")
        print("missing:", ", ".join(f"{c['num']} {c['name']}" for c in missing))
        return
    if not channels:
        sys.exit("no channel list (TV off and nothing cached)")
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"updated": int(dt.datetime.now().timestamp()), "channels": channels}, f,
                  ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, OUT)
    print(f"wrote {OUT}: {len(channels) - len(missing)}/{len(channels)} channels with guide")


if __name__ == "__main__":
    main()
