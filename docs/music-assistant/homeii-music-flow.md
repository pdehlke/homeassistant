# HOMEii Flow music dashboard

Replaced the two cards on the Sound dashboard (`custom:wall-clock-card`, `custom:sonos-card`)
with [HOMEii Flow](https://github.com/r11a/homeii-music-flow), a HACS Lovelace card built for
Music Assistant. Installed 2026-08-04 against Home Assistant 2026.7.4.

| Object | Value |
|---|---|
| Card | `custom:homeii-music-flow`, HACS repo `r11a/homeii-music-flow`, v5.9.3 |
| Dashboard | `dashboard-sound` ("Sound"), single `panel` view |
| Helper | `input_text.homeii_flow_active_player` |
| Wall clock | moved to new `dashboard-clock` ("Clock") dashboard |

## Why the wall clock had to move rather than stay

The Sound dashboard held three cards, not two: a `heading` reading "New section", the
`wall-clock-card`, and the `sonos-card`. All three came out; HOMEii Flow replaced them as a
single card.

The obvious place to park the wall clock was the Overview dashboard. That turned out to be the
wrong assumption. On this Home Assistant version, the sidebar's "Overview" entry is not a
conventional storage dashboard. It is a generated dashboard at url_path `home`, using the built
in `home` strategy, with one view per area (Gym, Living Room, Kitchen, Bedroom, Office) plus
`home-media-players` and `home-other-devices` views, none of them backed by a stored config.
Saving anything to it means taking control of it: freezing the current five areas and two
summary views as static YAML, so new areas and newly discovered devices stop appearing on their
own. That cost was not worth a wall clock, so it went to a new storage dashboard,
`dashboard-clock`, with its original section shape, `grid_options`, and glass layout preserved
unchanged.

One dead end along the way: a first attempt saved a view to the legacy `lovelace` dashboard
(url_path `lovelace`, the pre-strategy default). Nothing in the sidebar or navigation links to
it on this instance; it was an orphan. Deleted with `lovelace/config/delete`, confirmed back to
`config_not_found`.

## Why the Sound view is `panel`, not `sections`

The Sound dashboard's section is 36 columns wide (`column_span: 3` on a 12-column section grid;
see the Lovelace notes in the `home-assistant` skill for the math). The obvious move was to give
the card `grid_options: {columns: 36, rows: "auto"}` inside a `sections` view.

That rendered the card at 431px wide inside a 1310px section, stuck in the card's mobile layout.
The cause is in the card's own code: `homeii-music-flow.js` implements `getGridOptions()` and
hardcodes `max_columns: 12`. Home Assistant clamps any section card to whatever `getGridOptions`
declares, so no `grid_options` set from outside the card can push it past 12 of 36 columns. This
is a property of the card, not a config mistake, and there is no documented override for it.

Switching the view `type` from `sections` to `panel` sidesteps the clamp: panel views give the
one card the full width with no grid sizing at all. The card then renders its desktop layout,
left player rail plus full now-playing pane plus playlist carousel. Confirmed by screenshot.
The tradeoff is that a panel view holds exactly one card, so nothing else can share the Sound
dashboard's main view without a second view added alongside it.

## Configuration used

```yaml
type: custom:homeii-music-flow
card_id: sound-main
language: auto
theme_mode: auto
phone_display_mode: auto
active_player_helper_entity: input_text.homeii_flow_active_player
ma_url: "https://mass.ehlke.net"
ma_token: "<redacted>"
```

`active_player_helper_entity` publishes the currently selected player's entity ID to the
helper, confirmed live: it read `media_player.gym` after selecting that player in the UI.
Nothing currently consumes it; it exists so a future automation (for example, "announce on
whichever room is playing") has something to read.

## Sendspin: works in the API, blocked in the browser

`ma_url` and `ma_token` enable Sendspin, HOMEii Flow's "play through this browser tab" feature.
The token is a Music Assistant long-lived access token, generated via `auth/token/create`
(role `admin`, scoped to the account that created it), not a Home Assistant token.
Music Assistant on this instance runs 2.9.10, schema 31, and authentication has been mandatory
there since schema 28. The login provider used was `homeassistant` (OAuth through HA), which the
server also exposes alongside `builtin` username and password, queried live via
`auth/providers`. Token creation was done by hand in Music Assistant's web UI at
`http://mass.ehlke.net:8095` under Settings, Profile, since it is a one-time interactive step with no
REST equivalent worth scripting. See the [Music Assistant reference in the `home-assistant`
skill](https://www.music-assistant.io/first-run/) for the general shape of first-run auth if this
needs repeating for another integration.

That token does not currently work from a browser. Chrome, Edge, and Chromium-based mobile
WebViews refuse the connection outright:

```
WebSocket connection to 'ws://mass.ehlke.net:8095/ws' failed:
net::ERR_BLOCKED_BY_LOCAL_NETWORK_ACCESS_CHECKS

Access to image at 'http://mass.ehlke.net:8095/imageproxy?...' blocked by CORS policy:
The request client is not a secure context and the resource is in more-private
address space `local`.
```

Music Assistant is not misconfigured. It returns `Access-Control-Allow-Origin: *` on every
response, confirmed with a direct `curl`. The block is Chrome's [Local Network
Access](https://developer.chrome.com/blog/local-network-access) restriction: a page must be a
secure context (HTTPS, or `localhost`) before Chrome will let it reach an address in local
network space at all, permission prompt included. `http://hass.ehlke.net` is plain
HTTP, so the request is refused before it reaches Music Assistant.

This breaks two things specifically:
- Sendspin's own WebSocket to `mass.ehlke.net`, so "This device" playback cannot connect.
- Playlist and library artwork, since Music Assistant serves cover art through its own
  `imageproxy` endpoint on the same host. This half breaks independently of Sendspin:
  the library metadata HOMEii Flow reads through Home Assistant already carries
  `mass.ehlke.net/imageproxy/...` URLs (Music Assistant's `base_url` config entry, confirmed via
  `/info`), so thumbnails come back blank even for playback that has nothing to do with
  Sendspin.

Since the 2026-08-24 Caddy reverse-proxy migration (see
[docs/networking/caddy-reverse-proxy.md](../networking/caddy-reverse-proxy.md)), the old
`mass.ehlke.net:8095` direct port doesn't exist any more either, on top of the Chrome block
above: even a client unaffected by Local Network Access (Firefox, Safari) now has to go through
`mass.ehlke.net` on port 80 like everything else. The quoted console errors below predate that
change and still show the original `:8095` URLs; they're the literal captured output from
2026-08-04 and are left as recorded, not evidence of the current URL.

Player selection, transport control, queue management, and the FLOW wizard are unaffected: those
go through Home Assistant's own WebSocket, which the browser already trusts as same-origin.

Firefox and WebKit-based Safari do not implement this restriction as of this writing ([Chrome
Local Network Access blog post](https://developer.chrome.com/blog/local-network-access),
[WICG explainer](https://github.com/WICG/local-network-access/blob/main/explainer.md)), so both
Sendspin and artwork should work unmodified in either. Not verified directly here; only Chromium
was available to test against. The durable fix for Chrome is putting Home Assistant behind
HTTPS, which makes `hass.ehlke.net` a secure context and turns the outright block into a
one-time permission prompt instead.

### Update, 2026-08-24: HTTPS landed, and the predicted fix was half right

Caddy's automatic HTTPS went live the same day as the port-drop migration above (real Let's
Encrypt certificate; see [docs/networking/caddy-reverse-proxy.md](../networking/caddy-reverse-proxy.md)).
Re-tested live against `dashboard-sound` in Chromium via Playwright, authenticated as `Pete`:

- **The outright Local Network Access block is gone.** `net::ERR_BLOCKED_BY_LOCAL_NETWORK_ACCESS_CHECKS`
  did not appear anywhere in the console on either pass below. The prediction above was correct
  on this specific point: a secure-context page no longer gets refused outright.
- **First pass (before fixing this card's `ma_url`) surfaced a different, new problem:** the
  live `dashboard-sound` HOMEii Flow card still had `ma_url: "http://mass.ehlke.net"` (set by the
  2026-08-24 port-drop migration, before HTTPS existed). Loading that over the now-HTTPS page
  produced Mixed Content errors instead: `img` elements got silently auto-upgraded to HTTPS by
  Chrome (and then 400'd, see below), while at least one `fetch()`-based request was hard-blocked:
  "the content must be served over HTTPS."
- **Fixed the immediate cause:** updated the live card's `ma_url` to `https://mass.ehlke.net` via
  `apply-card.py` (`HA_MATCH_TYPE=custom:homeii-music-flow`, dry-run first, one match; the
  "Configuration used" block above now reflects this). The Mixed Content errors disappeared on
  reload.
- **What's left, confirmed still broken over HTTPS with the corrected `ma_url`:**
  - Artwork: `GET https://mass.ehlke.net/imageproxy?...` (both the auto-upgraded `<img>` requests
    and direct `fetch()` calls) returns `400`. A `fetch()`-based variant additionally fails CORS
    preflight: `Response to preflight request doesn't pass access control check: No
    'Access-Control-Allow-Origin' header is present`, despite Music Assistant returning
    `Access-Control-Allow-Origin: *` on ordinary `GET` responses (confirmed via direct `curl`
    against `/info`, not against `/imageproxy` specifically, and not against an `OPTIONS`
    preflight). The card fell back to its own placeholder art (see
    `evidence`-style screenshot from this session), not real cover art.
  - Sendspin: `WebSocket connection to 'wss://mass.ehlke.net/ws' failed: WebSocket is closed
    before the connection is established.` No longer the outright block from before, but not a
    working connection either. Plausible cause, not confirmed: Chrome's Local Network Access
    permission prompt requires a real user gesture and a click Playwright's automated session
    never produced. A real browser tab with pde clicking through the prompt may behave
    differently. Not reproduced with a real user gesture; worth a manual re-check before
    concluding this is a deeper bug.
  - **Suspected root cause of the artwork half:** Music Assistant's own `base_url` setting
    (`webserver` config, confirmed via `/info` in the earlier hostname-migration writeup) was
    last set to `http://mass.ehlke.net` by the port-drop migration and has **not** been updated to
    `https://`. That setting is what gets baked into the `imageproxy` URLs embedded in library
    metadata HOMEii Flow reads through Home Assistant, independent of this card's own `ma_url`.
    Not fixed here: it lives in Music Assistant's own web UI (Settings, not reachable through
    Home Assistant or `$HA_TOKEN`; see the note above on how the Sendspin token itself was
    created), which needs pde's own interactive login. Until it moves to `https://`, expect the
    artwork problem to persist regardless of this card's `ma_url`.

Net effect: HTTPS fixed the browser-level outright block Chrome's Local Network Access imposed,
exactly as predicted, but did not automatically fix Sendspin or artwork. Those need every
http-valued setting in the chain (this card's `ma_url`, done; Music Assistant's own `base_url`,
not done) actually flipped to https, and possibly a real user gesture for the permission prompt
Sendspin's WebSocket depends on.

## Installing HOMEii Flow via the HACS WebSocket API

HACS has no REST surface. Installing a custom repository plugin from a script takes two
WebSocket calls in sequence, using the `scripts/haws.py` client from the `home-assistant` skill:

```bash
python3 scripts/haws.py \
  '{"type":"hacs/repositories/add","repository":"r11a/homeii-music-flow","category":"plugin"}'
```

The add call returns no useful ID; look it up afterwards from the repository list:

```bash
python3 scripts/haws.py '{"type":"hacs/repositories/list","categories":["plugin"]}' \
  | python3 -c "
import json,sys
for r in json.loads(sys.stdin.readline())['result']:
    if r['full_name'] == 'r11a/homeii-music-flow': print(r['id'])
"
```

Then download by that numeric ID, which registers the Lovelace resource automatically:

```bash
python3 scripts/haws.py \
  '{"type":"hacs/repository/download","repository":"<id>","version":"v5.9.3"}'
```

`hacs/repository/add` and `hacs/repository` are not valid command names, despite reading like
plausible ones; they return `unknown_command`. The correct pair is `hacs/repositories/add` then
`hacs/repository/download`.

## Reproducing the checks

Confirm the resource registered:

```bash
python3 scripts/haws.py '{"type":"lovelace/resources"}'
```

Confirm the helper is live:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "https://hass.ehlke.net/api/states/input_text.homeii_flow_active_player"
```

Confirm Music Assistant's CORS headers directly, bypassing the browser:

```bash
curl -s -o /dev/null -D - -H "Origin: https://hass.ehlke.net" \
  "https://mass.ehlke.net/info" | grep -i access-control
```

Query Music Assistant's own auth setup:

```bash
curl -s -X POST https://mass.ehlke.net/api \
  -H 'Content-Type: application/json' \
  -d '{"message_id":"1","command":"auth/providers"}'
```
