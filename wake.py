#!/usr/bin/env python3
"""Wake the TV over HDMI-CEC by launching an app on the Chromecast plugged into it.

Usage: wake.py [CHROMECAST_NAME] [CHROMECAST_IP]      (defaults: chromecast in config.json)
"""
import sys
import time

import pychromecast

from config import CONFIG

CAST = CONFIG.get("chromecast", {})
NAME = sys.argv[1] if len(sys.argv) > 1 else CAST.get("name")
HOST = sys.argv[2] if len(sys.argv) > 2 else CAST.get("host")
DEFAULT_MEDIA_RECEIVER = "CC1AD845"

casts, browser = pychromecast.get_listed_chromecasts(friendly_names=[NAME], known_hosts=[HOST] if HOST else None, timeout=8)
try:
    if not casts:
        print("chromecast not found", file=sys.stderr)
        sys.exit(1)
    cast = casts[0]
    cast.wait(timeout=8)
    # Launching an app makes the Chromecast send CEC "power on + switch to me" to the TV.
    cast.start_app(DEFAULT_MEDIA_RECEIVER)
    time.sleep(3)
    cast.quit_app()
    print("ok")
finally:
    browser.stop_discovery()
