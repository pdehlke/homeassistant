# Group-level presets use HA labels, not nested areas or hardcoded entities

**Status:** Superseded by [ADR-0062](0062-native-dashboards-retired.md) — the pattern this decision applied to is retired.

Primary Suite's bedroom/bath fixture split needs a grouping level between "whole area" and "one
fixture," which HA areas can't express since they can't nest (see the Garage floor ADR for the
same underlying limitation applied to a different problem). Rather than hardcode the `light.bath_*`
entity names directly — breaking the same area-targeting guarantee presets exist for — ordinary
labels (`bath`, `bedroom`) applied to entities carry the area-targeting idea down one level; a
group preset row targets `label_id` the same way a room-wide preset targets `area_id`. Because a
label isn't exclusive, a fixture genuinely shared between groups (the hallway carries both labels)
answers to both rows without being duplicated or needing a third row of its own. See
[docs/native-dashboards/native-dashboards-retired.md](../native-dashboards/native-dashboards-retired.md).
