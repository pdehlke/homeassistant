# Energy statistics

Any entity with `state_class: total`/`total_increasing` that resets to zero
at local midnight (most Sense `device_class: energy` sensors, including
`sensor.sense_287516_daily_to_grid`/`daily_from_grid`) makes its *live*
state useless for "yesterday's total" once it has already reset. The
recorder's built-in `recorder.get_statistics` service computes the correct
per-period `change`, with no extra integration needed — this is the pattern
behind `docs/energy/low-grid-export-alert.md`'s automation and every future
energy alert built the same way.

## Sub-features

- `stats-period-total` — `recorder.get_statistics` returns a correct
  `change` value for a named period even after the live sensor has reset.
- `stats-response-required` — this service returns data that is not
  optional; omitting `?return_response` (REST) or `"return_response": true`
  (WebSocket) silently drops it.
- `stats-timezone` — `start_time`/`end_time` need an explicit UTC offset;
  this instance is fixed America/Phoenix, no DST, offset `-07:00` always.

## How to get to it (user POV)

- No direct UI path — this is what backs the Energy dashboard's own daily
  totals, and what any custom alert automation calls instead of trusting the
  live sensor.

## Driving it with REST/WebSocket

Preconditions:

- `doctor.py` passes and does not flag the target sensor as one of the
  known-dead Sense detections.
- Pick a real period that has already fully elapsed (yesterday, not today)
  so the `change` value is stable and reproducible.

- **Call it, REST, with `?return_response`:**

  ```bash
  HB="Authorization: Bearer $HA_TOKEN"; U=https://hass.ehlke.net
  curl -s -X POST --max-time 8 -H "$HB" -H "Content-Type: application/json" \
    "$U/api/services/recorder/get_statistics?return_response" \
    -d '{
      "start_time": "2026-08-22T00:00:00-07:00",
      "end_time": "2026-08-23T00:00:00-07:00",
      "statistic_ids": ["sensor.sense_287516_daily_to_grid", "sensor.sense_287516_daily_from_grid"],
      "period": "day",
      "types": ["change"]
    }' | python3 -m json.tool
  ```

- **Cross-check against the automation's own read**, if verifying an
  automation built on this pattern rather than the raw service: trigger it
  (see [automation-trigger-and-trace.md](automation-trigger-and-trace.md)),
  read its trace's `variables:` step, and confirm the `response_variable`
  value there matches this call's `service_response` exactly — same
  `statistics['<entity_id>'][0].change`, not `['<entity_id>']` directly (a
  common indexing mistake between the two contexts).

## Gotchas

- An ISO timestamp from Python's `.isoformat()` on a UTC-aware datetime
  produces a `+00:00` suffix. `/api/history/period` silently returns `[]`
  for that; `recorder.get_statistics`'s `start_time`/`end_time` want an
  explicit offset too — use this instance's fixed `-07:00`, not `Z`, for
  this specific service (unlike `/api/history/period`, which wants `Z` — the
  two endpoints don't share a convention).
- In an automation/script, bind the result with `response_variable:`, not
  `return_response` (that flag is REST/WebSocket-only). The bound variable
  has the same `{"statistics": {...}}` shape as `service_response` — index
  as `some_name.statistics['<entity_id>']`, not `some_name['<entity_id>']`.
- `utility_meter` (the other standard HA "remember pre-reset total" pattern)
  is not installed on this instance. Don't reach for it or assume it's
  available as a fallback.
- Verify `doctor.py`'s dead-Sense-detection list before trusting any new
  Sense-backed statistic; a sensor reading a flat `change: 0` might be
  correctly idle, or might be one of the permanently dead detections.
