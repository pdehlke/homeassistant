# Home Assistant and Music Assistant behind a Caddy reverse proxy

## What changed

As part of moving Home Assistant off the Raspberry Pi onto a Proxmox VE host (see
[docs/hardware/mac-mini-migration.md](../hardware/mac-mini-migration.md) and
[ADR-0063](../adr/0063-proxmox-virtualization-over-bare-metal.md)), a small Caddy LXC container
now sits in front of every HTTP service on that machine and routes by hostname:
`hass.ehlke.net` to Home Assistant, `mass.ehlke.net` to Music Assistant, and `jellyfin.ehlke.net`
to the new Jellyfin instance (out of scope for this repo beyond noting it shares the same proxy).
See [ADR-0064](../adr/0064-caddy-reverse-proxy-replaces-direct-ports.md) for why name-based
routing was chosen over continuing to expose each service's own port.

The direct ports Home Assistant and Music Assistant used to answer on, `:8123` and `:8095`, no
longer work at all, from any client, on this LAN or otherwise. Everything goes through the proxy
on port 80 now. This is a bigger change than dropping a port number: it landed at the same time as
the underlying host itself changed, from the Raspberry Pi 4 to a VM on the new Mac mini, so the
LAN address behind both hostnames changed too.

## Verified live, 2026-08-24

- `hass.ehlke.net` and `mass.ehlke.net` both resolve to `192.168.4.143`. Before this migration
  they resolved to the Raspberry Pi's `192.168.4.125`
  ([docs/networking/hostname-migration-to-ehlke-net.md](hostname-migration-to-ehlke-net.md)).
- `http://hass.ehlke.net/` and `http://mass.ehlke.net/` both return `200`, serving the real Home
  Assistant frontend and Music Assistant UI respectively, not just a static placeholder — `GET
  /api/` on the HA hostname returns `401` (a real, authenticated API behind the proxy, not a 404),
  and `GET /info` on the MA hostname returns Music Assistant's real server info JSON.
  `Authorization: Bearer $HA_TOKEN` against `/api/` still authenticates normally, and returns
  `401`/`200` rather than the `400` HA's `http` integration returns when a reverse proxy's
  `X-Forwarded-For` header comes from an address it doesn't trust, so the proxy is correctly
  configured as HA's trusted proxy (see the `pdehlke/proxmox` repo's `mac-mini-proxmox-plan.md`,
  section 8.5, for the `trusted_proxies` step this depends on).
- `http://hass.ehlke.net:8123/` and `http://mass.ehlke.net:8095/` both refuse the connection
  outright (`curl: (7) Failed to connect`), not a redirect or an error page. Same for `:443` on
  either hostname — still plain HTTP only, no TLS, same as before this change.
- Response headers carry `Via: 1.1 Caddy`, confirming the proxy in front.
- HA's own `external_url`/`internal_url` (`GET /api/config`) are both still unset, unaffected by
  this change — nothing to update there.
- **SSH/SFTP broke as a side effect, and needed its own fix.** `root@hass.ehlke.net:2222`
  (the address every doc used to document) now refuses the connection outright, not because SSH
  is proxied (it isn't — Caddy only speaks HTTP) but because `hass.ehlke.net` itself now resolves
  to the proxy's address, `192.168.4.143`, which has nothing listening on `2222`. SSH has to go
  directly to the Home Assistant VM's own LAN address instead: `root@192.168.4.141:2222`,
  confirmed live 2026-08-24 (the SSH & Web Terminal add-on was already running; this wasn't the
  usual manual-boot `Connection refused`, confirmed by checking its state first). Every doc and
  skill file that hardcoded the old `hass.ehlke.net:2222` target as current instructions
  (`home-assistant` skill's `SKILL.md`/`references/api-access.md`, `verify-homie-dashboard`'s
  `SKILL.md` in the sibling repo) now points at `192.168.4.141`. This address was found by
  testing directly, not read from any config; reconfirm it if SSH ever breaks again.

## What was updated as a result

- This repo: every doc and skill file (`home-assistant`, `verify-home-assistant`) that hardcoded
  `hass.ehlke.net:8123` or `mass.ehlke.net:8095` as current instructions now uses the bare
  hostname. Historical narrative that quoted an exact past URL or error message (the
  2026-08-10/11 checkpoints in
  [homie-dashboard-install-plan.md](../homie-dashboard/homie-dashboard-install-plan.md), the
  captured browser console errors in
  [homeii-music-flow.md](../music-assistant/homeii-music-flow.md)) was left alone, same
  convention the previous hostname migration used.
- `homie-dashboard` fork: `dist/config.js`'s `WS_URL` dropped `:8123`, deployed and Playwright-
  verified; `test/screen-a.test.cjs`'s regression test updated to match. The sibling
  `verify-homie-dashboard` skill's hardcoded `:8123` URLs (its `SKILL.md`, feature docs, and
  `scripts/doctor.py`/`make-auth-state.py`) were updated too, so verification runs against the
  live instance instead of a dead port.
- Live Home Assistant: the `dashboard-sound` Lovelace dashboard's HOMEii Flow card had `ma_url:
  "http://mass.ehlke.net:8095"` hardcoded (the same card the 2026-08-11 hostname migration had
  already fixed once, from `mass.local:8095`); updated to `http://mass.ehlke.net`.
- Music Assistant's own `base_url` setting (`webserver` config, its own web UI, not reachable
  through Home Assistant) was `http://mass.ehlke.net:8095` — already updated once, from the
  literal IP, by the 2026-08-11 migration's leftover item — and is now `http://mass.ehlke.net`.
  This feeds the `imageproxy` URLs embedded in library metadata; see
  [homeii-music-flow.md](../music-assistant/homeii-music-flow.md).

## What's still open

- **The Fire HD tablet's Fully Kiosk start URL** was not checked as part of this pass, same gap
  the 2026-08-11 migration left open. If it hardcodes a port anywhere, confirm or fix it next time
  the tablet is at hand. Now doubly worth checking: if it hardcodes `http://` rather than a
  bare hostname, it will hit the 308 redirect to `https://` on every load instead of connecting
  directly.
- **Music Assistant's own `base_url` setting** is still `http://mass.ehlke.net` (set by this
  migration, before HTTPS existed) and needs updating to `https://` through Music Assistant's own
  web UI (Settings; not reachable through Home Assistant or `$HA_TOKEN`). Until it moves, expect
  the artwork half of the issue below to persist regardless of anything on the HA side. See the
  2026-08-24 HTTPS update in [homeii-music-flow.md](../music-assistant/homeii-music-flow.md) for
  the full evidence trail.
- **The Chrome Local Network Access block on Sendspin and Music Assistant artwork**
  ([homeii-music-flow.md](../music-assistant/homeii-music-flow.md)) is **partially resolved** by
  the HTTPS work below: the outright block predicted to need HTTPS is confirmed gone. Sendspin's
  WebSocket and artwork loading both still fail, for different reasons (a CORS-preflight gap and
  Music Assistant's still-http `base_url`, respectively); see that document's 2026-08-24 update
  for the full detail. Not closed.
- **Whether the Raspberry Pi's DNS-under-load flakiness
  ([nabucasa-remote-ui-dns-fragility.md](../nabucasa-remote-access/nabucasa-remote-ui-dns-fragility.md))
  reproduces on the new VM** is unverified. That document's root-cause theory was specific to the
  Pi's resource constraints; nothing here re-tested it against the new host.

## Verified live, 2026-08-24 (HTTPS enabled by default)

Later the same day as the plain-HTTP migration above, Caddy's automatic HTTPS was turned on for
all three site addresses (`hass.ehlke.net`, `mass.ehlke.net`, `jellyfin.ehlke.net`), the
possibility the ADR-0064 decision explicitly left open ("a single place to add TLS later").

- `https://hass.ehlke.net/` and `https://mass.ehlke.net/` both return `200` over TLS 1.3, HTTP/2,
  with a real publicly-trusted certificate: `subject: CN=hass.ehlke.net` (and the `mass` equivalent),
  `issuer: Let's Encrypt (CN=YE1)`, issued 2026-08-24, valid through 2026-11-22, the standard
  90-day Let's Encrypt lifetime. This works despite both hostnames resolving only to an internal
  LAN address (`192.168.4.143`, confirmed from an external resolver too), which means Caddy is not
  using the HTTP-01 challenge (port 80 on that address isn't reachable from the internet); the
  exact challenge mechanism (most likely DNS-01 against whatever provider hosts the `ehlke.net`
  zone) lives in the Caddy config on the LXC itself, not in this repo, and wasn't confirmed directly here.
- `http://hass.ehlke.net/` and `http://mass.ehlke.net/` now return `308 Permanent Redirect` to the
  `https://` equivalent, rather than serving plain HTTP as the migration above described. Plain
  HTTP access still works in the sense that the redirect itself doesn't require TLS, but nothing
  is served over it directly any more.
- `alt-svc: h3=":443"` is advertised, meaning Caddy also offers HTTP/3, though this wasn't tested
  independently of HTTP/2.

### What was updated as a result

- This repo: every doc and skill file (`home-assistant`, `verify-home-assistant`) that used
  `http://hass.ehlke.net`/`http://mass.ehlke.net` as current instructions now uses `https://`,
  including script defaults (`scripts/*.py`'s `HA_URL` fallback). Same convention as the port-drop
  migration: historical narrative that quoted an exact past URL or error message (the 2026-08-10/11
  checkpoints in [homie-dashboard-install-plan.md](../homie-dashboard/homie-dashboard-install-plan.md),
  the captured browser console errors and the "Configuration used"-adjacent one-time token-creation
  note in [homeii-music-flow.md](../music-assistant/homeii-music-flow.md)) was left alone.
- Live Home Assistant: the `dashboard-sound` Lovelace dashboard's HOMEii Flow card had `ma_url:
  "http://mass.ehlke.net"` hardcoded (set by the port-drop migration above); updated to
  `https://mass.ehlke.net` via `apply-card.py`, deployed and Playwright-verified. This is the one
  that turned out to matter for the Local Network Access investigation below.
- `homie-dashboard` fork: `dist/config.js`'s `WS_URL` was still `ws://hass.ehlke.net/api/websocket`
  from the port-drop migration. **This was a live outage, not just a stale doc**: a browser refuses
  to open a plain `ws://` connection from a page loaded over `https://`, so `homie-dash` was
  rendering all-dashes ("—") for every value, confirmed by loading it live before the fix.
  Updated `WS_URL` to `wss://`, bumped `HOMIE_ASSET_VERSION` `20260824.1` → `20260824.2`,
  `test/screen-a.test.cjs`'s config-host regression test updated to assert `wss://` (106/106 pass),
  deployed via the same SFTP splice-and-atomic-rename pattern as every prior `config.js` change,
  `homie-dash`'s Lovelace iframe `?v=` bumped to match. Live-verified via Playwright as the
  `Homie Dashboard` account: real data rendered again (weather, status grid, solar pill), zero
  Mixed Content or WebSocket errors. The sibling `verify-homie-dashboard` skill's own hardcoded
  `http://` URLs (its `SKILL.md`, feature docs, `scripts/doctor.py`/`make-auth-state.py`) were
  updated too.
- What was investigated but **not** fixed: Music Assistant's own `base_url` setting, and the
  Sendspin WebSocket / artwork CORS gap. Both listed under "What's still open" above.

### A credential-handling note from this pass

While inspecting the live `dashboard-sound` Lovelace config to find the HOMEii Flow card's
`ma_url`, an early, less careful extraction printed the card's full JSON to a tool-output stream
that included `ma_token`, Music Assistant's own admin-role long-lived token (not `$HA_TOKEN`,
not a Homie credential). Told to pde immediately; that token should be rotated. Every extraction
after that point filtered the token out before printing, and the temporary local files that held
it (Lovelace config backups, the card JSON written to the scratchpad) were deleted once the fix
was confirmed live.
