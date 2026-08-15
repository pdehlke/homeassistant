# Lennox _alert is the trigger of record; _active_alerts is enrichment only

The `lennoxs30` integration exposes two alert signals per thermostat that can genuinely disagree:
`_alert` mirrors the console's current status field directly, while `_active_alerts` is a
structured queue that many conditions (including transient inverter comm errors) can clear from
once the underlying condition passes, even while `_alert` stays at whatever level it last reported.
Confirmed live: South's `_alert` read `critical` while its `_active_alerts` list was already empty
for that same code. `_alert` drives the alert automation's trigger and severity, since it's the one
confirmed to match what's actually on the console right now; `_active_alerts` is used only as
best-effort detail, and the notification says so plainly when the matching detail has already
rotated out rather than guessing. See `docs/lennox-climate/lennox-thermostat-alerts.md`.
