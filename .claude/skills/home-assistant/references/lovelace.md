# Lovelace dashboards and cards

## Editing is WebSocket-only, and saves are destructive

REST cannot read or write dashboards. Use WebSocket:

- `{"type":"lovelace/dashboards/list"}`
- `{"type":"lovelace/config","url_path":"dashboard-sound"}`
- `{"type":"lovelace/config/save","url_path":"dashboard-sound","config":{...}}`

**A save replaces the entire dashboard config.** There is no partial update. Always read the live config, write a timestamped backup, modify in memory, then save. Three scripts share that read-backup-modify-save discipline, one per shape of edit; extend the matching one rather than writing a new save path:

- `scripts/apply-card.py` swaps a single card matching a `type` (and optional `entity`), refuses to write unless it matched exactly one.
- `scripts/append_section.py` adds one new section to a view, refuses to write unless the existing section count matches what you told it to expect.
- `scripts/replace_section.py` overwrites one section by index, for iterating on a section you just added without duplicating it.
- `scripts/add-kiosk-mode.py` adds a root-level `kiosk_mode` block scoped to one user's display
  name, refuses to write if one is already present. Also the reapply tool for
  [ADR-0061](../../../../docs/adr/0061-kiosk-mode-lost-on-gui-edit-reapply-dont-prevent.md): the
  Lovelace UI editor doesn't round-trip this key, so any GUI edit to a kiosk_mode-bearing dashboard
  can silently drop it. Re-run with the same arguments to restore it.

```bash
export HA_URL=https://hass.ehlke.net
export HA_BACKUP_DIR=/path/to/scratchpad   # defaults to cwd; never let it default into the skill dir
export HA_DASHBOARD=dashboard-sound        # defaults to dashboard-sound
python3 scripts/apply-card.py new-card.json --dry-run   # always dry-run first
python3 scripts/apply-card.py new-card.json

export HA_EXPECT_SECTIONS=3                # append_section.py: sanity check, not the new count
python3 scripts/append_section.py new-section.json --dry-run
python3 scripts/append_section.py new-section.json

python3 scripts/replace_section.py 3 revised-section.json --dry-run   # index is 0-based
python3 scripts/replace_section.py 3 revised-section.json

python3 scripts/add-kiosk-mode.py dashboard-office Office --dry-run
python3 scripts/add-kiosk-mode.py dashboard-office Office
```

## Sections grid math

Cards in a sections view are sized by `grid_options: {columns, rows}`.

- A section's internal grid is 12 columns, multiplied by its `column_span`. The Sound dashboard's section has `column_span: 3`, so its grid is **36 columns wide**, roughly 36px per column at a 1600px viewport.
- Row height is **56px plus an 8px gap**, so N rows is `64N - 8` pixels tall.

To get a square card, use roughly **1.75 columns per row**. `columns: 12, rows: 7` measured 427 by 439 pixels. `columns: 36` is full width.

The user can also drag a card's corner in edit mode, which writes `grid_options` for them.

## Custom cards do not scale with their container

This is the single biggest trap here. Shrinking a card's `grid_options` does not shrink its contents. Widgets keep their absolute font and icon sizes and overflow catastrophically.

When resizing any custom card, expect to set every size explicitly and to verify visually. A config that passes `check_config` and saves cleanly can still render as unreadable overlap.

## A strategy view can still take a `header`, undocumented

A view using `strategy:` (e.g. `areas-overview`, `light`) is typed as `LovelaceStrategyViewConfig` in the frontend source, which does **not** include a `header` field the way a normal `LovelaceViewConfig` does. Adding one anyway works. `expandLovelaceConfigStrategies` spreads the raw stored view config first, then overlays the strategy's generated output: `{...base, ...generated}`. Since a strategy's generated output doesn't set `header` itself, the raw `header` from `base` survives the merge and renders normally, sitting above whatever the strategy generates.

Confirmed working (2026-08-04): the Lights dashboard uses `strategy: {type: areas-overview}` for dynamic per-area cards, with a sibling `header: {card: {...}}` for a date/time/weather banner. Both rendered together; areas still add and remove live.

Card recipe used for that header, reusable elsewhere:

```yaml
header:
  card:
    type: horizontal-stack
    cards:
      - type: vertical-stack
        cards:
          - type: markdown
            content: "{{ now().strftime('%B %-d, %Y') }}"
          - type: clock
            clock_style: digital
            time_format: "12"
            show_seconds: false
      - type: weather-forecast
        entity: weather.openweathermap
        show_current: true
        show_forecast: false
```

The `markdown` card's `now()` template re-renders on its own each minute; no separate date entity or `time_date` integration needed.

**Caveat:** this isn't a supported combination, just an emergent property of the current merge order in `get-strategy.ts`. A future frontend rewrite could change that and silently drop the header. If it stops appearing after a HA update, this is why.

## Built-in view strategies hardcode their card sizes

A strategy computes its cards' `grid_options` in code. None of the area/light strategies expose a layout knob, so the only way to change the arrangement is to pick a different strategy or hand-build the view.

| Strategy | Area card `grid_options` | Renders as |
|---|---|---|
| `areas-overview` | `columns: 12`, `rows: 1` (`rows: 4` when `card_size: large`) | one full-width row per area |
| `home-overview` (the default Overview dashboard) | `columns: 4`, `rows: 2`, plus `vertical: true` | compact square tiles, ~6 across |
| `light` | per-*entity* tiles, not per-area | grid of individual light tiles under an area heading |

`areas-overview`'s entire config surface is `areas_display` (hidden/order), `floors_display` (order), and `areas_options.<area>.card_size` (`small`/`large`). `card_size: large` switches the card to `display_type: camera` and `rows: 4` but stays `columns: 12`, so it gets taller, never narrower. Its editor (`strategies/areas/editor/`) exposes nothing further.

Consequence: **you cannot get Overview's area-tile grid out of `areas-overview`.** Matching that look means hand-building the section with `{type: area, display_type: compact, vertical: true, grid_options: {rows: 2, columns: 4}}` cards, which gives up the strategy's live add/remove of areas. Confirmed 2026-08-04 on HA 2026.7.4.

### Domain dashboards and Home's tabs: retired 2026-08-16

A three-level Crestron-mirrored dashboard pattern (standalone `dashboard-lights`/`dashboard-av`/
`dashboard-lennox-home`/`dashboard-alarm-system`, plus a tabbed `vision-sample`/"Home" dashboard
generated from the same registries) predated Homie Dashboard and is now retired in favor of it;
`scripts/rebuild-domain-dashboard.py` and `scripts/rebuild-home-tab.py`, the generators that built
it, are deleted. See [docs/native-dashboards/native-dashboards-retired.md](../../../../docs/native-dashboards/native-dashboards-retired.md) and ADR-0062 in the
`pdehlke/homeassistant` repo for the full design (the three-level hierarchy, area-targeted presets,
the header-card and strategy-merge behaviors it relied on) and why it was retired.

### `hui-button-card` ignores `grid_options: {rows: 1}` when it shows an icon and a name

Cost real time on 2026-08-06 sizing preset buttons on the now-retired Home dashboard's leaves for
the wall tablet's 1280x800 screen; the underlying frontend behavior is still current and worth
knowing for any future button-card work. `getGridOptions()` in `hui-button-card.ts`
(home-assistant/frontend) is hardcoded, with no config field reaching it:

```ts
if (config.show_icon && (config.show_name || config.show_state)) {
  return { rows: 2, columns: 6, min_columns: 2, min_rows: 2 };  // icon + text
}
return { rows: 1, columns: 3, min_columns: 2, min_rows: 1 };     // icon only
```

Any button showing both an icon and a name or state gets `min_rows: 2` regardless of what
`grid_options.rows` in its own config says. The outer grid wrapper (a plain `<div>` inside the
section's own shadow root, one level above anything a card's own UIX rule can reach) is pinned to
that span; a UIX rule shrinking the card's own rendered height only shrinks the content inside an
unchanged wrapper cell, leaving dead space behind, not a smaller footprint. Confirmed by walking
every shadow root to the wrapper `<div>` directly and reading its computed `grid-row`: `span 2`,
unmoved by forcing the inner card down to 30px live. The only way to reach the smaller
`min_rows: 1` branch is `show_name: false` or `show_icon: false`; there is no `grid_options`
override for it. `rebuild-home-tab.py`'s `preset_card()` uses `show_name: false` plus a UIX
icon-size cap as the combination that actually works.

### `strategy: {type: light}` is the auto-discovering grid, once lights exist

The `light` view strategy lays lights out as a grid *and* still regenerates live, so it looks like the way to get both. The catch: it emits a section only for an area holding at least one `light` entity with `entity_category: none`, and skips every area with none. On an instance with no light entities yet it renders a completely empty view. That is why the Lights dashboard here runs `areas-overview` (which lists areas regardless of contents) rather than `light`. Revisit once real lights are assigned to areas.

## The built-in `calendar` card ignores its own `theme:` key

Confirmed 2026-08-14 on `dashboard-office`. Setting `theme: "Frosted Glass"` directly on a
`type: calendar` card config does nothing for its month-grid view, while the identical `theme:`
line on a `weather-forecast` card right next to it works fine. The card renders inside its own
`ha-full-calendar` custom element (a second shadow root nested inside `hui-calendar-card`'s own),
and FullCalendar's root `.fc` div paints its own near-opaque `--card-background-color` background
directly, on top of the outer `ha-card` shell. The outer shell *does* pick up the theme (and, for
Frosted Glass specifically, the theme's global `card-mod-theme` glass overlay) correctly; FullCalendar's
internal DOM just paints over it and hides it.

Fix with UIX, piercing the extra shadow boundary with the `$`
selector to reach FullCalendar's own classes:

```json
"uix": {
  "style": {
    "ha-full-calendar$": ".fc { background: var(--ha-card-glass-tint, rgba(255,255,255,0.08)) !important; }\n.fc-scrollgrid, .fc-scrollgrid table, .fc-scrollgrid td, .fc-scrollgrid th { border-color: var(--divider-color) !important; }\n.fc-col-header-cell { background: rgba(255,255,255,0.06) !important; }\n.fc-daygrid-day-number { color: var(--primary-text-color) !important; }\n.fc-daygrid-day-frame:hover { background: rgba(255,255,255,0.10) !important; }\na.fc-col-header-cell-cushion { color: var(--secondary-text-color) !important; }\n.fc-day-today { background: rgba(255,255,255,0.08) !important; }\n"
  }
}
```

Verified only for the default `dayGridMonth` view. The list/week/day FullCalendar views use
different `.fc-list-*` / `.fc-timegrid-*` classes and were not tested; expect the same problem
there if anyone switches views on a themed instance and hits an unstyled white panel again.

## mini-media-player (kalkih/mini-media-player v1.16.12): two undocumented config keys

Confirmed 2026-08-14 building the Office dashboard's now-playing footer (see
[office-now-playing-footer.md](../../../../docs/native-dashboards/office-now-playing-footer.md) in the
`pdehlke/homeassistant` repo for the full build). The published docs Context7 serves for this card
are stale relative to the installed version; both facts below only surfaced by fetching
`/hacsfiles/mini-media-player/mini-media-player-bundle.js` from the live instance and reading it
directly.

- **`hide.power: true`** hides the power toggle button entirely. This key isn't in the documented
  `hide` object at all. The documented `hide.power_state` only hides the button's colored
  active/inactive indicator, not the button itself, `showPowerButton` in the bundle checks
  `!this.config.hide.power` specifically. Needed for any non-interactive/kiosk use, otherwise a
  clickable-looking power icon renders regardless of every other `hide.*` flag.
- **`artwork` mode naming is a trap.** `cover`, `full-cover`, and `full-cover-fit` are all the same
  full-bleed-background family (`ha-card.--has-artwork[artwork*='cover']` in the card's own CSS).
  `default` is the actual small-thumbnail-plus-text layout. Picking `artwork: cover` expecting a
  compact thumbnail produces a full-bleed background image instead, which will bury any translucent
  theme (Frosted Glass included) the card sits on.

## Also confirmed 2026-08-14: config-flow Template helpers have no delay_on/delay_off

The UI/API-driven Template helper (`config_entries/flow`, handler `template`, step `binary_sensor`)
exposes `name`, `state`, `device_class`, `device_id`, and `availability`, nothing else, confirmed by
reading its live `data_schema`. `delay_on`/`delay_off` only exist on the legacy YAML `template:`
platform, which isn't reachable from this machine (no filesystem access to the host's `/config`, no
API for editing `configuration.yaml`). Any hysteresis/anti-flicker delay on a template-derived
helper needs an automation instead: two state triggers (`to`/`from` the target state(s)) branching
on `trigger.id` via `choose`, with `mode: restart` so a value flipping back before the delay elapses
cancels the pending change cleanly, no extra guard condition needed.

## wall-clock-card (rkotulan/ha-wall-clock-card v3.4.0)

Docs live in the repo under `docs/`, not just the README. Fetch them at the installed tag:

```
https://raw.githubusercontent.com/rkotulan/ha-wall-clock-card/v3.4.0/docs/<name>.md
```

`layout.md` is the important one. Others: `configuration`, `weather`, `sensors`, `calendar`, `clock-date`, `action-bar`, `image-sources`, `background-handling`, `separator`, `transportation`.

### Layout model

Nine zones (`top-left` through `bottom-right`). `layout.format` reshapes them:

| Format | Result |
|---|---|
| `grid-3x3` | Default 3x3 canvas |
| `vertical-1-2` | Narrow panel **left**, main area right |
| `vertical-2-1` | Main area left, narrow panel right |
| `horizontal-1-2` / `horizontal-2-1` | Same, split horizontally |

In a vertical split, the narrow panel takes the left logical zones and the main area takes center plus right. `top-*` widgets stack from the top of their panel, `bottom-*` pin to its bottom, `center` stays centered. `layout.preset: glass` gives the narrow third a dark translucent surface.

### Lessons paid for in wasted turns

- **`showTitle: false`** removes a widget's heading. The docs only show it under the OpenWeatherMap provider but it works for the Home Assistant provider too. Setting `title: ""` does **not** work; it falls back to the localized default.
- **The action bar clips its labels to roughly icon width in a narrow panel.** In a 145px glass panel the labels truncated to "H..." and "M..." at four columns, two columns, and one column, with one column spilling outside the panel entirely. `style.fontSize` is ignored by built-in widgets. There is no option to hide labels. In a small card, leave the action bar out.
- **Weather `orientation`** matters. `vertical` stacks forecast days as rows, `horizontal` lays them out as day columns like the reference screenshots. In a side zone, `auto` resolves to vertical.
- **Sensors `orientation`** defaults to vertical in side zones. Set `horizontal` explicitly for the side-by-side pair with a divider.
- `background.source: picsum` needs no API key and is the easy default, but it serves a different random photo on every load. Use `local` with files under `/config/www` (served as `/local/...`) when consistency matters.
- The calendar widget needs a real calendar entity. With `entities: []` and `hideWhenEmpty: false` it renders a permanently empty box. Local Calendar is the zero-dependency way to give it one.

### Working small-card size set

For a roughly 430px square, these values fit without overflow:

`appearance.size: small`, `layout.spacing: compact`, `clockSize: 4rem`, `dateSize: 0.95rem`, weather `labelSize: 0.6rem` / `valueSize: 0.75rem` / `forecastDays: 3`, sensors `iconSize: 0.85rem` / `labelSize: 0.55rem` / `valueSize: 0.75rem` / `itemGap: 4px`, calendar `calendarDateSize: 0.6em` / `eventTitleSize: 0.65em` / `eventDetailSize: 0.55em` / `maxEvents: 2`, and no action bar.

## UIX replaces deprecated card-mod

`card-mod` 4.2.1 is permanently deprecated for this instance. Home Assistant 2026.8 renamed
the frontend `developer-tools` route to `tools`, which breaks card-mod's frontend integration
path. The upstream compatibility report is [card-mod issue #606](https://github.com/thomasloven/lovelace-card-mod/issues/606).
Do not restore, pin, downgrade, upgrade, or otherwise backward-fix card-mod.

UI eXtension (UIX) replaced it live with resource `/uix/uix.js?v=8.0.1`. The [UIX migration
FAQ](https://uix.lf.technology/faq/) documents it as a drop-in replacement through card-mod
4.2.1, so existing `card_mod` card and theme keys remain compatible during the transition. All
new or edited configuration must use `uix:` and `uix-*` theme keys instead. Do not use the
compatibility layer as a reason to add new card-mod syntax.

The replacement was verified in a fresh Playwright CLI session on 2026-08-15:

- The `vision-sample` A/V view rendered 14 cards and 44 `uix-node` elements.
- The three existing A/V overrides emitted their configured `blur(22px) saturate(140%)`,
  translucent background, border, and shadow rules through UIX.
- Computed background, border, and box-shadow values matched the per-card configuration.
- Liquid Glass's theme-level `ha-card { backdrop-filter: unset !important; }` still wins over
  the per-card blur declaration, leaving the theme's `::before` blur at `blur(8px)`. This is a
  Liquid Glass cascade decision, not a UIX loading failure, and it is relevant only to the
  development-only Office theme.
- The Office control dashboard rendered 10 cards and 19 `uix-node` elements.
- The only console errors were the pre-existing duplicate `rss-news-card` registration and its
  related 404, with no UIX errors.

For styling work, use UIX and verify the computed property that matters. Do not reopen the closed
card-mod investigation for a backward fix.

## Verify visually

The whole point of a dashboard is how it looks, so screenshot it. See the Playwright section of [api-access.md](api-access.md) for the auth pattern and its token-safety requirements.
