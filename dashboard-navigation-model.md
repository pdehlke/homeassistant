# Dashboard navigation model

How dashboards are organised in Home Assistant, why they are shaped like the Crestron touch panels
they are replacing, and how the same structure gets reused for each subsequent subsystem.

Established 2026-08-04 on Home Assistant 2026.7.4, with the lights domain as the first
implementation.

## The model

The Crestron TSW-752 panels present a fixed three-level hierarchy. The top screen shows a card per
subsystem: A/V, Climate, Lights, Alarm. Tapping one leads to a screen of cards, one per area that
subsystem exists in. Tapping an area leads to a screen that controls that one subsystem in that one
area and nothing else.

Home Assistant's own dashboards are organised the other way round: an area page shows everything in
that room, grouped by domain. That is a reasonable default and it is not what a lighting keypad
replacement should do. Reaching a dimmer by scrolling past media players and door locks is a
regression from a physical button on a wall.

The Home Assistant dashboards therefore mirror the Crestron hierarchy:

| Level | Screen | Contents | Status |
| :--- | :--- | :--- | :--- |
| 1 | Root | One card per domain | Built, see [dashboard-tablet-home.md](dashboard-tablet-home.md) |
| 2 | Domain | One card per area | Built for lights and A/V |
| 3 | Leaf | One domain in one area | Built for lights and A/V |

Level 1 was deferred at first. The sidebar already listed the domain dashboards, so it did the same
job with no work, until [Tablet Home](dashboard-tablet-home.md) needed a real one to put a kiosk
device's default dashboard on, at which point the sidebar was no longer available to stand in for
it at all.

## Level 2, the area grid

The page opens with a title-only heading, the domain name and its icon, no cards under it. This
exists for the same reason the leaf grew its own back button: kiosk-mode hides HA's native top app
bar for the [Tablet Home](dashboard-tablet-home.md) user, which is the only other place the view's
title (`Lights`, `A/V`, ...) would ever render, and without it every domain dashboard's floor
sections look identical.

Every area gets a card, including areas that contain nothing of that domain. This is on purpose.
Most rooms have no lights in Home Assistant yet because the Crestron channel mapping is unknown, so
the dashboard doubles as a migration checklist: cards light up one at a time as channels get wired,
and the remaining dim ones are the work still outstanding. Once every room is mapped, the display
converges on the correct end state without anyone having to change the rule.

An area with nothing in it is **not tappable**, so it cannot dead-end. This is achieved by omitting
`tap_action` entirely rather than by setting an explicit "do nothing" action. Home Assistant's area
card falls back to `{action: "none"}` when no tap action is configured, and its internal
`hasAction()` check reports false for that value, so the card renders with no ripple and no pointer
cursor. Populated areas additionally get an inline area-controls toggle for the whole room.

The alternative, showing only populated areas, is what a finished Crestron panel does. It was
rejected for now because it would currently collapse the Lights dashboard to a single card and hide
exactly the information that is most useful during a migration.

## Level 3, the leaf

Each populated area gets a subview at `/<dashboard>/area-<area_id>`. Marking it `subview: true`
keeps it out of the tab bar and gives a back button that returns to level 2, in HA's own top app
bar. That native back button is invisible to anyone using [Tablet
Home](dashboard-tablet-home.md), whose kiosk-mode setup hides that whole bar, so the leaf also
carries its own explicit back button as in-page content, first thing on the page.

The leaf holds up to five things in order:

1. A full-width button back to level 2, labelled with the domain title, `m3rf:arrow-back` icon.
   Its own section, not mixed into the presets, so it reads as navigation rather than a device
   action. Redundant with the native subview back button for anyone who can see it, but the only
   way back for anyone who can't.
2. Room-wide preset buttons.
3. One preset row per configured group, for the rare area that holds more than one distinct
   fixture cluster. Omitted entirely for every area that has none configured.
4. Any real scene entities assigned to that area, omitted entirely when there are none.
5. One tile per entity, each with the appropriate inline control. For lights that is a brightness
   slider, so a fixture can be dimmed without leaving the screen.

### Presets target the area, not the entities

The preset buttons issue area-targeted service calls:

```yaml
tap_action:
  action: perform-action
  perform_action: light.turn_on
  target:
    area_id: office
  data:
    brightness_pct: 25
```

Nothing about a specific fixture appears anywhere. That matters for three reasons. The buttons work
in any room the moment it gains its first light, with no per-room configuration. They automatically
cover fixtures added later, which is the normal case here as Crestron channels get mapped one by
one. And they cannot break when an entity is renamed.

The current presets are All Off, Low at 25 percent, Medium at 60 percent, and Bright at 100 percent.

Real Home Assistant scenes were considered as the mechanism and rejected as the *only* mechanism,
because a scene is a snapshot of named entities at named states and therefore cannot be written for
a room whose fixtures are unknown. Only one room currently qualifies. Scenes are instead layered in
on top: any `scene` entity assigned to an area appears in its own section on that area's leaf, so
faithful Crestron presets can be added per room as the channel map lands, without waiting for all of
them.

### Group presets target a label, for the areas that need a level between area and fixture

Primary Suite holds five lights split across two physical clusters, bedroom and bath, and HA areas
cannot nest (see [area-floor-layout.md](area-floor-layout.md) on why the Garage is a floor rather
than a sub-area for the same reason). An area-targeted preset cannot express "just the bath
fixtures," and naming the two `light.bath_*` entities directly in the button config would have
broken the same guarantee area-targeting exists for in the first place.

The fix carries the area-targeting idea down one level: a label instead of an area. `bath` and
`bedroom` are ordinary labels (`config/label_registry/create`), applied to the relevant light
entities by hand, the same one-time step as assigning an entity to an area. The preset buttons then
target `label_id` instead of `area_id`:

```yaml
tap_action:
  action: perform-action
  perform_action: light.turn_on
  target:
    label_id: bath
  data:
    brightness_pct: 25
```

Which areas get which group rows is a table, `AREA_GROUP_PRESETS` in `rebuild-domain-dashboard.py`,
keyed by `area_id` with a list of `{name, label_id, icon}`. Added for `primary_suite` only, since it
is the only area that currently needs it; extending it to another area later is a table entry, not
new code, the same shape as `DOMAINS` itself. Confirmed live: the Bath row's Low preset turned on
only `light.bath_perimeter` and `light.bath_diagonals` at 25 percent, leaving both bedroom lights
untouched.

## Generation

None of this is hand-edited. `rebuild-domain-dashboard.py`, in the `home-assistant` agent skill,
reads the live floor, area, entity and device registries and rewrites the entire dashboard including
every leaf. Editing a dashboard by hand in the UI will be overwritten the next time it runs.

It resolves an entity's area the same way Home Assistant does, using the entity's own `area_id` when
set and falling back to the area inherited from its device, and it skips disabled and hidden
entities.

Run it after adding, removing, renaming or re-flooring an area, and after adding entities that
change whether an area counts as populated.

Three safety behaviours are worth knowing. It copies the level 2 header card verbatim and refuses
to save if the live config has none, so the hand-authored date, time and weather banner cannot be
lost by a regeneration. It writes a timestamped backup of the existing config before every save,
because a Lovelace save replaces the whole dashboard rather than merging. And the config it saves
is the live config spread first, `{**config, "views": [...]}`, not a bare `{"views": [...]}`, so
any other hand-authored key at the config root survives too.

That last one was a real bug, not a precaution taken in advance. The first version of this script
built `updated = {"views": [...]}` directly, which is fine as long as `views` is the only thing
that has ever lived at the config root. It stopped being fine on 2026-08-05, the day
[dashboard-tablet-home.md](dashboard-tablet-home.md) added a root-level `kiosk_mode` key to the
Lights and A/V dashboards by hand. The next regeneration of either domain silently dropped it,
because the header-preservation logic only ever looked inside `views[0]`, never at the config root
itself. Caught by re-testing the Tablet kiosk user right after the regeneration, not by reading the
saved config back, which would have shown a config that looked complete. `kiosk_mode` had to be
restored by hand afterward.

### Adding a domain

Everything domain-specific lives in a single `DOMAINS` table: which entity domains count, which
dashboard to write, the icons, the leaf title suffix, which inline feature each tile gets, and the
preset buttons. The generalisation was done before the second domain existed rather than after, on
the grounds that the second case was already known and specified, which is the condition under which
speculative abstraction is usually worth it.

That mostly held. A/V was added on 2026-08-05 as a table entry, but it also needed one small change
to the code, described below, because the area card cannot control a media player. The prediction
that a new domain would be pure configuration was therefore close but not exact, and the reason is
worth recording: the table can only express choices the underlying cards actually support.

## A/V, the second domain

Built 2026-08-05 over the 11 `media_player` entities. Only three areas are populated: Living Room,
Office and Gym. Everything else is a card without a tap action, exactly as with lights.

Two things differ from the lights case.

**No inline area toggle.** The level 2 area card offers an `area-controls` feature, and the lights
dashboard uses it to put a room-wide toggle on each populated card. That feature does not cover media
players. `AREA_CONTROL_DOMAINS` in the frontend is `light`, `fan`, the `cover-*` variants and
`switch`, and nothing else
([source](https://github.com/home-assistant/frontend/blob/dev/src/panels/lovelace/card-features/types.ts)).
Configuring `media_player` there would have produced a feature that silently does nothing, so
`area_control` was made optional instead and the A/V cards are tappable with no inline control. The
presets on the leaf still cover the room-wide case.

**Duplicate players.** Music Assistant mirrors players it adopts, so a single physical device appears
more than once. The generator has no way to tell a mirror from an original, so this was fixed at the
source by hiding the redundant entity in the registry rather than by filtering in the dashboard.
`group_by_area()` already skips anything hidden or disabled, so a regeneration picks the change up.

The obvious rule, hide everything Music Assistant duplicates, is wrong here. Music Assistant is not
consistently the redundant side:

| Physical device | Kept | Hidden | Why that way round |
| :--- | :--- | :--- | :--- |
| Gym Sonos | `gym_gym` (sonos) | `gym` (MA), `gymnasium` (MA) | `gym` carries the same `RINCON_…` unique ID as the Sonos entity; `gymnasium` is a stale AirPlay view and was unavailable |
| carol | `carol_2` (MA) | `carol` (cast) | the cast entity is the dead one |
| LSX II-045089 | `lsx_ii_045089_2` (MA) | `lsx_ii_045089` (cast) | the MA entity is the one assigned to the Office area |

Hiding uniformly by platform would have left `carol` as a dead entity and, worse, emptied the Office
area entirely, since its only assigned player is the Music Assistant one. The rule that actually
holds is to keep whichever entity of a pair is live and area-assigned, whatever platform it came
from. Identifying the pairs is best done on `unique_id` rather than on name, since only the Gym pair
shares a name.

Hiding is not disabling. All four entities still hold state and still answer service calls; they are
only kept out of auto-generated UI. The Sound dashboard is unaffected because the HOMEii Flow card
talks to the Music Assistant server directly rather than through entity IDs.

The presets are All Off, Play, Pause and Mute, all area-targeted in the same way as the lights
presets, so they need no per-room entity data.

## The alarm dashboard

The Alarm System dashboard exists and carries the standard header, but has no content, because there
are no `alarm_control_panel` entities yet. The DSC panel's model is still unidentified and that is
the blocking item, so there is nothing to generate a dashboard from. It is deliberately not in the
`DOMAINS` table: adding it before the entities exist would produce a grid where no area is ever
tappable. See [crestron-strategy.md](crestron-strategy.md) for the state of that decision.

## What was verified

Confirmed by driving the real dashboard on 2026-08-04 rather than by reading the config back:

- Tapping a populated area card navigates to its leaf.
- The back button returns to level 2.
- Tapping an unpopulated area card does not navigate at all.
- All Off, Low and Bright drove both Office lights to 0, 25 and 100 percent, with neither light
  named anywhere in the button configuration.

## Related

- [dashboard-tablet-home.md](dashboard-tablet-home.md) for level 1, and for why kiosk-mode hiding
  HA's native chrome is what forced level 2 to grow its own title and level 3 its own back button.
- [dashboard-header-card.md](dashboard-header-card.md) for the date, time and weather banner the
  level 2 view carries, and the view-type constraint on reusing it elsewhere.
- [light-entity-strategy.md](light-entity-strategy.md) for how the light entities themselves are
  built and what happens to them when Crestron control arrives.
- [area-floor-layout.md](area-floor-layout.md) for the area and floor structure the area grid is
  generated from.
- [crestron-strategy.md](crestron-strategy.md) for the migration this navigation model is preparing
  for.
