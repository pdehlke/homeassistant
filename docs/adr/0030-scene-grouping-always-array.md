# Scene grouping: always an array field

Letting one bubble activate and clear more than one scene together (e.g. a combined "Primary
Suite Evening") could have added a separate `isGroup`/`groupEntities` field alongside the existing
singular `entity` field, but that means two shapes to keep in sync in every function that reads a
scene, and every future single-scene entry would still need to know which field it uses. Chosen
instead: every scene entry's field is always an array (`entities: [...]`), so a single-scene
bubble is just the one-element case rather than a distinct kind of bubble. See
[docs/homie-dashboard/homie-scenes-chip.md](../homie-dashboard/homie-scenes-chip.md).
