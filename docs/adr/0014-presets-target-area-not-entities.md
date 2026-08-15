# Preset buttons target areas or labels, never hardcoded entity lists

Room-wide and group preset buttons issue `target: {area_id: ...}` / `{label_id: ...}` service
calls with no specific fixture named anywhere in the config, rather than listing entities
directly. This means a preset works in any room the moment it gains its first light with zero
per-room configuration, automatically covers fixtures added later (the normal case as Crestron
channels get mapped one at a time), and can't break when an entity is renamed. See
`docs/native-dashboards/dashboard-navigation-model.md`.
