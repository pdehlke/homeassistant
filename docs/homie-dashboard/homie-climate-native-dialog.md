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

## A side effect: `project-todo.md` item 1 resolved for free

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

## Same day: hiding Home Assistant's own chrome only while the dialog is open

Later the same day, pde compared the native dialog on two clients: the Fire HD tablet (and a
1280x800 responsive-mode browser logged in as the `Homie Dashboard` account, matching it) versus
a normal desktop browser logged in as `Pete`, HA's own admin account. On the tablet the dialog
looked exactly as wanted: a contained overlay, nothing recognizable as "having left Homie"
visible behind it. As Pete, the same tap opened the same real dialog, but Home Assistant's own
sidebar and top app bar were visible (dimmed, but legible) around and behind it, which read as
having exited Homie's dashboard into raw Home Assistant rather than staying inside an overlay.
pde: "I dislike the desktop browser behavior intensely."

### Why the two accounts looked different

Nothing about the morning's dialog-routing change caused this. The 2026-08-07 fix that first
added `kiosk_mode` to `homie-dash` (see [homie-dashboard-install-plan.md](./homie-dashboard-install-plan.md)'s checkpoint of that
date) deliberately scoped it to `users: ["Homie Dashboard"]` only, specifically so Pete's admin
session would keep its sidebar and top bar for dev and testing navigation. That scoping was
still in place, untouched. Home Assistant's real more-info dialog always renders as an overlay
across the entire parent app, sidebar and header included, for every account, everywhere in Home
Assistant; that is standard dialog behavior, not something this fork controls. On the tablet
there was no sidebar or header behind the dialog to reveal, because `kiosk_mode` had already
removed them outright for that one named account. As Pete, they were still there, so the same
dialog backdrop dimmed them instead of hiding them, and that visible, dimmed chrome is what read
as "exited the app."

### What was asked for, and what almost got built instead

pde confirmed the fix needed to work generally, for his own admin browsing and for any future
household member who might view Homie Dash from a desktop or laptop under their own (non-Homie)
account, not as a one-off carve-out for the `Pete` account specifically. The obvious way to get
there is dropping `kiosk_mode`'s `users` filter on `homie-dash` entirely, so nobody ever sees
Home Assistant's sidebar or top bar there. That was raised and pde rejected it outright: it would
mean losing that chrome permanently, on every visit to Homie Dash, dialog or not, which is
exactly the admin-navigation cost the 2026-08-07 scoping was written to avoid in the first place.

The actual fix reads `NemesisRE/kiosk-mode`'s own documentation rather than assuming its only
mode is a static per-user list. The plugin supports a live, reactive template condition (Jinja or
JS) as the value of `hide_header`/`hide_sidebar`, tracking whichever entities the template
references and re-evaluating over the same websocket connection whenever their state changes, no
dashboard reload required. That makes it possible to key chrome-hiding off something other than
which account is logged in: an entity's state, flipped only for the seconds a dialog is actually
on screen.

### Design

- **`input_boolean.homie_native_dialog_open`**, a new hidden helper created for this alone. It
  carries no meaning on its own; it exists only to give `kiosk_mode`'s template something to
  watch.
- **`homie-dash`'s saved `kiosk_mode` block** changed from the static `user_settings` list to a
  single combined Jinja condition, replacing that block rather than layering a new one next to
  it, so there is exactly one rule to reason about instead of two whose precedence would
  otherwise need to be verified against the plugin's own undocumented tie-breaking order:

  ```yaml
  kiosk_mode:
    hide_header: '{{ is_state("input_boolean.homie_native_dialog_open", "on") or user_name == "Homie Dashboard" }}'
    hide_sidebar: '{{ is_state("input_boolean.homie_native_dialog_open", "on") or user_name == "Homie Dashboard" }}'
  ```

  `user_name` is a variable `kiosk-mode` itself supplies to these templates (confirmed from its
  own README, which shows the identical pattern), so the `Homie Dashboard` account keeps exactly
  the always-hidden chrome it already had; the `or` clause is what makes the behavior general for
  every other account instead of naming `Pete` specifically.
- **`openThermostatNative(entityId)`**, already the single function every Climate entry point
  calls, now turns the helper on with `haService("input_boolean", "turn_on", ...)` before
  dispatching `hass-more-info`, and only after confirming the parent frame is actually reachable,
  so the helper never gets set with no dialog able to open and clear it again. It then registers
  a listener for Home Assistant's own `dialog-closed` event (fired by `ha-more-info-dialog` when
  it closes, bubbled and composed the same way `hass-more-info` is, confirmed by reading
  `home-assistant/frontend`'s dialog and `fireEvent` source directly rather than assumed) and
  turns the helper back off once that fires. The listener filters on
  `evt.detail.dialog === "ha-more-info-dialog"` specifically, because `dialog-closed` carries only
  the closing dialog's tag name, not which entity it was for: any more-info dialog closing
  fires the identical event. Without that filter, an admin opening entity settings from inside
  the open thermostat dialog and then closing just that nested dialog would prematurely restore
  chrome while the thermostat dialog was still open underneath it.
- The helper turns on **before** the dialog is asked to open, not after, so kiosk-mode's
  websocket-driven template has a head start reacting by the time the dialog actually appears
  rather than visibly hiding chrome a beat after it does.
- **No timeout or other safety net** if the helper ever gets stuck "on": if the real dialog
  somehow never opens after all despite a reachable parent frame, or gets torn down by something
  other than its own close handler (a tab closed mid-dialog, a crash), nothing turns the helper
  back off, and the sidebar and top bar stay hidden until the next dialog open/close cycle or a
  page reload. Deliberately not engineered around, on pde's explicit call: it matches the
  fail-silently-no-fallback approach `openThermostatNative`'s cross-frame dispatch already uses a
  few lines above it, for the same reason, there is nothing else this code could do instead that
  would not risk being wrong about what actually happened. If it ever does happen, the failure is
  a visibly missing sidebar, which is easy to notice and self-corrects the next time any dialog
  opens and closes normally; it does not affect the real thermostat underneath it either way.

### A known, accepted gap

The `evt.detail.dialog === "ha-more-info-dialog"` filter cannot tell *which* entity's more-info
dialog closed, because Home Assistant's `dialog-closed` event does not carry that information,
only the closing dialog's tag name. Every more-info dialog anywhere in Home Assistant uses that
same tag. In the ordinary Homie flow this never matters, since nothing else in Homie opens a
second native dialog while the first is still up. But an admin, having opened the thermostat
dialog from Homie, could independently open some unrelated entity's more-info dialog elsewhere in
the same Home Assistant session (a light from a Related-items link, say) and close that one first.
That would satisfy the filter and restore chrome while the thermostat dialog is technically still
open behind it. This is a real, understood limitation, not an oversight, and it is left as-is for
the same reason there is no stuck-open timeout: guarding against it would mean matching on the
specific entity a `dialog-closed` event does not report, which is not information this code has
access to.

### Verification

- `node --test test/screen-a.test.cjs`: 85/85 (2 new: `openThermostatNative` turns the helper on
  before dispatching and off when the real dialog reports itself closed, confirmed by call order
  as well as by content; and a different dialog's `dialog-closed` firing first, simulating a
  nested admin dialog, does not restore chrome while the thermostat dialog is still open).
  Existing thermostat-overlay tests were updated for `openThermostatNative` becoming `async`
  (it now awaits the turn-on call before dispatching), not for any behavior change in what they
  already covered.
- `input_boolean.homie_native_dialog_open` created live via the `input_boolean/create` websocket
  command, confirmed `off` immediately after creation.
- `homie-dash`'s `kiosk_mode` block edited live over the websocket API, with the prior config
  backed up to `/Users/pde/tmp/` first and the edit refusing to run if the live block did not
  exactly match the known 2026-08-07 shape.
- Release token bumped `20260812.6` -> `20260812.7`. `dist/homie-dashboard.html` deployed by
  temporary name and atomic rename, confirmed SHA-256-identical to the fork's local `dist/` after
  upload. `homie-dash`'s Lovelace iframe `?v=` bumped to match, prior dashboard config backed up
  first.
- Live-verified via Playwright, redacted throughout, as both accounts at a 1280x800 viewport:
  - As `Pete`: sidebar and top bar visible before opening the dialog; both hidden, with Homie's
    own dimmed content still visible around the dialog rather than Home Assistant's chrome, while
    the dialog was open; both restored immediately after closing it. `input_boolean.homie_native_
    dialog_open` read back as `off` again via `GET /api/states` after close.
  - As `Homie Dashboard`: unchanged from before this change in every case checked, chrome hidden
    at all times regardless of the helper's state, confirming the `or user_name == "Homie
    Dashboard"` clause preserved the tablet's existing always-hidden behavior.

### The remaining background difference was never kiosk_mode: it was theme

pde reviewed the chrome fix above and flagged one more difference: on the `Homie Dashboard`
account the page behind the dialog is heavily blurred as well as dimmed; on `Pete` it was only
dimmed, background text still sharp and legible. The chrome (sidebar and top bar) was already
confirmed fixed at this point, correctly absent from both. This was a separate, unrelated
difference that happened to surface at the same time.

Traced live, not guessed: the real `<dialog>` element's `::backdrop` pseudo-element, which is what
actually paints the dimmed/blurred layer behind a native HTML dialog, computed to
`backdrop-filter: blur(10px)` and `background-color: rgba(0,0,0,0.6)` on `Homie Dashboard`, and to
`backdrop-filter: none` and a fully transparent `rgba(0,0,0,0)` background on `Pete`. Home
Assistant's dialog styling reads both of those from theme-level CSS custom properties
(`--ha-dialog-scrim-backdrop-filter` and `--mdc-dialog-scrim-color`), and `frontend/get_user_data`
confirmed the two accounts are simply on different HA frontend themes: `Pete` was on `visionos`,
`Homie Dashboard` is on `noctis`. Diffing the two theme definitions (`frontend/get_themes`) found
the actual cause: `noctis` sets `--ha-dialog-scrim-backdrop-filter: blur(10px)` and
`--mdc-dialog-scrim-color: rgba(0,0,0,0.6)`; `visionos` sets the same scrim-blur variable to `none`
and never sets a scrim color at all, even though `visionos` already blurs cards at `blur(20px)` via
its own `--ha-card-backdrop-filter` elsewhere in the same theme, so the dialog scrim reads like an
unfinished variable in that theme rather than an intentional choice. Nothing about this is
Homie-specific: any account on `visionos` would see the same flat, unblurred dialog backdrop
anywhere in Home Assistant, not just from Homie's Climate chip. That included the `Tablet` kiosk
account, which was also on `visionos` and opened native more-info dialogs of its own from the
now-retired Home dashboard's native Lennox thermostat cards (see
[native-dashboards-retired.md](../native-dashboards/native-dashboards-retired.md)), not just from
Homie Dash.

Given the choice between fixing `visionos`'s theme definition (fixes every dialog on that theme
everywhere), scoping a CSS override to just Homie's own dialog-open flow (fixes only what Homie
triggers, leaves `visionos` itself untouched elsewhere), or reassigning an account to a different
theme entirely, pde resolved it directly: switched `Pete`'s personal account theme from `visionos`
to `noctis` and confirmed live that this fixed the dialog backdrop. That is a personal account
preference change, not a fix applied to this fork, `homie-dash`, or the `visionos` theme itself.

## Still open

The `Tablet` kiosk account is still on `visionos` and still has the same flat, unblurred dialog
backdrop on any native more-info dialog it opens, including from Home's own Lennox thermostat
cards, unrelated to anything Homie Dash does. Not fixed here since `Pete`'s theme switch was scoped
to `Pete`'s own account only; flagged for a future pass if the same contained look is wanted there
too, either by fixing `visionos`'s `--ha-dialog-scrim-backdrop-filter`/`--mdc-dialog-scrim-color`
directly (would fix it for every `visionos` account at once) or switching `Tablet` to a different
theme the way `Pete` was.

The known, accepted `dialog-closed` filtering gap described above (a different, unrelated native
dialog closing first can prematurely restore chrome while the thermostat dialog is still open
underneath it). Not tracked as a bug to fix; it was weighed and explicitly accepted rather than
engineered around. Nothing else from either change in this document touches any other item
tracked in [homie-dashboard-install-plan.md](./homie-dashboard-install-plan.md)'s open-work list.
