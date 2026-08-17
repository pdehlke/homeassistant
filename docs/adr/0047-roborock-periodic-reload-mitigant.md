# Roborock stall mitigation: periodic reload of just the config entry

Roborock's `status`/`charging` entities freeze when its MQTT push channel stalls after some hours
of uptime, a known upstream `home-assistant/core` bug, not a local misconfiguration. Waiting for an
upstream fix was rejected as the sole strategy (leaves the dashboard silently wrong indefinitely);
restarting Home Assistant periodically was rejected as disproportionate (resets every other
integration too); manually reloading whenever noticed was rejected as requiring someone to notice
first, defeating the point of a status pill. Chosen: an automation reloading only the Roborock
config entry every 30 minutes, the narrowest blast radius available and the same recovery action
the upstream issue reporters already use by hand. See
[docs/device-alerts/roborock-status-mqtt-stall.md](../device-alerts/roborock-status-mqtt-stall.md).
