# Roborock maintenance alerts

The Roborock integration exposes four maintenance countdown sensors for the Q5 Max+:

| Maintenance item | Entity |
|---|---|
| Main brush replacement | `sensor.q5_max_main_brush_time_left` |
| Side brush replacement | `sensor.q5_max_side_brush_time_left` |
| Air filter replacement | `sensor.q5_max_filter_time_left` |
| Sensor cleaning | `sensor.q5_max_sensor_time_left` |

These are hour counters. Zero means Roborock considers the task due, and negative values mean it
is overdue. Home Assistant documents the first three as replacement intervals and the last as a
cleaning interval in the
[Roborock integration's supported entities](https://www.home-assistant.io/integrations/roborock/#sensor).
The Q5 Max+ exposes no dock maintenance-brush or strainer countdown, including among disabled
entities, so dock maintenance is outside this automation.

## Decision

Use one automation to reconcile four separate persistent notifications. Each maintenance item has
a stable notification ID. A counter at or below zero creates or updates that item's notification;
a counter above zero dismisses it after the corresponding Roborock counter is reset. An `unknown`
or `unavailable` counter leaves the existing notification unchanged so a temporary integration
failure cannot erase a legitimate reminder.

Run the reconciliation whenever any counter changes and when Home Assistant starts. Run it once
manually after creation so items already overdue appear immediately. The automation calls only
`persistent_notification` actions. It must not call `notify.*`, so these alerts remain in the Home
Assistant interface and do not reach phones.

## Rejected options

- Four independent automations repeat the same trigger, availability, and dismissal logic without
  adding useful isolation.
- A daily scheduled check can delay a new reminder by almost a day.
- Threshold-crossing triggers alone miss counters that were already overdue when the automation
  was created and can miss a transition while the integration is unavailable.
- One combined notification makes it harder to dismiss a completed task independently and obscures
  which Roborock counter was reset.

## Verification

Validate the live automation with Home Assistant's configuration checker, confirm its entity is
enabled, trigger one reconciliation, and inspect the automation trace. Then read persistent
notifications over Home Assistant's WebSocket API and confirm exactly the currently overdue items
exist under their stable IDs. No phone notification service should appear in the automation.
