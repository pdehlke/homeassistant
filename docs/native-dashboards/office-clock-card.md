# Office dashboard: clock card swapped for larger text

`dashboard-office`'s clock, already set to the native `type: clock` card's largest built-in size,
needed to be larger still. Swapped to `custom:wall-clock-card` (rkotulan/ha-wall-clock-card
v3.5.0, already HACS-installed and documented in this skill's `references/lovelace.md`), which has
no upper size cap. Built 2026-08-15 on Home Assistant 2026.8.1.

## Why the native card couldn't do this

`type: clock`'s `clock_size` is a closed enum: `small` / `medium` / `large`, confirmed by reading
`hui-clock-card.ts` in the `home-assistant/frontend` repo. `large` maxes out at
`--ha-font-size-2xl`, measured live at 56px for the digits. There is no bigger built-in option and
no numeric override in the card's own config schema.

## Two paths considered

- **UIX override on the same card (rejected).** Bumping font-size past 2xl with a `uix:` style
  rule would have been the smaller diff, keeping the native card's exact look. Rejected because
  the card's `grid_options: {rows: "auto", ...}` computes its row count internally from
  `clock_size`/`clock_style`, capped at whatever `large` needs; a CSS-only size increase wouldn't
  grow that computed row count with it, and this instance has already been bitten once by the
  general version of that trap (shrinking a card's `grid_options` doesn't shrink its contents,
  documented in `references/lovelace.md`'s "Sections grid math"; the enlarging direction has the
  same box/content mismatch risk). Fixable only by hand-tuning an explicit `grid_options.rows`
  against CSS that HA's own row-height math knows nothing about.
- **Swap to `custom:wall-clock-card` (chosen).** Its `clockSize` field takes a raw CSS size, no
  cap, and its `grid_options` are just an ordinary card's, no internal auto-row logic to fight.
  Cost: a different card means a different rendering path, own fonts, and its own layout model
  (nine zones) even though only one zone is used here.

## What changed

```yaml
type: custom:wall-clock-card
appearance:
  size: custom
background:
  source: none
layout:
  zones:
    center:
      align: center
      widgets:
        - type: clock
          clockSize: 6rem
          timeFormat:
            hour: numeric
            minute: "2-digit"
            hour12: true
        - type: date
          dateSize: 1.75rem
          dateFormat:
            weekday: long
            month: long
            day: numeric
            year: numeric
grid_options:
  rows: 4
  columns: 12
```

Swapped via `scripts/apply-card.py` (`HA_MATCH_TYPE=clock` for the first save, replacing the
native card; `HA_MATCH_TYPE=custom:wall-clock-card` for the follow-up save described below), which
backs up the dashboard's full saved config before writing. Backups are timestamped JSON, kept
outside the repo; the pre-swap one is the rollback path if this doesn't hold up.

- **`clockSize: 6rem` (96px), `dateSize: 1.75rem` (28px).** Roughly 1.7x the old 56px digits,
  chosen by eye against a live screenshot rather than a fixed ratio: this instance's own working
  size-set for `wall-clock-card` (`references/lovelace.md`'s "Working small-card size set") is for
  a ~430px card and 4rem clock text, a smaller target than this one, so it wasn't reused directly.
- **`timeFormat`/`dateFormat` set explicitly.** The native card had left format to HA locale
  defaults; `wall-clock-card` needs the format spelled out, so `hour12: true` and the same
  weekday/month/day/year fields the native card was already configured with were carried over
  rather than changed.
- **`grid_options.rows: 4`**, up from the native card's `"auto"` (which had resolved to a box just
  tall enough for 56px digits). `wall-clock-card` doesn't compute its own row count from its
  widgets' configured sizes the way the native clock card does for its own presets, so this had to
  be picked by hand rather than left to auto-sizing. 4 rows was confirmed live to fit both widgets
  with no clipping and no gap large enough to look wrong, at a 1920x1080 viewport (see
  "Verification").
- **`background.source: none`.** Without it, the card still attempts to initialize a
  background-image manager and fails; see the console-noise note below. Setting it explicitly
  didn't stop the failure, but it is still the correct config for "no background image wanted" and
  was kept.
- **`appearance.size: custom`**, since every size that matters here is set per-widget
  (`clockSize`/`dateSize`) rather than picked from the card's small/medium/large presets.

## A console-noise quirk, not a bug

Even with `background.source: none` set explicitly, the installed build (3.5.0) logs two
`[wall-clock] [background-image-manager] No image source initialized` errors and several related
warnings on every load, tracing into `BackgroundImageController`/`BackgroundImageManager` code that
runs unconditionally regardless of whether a background image was ever requested. No visible effect
confirmed across three live reloads and matching screenshots; recorded here so it isn't mistaken for
a sign the swap is broken next time someone reads this card's console output.

## Verification

Confirmed live via `playwright-cli`, as the `Pete` admin account (a storage-state file built from
`$HA_TOKEN`, loaded and deleted per this skill's token-safety pattern; `dashboard-office` has no
`kiosk_mode` scoping for `Pete`, so its header and sidebar render normally in these screenshots,
unlike what the `office` account itself sees). At a 1920x1080 viewport:

- Before: native clock card measured 376x108.6px, digits at 56px computed font-size.
- After: no clipping against the News card stacked below it in the same section, confirmed by
  screenshot at each of the two saves (first without `background.source`, then with it added).
- Not verified as the `office` user itself, for the same reason noted in
  [office-kiosk-mode.md](office-kiosk-mode.md): no stored credentials or long-lived token exist for
  that account. Whoever looks at the physical Office display next should confirm the card reads
  well at actual viewing distance; 1920x1080 in a browser is a proxy, not the real display.
