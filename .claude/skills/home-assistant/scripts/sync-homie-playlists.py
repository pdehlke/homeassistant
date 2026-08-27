"""Sync Jellyfin-sourced MA library playlists into sensor.homie_dynamic_playlists.

Homie Dashboard's Music chip Playlists row used to be a hand-maintained array in
homie-dashboard's dist/config.js: adding a Jellyfin playlist meant editing that
file and redeploying. This script replaces that with a periodically-refreshed
HA sensor the dashboard reads at popup-open time instead. See
docs/homie-dashboard/homie-dynamic-playlists.md in the pdehlke/homeassistant
repo for the full design writeup and the alternatives this rejected.

Why this needs MA's own WebSocket API, not the HA-side music_assistant.get_library
service: get_library's response schema is exactly
{media_type, uri, name, version, image, favorite, explicit} -- no provider
field, confirmed 2026-08-04 (see references/music-assistant.md). Only MA's own
music/get_library_item command returns provider_mappings, which is the one
reliable way to know a playlist came from Jellyfin and not from MA's own
builtin smart-playlist provider (or some future provider). That command is
reachable only through HA's ingress proxy for the Music Assistant add-on, per
"Reaching MA's full API through HA ingress" in the same reference doc.

Why this doesn't run as a Home Assistant automation: HA's own
script/shell_command execution environment on this instance has no proven
WebSocket-capable tool (the one precedent, /config/scripts/rss-news-fetch.sh,
uses curl+jq+POSIX sh, checked 2026-08-26) and curl's own WebSocket support
isn't practical for a multi-message JSON-RPC exchange matched by message_id.
So this script talks to hass.ehlke.net the same way any other external client
does: $HA_TOKEN over HTTPS, both for the Supervisor calls that mint the MA
ingress session and for the final REST write of the result. It does not need
Home Assistant's own process at all -- it just needs network access to
hass.ehlke.net and a Python with aiohttp.

Where this runs, and the still-open scheduling problem: this script and its
token wrapper (homie-playlists-env.sh.example, same directory) are deployed
to /config/scripts/ on the HA host, and the SSH & Web Terminal add-on's own
container (root@192.168.4.141:2222) has py3-aiohttp installed via that
add-on's `packages` config option. A cron entry was also installed there,
but does nothing: that container has no `crond` process actually running,
so nothing ever reads the crontab. See homie-dynamic-playlists.md for that
finding in full and for whatever scheduling mechanism replaces it. Until
then, this script only runs when invoked by hand.

Usage:
    python3 sync-homie-playlists.py [--dry-run]

Reads HA_TOKEN and HA_URL (default https://hass.ehlke.net) from the
environment, same convention as haws.py.
"""

import argparse
import asyncio
import json
import os
import sys

import aiohttp

URL = os.environ.get("HA_URL", "https://hass.ehlke.net")
TOKEN = os.environ["HA_TOKEN"]
MA_ADDON_SLUG = "d5369777_music_assistant"
SENSOR_ENTITY_ID = "sensor.homie_dynamic_playlists"


async def rest_get(session, path):
    async with session.get(f"{URL}{path}") as resp:
        resp.raise_for_status()
        return await resp.json()


async def rest_post(session, path, body):
    async with session.post(f"{URL}{path}", json=body) as resp:
        resp.raise_for_status()
        return await resp.json()


async def get_config_entry_id(session):
    entries = await rest_get(session, "/api/config/config_entries/entry")
    for e in entries:
        if e["domain"] == "music_assistant":
            return e["entry_id"]
    raise RuntimeError("no music_assistant config entry found")


async def call_service_ws(command):
    """One-shot WS call, mirroring haws.py's pattern. Used for get_library,
    which the HA-side integration does expose (unlike get_library_item)."""
    ws_url = URL.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(ws_url, heartbeat=30) as ws:
            await asyncio.wait_for(ws.receive_json(), timeout=15)  # auth_required
            await ws.send_json({"type": "auth", "access_token": TOKEN})
            auth_result = await asyncio.wait_for(ws.receive_json(), timeout=15)
            if auth_result.get("type") != "auth_ok":
                raise RuntimeError(f"HA WS auth failed: {auth_result}")
            command["id"] = 1
            await ws.send_json(command)
            while True:
                msg = await asyncio.wait_for(ws.receive_json(), timeout=15)
                if msg.get("id") == 1 and msg.get("type") == "result":
                    if not msg.get("success"):
                        raise RuntimeError(f"service call failed: {msg}")
                    return msg["result"]["response"]


async def get_all_playlists(config_entry_id):
    response = await call_service_ws({
        "type": "call_service",
        "domain": "music_assistant",
        "service": "get_library",
        "return_response": True,
        "service_data": {
            "config_entry_id": config_entry_id,
            "media_type": "playlist",
            "limit": 500,
        },
    })
    return response["items"]


async def get_ingress_context(rest_session):
    # /api/hassio/* over REST 401s per references/music-assistant.md; go through
    # supervisor/api over the HA WebSocket instead, same as haws.py does.
    ws_url = URL.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
    async with rest_session.ws_connect(ws_url, heartbeat=30) as ws:
        await asyncio.wait_for(ws.receive_json(), timeout=15)
        await ws.send_json({"type": "auth", "access_token": TOKEN})
        auth_result = await asyncio.wait_for(ws.receive_json(), timeout=15)
        if auth_result.get("type") != "auth_ok":
            raise RuntimeError(f"HA WS auth failed: {auth_result}")

        async def supervisor_api(msg_id, endpoint, method="get"):
            await ws.send_json({
                "id": msg_id, "type": "supervisor/api",
                "endpoint": endpoint, "method": method,
            })
            while True:
                msg = await asyncio.wait_for(ws.receive_json(), timeout=15)
                if msg.get("id") == msg_id:
                    if not msg.get("success"):
                        raise RuntimeError(f"supervisor/api {endpoint} failed: {msg}")
                    return msg["result"]

        info = await supervisor_api(1, f"/addons/{MA_ADDON_SLUG}/info")
        ingress_entry = info["ingress_entry"]
        session_result = await supervisor_api(2, "/ingress/session", method="post")
        return ingress_entry, session_result["session"]


async def get_provider_domain(rest_session, ingress_entry, ingress_session_token, item_id):
    async with aiohttp.ClientSession(
        cookies={"ingress_session": ingress_session_token},
        cookie_jar=aiohttp.CookieJar(unsafe=True),
    ) as ma_session:
        ws_url = URL.replace("https://", "wss://").replace("http://", "ws://") + ingress_entry + "/ws"
        async with ma_session.ws_connect(ws_url) as ws:
            await ws.receive_json()  # greeting
            await ws.send_json({
                "command": "music/get_library_item",
                "message_id": item_id,
                "args": {
                    "media_type": "playlist",
                    "item_id": item_id,
                    "provider_instance_id_or_domain": "library",
                },
            })
            for _ in range(50):
                msg = await asyncio.wait_for(ws.receive_json(), timeout=15)
                if msg.get("message_id") == item_id:
                    mappings = msg["result"].get("provider_mappings", [])
                    return mappings[0]["provider_domain"] if mappings else None
    return None


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                         help="print the filtered playlist list, don't write the sensor")
    args = parser.parse_args()

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {TOKEN}"}, timeout=timeout) as rest_session:
        config_entry_id = await get_config_entry_id(rest_session)
        all_playlists = await get_all_playlists(config_entry_id)
        ingress_entry, ingress_session_token = await get_ingress_context(rest_session)

        jellyfin_playlists = []
        for item in all_playlists:
            item_id = item["uri"].rsplit("/", 1)[-1]
            domain = await get_provider_domain(rest_session, ingress_entry, ingress_session_token, item_id)
            if domain == "jellyfin":
                jellyfin_playlists.append({"uri": item["uri"], "label": item["name"]})

        jellyfin_playlists.sort(key=lambda p: p["label"])

        if args.dry_run:
            print(json.dumps(jellyfin_playlists, indent=2))
            return

        await rest_post(rest_session, f"/api/states/{SENSOR_ENTITY_ID}", {
            "state": str(len(jellyfin_playlists)),
            "attributes": {
                "friendly_name": "Homie Dynamic Playlists",
                "icon": "mdi:playlist-music",
                "playlists": jellyfin_playlists,
            },
        })
        print(f"Wrote {len(jellyfin_playlists)} Jellyfin playlist(s) to {SENSOR_ENTITY_ID}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
