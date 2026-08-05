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
| 1 | Root | One card per domain | Not built. The sidebar stands in for it |
| 2 | Domain | One card per area | Built for lights |
| 3 | Leaf | One domain in one area | Built for lights |

Level 1 is deliberately deferred. The sidebar already lists the domain dashboards, so it does the
same job with no work, and building the real thing is trivial whenever it is wanted.

## Level 2, the area grid

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
keeps it out of the tab bar and gives a back button that returns to level 2.

The leaf holds three things in order:

1. Room-wide preset buttons.
2. Any real scene entities assigned to that area, omitted entirely when there are none.
3. One tile per entity, each with the appropriate inline control. For lights that is a brightness
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

## Generation

None of this is hand-edited. `rebuild-domain-dashboard.py`, in the `home-assistant` agent skill,
reads the live floor, area, entity and device registries and rewrites the entire dashboard including
every leaf. Editing a dashboard by hand in the UI will be overwritten the next time it runs.

It resolves an entity's area the same way Home Assistant does, using the entity's own `area_id` when
set and falling back to the area inherited from its device, and it skips disabled and hidden
entities.

Run it after adding, removing, renaming or re-flooring an area, and after adding entities that
change whether an area counts as populated.

Two safety behaviours are worth knowing. It copies the level 2 header card verbatim and refuses to
save if the live config has none, so the hand-authored date, time and weather banner cannot be lost
by a regeneration. And it writes a timestamped backup of the existing config before every save,
because a Lovelace save replaces the whole dashboard rather than merging.

### Adding a domain

Everything domain-specific lives in a single `DOMAINS` table: which entity domains count, which
dashboard to write, the icons, the leaf title suffix, which inline feature each tile gets, and the
preset buttons. Adding A/V means adding a block to that table, not writing code. The generalisation
was done before the second domain existed rather than after, on the grounds that the second case was
already known and specified, which is the condition under which speculative abstraction is usually
worth it.

## What was verified

Confirmed by driving the real dashboard on 2026-08-04 rather than by reading the config back:

- Tapping a populated area card navigates to its leaf.
- The back button returns to level 2.
- Tapping an unpopulated area card does not navigate at all.
- All Off, Low and Bright drove both Office lights to 0, 25 and 100 percent, with neither light
  named anywhere in the button configuration.

## Related

- [light-entity-strategy.md](light-entity-strategy.md) for how the light entities themselves are
  built and what happens to them when Crestron control arrives.
- [area-floor-layout.md](area-floor-layout.md) for the area and floor structure the area grid is
  generated from.
- [crestron-strategy.md](crestron-strategy.md) for the migration this navigation model is preparing
  for.
