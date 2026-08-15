# Lennox thermostat IP identification: TLS certificate inspection, not the eero app's device list

The eero app's device list identified two Espressif-chip devices as plausible thermostat
candidates; neither address answered on any common port, and both turned out to be some other IoT
device entirely. The reliable method established instead: physically power-cycling each thermostat
and watching which eero client drops offline to find the real address, then confirming it's
genuinely a Lennox unit (not just a correctly-guessed IP) via `openssl s_client`, checking for a TLS
certificate issued to `O=Lennox International Inc.`. This is the standing method for any future IP
change too (e.g. before a DHCP reservation exists), not a one-time troubleshooting step. See
`docs/lennox-climate/lennoxs30-integration.md`.
