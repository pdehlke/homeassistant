# Climate alert dot threshold raised to moderate/critical only

The Climate chip's alert dot originally lit for any Lennox `_alert` state other than
`none`/`unavailable`/`unknown`, including `info` and `minor` — a deliberate original design meant
to be more permissive than the phone-notification threshold. With both real thermostats spending
most of their time at `info`, that bar kept the dot lit almost continuously, defeating its purpose
as a glanceable signal. Raised to match the same `critical`/`moderate` bar the phone/
persistent_notification automation already uses, rather than maintaining a per-code suppression
list for specific chronic codes. See `docs/homie-dashboard/climate-alert-dashboard-threshold.md`.
