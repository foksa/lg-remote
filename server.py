#!/usr/bin/env python3
"""Phone-friendly remote for LG NetCast TVs (UDAP/2.0), e.g. 32LS570S.

Build the web app first (cd web && npm run build), then
run:  python3 server.py [TV_IP]
and open http://<this-machine>:8765 on your phone.
"""
import gzip
import html
import json
import os
import re
import socket
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TV_IP = sys.argv[1] if len(sys.argv) > 1 else "192.168.1.60"
PORT = 8765
HERE = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(HERE, "pairing_key.txt")
DIST = os.path.realpath(os.path.join(HERE, "web", "dist"))
EPG_FILE = os.path.join(HERE, "epg.json")
MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".webmanifest": "application/manifest+json",
}


def udap(path, api_xml):
    body = f'<?xml version="1.0" encoding="utf-8"?><envelope>{api_xml}</envelope>'
    # Go through curl: macOS Local Network privacy blocks Python itself from reaching LAN devices.
    try:
        out = subprocess.run(
            ["curl", "-s", "-m", "4", "-o", "/dev/null", "-w", "%{http_code}",
             "-A", "UDAP/2.0", "-H", "Content-Type: text/xml; charset=utf-8",
             "-X", "POST", "--data-binary", body,
             f"http://{TV_IP}:8080/udap/api/{path}"],
            capture_output=True, text=True, timeout=6,
        ).stdout
        return int(out or 0)
    except (subprocess.SubprocessError, ValueError):
        return 0


def show_key():
    return udap("pairing", '<api type="pairing"><name>showKey</name></api>')


def pair(key):
    status = udap(
        "pairing",
        f'<api type="pairing"><name>hello</name><value>{key}</value><port>8080</port></api>',
    )
    if status == 200:
        with open(KEY_FILE, "w") as f:
            f.write(key)
    return status


def send_key(code):
    status = udap(
        "command",
        f'<api type="command"><name>HandleKeyInput</name><value>{code}</value></api>',
    )
    # 401 means the TV forgot us (e.g. after a restart); re-pair with the saved key and retry.
    if status == 401 and os.path.exists(KEY_FILE):
        if pair(open(KEY_FILE).read().strip()) == 200:
            status = udap(
                "command",
                f'<api type="command"><name>HandleKeyInput</name><value>{code}</value></api>',
            )
    return status


def tv_is_on():
    # The TV's network stack is down in standby, so any HTTP answer means it's on.
    out = subprocess.run(
        ["curl", "-s", "-m", "1.5", "-o", "/dev/null", "-w", "%{http_code}", f"http://{TV_IP}:8080/"],
        capture_output=True, text=True,
    ).stdout
    return out not in ("", "000")


def wake_tv():
    python = os.path.join(HERE, ".venv", "bin", "python")
    if not os.path.exists(python):
        return False
    try:
        return subprocess.run([python, os.path.join(HERE, "wake.py")], capture_output=True, timeout=30).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def current_channel():
    """{num, name, prog} of what the TV is showing, or {} when it can't be read."""
    def read():
        return subprocess.run(
            ["curl", "-s", "-m", "4", "-A", "UDAP/2.0", f"http://{TV_IP}:8080/udap/api/data?target=cur_channel"],
            capture_output=True, text=True,
        ).stdout
    xml = read()
    if "<chname>" not in xml and os.path.exists(KEY_FILE):
        pair(open(KEY_FILE).read().strip())
        xml = read()
    fields = {k: re.search(f"<{k}>(.*?)</{k}>", xml) for k in ("displayMajor", "chname", "progName")}
    if not fields["displayMajor"]:
        return {}
    return {
        "num": int(fields["displayMajor"].group(1)),
        "name": html.unescape(fields["chname"].group(1)) if fields["chname"] else "",
        "prog": html.unescape(fields["progName"].group(1)) if fields["progName"] else "",
    }


def toggle_power():
    if tv_is_on():
        return "off" if send_key(1) == 200 else "error"
    return "waking" if wake_tv() else "wake-failed"


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            path = "/index.html"
        if path == "/epg.json":
            file = EPG_FILE   # written by epg.py, lives outside dist so deploys don't wipe it
        else:
            file = os.path.realpath(os.path.join(DIST, path.lstrip("/")))
            if not file.startswith(DIST + os.sep):
                file = None
        if not file or not os.path.isfile(file):
            self.send_error(404)
            return
        with open(file, "rb") as f:
            data = f.read()
        ext = os.path.splitext(file)[1]
        self.send_response(200)
        self.send_header("Content-Type", MIME_TYPES.get(ext, "application/octet-stream"))
        # Hashed build assets never change; everything else must revalidate so updates show up.
        self.send_header("Cache-Control", "public, max-age=31536000, immutable" if "/assets/" in path else "no-cache")
        if ext == ".json" and "gzip" in (self.headers.get("Accept-Encoding") or ""):
            data = gzip.compress(data, 6)
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            body = {}
        if self.path == "/api/showkey":
            self._json({"status": show_key()})
        elif self.path == "/api/pair":
            key = "".join(c for c in str(body.get("key", "")) if c.isalnum())
            self._json({"status": pair(key)})
        elif self.path == "/api/key":
            self._json({"status": send_key(int(body.get("code", 0)))})
        elif self.path == "/api/current":
            self._json(current_channel())
        elif self.path == "/api/power":
            self._json({"result": toggle_power()})
        elif self.path == "/api/state":
            self._json({"paired": os.path.exists(KEY_FILE), "tv": TV_IP})
        else:
            self.send_error(404)

    def log_message(self, *args):
        pass


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((TV_IP, 8080))
        return s.getsockname()[0]
    finally:
        s.close()


if __name__ == "__main__":
    if os.path.exists(KEY_FILE):
        pair(open(KEY_FILE).read().strip())
    print(f"TV: {TV_IP}")
    print(f"Open on your phone: http://{local_ip()}:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
