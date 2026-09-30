# Clock dashboard: live energy cards

Two cards on `dashboard-clock` moved off Home Assistant's built-in energy cards and onto live
sensors on 2026-09-30, because the built-in cards can be up to an hour behind while presenting
themselves as today's totals. On a wall display that is glanced at rather than studied, a stale
number reads as a wrong number.

The trigger was pde comparing the dashboard against the Sense phone app: the dashboard said net
grid export was 5.4 kWh, the app said 7.9 kWh, and the app was right.

## Three separate lags, which is why the first diagnosis was incomplete

The gap between the two figures was not one problem. It was three, stacked on one moment, and the
first pass conflated them by confirming the sensors were correct and then claiming the displays
were correct. Those are different claims.

| Lag | Size | Fixed? |
| --- | --- | --- |
| The Energy dashboard's solar source pointed at a dead Sense sensor | permanent, never caught up | Yes, see below |
| Sense's trends API trails its own realtime stream | about 7 minutes | No, and not fixable from here |
| HA's energy cards read hourly statistics | up to 60 minutes | Worked around, not fixed |

The first is written up separately in
[overview-c-solar-today-totals.md](../homie-dashboard/overview-c-solar-today-totals.md), under the
2026-09-30 correction in its "Data available" section. In short, the solar source was
`sensor.solar_daily_energy`, a Sense device-level trend sensor for the auto-detected "Solar"
pseudo-device, which has never had anything attributed to it. It now points at
`sensor.sense_287516_daily_production`.

The third is the one this document is about.

## The energy cards read hourly statistics, and HA already has finer data

At 10:25 local, three different answers to the same question were available from the same recorder:

| Source | Exported today | Through |
| --- | --- | --- |
| `period: "hour"` statistics | 9.4 kWh | 10:00 |
| `period: "5minute"` statistics | 11.9 kWh | 10:15 |
| `sensor.sense_287516_daily_to_grid` live state | 12.9 kWh | 10:22 |

The Energy panel showed 9.4 kWh exported, 4 kWh imported, and a grid balance of -5.4 kWh. That is
the hourly figure exactly, and it is what proves which resolution the cards use: the hourly sum of
`change` for the day was 0.1 + 3.5 + 5.8 = 9.4, while the five-minute sum was 11.9. Solar agreed
the same way, 0.4 + 4.0 + 6.5 = 10.9 against the panel's 10.9 kWh. The chart drawing one bar per
hour is the visible corroboration.

So the five-minute statistics exist, are current, and the single-day energy views decline to use
them. The staleness grows through each hour and snaps shut at the top of it.

This is Home Assistant's own design for the `/energy` panel and its `energy-*` cards. It is not
configurable, which is why the Clock dashboard had to stop using those cards rather than be
tuned into behaving.

## The Sense trend sensors are accurate, just late

Before replacing anything with them, the daily trend sensors were checked against a completely
independent path: integrating `sensor.solar_power`, which comes from Sense's realtime stream rather
than its trends API. 6,718 recorded points across the window, integrated trapezoidally, with each
sample interval split at local midnight so partial intervals land on the right day. Arizona has no
DST, so that boundary needs no special handling. Only complete days are compared.

| Day | `daily_production` change | Integrated `solar_power` | Difference |
| --- | --- | --- | --- |
| 2026-09-23 | 24.3 | 24.10 | 0.20 |
| 2026-09-24 | 41.0 | 40.65 | 0.35 |
| 2026-09-25 | 55.5 | 55.48 | 0.02 |
| 2026-09-26 | 49.0 | 48.72 | 0.28 |
| 2026-09-27 | 23.1 | 23.02 | 0.08 |
| 2026-09-28 | 15.4 | 15.21 | 0.19 |
| 2026-09-29 | 19.1 | 18.60 | 0.50 |

Within half a kWh every day, against a measurement path that shares nothing with the one being
checked. The trend sensors are sound at day scale.

The intraday lag was measured rather than assumed. The running integral crossed 10.9 kWh at
09:49:19 and the trend sensor reported 10.9 at 09:57:13, a lag of 7m54s. It crossed 12.3 kWh at
10:00:19 and the sensor reported 12.3 at 10:07:15, 6m56s. Call it seven minutes. The phone app
reads the realtime side, so it is always that far ahead of anything Home Assistant gets from
trends.

## The hourly bad poll, which only bites live readers

Roughly once an hour, Sense's trends endpoint returns a partial day and the trend sensors publish a
value far below the real one, correcting on the next five-minute poll. Raw history for
`sensor.sense_287516_daily_production` on 2026-09-30:

```
08:57:01   4.4
09:02:02   0.6   <- bad poll
09:07:03   5.4
...
09:57:13  10.9
10:02:14   5.3   <- bad poll
10:07:15  12.3
```

The dips landed at 08:01, 09:02 and 10:02, so shortly after the hour, and each lasted one poll
interval. `sensor.solar_daily_energy` flapping to `unavailable` hourly is the same fault seen from
a different sensor.

**The statistics engine nets these out correctly and the live state does not.** Hourly `change` for
production that day ran 0.4, 4.0, 6.5, summing to exactly the state at the end of the 09:00 hour,
with no double counting. Across the 10:00 dip the five-minute buckets recorded -5.1 then +6.3,
netting +1.2, which is precisely 10.6 minus 9.4. So anything reading statistics is immune and
anything reading live state is not.

Two consequences worth knowing:

- The `Today So Far` card will show visibly wrong low numbers for about five minutes an hour. This
  is a known, accepted cost of reading live state, not a defect in the card.
- `automation.low_grid_export_alert` is safe. It calls `recorder.get_statistics` with `period: day`
  and `types: [change]` rather than reading state, so a bad poll cannot trip it.

This also explains a misreport during the investigation itself: a figure of 5.3 kWh quoted for
`daily_production` was one of these dips, caught by chance. The 10.9 kWh the Energy panel showed at
the same moment was the statistics value and was correct.

## What replaced what

| Slot | Before | After |
| --- | --- | --- |
| Section 1, card 1 | `energy-usage-graph`, titled "Energy Balance" | `custom:apexcharts-card`, "Power Flow Today" |
| Section 1, card 2 | `energy-grid-neutrality-gauge` | `markdown`, "Today So Far" |

`Power Flow Today` plots `sensor.homie_solar_generation`, `sensor.homie_whole_house_load` and
`sensor.homie_grid_flow`, the three existing kW template helpers, midnight to midnight, with
`extend_to: now`. `homie_grid_flow` is negative when exporting, so the line dropping below zero is
power leaving the house. The header carries `show_states` and `colorize_states`, which makes the
bottom legend redundant, so it is turned off to reclaim about 35px.

`Today So Far` reads the four Sense daily trend sensors and shows an `as of` stamp derived from
`last_reported`, so the card states its own freshness instead of leaving a reader to guess. That
stamp only advances when one of the four values changes, which in practice is every poll during
daylight and never overnight, when nothing is moving anyway.

The remaining `Current Solar Production` gauge on `sensor.solar_power` was already live and was not
touched. Nor was the `Net Grid Energy: Last 10 Days` apexcharts card, which calls
`recorder/statistics_during_period` directly in its `data_generator` and so bypasses the energy
cards entirely. It was correct before and after.

## Rejected options

**Keeping the built-in energy cards and tuning them.** There is no configuration that moves the
single-day energy views onto five-minute statistics. The lag is structural.

**Pointing the Energy dashboard at a Riemann-sum integration helper over `sensor.solar_power`.**
This would be genuinely live, and was rejected because a new helper starts accumulating from the
moment it is created, so the Energy dashboard would lose every day of history it has. It also
introduces a second source of truth for the same quantity. The trend sensor carried 2,331.6 kWh of
statistics that would have been abandoned.

**Four monotonic template helpers to suppress the hourly bad poll.** A template sensor can refuse
to decrease within a day by reading `this.state`, which would clean up the five-minutes-an-hour
glitch on the live card. Deferred rather than rejected: pde chose the option with no new helper
entities, on the reasoning that it is better to see how often the glitch actually annoys before
adding four entities to suppress it.

**Inline HTML with a `style` attribute for the conditional colour.** Rejected without testing.
Home Assistant's markdown card sanitises rendered HTML through the `xss` library's whitelist, and
whether `style` survives that has never been verified on this instance; the Home Status card's own
write-up
([clock-home-status-card.md](clock-home-status-card.md)) records deliberately avoiding the same
question. Plain markdown emphasis already renders, so there was no need to find out.

**card-mod.** Retired on this instance. All styling here is UIX.

## Two things that needed CSS rather than configuration

**The sign of a number cannot be expressed in CSS.** Net export is green when positive and red when
negative, which means the template has to encode the sign structurally: `**value**` when above
zero, `*value*` when below, and bare when exactly zero. Two UIX rules then colour `strong` and `em`
inside that cell, with `font-style: normal` on the `em` so it does not come out italic. Verified in
the rendered DOM: positive computes `rgb(102, 187, 106)`, and substituting the `em` form in the
browser alone, with no config change, computes `rgb(239, 83, 80)`.

**Home Assistant's stylesheet left-aligns and bolds every `th`, beating marked's own `align`
attribute.** This matters twice. The `Net export` row is a header-only table, so its value needed
`text-align: right` set explicitly. The top table's header row carries real values rather than
column labels, so it needed both `font-weight: normal` and per-column `text-align: right` to stop
reading as a header. Both rules carry comments saying why, because they look removable and are not.

Values also carry `white-space: nowrap`. Without it, a value and its `kWh` label break onto separate
lines once the section column is narrow, which happens at a 1920 viewport with the sidebar expanded
and would happen on the Office display as soon as production reaches three digits.

## Layout arithmetic, and two wrong guesses

A sections-view grid row is 56px with an 8px gap, so an `n`-row slot is `56n + 8(n-1)` pixels tall.
A custom card that overflows its slot does not grow the slot; it draws over the card below.

That was learned twice. `grid_options.rows: 5` with a 300px chart overflowed and the axis labels
landed on top of the next card's title. `rows: 8` cleared it and left about 100px of dead space.
`rows: 7` was right for that size. After the later request to shrink the card, turning the legend
off and dropping the chart to 180px brought content to roughly 290px, which fits `rows: 5` at 312px.

Card heights measured live at a 1920x1080 viewport, as `Pete`, so with the header and sidebar the
`Office` account does not get:

| Card | Top | Bottom | Height |
| --- | --- | --- | --- |
| Home Status | 80 | 368 | 288 |
| Power Flow Today | 376 | 668 | 292 |
| Today So Far | 696 | 967 | 270 |
| Current Solar Production | 975 | 1171 | 196 |

## Open: the gauge and the unmeasured display

The reason for shrinking both cards was that `Current Solar Production` was running off the bottom
of the Office monitor. It is not confirmed fixed. At the 1920x1080 proxy above its bottom edge sits
at 1171, which is 91px past a 1080 viewport; removing the header that kiosk mode hides brings that
to roughly 1107, still about 27px over.

Whether it clears the real display is unknown, because **the Office display's resolution has never
been measured**. Both [clock-weather-widget.md](clock-weather-widget.md) and
[office-clock-card.md](office-clock-card.md) hit the same wall and say so explicitly, the latter
noting that "1920x1080 in a browser is a proxy, not the real display". pde reported the result
acceptable after the shrink, which is the only evidence that exists about the actual panel.

Measuring that resolution once and writing it down would retire a recurring unknown across at least
three documents.

## Verification

Every write used a JSON Patch with a `test` operation on the target card's type or title plus an
optimistic-locking `config_hash`, so a wrong index would have failed instead of overwriting a
neighbour. The full config was read and saved before the first change and again mid-way.

One write was rejected with a conflict, caused by passing the `config_hash` returned by a previous
write rather than one from a read; the MCP server tracks its own last-read separately. Before
retrying, the live config was diffed against the pre-change backup to confirm nothing outside this
work had changed. It had not. Re-reading with `ha_config_get_dashboard` cleared the conflict.

The markdown template was rendered against live state through the template API before each save,
never after, which is the same discipline
[clock-home-status-card.md](clock-home-status-card.md) used. Every layout change was confirmed by
screenshot at 1920x1080 via `playwright-cli`, and the cell geometry was read back out of the shadow
DOM rather than judged by eye: all ten cells report `white-space: nowrap` and a uniform 37px
height.

Browser console showed only the two pre-existing errors already recorded in the `home-assistant`
skill's [lovelace.md](../../.claude/skills/home-assistant/references/lovelace.md), the duplicate
`rss-news-card` registration and its related 404. Nothing new.
