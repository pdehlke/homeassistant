# Clock dashboard: a Home Status summary card

Added a "Home Status" markdown card to `dashboard-clock`, below the existing "Current Solar
Production" gauge, as a four-line vertical list: `Lights: <n> On`, `HVAC: <n> On`,
`Media: <now playing|Idle>`, `EV: <Connected|Disconnected|Charging>`. Built 2026-09-07 on Home
Assistant 2026.8.1.

## Recovering from a mangled card, same day

pde edited the card through the Lovelace UI shortly after it was built and, going by the resulting
config, pasted the card's own YAML (`type`/`title`/`content`) into the card's `content` field
rather than editing the fields directly. The saved card ended up as `{type: markdown, content:
"type: markdown\ntitle: Home Status\ncontent: ..."}` with no top-level `title` or `theme` left at
all, rendering the raw YAML as literal text instead of evaluating the template. Fixed by rebuilding
the card from the original design's exact fields (below) and re-saving, verified against
`/api/template` before the save and a live screenshot after.

## Why a markdown card

The four lines pull from four unrelated domains with no single entity that already reports all of
them together. A `markdown` card's `content:` field supports a Jinja template, so one card can
combine four independent template expressions without a new template helper entity. `theme: Liquid
Glass` was added to match the three sibling cards already in the same section (`energy-usage-graph`,
`energy-grid-neutrality-gauge`, and the solar production `gauge`), all of which set that theme
per-card rather than relying on the viewing user's own theme.

## Three design decisions, each confirmed with pde rather than guessed

**Lights.** Reused `sensor.homie_lights_status` rather than re-deriving a light count from scratch.
That sensor already carries the double-counting fix for HA light groups (see this repo's
[homie-dashboard-install-plan.md](../homie-dashboard/homie-dashboard-install-plan.md), 2026-09-06
checkpoint), so parsing its text (`"All Off"` → `0`, `"<n> On"` → `<n>`) keeps this card in sync
with any future change to that counting logic instead of duplicating it.

**HVAC.** The two Lennox zones (`climate.casasolar_north_zone_1`, `climate.casasolar_south_zone_1`)
distinguish thermostat mode (`hvac_mode`, e.g. `heat_cool`) from what's actually running
(`hvac_action`, e.g. `cooling` or `idle`). At the time this was built, both zones were in
`heat_cool` mode, but only one had `hvac_action: cooling`; the other was `idle`. Two options:

- **Actively conditioning (chosen).** Count a zone as On only when `hvac_action` is `heating` or
  `cooling`. Reflects what's actually running, not just enabled.
- **Thermostat enabled (rejected).** Count a zone as On whenever its mode isn't `off`, regardless
  of whether it's currently running. Rejected because both zones are in `heat_cool` essentially all
  the time on this system, which would make the count nearly always read `2` and say nothing useful
  about current activity.

**Media.** Of the 11 `media_player` entities on this instance, several are stale duplicates that
read `unavailable` (`gymnasium`, `gym_2`, `carol`). At build time, Gym was `paused` on an 80s/90s
radio station; everything else was `idle`, `off`, or `unavailable`. Two options:

- **Playing only (chosen).** Only a player in state `playing` counts as "now playing"; paused,
  idle, off, and unavailable all read as `Idle`. No exclusion list needed for the stale duplicates,
  since `unavailable` never matches `playing` anyway.
- **Playing or paused (rejected).** A paused player would also show its title. Rejected because a
  paused radio station sitting untouched for hours isn't what "now playing" is meant to convey.

**EV.** The OpenEVSE integration's own `sensor.garage_ev_charger_charging_status` read the raw
value `active` at build time. Home Assistant's published OpenEVSE docs list `Not connected` /
`Connected` / `Charging` / `Sleeping` as that sensor's enum, and the entity registry confirmed
`translation_key: status`, but the entity's `device_class` was plain (not `enum`) and its value
didn't match any of the documented options, meaning this installed version isn't normalizing the
charger's raw status string the way current upstream code does. Two options:

- **Connected sensor + charging power (chosen).** `binary_sensor.garage_ev_charger_vehicle_connected`
  gives `Disconnected` when off; otherwise `sensor.garage_ev_charger_charging_power` above zero
  gives `Charging`, else `Connected`. Both source entities have unambiguous semantics regardless of
  what `charging_status` happens to say.
- **Pass through `charging_status` text (rejected).** Would have needed an ad hoc mapping anyway,
  since `active` isn't one of the three requested states, and there's no confirmed table from raw
  device state to that text on this integration version.

## Configuration used

```yaml
type: markdown
title: Home Status
theme: Liquid Glass
content: >
  {% set lights_state = states('sensor.homie_lights_status') %}
  {% set lights_n = 0 if lights_state == 'All Off' else (lights_state.split(' ')[0] | int) %}
  {% set hvac_n = states.climate | selectattr('attributes.hvac_action', 'in', ['heating', 'cooling']) | list | count %}
  {% set playing = states.media_player | selectattr('state', 'eq', 'playing') | list %}
  {% set media_text = playing[0].attributes.media_title if playing else 'Idle' %}
  {% set ev_connected = is_state('binary_sensor.garage_ev_charger_vehicle_connected', 'on') %}
  {% set ev_power = states('sensor.garage_ev_charger_charging_power') | float(0) %}
  {% set ev_text = 'Disconnected' if not ev_connected else ('Charging' if ev_power > 0 else 'Connected') %}
  - Lights: {{ lights_n }} On
  - HVAC: {{ hvac_n }} On
  - Media: {{ media_text }}
  - EV: {{ ev_text }}
```

`states.climate` and the `selectattr`/`map` chains over `states.media_player` are domain-wide
reads, so Home Assistant's template render-info tracking registers listeners across the whole
domain rather than a fixed entity list; the card re-renders on any climate or media_player state
change, not just the two Lennox zones or the players that happened to be active when this was
built. Same structural reasoning as the light-group fix in
[homie-dashboard-install-plan.md](../homie-dashboard/homie-dashboard-install-plan.md): avoid a
hardcoded entity list where a domain-wide filter expresses the same intent and won't need editing
if a new climate zone or media player is added later.

Applied by reading `dashboard-clock`'s config, appending this card to the section already holding
`energy-usage-graph` / `energy-grid-neutrality-gauge` / the solar gauge, and saving via
`scripts/replace_section.py` (index 1, dry-run first). The Jinja template was rendered against live
state via `POST /api/template` before saving, matching the verification method already used for
`sensor.homie_lights_status`.

## Title and content text sized up 25%, same day

pde asked for both the card's title and its body text 25% larger, after the mangled-card fix above.

Measured the actual rendered sizes first rather than guessing a starting point: walking the live
card's shadow DOM (`hui-markdown-card` → its own shadow root → `ha-card`'s separate nested shadow
root for the title, `ha-markdown` for the body) gave a baseline of 24px/48px line-height for the
`h1.card-header` title and 14px/22.4px for the body text and its list items. 25% larger is
30px/17.5px.

card-mod is retired on this instance, so the increase has to go through UIX. Two approaches were
considered for reaching the title, which renders inside `ha-card`'s own nested shadow root, one
level deeper than the markdown card's own:

- **Pierce into `ha-card`'s shadow root with UIX's `$` selector (rejected as the first attempt).**
  This project's own precedent for `$`-piercing (the FullCalendar fix in
  [references/lovelace.md](../../.claude/skills/home-assistant/references/lovelace.md)) uses a
  bare CSS block as the value for a `"<selector>$"` key, but external UIX documentation describes a
  different nested-dictionary form for the same feature. Rather than trust either against a config
  that renders wrong silently, this was set aside for the option below, which needed no piercing at
  all.
- **Set `--ha-card-header-font-size` on the card's own host, unpierced (chosen).** Empirically
  confirmed live, before touching the saved config, that setting this custom property on the
  `hui-markdown-card` host element changes the nested `h1.card-header`'s computed font-size, because
  CSS custom properties inherit through shadow boundaries even when ordinary selectors can't cross
  them. Also confirmed both the title's line-height (48px) and the body's list-item line-height
  (22.4px) are relative to their own font-size (exactly 2x and 1.6x respectively) and recompute
  automatically, so neither needed a separate override.

Final `uix.style` (a single unpierced string, the same form already used for the
`atomic-calendar-revive` card's `.single-event-container` override elsewhere on this dashboard):

```yaml
uix:
  style: |
    :host {
      --ha-card-header-font-size: 30px;
    }
    ha-markdown {
      font-size: 17.5px;
    }
```

Verified after saving by re-measuring the live shadow DOM rather than trusting the config alone:
title rendered at 30px/60px, body and its `<li>` elements at 17.5px/28px, both exactly the
25%-larger target with line-height scaling proportionally as predicted.

## A fifth status item and a two-column layout, 2026-09-07

Between the font-size change above and this one, pde moved the card to the top of its column and
increased the content font size further by hand through the Lovelace UI, to 20.5px; those edits are
reflected in the current live config but weren't made through this skill's scripts, so there's no
separate record of exactly when. He then asked for a fifth item, `Vacuum:`, mirroring Homie
Dashboard's own "Robot" status grid item on its Overview A/B screens, and for the card to become a
header plus two columns: Lights/HVAC/Media on the left, EV/Vacuum on the right.

**What "mirroring" Robot means.** Read directly from the Homie Dashboard fork's `dist/config.js`
and `dist/homie-dashboard.html`: the "Robot" grid item has no `onValue`/`offValue` pair and no
`unit`, so `_refreshStatGrid()` takes its plain-passthrough branch and displays
`sensor.homie_robot_status`'s raw state string verbatim, with no threshold, mapping, icon, or color
logic at all. Reproducing it faithfully means exactly one thing: template that same sensor directly,
`{{ states('sensor.homie_robot_status') }}`, the same pattern already used for `sensor.
homie_lights_status`.

**Two-column layout: raw HTML considered and rejected.** The obvious approach was wrapping the two
groups in `<div>`s with a class, then styling that class via UIX. Rejected without trying it live:
Home Assistant's markdown card sanitizes rendered HTML through the `xss` library's tag/attribute
whitelist (`markdown-worker.ts` in `home-assistant/frontend`), not DOMPurify, and confirming whether
`div`, `class`, or `style` survive that whitelist would have meant the same kind of guesswork this
project's own rules argue against. A structural alternative avoided the question entirely: two
separate markdown bullet lists, split by a `---` thematic break, render as two sibling `<ul>`
elements plus an `<hr>`, confirmed live by walking the shadow DOM. `<ul>`/`<li>`/`<hr>` were already
known to render (the four-item version already used `<li>`), so nothing new needed sanitizer
verification at all.

```
- Lights: {{ lights_n }} On
- HVAC: {{ hvac_n }} On
- Media: {{ media_text }}

---

- EV: {{ ev_text }}
- Vacuum: {{ vacuum_text }}
```

**The layout itself needed real shadow-piercing, resolved empirically.** The two `<ul>`s' direct
parent, `<ha-markdown-element>`, lives inside `ha-markdown`'s own separate internal shadow root, one
level deeper than where the font-size fix above could reach by relying on inherited properties.
`display: flex` doesn't inherit, so there was no equivalent shortcut this time; reaching it requires
UIX's shadow-piercing selector syntax, the exact form of which this project's own docs and an
external UIX documentation fetch had already disagreed about (see the font-size section above).
Tested directly on the live card rather than trusting either source: `uix.style` as an object with a
`"."` key for the unpierced base rules and a `"<selector>$"` key for pierced ones, each holding a
plain CSS-block string, works exactly as this project's own prior `ha-full-calendar$` example
implied.

```yaml
uix:
  style:
    ".": |
      :host {
        --ha-card-header-font-size: 30px;
      }
      ha-markdown {
        font-size: 20.5px;
      }
    "ha-markdown$": |
      ha-markdown-element {
        display: flex;
        gap: 32px;
        align-items: flex-start;
      }
      hr {
        display: none;
      }
```

Verified live in three stages before touching the real content: first that setting `display: flex`
directly on the located `<ha-markdown-element>` via an inline-style probe actually produced the
side-by-side layout, then that the same effect landed through the `uix.style` object form once
deployed, then a final screenshot with the real Jinja content and all five items showing correct
live values (`Lights: 0 On`, `HVAC: 2 On`, `Media: Idle`, `EV: Charging`, `Vacuum: Charging`,
the last two agreeing since both read real activity at the same moment). Browser console showed
only the same two pre-existing errors already documented below; nothing new from this change.

## Initial verification

Confirmed live via `playwright-cli` as the `Pete` admin account (storage-state file built from
`$HA_TOKEN`, loaded and deleted per this skill's token-safety pattern). Screenshot after save shows
the card immediately below "Current Solar Production," rendering as a bulleted four-line list with
the same translucent Liquid Glass panel styling as its neighbors:

```
Lights: 0 On
HVAC: 2 On
Media: Idle
EV: Disconnected
```

That matched live state at the time (all lights off; both Lennox zones had started cooling by the
time of the final check, which is why HVAC read `2`, not the `1` seen earlier in the same session
when only one zone was active; no media playing; no vehicle connected to the garage charger). Browser
console showed the same two pre-existing errors already documented in
[references/lovelace.md](../../.claude/skills/home-assistant/references/lovelace.md) (duplicate
`rss-news-card` registration and its related 404); nothing new from this card.
