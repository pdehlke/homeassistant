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

## Fixed 2026-08-15: duplicate summary row hidden with UIX

Filed as [#5](https://github.com/pdehlke/homeassistant/issues/5), closed the same day. The wart
above stands as the original build note; this section records the fix on top of it rather than
rewriting it away.

Confirmed live via Playwright before writing any selector, per the issue's own requirement: each
`more-info-card`'s own shadow root (no nested shadow boundary to pierce) contains

```html
<ha-card>
  <div class="card-content">
    <state-card-content></state-card-content>
    <more-info-content></more-info-content>
  </div>
</ha-card>
```

`state-card-content` is the whole redundant block (icon, entity name, hvac-action text, and the
`Currently: X / Y` line); `more-info-content` is everything else (current temperature/humidity
readout, dial, +/- buttons, hvac-mode icon toggles, Mode/Preset/Fan chip row). Hiding
`state-card-content` outright, rather than trying to isolate just the literally-duplicated
`Currently:` half, was a deliberate choice: the row also carries the hvac-action word ("Idle") and
the preset's numeric range ("62-78°F"), neither shown elsewhere on the card, but the issue asked
for the whole row gone and the entity name is already redundant with the card's own `title`.

Verified live with a temporary unsaved DOM style injection before touching the saved config, then
applied for real with a `uix` key added to each card, flat-string form since the target is in the
card's own top-level shadow root (no `$`-piercing selector needed, unlike the FullCalendar fix
elsewhere in this repo):

```json
{
  "type": "custom:more-info-card",
  "entity": "climate.casasolar_south_zone_1",
  "title": "Main House",
  "theme": "Liquid Glass",
  "uix": {
    "style": "state-card-content { display: none !important; }"
  }
}
```

Same `uix` block added to the North card (`climate.casasolar_north_zone_1`, "Office Wing"), no
`theme` key, matching its pre-existing asymmetry with South. Applied with `scripts/apply-card.py`,
one save per card, matched on `type: custom:more-info-card` plus `entity`, dry-run before each
real save.

Confirmed by screenshot: both cards keep current temperature, current humidity, the dial, +/-
buttons, hvac-mode icon toggles, and the Mode/Preset/Fan chip row, with the redundant row gone and
each card correspondingly shorter. Spot-checked the `dashboard-office` calendar card (the
FullCalendar `$`-piercing UIX fix recorded in [references/lovelace.md](../../.claude/skills/home-assistant/references/lovelace.md)) on the same page load; its
tinted background was still applying, so this change did not destabilize UIX elsewhere on the
dashboard. The only browser console errors on reload were the pre-existing duplicate
`rss-news-card` registration and its related 404, both already on record as unrelated.
