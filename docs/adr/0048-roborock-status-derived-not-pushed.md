# Roborock dashboard status derived from cleaning state and battery, not the frozen push fields

The periodic reload mitigant left the dashboard-facing pill's actual effect genuinely unresolved,
and it still depended on the exact fields proven to freeze
(`binary_sensor.q5_max_charging`/`sensor.q5_max_status`). Rather than wait to see whether reloads
reliably correct them, `sensor.homie_robot_status`'s template was rewritten to derive its value
from `binary_sensor.q5_max_cleaning` and `sensor.q5_max_battery` instead, both proven by the same
incident's evidence to keep updating normally through the entire stall that froze the push fields.
Implemented as the same UI-managed template-sensor pattern every other Homie status pill uses,
rejecting a Homie-fork-side JS reimplementation so this pill stays consistent with its siblings
rather than becoming the one computed differently. See
`docs/device-alerts/roborock-status-mqtt-stall.md`.
