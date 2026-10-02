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

- The `Today So Far` card used to show visibly wrong low numbers for about five minutes an hour,
  accepted at the time as the cost of reading live state. It no longer reads these sensors
  directly, so neither this fault nor the `unavailable` one below reaches it. See the two sections
  that follow.
- `automation.low_grid_export_alert` is safe. It calls `recorder.get_statistics` with `period: day`
  and `types: [change]` rather than reading state, so a bad poll cannot trip it.

This also explains a misreport during the investigation itself: a figure of 5.3 kWh quoted for
`daily_production` was one of these dips, caught by chance. The 10.9 kWh the Energy panel showed at
the same moment was the statistics value and was correct.

## The dropout that rendered as a measured zero, fixed 2026-10-02

pde reported that before dawn the card read 0 kWh for Produced and Exported, which is correct, and
0 kWh for Used, Imported and Net export, which is not: the house draws from the grid all night. The
three wrong figures only appeared once the panels started producing.

The sensors were never at fault. `sensor.sense_287516_daily_energy` and
`sensor.sense_287516_daily_from_grid` climb through every night, reaching 2 to 3 kWh by dawn, on
each of the six days the recorder still holds. The template was at fault:

```jinja
{% set u = states('sensor.sense_287516_daily_energy') | float(0) %}
```

`float(0)` yields 0 for any state that is not a number, so an `unavailable` sensor rendered as a
measured zero rather than as an outage. All four Sense daily trend sensors drop to `unavailable`
together for exactly one five-minute poll, several times a day, usually in a run at the same minute
past the hour, and on the last three mornings that run sat squarely in the pre-dawn hours:

| Day | episodes | local times |
| --- | --- | --- |
| 2026-09-30 | 6 | 00:00 (10 min), 03:45, 04:46, 05:46, 06:46, 07:46 |
| 2026-10-01 | 5 | 04:46, 05:46, 06:46, 07:46, 08:46 |
| 2026-10-02 | 2 | 05:46, 06:46 |

Each lasts 301 seconds, one poll interval. On both 10-01 and 10-02 the last dropout before sunrise
ran 06:46 to 06:51 and the first nonzero production arrived at 06:56, which is exactly the
coincidence the report describes: all five figures read zero, and then minutes later Produced
appeared and Used, Imported and Net export came back with it.

### Three explanations ruled out first

**A stale card.** The card carries an `entity_id:` list naming the four sensors, which reads like it
controls when the card re-renders, so a card frozen at the midnight reset was the first suspect.
Core ignores it. A `render_template` subscription whose template read only `sensor.solar_power`,
with `entity_ids` naming only `sensor.sense_287516_daily_production`, reported
`listeners: {"entities": ["sensor.solar_power"]}` on every render and fired on `solar_power`'s
changes, not production's. Tracking comes from what the template reads, nothing else. A second
subscription confirmed a `daily_energy` change does produce a render, so the card updates every ten
minutes all night. The `entity_id:` key is dead configuration; it was left in place rather than
mixed into this fix.

**The hourly bad poll** from the section above. It returns a partial-day total rather than nothing,
and before dawn that partial is only near zero in the first hour or two after midnight. At 05:00 on
2026-10-02 it read 2.0 kWh against a true 2.4. It cannot produce a zero at 6am.

**A sensor that only populates once solar does.** Hourly statistics for `daily_energy` from
2026-09-26 through 2026-10-02 show it climbing from 0.4 to 0.5 kWh in the first hour of every day
and rising steadily from there. There is no day where it waits for sunrise.

### The fix

Every value is now gated on `has_value()`, and a sensor without one renders `n/a` instead of a
number nobody measured:

```jinja
{% set dp = (states(P) | float | round(1) ~ ' kWh') if has_value(P) else 'n/a' %}
```

Net export is gated on both of its inputs. The footer switches too: `as of 7:56 AM` when every
sensor has a value, `no reading since 6:46 AM` from the `last_changed` of the first one that does
not, so an outage announces itself rather than hiding behind a plausible number. The markdown
structure is unchanged, so every UIX selector still matches; the `n/a` cell in the Net export row
carries no `strong` or `em`, so it is uncoloured, which is correct for a value that is not a sign.

Verified by rendering both branches through `POST /api/template` before saving, the second with the
four entity ids swapped for a currently unavailable sensor, and by screenshot at 1920x1080 after
saving. Console showed only the two pre-existing 404s.

### Rejected and deferred

**Holding the last good value in the card.** A markdown card template is stateless, so there is
nowhere to keep it. There is also no second source to fall back on: every `device_class: energy`
sensor on the instance with a cumulative state class is either a Sense device-level trend sensor
from the same coordinator or a per-plug counter. Grid import and export come from Sense alone.

**Four monotonic template sensors.** Deferred at the time, then asked for and built the same day;
see the next section.

## Four held sensors, built 2026-10-02

Four Template Helpers now sit between the Sense trend sensors and the card. Each holds its last
good value through a dropout and refuses to decrease within a day, so neither Sense fault reaches
the display.

| Helper | Source |
| --- | --- |
| `sensor.produced_today` | `sensor.sense_287516_daily_production` |
| `sensor.used_today` | `sensor.sense_287516_daily_energy` |
| `sensor.exported_today` | `sensor.sense_287516_daily_to_grid` |
| `sensor.imported_today` | `sensor.sense_287516_daily_from_grid` |

The state template is the same for all four apart from the source. It is shown wrapped here for
reading; the deployed value is this text on one line, because a line break inside the `if`/`elif`
chain lands in the rendered state.

```jinja
{% set src = 'sensor.sense_287516_daily_production' %}
{% set has = has_value(src) %}
{% set val = states(src) | float(0) %}
{% set reset = state_attr(src, 'last_reset') %}
{% set held = this.state | float(none) %}
{% if not has %}{{ held }}
{% elif held is none or reset is none or as_timestamp(reset) > as_timestamp(this.last_reported) %}{{ val | round(1) }}
{% else %}{{ [held, val] | max | round(1) }}{% endif %}
```

Availability, which is what makes the hold possible:

```jinja
{{ has_value('sensor.sense_287516_daily_production') or is_number(this.state) }}
```

### The day key has to be the source's own `last_reset`

A monotonic clamp needs to know when the day rolls over or it holds yesterday's total forever.
Three candidates, two of them wrong:

**`now().date()` against the helper's own last render.** Wrong, and wrong in a way that latches for
a whole day. Referencing `now()` makes a template re-render every minute, so a tick at 00:01 would
take the reset branch while the Sense sensor still holds yesterday's total: its first poll of the
new day lands somewhere between 00:00:04 and 00:10. The helper would adopt yesterday's figure, mark
itself as having rendered today, and then clamp every real value of the new day below it.

**The source's value dropping.** Indistinguishable from the bad poll, which is the thing being
suppressed.

**`last_reset` on the Sense sensor.** It is set to local midnight and advances daily. Verified
against four days of recorder history, where it moved 09-28 to 09-29 to 09-30 to 10-01 to 10-02,
each at 07:00 UTC, which is 00:00 Phoenix. It also reads `None` during the dropouts, which the
template treats as "do not clamp" rather than "new day".

The comparison is `as_timestamp(reset) > as_timestamp(this.last_reported)`: the source's day began
after the helper last wrote, so whatever the helper is holding belongs to a previous day.
`last_reported` rather than `last_changed`, because `last_reported` advances on every render even
when the value is unchanged, while `last_changed` can sit a day stale on a sensor whose value
legitimately does not move. `exported_today` on an overcast day ends at 0.0 and starts the next at
0.0, and keying on `last_changed` would leave the clamp disabled until the value first moved.

### Three things not to change

**Availability is `has_value(src) or is_number(this.state)`, not `has_value(src)`.** The obvious
availability template takes the helper offline for the whole dropout, which hands the card exactly
the hole this work is closing. The `or` keeps the helper available while it has a value worth
holding and lets it go unavailable only when it has none, which is a cold start.

**`float(none)`, not `float(0)`.** The helper has to be able to tell "no value yet" from "measured
zero"; the `held is none` branch is what adopts the source outright on a cold start. A default of 0
is the same mistake one layer down that put the zeros on the card in the first place.

**No `state_class`.** The Sense sensors carry `state_class: total` and feed the Energy dashboard's
long-term statistics. Giving these helpers one would write a second set of statistics for the same
quantities under new entity ids and offer them in the Energy dashboard's pickers as though they
were another meter. They exist to be displayed, so they carry `device_class: energy`, a unit, and
nothing else.

### Built through the config flow, not YAML

The best-practice default is a Template Helper created through the config flow rather than a
`template:` block: a flow helper is UI-editable and reloads in place. The one thing that would have
forced YAML is `attributes:`, which has no flow field, and an earlier draft wanted one to store the
day key. Keying off `last_reset` and `this.last_reported` removed the need. Note that the flow puts
`availability` inside its `additional_options` section; a flat `availability` at the top of the
payload fails validation.

No built-in helper covers this. `utility_meter` accumulates a meter across cycles rather than
passing a value through, and its answer to a decreasing source is a meter-reset path rather than a
dip-suppression one. `statistics` with a maximum characteristic works over a sliding window rather
than a calendar day, so it would carry yesterday's peak well into today. `filter`'s outlier
rejection cannot tell the midnight reset from a bad poll.

### What the card reads now

The four figures come from the helpers. The `as of` stamp still reads the Sense sensors directly,
because the helpers re-render during a dropout and their own `last_reported` would claim a
freshness that nothing measured. While any Sense sensor has no value the footer reads
`held since 6:46 AM`, taken from its `last_changed`, so the card shows real numbers and says
plainly that they are being held. The `has_value()` gating added earlier stays, now covering only a
cold start.

The card's `entity_id:` key still lists the four Sense sensors. It is inert either way, as the
section above establishes, and it was left alone rather than folded into this change.

### Verified against both real faults within an hour of building them

Every branch of the state template was exercised first by rendering it through `POST /api/template`
with the three source reads replaced by literals and everything from `{% if not has %}` onward left
byte-identical: normal climb, bad poll, dropout, new-day rollover, a stale pre-rollover source, cold
start, a dropout with no held value, and a missing `last_reset`. All eight behaved as designed. The
cold-start case renders the literal string `None`, which is exactly why the availability template
has to carry the `or is_number(this.state)` clause.

That is a test of the logic, not of the wiring, so the helpers were then watched against the live
sensors at 20-second resolution from 08:09 to 09:10 on 2026-10-02. Both faults turned up on their
own:

```
08:36:54           production   src=         4.4  held=         4.4
08:46:56  DROPOUT  production   src= unavailable  held=         4.4
08:46:56  DROPOUT  energy       src= unavailable  held=         5.7
08:46:56  DROPOUT  to_grid      src= unavailable  held=         2.6
08:46:56  DROPOUT  from_grid    src= unavailable  held=         3.8
08:51:58           production   src=         5.3  held=         5.3
08:56:59           production   src=         6.1  held=         6.1
09:02:00  DIP      production   src=         2.3  held=         6.1
09:02:00  DIP      energy       src=         5.3  held=         5.9
09:02:00  DIP      to_grid      src=         0.9  held=         4.1
09:07:01           production   src=         7.1  held=         7.1
```

The :46 dropout and the top-of-hour partial-day poll, one after the other, both absorbed. The last
line is the one that matters almost as much as the DIP line: the clamp released as soon as the
source climbed past the held value, so nothing latches.

The card was screenshotted at 1920x1080 during the live dropout, reading 4.4, 2.6, 5.7, 3.8 and
-1.2 kWh under a footer of `held since 8:46 AM`. The same moment before this work would have shown
five zeros.

Two further checks. The four helpers do not re-render themselves: `last_reported` on all four was
unchanged across a 45-second window with no source update, so reading `this` creates no loop. And
the system log carried no template error from any of them.

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
`last_reported`, so the card states its own freshness instead of leaving a reader to guess. An
earlier version of this paragraph claimed the stamp never advances overnight because nothing is
moving then. That is wrong, and believing it is part of why the zeros above went unexplained: used
and imported climb all night, so the card re-renders roughly every ten minutes until dawn.

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

**Four monotonic template helpers to suppress the hourly bad poll.** Deferred on 2026-09-30 rather
than rejected: pde chose the option with no new helper entities, on the reasoning that it is better
to see how often the glitch actually annoys before adding four entities to suppress it. It annoyed
on 2026-10-02 and the helpers were built; see "Four held sensors" above.

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
