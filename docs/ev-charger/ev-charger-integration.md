# Garage EV charger: OpenEVSE integration inventory

An OpenEVSE Level 2 charger sits in the Garage area, integrated via Home Assistant's
official [`openevse`](https://www.home-assistant.io/integrations/openevse) integration.
The config entry was added 2026-08-11, discovered live during an instance inventory
refresh; nothing about it had been written up here before this document.

This is an inventory, not a design decision. It records what the integration exposes,
what's already live, and what's available but unused, so a future automation or
dashboard pass has the full picture instead of rediscovering it entity by entity.

## What's live now

19 entities are enabled under the `garage_ev_charger_*` prefix:

- **Charging status**: `sensor.garage_ev_charger_charging_status`, `charge_time_elapsed`,
  `charging_current`, `charging_voltage`, `charging_power`, `current_power`.
- **Session and lifetime usage**: `sensor.garage_ev_charger_usage_this_session`,
  `total_energy_usage`.
- **Vehicle**: `binary_sensor.garage_ev_charger_vehicle_connected`,
  `sensor.garage_ev_charger_vehicle_state_of_charge`, `vehicle_range`,
  `vehicle_charge_completion`. All three vehicle-specific sensors read `unknown` as of
  this snapshot, which likely means the vehicle side isn't linked or reporting yet,
  worth checking before building anything on them.
- **Load management, read-only**: `binary_sensor.garage_ev_charger_divert_active`,
  `shaper_active`, and `sensor.garage_ev_charger_ambient_temperature`.
- **Control**: `number.garage_ev_charger_charge_rate` (settable, currently 40),
  `sensor.garage_ev_charger_current_capacity`, `current_limit`, and two buttons,
  `button.garage_ev_charger_restart` and `restart_wi_fi`.

There is no dedicated `openevse` service domain. Everything is controlled through
generic domain services: `number.set_value` on the charge rate, `button.press` on the
restart buttons.

## What's installed but disabled

22 more entities exist under the device but are disabled by the integration itself
(`disabled_by: integration` in the entity registry), meaning OpenEVSE reports this data
but Home Assistant isn't polling or storing it unless someone enables it:

- **Connectivity and diagnostics**: `ethernet_connected`, `mqtt_connected`,
  `signal_strength`, `uptime`, `free_memory`, `service_level`.
- **Hardware temperature**: `ir_temperature`, `rtc_temperature`, `esp_temperature`.
- **Amperage limits**: `minimum_amperage`, `maximum_amperage` (the hardware/wiring-level
  ceiling, separate from the software `current_limit` above).
- **Separate energy rollups**: `daily_energy_usage`, `weekly_energy_usage`,
  `monthly_energy_usage`, `yearly_energy_usage`. These duplicate what Sense's
  `sense_*` entities and the Energy dashboard already cover for this circuit, which is
  probably why they're off by default, but they'd give an OpenEVSE-native cross-check
  independent of Sense's detection.
- **Load-shaper detail**: `shaper_live_power`, `shaper_available_current`,
  `shaper_maximum_power`. The `divert_active` / `shaper_active` binary sensors above are
  enabled and tell you *whether* load management is active; these three tell you *how
  much*, and are off.
- **Safety trip counters**: `gfci_trip_count`, `no_ground_trip_count`,
  `stuck_relay_trip_count`. Cumulative counts, not events, so they'd need a
  delta/threshold automation rather than a state trigger. This archive already has a
  pattern for that kind of device-health monitoring; see
  [fridge-failure-alert.md](../device-alerts/fridge-failure-alert.md) and
  [roborock-status-mqtt-stall.md](../device-alerts/roborock-status-mqtt-stall.md).

## Interesting capabilities not used in Homie Dash

Homie Dash has zero references to this device, verified against its live Lovelace
config, not just against this archive's other docs.

- **Solar-aware ("divert") charging.** OpenEVSE's own documented use cases include
  "optimizing charging using surplus solar power," and the hardware clearly supports
  it, that's what `divert_active` and the disabled `shaper_*` sensors report on. But
  there's no writable divert-mode entity in this integration; enabling it appears to be
  a setting on the charger's own web interface or RAPI console, not something Home
  Assistant can flip. If divert mode gets turned on at the hardware level, the shaper
  sensors above would be worth enabling to see it working. This would also pair
  naturally with the green-percentage solar work already done for Overview C; see
  [overview-c-solar-home-green-percentage.md](../homie-dashboard/overview-c-solar-home-green-percentage.md)
  and [overview-c-solar-today-totals.md](../homie-dashboard/overview-c-solar-today-totals.md).
- **Peak-rate charge throttling.** Also a documented OpenEVSE use case: "adjusting
  charging current based on peak electricity rates." `number.garage_ev_charger_charge_rate`
  is already live and settable, so this is an automation away, not an integration
  limitation, nobody has built it yet.
- **Device health surfacing.** The three trip counters above would slot into the same
  "something's wrong with a device" alerting pattern already used for the fridge and
  the Roborock, and currently nothing watches them at all.
- **Charging notifications.** OpenEVSE's docs mention automating notifications on
  charging status changes. Real mobile push now exists on this instance (see the
  Notifications section of
  [../../.claude/skills/home-assistant/references/instance-inventory.md](../../.claude/skills/home-assistant/references/instance-inventory.md)),
  so a "charging started/completed" push is now cheap to build where it wasn't before.

## Troubleshooting note worth keeping

Per OpenEVSE's own docs, the charge rate can't be raised past whatever's configured in
the charger's own web interface: the ceiling is a hardware/electrical setting, not a
Home Assistant one, and raising it means confirming the wiring and breaker are rated
for the higher current first.

## Sources

- [home-assistant.io/integrations/openevse](https://www.home-assistant.io/integrations/openevse)
