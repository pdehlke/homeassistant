"""Minimal Home Assistant WebSocket client.

REST cannot read or write Lovelace dashboards, the area registry, or the entity
registry; those live behind the WebSocket API only. Usage:

    python3 haws.py '{"type":"lovelace/dashboards/list"}' ...

Each argument is one command, sent in order. Results print as JSON, one per line.
Reads the token from HA_TOKEN and the base URL from HA_URL.
"""

import asyncio
import json
import os
import sys

import aiohttp

URL = os.environ.get("HA_URL", "https://hass.ehlke.net")
TOKEN = os.environ["HA_TOKEN"]
WS = URL.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"


async def main(commands):
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS, heartbeat=30) as ws:
            msg = await ws.receive_json()
            if msg.get("type") != "auth_required":
                print(json.dumps({"error": "unexpected greeting", "msg": msg}))
                return 1
            await ws.send_json({"type": "auth", "access_token": TOKEN})
            msg = await ws.receive_json()
            if msg.get("type") != "auth_ok":
                print(json.dumps({"error": "auth failed", "msg": msg}))
                return 1

            for i, raw in enumerate(commands, start=1):
                payload = json.loads(raw)
                payload["id"] = i
                await ws.send_json(payload)
                while True:
                    msg = await ws.receive_json()
                    if msg.get("id") == i and msg.get("type") == "result":
                        print(json.dumps(msg))
                        break
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
