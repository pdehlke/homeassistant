# No fork of HA core's rachio integration for native DELTA handling

Rachio's `DELTA`/`ZONE_DELTA` webhook categories, which would report a zone being disabled or
enabled, are confirmed live and registerable (a public-docs gap, not a removed feature), so forking
HA core's `rachio` integration to subscribe to them natively was feasible. Not done: the `DELTA`
payload itself carries no field-level diff, only "something changed, go re-fetch," so both a fork
and a simpler native-webhook-triggered reload buy the same thing — faster detection, not better
data — and a fork means permanently shadowing a core HA component and manually re-syncing it
against upstream forever, for a benefit narrower than it first looked. See
`docs/rachio/rachio-webhook-responsiveness-plan.md`.
