# Populating the Vision Sample dashboard's placeholder entities

Established 2026-08-05 on Home Assistant 2026.7.4.

## The problem

The Vision Sample dashboard was seeded from the [visionos theme's sample
dashboard](https://github.com/Nezz/homeassistant-visionos-theme/blob/sample/sample.yaml), which
is built against a fresh Home Assistant instance with the built-in `demo:` integration enabled.
This instance never had `demo:` installed, so several of the sample's cards pointed at entities
that simply did not exist, rendering as unavailable placeholders instead of the live controls
shown in the theme's own reference screenshots.

## What was actually missing

Checked every entity the live dashboard config referenced against `/api/states` rather than
assuming the whole card set was fake. Most of it turned out to already be real, either because
pde had built it directly (`light.primary_suite_lights`, a native HA Light Group helper
aggregating the five Primary Suite lights, added through the UI after the [light entity
strategy](light-entity-strategy.md) work) or because it was a genuine integration
(`binary_sensor.garage_ev_charger_vehicle_connected`, `vacuum.q5_max`,
`climate.casasolar_north_zone_1` / `south_zone_1`, `media_player.gym`, `todo.shopping_list`,
`weather.openweathermap` and its sensors). Only seven entities were genuinely missing:

`light.bed_light`, `light.ceiling_lights`, `lock.poorly_installed_door`, `cover.pergola_roof`,
`alarm_control_panel.security`, `device_tracker.demo_home_boy`, `water_heater.demo_water_heater`.

## The options, and why six of seven went one way and the seventh went another

Three ways to get demo-shaped entities were on the table:

| Option | Verdict |
| :--- | :--- |
| Template Helper, config flow, no file access | Chosen for six of seven |
| The real `demo:` integration | Rejected |
| Hand-written `template:` YAML for just the gap | Rejected for now |

**The real `demo:` integration** was rejected for the same reason [light entity
strategy](light-entity-strategy.md#why-this-and-not-something-simpler) rejected it the first
time: no config flow, YAML-only, and it seeds a fixed set of names across nearly every domain
(`climate.hvac`, `lock.front_door`, `cover.garage_door`, and dozens more) that this dashboard
does not use. It would also mean editing `configuration.yaml`, which this instance currently has
no remote way to do — no File Editor, Terminal & SSH, or Studio Code Server add-on is installed,
only Music Assistant. Worth noting for later: Home Assistant does **not** auto-remove entity
registry entries when a YAML-only platform is removed and HA restarts. They persist as
unavailable, orphaned registry rows. Core has no bulk-delete for this, but since `demo:`'s
entity list is fixed and known, a teardown is just one `config/entity_registry/remove` call per
entity id, not something that needs a third-party cleanup integration.

**Blueprint Studio**, a HACS custom integration (`ha-china/blueprint-studio`) pde installed
mid-investigation, would have solved the file-access half of that blocker — it is a genuine
in-dashboard YAML editor with an authenticated API, MIT licensed, with documented path-traversal
protection. It does not solve the other half: it is a fresh HACS install with no config entry
yet, so Home Assistant has not loaded its code, and it needs a `homeassistant.restart` before
its own config flow can even run — the same restart `demo:` itself needs to take effect. It also
does not change the risk profile of adding `demo:`: unlike every other custom component in this
instance (`card-mod`, `wall-clock-card`, `kiosk-mode`, `sonos-card`, `music-flow`, all
frontend-only, browser-side Lovelace code), Blueprint Studio is a server-side integration with
unsandboxed read/write across `/config`. Flagged that distinction to pde directly rather than
just using it. Not used for this pass.

**Template Helper via the config-flow API** is exactly the pattern used for every light in
[light entity strategy](light-entity-strategy.md), generalized to whatever domain the flow's
menu step offers. Confirmed live by walking the flow: `alarm_control_panel`, `binary_sensor`,
`button`, `cover`, `device_tracker`, `event`, `fan`, `image`, `light`, `lock`, `number`,
`select`, `sensor`, `switch`, `update`, `vacuum`, `weather`. Six of the seven missing entities
fall in domains that menu covers. No restart, no file access, no new component to trust.

`water_heater` is not on that list. It cannot be built through Template Helper at all, only
through `demo:` or hand-written YAML, both of which mean touching `configuration.yaml`. Asked
pde directly rather than deciding unilaterally: leave `water_heater.demo_water_heater` missing.
That tile shows "Entity not found" on the dashboard; everything else is live.

## What was built

Same three-piece pattern as every template light, extended per domain:

| Entity | Backed by | Notes |
| :--- | :--- | :--- |
| `light.bed_light` | `input_boolean` + `input_number` | Standard light recipe |
| `light.ceiling_lights` | `input_boolean` + `input_number` | Standard light recipe |
| `lock.poorly_installed_door` | `input_boolean` | `on` = locked |
| `cover.pergola_roof` | `input_number`, 0-100 | Position only, see limitation below |
| `alarm_control_panel.security` | `input_boolean` | `on` = armed_away |
| `device_tracker.demo_home_boy` | `input_boolean` + `zone.home`'s own coordinates | See below |

The device tracker doesn't use a state template at all — the Template Helper's `device_tracker`
step has no `state` field, only `latitude` / `longitude` / `in_zones`. It derives `home` /
`not_home` the way a real GPS tracker would: the templates read `zone.home`'s own latitude and
longitude when the backing boolean is on, and add one degree to both when it's off, which is
comfortably outside every configured zone.

### Template covers have no tilt support

`cover.pergola_roof`'s card in the sample dashboard uses `cover-tilt-position` and `cover-tilt`
features. The config-flow Template Helper for covers has no tilt fields at all (confirmed by
reading its full form schema) — only `position`, `open_cover`, `close_cover`,
`set_cover_position`. The entity built here supports position, open, and close, which is enough
for the tile to show a correct state and respond to its more-info dialog, but those two specific
tilt features on the card render without effect since the entity has nothing to back them. A
YAML-only `template:` cover platform does support tilt; not worth the file-access and restart
cost for one card's cosmetic feature given the rest of the entity already works.

## Verified live

Checked `/api/states` after creation (all six read sane defaults, not unavailable), exercised
each entity once through its real service (`light.turn_on` at a specific brightness,
`lock.lock`, `cover.close_cover`, `alarm_control_panel.alarm_arm_away`), confirmed the state
changes landed, then returned everything to its resting state (lights off, door unlocked, cover
closed, alarm disarmed). Screenshotted the live Vision Sample dashboard: all six cards render
interactive controls, and the water heater tile is the one remaining "Entity not found" card,
as decided.
