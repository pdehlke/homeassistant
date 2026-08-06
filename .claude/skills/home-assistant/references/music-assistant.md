# Music Assistant

Server 2.9.10, schema 31, running as an HA add-on. `http://mass.local:8095`, also `http://192.168.4.125:8095`.

## Reaching MA's full API through HA ingress

The `music_assistant.*` HA services cover playback and queries only. Anything else, favorites included, needs MA's own API. MA rejects `$HA_TOKEN` directly, **but HA's ingress proxy authenticates on your behalf**. This works and is the way in.

`GET /api/hassio/*` over REST returns **401** with a long-lived token. Use the WebSocket `supervisor/api` command instead, which does work:

```bash
python3 scripts/haws.py '{"type":"supervisor/api","endpoint":"/addons","method":"get"}'
python3 scripts/haws.py '{"type":"supervisor/api","endpoint":"/addons/d5369777_music_assistant/info","method":"get"}'
python3 scripts/haws.py '{"type":"supervisor/api","endpoint":"/ingress/session","method":"post"}'
```

Add-on slug is `d5369777_music_assistant`. Read `ingress_entry` from its info; **do not hardcode it**, the token can rotate. Then open MA's websocket through HA carrying the session as a cookie:

```python
async with aiohttp.ClientSession(cookies={"ingress_session": SESSION},
                                 cookie_jar=aiohttp.CookieJar(unsafe=True)) as s:
    async with s.ws_connect(f"ws://homeassistant.local:8123{INGRESS_ENTRY}/ws") as ws:
        await ws.receive_json()          # server greeting, no auth command needed
        await ws.send_json({"command": "music/favorites/add_item",
                            "message_id": "f1", "args": {"item": uri}})
```

No `auth` command is required; arriving through ingress is the authentication. Useful commands include `music/favorites/add_item`, `music/favorites/remove_item`, `music/library/add_item`, `music/library/remove_item`, `music/get_library_item`.

### Draining replies

MA emits a stream of events alongside command replies. Match on your `message_id` and ignore everything else. Favoriting a **provider** item is slow, since MA fetches and imports it, so allow generous per-message timeouts (90s) and a high drain count (400). Tight limits caused a hang partway through a 42-item batch.

Sessions are cheap. Mint a fresh one per run rather than reusing.

## Two APIs, and which one you can use

- **HA-side services** (`music_assistant.*`). This is the usable path. `$HA_TOKEN` authorizes it.
- **MA server's own WebSocket**, direct at `ws://mass.local:8095/ws`. Connecting and reading the greeting works unauthenticated, and `GET /info` over HTTP is open, but any real command returns `Authentication required.` `$HA_TOKEN` is rejected here with `Invalid or expired token`. **Do not go direct.** Reach the same API through HA ingress instead, as described above, which needs no MA credentials at all.

## Calling the services

Four return data: `search`, `get_library`, `get_queue`, and their responses are **not optional**. You must ask for the response or the call is rejected.

REST:

```bash
curl -s -X POST -H "$HB" -H "Content-Type: application/json" \
  -d '{"config_entry_id":"<id>","media_type":"radio","limit":500}' \
  "$U/api/services/music_assistant/get_library?return_response"
```

WebSocket (preferred, see below):

```bash
python3 scripts/haws.py '{"type":"call_service","domain":"music_assistant",
  "service":"get_library","return_response":true,
  "service_data":{"config_entry_id":"<id>","media_type":"radio","limit":500}}'
```

Look up `config_entry_id` rather than hardcoding it; it changes if the integration is re-added:

```bash
curl -s -H "$HB" $U/api/config/config_entries/entry \
  | jq -r '.[] | select(.domain=="music_assistant") | .entry_id'
```

It was `01KZ4ZHK4H9WS68FPMYTZG3JR9` on 2026-08-04.

## The `pagination` trap

`get_library`'s published schema advertises a nested `pagination: {limit, offset}` field. **It does not work.** The service validator rejects it:

```
extra keys not allowed @ data['pagination']
```

Pass `limit` and `offset` **top-level** instead. This is a schema/validator mismatch in the integration, not a usage error, so expect the published schema to keep lying about it.

The default limit is 25 and it silently truncates. A result with exactly 25 items usually means there are more. Radio looked like 25 stations until `limit: 500` revealed 36.

## Debug service calls over WebSocket, not REST

This generalizes beyond Music Assistant. A rejected service call over REST returns a bare `400: Bad Request` with no body. The identical call over WebSocket returns the actual voluptuous validator message naming the offending key. When a service call fails and you cannot see why, re-issue it through `scripts/haws.py`.

## What is in the library

Checked 2026-08-04:

| Media type | Count |
|---|---|
| artist | 0 |
| album | 0 |
| track | 0 |
| playlist | 8 |
| radio | 36 |
| audiobook | 0 |
| podcast | 0 |

**Pandora is connected.** pde added the account on 2026-08-03. Those 36 "radio" items are Pandora stations: 35 serve artwork from `content-images.p-cdn.com` or `mediaserver-*.pandora.com`, and the list contains *Thumbprint Radio*, which is Pandora-exclusive, alongside personal artist stations such as *Cocteau Twins Radio*, *M83 Radio* and *Dead Can Dance Radio*.

**The zeros for artist, album and track do not mean an empty library.** Pandora is a station service. It exposes no browsable artist/album/track catalogue, so MA represents the entire account as radio items. Judge whether a provider is present from the radio and playlist counts plus artwork hosts, never from the artist/album/track counts.

In `browse_media`, MA's own "Radio stations" node is distinct from the separate `media-source://radio_browser` entry, which belongs to HA's Radio Browser integration. Do not conflate them.

The 8 playlists are MA's built-in smart playlists, not user-created: *500 Random tracks (from library)*, *All favorited tracks*, *Infinite Mix (favorites)*, *Infinite Mix (library)*, *Random Album (from library)*, *Random Artist (from library)*, *Recently added tracks*, *Recently played tracks*. These do draw on library and favorites, which Pandora does not populate, so they will still produce nothing. Zero of the 36 stations are marked `favorite`.

## SiriusXM is also connected, but it is invisible to `get_library`

Added 2026-08-04. Channels return `siriusxm://radio/<id>` URIs with artwork on `pri.art.prod.streaming.siriusxm.com`. Some ids are slugs (`siriushits1`, `chill`, `leftofcenter`), others numeric (`9413`, `8186`).

**`get_library` does not see it.** The radio count stayed at exactly 36 after SiriusXM was added, because MA's *library* holds only what has been added or synced to your account. Pandora's stations are your personal library and sync in; SiriusXM is a broadcast catalogue and does not.

This matters because it makes `get_library` the wrong probe for provider presence. That mistake was made here: the plan for verifying SiriusXM was "check whether the radio count jumps", it did not jump, and the provider was working the whole time.

`search` will *detect* a provider (read the `uri` scheme of the hits), but **never use it to enumerate**. The SiriusXM provider's `search` does a plain substring match on the channel **name only** and stops at `limit`, whose default is **5**. Searching `radio` returned 66 `siriusxm://` hits, which is not a channel count; it is "channels with 'radio' in the name, up to the cap". The real total is 436, so that estimate was low by a factor of nearly seven. 371 channels have no "radio" in their name at all (*The Pulse*, *80s on 8*, *PopRocks*, *Unwell Music*).

**To enumerate a provider, use MA's `music/browse` over ingress.** Note this is MA's API, not HA's `media_player/browse_media`; the latter is a library view and returns `Media not found` for `siriusxm://`, which is what made this look impossible at first.

```bash
# 1. root browse lists every provider that supports BROWSE, with its path
{"command":"music/browse","message_id":"r","args":{}}
# 2. browse that path for the provider's full catalogue
{"command":"music/browse","message_id":"s","args":{"path":"siriusxm://"}}
```

Root browse also yields the provider **instance ids**, which are otherwise hard to get: `builtin://`, `pandora://`, `siriusxm://`.

Provider browse is **not paginated**. The SiriusXM provider returns its whole `_channels` list in one response, and `music/browse` takes no limit or offset. Checked 2026-08-04: 437 entries, being one `..` folder (`library://folder/root`) plus **436 channels**, all `siriusxm://`, 436 unique uris, one duplicated display name (*Little Miss Twain Radio*).

When counting, filter `media_type == "radio"` to drop the `..` folder, or you will report one too many.

### Never infer the provider from library items

The library item schema is exactly `media_type, uri, name, version, image, favorite, explicit`. **There is no `provider` field.** Querying `.provider` returns null for every item, which reads as "no provider configured" and is wrong. That error was made here once, and it produced a confident, incorrect report that Music Assistant had no provider at all.

The general lesson: a null from a field you assumed exists is not evidence of absence. Dump one full object and read its real keys before concluding anything from a field query.

To identify a provider, use the `image` host, or resolve the `uri`. `uri` is `library://radio/<n>`, the library-local form, which hides the origin.

### Naming the provider instance needs MA credentials

MA's WebSocket rejects `$HA_TOKEN` with `Invalid or expired token`, and `/api/hassio/addons` through the HA proxy returns nothing usable. The provider's instance id and domain therefore cannot be read programmatically right now. Identification rests on artwork hosts and station naming, which is circumstantial but conclusive.

## Players

11 MA devices. 7 enabled, 4 disabled at the device level (`disabled_by: device`).

Enabled: `media_player.gym` (Sonos Playbar), `media_player.crestron` (SOUNDFORM AirPlay2 Adapter), `media_player.gymnasium` (Apple TV 4K), `media_player.lsx_ii_045089_2` (LSX II), `media_player.carol_2` (VFD40M-0809), `media_player.samsung_qn90ba_85`, `media_player.samsung_tu7000_60_tv`, `media_player.lg_webos_tv_um7300pua`.

Disabled: Pete's MacBook Pro, Pete's Mac mini, Office AirPort Express.

Each player also gets a `button.<name>_favorite_current_song`.

Note the `_2` suffixes. `media_player.carol_2` and `media_player.lsx_ii_045089_2` are the MA entities; the unsuffixed names belong to Sonos or the native integration. Target the MA ones for `music_assistant.*` services, since those services filter on `integration: music_assistant`.

`get_queue` returns `No active queue found` when a player is idle rather than an empty queue. That is normal, not an error.

## Playing something

Pandora stations are the working content. Play one by URI:

```bash
python3 scripts/haws.py '{"type":"call_service","domain":"music_assistant","service":"play_media",
  "target":{"entity_id":"media_player.gym"},
  "service_data":{"media_id":"library://radio/2","media_type":"radio"}}'
```

`play_media` targets only entities whose integration is `music_assistant`, so use the MA entity (note the `_2` suffixes above), not the Sonos one.
