"""Replace one card on a dashboard, preserving everything else.

Lovelace saves are whole-config writes, so this reads the live config, backs it up
with a timestamp, swaps only the single card matching HA_MATCH_TYPE (and, if set,
HA_MATCH_ENTITY), and writes the result back. Refuses to save if it does not find
exactly one match.

Usage: python3 apply-card.py <new-card.json> [--dry-run]
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
DASHBOARD = os.environ.get("HA_DASHBOARD", "dashboard-sound")
WS = URL.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
BACKUP_DIR = pathlib.Path(os.environ.get("HA_BACKUP_DIR", "."))
MATCH_TYPE = os.environ.get("HA_MATCH_TYPE", "custom:wall-clock-card")
MATCH_ENTITY = os.environ.get("HA_MATCH_ENTITY")  # optional extra filter


def swap(node, new_card, found):
    """Recursively replace any dict matching MATCH_TYPE (and MATCH_ENTITY) with new_card."""
    if isinstance(node, dict):
        matches = node.get("type") == MATCH_TYPE
        if matches and MATCH_ENTITY is not None:
            matches = node.get("entity") == MATCH_ENTITY
        if matches:
            found.append(node)
            return json.loads(json.dumps(new_card))
        return {k: swap(v, new_card, found) for k, v in node.items()}
    if isinstance(node, list):
        return [swap(v, new_card, found) for v in node]
    return node


async def run(new_card, dry_run):
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

            found = []
            updated = swap(config, new_card, found)
            print(f"matching cards found: {len(found)}")
            if len(found) != 1:
                print("expected exactly 1, refusing to save")
                return 1

            if dry_run:
                print("dry run, not saving")
                return 0

            await ws.send_json(
                {"id": 2, "type": "lovelace/config/save",
                 "url_path": DASHBOARD, "config": updated}
            )
            msg = await ws.receive_json()
            print("save result:", json.dumps(msg))
            return 0 if msg.get("success") else 1


if __name__ == "__main__":
    card = json.loads(pathlib.Path(sys.argv[1]).read_text())
    sys.exit(asyncio.run(run(card, "--dry-run" in sys.argv)))
