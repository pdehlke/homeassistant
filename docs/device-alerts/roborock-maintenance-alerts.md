# Roborock Maintenance Alerts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this
> plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create separate Home Assistant interface notifications for each overdue Q5 Max+
maintenance counter without sending phone alerts.

**Architecture:** One live Home Assistant automation reconciles four stable persistent notification
IDs from four numeric countdown sensors. Every sensor change and Home Assistant start evaluates all
four items, creating overdue notifications, dismissing reset items, and preserving alerts through
temporary unavailable states.

**Tech Stack:** Home Assistant 2026.8.2 automation REST API, Jinja templates, persistent notification
actions, and Home Assistant WebSocket trace and notification APIs.

## Global constraints

- Use only the four Q5 Max+ maintenance entities listed below.
- Use only `persistent_notification.create` and `persistent_notification.dismiss` for user alerts.
- Never call `notify.*`; no phone alert may be sent.
- Keep one stable notification ID per maintenance item.
- Treat numeric states at or below zero as due, numeric states above zero as reset, and
  `unknown` or `unavailable` states as no change.

---

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

## Implementation task

### Task 1: Live maintenance notification automation

**Live objects:**

- Create: automation config ID `roborock_maintenance_alerts`
- Produce: entity `automation.roborock_maintenance_alerts`
- Produce: persistent notification IDs `roborock_maintenance_main_brush`,
  `roborock_maintenance_side_brush`, `roborock_maintenance_air_filter`, and
  `roborock_maintenance_sensors`
- Modify after verification: `docs/device-alerts/roborock-maintenance-alerts.md`

**Interfaces:**

- Consumes the four numeric sensor states listed above.
- Produces four independent Home Assistant interface notifications with automatic dismissal.

- [x] **Step 1: Verify the behavior is absent**

  Read `/api/config/automation/config/roborock_maintenance_alerts`, the automation entity, and
  `persistent_notification/get`. Confirm no automation or notification with the planned IDs exists.

- [x] **Step 2: Create the minimal live automation**

  Submit this payload to `/api/config/automation/config/roborock_maintenance_alerts`:

  ```json
  {
    "id": "roborock_maintenance_alerts",
    "alias": "Roborock maintenance alerts",
    "description": "Creates separate in-app reminders when a Q5 Max+ maintenance counter reaches zero, dismisses each reminder after its counter is reset, and leaves reminders unchanged while a counter is unavailable. Never sends phone notifications.",
    "triggers": [
      {
        "trigger": "state",
        "entity_id": [
          "sensor.q5_max_main_brush_time_left",
          "sensor.q5_max_side_brush_time_left",
          "sensor.q5_max_filter_time_left",
          "sensor.q5_max_sensor_time_left"
        ]
      },
      {
        "trigger": "homeassistant",
        "event": "start"
      }
    ],
    "conditions": [],
    "actions": [
      {
        "repeat": {
          "for_each": [
            {
              "entity": "sensor.q5_max_main_brush_time_left",
              "key": "main_brush",
              "task": "Main brush replacement",
              "instruction": "Replace the main brush, then reset its consumable counter."
            },
            {
              "entity": "sensor.q5_max_side_brush_time_left",
              "key": "side_brush",
              "task": "Side brush replacement",
              "instruction": "Replace the side brush, then reset its consumable counter."
            },
            {
              "entity": "sensor.q5_max_filter_time_left",
              "key": "air_filter",
              "task": "Air filter replacement",
              "instruction": "Replace the air filter, then reset its consumable counter."
            },
            {
              "entity": "sensor.q5_max_sensor_time_left",
              "key": "sensors",
              "task": "Sensor cleaning",
              "instruction": "Clean the vacuum sensors, then reset their consumable counter."
            }
          ],
          "sequence": [
            {
              "variables": {
                "counter_state": "{{ states(repeat.item.entity) }}"
              }
            },
            {
              "choose": [
                {
                  "conditions": [
                    {
                      "condition": "template",
                      "value_template": "{{ is_number(counter_state) and (counter_state | float) <= 0 }}"
                    }
                  ],
                  "sequence": [
                    {
                      "action": "persistent_notification.create",
                      "data": {
                        "notification_id": "roborock_maintenance_{{ repeat.item.key }}",
                        "title": "Roborock maintenance due: {{ repeat.item.task }}",
                        "message": "Q5 Max+ reports this task is overdue by {{ (0 - (counter_state | float)) | round(1) }} operating hours. {{ repeat.item.instruction }}"
                      }
                    }
                  ]
                },
                {
                  "conditions": [
                    {
                      "condition": "template",
                      "value_template": "{{ is_number(counter_state) and (counter_state | float) > 0 }}"
                    }
                  ],
                  "sequence": [
                    {
                      "action": "persistent_notification.dismiss",
                      "continue_on_error": true,
                      "data": {
                        "notification_id": "roborock_maintenance_{{ repeat.item.key }}"
                      }
                    }
                  ]
                }
              ]
            }
          ]
        }
      }
    ],
    "mode": "queued",
    "max": 10
  }
  ```

- [x] **Step 3: Validate creation**

  Call `/api/config/core/check_config` and require `result: valid`. Confirm
  `automation.roborock_maintenance_alerts` is enabled. Read the saved configuration and require
  one `persistent_notification.create` definition, one `persistent_notification.dismiss`
  definition, four stable notification IDs supplied by the loop, and zero `notify.*` actions.

- [x] **Step 4: Verify both reconciliation branches**

  Create a temporary `roborock_maintenance_main_brush` persistent notification while its counter is
  positive. Trigger `automation.roborock_maintenance_alerts` once with conditions skipped. Require
  the temporary main-brush notification to be dismissed, air-filter and sensor-cleaning
  notifications to exist, and no side-brush notification to exist.

- [x] **Step 5: Inspect execution evidence**

  Read the newest automation trace. Require `script_execution: finished` and no action errors. Read
  each resulting notification and confirm its displayed overdue hours agree with the corresponding
  live sensor value after rounding to one decimal place.

- [x] **Step 6: Record the verified result**

  Add the live automation ID, verification date, resulting notification IDs, and observed checks to
  this document. Run `git diff --check`, secret-scan the staged change, and commit with a
  Conventional Commit containing a body.

## Live result

Created `automation.roborock_maintenance_alerts` on 2026-08-17. Home Assistant's configuration
checker returned `valid` with no errors or warnings, and the automation entity was enabled. The
saved configuration contained the four intended sensor IDs, one persistent-notification create
definition, one persistent-notification dismiss definition, and no `notify.*` action.

The initial reconciliation exercised both action branches. A temporary
`roborock_maintenance_main_brush` notification was dismissed while its counter was positive. The
positive side-brush counter produced no notification. The two negative counters produced these
on-screen notifications:

| Notification ID | Sensor state | Displayed overdue time |
|---|---:|---:|
| `roborock_maintenance_air_filter` | -79.7381 h | 79.7 h |
| `roborock_maintenance_sensors` | -105.8564 h | 105.9 h |

Trace run `58102b4f0726298955156601f2d7944a` finished with no action errors. The main-brush and
side-brush notification IDs were absent after the run, and the two overdue notification messages
matched their live counter states rounded to one decimal place.
