# Office dashboard: thermostat cards replaced with the more-info overlay

`dashboard-office`'s Main House and Office Wing `thermostat` cards were replaced with cards that
render the same content as the more-info dialog you get by clicking the small icon in a
`thermostat` card's own top-right corner, inline on the dashboard instead of behind a click. Built
2026-08-14 on Home Assistant 2026.8.1.

## What the top-right icon actually opens

The `thermostat` card's top-right icon is HA's standard "show more information" trigger. Clicking
it opens the climate entity's more-info dialog: current temperature and humidity readouts side by
side, the round dual-handle setpoint dial, +/- buttons, hvac-mode icon toggles, and a row of
Mode/Preset/Fan mode chips. That is materially more information than the bare `thermostat` card
shows (dial only, no humidity, no preset/fan chips), which is what made it worth pulling onto the
dashboard directly rather than leaving it a click away on a kiosk display nobody taps casually.

## Why a custom card was necessary

Home Assistant has no built-in card that renders more-info content inline. `tile` card features get
partway there for some domains but can't reproduce the dial-plus-chips layout together. Confirmed
by web search before spending time on a native approximation: the same question has come up on the
HA community forum with the same answer both times (embedding a more-info dialog permanently on a
dashboard, and defaulting a climate card to more-info view) and the only working answer in either
thread was a custom card, `thomasloven/lovelace-more-info-card`.

An approximation built from native cards was the rejected alternative: no new dependency, but no
combination of `tile`, `thermostat`, or `entities` cards produces the dial and the chip row
together, so it would have been a visually different result from what was actually asked for
("that overlay view"), not a lighter version of the same thing.

## Install

`thomasloven/lovelace-more-info-card` was already present in HACS's default store on this instance
(no custom repository needed), id `180528950`, 211 stars, last updated 2023-10-17. pde installed it
by hand through the HACS UI rather than any programmatic call, the same path every other HACS
plugin here has gone in by (see the mini-media-player install note in
[office-now-playing-footer.md](office-now-playing-footer.md)). Confirmed installed
(`installed_version: c0a9c94`) and self-registered as a Lovelace resource
(`/hacsfiles/lovelace-more-info-card/more-info-card.js`) via `hacs/repositories/list` and
`lovelace/resources` over WebSocket.

## Config

Both `thermostat` cards were swapped in place with `scripts/apply-card.py`, matched on
`type: thermostat` plus `entity` to hit exactly one card per save:

```json
{
  "type": "custom:more-info-card",
  "entity": "climate.casasolar_south_zone_1",
  "title": "Main House",
  "theme": "Liquid Glass"
}
```

```json
{
  "type": "custom:more-info-card",
  "entity": "climate.casasolar_north_zone_1",
  "title": "Office Wing"
}
```

The South card's pre-existing `theme: "Liquid Glass"` (not present on the North card, an
inconsistency that predates this change) was carried over unchanged rather than reconciled; the
`theme` key is handled generically by the dashboard host for any card type, custom cards included,
so it applies the same way it did on the old `thermostat` card.

## What it looks like, and one wart

Confirmed via Playwright screenshot: both cards render the full more-info content inline,
current temperature, current humidity, the dial, +/- buttons, mode icon toggles, and the
Mode/Preset/Fan mode chip row, matching the dialog exactly. Neither card set a `grid_options`
before or after this change, so each grows to its natural height (noticeably taller than the old
`thermostat` card, roughly 600px) rather than being clipped or overlapping the section below;
confirmed by a full-page screenshot showing both new cards complete and the Weather/News section
underneath undisturbed.

One difference from the popup dialog: with no dialog chrome wrapping it, `more-info-card` renders
its own summary row above the dial (`icon, entity name, "Idle (Heat/Cool) - summer 62°F-78°F" /
"Currently: 78°F / 49%"`), duplicating the current-temperature/current-humidity numbers shown again
just below. The popup version doesn't show this line; it's `ha-dialog`'s own header framing that
takes its place there. The community thread that pointed at this card also documents the fix,
hiding `state-card-content` via CSS. It was not applied here. If this wart is revisited, use UIX,
not the deprecated card-mod mechanism, and verify the result from computed style.
