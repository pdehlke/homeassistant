# Scene off turns off every controlled entity directly, no automation wrapper

Pointing a chip straight at a `scene.*` entity doesn't work: Homie's stock popup fires
`automation.trigger`, which HA silently no-ops against a non-automation entity. The first working
version wrapped each scene in a dedicated HA automation, but that only ever fired the scene
forward; reversing it would have meant a second automation per scene, or bypassing the wrapper for
the off path only. The final design branches on entity domain and calls `scene.turn_on` directly
for "on," and `homeassistant.turn_off` targeting every entity the scene controls for "off,"
removing the automation indirection entirely. See [docs/homie-dashboard/homie-scenes-chip.md](../homie-dashboard/homie-scenes-chip.md).
