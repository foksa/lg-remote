#!/bin/sh
# Build the web app and push everything to the server named in config.json, then restart the service.
set -e
cd "$(dirname "$0")"
HOST=$(python3 -c "import json; print(json.load(open('config.json'))['server'])")
(cd web && npm run build)
ssh "$HOST" 'mkdir -p ~/lg-remote/web && rm -rf ~/lg-remote/web/dist ~/lg-remote/index.html ~/lg-remote/manifest.json ~/lg-remote/*.png'
scp -q server.py wake.py epg.py config.py config.json "$HOST":lg-remote/
scp -qr web/dist "$HOST":lg-remote/web/
ssh "$HOST" 'sudo systemctl restart lg-remote && sleep 1 && systemctl is-active lg-remote'
