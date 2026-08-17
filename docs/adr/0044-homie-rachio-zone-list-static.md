# Homie's Rachio zone list stays static, not dynamically enumerated

Two places outside the Rachio alert automations, Homie Dashboard's Irrigation control
(`dist/config.js`) and the `sensor.homie_irrigation_status` template helper, hardcode the zone
list rather than enumerating it at runtime via `device_entities()`, the way the alert automations
already do. Making either dynamic was considered and rejected: zone additions or deletions are
rare, maybe once every few years, and the cost of a dynamic implementation isn't worth it against
occasionally noticing a zone is missing and updating two lists by hand. A standing decision, not an
open TODO, confirmed live when North's re-enablement required exactly that manual update. See
[docs/rachio/rachio-zone-disabled-alert.md](../rachio/rachio-zone-disabled-alert.md).
