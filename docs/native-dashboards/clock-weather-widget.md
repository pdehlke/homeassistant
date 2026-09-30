# Clock dashboard: the wall-clock weather widget

`dashboard-clock`'s `custom:wall-clock-card` carries a weather widget in the narrow left panel of
its `vertical-1-2` layout. Two things were wrong with it, both fixed live on 2026-09-25: the text
was too small to read from across the office, and the forecast row was labelled a day early,
showing Thursday through Sunday on a Friday. In neither case was the fix the one the card's own
configuration suggests, so the reasoning below matters more than the result.

The installed card is `rkotulan/ha-wall-clock-card` v3.10.0, confirmed from
`hacs/repositories/list` and from the bundle's own console banner. This skill's
[references/lovelace.md](../../.claude/skills/home-assistant/references/lovelace.md) had it at
v3.4.0, which was stale. v3.17.1 was available and not installed, and it changes one of the two
answers below but not the other.

## Part one: the font sizes are capped, and the widget's own fields cannot beat the cap

The weather widget documents two size fields,
[`labelSize` and `valueSize`](https://raw.githubusercontent.com/rkotulan/ha-wall-clock-card/v3.10.0/docs/weather.md),
described as "CSS size for labels/title" and "CSS size for values". In the horizontal layout, which
is what this widget uses, v3.10.0 wraps both of them in a cap before writing them to an inline
style:

| Element | Inline `font-size` in horizontal orientation | Effective ceiling |
| --- | --- | --- |
| `.weather-temp` | `min(valueSize, clamp(1.8rem, 10cqw, 3rem))` | 3rem |
| `.forecast-date`, `.forecast-temp` | `min(labelSize, clamp(0.82rem, 4cqw, 1.4rem))` | 1.4rem |
| `.weather-condition` | `clamp(0.9rem, 3.5cqw, 1.15rem)` | 1.15rem, not configurable at all |
| `.weather-current-copy .weather-title` | `clamp(0.75rem, 3cqw, 1rem)` | 1rem, not configurable at all |

None of this is in the upstream docs at any tag. It was read out of the served bundle.

`cqw` is a container query unit against `ha-weather`'s own `:host`, which declares
`container-type: inline-size`. The widget sits in the left third of a `vertical-1-2` split inside a
`column_span: 2` section, so that container is roughly 300px wide. At that width `10cqw` is 30px
and `4cqw` is 12px, below its own 0.82rem floor. That is why the current temperature read at about
30px and the forecast row at about 13px, and why the forecast row in particular was unreadable at
viewing distance.

The live config already carried the evidence that the documented path had been tried and had
failed: `valueSize: 200rem`. Three thousand two hundred pixels resolves, through that `min()`, to
3rem.

### Rejected alternatives

- **Raise `labelSize` and `valueSize` further.** Cannot work, for the reason above. Recorded here
  because it is the obvious first move and the config's own `200rem` is the artefact of someone
  making it.
- **Switch the widget to `orientation: vertical`,** where v3.10.0 writes `labelSize` and
  `valueSize` straight through with no cap. Rejected because it also restacks the forecast from day
  columns into rows, which is a different widget, not a larger one. It does not escape fixed
  geometry either: `.forecast-date` has a hard `width: 2rem` and `.forecast-temp` takes its width
  from a size preset, so large text in vertical orientation overflows both boxes and would have
  needed a CSS override anyway.
- **Move the widget to the wide right-hand zone,** where a larger `cqw` would let every clamp reach
  its ceiling. Rejected as a layout change that displaces the clock, and it only buys 48px and
  22px, still capped.
- **Smuggle CSS through the config value,** exploiting the fact that `valueSize` is interpolated
  raw into a `style` attribute. Rejected outright. It cannot actually defeat a `min()` from inside
  the `min()`, and a config value crafted to break out of one CSS declaration into another is the
  kind of thing that silently stops working on an upgrade with no error anywhere.
- **Patch the card's JavaScript on the host.** Rejected: HACS owns those files and would overwrite
  it on the next update, silently.

### What shipped

A UIX rule on the card, injected into `ha-weather`'s shadow root:

```yaml
uix:
  style:
    wcc-layout $$ ha-weather $: |
      /* Office wall display: the widget's own labelSize/valueSize are capped by
         min()/clamp() in the card's horizontal weather layout, so the text sizes are
         set here instead. Container-relative so they track the narrow panel's width. */
      .weather-container.horizontal .weather-temp {
        font-size: clamp(2.5rem, 20cqw, 5rem) !important;
        line-height: 1.05 !important;
      }
      .weather-container.horizontal .weather-current-copy .weather-condition {
        font-size: clamp(1.1rem, 6cqw, 2rem) !important;
        white-space: normal !important;
      }
      .weather-container.horizontal .forecast-date,
      .weather-container.horizontal .forecast-temp {
        font-size: clamp(1rem, 10cqw, 2.25rem) !important;
      }
```

Four things about that rule are deliberate.

**`!important` is load-bearing.** Every one of those sizes is an inline `style` attribute written
by the card's own template, and nothing weaker than `!important` beats an inline style.

**The selector uses UIX's `$$` express search rather than the explicit chain.** The real path is
five shadow roots deep: `wall-clock-card` → `ha-card` → `wcc-layout` → `wcc-zone` →
`wcc-weather-widget` → `ha-weather`. Written out in full it would name four of the card's internal
element tags; `wcc-layout $$ ha-weather $` names two, so there is less to break when the card
refactors its internals. `$$` performs a recursive shadow-piercing descent and is confirmed present
in the installed UIX 8.1.0, not only in the 8.4.0 docs. It must sit between two selector steps and
can never start a path, which the implementation enforces by returning nothing.

**Nothing outside the weather widget can be reached by that selector.** `ha-weather` exists only
inside the weather widget, so the clock, the date, and every other card on the dashboard are out of
scope by construction. That was the explicit constraint on this work.

**The sizes are container-relative rather than absolute.** The office display's resolution was never
measured, and the panel is a third of a section whose width depends on how many columns the view
resolves to. Sizing in `cqw` means the text tracks the panel instead of assuming a display. The
ceilings in `rem` only stop it growing absurd on a hypothetically enormous panel.

The numbers were picked against the geometry, not by eye, because there was no way to look. With a
300px panel and four forecast columns: gaps are `clamp(3px, 1.2cqw, 18px)`, so each column is about
72px, and three characters at `10cqw` is about 50px, leaving margin. The current-conditions row has
about 282px of usable width after the card's own `margin-left` arithmetic, spent on a 40px icon, a
three-character temperature at `20cqw` (about 108px), and the condition text. The condition is the
one place that did not fit, because the card sets `white-space: nowrap` on it, so the rule releases
it to wrap onto a second line instead of being clipped by the container's `overflow: hidden`.

**pde has since raised `forecastDays` from 4 to 5 in the card's own editor.** That narrows each
column by about a fifth, to roughly 57px, which is tight against a three-character weekday at
`10cqw`. It reads correctly today. If a long weekday ever looks crowded, `10cqw` is the number to
lower, not the font ceiling.

That editor round-trip also dropped `forecastType: daily`, which had been saved and verified
minutes earlier. The card's own designer rebuilds a widget from the fields its form models and
discards the rest. The key was belt and braces rather than necessary, because the entity reports
`supported_features: 3` and the card's auto resolution tries `daily` first and succeeds, so nothing
regressed. Worth knowing before putting any other unmodelled key on a wall-clock widget: it is the
same hazard as [ADR-0061](../adr/0061-kiosk-mode-lost-on-gui-edit-reapply-dont-prevent.md), one
level down, and on this occasion `kiosk_mode` and both other cards' `uix` blocks came through
untouched.

## Part two: the forecast row started on yesterday

On a Friday the four columns read Thursday, Friday, Saturday, Sunday. The data was today's; the
labels were a day early. The card's direct OpenWeatherMap provider does this:

```js
const o = new Date(1e3 * e.dt).toISOString().split("T")[0];   // "2026-09-25", a UTC date
...
date: new Date(o)                                              // 2026-09-25T00:00:00Z
```

It buckets the 5-day/3-hour list by UTC date, keeps the bucket key as a bare `YYYY-MM-DD` string,
and re-parses that string into a `Date`. A bare date string parses as UTC midnight. The label is
then rendered by `toLocaleDateString(locale, {weekday: "short"})` with no `timeZone` argument, which
formats in the browser's own zone. In Phoenix, UTC-7 with no DST, `2026-09-25T00:00:00Z` is Thursday
at 17:00, so the column says Thu.

Every column is mislabeled, not just the first, and the error is structural rather than a boundary
case: any browser west of UTC sees it, and no browser at or east of UTC does. The card's default
coordinates are Prague, which is why this ships.

There is a second, quieter consequence of the same UTC bucketing. A bucket keyed `2026-09-25` holds
the three-hour slots from 00:00Z to 21:00Z, which locally is 17:00 on the 24th through 14:00 on the
25th. Each day's high and low were therefore drawn from a window straddling two local days. Fixing
only the label would have left that in place.

### Rejected alternatives

- **Correct the label and keep the provider.** Not reachable from configuration, and it would have
  left the straddled temperature windows above.
- **Patch the card's JavaScript.** Same objection as in part one: HACS overwrites it.
- **Upgrade the card and wait for an upstream fix.** Checked rather than assumed.
  [`openweathermap-provider.ts` at v3.17.1](https://raw.githubusercontent.com/rkotulan/ha-wall-clock-card/v3.17.1/src/weather-providers/openweathermap-provider.ts)
  still does `date.toISOString().split('T')[0]` at line 78 and `new Date(dateString)` at line 107.
  The latest available version has the same bug, so upgrading is not a fix for this half.

### What shipped: the card's Home Assistant provider

```yaml
- type: weather
  id: weather
  provider: homeassistant
  providerConfig:
    entityId: weather.openweathermap
  displayMode: both
  forecastDays: 5
  title: ' '
  showTitle: false
  iconSet: wall-clock
  orientation: horizontal
  labelSize: 2.25rem
  valueSize: 5rem
```

The card's other weather provider calls `weather.get_forecasts` and reads `datetime` off each entry
with `new Date(entry.datetime)`. There is no bucketing in the card at all, because Home Assistant
has already done it in `America/Phoenix`, and no bare date string to misparse. The values come back
stamped at local midday:

```
weather.openweathermap  daily
  2026-09-25T19:00:00+00:00  hi 95   lo 66  sunny     <- today, 12:00 MST
  2026-09-26T19:00:00+00:00  hi 100  lo 74  sunny
  2026-09-27T19:00:00+00:00  hi 93   lo 74  cloudy
  2026-09-28T19:00:00+00:00  hi 92   lo 70  sunny
```

A timestamp at local midday cannot render as the wrong weekday in any zone within twelve hours of
local, which is what makes this immune to the class of bug above rather than merely luckier about
it. Upstream calls this "the recommended provider" for unrelated reasons.

**`weather.openweathermap` was chosen over `weather.forecast_home`,** both of which are on the
instance with daily support, so that the numbers stay continuous with the source the widget was
already reading. The two disagree by several degrees: on the afternoon of the switch they gave
today's high as 95 and 98.

Five things came along with the switch, all of them improvements, none of them requested:

- The OpenWeatherMap API key left the dashboard config entirely. It had been stored in plaintext in
  the Lovelace config, readable by any logged-in user, which is simply how that provider works. It
  remains in the OpenWeatherMap integration's own config entry, where it belongs. It was also
  exposed in the session transcript while diagnosing this, so it is worth rotating at
  OpenWeatherMap and updating only the integration.
- The widget now takes live push updates over `weather/subscribe_forecast` instead of re-polling
  OpenWeatherMap directly on an interval. `updateInterval` was dropped as meaningless on this path.
- The daily lows are the forecast's own `templow` rather than the minimum across whatever
  three-hour slots landed inside a UTC day.
- The widget became clickable through to the entity's more-info dialog, because the provider
  returns an `entityId` and the card gates `.clickable` on that.
- The condition text is Home Assistant's localized condition, "Sunny", rather than
  OpenWeatherMap's raw description, "clear sky". Confirmed to read correctly, along with the
  `wall-clock` icon set's mapping onto Home Assistant's condition keys, which is a different
  mapping from the one the direct provider used.

## Verification

The font rule and the provider switch were each saved by a purpose-built script that reads the live
config, writes a timestamped backup, refuses to proceed unless it matches exactly one
`custom:wall-clock-card` and exactly one weather widget inside it, patches those in place, saves,
and reads the result back. The provider script additionally refuses to run if the provider is not
still `openweathermap`, so it cannot be applied twice. Read-back confirmed on both saves that the
injected CSS round-tripped byte-identical, and that the root `kiosk_mode` block survived the
whole-config write. The second save also confirmed that no `apiKey` string remained anywhere in the
dashboard and that the font rule was still in place.

Playwright is not installed on this machine, so **not one pixel of either change was checked by an
agent.** Everything above about the mechanism was established by reading the served bundle, the
upstream sources at two tags, and the live `weather.get_forecasts` response. pde confirmed both
results on the office wall display: the fonts read correctly at distance, and the forecast row now
starts on today with the condition text and icons correct.

## Operational notes

Writes to this dashboard are refused by Claude Code's auto-mode classifier, the same way Crestron
join presses are, while reads go through. Both saves here were run by pde with a `!` prefix. Reads
of the Lovelace config need `uv run --quiet --with aiohttp`, because `aiohttp` is not in this
machine's system Python; see
[references/api-access.md](../../.claude/skills/home-assistant/references/api-access.md).

## If the card is ever upgraded

v3.17.1 changes the answer to part one and not to part two. Its cap became conditional:

```js
const customValueSize = this.size === Size.Custom && !!this.valueSize?.trim();
...
font-size: ${horizontal && !customValueSize
    ? `min(${valueSize}, clamp(1.8rem, 10cqw, 3rem))`
    : valueSize};
```

Setting either size field puts the widget in `Size.Custom`, so on v3.17.1 an explicit `labelSize`
or `valueSize` bypasses the cap and applies directly, and the condition and title honour
`labelSize` too. That is exactly what the UIX rule works around. So on an upgrade, delete the
`uix:` block from this card and let `labelSize: 2.25rem` and `valueSize: 5rem`, already in the
config and already matching the rule's own ceilings, do the work. Leaving both in place would not
look broken, because the `!important` CSS would keep winning, which is precisely why it would go
unnoticed.

Two upgrade hazards in the other direction. The rule depends on the internal class names
`.weather-container.horizontal`, `.weather-temp`, `.weather-current-copy`, `.weather-condition`,
`.forecast-date` and `.forecast-temp`, and on the element tags `wcc-layout` and `ha-weather`. All
six classes and both tags still exist at v3.17.1, but if any of them is renamed the rule stops
matching and the fonts revert to their capped sizes with no error logged anywhere. And the rule is
written for the daily horizontal layout specifically; an hourly forecast renders a `.hourly`
variant that these sizes were never checked against.
