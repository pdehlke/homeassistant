# Climate History Graph Feasibility (Item 1)

**Superseded 2026-08-12**: item 1 turned out not to need building at all. See
[homie-climate-native-dialog.md](homie-climate-native-dialog.md): the Climate overlay now opens
Home Assistant's own native more-info dialog instead of a Homie-drawn reimplementation, and that
dialog already has a real, recorder-backed history graph built in. The analysis below is kept as
the record of what this would have taken under the approach that was in place at the time.

Feasibility analysis for [project-todo.md](../project-todo.md) item 1: adding a temperature/humidity history
graph to the Climate chip's thermostat overlay, matching the history-graph icon on Home
Assistant's native climate more-info dialog. The item was deferred out of the 2026-08-11
native-parity overlay rebuild (see [homie-dashboard-install-plan.md](./homie-dashboard-install-plan.md)'s checkpoint of that
date) with the note that it "needs either a charting library or a hand-rolled sparkline
against the recorder API, real scope and risk beyond that session." This document checks
that assumption before implementation starts, so the check does not have to be repeated.

## The question

Overview C's Weather card already has a chart, labeled "Hourly Forecast." Could item 1 reuse
that chart's constructs directly, or does it really need a charting library, or a hand-rolled
sparkline built from nothing?

## Finding: no charting library anywhere in the bundle

Grepped `dist/homie-dashboard.html`, `dist/homie-custom.js`, and `dist/config.js` for
Chart.js, ApexCharts, D3, and Plotly. None are present. Every chart currently on Overview C
is hand-built inline SVG: manual pixel-position math plus string-templated `<path>`,
`<circle>`, `<rect>`, and `<text>` elements, assembled in plain JavaScript with no rendering
library at all.

## The two existing implementations

**Weather Hourly Forecast** (`_fetchOv3HourlyChart`, `dist/homie-dashboard.html` around line
19418): a single-series smoothed-line chart. Computes x/y pixel positions from up to 8 data
points, builds a Bezier path with a gradient-filled area beneath it, color-grades each point
by temperature, and labels alternating points with time and temperature text. Data source is
a `weather.get_forecasts` service call (`return_response: true`) sent over Homie's existing
WebSocket connection, targeting `CONFIG.weather.entity`. This is forecast data: it looks
forward, not back.

**Solar hourly history** (`_sfsFetchHourlyStatistics` at line 10249, rendered by `_sfsDraw` at
line 10422): a two-series grouped bar chart (solar production, home consumption), sharing one
linear scale because both series are in kW, with gridlines and y-axis labels. Data source is
a `recorder/statistics_during_period` WebSocket call, requesting hourly buckets from local
midnight to now for a list of `statistic_ids`. This looks backward, the direction item 1
actually needs.

## Why "Hourly Forecast" can't just be pointed at new data

It isn't a reusable chart component or entity. It's a bespoke function wired to one call
(`weather.get_forecasts`) and one shape of data (a short forecast array). The *rendering*
technique (smoothed line, gradient fill, labeled points) is worth reusing. The *data-fetch*
call is not: it fetches the wrong direction in time for a history graph.

## Recommended approach

Combine the two existing implementations rather than build a third from scratch: reuse the
Solar chart's `recorder/statistics_during_period` fetch pattern, pointed at the climate
entities' temperature/humidity sensors, and adapt the Weather chart's line-rendering
technique to draw two series against two independent y-axes (true dual axis, matching HA's
native history-graph). Two alternative renderings were considered and rejected in a grilling
session on 2026-08-11:

- **Normalized overlay** (both series mapped to a shared 0-1 scale): simpler to build, but
  the two lines would cross at points with no real meaning, which could mislead at a glance.
- **Two stacked mini-charts** (separate single-series temperature and humidity charts,
  stacked vertically): simplest to build, since it reuses the Weather chart's single-series
  renderer twice with no new axis logic, but takes more vertical space in the overlay and
  isn't what HA's native dialog does.

True dual axis was chosen because native parity is the stated goal of item 1.

## Confirmed live: the needed sensor data already exists

A climate entity's `current_temperature` and `current_humidity` are attributes of the
entity's own state, not the entity's state itself, and attributes are not normally
statistics-eligible. That would have forced using `history/history_during_period` (raw
state+attribute history) instead of the simpler `recorder/statistics_during_period` call the
Solar chart already uses.

Checked directly against the real instance on 2026-08-11 via `GET /api/states`, filtering for
`casasolar` (both Lennox zones), rather than assuming: the `lennoxs30` integration exposes
temperature and humidity as their own separate numeric sensor entities, sibling to the
`climate.*` entities, not just as climate attributes:

| Entity | Unit | `device_class` | `state_class` |
|---|---|---|---|
| `sensor.casasolar_north_zone_1_casasolar_north_zone_1_temperature` | °F | `temperature` | `measurement` |
| `sensor.casasolar_north_zone_1_casasolar_north_zone_1_humidity` | % | `humidity` | `measurement` |
| `sensor.casasolar_south_zone_1_casasolar_south_zone_1_temperature` | °F | `temperature` | `measurement` |
| `sensor.casasolar_south_zone_1_casasolar_south_zone_1_humidity` | % | `humidity` | `measurement` |

All four carry `state_class: measurement`, which is what makes an entity statistics-eligible.
`recorder/statistics_during_period`, the exact call the Solar chart already makes, will work
directly against these four entities. No need to parse temperature/humidity out of the
climate entity's own attribute history.

## The one real gap

Dual y-axis, two-series line rendering does not exist anywhere in the codebase yet. The
Weather chart is single-series. The Solar chart's two series share one scale only because
both happen to already be in the same unit (kW). Building a chart that overlays a °F-ranged
line and a 0-100%-ranged line, each against its own axis, is the actual new code item 1
needs.

## Ruled out: borrowing HA's native history-graph component

Considered reaching into Home Assistant frontend's own native history-graph web component
instead of hand-rolling anything. Not practical: Homie's dashboard is a standalone static
HTML page loaded through a Lovelace iframe strategy, not part of HA frontend's own component
tree, so there is no native chart element available to borrow at runtime.

## Net effect on item 1's scope

The deferred note's framing ("needs either a charting library or a hand-rolled sparkline
against the recorder API, real scope and risk beyond that session") was more pessimistic than
the codebase actually supports. Both halves of the problem, the past-looking statistics fetch
and the SVG line-chart rendering, already exist as proven, shipped code on Overview C. What's
left for implementation is adapting and combining those two functions and adding true
dual-axis support, not building a new charting surface from nothing.
