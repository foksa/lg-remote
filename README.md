# LG Remote

A phone remote for old LG NetCast smart TVs (2012-era models such as the 32LS570S) that talk
LG's UDAP/2.0 protocol on port 8080, plus a TV guide for the TV's own channel list.

- **Android app** (Svelte + Capacitor): talks to the TV directly over Wi-Fi, finds it with
  SSDP or a subnet sweep, and pairs with the code the TV shows on screen.
- **Browser version**: the same UI served by `server.py`, which relays commands to the TV.
- **Guide**: `epg.py` builds the next 24 hours of programs for the TV's channels and
  `server.py` serves it as `/epg.json`.

## Layout

| Path | What |
|---|---|
| `web/` | Svelte app (Remote / Numbers / Guide pages); `web/android/` is the Capacitor Android project |
| `web/android/.../TvPlugin.java` | Native UDAP calls, TV discovery, Android 17 local-network permission |
| `server.py` | Serves the web build, `/epg.json`, and `/api/*` (keys, pairing, power, current channel) |
| `epg.py` | Builds `epg.json` from public guides, matched to the TV's channel list by name |
| `wake.py` | Optional: wakes the TV over HDMI-CEC through a Chromecast |
| `deploy.sh` | Builds the web app and pushes everything to a Raspberry Pi |
| `build-apk.sh` | Builds the debug APK; `--install` puts it on a USB-connected phone |

## Running

```sh
cd web && npm install && npm run build && cd ..
python3 server.py 192.168.1.60        # your TV's IP
python3 epg.py                        # build the guide (run it every few hours)
```

Open `http://<this machine>:8765` on a phone, or build the Android app with `./build-apk.sh`.

### Guide sources

`epg.py` uses SBB/EON's public guide (the one behind epg.sbb.rs) first and mts.rs for
anything it doesn't list. The SBB guide needs the web client header that epg.sbb.rs uses,
saved as `sbb_client.txt` next to `epg.py`; without it only mts.rs is used.

### Notes

- The TV turns its network off in standby, so the app can turn it off but not on.
  `wake.py` can wake it over HDMI-CEC through a Chromecast that stays powered.
- Addresses for this setup (TV `192.168.1.60`, Pi at `pi.lan`) are set at the top of
  `server.py`, `epg.py`, `web/src/lib/api.js` and `deploy.sh`.
