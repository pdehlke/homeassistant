# Lovelace dashboards and cards

## Editing is WebSocket-only, and saves are destructive

REST cannot read or write dashboards. Use WebSocket:

- `{"type":"lovelace/dashboards/list"}`
- `{"type":"lovelace/config","url_path":"dashboard-sound"}`
- `{"type":"lovelace/config/save","url_path":"dashboard-sound","config":{...}}`

**A save replaces the entire dashboard config.** There is no partial update. Always read the live config, write a timestamped backup, modify in memory, then save. `scripts/apply-card.py` implements exactly this and refuses to write unless it matched exactly one target card. Extend its matcher rather than writing a new save path.

```bash
export HA_URL=http://homeassistant.local:8123
export HA_BACKUP_DIR=/path/to/scratchpad   # defaults to cwd; never let it default into the skill dir
export HA_DASHBOARD=dashboard-sound        # defaults to dashboard-sound
python3 scripts/apply-card.py new-card.json --dry-run   # always dry-run first
python3 scripts/apply-card.py new-card.json
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

### Domain dashboards are generated, not hand-edited

Because of the constraint above, the domain dashboards give up `areas-overview` and are generated by `scripts/rebuild-domain-dashboard.py`, which also builds the drill-down subviews. It implements a three-level navigation model borrowed from the Crestron panels being replaced: level 1 is domain cards (the sidebar stands in for it), level 2 is area cards, level 3 is one domain in one area.

```bash
export HA_URL=http://homeassistant.local:8123
export HA_BACKUP_DIR=/path/to/scratchpad
python3 scripts/rebuild-domain-dashboard.py lights --dry-run   # always dry-run first
python3 scripts/rebuild-domain-dashboard.py lights
```

Run it after adding, removing, renaming or re-flooring an area, and after adding entities that change whether an area is populated. Everything domain-specific lives in the `DOMAINS` table at the top, so adding A/V later means adding a block there rather than writing code.

Behaviour worth knowing:

- It preserves the level 2 view's `header` card verbatim and refuses to save if the live config has none, rather than silently dropping it.
- It writes a timestamped backup before every save.
- Ordering comes from the explicit `FLOOR_ORDER` / `AREA_ORDER` lists; anything absent is appended rather than dropped, with a printed note.
- Every area gets a level 2 card, but only populated areas are tappable. Omitting `tap_action` is genuinely inert: `hui-area-card` falls back to `{action: "none"}` and `hasAction()` reports false for it, so the card renders with no ripple. Unpopulated rooms therefore cannot dead-end, and the dashboard doubles as a migration checklist.
- Leaf presets are **area-targeted** service calls (`target: {area_id: ...}`), so they need no per-room entity data and automatically cover fixtures added later.

Verified 2026-08-04 on the lights domain: clicking a populated card navigates to its leaf, the back button returns to level 2, an unpopulated card does not navigate at all, and the All Off / Low / Medium / Bright presets drove both Office lights to 0, 25 and 100 percent without either being named.

### Home's own tabs are generated too, by a second script

`vision-sample` (titled "Home") is meant to become the main kiosk dashboard for wall-mounted touch
panels, not just the theme demo it started as; see the `home-dashboard-main-kiosk` memory and
`dashboard-tablet-home.md` in the `pdehlke/homeassistant` repo for the full story. Each of its tabs
(Lights so far) mirrors a domain dashboard's content but has to stay self-contained: everything on
Home navigates within `/vision-sample/...`, never out to `dashboard-lights` or the other standalone
domain dashboards, which have different `kiosk_mode` chrome and a home icon that points to Tablet
Home instead.

`scripts/rebuild-home-tab.py` builds one Home tab from the same live registries
`rebuild-domain-dashboard.py` reads, not by copying another dashboard's saved config. It's based on
that script; differences worth knowing before extending it to another domain:

```bash
export HA_URL=http://homeassistant.local:8123
export HA_BACKUP_DIR=/path/to/scratchpad
python3 scripts/rebuild-home-tab.py lights --dry-run   # always dry-run first
python3 scripts/rebuild-home-tab.py lights
```

- No title-only heading section. Home never hides its native header the way the kiosk-moded domain
  dashboards do, so the tab strip already carries the title.
- Every `navigate` action targets `/vision-sample/...`. Never the domain's own dashboard.
- Leaf views are namespaced `<domain>-area-<area_id>`, not `area-<area_id>`: Home hosts leaves from
  more than one domain in one flat `views` list, where the plain name would collide between e.g. a
  Lights leaf and an A/V leaf.
- It preserves the target tab's `badges` (pde's hand-picked chips: device trackers, the alarm panel,
  weather), never invents them, the same principle as `header` preservation above just for a
  different config key: Home has no per-tab header card, badges are its equivalent.
- It only rebuilds a tab that already exists on Home (`home_view_path` in its own `DOMAINS` table
  must match a real view's `path`) and only touches that domain's tab and leaves; every other Home
  view is read back and rewritten unchanged, at its original index, so the tab order never shifts.
- Its own `DOMAINS` table is a copy of `rebuild-domain-dashboard.py`'s, minus the fields that name
  the standalone dashboard, plus `home_view_path`. Nothing enforces the two staying in sync; update
  both by hand.

### `hui-button-card` ignores `grid_options: {rows: 1}` when it shows an icon and a name

Cost real time on 2026-08-06 sizing preset buttons on the Home leaves for the wall tablet's 1280x800
screen. `getGridOptions()` in `hui-button-card.ts` (home-assistant/frontend) is hardcoded, with no
config field reaching it:

```ts
if (config.show_icon && (config.show_name || config.show_state)) {
  return { rows: 2, columns: 6, min_columns: 2, min_rows: 2 };  // icon + text
}
return { rows: 1, columns: 3, min_columns: 2, min_rows: 1 };     // icon only
```

Any button showing both an icon and a name or state gets `min_rows: 2` regardless of what
`grid_options.rows` in its own config says. The outer grid wrapper (a plain `<div>` inside the
section's own shadow root, one level above anything a card's own `card_mod` can reach) is pinned to
that span; a `card_mod` shrinking the card's own rendered height only shrinks the content inside an
unchanged wrapper cell, leaving dead space behind, not a smaller footprint. Confirmed by walking
every shadow root to the wrapper `<div>` directly and reading its computed `grid-row`: `span 2`,
unmoved by forcing the inner card down to 30px live. The only way to reach the smaller
`min_rows: 1` branch is `show_name: false` or `show_icon: false`; there is no `grid_options`
override for it. `rebuild-home-tab.py`'s `preset_card()` uses `show_name: false` plus a `card_mod`
icon-size cap as the combination that actually works.

### `strategy: {type: light}` is the auto-discovering grid, once lights exist

The `light` view strategy lays lights out as a grid *and* still regenerates live, so it looks like the way to get both. The catch: it emits a section only for an area holding at least one `light` entity with `entity_category: none`, and skips every area with none. On an instance with no light entities yet it renders a completely empty view. That is why the Lights dashboard here runs `areas-overview` (which lists areas regardless of contents) rather than `light`. Revisit once real lights are assigned to areas.

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

## Verify visually

The whole point of a dashboard is how it looks, so screenshot it. See the Playwright section of [api-access.md](api-access.md) for the auth pattern and its token-safety requirements.
