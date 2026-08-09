# Climate chip's "N on" count: activity, not mode

The Climate chip on Overview A and B said "2 on" while South was idle and North was actively
cooling. Fixed to count only thermostats actually heating or cooling right now, so the same
moment now reads "1 on."

## The problem

Both real thermostats run in `heat_cool` mode nearly all the time (see
[lennoxs30-integration.md](lennoxs30-integration.md)'s "Known quirk" section and
[homie-thermostat-control-fix.md](homie-thermostat-control-fix.md)), so their `climate.*` entity
state is essentially never `"off"`. The chip's on-count, in `refreshControls()`, was using the
generic `entityIsOn(state, entity)` helper, whose climate branch is `state !== "off"`. Against
these two entities that condition is true almost permanently, regardless of whether either unit
is actually running: it was counting "enabled" as "on," not "actively conditioning."

Overview C's sidebar icon glow had already solved exactly this problem, in a `climateIsActive()`
helper local to `_refreshOv3SidebarControls()`, reading the `hvac_action` attribute
(`"heating"`/`"cooling"`) instead of `state`. That fix was never applied to the Overview A/B chip
count, which is a separate piece of code, so the two screens disagreed about what "on" meant for
the same entities.

## The fix

`climateIsActive(entity)` was hoisted from a closure inside `_refreshOv3SidebarControls()` to a
shared, module-scope function (next to `entityIsOn()`), and `refreshControls()`'s climate branch
now calls it instead of `entityIsOn()`:

```js
if (isClimateChip) {
  activeCount = allSubs.filter(s => climateIsActive(s.entity)).length;
} else {
  activeCount = allSubs.filter(s => {
    const d = haGetCached(s.entity);
    return d && entityIsOn(d.state, s.entity);
  }).length;
}
```

Both the printed count and the chip's own lit/dim glow come from the same `activeCount > 0` value
that already drove both, so fixing the count fixed the glow at the same time; no separate change
needed there. Overview B's sidebar list mirrors Overview A's rendered chip text rather than
recomputing anything, so it picked up the fix automatically.

## What this intentionally does not touch

- **Overview C's sidebar icon** already used `climateIsActive()`; unchanged in behavior, now
  reading the shared definition instead of its own local copy.
- **The AC control card's own on/off toggle** (`_acCardState.isOn`, driven by `hvac_mode`, not
  `hvac_action`) is untouched. That toggle means "is the system enabled at all," which is a
  different and equally correct concept from "is it actively conditioning right now." Confirmed
  with pde before changing anything: this fix is scoped to the Overview A/B/C summary displays
  only.
- **The old `_acCardState`-based instant-feedback path** for the chip count, which updated the
  count immediately when the AC card's own toggle was tapped, is gone. Kept deliberately: activity
  can't be known optimistically (real compressor lag exists between "enabled" and "actually
  running"), so an instant update was never honestly representing activity in the first place.
  Confirmed with pde that a few seconds of lag after a manual toggle, matching what Overview C's
  glow already has, is the right trade.

## Verification

`test/screen-a.test.cjs`: `climateIsActive()` exists exactly once at module scope and reads
`hvac_action`; both `_refreshOv3SidebarControls()` and `refreshControls()` call it; the old
`_acCardState`-optimistic path is gone from `refreshControls()`. 58/58 passing.

Deployed live (`HOMIE_ASSET_VERSION` `20260809.2` → `20260809.3`, Lovelace iframe `?v=` bumped to
match, same two-boundary cache-busting requirement recorded in
[overview-c-solar-home-green-percentage.md](overview-c-solar-home-green-percentage.md)) and
confirmed against real data: South `hvac_action: idle`, North `hvac_action: cooling`. Overview A's
Climate chip read "1 on," matching what was asked.
