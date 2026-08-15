# Office dashboard: larger event text on Upcoming Events

`dashboard-office`'s "Upcoming Events" card (`custom:atomic-calendar-revive`) had its event rows
(date, title, time, location) bumped from 14px to 18px, leaving the card's own header text
("Upcoming Events," 24px) unchanged. Built 2026-08-15 on Home Assistant 2026.8.1.

## No built-in lever for this

Read `totaldebug/atomic-calendar-revive`'s full config reference (`main.html`, `event.html`,
`styling.html`) before touching anything. There is no dedicated font-size option for event rows.
`compactMode` exists but only shrinks. The only font-size-shaped custom properties are
`--cal-description-size` and `--cal-location-link-size`, both relative percentages scoped to
description text and location hyperlinks specifically, neither of which covers the title/date/time
text that makes up most of what's on screen. Same shape of problem as the clock card
([office-clock-card.md](office-clock-card.md)): already at whatever ceiling the card's own config
exposes, just a lower one this time (no size option at all, rather than a capped enum).

## UIX, targeting a class found by reading the live shadow DOM, not guessed

Per this instance's Lovelace styling policy, `card-mod` is out; this needed a `uix: style:` rule
the same way [office-thermostat-overlay-cards.md](office-thermostat-overlay-cards.md) used one for
`more-info-card`. Rather than guess a selector from the published docs (which only document CSS
custom properties, not the DOM structure they attach to), read the card's actual computed styles
and stylesheet live via Playwright, piercing its shadow root:

- Every event-row element (`.event-left`, `.event-date-day`, `.event-right`, `.event-title`,
  `.event-location`) measured at exactly 14px, and none of them carry their own `font-size` rule in
  the card's stylesheet, only layout properties (`display`, `grid-column`, `color`). That means
  14px is inherited from one shared ancestor, not set per element.
- `.single-event-container`, the direct wrapper around each event row, is that ancestor. Setting
  its `font-size` cascades to every child that doesn't override it, which is all of them.
- The header (`"Upcoming Events"`, class `header-name`) has its own explicit rule,
  `font-size: var(--ha-card-header-font-size, 24px)`, unaffected by anything set on
  `.single-event-container`. Confirms the ask ("just the events, not necessarily the title") falls
  out of the DOM structure for free rather than needing separate suppression.

```yaml
uix:
  style: ".single-event-container { font-size: 18px !important; }"
```

`!important` needed to beat the card's own stylesheet, same as every other UIX override on this
instance.

Added via a small script (`add_uix_style.py`, written ad hoc for this change; not promoted into
`scripts/` since, unlike the kiosk_mode reapply case in
[office-kiosk-mode.md](office-kiosk-mode.md), there's no expectation this exact operation
recurs) that matches a card by `type` + `name` rather than `type` + `entity` the way
`apply-card.py` does, since `atomic-calendar-revive` cards use a plural `entities` list and
`dashboard-office` has two cards of this type (this one, and an undecorated month-grid calendar
below it with no `name` set, so matching on `name: "Upcoming Events"` picks the right one
unambiguously).

## Sizing

18px chosen by eye against a live screenshot at a 1920x1080 viewport: a clear step up from 14px
without approaching the 24px header, preserving the header-is-biggest hierarchy, and without
wrapping the longest visible content (an event location address) into more lines than fit
comfortably in the card's fixed-width column.

## Verification

Confirmed live via `playwright-cli`, as the `Pete` admin account, same session and token-safety
pattern as [office-clock-card.md](office-clock-card.md). Screenshot showed all four event fields
(date, title, time, location) rendered at the larger size, header unchanged, no clipping against
the calendar grid card stacked below it in the same section. Not verified as the `office` user
itself, same credential gap noted in [office-kiosk-mode.md](office-kiosk-mode.md).
