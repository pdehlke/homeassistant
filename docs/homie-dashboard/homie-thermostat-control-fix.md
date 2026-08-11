# Homie thermostat control: post-mortem

Why the Homie dashboard's thermostat launcher and overlay looked right but did not actually
control the real thermostats, and what it took to find out. See
[homie-dashboard-install-plan.md](homie-dashboard-install-plan.md) for the fork location and
deployment workflow this fix went through, and
[lennoxs30-integration.md](../lennox-climate/lennoxs30-integration.md#known-quirk-climatesettemperature-requires-both-bounds-and-silently-drops-off-step-calls)
for the reusable integration-level facts this investigation turned up.

## Symptom

On Overview C, the bottom-right Main House launcher card showed the AC's mode as "Unavailable".
Opening the thermostat overlay (from that card, or from Overview A's unfiltered Climate chip)
showed a target temperature of "—" until the first tap on plus or minus, at which point a number
appeared and moved in half-degree steps on screen. The number never reflected on the physical
Lennox thermostat. ChatGPT/Codex had already spent time on this without resolving it.

## Starting point

A prior Claude session's uncommitted work-in-progress was already sitting in the fork's working
tree: unit-aware Fahrenheit/Celsius conversion, a first attempt at handling dual-setpoint
`heat_cool` entities, and a corrected dial range. It was never deployed; the live dashboard (release
`20260807.11`) matched the pre-fix commit `35bf0f9`/`b0d56d1` byte for byte. That WIP was kept as
the starting point rather than discarded, since it already had the right shape and passing tests
for the parts it covered.

## Why the symptom happened

Both real thermostats (`climate.casasolar_south_zone_1`, `climate.casasolar_north_zone_1`, see
lennoxs30-integration.md) run in `heat_cool` mode essentially all the time, reporting
`target_temp_high`/`target_temp_low` rather than a single `temperature` attribute. The dashboard
code, both upstream's generic climate popup and the dedicated overlay built to replace it, assumed
a single Celsius-style setpoint. The overlay's fallback path, when no single setpoint attribute
existed, seeded the pending value from a hardcoded `22` and adjusted it in fixed 0.5° steps,
explaining both the "—" before the first tap and the Celsius-looking numbers afterward.

Fixing the display was not enough, because two further defects sat underneath it, both silent and
both only found by testing directly against the real entities rather than trusting the service
call's own response:

- **Home Assistant's `climate.set_temperature` schema requires `target_temp_high` and
  `target_temp_low` together.** A call supplying only one is rejected with a bare `400` before it
  reaches the entity at all.
- **Both zones declare `target_temp_step: 1.0`.** A call whose delta does not land on a whole
  degree returns HTTP `200` with an empty body, indistinguishable from success, and is silently
  dropped: no state change, no `logbook` entry, nothing. The dial's plus/minus buttons were
  hardcoded to a 0.5° delta.

Neither of these produces a client-visible error under normal use, which is consistent with why an
earlier attempt at this fix did not resolve it: the failure mode gives no signal to chase.

## What changed

In `dist/homie-custom.js`:

- `thermostatTemperatureView` now derives the displayed target from `hvac_action` when the entity
  is in `heat_cool`/`auto` mode: the bound the equipment is actively working toward (`cooling` ->
  `target_temp_high`, `heating` -> `target_temp_low`), falling back to the band midpoint only when
  there is no single active bound (idle, fan, or unreported).
- `thermostatSetTemperaturePayload` always sends both `target_temp_high` and `target_temp_low`
  when adjusting a dual-setpoint entity. Only the active bound's value actually changes; the other
  is passed through unchanged, satisfying Home Assistant's pairing requirement without silently
  moving a setpoint the user cannot see.
- A new `thermostatStepSize` reads the entity's own `target_temp_step` (falling back to 0.5° only
  when an entity does not declare one) and `thermAdjust` sends `direction * that step` instead of a
  hardcoded 0.5°.

Release token bumped `20260807.11` -> `.13` (see "Two mistakes" below for why it went through
`.12` first) and the Lovelace `homie-dash` iframe URL updated to match.

## Options considered and rejected

- **Adjust only the active bound, send only that one key.** This was the first fix attempted and
  is what actually caused the `400`s during verification. Home Assistant's schema does not allow a
  lone bound. Rejected in favor of always sending both keys, changing only one value.
- **Keep the hardcoded 0.5° step.** Simpler, and matches the visual half-degree tick marks on the
  dial. Rejected once live testing showed the real entities silently ignore anything that is not a
  whole degree; a UI convention is not evidence of what the backing entity actually accepts.
- **Always show the band midpoint as the target.** This is what the inherited WIP did, and it is
  defensible as a general-purpose fallback, but it produces a number like 70° next to a badge that
  says "Cooling" while the unit works toward 78°, which reads as broken even when the underlying
  data is technically correct. Rejected in favor of an `hvac_action`-aware target that matches what
  the equipment is actually doing, falling back to the midpoint only when there is no active bound
  to report.

## Two mistakes caught by testing against the real thing

Both were caught only because verification went past unit tests and a hand-typed `curl` call, all
the way to an actual tap through the deployed dashboard in a real browser:

1. The first "fixed" version of `thermostatSetTemperaturePayload` still sent only the active
   bound's key. The `curl` command used to "verify" it beforehand had the second key added by
   hand, not produced by the function itself, so the gap went unnoticed until a live click through
   Playwright produced the real `400` from the real request the browser actually sent.
2. After fixing that and redeploying `homie-custom.js` under the same `?v=20260807.12` query
   string, the browser kept executing its cached pre-fix copy. A `curl` fetch of the same URL (no
   browser cache) showed the corrected file on disk, which briefly looked like proof the fix had
   shipped. Only a fresh browser navigation surfaced that the running code was stale. The lesson:
   the cache-busting token has to change on every deploy that touches a nested asset's bytes, not
   only on releases meant for a person to notice, and "the file on disk is correct" is not the same
   claim as "the browser is running the file on disk."

## Verification

- `node --test test/screen-a.test.cjs`: 38/38, including new tests for the `hvac_action`-aware
  target selection, the step-size lookup, and a regression test asserting every dual-setpoint
  payload carries both bound keys regardless of `hvac_action`.
- Direct REST calls against `climate.casasolar_south_zone_1` reproduced both silent failure modes
  before the fix, and confirmed the corrected payload shape and step size actually move
  `target_temp_high`/`target_temp_low`, before any browser was involved.
- An actual Playwright tap through the deployed dashboard (release `20260807.13`) moved the real
  entity's `target_temp_high` from 78 to 79, confirmed by `last_updated` advancing. Verified both
  entry points: Overview C's launcher (filtered to South only) and Overview A's Climate chip
  (unfiltered, both South and North tabs present).
- The thermostat was returned to its original 78/62 setpoint after testing. Live
  `homie-dashboard.html` and `homie-custom.js` were confirmed byte-for-byte identical to the fork's
  working tree after deployment.

## Still open

The close-time filter-reset test recorded in
[homie-dashboard-install-plan.md](homie-dashboard-install-plan.md) as not mutation-sensitive is
unrelated to this fix and remains deferred.

A credential-handling incident occurred during the browser-verification step of this work and was
resolved directly with pde at the time. Deliberately not detailed here since this repository may
become public.
