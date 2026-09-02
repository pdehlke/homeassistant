# Build placeholder and light entities via Template Helper, never demo: or hand-written YAML

Every light entity, and later six of the seven missing Vision Sample placeholder entities, are
built as Template Helper config-flow entities (`input_boolean`/`input_number` backing) rather than
through the built-in `demo:` integration or hand-written `template:` YAML. This instance has no
file-edit path to `configuration.yaml` at all (no File Editor, Terminal & SSH, or Studio Code
Server add-on), and `demo:` is YAML-only besides, with a fixed entity set that doesn't match real
room names. `switch_as_x` was also rejected for lights specifically: its entity selector is hard
filtered to `domain: ["switch"]`, so an `input_boolean` can't feed it. See
[docs/areas-and-entities/light-entity-strategy.md](../areas-and-entities/light-entity-strategy.md) and
[docs/native-dashboards/native-dashboards-retired.md](../native-dashboards/native-dashboards-retired.md).

## Consequences

`water_heater` has no Template Helper domain step, so it can't be built this way at all. Rather
than fall back to YAML for that one entity, `water_heater.demo_water_heater` was deliberately left
missing (an "Entity not found" tile) — a call made with pde directly rather than assumed.

## The no-file-access premise is obsolete (2026-09-02)

The reasoning above rests on this instance having no file-edit path to `configuration.yaml` at all.
That stopped being true when the Advanced SSH & Web Terminal add-on was installed. `/config` is
now fully reachable over SFTP, `configuration.yaml` is editable, `custom_components/` exists and
holds eight integrations, and `command_line:` sensors already shell out to `/config/scripts/`.

This does not reverse the decision. Template helpers were still the right way to build placeholder
lights, and the entity IDs they established are the thing the Crestron bridge was designed to
inherit. What it changes is that "we cannot write files" is no longer a reason to reject an option,
so any future choice between a helper and a custom integration has to be argued on its merits
rather than on access. In particular, a native `light` platform serving these same thirty entity
IDs is now buildable, and choosing not to build one is a live decision rather than a constraint.
