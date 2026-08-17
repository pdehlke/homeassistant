# climate.set_temperature requires paired bounds and the entity's own declared step

Home Assistant's `climate.set_temperature` schema rejects a call supplying only one of
`target_temp_high`/`target_temp_low` with a bare 400, and a call whose delta doesn't land on the
entity's own declared `target_temp_step` (both Lennox zones declare `1.0`, not the dial's assumed
`0.5`) returns HTTP 200 with no state change and no logbook entry — both silent to a normal
client. Homie's thermostat control always sent both bound keys (changing only the active one) and
read each entity's own step size rather than a hardcoded default, discovered only by testing
directly against the real entities rather than trusting a service call's own response. See
[docs/homie-dashboard/homie-thermostat-control-fix.md](../homie-dashboard/homie-thermostat-control-fix.md).

## Consequences

The code this applied to (`thermostatSetTemperaturePayload`, `thermAdjust`, `thermostatStepSize`)
was deleted outright when Climate control was routed through HA's native dialog instead (see the
native-dialog-routing ADR). The API constraints themselves remain true for any future direct
`climate.set_temperature` call against these entities, from any client.
