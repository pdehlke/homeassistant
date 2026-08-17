# Retiring `.local`/mDNS hostnames for `hass.ehlke.net` and `mass.ehlke.net`

## Context

On 2026-08-10 the Homie Dashboard fork's `dist/config.js` was changed to hardcode the literal
LAN IP `192.168.4.125` for `WS_URL` (and, derived from it, `BASE`), because a Fire HD 10 tablet
had joined the house for `homie-dash` and FireOS ships with no mDNS resolver at all, so
`homeassistant.local` never resolved there. That fix worked for the tablet, and the same
checkpoint entry ([homie-dashboard-install-plan.md](../homie-dashboard/homie-dashboard-install-plan.md), 2026-08-10) noted the
side effect it introduced: any *other* client loading `homie-dash` from `homeassistant.local`
while Homie's own `fetch()` calls targeted the IP would hit a cross-origin mismatch, since HA's
default CORS config has no `Access-Control-Allow-Origin` for that origin pair. That entry's own
conclusion was that this "does not come up" in practice, because the tablet always uses the IP
for both the outer page and the inner iframe, so the two origins always match there.

That conclusion turned out to be incomplete: it accounted for the tablet, but not for anyone else
checking the same dashboard from a normal browser.

## The bug: Overview C's Solar card showed "History Unavailable"

On 2026-08-11, pde reported that the Hourly Average Power chart in Overview C's Solar overlay had
shown "History Unavailable" since the evening before. First investigation pass got this wrong:
every direct test (replicating the exact `/api/history/period` call the code makes, checking both
Sense entities' live state, checking the deployed Homie Dashboard token's validity against a
pre-deploy backup) came back clean, and a fresh Playwright session against the live code rendered
the chart correctly. The conclusion drawn at that point was that the failure must have been a
transient backend blip, plausible given HA's system log showed real, unrelated DNS/API flakiness
that day (Sense's cloud API, OpenWeatherMap, lg_thinq).

That was wrong, and the reason it looked right is that the reproduction attempt loaded the page
from the same origin `BASE` pointed at (the literal IP), sidestepping the exact cross-origin
mismatch the 2026-08-10 checkpoint had already flagged as a known, real consequence, not a fixed
one. pde supplied the actual counter-evidence: a screenshot from a freshly opened incognito
browser on his laptop, showing the identical "History Unavailable" state, with every other stat
tile on the same view populated with real live numbers.

That screenshot is the tell. The live-populated tiles (Live Usage, Production, Grid, and so on)
come from Home Assistant's WebSocket `state_changed` subscription, which is not subject to the
same-origin restriction the same way a plain `fetch()` is. The one broken element, the Hourly
Average Power chart, is the one thing on that view built from an independent `fetch()` call to
`/api/history/period`. Reloading via `http://homeassistant.local:8123/homie-dash/0` reproduced it
exactly: the browser blocked the request with

```
Access to fetch at 'http://192.168.4.125:8123/api/history/period/...' from origin
'http://homeassistant.local:8123' has been blocked by CORS policy: Response to preflight
request doesn't pass access control check: No 'Access-Control-Allow-Origin' header is present
on the requested resource.
```

repeating on every 5-second retry the Solar view's own refresh loop makes while it's open. The
same block hit the calendar fetches (`calendar.home`, `calendar.rachio_base_station_ca358975`)
in the same console log, confirming this was never chart-specific; it affects every one of
Homie's plain `fetch()` calls whenever the outer page and `BASE` don't share an origin.

## The fix: real DNS instead of mDNS

The actual problem was never "the tablet needs an IP." It was "the tablet's OS can't do mDNS,"
and the fix for that turned out to be giving every client, tablet included, one hostname that
resolves without mDNS at all. pde added DNS records under his own domain:

- `hass.ehlke.net` → `192.168.4.125`
- `mass.ehlke.net` → `192.168.4.125`

Both resolve via ordinary DNS, which FireOS supports natively (mDNS was the specific thing it
lacked, not DNS in general). Both still resolve to the same private LAN address as before,
plain HTTP, same ports (8123 for HA, 8095 for Music Assistant), confirmed directly: no TLS
listener on either host, `curl` against both returns the same 200 responses `homeassistant.local`
and `mass.local` used to. Writing these hostnames down carries the same
not-useful-without-network-access exception as the LAN IP addresses already documented as safe
to record here, they resolve to a private RFC1918 address, meaningless from the public internet.

With that in place, `dist/config.js`'s `WS_URL` moved from the literal IP to `hass.ehlke.net`,
retiring the 2026-08-10 workaround entirely: every client, tablet or otherwise, now loads the
outer page and gets Homie's inner `fetch()` calls from the same hostname, so the cross-origin
mismatch can't recur regardless of which client asks.

## What changed

- `homie-dashboard` fork: `dist/config.js`'s `WS_URL` (and derived `BASE`) now point at
  `hass.ehlke.net`. Release `20260811.3`. `test/screen-a.test.cjs`'s regression test now asserts
  the DNS name and forbids both the old hostname and the literal IP.
- This repo: [CLAUDE.md](../../CLAUDE.md), the `home-assistant` skill ([SKILL.md](../../.claude/skills/home-assistant/SKILL.md), `references/*.md`,
  `scripts/*.py`), and every doc that referenced `homeassistant.local`/`mass.local` as current
  guidance now say `hass.ehlke.net`/`mass.ehlke.net`. Historical narrative (what a doc says was
  literally true at some past date, the mDNS conflict during the Mac mini migration, the
  original dual-stack login bug) was left alone; only forward-looking instructions were updated.
- Live Home Assistant: the `dashboard-sound` Lovelace dashboard's HOMEii Flow card had
  `ma_url: "http://mass.local:8095"` hardcoded; updated to `mass.ehlke.net`.
- SSH/SFTP access (`root@<host>:2222`) confirmed working against `hass.ehlke.net` directly.

## What's still open

- **Music Assistant's own `base_url` setting is still the literal IP.** Confirmed via its `/info`
  endpoint: `"base_url": "http://192.168.4.125:8095"`. This feeds the `imageproxy` URLs embedded
  in library metadata (see [homeii-music-flow.md](../music-assistant/homeii-music-flow.md)), so artwork links will keep pointing at the
  old IP until it's changed. There's no HA-side options flow for the `music_assistant` config
  entry (`supports_options: false`), and Music Assistant's own API rejects the HA token and
  needs separate credentials this session doesn't have (a gap the skill already documented
  before this investigation). Needs a manual change in Music Assistant's own web UI, its config
  domain is named `webserver`, so look there first, not through Home Assistant.
- **The Fire HD tablet's Fully Kiosk start URL** was not checked or changed as part of this pass;
  confirm it's pointed at `hass.ehlke.net` (or update it) the next time the tablet is at hand.
- **HA's own `external_url`/`internal_url`** are both unset (checked via `/api/config`), so there
  was nothing to change there. No `cors_allowed_origins` override exists either; the fix here is
  that both origins now match, not that CORS was relaxed.

## Verification

Reproduced the exact bug (CORS-blocked `/api/history/period` calls, "History Unavailable"
rendered, repeating every 5 seconds) by loading `homie-dash` via `http://homeassistant.local:8123`
against the pre-fix code. Confirmed fixed by loading the same view via
`http://hass.ehlke.net:8123` against the deployed `20260811.3` release: the chart rendered real
data, zero CORS-related console entries, and the same calendar fetches that failed alongside the
chart succeeded too.
