"""Append one section to a dashboard's single view, preserving everything else.

Same discipline as apply-card.py: read live config, back it up with a timestamp,
append the new section, refuse to save if the view doesn't look like what we
expect, write it back.

Usage: python3 append_section.py <new-section.json> [--dry-run]
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
DASHBOARD = os.environ.get("HA_DASHBOARD", "dashboard-office")
WS = URL.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
BACKUP_DIR = pathlib.Path(os.environ.get("HA_BACKUP_DIR", "."))
EXPECT_SECTIONS = int(os.environ.get("HA_EXPECT_SECTIONS", "3"))


async def run(new_section, dry_run):
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

            views = config["views"]
            if len(views) != 1:
                print(f"expected exactly 1 view, found {len(views)}, refusing to save")
                return 1
            sections = views[0]["sections"]
            print(f"found {len(sections)} existing sections (expected {EXPECT_SECTIONS})")
            if len(sections) != EXPECT_SECTIONS:
                print("section count mismatch, refusing to save")
                return 1

            sections.append(new_section)

            if dry_run:
                print(f"dry run: would append, new total {len(sections)} sections. not saving.")
                return 0

            await ws.send_json(
                {"id": 2, "type": "lovelace/config/save",
                 "url_path": DASHBOARD, "config": config}
            )
            msg = await ws.receive_json()
            print("save result:", json.dumps(msg))
            return 0 if msg.get("success") else 1


if __name__ == "__main__":
    section = json.loads(pathlib.Path(sys.argv[1]).read_text())
    sys.exit(asyncio.run(run(section, "--dry-run" in sys.argv)))
