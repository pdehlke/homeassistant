# Native dashboards: what Home and the standalone domain dashboards were, and why they're gone

Retired 2026-08-16 (see [ADR-0062](../adr/0062-native-dashboards-retired.md)). This is a
consolidated retrospective of `dashboard-home.md`, `dashboard-navigation-model.md`,
`dashboard-header-card.md`, `vision-sample-demo-entities.md`, and `vision-sample-pergola-solar-gauge.md`,
which together documented roughly two weeks of work (2026-08-04 through 2026-08-07) before Homie
Dashboard existed. Those five files are deleted; this doc keeps the reasoning worth keeping. Full
detail, including exact CSS values, Playwright verification transcripts, and every intermediate
dead end, is still recoverable from git history if it's ever needed.

## What it was

Before Homie Dashboard, the plan was to build the kiosk experience for the eventual wall-mounted
touch panel directly out of Home Assistant's own Lovelace dashboards, shaped to match the Crestron
TSW-752 panels being replaced. The Crestron panels present a fixed three-level hierarchy: a top
screen with one card per subsystem (A/V, Climate, Lights, Alarm), each leading to a screen of area
cards, each leading to a single-domain single-area control screen. HA's own default area page does
the opposite, grouping everything in a room by domain, which is a real regression from a physical
keypad: reaching a dimmer by scrolling past media players and door locks. The native dashboards
mirrored the Crestron shape instead: level 1 domain selection, level 2 an area grid, level 3 a leaf
with presets, scenes, and per-entity tiles.

**Level 1** went through two shapes. It was first just the HA sidebar, which did the job for free
while a kiosk device wasn't yet in the picture. Once a kiosk device needed an actual default
dashboard, it briefly became its own dashboard, `tablet-home` ("Tablet Home"), a 2x2 button grid
navigating out to four standalone domain dashboards — `dashboard-lights`, `dashboard-av`,
`dashboard-lennox-home`, `dashboard-alarm-system`. That lasted under a day: a `Tablet` HA user's
`default_panel` was retargeted to `vision-sample` (titled "Home," originally the visionos theme's
demo dashboard), whose own native view-tab strip (Home, Lights, A/V, Alarm, Climate) did level 1's
job directly, one tab per domain, with each tab holding that domain's own level 2/3 content
generated onto Home's own views rather than linking out to the standalone dashboards. The standalone
dashboards kept existing as pure generation sources afterward, never a navigation destination.

**Level 2**, the area grid, gave every area a card, including areas with nothing of that domain yet
— deliberately, so the grid doubled as a migration checklist while Crestron channels were mapped one
by one. An area with nothing in it was not tappable: omitting `tap_action` entirely (not setting an
explicit "do nothing" action) works because `hui-area-card` falls back to `{action: "none"}` and its
`hasAction()` check reports false for that value, rendering with no ripple and no pointer cursor.

**Level 3**, the leaf, held a back button, room-wide preset buttons, group-preset rows for areas
with sub-clusters, any real scene entities, and a tile per entity. Presets were area- or
label-targeted service calls (`target: {area_id: ...}` / `{label_id: ...}`), never a hardcoded
entity list, so a room's buttons worked the moment it gained its first light and automatically
covered fixtures added later. Real scenes were layered on top for the cases a preset genuinely
can't express (three different brightness levels in one "evening" scene, one light off) rather than
replacing presets outright, since a scene is a snapshot of named entities and can't be written for a
room whose fixtures are still unknown. A group level between "whole area" and "one fixture" (Primary
Suite's bedroom/bath split) was expressed with HA labels rather than nested areas, since areas can't
nest and hardcoding entity IDs would have broken the point of area-targeting.

A plain `light.toggle` on a multi-entity area/label target turns out not to be one decision — it
toggles each entity by its own state, so a room half on and half off can end up fully inverted
instead of uniformly on or off. `script.smart_toggle_lights` fixed that: given a target area or
label, it checked whether any covered light was on and drove the whole group to a single shared
direction. Its fields were deliberately named `target_area_id`/`target_label_id`, not `area_id`/
`label_id` — HA's Jinja template engine registers `area_id()`, `label_id()`, and similar names as
built-in global functions available in any template, so a script field sharing one of those exact
names doesn't render as empty when unset; it silently resolves to the built-in function object
instead, which is truthy, and every template guard written to catch "unset" quietly fails. This bit
the first version of the script for real, diagnosed only by reading the script's own trace rather
than guessing from the wrong output.

Generation was table-driven: `rebuild-domain-dashboard.py` read the live floor/area/entity/device
registries and rebuilt a standalone dashboard from a `DOMAINS` table (entity domains, icons, presets,
per-tile features). `rebuild-home-tab.py`, added once Home's tabs needed the same treatment, was
built the same way against its own copy of that table, reading the same live registries rather than
copying the standalone dashboard's saved config, so the two could drift independently — accepted
consciously as a duplication tradeoff, never resolved, and ultimately mooted by this retirement
rather than fixed. The A/V domain needed one real code change beyond the table: the area card's
inline toggle feature doesn't support `media_player`, so `area_control` had to become optional
rather than assumed. Music Assistant also mirrors adopted players, so a physical device could appear
more than once; fixed by hiding the redundant registry entries (chosen per pair by which one was live
and area-assigned, not uniformly by platform, since Music Assistant wasn't consistently the
redundant side).

A shared date/time/weather header (a `horizontal-stack` of a clock and a weather card, injected via
a view-level `header:` key) sat above the standalone dashboards' content, needed because their
`kiosk_mode` setup hid HA's native top app bar entirely and nothing else on the page carried a
title. Two undocumented Lovelace behaviors came out of building it: a view's `header` key only
renders on `sections` views (silently stored and never drawn on `masonry`, with no error anywhere),
and UIX styling loses cascade ties against a card's own built-in stylesheet — a card's own rule,
attached via `adoptedStyleSheets`, always comes after an injected `<style>` element in the same
shadow root, so anything that needs to override a card's own CSS needs `!important`, full stop.

Home's own tabs, by contrast, kept HA's native header and hid only the sidebar (`hide_sidebar`, not
`hide_header`) — the native tab strip already showed the current tab's title, so Home needed none of
the standalone dashboards' title-heading or hand-built back-button workarounds. Sizing Home's leaves
for the target 1280x800 Fire HD 10 surfaced one more real HA quirk: `hui-button-card`'s
`getGridOptions()` is hardcoded in the frontend, and any button showing both an icon and a name gets
forced to `min_rows: 2` regardless of what `grid_options.rows` asks for. The only way to reach the
smaller footprint is `show_name: false`; there's no config field that reaches the hardcoded branch
directly.

## Why it's gone

The pattern was an experiment, built and refined before Homie Dashboard was ever installed. Once
work on Homie started, it became the dashboard actually invested in, and the physical Fire HD
tablet has been running Homie exclusively since the `kiosk_mode` fix in the 2026-08-07 checkpoint of
[homie-dashboard-install-plan.md](../homie-dashboard/homie-dashboard-install-plan.md) — nothing has
navigated to Home or the standalone dashboards since. Maintaining two independently regenerated
copies of the same dashboard content, for a pattern nobody was using, was pure upkeep for no payoff.
[GitHub issue #2](https://github.com/pdehlke/homeassistant/issues/2) had tracked the drift risk
between the two copies without picking a fix; this is a fifth path the issue didn't consider,
chosen instead of any of its four.

## What was removed (2026-08-16)

- Live dashboards: `vision-sample` (Home), `tablet-home` (already dead before this), `dashboard-lights`,
  `dashboard-av`, `dashboard-lennox-home`, `dashboard-alarm-system`.
- The `Tablet` HA user account.
- `script.smart_toggle_lights` and the `bath`/`bedroom` labels.
- `rebuild-domain-dashboard.py` and `rebuild-home-tab.py`.

Every dashboard config, the script config, and the label/entity assignments were backed up to
`/Users/pde/tmp/native-dashboards-retired-backup-20260816/` before deletion.

Untouched: `dashboard-office` and its docs, `dashboard-sound`, `dashboard-clock`, `dashboard-test`,
the `Homie Dashboard` and `Office` HA users, and `homie-dash` itself — none of these are part of the
retired pattern.

## Related

- [ADR-0062](../adr/0062-native-dashboards-retired.md) for the retirement decision itself.
- ADR-0012 through ADR-0018 for the individual decisions summarized above, each now marked
  superseded by ADR-0062 but left in place with their original reasoning.
- [dashboard-office docs](office-kiosk-mode.md) for the one native dashboard still in active use,
  which borrowed this pattern's `kiosk_mode` mechanism.
