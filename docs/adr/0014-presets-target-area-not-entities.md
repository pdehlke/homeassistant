# Preset buttons target areas or labels, never hardcoded entity lists

**Status:** Superseded by [ADR-0062](0062-native-dashboards-retired.md) — the pattern this decision applied to is retired.

Room-wide and group preset buttons issue `target: {area_id: ...}` / `{label_id: ...}` service
calls with no specific fixture named anywhere in the config, rather than listing entities
directly. This means a preset works in any room the moment it gains its first light with zero
per-room configuration, automatically covers fixtures added later (the normal case as Crestron
channels get mapped one at a time), and can't break when an entity is renamed. See
[docs/native-dashboards/native-dashboards-retired.md](../native-dashboards/native-dashboards-retired.md).
