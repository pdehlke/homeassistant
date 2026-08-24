# Low grid export alert

Automation that checks yesterday's net solar export every morning and notifies when it was low
or when the house was a net importer for the day.

| Object | Entity |
|---|---|
| Automation | `automation.low_grid_export_alert` (id `low_grid_export_alert`) |
| Source | `sensor.sense_287516_daily_to_grid`, `sensor.sense_287516_daily_from_grid` (Sense) |

Live and enabled. Created and verified 2026-08-20 against Home Assistant 2026.8.1.

## Why it exists

pde asked to be told when solar underperforms: a low-export day is worth investigating (shading,
an inverter fault, a cloudy stretch worth knowing about), and a net-import day is worth knowing
about the same morning rather than discovering it on a utility bill weeks later.

## What "daily_to_grid" actually is, and why the design changed

The Sense integration exposes `to_grid` and `from_grid` as two separate, non-negative
accumulators per period (`daily_`, `weekly_`, `monthly_`, `yearly_`, `bill_`): one counts energy
flowing out to the grid, the other counts energy pulled in. Both reset to 0 at local midnight
(`last_reset` steps forward daily; Phoenix has no DST, so that's always `07:00:00Z`).

The original ask was "check `daily_to_grid`; if negative, we imported more than we exported." A
single non-negative accumulator can't do that; there's no code path that makes it go negative. The
"we imported more than we exported" case is a statement about the **net** of the two entities, so
the check was built around that net figure instead of `daily_to_grid` alone. Confirmed with pde
before building: `net = to_grid − from_grid`, checked against both thresholds.

## How it works

```yaml
alias: Low grid export alert
triggers:
  - trigger: time
    at: "07:00:00"
conditions: []
actions:
  - action: recorder.get_statistics
    data:
      start_time: >-
        {{ (now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)).isoformat() }}
      end_time: >-
        {{ now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat() }}
      statistic_ids:
        - sensor.sense_287516_daily_to_grid
        - sensor.sense_287516_daily_from_grid
      period: day
      types:
        - change
    response_variable: grid_stats
  - variables:
      to_grid: >-
        {{ grid_stats.get('statistics', {}).get('sensor.sense_287516_daily_to_grid', [{}])[0].get('change') }}
      from_grid: >-
        {{ grid_stats.get('statistics', {}).get('sensor.sense_287516_daily_from_grid', [{}])[0].get('change') }}
  - variables:
      net_export: "{{ (to_grid - from_grid) if to_grid is not none and from_grid is not none else none }}"
  - if:
      - condition: template
        value_template: "{{ net_export is not none and net_export < 0 }}"
    then:
      - action: persistent_notification.create
        data:
          title: Grid export negative
          notification_id: grid_export_negative
          message: >-
            Yesterday you imported more energy than you exported: net
            {{ net_export | round(1) }} kWh (to_grid {{ to_grid | round(1) }}, from_grid
            {{ from_grid | round(1) }}).
      - action: notify.mobile_app_pete_iphone
        data:
          title: Grid export negative
          message: >-
            Yesterday's net grid export was negative: {{ net_export | round(1) }} kWh. You
            imported more than you exported.
    else:
      - if:
          - condition: template
            value_template: "{{ net_export is not none and net_export < 20 }}"
        then:
          - action: persistent_notification.create
            data:
              title: Low grid export
              notification_id: grid_export_low
              message: >-
                Yesterday's net grid export was {{ net_export | round(1) }} kWh, under the 20 kWh
                threshold (to_grid {{ to_grid | round(1) }}, from_grid {{ from_grid | round(1) }}).
mode: single
```

Runs once at 7:00 AM local. `net_export ≥ 20` is silent by design; nothing to say on a normal day.

### Why `recorder.get_statistics`, not the live entity state or a Utility Meter helper

By 7 AM the source sensors have already reset (they reset at local midnight, seven hours
earlier), so the live state is today's partial value, not yesterday's total. Some way to recover
the finished prior-day total is required.

Two options were available:

- **Utility Meter helper**, wrapping the source with its own `cycle: daily` and reading its
  `last_period` attribute after each reset. This is the standard HA pattern for exactly this
  problem, but the `utility_meter` integration is not installed on this instance
  (`GET /api/config/config_entries/entry` doesn't list it), so using it means adding a new
  integration for what turns out to be one attribute read.
- **`recorder.get_statistics`**, a service already available on this instance
  (`GET /api/services` lists it under the `recorder` domain, response required). Both source
  entities are `state_class: total`, `device_class: energy`, so HA's own long-term statistics
  already track a `sum` for each of them and compute a correct `change` per period that accounts
  for the daily reset the same way Utility Meter's reset-detection would. No new integration
  needed.

`recorder.get_statistics` won. Verified directly before wiring it into the automation:

```bash
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "http://hass.ehlke.net:8123/api/services/recorder/get_statistics?return_response" \
  -d '{
    "start_time": "2026-08-19T00:00:00-07:00",
    "end_time": "2026-08-20T00:00:00-07:00",
    "statistic_ids": ["sensor.sense_287516_daily_to_grid", "sensor.sense_287516_daily_from_grid"],
    "period": "day",
    "types": ["change"]
  }'
```

returned `to_grid` change `25.2`, `from_grid` change `33.7` for 2026-08-19, matching a manual
reconstruction from raw recorder state history done earlier the same session (last value before
each day's reset, cross-checked against the next day's carried-over boundary reading). Net for
that day was **-8.5 kWh**: a real net-import day, which is what the live test below actually
fired on.

`response_variable` on a service call binds to the same object REST returns under
`service_response`: a `{"statistics": {"<entity_id>": [...]}}` mapping, one list entry per
requested period. The automation's `variables` steps index into that shape, not directly by
entity id.

### Local-day boundaries

Phoenix has no DST (fixed `America/Phoenix`, UTC-7 year round), so `now()` inside the automation
at trigger time gives a timezone-aware local datetime; zeroing it to midnight and subtracting a
day gives yesterday's local midnight directly, with no separate DST handling needed. This produces
the same `T00:00:00-07:00` / `T00:00:00-07:00` boundaries as the manual verification above.

## Verification

Created via `POST /api/config/automation/config/low_grid_export_alert`, confirmed with
`POST /api/config/core/check_config` (`valid`, no warnings), and confirmed live as
`automation.low_grid_export_alert` (`state: on`) in `/api/states`.

Manually triggered once via `POST /api/services/automation/trigger` to exercise the real path,
with pde's explicit go-ahead since 2026-08-19's real net was negative, meaning this would send a
real push to Pete's iPhone rather than a synthetic test value:

| When | What |
|---|---|
| 2026-08-20T15:25:23Z | Manual test trigger, run against real 2026-08-19 data (net -8.5 kWh) |

`last_triggered` updated to that timestamp, and `GET /api/logbook/<start>?entity=automation.low_grid_export_alert`
showed a clean `triggered` entry with no automation error, for both branches: the persistent
notification and the push to Pete's iPhone. pde confirmed both arrived with the expected text; the
test persistent notification was then dismissed via `persistent_notification.dismiss`.

Reading the actual trace (`trace/get`) or the persistent notification list
(`persistent_notification/get`) needs the WebSocket API. `aiohttp`, which `scripts/haws.py`
depends on, was not installed in the shell this was built in. A hand-rolled stdlib socket client
completed the WebSocket handshake but had the connection closed by the server immediately
afterward (a normal-closure close frame, code 1000) before any command could be sent; not
pursued further given the REST-level evidence and pde's direct confirmation were already
sufficient. Worth knowing if this needs debugging again: it means the gap is somewhere past the
HTTP Upgrade, not the handshake itself.

## Reproducing the measurements

```bash
U=http://hass.ehlke.net
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  "$U/api/services/recorder/get_statistics?return_response" \
  -d '{
    "start_time": "'"$(date -v-1d +%Y-%m-%d)"'T00:00:00-07:00",
    "end_time": "'"$(date +%Y-%m-%d)"'T00:00:00-07:00",
    "statistic_ids": ["sensor.sense_287516_daily_to_grid", "sensor.sense_287516_daily_from_grid"],
    "period": "day",
    "types": ["change"]
  }'
```

Read the automation's current configuration with:

```bash
curl -s -H "Authorization: Bearer $HA_TOKEN" "$U/api/config/automation/config/low_grid_export_alert"
```
