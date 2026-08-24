# Fridge failure alert

Automation that raises an alert when the fridge stops drawing power for long enough to suggest
the appliance, its breaker, or its outlet has failed.

| Object | Entity |
|---|---|
| Automation | `automation.fridge_failure_alert` (id `fridge_failure_alert`) |
| Helper | `sensor.fridge_on_time_3h` (history_stats, entry `01KZ6RW8CM0YSGS353JVRANRTY`) |
| Source | `binary_sensor.fridge_power`, `sensor.fridge_power` (Sense) |

Both are live and enabled. Verified working on 2026-08-04 against Home Assistant 2026.7.4.

## Why it exists

A failed fridge is expensive and silent. Nothing about a dead compressor announces itself until
the food is warm. Sense already measures the fridge circuit, so the failure signal is available
for free.

## How it works

Sense exposes two relevant entities:

| Entity | Meaning |
|---|---|
| `sensor.fridge_power` | instantaneous draw in watts |
| `binary_sensor.fridge_power` | `on` when Sense believes the fridge is drawing power |

A history_stats helper accumulates how many hours `binary_sensor.fridge_power` has spent `on`
across a rolling three hour window. The automation fires when that total falls near zero.

Helper configuration:

| Field | Value |
|---|---|
| `entity_id` | `binary_sensor.fridge_power` |
| `state` | `on` |
| `type` | `time` (result in hours) |
| `end` | `{{ now() }}` |
| `duration` | 3 hours |
| `state_class` | `measurement` |

Automation:

```yaml
triggers:
  - trigger: numeric_state
    entity_id: sensor.fridge_on_time_3h
    below: 0.05
    for:
      minutes: 10
conditions:
  - condition: not
    conditions:
      - condition: state
        entity_id: binary_sensor.fridge_power
        state: "on"
actions:
  - action: persistent_notification.create
    data:
      notification_id: fridge_failure
      title: Fridge may have failed
      message: >-
        The fridge has run for only
        {{ (states('sensor.fridge_on_time_3h') | float(0) * 60) | round(1) }} minutes in the
        last 3 hours. Last power reading: {{ states('sensor.fridge_power') }} W. Check the
        appliance, the breaker, and whether Sense still detects it.
  - action: notify.notify
    continue_on_error: true
    data:
      title: Fridge may have failed
      message: >-
        Only {{ (states('sensor.fridge_on_time_3h') | float(0) * 60) | round(1) }} min of
        running time in the last 3 hours. Last reading {{ states('sensor.fridge_power') }} W.
mode: single
```

### Choosing the threshold

A fridge compressor cycles constantly, so any threshold has to clear normal idle and defrost
gaps. Measured over a 22.5 hour window on 2026-08-03 and 2026-08-04:

| Measure | Value |
|---|---|
| Longest `off` run | 51 min |
| Median `off` run | 17 min |
| Longest `on` run | 111 min |
| Median `on` run | 20 min |
| Duty cycle | roughly 57% on |

At a 57% duty cycle a healthy fridge puts about 1.7 hours of running time into every three hour
window. The observed live value was 1.63 h. The threshold of 0.05 h, which is three minutes,
therefore sits roughly 30 times below normal. A dead fridge drives the helper to zero.

Detection latency is about three hours and ten minutes: the window has to almost empty, then the
`for: 10 minutes` hold has to elapse.

### Why the condition exists

history_stats recomputes from the recorder on restart. If Home Assistant restarts when the
recorder holds less than three hours of history, the helper reads artificially low and would
trip the trigger. Requiring `binary_sensor.fridge_power` to not currently be `on` suppresses
that, and is correct on its own terms, since a fridge actively drawing power has not failed.

## Why not a state trigger, which is what this used to be

The original version triggered on `binary_sensor.fridge_power` reading `off` continuously for
three hours. That automation was close to useless and the reason is not visible from reading it.

The Sense integration drops out briefly and often. Over the same 22.5 hour window,
`binary_sensor.fridge_power` went `unavailable` 12 times, each lasting about a minute:

| Measure | Value |
|---|---|
| Dropouts observed | 12 |
| Median gap between dropouts | 120 min |
| Longest gap between dropouts | 240 min |
| Gaps longer than 3 hours | 3 of 11 |

A `for:` duration on a state trigger requires the entity to hold that exact state continuously.
A transition from `off` to `unavailable` and back to `off` restarts the three hour clock from
zero. With dropouts arriving roughly every two hours and only 3 of 11 gaps exceeding three
hours, a genuine failure would most likely be interrupted before the timer matured. Rough
estimate: it would have failed to fire something like three times out of four.

The old description framed the `unavailable` behaviour as protection against false positives
from Sense outages, which it is. The cost of that protection was not accounted for. The same
mechanism suppressed true positives.

Accumulating `on` time sidesteps this entirely. A one minute dropout contributes no running
time, which is the truth, and resets nothing.

## Mobile push

The automation calls `notify.notify`, which fans out to every registered notification platform.
It is wrapped in `continue_on_error: true` so a notification failure can never prevent the
persistent notification, which is deliberately the first action.

**This does not reach a phone yet.** There is no `mobile_app` config entry on this instance and
no `notify.mobile_app_*` service, because the companion app has never been registered. Right now
`notify.notify` completes successfully and delivers to nothing.

Finishing it requires action on the phone and cannot be done server side:

1. Install the Home Assistant companion app on iOS or Android.
2. Sign in to `http://hass.ehlke.net` while on the home network.
3. The app registers itself, creating a `mobile_app` config entry and a
   `notify.mobile_app_<device>` service.

No automation edit is needed afterwards. `notify.notify` picks up the new platform
automatically.

Push works on a LAN-only instance with no remote access, as long as Home Assistant has outbound
internet. The alert leaves the instance to a push proxy rather than arriving over an inbound
connection.

## Remaining gaps

Nothing clears the notification when the fridge recovers. `notification_id: fridge_failure`
means repeat triggers overwrite the existing notification rather than stacking, but a companion
automation dismissing it on recovery would be tidier.

There is no equivalent freezer alert, deliberately. Sense's freezer detection looks unreliable:
`sensor.freezer_yearly_energy` reads 27.9 kWh against the fridge's 402.5 kWh, and
`sensor.freezer_power` currently reads 0 W with the binary sensor `off`. Confirm Sense is
actually tracking that appliance before building anything on those entities.

## Trigger history

Neither version has ever fired on real conditions. Both recorded triggers were manual tests:

| When | What |
|---|---|
| 2026-08-04T01:34:12Z | Test of the original state-trigger version |
| 2026-08-04T16:15:41Z | Test of the current version, after the rewrite |

A logbook entry carrying a `context_user_id` marks an API-initiated trigger rather than a real
one. Check that before reading anything into `last_triggered`.

The second test confirmed `script_execution: finished` with no error, both actions running, and
correctly rendered templates. The resulting notification was dismissed afterwards.

## Gotchas hit while building this

**Persistent notifications are not entities.** Recent Home Assistant versions removed them from
the state machine, so `GET /api/states` filtered on `persistent_notification.` returns nothing
whether or not notifications exist. That reads exactly like "no notifications" and is not.
Query them over WebSocket:

```bash
python3 scripts/haws.py '{"type":"persistent_notification/get"}'
```

**History timestamps must end in `Z`.** An ISO string with a `+00:00` offset silently returns an
empty array. A start time earlier than the oldest recorded data also returns an empty array
rather than the available subset, which is easy to misread as "no data" when the recorder simply
does not reach back that far. A 48 hour query returned nothing while a 24 hour query returned 86
events.

## Reproducing the measurements

```bash
U=http://hass.ehlke.net
S=$(python3 -c "import datetime;print((datetime.datetime.now(datetime.UTC)-datetime.timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ'))")
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$U/api/history/period/$S?filter_entity_id=binary_sensor.fridge_power&minimal_response"
```

Read the automation's current configuration with:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$U/api/config/automation/config/fridge_failure_alert"
```

Inspect a run with `trace/list` then `trace/get` over WebSocket, which reports
`script_execution` and any per-action error that `continue_on_error` swallowed.
