# Alarmo configuration

How [`nielsfaber/alarmo`](https://github.com/nielsfaber/alarmo) is set up on this instance, and
the reasoning behind the choices that aren't obvious from the live config alone. Written
2026-09-08 as part of [issue #24](https://github.com/pdehlke/homeassistant/issues/24), which is
the spec of record for why Alarmo exists here at all and how it wires into Homie Dashboard; this
document covers the Home Assistant side only.

Alarmo is a virtual, HA-native alarm engine. It has no connection to the house's real
Crestron/DSC/Apex hardware and none is planned as part of this work; see
[crestron-alarm-open-questions.md](../crestron/crestron-alarm-open-questions.md) for that separate,
unresolved puzzle.

## Install

Downloaded via HACS (pde, 2026-09-08, v1.10.19). The Home Assistant integration entry itself
(Settings → Devices & Services → Add Integration → Alarmo) was added the same day with an empty
config flow — Alarmo has no setup-time options, everything is configured after the fact through its
own config endpoints. `alarm_control_panel.alarmo` and `update.alarmo_update` exist as soon as the
entry is created.

## Area and arm modes

Alarmo ships one area by default. This instance uses just that one (`area_id` `1788876496`,
name "Alarmo") rather than splitting into multiple areas — the house has one real DSC keypad and
one real alarm state, so one Alarmo area matches that.

Arm modes, matching the PRD's explicit want of "home/away/night/disarm":

| Mode | Enabled | Exit delay | Entry delay | Trigger time |
|---|---|---|---|---|
| Away | yes | 60s | 60s | 1800s (30 min) |
| Home | yes | none | none | 1800s |
| Night | **no** | — | — | — |
| Custom bypass | no | — | — | — |
| Vacation | no | — | — | — |

Night was enabled once (mirroring Home's no-delay settings) and then explicitly turned back off at
pde's request the same session, before any zone or dashboard work depended on it being present. It
stays defined in Alarmo's config (`enabled: false`) rather than removed, so re-enabling later is a
one-field flip rather than re-deriving the settings. The dashboard's popup and Overview C card both
already render an "ARM HOME" / "ARM AWAY" / "DISARM" button set — Alarmo not offering `armed_night`
as a ready-to-arm mode just means a fourth button never appears; no dashboard code depends on which
modes are enabled.

**Gotcha, worth knowing before touching this again:** `POST /api/alarmo/area` replaces the entire
`modes` dict with whatever `modes` object is in the request body — it does not merge per-mode. A
request that names only `armed_night` silently drops `armed_away` and `armed_home` from the area
entirely, not just leaves them unmentioned. Any future edit to one arm mode's settings must include
every mode meant to survive the call, not just the one changing. Confirmed the hard way this
session: enabling night dropped away/home, caught immediately via `alarmo/areas` and fixed in the
same session by resending all three together.

## Global config

Left at Alarmo's defaults except where the PRD asked for something specific: `code_format: number`
(matches the DSC keypad's own numeric-only convention), everything else (`code_arm_required`,
`code_disarm_required`, `code_mode_change_required`, `disarm_after_trigger`,
`ignore_blocking_sensors_after_trigger`) still `false`.

**Not done, needs pde's input:** the PRD's user story 4 wants a PIN required before disarm, so a
child or guest tapping the tablet can't casually disarm the house. That needs an actual PIN value,
which isn't something to invent — set `code_disarm_required: true` via `POST /api/alarmo/config`
and create at least one Alarmo user with a real `code` via `POST /api/alarmo/users` once pde
supplies one. Until then, `ALARM_CODE` in Homie Dashboard's `config.js` stays empty (correct, since
Alarmo doesn't require a code yet — setting a code client-side that the server doesn't ask for would
do nothing).

## Zones

The 24 zones inventoried in
[crestron-alarm-zone-inventory.md](../crestron/crestron-alarm-zone-inventory.md) already exist in
Home Assistant as `binary_sensor.alarm_zone_*` template entities, all reading `unknown` — no live
Crestron/DSC connection feeds them yet (separate, blocked work; see that document's "What is not
done"). 22 of the 24 are registered as Alarmo sensors; the two excluded
(`binary_sensor.alarm_zone_dining_room_doors`, `binary_sensor.alarm_zone_room_4_east_windows`) are
the ones with a known Crestron join collision, per that same document — not re-litigated here.

Each registered sensor gets a `type` (Alarmo's own vocabulary: `door`, `window`, `motion`,
`tamper`, `environmental`, `other`) and, except for the one `environmental` sensor, a `modes` list
saying which arm states it's monitored in. Mapping, and the reasoning behind it:

| Zone shape | Alarmo `type` | Modes | Why |
|---|---|---|---|
| Pure door zones, garage overhead doors, and combined "Dr / Wins" zones | `door` | away, home, night | Perimeter entry points; monitored in every armed state, same as every consumer alarm's default "perimeter" behavior. Combined door+window zones (one physical wire loop, can't be split by this project) get the door treatment since the door is the more likely-to-be-forced-open component. |
| Pure window zones | `window` | away, home, night | Same perimeter reasoning as doors. |
| Motion sensors, including the pool photobeam | `motion` | away only | Standard alarm-system convention: interior motion is excluded from Home/Night because someone is expected to be moving around; Away is the only mode with nobody home to trigger a false alarm. |
| Garage Heat | `environmental` | n/a (`always_on: true`) | Not an intrusion sensor — a hazard sensor, conventionally monitored regardless of arm state rather than gated by one. |

This is a **first-pass, provisional** assignment, not a verified-against-the-real-panel one. It
can't be verified yet: all 22 zones read `unknown`, so there's no live open/closed signal to test
delay or bypass behavior against. In particular, `use_entry_delay`/`use_exit_delay`/`allow_open`/
`auto_bypass` were deliberately left at Alarmo's own per-sensor defaults (omitted from every `POST
/api/alarmo/sensors` call) rather than guessed at — which door is "the" entry/exit path is a
house-specific fact this session had no way to confirm, and fabricating it risked being
confidently wrong in a way nothing would catch. Revisit once the DSC-vs-Apex puzzle gives the zones
real state, at which point live behavior (or pde's own knowledge of the house) can settle it
properly.

## Verified live, 2026-09-08

Full arm/disarm cycle via the deployed Homie Dashboard's security popup, Playwright-driven against
the real instance (not a mock): disarmed → tapped Arm Home → `alarm_control_panel.alarmo` read
`armed_home` (confirmed both in the popup's badge and independently via `ha_get_state`) → tapped
Disarm → back to `disarmed`. `sensor.homie_alarm_status` (see
[homie-dashboard-install-plan.md](../homie-dashboard/homie-dashboard-install-plan.md) for that
sensor's own record) tracked the state live throughout with no manual refresh needed.
