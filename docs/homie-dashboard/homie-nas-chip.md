# NAS chip: admin-only Synology health/capacity overlay

A "NAS" chip on Homie Dashboard's bottom control row, visible only to admin viewers, that
reproduces the essential content of the native `dashboard-nas` Overview
([synology-nas-dashboard.md](../synology-nas/synology-nas-dashboard.md)) inside an overlay: a
health hero, capacity and drive-temperature tiles, a health-checks list, system context, and a
conditional Open DSM link.

## Goal

pde wanted to check Synology NAS health from the surface he actually uses day to day, rather than
switching to the separate native dashboard. The chip needed to stay invisible on the shared kiosk
tablet, since NAS health isn't relevant to other household members and the `Homie Dashboard`
account's surface shouldn't grow a control nobody there needs.

Design was reached through an extensive grilling session before any code was written, grounded in
live facts pulled directly from Home Assistant rather than assumed: the exact enabled Synology
entity list, and the live `dashboard-nas` Overview configuration itself (every card, icon, literal
state string, and UIX color formula), fetched via WebSocket rather than re-derived. The overlay's
content and entity list are therefore a direct port of an already-approved, already-deployed
configuration, not a fresh design.

## Design

**Chip config.** `CONFIG.controls` gains a dedicated entry (`isNasChip: true`, `action: "nas"`,
`entity: "sensor.nas_health"`) using the same `action`-dispatch pattern as the TV chip
(`controlOnClick` routes it to `openNasOverlay()`), not the generic subEntities/subGroups popup,
since NAS data isn't a domain-typed on/off entity list.

**Admin-only visibility.** `isAdminViewer()` reads the real logged-in HA user's admin flag off the
parent frame — `window.parent.document.querySelector("home-assistant").hass.user.is_admin`, the
same same-origin cross-frame access already established for the Climate overlay's native dialog
(`openThermostatNative`, since the 2026-08-11 hostname migration made Homie's iframe same-origin
with the parent HA frontend). Fails closed (hidden) on any missing property or cross-frame error.
The chip is never removed from `CONFIG.controls`/`activeControls` — every other chip's numeric
index (`chip-${i}`, used pervasively for tap dispatch) would shift depending on who's viewing if it
were. Instead a `chip-hidden` class is toggled on the rendered element, checked at initial render in
all three chip surfaces (Overview A/B/C) so it never flashes visible for a moment before the first
refresh, and re-checked every refresh cycle after that so a parent frame that hadn't finished
hydrating its own `hass` object yet at first paint self-corrects moments later.

**Chip glow.** Reuses the existing `.chip.on` mechanic every toggle-style chip already has,
triggered when `sensor.nas_health` is `Attention` or `Critical` (`nasChipNeedsAttention()`) — not
`Unknown`, and not the generic `entityIsOn()` fallback, since "needs attention" isn't the same
concept as "this entity's state is on." Unlike every other chip, the glow color is not derived from
the active theme's accent variables: `.chip.chip-nas.on` uses a fixed literal color instead, so the
signal can't render as reassuring green under an unlucky theme choice (Emerald, say) during a real
Critical state. Reuses `#FF5252`, the same red already established for disabled irrigation zones,
rather than inventing a new color. The same override exists for the Overview B sidebar list
(`.ov2-ctrl-btn.chip-nas.on`) and the Overview C sidebar icon (`.ov3-sb-btn.chip-nas.on`).

**Overlay.** A dedicated `#nas-overlay` popup, `openNasOverlay()`/`closeNasOverlay()`, registered in
the global Escape-key overlay list, following the TV chip's dedicated-overlay precedent rather than
the generic accordion. `refreshNasOverlay()` populates every dynamic value from the shared
WebSocket-fed state cache (`haGetCached()`) — no new fetch mechanism, no new polling. Content, in
order, direct-ported from the live `dashboard-nas` Overview:

1. A four-state health hero (`nasHeroTintClass()`: Healthy/Attention/Critical/Unknown, each its own
   color, mirroring the native hero exactly), inert.
2. Volume-used and max-drive-temperature tiles, tappable for HA's native more-info dialog.
3. A health-checks list: volume status, used space, total size, Security Advisor, then each drive's
   status, SMART, bad-sector, and remaining-life fields under a "Drive 1"/"Drive 2" section divider.
   Every row tappable for more-info except the two section dividers themselves.
4. System-context tiles: CPU, memory, DSM update availability (inert), uptime, fan mode (inert),
   internal temperature.
5. An "Open DSM" button (`window.open(url, "_blank")`, the first external-navigation code anywhere
   in Homie) visible for `Attention`, `Critical`, and `Unknown` (`nasDsmLinkVisible()`) — three
   states, wider than the chip glow's two-state condition.

Tappable rows dispatch the real `hass-more-info` event via `nasOpenMoreInfo()`, the same cross-frame
technique as `isAdminViewer()`/`openThermostatNative`. The hero, DSM-update tile, and fan-mode tile
carry no `onclick` at all, matching the native dashboard's read-only boundary.

**Entity list**, ported verbatim from the live `dashboard-nas` Overview:

| Field | Entity |
|---|---|
| Health state | `sensor.nas_health` |
| Volume used | `sensor.nas01_volume_1_volume_used` |
| Max drive temp | `sensor.nas01_volume_1_maximum_disk_temp` |
| Volume status | `sensor.nas01_volume_1_status` |
| Used space | `sensor.nas01_volume_1_used_space` |
| Total size | `sensor.nas01_volume_1_total_size` |
| Security Advisor | `binary_sensor.nas01_security_status` |
| Drive 1/2 status | `sensor.nas01_drive_{1,2}_status` |
| Drive 1/2 SMART | `sensor.nas01_drive_{1,2}_status_smart` |
| Drive 1/2 bad-sector limit | `binary_sensor.nas01_drive_{1,2}_exceeded_max_bad_sectors` |
| Drive 1/2 remaining life | `binary_sensor.nas01_drive_{1,2}_below_min_remaining_life` |
| CPU | `sensor.nas01_cpu_utilization_total` |
| Memory | `sensor.nas01_memory_usage_real` |
| DSM update | `update.nas01_dsm_update` |
| Uptime | `sensor.nas01_uptime` |
| Fan mode | `select.nas01_fan_speed_mode` |
| NAS temperature | `sensor.nas01_temperature` |

DSM URL is `https://192.168.4.106:5001`, confirmed live from the Synology device's own
`configuration_url` rather than reused blindly from the native doc. Trend/history entities
(throughput, average disk temp) are deliberately excluded — see Deferred, below.

## Options considered and rejected

Resolved by grilling before any code was written:

- **Overlay scope.** Chosen: all five Overview pieces (hero, capacity/temp tiles, health checks,
  system context, DSM link). Trends charts deferred — no charting library exists anywhere in Homie
  yet, and the native Trends view hasn't had its own 7-day usefulness review to justify porting it
  into a second surface.

- **Read-only boundary.** Chosen: identical to the native dashboard, no exceptions. No reason for
  the Homie surface to be more permissive than the admin-only native dashboard it's derived from.

- **Visibility mechanism.** Chosen: live cross-frame identity check
  (`isAdminViewer()`). Considered and rejected: a per-browser Settings toggle (ships with zero
  unverified capability, but is a device preference, not an identity check — anyone using that
  browser could enable it regardless of their own admin status). The native `kiosk_mode` config
  already distinguishes the `Homie Dashboard` and `Pete` accounts at this exact dashboard
  (`hide_header`/`hide_sidebar` scoped per user), which was independent live proof this instance
  reliably exposes distinguishable per-user identity to the parent frame — de-risking the
  cross-frame approach before it was chosen. Kiosk_mode itself can't be extended into the chip: it
  only manipulates the outer HA Lovelace chrome (the header/sidebar around the iframe), with no
  channel into the iframe's own content.

- **Collapsed-chip signal.** Chosen: reuse the existing `.chip.on` glow (Attention/Critical only),
  not a new corner-dot badge. Considered and rejected: a three-color badge dot mirroring the native
  hero's four states — more precedent-consistent with Climate/Irrigation's existing alert-dot
  language, but this chip's own glow only needed a boolean signal, not four discrete states, once
  the overlay's own hero was agreed to carry the full four-state detail instead.

- **Glow color.** Chosen: fixed literal color (`#FF5252`), not the active theme's accent variables,
  despite every other chip using accent-derived color for its `.on` state. Reasoning above. pde has
  explicitly reserved the right to revisit this back toward theme-accent consistency in a later
  iteration.

- **Unknown state in the chip glow.** Chosen: glow fires for Attention/Critical only, Unknown does
  not light it — but the overlay's own DSM link keeps the native dashboard's three-state condition
  (Attention/Critical/Unknown) even though the chip's glow only covers two of those three. An
  entity going unavailable (Unknown) is arguably exactly when a fast path to DSM matters most, more
  than a merely-elevated-but-known Attention state — worth surfacing in the overlay even though it
  doesn't justify lighting the collapsed chip.

- **Overlay hero tinting.** Chosen: genuine four-state tinting (Healthy/Attention/Critical/Unknown,
  each its own color), mirroring the native hero exactly, rather than collapsing to the chip's own
  boolean treatment. The chip's simplification was specifically about its theme-accent color trap,
  not a statement that four-state signaling itself is unwanted — the overlay has the room to be as
  precise as the native dashboard.

- **Notification automation.** Considered: a new HA automation forwarding `sensor.nas_health`
  Attention/Critical into the existing `persistent_notification`/Alert-Indicator feed, the same
  pattern Lennox thermostat alerts already use — the plumbing already exists and would need zero new
  Homie code. Deferred to a later iteration, matching the native dashboard's own "reusable attention
  state now, notifications later" decision.

## Verification

`node --test test/screen-a.test.cjs`: 106/106 (16 new — every pure helper function
(`isAdminViewer`, `nasHealthState`, `nasChipNeedsAttention`, `nasHeroTintClass`,
`nasDsmLinkVisible`, the five formatters, `nasOpenMoreInfo`) tested in isolation against a fake
state cache and a fake parent frame, the same slice-real-source approach as the existing
Climate/Music/Scenes tests; the admin-visibility wiring across all three render paths and both
refresh paths; the `_sbIcon` action-based override; `controlOnClick`'s `"nas"` dispatch; the
Escape-key registration; the DSM link's exact URL and three-state condition; the hero/DSM-update/
fan-mode inertness; and the fixed-color CSS assertion).

Deployed to `/config/www/community/homie-dashboard/` via SFTP: prior copies backed up first, real
`HA_TOKEN` spliced into the placeholder-bearing `config.js` entirely on the HA host (BusyBox `sed`,
no `-P`), never captured or printed locally. `homie-dashboard.html` and `homie-custom.js` confirmed
SHA-256-identical to the fork's local `dist/` after upload. `homie-dash`'s Lovelace iframe `?v=`
bumped via direct WebSocket `lovelace/config/save`, prior config read back and diffed first.

Live-verified via Playwright, both directions, against the real live instance rather than mocked
state:

- As `Pete` (admin, real session): `isAdminViewer()` → `true` inside the live iframe; the rendered
  chip's class list was `"chip chip-nas"` (no `chip-hidden`) — visible, as designed.
- As `Homie Dashboard` (its own dev-only long-lived token, not a simulated non-admin): `hass.user.name`
  read back as `"Homie Dashboard"`, `isAdminViewer()` → `false`; the rendered chip's class list was
  `"chip chip-nas chip-hidden"` — hidden, as designed. This is the exact mechanism the kiosk tablet
  will see, exercised on the real account rather than assumed from the unit tests alone.
- Opened the real overlay via `openNasOverlay()` against live data: `sensor.nas_health` read
  `Healthy`, volume used 30.3%, max drive temp 99°F (98.6°F rounded), both drives Normal/OK across
  every field, CPU 3%, memory 26%, DSM update Available, uptime "Up 34d" (booted 2026-07-14), fan
  mode quiet, NAS temp 106°F — all matching a direct REST/WebSocket read of the same entities taken
  during design research. DSM link correctly hidden while Healthy. The Critical hero tint's color
  was also previewed directly (bypassing a full state simulation, since the live entity's actual
  state was Healthy at verification time) and rendered as designed.

**Bug found and fixed live**, before pde's review: the overlay initially had no `max-height`/
`overflow-y`. Every NAS row renders expanded at once, unlike the accordion-style Lights/Irrigation
popups, so with real content loaded the popup ran taller than the viewport — inside a vertically
centered flex overlay, that meant the title and hero rendered off the top edge of the browser
entirely, unreachable, while the DSM button rendered off the bottom. Fixed with `max-height: 85vh;
overflow-y: auto` on `.popup--nas`, the same pattern `.popup--media-browser` already uses elsewhere
in the fork. Verified by scrolling the live popup element (`scrollHeight` 1064px vs `clientHeight`
610px) and reading back both the top and bottom of its content via screenshot. A regression test
now asserts both properties are present. Redeployed as release `20260817.2`; the first upload
(`20260817.1`) never reached pde's review.

pde reviewed the live result on his own admin session and approved. Committed to the fork,
`52830fb` on `main`.

## Deferred

- Trends-style history charts. No charting library exists in Homie yet; tracked as a natural
  follow-up once the native dashboard's own Trends view has its planned usefulness review.
- The `persistent_notification` forwarding automation described above.
- Revisiting the chip glow's fixed-color-vs-theme-accent choice, at pde's discretion.
