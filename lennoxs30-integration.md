# Lennox iComfort S30: the lennoxs30 integration

What was actually done to bring the two Lennox iComfort S30 thermostats (North and South, see
[crestron-migration.md](crestron-migration.md#status-as-of-2026-08-04-for-picking-this-back-up)) into
Home Assistant, and what to do if the South thermostat's IP address changes before a DHCP reservation
is in place for it.

This is the concrete record of step 2 in
[crestron-strategy.md's plan of attack](crestron-strategy.md#plan-of-attack); see that document's
"HVAC: independent of Crestron" section for why this integration was chosen over the alternatives.

## What was installed

The [lennoxs30](https://github.com/PeteRager/lennoxs30) custom integration, installed via HACS on
2026-08-04 (version 2026.6.0 at install time). It has shipped in HACS's default repository list since
October 2023, so no custom repository add was needed, just a search for "Lennox S30/E30" inside HACS.
Installing a HACS integration only downloads the files into `custom_components/`; it does not load
until Home Assistant restarts, which happened as part of this install (about 15-20 seconds of
downtime).

## Identifying the right IP addresses

The eero app's device list showed two unidentified devices with Espressif Wi-Fi chips, which looked
like a reasonable guess for the thermostats. That guess (`192.168.4.20` and `192.168.4.89`) turned out
to be wrong: neither address answered on any common web port from another machine on the same LAN,
which is consistent with those being some other IoT device, not with a reachable local API.

The correct addresses were found the reliable way: physically power-cycling each thermostat and
watching which eero client dropped offline. That gave `192.168.4.50` for North and `192.168.4.126` for
South. These were confirmed as genuine Lennox devices, not just correctly-guessed IPs, before trusting
them with a live integration:

```
openssl s_client -connect 192.168.4.50:443 -servername 192.168.4.50 2>/dev/null | openssl x509 -noout -subject -issuer -dates
```

Both addresses answered on port 443 with a TLS certificate issued to `CN=Lennox, O=Lennox
International Inc., L=Richardson, ST=TX`, which is Lennox's own local API certificate, not a
self-signed placeholder or an unrelated device. A plain `curl` to `/` on either address returns a bare
`404`, which is expected: the local API does not serve a browsable page at the root, only at the paths
the integration itself uses.

Keep this verification method in mind for the DHCP problem below; the eero app's device list alone is
not enough to trust an IP as a thermostat.

## Configuration used

Two connection modes are available per thermostat: local (LAN, HTTPS to port 443) and cloud (Lennox
account email and password). Local was chosen for both, since it has no dependency on Lennox's cloud
uptime and the integration's own docs note that cloud-connected S30s have seen stability problems with
power-inverter and diagnostic sensors enabled.

Two separate config entries were created, one per thermostat, since they are independent systems. The
integration's docs are explicit that every simultaneous instance, local or cloud, needs a distinct
`app_id`; reusing the default (`homeassistant`) across both would make the two connections collide.

| | North | South |
| :--- | :--- | :--- |
| Host | `192.168.4.50` | `192.168.4.126` |
| `app_id` | `ha_north` | `ha_south` |
| Protocol | `https` (default) | `https` (default) |

Every other option was left at the integration's own default: `create_sensors` on, everything else
(`allergen_defender_switch`, `create_inverter_power`, `create_diagnostic_sensors`, `create_parameters`)
off, and the advanced timing/logging options (`scan_interval` 1s, `fast_scan_interval` 0.75s,
`fast_scan_count` 10, `init_wait_time` 30s, `timeout` 30s, `message_debug_logging` on,
`pii_in_message_logs` and `log_messages_to_file` off) untouched.

## What it created

Both config entries reached `state: loaded` on the first attempt, no retries needed. Each thermostat
produced roughly 20 entities: one `climate` entity for its zone, plus outdoor temperature, indoor
temperature and humidity, demand percentage, Wi-Fi signal strength, active alerts, home/away state,
internet and relay-server status, a manual-away switch, a smart-away-enable switch, dehumidification
controls, an HVAC mode selector, and an `update` entity for the integration itself. Entity IDs are
prefixed with the system name configured in the homeowner's Lennox account, not reproduced here since
it identifies the property; the pattern is `climate.<name>_north_zone_1` and
`climate.<name>_south_zone_1`.

The data is live, not placeholder values: at install time, North read 75°F actively cooling toward a
62-74°F range, and South read 77°F actively cooling toward 62-75°F, both with real humidity and demand
percentages attached.

## Known gap: no DHCP reservation on South

As of 2026-08-04, the South thermostat's address is not reserved in the router (eero). North's
reservation status has not been separately confirmed either, but South is the one known to be
unreserved right now. If South's DHCP lease renews with a different address, its config entry will
start failing even though nothing about the thermostat itself changed: entities go `unavailable`, or
the integration logs a connection error.

### If South's IP address changes before the reservation is set

1. Notice it. The South entities (`climate.*_south_zone_1` and everything alongside it) will read
   `unavailable`, or the "Lennox S30,E30,M30" entry for South under Settings > Devices & Services will
   show an error state.
2. Find the new address. Do not trust the eero app's device list by itself; it misidentified both
   thermostats once already (see "Identifying the right IP addresses" above). Confirm any candidate
   address before using it:
   ```
   openssl s_client -connect <candidate-ip>:443 -servername <candidate-ip> 2>/dev/null | openssl x509 -noout -subject
   ```
   A genuine S30 answers with `subject=CN=Lennox, ... O=Lennox International Inc. ...`. Nothing on
   port 443 means that is not the thermostat. If no candidate is obvious, the reliable fallback is the
   same physical toggle test used originally: power-cycle the South unit and watch which eero client
   drops offline.
3. Remove the stale config entry. This integration does not support live reconfiguration
   (`supports_reconfigure` reports `false`), so the old entry has to be deleted rather than edited in
   place: Settings > Devices & Services > find the "Lennox S30,E30,M30" entry titled with the old IP >
   its three-dot menu > Delete.
4. Add it back: Settings > Devices & Services > Add Integration > "Lennox S30,E30,M30" > choose the
   local connection option > enter the new address as the host > set `app_id` back to `ha_south` (safe
   to reuse once the old entry is gone) > leave every other option at the defaults listed in
   "Configuration used" above.
5. Confirm the entities reappear under their previous names. Entity IDs come from the device's own
   reported name, not from its IP address, so they should not change.
6. While there, set the DHCP reservation in eero for the new address so this does not happen again.

## Open follow-ups

- Set DHCP reservations for both S30s in eero. South is confirmed missing; North should be verified
  too rather than assumed fine.
- The extra sensor options (`create_inverter_power`, `create_diagnostic_sensors`, and similar) were
  left off. Revisit once there is a sense of which ones are actually useful; the project's own docs
  warn that inverter and diagnostic sensors have caused stability problems in cloud mode, and it is not
  yet known whether that risk carries over to local mode.
