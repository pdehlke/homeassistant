# Climate overlay idle target: nearest bound, not band midpoint

Why the Homie dashboard's Climate overlay showed a target of 70°F for Main House when the
real setpoint was 78°F, and why the fix is "nearest setpoint" rather than the other options
considered.

## Symptom

The Main House thermostat (`climate.casasolar_south_zone_1`) was set to 78°F cooling / 62°F
heating, but every Homie surface that shows a single target number read 70°F: the Climate
overlay's dial, all three Overview screens' Climate entry points, and the floors card's
Target stat. The Lennox Home dashboard, showing the same entity through Home Assistant's stock
`thermostat` card, correctly showed 78°F.

## Why it happened

Both real thermostats (`climate.casasolar_south_zone_1`, `climate.casasolar_north_zone_1`) run
in `heat_cool` mode almost all the time, reporting `target_temp_high`/`target_temp_low` rather
than a single `temperature` attribute. `thermostatTemperatureView()` in
`dist/homie-custom.js` (in the fork at
[`/Users/pde/src/github.com/pdehlke/homie-dashboard`](https://github.com/pdehlke/homie-dashboard))
already handled this dual-setpoint band by preferring the bound `hvac_action` reported as
actively in play: `target_temp_high` while `cooling`, `target_temp_low` while `heating`. That
logic was added deliberately in an earlier fix (see
[homie-thermostat-control-fix.md](homie-thermostat-control-fix.md)) specifically to avoid
showing a midpoint next to a "Cooling" badge when the unit was really working toward 78°.

That earlier fix left one case unresolved: `hvac_action` is `idle` whenever the equipment is
satisfied and not actively running, which for a thermostat holding a comfortable house is the
*normal resting state*, not a rare edge case. With no bound "active," the code fell back to the
literal midpoint of the band: `(78 + 62) / 2 = 70`. That 70 matches no real setpoint on either
thermostat and reads as wrong, which is exactly what was observed. The bug was already covered
by a passing, deliberately-written test
(`test/screen-a.test.cjs`, "thermostat range setpoint follows the active hvac_action bound, not
a midpoint average," idle case) that asserted the midpoint was the intended behavior. It was a
real design decision, just one that didn't hold up once idle turned out to be the common case
rather than the exception.

## What changed

In `dist/homie-custom.js`, `thermostatTemperatureView()`'s fallback for
idle/fan/unreported `hvac_action` now picks whichever bound `current_temperature` is nearer to,
instead of averaging the two. A tied or missing `current_temperature` defaults to the high
(cooling) bound. `floorTargetText()` calls the same function, so the floors card's Target stat
picks up the fix for free; no other display path exists (confirmed: `thermostatTemperatureView`
and `floorTargetText` are the only two places any Homie surface computes a displayed target).

`thermostatSetTemperaturePayload()`'s idle-fallback behavior (shifting both bounds together to
preserve the band's width when the user taps +/- with no bound active) was deliberately left
unchanged. That is a separate, already-tested adjustment-semantics decision unrelated to what
was reported here, a display-only bug. Changing it was out of scope.

Release token bumped `20260809.6` -> `20260810.1` in `dist/homie-dashboard.html` and the
`homie-dash` Lovelace iframe URL, per the fork's cache-busting convention.

## Options considered and rejected

- **Always show the cooling bound (`target_temp_high`) when idle.** Simplest, and matches the
  observed case (Arizona, August, AC-dominant). Rejected: silently wrong once the North zone (or
  the South zone, in winter) idles on the heating side, at which point it would show the wrong
  setpoint with no signal anything was off.
- **Show the band as a range ("62–78°") instead of collapsing to one number.** The most honest
  representation, and closest to what the Lennox Home dashboard's native card actually does.
  Rejected for now: it's a bigger change than the bug warranted, touching the compact
  single-line layout budget on all three Overview screens and the floors card's small stat
  tiles, not just the fallback branch. Worth reconsidering if a future redesign has room for it.
- **Remember the last active bound and keep showing it through idle.** Matches the physical
  intuition ("still working toward 78") most closely of any option. Rejected: requires
  persisting state across renders per entity, which none of `thermostatTemperatureView`'s other
  branches need; a stateless nearest-bound heuristic gets the same answer in the case that
  matters (current_temperature is almost always close to the setpoint it's holding) without the
  added state.
- **Nearest bound to `current_temperature` (chosen).** Stateless, matches the observed case,
  self-corrects seasonally without a mode-specific assumption, and required only a small,
  isolated change to logic that was already structured around picking one of two bounds.

## Verification

- `node --test test/screen-a.test.cjs`: 63/63, including updated expectations for the two
  existing idle/no-hvac_action fixtures (now resolved to the nearer bound instead of the
  midpoint) and new cases for a low-side idle fixture, a tie, and a missing `current_temperature`.
- Direct `GET /api/states/climate.casasolar_south_zone_1` confirmed the live fixture used in the
  fix (`current_temperature: 76`, `target_temp_high: 78`, `target_temp_low: 62`,
  `hvac_action: "idle"`) before and after deploy, unchanged by the deploy itself.
- Deployed `homie-custom.js` and `homie-dashboard.html` to
  `/config/www/community/homie-dashboard/`, backing up the previous copies first; confirmed the
  live files are byte-identical to the fork's `dist/` after upload.
- Updated the `homie-dash` Lovelace dashboard's iframe `?v=` to match, backing up its prior
  config to `/Users/pde/tmp/` first.
- Live-verified via Playwright, authenticated as the Homie Dashboard account: opened the Climate
  overlay for Main House and confirmed it now reads "TARGET 78°" against a current reading of
  77°, matching the real entity's `target_temp_high`. Confirmed the entity's
  `target_temp_high`/`target_temp_low` were unchanged after the verification pass.

## Still open

None. This fix is self-contained; it does not touch any of the items already tracked in
`homie-dashboard-install-plan.md`'s open-work list.
