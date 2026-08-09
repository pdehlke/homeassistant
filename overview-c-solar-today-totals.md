# Overview C Solar: today's green % and CO2 intensity

The full-screen Solar view's "Low Carbon" and "CO2 Intensity" stats are both instantaneous: they
describe the grid's mix and the home's blend of it at this exact moment. This document covers two
new stats, "% Green Today" and "CO2 Intensity Today", that answer a different question: what
fraction of everything the house actually used *today* was low carbon, and what was today's average
carbon intensity per kWh consumed. See [homie-dashboard-install-plan.md](homie-dashboard-install-plan.md)
for the fork location and deployment workflow, and
[overview-c-solar-home-green-percentage.md](overview-c-solar-home-green-percentage.md) for the
instantaneous version this extends.

Written before implementation this time, per pde's request, unlike the home-green-percentage
change above which was written up after the fact. The Verification section below stays empty
until the change ships.

## The problem

The instantaneous "Low Carbon" stat is accurate for the moment it's read, but it can't answer "how
green was today." At night, solar production is zero, so the home runs entirely on grid power. The
utility still delivers a real, non-zero low-carbon share overnight (nuclear and wind don't stop
because the sun is down), but that share can differ substantially from whatever the grid's mix
happens to be at the moment someone glances at the dashboard. A single current reading, applied to
a full day of consumption, would misrepresent both sunny days (understating how green the day was,
since the instantaneous grid-only figure ignores accumulated solar) and the mirror case pde raised
directly: applying the *current* fossil percentage to a whole day punishes or flatters the day's
score based on nothing more than what time it happens to be checked.

## Data available

Confirmed against the live instance before agreeing to build anything:

- `sensor.sense_287516_daily_energy`: today's total home consumption, kWh, resets at local
  midnight.
- `sensor.sense_287516_daily_production`: today's total solar production, kWh, same reset.
- `sensor.sense_287516_daily_from_grid` / `sensor.sense_287516_daily_to_grid`: today's grid import
  and export, tracked as separate totals, not just a net figure.
- `sensor.electricity_maps_grid_fossil_fuel_percentage` and `sensor.electricity_maps_co2_intensity`:
  update roughly every 15 to 60 minutes, and go `unavailable` for a minute or two most cycles. This
  is a transient blip, not a dead sensor: history shows a steady stream of valid readings around
  each gap.
- Arizona has no DST, so the local-midnight reset on the Sense sensors never has a DST edge case to
  worry about.
- Home Assistant's recorder already compiles hourly long-term statistics for all five sensors above
  (confirmed via `recorder/statistics_during_period`): mean/min/max per hour for the two percentage
  sensors, and sum/change per hour for the three energy sensors, correctly split across the midnight
  reset. Every hour in a 24-hour test window had a value, even through the sensors' own transient
  unavailable spells, because the hourly aggregate only needs one valid sample in the hour to
  compute.
- The Energy Dashboard is configured with the grid import/export sensors above, but has no solar
  source and no carbon-intensity source wired in, so HA's own built-in low-carbon accounting isn't
  active. Noted for awareness; this project builds the two new stats directly rather than turning
  that on, since the ask was specifically for Homie Dashboard badges.

## Placement

Both new stats replace the two inverter-temperature placeholder cards (`Left Inverter`, `Right
Inverter`) in the full-screen Solar view's second stat row. Those cards have shown a permanently
unbound `— °F` since the Overview C solar rework, reserved for a future Tesla inverter integration.
That integration is not going to happen; see the correction to
[overview-c-solar-home-green-percentage.md](overview-c-solar-home-green-percentage.md)'s sibling
doc and [homie-dashboard-install-plan.md](homie-dashboard-install-plan.md) for where that reference
gets removed. Repurposing both slots now rather than reserving one turns two placeholders that were
never going to bind into two stats that are useful today.

- `Left Inverter` → **% Green Today**, leaf icon (reused from the existing Low Carbon stat, same
  green), value text colored green.
- `Right Inverter` → **CO2 Intensity Today**, emissions icon (reused from the existing CO2
  Intensity stat).

The existing instantaneous "Low Carbon" and "CO2 Intensity" stats in the first row are unchanged.

## The formulas

### % Green Today

For each elapsed hour today (midnight to now, in the recorder's own hourly buckets):

```
selfConsumedKwh_hour = max(0, solarProducedKwh_hour − gridExportedKwh_hour)
greenKwh_hour = selfConsumedKwh_hour + gridImportedKwh_hour × (100 − fossilPct_hour_mean) / 100
```

Sum `greenKwh_hour` across every hour that has a complete set of inputs, then:

```
% Green Today = totalGreenKwh / todaysTotalConsumptionKwh × 100, clamped to [0, 100]
```

`todaysTotalConsumptionKwh` is read live from `sensor.sense_287516_daily_energy`, the same figure
already shown as "Today's Usage" on this card, not reconstructed by summing the hourly buckets.

This mirrors the instantaneous `homeGreenPercentage` formula exactly (solar counts as 100% green
but only the portion the house actually used; grid import counts at the grid's own green fraction),
integrated hour by hour instead of read once.

### CO2 Intensity Today

For each elapsed hour today:

```
gramsCO2_hour = gridImportedKwh_hour × co2Intensity_hour_mean
```

Solar-covered hours contribute zero, since self-consumed solar carries no grid emissions. Sum across
every hour with both inputs present, then:

```
CO2 Intensity Today (gCO2/kWh) = totalGramsCO2 / todaysTotalConsumptionKwh
```

Same denominator sensor as % Green Today, for the same reason: consistency with the already-visible
"Today's Usage" figure.

### Missing data

Each formula treats an hour as valid only if every input it needs is present for that hour (four
inputs for % Green Today: solar, export, import, fossil%; two for CO2 Intensity Today: import, CO2
intensity). An hour missing any required input is skipped entirely rather than partially counted,
and the running total continues from the hours that did report. If literally no hour today has
valid data, the stat shows `—`, the same convention every other stat on this card already uses.

This makes the two stats' effective denominators (hours actually counted) potentially different
from each other, since they depend on different inputs, and both are technically an underestimate
of the true day whenever a gap is skipped rather than filled in. Accepted trade-off: a slightly
understated number that's always present beats a strict `—` that would trigger most days, given
fossil%/CO2 intensity blip on most refresh cycles even though the hourly long-term statistics have,
so far, always back-filled successfully around those blips.

## Technical approach

The existing full-screen Solar hourly chart fetches raw history via REST
(`/api/history/period`) and hand-averages it client-side, because all it needs is an instantaneous
mean per hour. This feature needs per-hour *sums* for three energy sensors plus per-hour *means* for
two percentage sensors, which HA's recorder already computes and exposes through the WS-only
`recorder/statistics_during_period` call. Rather than reimplement that bucketing and weighting by
hand from raw history, Homie's existing live WebSocket connection (already open for entity state
subscriptions) gets one additional request/response call, following the same
send-with-id/match-response/timeout-cleanup pattern already used for the alarm panel's
`call_service` calls.

New configuration roles added to `CONFIG.solar.stats` in `dist/config.js`:

- `daily-production`: `sensor.sense_287516_daily_production`
- `daily-from-grid`: `sensor.sense_287516_daily_from_grid`
- `daily-to-grid`: `sensor.sense_287516_daily_to_grid`

New pure functions in `dist/homie-custom.js`: a merge step that aligns the five hourly-statistics
series by bucket start time into one array of per-hour records, and the two formulas above, each
taking that merged array plus today's live consumption total.

The fetch is cached for 5 minutes, the same policy the existing hourly chart already uses, since an
hourly-bucketed running total doesn't need to be fresher than that and it keeps WS statistics calls
infrequent.

## Options considered and rejected

- **Add a 6th stat card to the first row, or a second row slot, instead of repurposing the
  inverters.** Rejected once pde pointed out the inverter placeholders are permanently unbound
  (Tesla inverter integration cancelled) and better spent on something real than reserved for
  hardware that was never coming.
- **Simpler grid-mix-only average**, ignoring solar self-consumption apportionment: take a
  kWh-import-weighted average of the grid's green % across the day and apply it to
  (consumption − solar produced). Rejected in favor of mirroring the existing instantaneous
  formula's self-consumption logic exactly, just integrated hourly instead of read once.
- **Reconstruct today's total consumption by summing the same hourly buckets used for the
  numerator**, instead of reading `sensor.sense_287516_daily_energy` directly. Rejected for the same
  reason the instantaneous version rejected it: the card already shows that figure as "Today's
  Usage," and reusing it keeps this stat honestly describing the same consumption number sitting
  next to it, at the cost of a theoretical (and so far unobserved) small mismatch between two
  independently metered accounting paths.
- **Show `—` for the whole badge if any hour today has a gap**, matching the strict convention every
  other stat here uses for missing live data. Rejected: fossil%/CO2 intensity blip for a minute or
  two on most refresh cycles, so a strict policy would blank the badge far more often than the
  underlying data problem actually warrants, given the hourly long-term statistics have so far
  always compiled successfully around those blips.
- **Hand-roll the hourly weighting from raw REST history**, extending the existing chart's
  `fetchHourlyAvg` approach. Rejected in favor of the recorder's own `recorder/statistics_during_period`
  statistics, which already compute the correct sum/mean per hour, including the midnight reset,
  without reimplementing logic HA provides for free. Costs the fork one new (small, well-scoped)
  WS request type.
- **CO2 Intensity Today as a raw time-weighted average of the grid's own published intensity**,
  ignoring solar, matching how the existing instantaneous CO2 Intensity stat is grid-only today.
  Rejected: it would sit oddly next to a home-blended % Green Today, and the whole point of a
  "Today" pair of stats is to describe the house's actual footprint, which solar genuinely reduces.
- **Distinct icons** for the two new stats, to visually separate "today" from "now" at a glance.
  Rejected in favor of reusing the existing Low Carbon leaf and CO2 Intensity emissions icons: the
  two pairs sit in different rows, so there's no adjacency confusion, and the shared icon signals
  "same kind of number, different time scale" without adding new visual vocabulary.

## Verification

Pending. Filled in after implementation, testing, and live deployment.
