# Build placeholder and light entities via Template Helper, never demo: or hand-written YAML

Every light entity, and later six of the seven missing Vision Sample placeholder entities, are
built as Template Helper config-flow entities (`input_boolean`/`input_number` backing) rather than
through the built-in `demo:` integration or hand-written `template:` YAML. This instance has no
file-edit path to `configuration.yaml` at all (no File Editor, Terminal & SSH, or Studio Code
Server add-on), and `demo:` is YAML-only besides, with a fixed entity set that doesn't match real
room names. `switch_as_x` was also rejected for lights specifically: its entity selector is hard
filtered to `domain: ["switch"]`, so an `input_boolean` can't feed it. See
`docs/areas-and-entities/light-entity-strategy.md` and
`docs/native-dashboards/native-dashboards-retired.md`.

## Consequences

`water_heater` has no Template Helper domain step, so it can't be built this way at all. Rather
than fall back to YAML for that one entity, `water_heater.demo_water_heater` was deliberately left
missing (an "Entity not found" tile) — a call made with pde directly rather than assumed.
