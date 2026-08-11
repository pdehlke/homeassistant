# Home Assistant area and floor layout

The area and floor structure this instance uses, and the reasoning behind the parts of it that are
not obvious. Areas matter more than they first appear: they drive the auto-generated Overview
dashboard, the [Lights dashboard](#how-this-interacts-with-the-lights-dashboard), and any future
automation that targets a room rather than a list of entities.

Set up on 2026-08-04 on Home Assistant 2026.7.4.

## The layout

Two floors, thirteen areas.

| Floor | Area | Icon | What is in it today |
| :--- | :--- | :--- | :--- |
| Main Floor | Courtyard | `m3rf:chair-umbrella` | empty |
| Main Floor | Dining Room | `m3rf:table-restaurant` | CasaSolar South thermostat and system controls |
| Main Floor | Entry | `m3rf:door-front` | empty |
| Main Floor | Guest Suite | `m3rf:single-bed` | empty |
| Main Floor | Gym | `m3rf:fitness-center` | Sonos gym speaker and its DSP switches |
| Main Floor | Kitchen | `m3rf:kitchen` | empty |
| Main Floor | Living Room | `m3rf:chair-alt` | media players |
| Main Floor | North Mechanical Closet | `m3rf:air` | CasaSolar North air handler |
| Main Floor | Office | `m3rf:desk` | CasaSolar North thermostat, plus office audio |
| Main Floor | Outside | `m3rf:yard` | both outdoor HVAC units (heat pump, AC) |
| Main Floor | Primary Suite | `m3rf:king-bed` | empty |
| Garage | Garage | `m3rf:garage-home` | empty, reserved for the CLX lighting rack |
| Garage | Garage Mechanical Closet | `m3rf:air` | CasaSolar South furnace |

Several areas are deliberately empty. They exist so the structure is in place before the Crestron
lighting migration lands, since that work will assign a lot of entities at once and it is easier to
have the rooms already named correctly. See [crestron-strategy.md](../crestron/crestron-strategy.md).

The `m3rf:` icon prefix is the Rounded and Filled variant of the
[Material Symbols](https://github.com/beecho01/material-symbols) icon pack, chosen to match the
Frosted Glass theme. Not every Material Symbols icon has a Rounded variant, and referencing one that
does not exist renders a silently blank icon rather than an error, so verify a name before using it.

## Areas cannot contain other areas

The natural way to express "the garage mechanical closet is part of the garage" would be to nest one
area inside another. Home Assistant does not support that. An area registry entry has these fields:

```
aliases, area_id, created_at, floor_id, humidity_entity_id, icon, labels,
modified_at, name, picture, temperature_entity_id
```

There is no parent area field. The only containment Home Assistant offers is Floor to Area, exactly
one level deep, and an area belongs to at most one floor.

That is why the Garage is modelled as a floor rather than an area containing a closet. The floor
named Garage holds two areas, the Garage itself and the Garage Mechanical Closet, which is as close
to the intended nesting as the data model allows.

### Options considered for the garage grouping

| Option | Result | Verdict |
| :--- | :--- | :--- |
| Floor named Garage holding both areas | Real containment. Dashboards that group by floor render a Garage heading, so it nests visually as well as structurally. | Chosen |
| Two flat sibling areas, Garage and Garage Mechanical Closet | Simplest, and the naming implies the relationship, but nothing enforces or displays it. | Rejected, no grouping |
| A shared `garage` label on both areas | Labels are the cross-cutting grouping mechanism and can be targeted by automations. They produce no visual hierarchy on a dashboard. | Rejected, wrong tool for layout |

The mild oddity of the chosen option is that a "floor" here is not a storey. That is a naming
compromise, not a functional problem, and it is worth knowing about before someone later wonders why
the garage is a floor.

## The mechanical closets are separate areas from the rooms they serve

Each Lennox system is split across several devices: a thermostat and system controller, an indoor
air handler or furnace, and an outdoor unit. These are in genuinely different physical places, so
they are in different areas.

| System | Thermostat and controls | Indoor equipment | Outdoor unit |
| :--- | :--- | :--- | :--- |
| CasaSolar North | Office | North Mechanical Closet | Outside |
| CasaSolar South | Dining Room | Garage Mechanical Closet | Outside |

Keeping the equipment separate matters because area assignment is what a dashboard or automation
sees. Putting a furnace in the Dining Room because its thermostat is there would make any future
"what is in this room" view wrong.

The two mechanical closets share the `m3rf:air` icon so they read as the same class of space.

## Areas the Lennox integration created on its own

Installing the `lennoxs30` integration (see [lennoxs30-integration.md](../lennox-climate/lennoxs30-integration.md))
auto-created two areas, `basement` and `outside`, from the equipment locations the S30 reports.
Neither name was chosen by hand, and both needed attention.

`basement` was simply wrong. This house does not have one. The integration had placed four devices
there: both system controllers and both pieces of indoor equipment. Everything was reassigned to the
real rooms above and the area was deleted once it held zero devices and zero entities.

`outside` was correct in substance but arrived lowercase, inconsistent with every other area name.
It was renamed to `Outside`. Renaming an area changes only its display name, so the `area_id` is
still `outside`. That is harmless, because nothing references an area by its ID in a way that a
display rename would break.

Worth remembering for any future integration that reports equipment locations: it will invent areas
without asking, and those areas describe where the vendor thinks the hardware is, not how the house
is actually organised.

## Entity IDs still contain old area names

Entities that existed while the wrong areas were in place kept their original entity IDs. For
example `binary_sensor.basement_casasolar_south_casasolar_south_home_state` still says `basement`
even though that area no longer exists, and the entity now lives in the Dining Room.

This is deliberate. Home Assistant never rewrites an entity ID when a device changes area, and
renaming entity IDs by hand is the most breakage-prone operation available: IDs are referenced by
dashboards, scripts, scenes, and some integrations' stored config entry data, none of which update
automatically. The [Lennox Home dashboard](../lennox-climate/lennoxs30-integration.md) hardcodes several of these IDs.

The stale prefixes are cosmetic. Entity IDs are opaque strings, the UI displays friendly names
instead, and nothing behaves differently. Leave them alone unless there is a concrete reason.

## How this interacts with the Lights dashboard

The Lights dashboard runs the built-in `areas-overview` view strategy, which reads the area registry
live at render time. Anything in this document takes effect there without editing the dashboard:
creating an area adds a card, deleting one removes it, and renaming or re-iconing an area updates
it.

Because the strategy also groups by floor, defining Main Floor and Garage split that dashboard into
two headed sections that sit side by side. That was a side effect of the floor work rather than the
goal, and it is the only multi-column behaviour available there, since the strategy hardcodes
full-width area cards.

One ordering caveat. Floors render in registry creation order, not by their `level` value. The
Garage floor appears before Main Floor purely because it was created first, and setting `level: 0`
on Main Floor does not change that. Fixing the order means telling the strategy explicitly:

```yaml
strategy:
  type: areas-overview
  floors_display:
    order: [main_floor, garage]
```

This has not been applied. It is recorded here so the ordering is not mistaken for a bug later.
