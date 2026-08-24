"""Add a kiosk_mode block, scoped to one user, to a dashboard's saved config root.

Same discipline as append_section.py: read live config, back it up with a
timestamp, add the block, refuse to save if it's already present, write back.

Also the reapply tool for ADR-0061: the Lovelace UI editor doesn't round-trip
this root-level key, so any GUI edit to a kiosk_mode-bearing dashboard can
silently drop it. Re-running this with the same arguments restores it; it
only refuses when kiosk_mode is already present, which is the "nothing to do"
case, not a conflict.

Usage: python3 add-kiosk-mode.py <dashboard-url-path> <display-name> [--dry-run]
"""

import asyncio
import datetime
import json
import os
import pathlib
import sys

import aiohttp

URL = os.environ.get("HA_URL", "http://hass.ehlke.net")
TOKEN = os.environ["HA_TOKEN"]
WS = URL.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
BACKUP_DIR = pathlib.Path(os.environ.get("HA_BACKUP_DIR", "."))


async def run(dashboard, display_name, dry_run):
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS, heartbeat=30) as ws:
            assert (await ws.receive_json())["type"] == "auth_required"
            await ws.send_json({"type": "auth", "access_token": TOKEN})
            if (await ws.receive_json())["type"] != "auth_ok":
                print("auth failed")
                return 1

            await ws.send_json({"id": 1, "type": "lovelace/config", "url_path": dashboard})
            msg = await ws.receive_json()
            if not msg.get("success"):
                print("could not read config:", msg)
                return 1
            config = msg["result"]

            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = BACKUP_DIR / f"backup-{dashboard}-{stamp}.json"
            backup.write_text(json.dumps(config, indent=2))
            print(f"backup written: {backup}")

            if "kiosk_mode" in config:
                print(f"kiosk_mode already present, refusing to overwrite: {config['kiosk_mode']}")
                return 1

            config["kiosk_mode"] = {
                "user_settings": [
                    {"users": [display_name], "hide_header": True, "hide_sidebar": True}
                ]
            }

            if dry_run:
                print("dry run: would save this kiosk_mode block:")
                print(json.dumps(config["kiosk_mode"], indent=2))
                return 0

            await ws.send_json(
                {"id": 2, "type": "lovelace/config/save", "url_path": dashboard, "config": config}
            )
            msg = await ws.receive_json()
            print("save result:", json.dumps(msg))
            return 0 if msg.get("success") else 1


if __name__ == "__main__":
    dashboard_arg = sys.argv[1]
    display_name_arg = sys.argv[2]
    sys.exit(asyncio.run(run(dashboard_arg, display_name_arg, "--dry-run" in sys.argv)))
