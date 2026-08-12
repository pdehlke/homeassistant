# Climate overlay: routed to Home Assistant's real native dialog

Why Homie's Climate overlay kept silently breaking its own +/- controls, and why the fix was
to stop reimplementing Home Assistant's climate more-info dialog and instead open the real
one, from inside Homie's own iframe.

## Symptom

On the morning of 2026-08-12, the Climate overlay's +/- buttons did nothing. No error, no
visual feedback, no change to the real thermostat. The Climate dashboard's native `thermostat`
cards, reached through Home Assistant directly, worked correctly: tapping +/- there moved the
real setpoint, and dragging the cool-to side of the dial worked too.

This was not a new kind of bug. It was the second time the same control had broken silently:

- [homie-thermostat-control-fix.md](homie-thermostat-control-fix.md) (2026-08-07): the +/-
  buttons displayed a plausible, moving number that never reached the physical Lennox units,
  because of two silent Home Assistant API gotchas (paired `target_temp_high`/`target_temp_low`
  keys, and step sizes that must land on the entity's declared `target_temp_step`).
- The 2026-08-11 "native-parity rebuild" (`b38a3c8`, see
  [homie-dashboard-install-plan.md](homie-dashboard-install-plan.md)'s checkpoint of that date)
  touched the same code again, adding humidity/preset/fan controls and fixing two more live
  bugs, and was itself live-verified with a real setpoint change at the time. Something in that
  work, or something after it, broke +/- again by the following morning.

pde: "I have kind of had it with screwing around with this set of controls." The request was
specific: make Homie's Climate chip show the exact overlay reachable from a scratch "test"
dashboard's single native `thermostat` card, opened via its three-dot menu -- the real Home
Assistant more-info dialog, not a lookalike.

## Why the hand-rolled overlay kept breaking

The overlay was a from-scratch reimplementation of Home Assistant's own climate more-info
dialog: a hand-drawn SVG dial, hand-written +/- buttons with their own debounce and payload
logic, hand-built mode/preset/fan-mode button rows. Getting the *content* to match HA's dialog
was achievable and was in fact done well (see the 2026-08-11 checkpoint). Getting the
*behavior* to match required independently re-deriving every quirk of Home Assistant's own
`climate.set_temperature` service schema and the `lennoxs30` integration's specific silent
failure modes, and keeping that derivation correct across every future change to the overlay.
Two rounds of silent breakage in five days is what that actually costs in practice: the failure
mode (HTTP 200, no state change, no logbook entry) gives no signal to notice regression by, so
nothing short of a live tap against the real entity, done deliberately at every change, would
have caught the second break before pde did.

## What changed

Homie's dashboard already runs inside a Lovelace `strategy: iframe` dashboard (`homie-dash`),
and has been same-origin with the parent Home Assistant frontend since the 2026-08-11
`hass.ehlke.net` migration (see
[hostname-migration-to-ehlke-net.md](../networking/hostname-migration-to-ehlke-net.md)). Home
Assistant's own frontend opens its more-info dialog by dispatching a `hass-more-info`
`CustomEvent` (`{ entityId }`, `bubbles: true`, `composed: true`) on any DOM node in the page --
confirmed by reading `home-assistant/frontend`'s own `handle-action.ts` via Context7, not
assumed. Because Homie's iframe is same-origin with its parent, a script running inside it can
reach `window.parent.document` and dispatch that exact event on the parent's `<home-assistant>`
element, opening Home Assistant's real dialog instead of a rendering of one.

This was checked live, with a throwaway Playwright script, *before* any implementation code was
written, specifically to avoid building against an assumption that iframe sandboxing might
block. It worked on the first try: dispatching the event produced the real dialog, rendered
over Homie's own dashboard, with the real dial, real current-temperature marker, and real
blue/orange cool-to/heat-to arcs pde described from the scratch "test" dashboard.

In the fork (`dist/homie-dashboard.html`, `dist/homie-custom.js`):

- **New `openThermostatNative(entityId)`** dispatches `hass-more-info` on the parent frame.
  Wrapped in try/catch with no fallback: if a future Home Assistant change makes the parent
  frame unreachable, the function fails silently rather than throwing inside a click handler,
  since there is nothing else it could do instead.
- **`openThermostat(entityId)`** (the single function every Climate entry point already called)
  now branches on how many climate entities the call resolves to. A filtered call -- Overview
  C's floors-card faces, which already resolve to exactly one entity each (Main House -> South
  zone, Office Wing -> North zone) -- goes straight to `openThermostatNative`, one tap, no
  Homie-drawn overlay at all. An unfiltered call -- Overview A/B's Climate chip, which has
  always shown both thermostats -- still shows the existing Main House/Office Wing picker
  first, unchanged, since the real dialog is single-entity and has no room switcher of its own.
  Picking a room now calls `openThermostatNative` instead of rendering a dial.
- **Deleted**, not just unused: the hand-rolled dial SVG and its arc math, the +/- buttons and
  their debounce/payload logic (`thermAdjust`, `_thermAdjustHumidity`), the mode/preset/fan-mode
  button rows and their builders (`_buildThermModes`, `_buildThermFeatures`), the
  temperature/humidity dial toggle, the action-badge/ambient-tint logic, and the
  `homie-custom.js` helpers that only existed to support them (`thermostatStepSize`,
  `thermostatSetTemperaturePayload`, `thermostatSupportsFeature`, `thermostatHumidityView`,
  `thermostatClampHumidity`, `thermostatHvacModeOptions`, `thermostatPresetOptions`,
  `thermostatFanModeOptions`). Around 940 lines of markup/CSS/JS gone. `#thermostat-overlay` now
  holds only the room picker.
- **Kept untouched**: `thermostatTemperatureView` and `floorTargetText`, which drive the floor
  card's own passive "Target" stat tile. That is a display, not a control, was never part of
  either round of breakage, and the floors card still needs it regardless of how the overlay
  itself opens.

Release token bumped `20260811.7` -> `20260812.1` in `dist/homie-dashboard.html`, and the
`homie-dash` Lovelace iframe `?v=` updated to match via `apply-card.py` (backup of the prior
Lovelace config saved automatically to `/Users/pde/tmp/`).

## A side effect: project-todo.md item 1 resolved for free

Item 1 on `project-todo.md` was a temperature/humidity history graph for the Climate overlay,
matching the history-graph icon on Home Assistant's native climate more-info dialog. A
feasibility pass ([climate-history-graph-feasibility.md](climate-history-graph-feasibility.md))
had already found that no charting library was needed and scoped the remaining work down to
combining two existing hand-rolled SVG charts plus new dual-axis rendering.

That entire item is moot now. Homie's Climate chip opens Home Assistant's actual more-info
dialog, which already has a History section with a real, recorder-backed graph built in.
Confirmed live: tapping the History icon on the real dialog for `climate.casasolar_south_zone_1`
rendered a real temperature/target history chart, no Homie code involved. Removed from
`project-todo.md`.

## Options considered and rejected

- **Nested iframe to a dedicated single-entity native dashboard**, cloning the scratch "test"
  dashboard's structure per zone. Considered as the fallback if the direct cross-frame event
  dispatch turned out to be blocked. Rejected once the spike confirmed direct dispatch works:
  it would mean maintaining two extra native Lovelace dashboards and confines the dialog to a
  nested iframe's box, for no benefit once the simpler approach was proven to work.
- **Keep hand-rolling the overlay**, fix the immediate +/- regression and continue pushing
  toward pixel/behavior parity with the native dialog. Rejected: this is the same maintenance
  pattern that already produced two rounds of silent breakage in five days, and every bit of
  parity work it would take is naturally free once Homie opens the actual dialog instead.
- **Default to whichever thermostat was last viewed**, skipping the picker on Overview A/B's
  unfiltered Climate chip entirely. Rejected in favor of keeping the existing two-button
  picker: zero extra taps sounds better until switching to the *other* thermostat requires
  first visiting it through the floors card, which is a worse trade than one extra tap on an
  entry point that only shows up when the caller hasn't already committed to a room.

## Verification

- `node --test test/screen-a.test.cjs`: 68/68, including new coverage for
  `openThermostatNative`'s event shape, the filtered-vs-picker routing split, picking a room
  from the picker, and the no-parent-frame fallback failing silently rather than throwing.
- A throwaway Playwright spike against the deployed page, run before any implementation code
  existed, confirmed the cross-frame `hass-more-info` dispatch actually opens Home Assistant's
  real dialog.
- Deployed release `20260812.1` (checksum-verified upload by temp name, atomic rename; prior
  files backed up first). Live-verified via Playwright, authenticated as the Homie Dashboard
  account:
  - Overview C's Main House floor face: one tap opens the real dialog for
    `climate.casasolar_south_zone_1` directly, no picker.
  - Overview C's Office Wing floor face: one tap opens the real dialog for
    `climate.casasolar_north_zone_1` directly, no picker.
  - Overview A/B's Climate chip: tap shows the Main House/Office Wing picker; tapping Office
    Wing opens the real dialog for `climate.casasolar_north_zone_1`.
  - A real tap on the native dialog's + button moved `climate.casasolar_north_zone_1`'s actual
    `target_temp_low` from 59 to 60 (`last_updated` advanced to match), confirmed via
    `GET /api/states`, then restored to 59/73 via
    `POST /api/services/climate/set_temperature`.
  - The native dialog's History icon rendered a real temperature/target chart for
    `climate.casasolar_south_zone_1`, confirming the project-todo item 1 side effect above.

## Still open

None from this change. It is self-contained and does not touch any other item tracked in
`homie-dashboard-install-plan.md`'s open-work list.
