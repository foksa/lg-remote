#!/bin/sh
# Build the web app and push everything to the Pi, then restart the service.
set -e
cd "$(dirname "$0")"
(cd web && npm run build)
ssh foksa@pi.lan 'mkdir -p ~/lg-remote/web && rm -rf ~/lg-remote/web/dist ~/lg-remote/index.html ~/lg-remote/manifest.json ~/lg-remote/*.png'
scp -q server.py wake.py epg.py foksa@pi.lan:lg-remote/
scp -qr web/dist foksa@pi.lan:lg-remote/web/
ssh foksa@pi.lan 'sudo systemctl restart lg-remote && sleep 1 && systemctl is-active lg-remote'
