# script.smart_toggle_lights decides one shared on/off direction for a group, not per-entity toggle

**Status:** Superseded by [ADR-0062](0062-native-dashboards-retired.md) — the pattern this decision applied to is retired.

A plain `light.toggle` call on an area or label target toggles each entity independently by its
own state — confirmed live: with the bedroom lights on and bath lights off, tapping a combined
On/Off button turned the bath on and the bedroom off, not the group one direction.
`script.smart_toggle_lights` checks whether any entity in the target is currently on and turns the
whole group off if so, on otherwise, so a single room-wide button makes one coherent decision for
the group. See [docs/native-dashboards/native-dashboards-retired.md](../native-dashboards/native-dashboards-retired.md).

## Consequences

The script's fields are named `target_area_id`/`target_label_id`, not `area_id`/`label_id` — not a
style choice. HA's template engine registers `area_id()` etc. as built-in Jinja globals available
in any template regardless of script fields, so a field literally named `area_id` silently
resolves to that built-in function (a truthy object) instead of the caller's value when the field
isn't supplied, and `default()` never catches it since the result isn't `Undefined`. The first
version of this script had exactly that bug.
