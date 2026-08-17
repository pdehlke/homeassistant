# Rachio config-entry reload: hourly, not the investigation's own 15-30 minute recommendation

The investigation that recommended a periodic `homeassistant.reload_config_entry` automation
suggested a 15-30 minute cadence. pde chose hourly instead, explicitly trading detection latency
for fewer reload-triggered `unavailable` blips across every Rachio entity, on the reasoning that a
pending webhook fix (making the instance internet-reachable) might make the whole reload
workaround moot within the week. See [docs/rachio/rachio-zone-disabled-alert.md](../rachio/rachio-zone-disabled-alert.md) and
[docs/rachio/rachio-webhook-responsiveness-plan.md](../rachio/rachio-webhook-responsiveness-plan.md).

## Consequences

The original rationale turned out to be wrong: the webhook fix that shipped later helps zone
on/off state responsiveness but does nothing for disabled-zone detection, since HA's `rachio`
integration never subscribes to Rachio's config-change webhook category at all. With that
reasoning stale and a later fix (see the reload-race ADR) decoupling reload frequency from
false-positive risk entirely, tightening the cadence became a pure detection-latency choice — still
open, still pde's call, not yet done.
