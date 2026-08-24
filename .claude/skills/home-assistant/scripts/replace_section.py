"""Replace one section (by index) in a dashboard's single view.

Usage: python3 replace_section.py <index> <new-section.json> [--dry-run]
"""

import asyncio
import datetime
import json
import os
import pathlib
import sys

import aiohttp

URL = os.environ.get("HA_URL", "https://hass.ehlke.net")
TOKEN = os.environ["HA_TOKEN"]
DASHBOARD = os.environ.get("HA_DASHBOARD", "dashboard-office")
WS = URL.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
BACKUP_DIR = pathlib.Path(os.environ.get("HA_BACKUP_DIR", "."))


async def run(index, new_section, dry_run):
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS, heartbeat=30) as ws:
            assert (await ws.receive_json())["type"] == "auth_required"
            await ws.send_json({"type": "auth", "access_token": TOKEN})
            if (await ws.receive_json())["type"] != "auth_ok":
                print("auth failed")
                return 1

            await ws.send_json({"id": 1, "type": "lovelace/config", "url_path": DASHBOARD})
            msg = await ws.receive_json()
            if not msg.get("success"):
                print("could not read config:", msg)
                return 1
            config = msg["result"]

            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = BACKUP_DIR / f"backup-{DASHBOARD}-{stamp}.json"
            backup.write_text(json.dumps(config, indent=2))
            print(f"backup written: {backup}")

            sections = config["views"][0]["sections"]
            print(f"found {len(sections)} sections")
            if index >= len(sections):
                print(f"index {index} out of range, refusing to save")
                return 1

            sections[index] = new_section

            if dry_run:
                print(f"dry run: would replace section {index}. not saving.")
                return 0

            await ws.send_json(
                {"id": 2, "type": "lovelace/config/save",
                 "url_path": DASHBOARD, "config": config}
            )
            msg = await ws.receive_json()
            print("save result:", json.dumps(msg))
            return 0 if msg.get("success") else 1


if __name__ == "__main__":
    idx = int(sys.argv[1])
    section = json.loads(pathlib.Path(sys.argv[2]).read_text())
    sys.exit(asyncio.run(run(idx, section, "--dry-run" in sys.argv)))
