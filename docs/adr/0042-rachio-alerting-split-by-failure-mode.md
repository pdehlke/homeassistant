# Rachio alerting: one automation per genuinely distinct failure mode

Rachio alerting is split into four separate automations rather than one combined automation, each
time a condition turned out to differ from an existing one in mechanism or blast radius rather than
just being folded in. Standby-mode-engaged got its own automation instead of joining the
zone-disabled alert: a state flip on an existing entity versus an entity disappearing, and pausing
every zone at once versus losing one zone. The Back Yard Smart Hose Timer's health alert (battery
low, offline) got its own automation instead of joining the Main Irrigation zone-disabled alert for
the same reason: pde considers a dead battery a completely different condition from a disabled
zone, and Back Yard has a real Rachio-provided battery signal that needs no reload-blip debounce,
unlike connectivity. See [docs/rachio/rachio-zone-disabled-alert.md](../rachio/rachio-zone-disabled-alert.md).
