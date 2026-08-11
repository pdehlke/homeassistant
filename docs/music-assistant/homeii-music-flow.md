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
ma_url: "http://mass.ehlke.net:8095"
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
network space at all, permission prompt included. `http://hass.ehlke.net:8123` is plain
HTTP, so the request is refused before it reaches Music Assistant.

This breaks two things specifically:
- Sendspin's own WebSocket to `mass.ehlke.net:8095`, so "This device" playback cannot connect.
- Playlist and library artwork, since Music Assistant serves cover art through its own
  `imageproxy` endpoint on the same host and port. This half breaks independently of Sendspin:
  the library metadata HOMEii Flow reads through Home Assistant already carries
  `mass.ehlke.net:8095/imageproxy/...` URLs (Music Assistant's `base_url` config entry, confirmed via
  `/info`), so thumbnails come back blank even for playback that has nothing to do with
  Sendspin.

Player selection, transport control, queue management, and the FLOW wizard are unaffected: those
go through Home Assistant's own WebSocket, which the browser already trusts as same-origin.

Firefox and WebKit-based Safari do not implement this restriction as of this writing ([Chrome
Local Network Access blog post](https://developer.chrome.com/blog/local-network-access),
[WICG explainer](https://github.com/WICG/local-network-access/blob/main/explainer.md)), so both
Sendspin and artwork should work unmodified in either. Not verified directly here; only Chromium
was available to test against. The durable fix for Chrome is putting Home Assistant behind
HTTPS, which makes `hass.ehlke.net` a secure context and turns the outright block into a
one-time permission prompt instead.

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
  "http://hass.ehlke.net:8123/api/states/input_text.homeii_flow_active_player"
```

Confirm Music Assistant's CORS headers directly, bypassing the browser:

```bash
curl -s -o /dev/null -D - -H "Origin: http://hass.ehlke.net:8123" \
  "http://mass.ehlke.net:8095/info" | grep -i access-control
```

Query Music Assistant's own auth setup:

```bash
curl -s -X POST http://mass.ehlke.net:8095/api \
  -H 'Content-Type: application/json' \
  -d '{"message_id":"1","command":"auth/providers"}'
```
