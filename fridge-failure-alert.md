# Fridge failure alert

Automation that raises an alert when the fridge stops drawing power for long enough to suggest
the appliance, its breaker, or its outlet has failed.

Entity: `automation.fridge_failure_alert`, id `fridge_failure_alert`. Enabled and live.

## Why it exists

A failed fridge is expensive and silent. Nothing about a dead compressor announces itself until
the food is warm. Sense already measures the fridge circuit, so the failure signal is available
for free.

## How it works now

Sense exposes two relevant entities:

| Entity | Meaning |
|---|---|
| `sensor.fridge_power` | instantaneous draw in watts |
| `binary_sensor.fridge_power` | `on` when Sense believes the fridge is drawing power |

The automation triggers on `binary_sensor.fridge_power` reading `off` continuously for three
hours, and creates a persistent notification carrying the last wattage reading.

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.fridge_power
    to: "off"
    for:
      hours: 3
conditions: []
actions:
  - action: persistent_notification.create
    data:
      notification_id: fridge_failure
      title: Fridge may have failed
      message: >-
        binary_sensor.fridge_power has read off for 3 hours straight. Last power reading:
        {{ states('sensor.fridge_power') }} W. Check the appliance, the breaker, and whether
        Sense still detects it.
mode: single
```

## Why three hours

A fridge compressor cycles constantly, so any threshold has to clear normal idle and defrost
gaps. Measured over a 22.5 hour window on 2026-08-03 and 2026-08-04:

| Measure | Value |
|---|---|
| Longest `off` run | 51 min |
| Median `off` run | 17 min |
| Longest `on` run | 111 min |
| Median `on` run | 20 min |
| Duty cycle | roughly 57% on |

Three hours sits well clear of the 51 minute worst case. It could be tightened toward 90
minutes once there is a longer history to confirm the real distribution, which would cut the
detection delay in half.

## Known defect: the alert will usually fail to fire

This is the important part of the document. The automation is currently unreliable, and the
reason is not obvious from reading it.

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
zero.

Since dropouts arrive roughly every two hours and only 3 of 11 observed gaps exceeded three
hours, a genuine fridge failure would most likely be interrupted by a dropout before the timer
matured. Rough estimate: the alert fails to fire something like three times out of four.

The automation's own description frames the `unavailable` behaviour as protection against false
positives from Sense outages, which it is. The cost of that protection was not accounted for.
The same mechanism suppresses true positives.

### Proposed fix, not yet implemented

Measure accumulated `on` time over a rolling window instead of requiring an unbroken run of
`off`. Brief dropouts then contribute no `on` time without resetting anything.

Add a [history_stats](https://www.home-assistant.io/integrations/history_stats/) helper:

```yaml
sensor:
  - platform: history_stats
    name: Fridge on time 3h
    entity_id: binary_sensor.fridge_power
    state: "on"
    type: time
    end: "{{ now() }}"
    duration:
      hours: 3
```

Then trigger on that helper falling near zero:

```yaml
triggers:
  - trigger: numeric_state
    entity_id: sensor.fridge_on_time_3h
    below: 0.05
    for:
      minutes: 10
```

Normal cycling puts roughly 1.7 hours of `on` time in every 3 hour window, so the margin against
a 0.05 hour threshold is very wide. A dead fridge drives it to zero regardless of how many times
Sense blinks.

## Other gaps

The action creates a persistent notification only, which appears in the Home Assistant UI and
nowhere else. If nobody opens the dashboard, nobody learns the fridge died. Adding a mobile push
via the companion app would fix this, and matters more than any threshold tuning.

Nothing clears the notification when the fridge recovers. `notification_id: fridge_failure` at
least means repeat triggers overwrite the existing notification rather than stacking up, but a
second automation dismissing it on recovery would be tidier.

There is no equivalent freezer alert, deliberately. Sense's freezer detection looks unreliable:
`sensor.freezer_yearly_energy` reads 27.9 kWh against the fridge's 402.5 kWh, and
`sensor.freezer_power` currently reads 0 W with the binary sensor `off`. Confirm Sense is
actually tracking that appliance before building anything on those entities.

## Trigger history

`last_triggered` reads `2026-08-04T01:34:12Z`. That was a manual test, not a real event. The
logbook entry carries a `context_user_id`, which marks an API-initiated trigger, and
`binary_sensor.fridge_power` was reading `on` at the time.

The automation has never fired on real conditions.

## Reproducing the measurements

History comes from the REST API. Timestamps must use a trailing `Z`; an ISO string with a
`+00:00` offset silently returns an empty array. A start time earlier than the oldest recorded
data also returns an empty array rather than the available subset, which is easy to misread as
"no data" when the recorder simply does not go back that far.

```bash
U=http://homeassistant.local:8123
S=$(python3 -c "import datetime;print((datetime.datetime.now(datetime.UTC)-datetime.timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ'))")
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$U/api/history/period/$S?filter_entity_id=binary_sensor.fridge_power&minimal_response"
```

Read the automation's current configuration with:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$U/api/config/automation/config/fridge_failure_alert"
```
