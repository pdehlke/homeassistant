# Roborock status entities freeze when the MQTT push channel stalls

## Symptom

The Q5 Max+ (`vacuum.q5_max`) docked at 10:04 AM local on 2026-08-07 and finished charging some
time early that afternoon. By 6:50 PM the Roborock phone app reported "Charged" and the vacuum's
own charging LED was off, confirmed by physical inspection. Home Assistant still reported
`binary_sensor.q5_max_charging` as `on` and `sensor.q5_max_status` as `charging`, and neither the
Overview A status pill nor the vacuum overlay in the Homie Dashboard fork ever caught up.

This was investigated immediately after a similar-looking but differently-caused bug in the
Rachio irrigation entities (see `project-todo.md`, item 2). The two turned out to be unrelated:
Rachio's problem is that this Home Assistant instance is not reachable from the internet, so
Rachio's cloud can never deliver the webhook it uses to report zone state. Roborock's integration
does not depend on inbound reachability at all.

## Evidence

Every `q5_max` entity's `last_updated` timestamp, read directly from `/api/states`, sorted
chronologically:

| Time (UTC) | What updated |
|---|---|
| 12:10:03 | A full batch of config-style entities (DND, volume, dock settings). Matches a Home Assistant restart seen across other integrations at the same moment. |
| 17:03:24 | Cleaning-session summary entities (cleaning time, area, counts, `last_clean_end`). Real event: the vacuum finished cleaning. |
| 17:04:24 | `vacuum.q5_max` state changes to `docked`. |
| 17:04:57 | `binary_sensor.q5_max_charging` becomes `on`, `sensor.q5_max_status` becomes `charging`. Real event: charging started. |
| 17:05:01 | `sensor.q5_max_current_room` updates (map/position data). |
| 19:18:24 | `sensor.q5_max_battery` reaches `100`. The only later update `charging`/`status` should have accompanied, but did not. |
| 00:07:06 (next day) | Brush and filter consumable timers update. |
| 01:49:34 (next day) | The map image entity's timestamp attribute ticks forward. |

`charging` and `status` never moved again after 17:04:57, through four more rounds of other
entities updating successfully. The integration was not dead: battery, consumable timers, and the
map all kept refreshing on their own schedule. Only the two push-driven state fields froze.

## Root cause

The official integration docs describe Roborock's update model as "a combination of local polling
and cloud-based MQTT push events"
([home-assistant.io/integrations/roborock](https://www.home-assistant.io/integrations/roborock)).
`status` and `charging` are populated from the MQTT push side, which is a known point of failure:

- [home-assistant/core#134448 — Roborock MQTT publishing gets stuck resulting in slow status
  updates](https://github.com/home-assistant/core/issues/134448): the integration works correctly
  after Home Assistant starts, then the MQTT push stalls after some hours of uptime, and reloading
  the integration forces a reconnection that clears it.
- [home-assistant/core#162666 — Roborock status not updating since
  2026.2.0](https://github.com/home-assistant/core/issues/162666): the same symptom, status stuck
  until a reload or a full restart.

Battery and consumable-timer entities apparently come from a separate polled path, which is why
they kept updating normally while `charging` and `status` sat frozen at whatever they were when the
MQTT session was last healthy. This matches this instance's timeline exactly: everything worked
for roughly the first two hours after the 12:10 restart, then the push channel silently stalled
sometime before the charge-complete transition would have been reported.

This is an upstream bug in `home-assistant/core`, not a misconfiguration here, and not something
fixable from the Homie Dashboard fork or from Lovelace config.

## Options considered

- **Wait for an upstream fix.** Both linked issues are open with no committed fix as of this
  writing. Rejected as the sole strategy: it leaves the dashboard silently wrong for an unbounded
  time, which is the exact problem being fixed.
- **Restart Home Assistant periodically.** Would clear the stall (matches the restart-recovers
  pattern seen in the evidence above) but resets every other integration and entity too. Rejected
  as disproportionate to a single integration's known bug.
- **Reload the Roborock integration manually whenever noticed.** This is what the GitHub issue
  reporters do by hand. Rejected as the ongoing approach because it requires someone to notice the
  staleness first, which defeats the point of a dashboard status pill.
- **Automate a periodic reload of just the Roborock config entry (chosen).** Narrowest blast
  radius: only this integration's entities go briefly `unavailable` while it reconnects, nothing
  else on the instance is affected. Matches the exact recovery action the upstream issue reporters
  already use.

## Mitigation: periodic reload automation

Created directly in Home Assistant (`automation.roborock_integration_periodic_reload`), not
committed anywhere as code. Per this repo's own convention, HA configuration is not mirrored here;
Home Assistant's own backups are the record of the automation's YAML. This file exists to record
why it exists.

- Trigger: `time_pattern`, every 30 minutes.
- Action: `homeassistant.reload_config_entry` targeting the Roborock config entry
  (`entry_id: 01KZ9D1NXNYH2X0HRWREEX2MN8`, title `pde@rfc822.net`, the account used to set up the
  integration).
- Mode: `single`.

The 30-minute interval was picked as a starting point to observe, not derived from how long the
stall actually takes to occur; the evidence above only shows it stalled at some point between
17:05 and 19:18, a roughly two-hour window, not a precise interval.

## Verification so far

Confirmed the automation is valid, enabled, and executes: `check_config` passed, the entity
appears and is `on`, and a manual trigger produced a real `last_triggered` timestamp. The manual
trigger also confirmed the reload mechanism itself works as intended: `binary_sensor.q5_max_charging`
and `sensor.q5_max_status` both received a fresh `last_updated` timestamp immediately after,
proving the reload does force a new push for those specific entities.

What it did not confirm: in that one test, the freshly-pushed values were still `on` / `charging`,
unchanged from before. Twenty seconds later, neither had moved again. This does not necessarily
mean the fix failed. It may mean the device's real state at that exact moment still involved some
post-100% activity (a brief top-off cycle) that the Roborock phone app rounds down to "Charged"
but the raw device status does not, in which case Home Assistant was reporting accurately and
there was nothing to fix in that instant. It is also possible the reload's first snapshot comes
from a cache that has not yet observed the true post-charge state, and only a later, real
device-driven transition will clear it correctly next time.

This needs to be watched over further reload cycles, ideally the next time the vacuum finishes a
full charge, before concluding the automation actually resolves the user-visible symptom rather
than just proving the reload path itself works.
