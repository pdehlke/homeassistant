# Scene chip on-state: any controlled entity currently on

HA's `scene.*` entities carry no on/off state of their own, only a last-activated timestamp, so
the Scenes chip needed to define "on" itself. Chosen: any entity the scene controls is currently
on, read live from the scene's own `attributes.entity_id` rather than duplicated in config — the
same any-on-counts convention already used by Lights and Climate elsewhere on the dashboard.
Rejected: a separately tracked boolean (drifts from reality the moment anything outside the
dashboard changes a light) and matching the exact scene snapshot (too strict — a light nudged a
few percent off its scene-defined brightness would read "off" for a scene a person would call
active). See [docs/homie-dashboard/homie-scenes-chip.md](../homie-dashboard/homie-scenes-chip.md).
