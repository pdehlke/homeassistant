# Lennox integration: local mode over cloud mode for both S30 units

Both iComfort S30 thermostats (North, South) are configured via the `lennoxs30` HACS integration
in local mode rather than cloud mode. Local avoids dependency on Lennox's cloud uptime and the
project's own documented stability problems with power-inverter/diagnostic sensors on
cloud-connected S30s, at the cost of needing a reserved LAN IP and possibly a firmware update per
thermostat instead of just an account login. See `docs/crestron/crestron-strategy.md` and
`docs/lennox-climate/lennoxs30-integration.md`.

## Consequences

Each thermostat is its own config entry with a distinct `app_id` (`ha_north`/`ha_south`), not the
integration's shared default. The integration's own docs are explicit that reusing the default
`app_id` across simultaneous instances, local or cloud, makes the two connections collide.
