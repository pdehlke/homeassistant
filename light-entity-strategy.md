# Creating light entities before Crestron control exists

How lights are represented in Home Assistant while the Crestron lighting bus is still unreachable,
and why they are built to survive being rewired to real control later rather than thrown away.

Established 2026-08-04 on Home Assistant 2026.7.4.

## The problem

The CLX lighting modules cannot be driven from Home Assistant yet. That work depends on the Path A
XSIG bridge described in [crestron-strategy.md](crestron-strategy.md), which has not been
commissioned. Until then there is nothing in the `light` domain at all, which makes it impossible to
lay out or test a lighting dashboard, or to write and try any automation that targets lights.

The goal is therefore light entities that behave like real lights now, and that become real lights
later without anything built on top of them having to change.

## The approach

Each light is three pieces, all created through the Home Assistant config flow with no YAML editing.

| Piece | Entity | Role |
| :--- | :--- | :--- |
| Toggle helper | `input_boolean.<name>_light_state` | Holds on/off |
| Number helper | `input_number.<name>_light_brightness` | Holds brightness, range 0 to 255, step 1 |
| Template light | `light.<name>` | The real entity. Reads the two helpers and writes back to them |

The template light is created from the Template helper, choosing the `light` domain. Its fields:

```yaml
state:    "{{ is_state('input_boolean.pool_bathroom_light_state', 'on') }}"
level:    "{{ states('input_number.pool_bathroom_light_brightness') | int(0) }}"

turn_on:
  - action: input_boolean.turn_on
    target: {entity_id: input_boolean.pool_bathroom_light_state}

turn_off:
  - action: input_boolean.turn_off
    target: {entity_id: input_boolean.pool_bathroom_light_state}

set_level:
  - action: input_number.set_value
    target: {entity_id: input_number.pool_bathroom_light_brightness}
    data: {value: "{{ brightness }}"}
  - action: input_boolean.turn_on
    target: {entity_id: input_boolean.pool_bathroom_light_state}
```

Template lights express brightness as 0 to 255, which is why the number helper uses that range
rather than a percentage. `set_level` also turns the light on, matching how a real dimmer behaves
when it receives a brightness command.

Because the Template helper produces no device, the area is set on the entity itself through the
entity registry rather than inherited from a device.

## Why this and not something simpler

Two shorter paths were tested first and both are dead ends on this instance.

| Option | Result | Verdict |
| :--- | :--- | :--- |
| Template light helper backed by two helpers | Works. Full on/off and brightness, config flow only, and the actions can be repointed later. | Chosen |
| `switch_as_x`, which converts an entity into a light | Its entity selector is hard filtered to `domain: ["switch"]`, so an `input_boolean` cannot feed it. Would need template switches first, which is more work than template lights and gives no brightness. | Rejected, cannot accept the input |
| The `demo` integration, which ships ready made lights | Its config flow aborts with `not_implemented`, so it is YAML only. It also provides a fixed handful of fixed names, which cannot match real rooms. | Rejected, no config flow |
| Writing `template:` light platform YAML by hand | Functionally equivalent, but needs a file edit on the Home Assistant machine plus a reload, and cannot be managed through the API. | Rejected, harder to manage |

## What happens when Crestron control arrives

Only the template light's three actions change. `turn_on`, `turn_off` and `set_level` get repointed
from the helper entities to whatever the Crestron bridge exposes, and `state` and `level` get
repointed at the corresponding Crestron feedback joins. The two helpers can then be deleted.

Everything else stays exactly as it is. The `light.<name>` entity IDs do not change, so dashboards,
area assignments, automations and scripts built against them keep working with no edits. That
stability is the whole reason for choosing template lights over any disposable approach, and it is
worth protecting: renaming these entity IDs later would undo the benefit.

## How the Lights dashboard reacts

The [Lights dashboard](area-floor-layout.md#how-this-interacts-with-the-lights-dashboard) shows one
card per area. An area card only gains an inline light toggle when that area actually contains at
least one light entity, which mirrors what Home Assistant's own `areas-overview` strategy does and
avoids rendering a dead control on empty rooms.

That logic lives in the dashboard's regenerate script rather than in the dashboard config, so adding
a light to a new area and rerunning the script is enough to make the toggle appear. The script
resolves an entity's area as its own `area_id` when set, falling back to the area inherited from its
device, which is the same order Home Assistant uses.

## Current inventory

Two lights exist from the first trial, assigned to the Office area:

- `light.pool_bathroom`
- `light.north_sink`

Their names describe fixtures elsewhere in the house, so the Office assignment is a testing
convenience rather than a claim about where they are.

Five more were added 2026-08-05, assigned to the Primary Suite area, this time with names that do
describe where they are:

- `light.bedroom_perimeter`
- `light.bedroom_diagonals`
- `light.bath_perimeter`
- `light.bath_diagonals`
- `light.hallway`

Same three-piece recipe, no changes. Created via the REST config flow API rather than the UI, which
only matters in that it made one gotcha avoidable up front: `input_number/create` takes an `initial`
field, so passing `initial: 255` at creation time means the very first `turn_on` never hits the
zero-brightness case described below at all, rather than needing a follow-up fix. Confirmed live: a
test `turn_on` at brightness 180 correctly set both helpers and reported back through `light.hallway`
before being turned off again to leave it in the same off state as every other light here.

Five more were added the same day, assigned to the Entry area:

- `light.door`
- `light.home_perimeter`
- `light.garage_sconces`
- `light.entry_perimeter`
- `light.entry_center`

Same recipe again, `initial: 255` included from the start this time too. No scenes and no
label-based sub-group presets for Entry yet, unlike Primary Suite's Bedroom/Bath split; nothing
about these five names implies a natural two-way grouping the way a bedroom and a bathroom under
one area do. Confirmed live with two calls to `script.smart_toggle_lights` targeting the Entry
area: all five went on together at brightness 255, then all five went off together, left off.

Three more went into Dining Room and five into Kitchen, same day:

- `light.table`, `light.north`, `light.south` (Dining Room)
- `light.range`, `light.island`, `light.pathway`, `light.cabinet`, `light.powder` (Kitchen)

Same recipe, no scenes, no group-preset labels for either area. Confirmed live the same way as
Entry: `script.smart_toggle_lights` targeting each area in turn brought all of that area's
lights on together at brightness 255, then off together, left off.

**Which CLX channel drives each of these is still unknown.** All seven lighting modules are labeled
`106 - Garage` in the MC2E program, which records where the hardware is racked and not what it
controls, so the channel to room mapping cannot be recovered from the console dumps already
collected. See the open verification checklist in
[crestron-migration.md](crestron-migration.md#open-verification-checklist). That mapping is a
prerequisite for the rewiring described above.

## Gotchas

The number helper starts at 0 unless told otherwise, so the very first `turn_on` after creating a
light reports the light as on at zero brightness, which looks broken. For the first two lights this
was fixed after the fact by setting both helpers to 255. For the five added later, passing
`initial: 255` to `input_number/create` avoided the bad state ever existing in the first place, which
is the better of the two and worth doing for any light created after this one. After the first real
use the behaviour is correct on its own regardless of which path got there, because the number
persists and acts as a last brightness memory across off and on cycles.

Setting brightness to 0 through the slider leaves the light on at zero rather than turning it off.
Real dimmers vary in how they handle this, and it is not worth adding conditional logic for a case
Home Assistant does not normally produce, since the frontend sends `turn_off` rather than a zero
brightness.
