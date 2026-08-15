# Dashboard header card

The date, time and weather banner that sits above the content on the domain dashboards, and the two
undocumented Lovelace behaviours that constrain where it can go and how it can be styled.

Established 2026-08-04, revised and extended to a second dashboard 2026-08-05, on Home Assistant
2026.7.4.

## What it is

A view-level `header`, not a card in the view body. It is a `horizontal-stack` holding a stacked
clock and date on the left and a current-conditions weather card on the right:

```yaml
header:
  card:
    type: horizontal-stack
    cards:
      - type: vertical-stack
        cards:
          - type: clock
            clock_style: digital
            time_format: "12"
            show_seconds: false
            clock_size: medium
            uix:
              style: |
                ha-card { height: 56px !important; }
                .time-wrapper.size-medium { padding: 6px 8px !important; height: calc(100% - 12px) !important; }
          - type: markdown
            content: "{{ now().strftime('%B %-d, %Y') }}"
            uix:
              style: |
                ha-markdown { padding: 5px 8px !important; font-size: 12px; }
      - type: weather-forecast
        entity: weather.openweathermap
        show_current: true
        show_forecast: false
```

The markdown card's `now()` template re-renders on its own each minute, so the date needs no helper
entity and no `time_date` integration.

## The 2026-08-05 layout change

The original arrangement put the date in the top slot and the clock underneath. Measured, that was a
56px date card above a 31px clock card, in a 95px stack. The two were swapped so the time reads
first, at the sizes the slots already had: the clock now fills the 56px top slot and the date sits in
the 31px slot below it.

Keeping the slot geometry fixed rather than letting it follow the cards was the point of the
exercise. The stack is still 95px tall and the area grid below it still starts at the same offset, so
nothing else on the page moved.

That required changing sizes as well as order. A card's height here is intrinsic to the card, not a
property of the position it sits in, so simply reordering the two would have carried the tall box
down with the date and left the time as the smaller of the two elements. Instead:

- The clock moved from its unset default of `small` to `clock_size: medium`, which renders the digits
  at 42px. `clock_size` accepts only `small`, `medium` and `large`, with nothing in between, so the
  56px box is then imposed separately.
  See [the clock card documentation](https://www.home-assistant.io/dashboards/clock/).
- The date's markdown card dropped to 12px text with 5px vertical padding, which lands it at exactly
  the 31px the clock used to occupy.

Two alternatives were rejected. A plain reorder, leaving both cards' styling alone, keeps the stack
at 95px and so moves nothing below it, but it inverts the visual emphasis by leaving the time
rendered smaller than the date. Setting `text_only: true` on the markdown
card is the documented way to shrink it, but it
[removes the border, background and padding](https://www.home-assistant.io/dashboards/markdown/),
so the thin slot would have stopped looking like a card at all while its neighbour still did.

## Two behaviours that are not documented

### A view `header` only renders on `sections` views

A `masonry` view accepts a `header` key, stores it without complaint, and never draws it. There is no
error, no repair issue and no hint in the config that anything is wrong. Reading the config back
shows the header exactly as written.

This was established on 2026-08-05 by saving the header onto the Lennox Home dashboard, which was a
masonry view, and finding no clock card anywhere in the rendered DOM. The
[view documentation](https://www.home-assistant.io/dashboards/views/) does not mention the header
option at all, so there is nothing to read that would have predicted it.

The practical consequence is that adding this header to a dashboard is not a purely additive change.
It requires the target view to be a `sections` view first.

A strategy view is the exception that made the Lights dashboard work. Its config type does not
include a `header` field, but adding one anyway renders, because
[`expandLovelaceConfigStrategies`](https://github.com/home-assistant/frontend/blob/dev/src/panels/lovelace/strategies/get-strategy.ts)
spreads the stored view config first and overlays the strategy's generated output on top. The
strategy does not set `header` itself, so the stored one survives the merge. That is an emergent
property of the current merge order rather than a supported combination, and a future frontend
rewrite could silently drop it.

### UIX loses ties against a card's own stylesheet

`ha-card { height: 56px; }` on the clock card was injected correctly by UIX and had no effect. The rule was
visible in the card's shadow root and the computed height was still 67.59px.

The cause is cascade order. `hui-clock-card` sets `ha-card { height: 100%; }` in its own stylesheet,
which the frontend attaches through `adoptedStyleSheets`, while UIX injects a `<style>` element
into the same shadow root. The CSSOM specification defines a shadow root's
[final CSS style sheets](https://drafts.csswg.org/cssom/#dom-documentorshadowroot-adoptedstylesheets)
as the tree-order sheets followed by the contents of `adoptedStyleSheets`, so the component's own
rule comes last and wins every tie. Equal specificity is not enough. Anything that collides with a
card's built-in rules needs `!important`.

The same applies to the padding override, because `.time-wrapper.size-medium` carries a `padding` and
a `height` from the same stylesheet. The default medium padding of 16px would have made the content
box too short once the card was pinned to 56px, which is why both properties are overridden together.

This is worth remembering because the failure mode is silent and can look like UIX is not working at
all. Check the computed style and the cascade before changing the rule.

## Where the header is used

| Dashboard | View | View type | How the header got there |
| :--- | :--- | :--- | :--- |
| Lights | `lights` | Strategy (`areas-overview`, generates sections) | Survives the strategy merge |
| Lennox Home | `lennox-home` | `sections` | View converted from `masonry` on 2026-08-05 |
| Alarm System | `alarm-system` | `sections` | View converted from `masonry` on 2026-08-05 |
| A/V | `av` | `sections` | Seeded by hand before generating, on 2026-08-05 |

The Lights and A/V headers are preserved by `rebuild-domain-dashboard.py`, which copies the live one
verbatim and refuses to save when there is none. That refusal has an ordering consequence worth
knowing: the generator never creates a header, so a brand new domain dashboard has to be created and
seeded with a view carrying the header *before* the generator will run against it at all.

The Lennox Home and Alarm System dashboards are hand-authored and have no generator, so their copies
are maintained by hand and will drift if the shared header changes.

An empty `sections` view still renders the header. The Alarm System dashboard has no content at all
and shows the banner alone. Its header is narrower than the others, 500px against 700px, because with
no sections there is no column layout for it to size against; it will widen when content lands.

## The Lennox Home conversion

Converting that view from `masonry` to `sections` was the price of the header. It was done in the way
that changed the least: each of the two existing top-level `vertical-stack` cards was moved into its
own grid section, with the stacks' contents untouched. Two sections lay out side by side, which
reproduces what masonry was doing at a desktop width. The columns measured 487px after the change
against 492px before.

The alternative was to leave the view as masonry and add the same card as the first card in the body.
That was rejected because masonry places each card in a single column, so the header would have read
as another card at the top left rather than as a banner spanning the view, and it would have pushed
whichever thermostat stack shared its column out of alignment with the other one.

## What was verified

Confirmed on 2026-08-05 by measuring the rendered DOM and screenshotting, not by reading the config
back:

- On the Lights dashboard the clock renders 56px tall at the top of the stack and the date 31px below
  it, in a 95px stack, matching the pre-change geometry exactly.
- The 42px digits do not overflow the shortened card, at both 1280px and 390px viewport widths.
- On the Lennox Home dashboard the header renders with identical geometry, the two thermostat columns
  survived the conversion, and the lower entity cards are unaffected.
- At 390px the sections view collapses to a single column and the header still fits.

## Related

- [dashboard-navigation-model.md](dashboard-navigation-model.md) for the three-level dashboard
  hierarchy this header sits on top of, and for the generator that preserves it.
- [lennoxs30-integration.md](../lennox-climate/lennoxs30-integration.md) for the thermostats the Lennox Home dashboard
  displays.
- [homeii-music-flow.md](../music-assistant/homeii-music-flow.md) for another case where the view type, rather than the
  card, was the thing that had to change.
