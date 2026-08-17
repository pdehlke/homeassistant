# Route the Climate chip through Home Assistant's native more-info dialog

Homie's Climate overlay was a from-scratch reimplementation of HA's climate more-info dialog
(hand-drawn dial, +/- buttons, mode/preset/fan rows) that broke silently twice in five days, each
time with no client-visible error to catch it. Since Homie's iframe is same-origin with its
parent HA frontend, dispatching HA's own `hass-more-info` `CustomEvent` on the parent document
opens the real dialog instead of a lookalike; roughly 940 lines of hand-rolled markup/CSS/JS were
deleted, not just left unused. See [docs/homie-dashboard/homie-climate-native-dialog.md](../homie-dashboard/homie-climate-native-dialog.md).

## Considered Options

- Nested iframe to a dedicated single-entity native dashboard per zone — rejected once cross-frame
  dispatch was confirmed to work directly, no benefit to the extra maintenance.
- Keep hand-rolling toward pixel/behavior parity — rejected as the same maintenance pattern that
  already produced two rounds of silent breakage.

## Consequences

An unrelated, already-scoped project-todo item (a temperature/humidity history graph for the
overlay) became moot for free, since the real dialog already has a recorder-backed History
section built in.
