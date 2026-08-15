# Climate chip's "N on" count tracks hvac_action, not entity state

The Overview A/B Climate chip's "N on" count used the generic `entityIsOn()` helper, whose climate
branch is `state !== "off"` — true almost permanently for both thermostats, which run in
`heat_cool` mode nearly always, so it counted "enabled" as "on" rather than "actively
conditioning." Fixed by hoisting Overview C's existing `climateIsActive()` (reading `hvac_action`
for `heating`/`cooling`) into a shared function used everywhere. The AC control card's own on/off
toggle (`hvac_mode`-based, meaning "is the system enabled at all") is a different, equally valid
concept and was deliberately left untouched, confirmed with pde before changing anything. See
`docs/homie-dashboard/climate-chip-activity-count.md`.
