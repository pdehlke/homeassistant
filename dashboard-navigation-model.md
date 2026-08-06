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
| 1 | Root | Tab selection on Home itself | Built, see [dashboard-home.md](dashboard-home.md) |
| 2 | Domain | One card per area | Built for lights and A/V |
| 3 | Leaf | One domain in one area | Built for lights and A/V |

Level 1 went through two shapes before landing here. It was deferred at first: the sidebar already
listed the domain dashboards, so it did the same job with no work. Then, once a kiosk device needed
a real level 1 to put its default dashboard on and the sidebar was no longer available to stand in
for it, it became its own root dashboard, Tablet Home, a 2x2 grid of cards each navigating to a
domain's standalone dashboard. That lasted less than a day: the kiosk user's default dashboard was
retargeted to Home (`url_path: vision-sample`), whose own native view tabs (Home, Lights, A/V,
Alarm, Climate) now do level 1's job directly, one tab per domain, with no separate dashboard or
button-grid step involved. See [dashboard-home.md](dashboard-home.md) for the full story, including
why the Tablet Home root dashboard is now considered dead.

## Level 2, the area grid

The page opens with a title-only heading, the domain name and its icon, no cards under it. This
exists for the same reason the leaf grew its own back button: kiosk-mode hides HA's native top app
bar for the Tablet kiosk user on these standalone domain dashboards (see
[dashboard-home.md](dashboard-home.md)), which is the only other place the view's title (`Lights`,
`A/V`, ...) would ever render, and without it every domain dashboard's floor sections look
identical.

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
bar. That native back button is invisible to anyone using the Tablet kiosk user on these standalone
dashboards (see [dashboard-home.md](dashboard-home.md)), whose kiosk-mode setup hides that whole
bar, so the leaf also
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

The current presets are On/Off, Low at 25 percent, Medium at 60 percent, and Bright at 100 percent.
On/Off was `light.turn_off`, labelled "All Off", until 2026-08-05, when it became a real toggle so
one button could do both directions. See below for why that took a script rather than a service
call.

### On/Off needed a script, because a plain toggle on a group is not one decision

The first attempt at a toggle button called `light.toggle` directly on the area or label target.
That is wrong for a group with more than one member, confirmed by actually using it: with the
bedroom lights on and the bath lights off, tapping Primary Suite's On/Off turned the bath on and
the bedroom off, because `light.toggle` on a multi-entity target toggles each entity by its own
state, not the group by one shared decision. There is no HA service that looks at a whole target and
picks a single on-or-off direction for it.

`script.smart_toggle_lights` does that instead. Given a `target_area_id` or a `target_label_id`, it
resolves the light entities in that area or label
([`area_entities()`](https://www.home-assistant.io/template-functions/area_entities/) /
[`label_entities()`](https://www.home-assistant.io/template-functions/label_entities/)), checks
whether any of them is on, and turns the whole group off if so, or on if not.
`preset_card()` routes any `script.*` preset action through the script's own fields as `data` rather
than through a service `target:`, since a script's fields are not a target. Confirmed live, both
directions, by reproducing the exact reported case: bedroom on, bath off, tapping the room-wide
On/Off button turned all five Primary Suite lights off together, not toggled per fixture.

**The fields are named `target_area_id` and `target_label_id`, not `area_id` and `label_id`, and
that is not a style choice.** Home Assistant's template engine registers `area_id()`, `area_name()`,
`area_entities()`, `label_id()`, `label_entities()`, and others as built-in Jinja global functions,
available in any template regardless of what script fields exist. A script field named `area_id`
that is not supplied for a given call is not empty or undefined inside the template; Jinja resolves
the bare name against its own global environment first and finds the built-in `area_id` function
instead, which is a function object, and therefore truthy. `{{ area_id | default(omit) }}` never
falls back, because `default()` only triggers on `Undefined`, and a function object is not that. The
first version of this script had exactly that bug: naming both fields `area_id`/`label_id` after the
service `target:` fields they were meant to mirror. It traced as `target_entities: []`, `any_on:
false`, and a rendered service target containing the literal string
`<function AreaExtension.area_id at 0x...>`, caught by reading the script's own trace
(`trace/get`) rather than by guessing from the wrong output, exactly the kind of failure that looks
like a different bug (a resolution problem, an empty area) until the trace is actually read.

Real Home Assistant scenes were considered as the mechanism and rejected as the *only* mechanism,
because a scene is a snapshot of named entities at named states and therefore cannot be written for
a room whose fixtures are unknown. Scenes are instead layered in on top: any `scene` entity assigned
to an area appears in its own section on that area's leaf, so faithful Crestron presets can be added
per room as the channel map lands, without waiting for all of them.

`scene.bedroom_evening` is the first one, added 2026-08-05: `light.bedroom_perimeter` on at
brightness 76, `light.bedroom_diagonals` off, `light.hallway` on at brightness 26. It is the concrete
illustration of what a preset cannot be. The Bedroom group preset's Low button sets every bedroom
light to the *same* 25 percent; this scene sets three different levels, one of them off, because that
combination is what "evening" is supposed to look like in that room, not "everything a bit dim."
Built through the same config-editor REST endpoint the automations and scripts here use
(`/api/config/scene/config/<id>`), assigned to Primary Suite through the entity registry exactly like
the lights themselves, since a scene has no device to inherit an area from either. Confirmed live:
it appears in the Scenes section on the Primary Suite leaf, its more-info dialog lists the three
entities with an Activate button rather than firing on a bare tap, and Activate set all three lights
to precisely the stored levels, bath fixtures untouched.

`scene.bathroom_evening` followed the same day: `light.bath_perimeter` on at 76, `light.bath_diagonals`
off, `light.hallway` on at 26, same numbers as the bedroom scene, same hallway entry in both. Both
scenes claiming the hallway is intentional and harmless, not a conflict to resolve; whichever one is
activated last is the one whose hallway level stands, exactly as if the hallway belonged to both
rooms, which on this floor plan it effectively does. Confirmed live the same way: Activate on
Bathroom Evening set the bath fixtures and left the bedroom lights, already on from testing the first
scene, untouched.

Both scenes sort into the Scenes section alphabetically, no ordering config of their own; nothing in
the generator controls it because nothing needed to yet.

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

A label is not exclusive to one row. `light.hallway` carries both `bath` and `bedroom`, so it answers
to either group's row while still being one fixture, not a third row of its own. That is the same
reason labels were chosen over a stricter one-fixture-one-group scheme: an entity can belong to
however many groups actually describe it, the way a hallway genuinely sits between both.

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
[the Tablet Home work](dashboard-home.md) added a root-level `kiosk_mode` key to the
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

- [dashboard-home.md](dashboard-home.md) for level 1, and for why kiosk-mode hiding HA's native
  chrome forced level 2 to grow its own title and level 3 its own back button on the standalone
  domain dashboards, though not on Home's own tabs, which keep their native header.
- [dashboard-header-card.md](dashboard-header-card.md) for the date, time and weather banner the
  level 2 view carries, and the view-type constraint on reusing it elsewhere.
- [light-entity-strategy.md](light-entity-strategy.md) for how the light entities themselves are
  built and what happens to them when Crestron control arrives.
- [area-floor-layout.md](area-floor-layout.md) for the area and floor structure the area grid is
  generated from.
- [crestron-strategy.md](crestron-strategy.md) for the migration this navigation model is preparing
  for.
