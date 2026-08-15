# Instance inventory

Snapshot taken 2026-08-11. Re-check with `GET /api/states` rather than trusting these counts if something looks off; the instance is young and changing fast.

## Core

- Home Assistant 2026.8.1, timezone `America/Phoenix`, units °F, 256 components.
- **Instance was created 2026-08-03.** It is still young, but no longer empty: 8 automations, several config-flow integrations, and a real dashboard buildout now exist. Sparse area assignments (22 of 695 registered entities have one) are still a consequence of age, not neglect. Do not report those as findings; do report a growing automation/integration list as expected progress, not as evidence the "young instance" framing no longer applies at all.
- Raspberry Pi host. Config dir `/config`, not mounted on this machine.

## Entity counts

`sensor` 270, `binary_sensor` 47, `input_boolean` 26, `switch` 26, `update` 25, `light` 24, `input_number` 22, `number` 16, `select` 13, `button` 12, `media_player` 11, `automation` 8, `event` 5, `script` 3, `device_tracker` 3, and one or two each of `tts`, `scene`, `input_text`, `lennoxs30`, `notify`, `weather`, `time`, `calendar`, `climate`, `conversation`, `stt`, `zone`, `person`, `sun`, `lock`, `alarm_control_panel`, `todo`, `image`, `vacuum`, `remote`.

Still nothing in `cover`, `fan`, `humidifier`, `water_heater`, `siren`, `valve`, or `camera`. Every other domain the 2026-08-04 snapshot called empty (`light`, `climate`, `lock`, `scene`, `script`, `input_boolean`, `input_number`) is now populated; automations that assumed otherwise no longer need to guard for it.

## Integrations

Config entries as of this snapshot (`GET /api/config/config_entries/entry`, 77 entries):

`analytics, aws_s3, backup, bluetooth, cast, cloud, co2signal, frosted_glass_manager, go2rtc, google_translate, group, hacs, harmony, hassio, history_stats, ibeacon, lennoxs30, lg_thinq, local_calendar, material_symbols, mcp_server, met, mobile_app, moon, music_assistant, openevse, openweathermap, rachio, radio_browser, raspberry_pi, roborock, rpi_power, sense, shopping_list, sonos, sun, template, thread, waqi, wemo`

`frosted_glass_manager` is a custom integration. New since the 2026-08-04 snapshot: `cloud` (Home Assistant Cloud / Nabu Casa, see [nabucasa-remote-ui-dns-fragility.md](../../../../docs/nabucasa-remote-access/nabucasa-remote-ui-dns-fragility.md)), `lennoxs30` (see [lennoxs30-integration.md](../../../../docs/lennox-climate/lennoxs30-integration.md)), `rachio` (see [rachio-zone-disabled-alert.md](../../../../docs/rachio/rachio-zone-disabled-alert.md)), `roborock` (see [roborock-status-mqtt-stall.md](../../../../docs/device-alerts/roborock-status-mqtt-stall.md)), `mobile_app` (two devices registered, see Notifications below), `harmony` (Logitech Harmony Hub, powers `remote.harmony_hub`, not written up anywhere yet), `lg_thinq` (powers the new `media_player.lg_webos_tv_um7300pua`, not the appliance line the name suggests), `openevse` (the garage EV charger, see the callout at the end of this section), `template`, `group`, `history_stats`, `moon`, `waqi`, `material_symbols`, `lg_thinq`.

**The garage EV charger (`openevse`) has no writeup anywhere in this archive.** It exposes charging status, current/power/voltage sensors, a settable charge rate, restart buttons, and vehicle-connected/divert-active/load-shaper-active binary sensors, all under `garage_ev_charger_*`. Worth a document of its own if it is staying.

## Sense energy monitor, and its dead detections

Sense supplies device-level power detection and is the richest data source here. Its yearly counters come from Sense's own cloud, so they predate this HA instance and are trustworthy even when HA history is empty.

**These detections are stale and read at or near 0 kWh/year. Never build automations on them:**

`heat_3`, `garage_door`, `washer`, `light_1`, `solar`, `sense_energy_monitor`, `central_ac` (new since the last snapshot, also reading 0)

Three more detections are new since the last snapshot and read low enough to be ambiguous rather than clearly healthy: `washer_2` (3.1 kWh/yr), `microwave` (4.7), `heat_1` (14.9). `freezer` is still the same borderline case as before, about 27.9 kWh/yr against `fridge` at 415, roughly 7%. Treat all of these as unreliable until they show real cycling.

Healthy, high-confidence signatures: `fridge` (415 kWh/yr, up from 401), `heat_pump` (1503, up from 1396), `electric_vehicle` (787, up from 745), `coffee_maker` (98, up from 94), `dryer` (77), `tv_monitor` (73), `oven` (17.1, new detection, plausible for a low-use oven), and `always_on` (1107, new detection, an aggregate baseload category rather than one appliance).

`sense_287516` is still the single largest consumer, now 6324 kWh/yr and still unnamed. `other` is now 2195, still unattributed. Together that is still over half of annual usage, invisible.

**Before using any Sense entity, check its `sensor.<device>_yearly_energy`.** A near-zero value means the detection is dead regardless of how plausible the entity name looks.

## Notifications

**This is now wrong if you remember the 2026-08-04 snapshot: mobile push exists.** Two devices are registered under `mobile_app`: `notify.mobile_app_pete_iphone` (Pete's iPhone) and `notify.mobile_app_fire_10` (the Fire HD 10 tablet). `device_tracker.pete_iphone` and `device_tracker.fire_10` come along with the same registration. See [lennox-thermostat-alerts.md](../../../../docs/lennox-climate/lennox-thermostat-alerts.md) for the automation that pushes to a phone and the severity thresholds behind it.

`notify` targets are `notify`, `persistent_notification`, `send_message`, `mobile_app_pete_iphone`, and `mobile_app_fire_10`. Automations can now raise a real phone notification, not just a dashboard one or Sonos TTS. Do not default to "no mobile push" when designing an alert; check whether it should go to Pete's phone instead of, or in addition to, a persistent notification.

## Weather and useful sensors

- `weather.openweathermap` and `weather.forecast_home`, both with daily and hourly forecast support.
- `sensor.openweathermap_temperature`, `sensor.openweathermap_humidity`, plus apparent temperature and dew point.
- `co2signal` provides grid carbon intensity.

## Media

- Sonos, with 9 `switch.gym_gym_*` entities that are all DSP toggles (crossfade, loudness, night sound, subwoofer, surround), not room controls.
- Music Assistant add-on, see the main SKILL.md.
- 11 `media_player` entities: Crestron (Living Room), Gym, LSX II-045089 (Office), Samsung QN90BA 85, carol, gymnasium, plus two new since the last snapshot: Samsung TU7000 60 TV and an LG webOS TV UM7300PUA (powered by the new `lg_thinq` integration). Several appear twice and some read `unavailable`.

## Dashboards

Current as of 2026-08-11 (re-check with `lovelace/dashboards/list`, this list grows fast):

- `dashboard-sound`, titled "Sound", storage mode. One sections view containing a heading, a `custom:wall-clock-card`, and a `custom:sonos-card`. Its section has `column_span: 3`.
- `dashboard-clock`, titled "Clock".
- `map`, titled "Map".
- `dashboard-test`, titled "test".
- `dashboard-lights` ("Lights"), `dashboard-av` ("A/V"), `dashboard-lennox-home` ("Lennox Home"), `dashboard-alarm-system` ("Alarm System"): the domain dashboards, level 2 area grid plus level 3 leaves. Lights and A/V are generated by `scripts/rebuild-domain-dashboard.py`; Lennox Home and Alarm System are hand-authored with no generator. Now pure generation source for Home's tabs (see below); nobody is meant to land on these directly anymore, though their own kiosk chrome (home icon, back buttons) is still live and still stale, pointing at the dead `tablet-home`. See [references/lovelace.md](lovelace.md#domain-dashboards-are-generated-not-hand-edited).
- `tablet-home`, titled "Tablet Home": dead. Was the level 1 root for the `Tablet` kiosk user, a four-card grid navigating to the domain dashboards above; superseded within a day by retargeting `Tablet`'s `default_panel` to `vision-sample`. Unreachable from anywhere in the UI now; should be deleted. Still present as of this snapshot. See `docs/native-dashboards/dashboard-home.md` in the `pdehlke/homeassistant` repo.
- `vision-sample`, **titled "Home"**: the main kiosk dashboard for wall-mounted touch panels, tabs Home, Lights, A/V, Alarm, Climate. `Tablet`'s `default_panel` points here. Lights is fully self-contained and generator-built (`scripts/rebuild-home-tab.py`); Climate is hand-copied from `dashboard-lennox-home` with no generator yet; A/V and Alarm tabs are still empty. See [references/lovelace.md](lovelace.md#homes-own-tabs-are-generated-too-by-a-second-script).
- `homie-dash`, titled "Homie Dash": the installed Homie Dashboard fork, new since the last snapshot. See `docs/homie-dashboard/homie-dashboard-install-plan.md` in the `pdehlke/homeassistant` repo for its architecture, deployment workflow, and checkpoint.
- The default Overview dashboard does not appear in `lovelace/dashboards/list`; its path is `/lovelace/0`.

## Users

- `pete` (id in `config/auth/list`), the owner account, admin.
- `Tablet` (username `tablet`, display name `Tablet`), non-admin, `local_only: true`. Built for a wall-mounted kiosk device; see `docs/native-dashboards/dashboard-home.md`. Its personal `default_panel` and `theme` are set via a short-lived login as that user, since `frontend/set_user_data` only ever writes the calling connection's own user; there is no admin-callable way to set another user's frontend preferences. `NemesisRE/kiosk-mode` hides its sidebar (and, on the domain dashboards, its header too) via `kiosk_mode.user_settings` blocks keyed on the display name `Tablet`, not the username.
- `Homie Dashboard` (display name `Homie Dashboard`), non-admin, `local_only: true`, new since the last snapshot. Scoped for the Homie Dashboard fork's own `kiosk_mode` block (`hide_header` + `hide_sidebar`), same pattern as `Tablet`. See `docs/homie-dashboard/homie-dashboard-install-plan.md`.

(System-created accounts — Supervisor, Home Assistant Cast, Home Assistant Content, and two Home Assistant Cloud accounts — exist but aren't relevant to dashboard or automation work.)

## HACS frontend plugins installed

As of 2026-08-15, the deprecated `thomasloven/lovelace-card-mod` v4.2.1 resource has been replaced by UIX v8.0.1 and must not be reinstalled. The remaining HACS inventory is `rkotulan/ha-wall-clock-card` v3.4.0, `punxaphil/custom-sonos-card` v10.7.1, `r11a/homeii-music-flow` v5.9.3, `NemesisRE/kiosk-mode` v14.0.2, `pkissling/clock-weather-card` v2.9.4, and `Big-Edge2297/homie-dashboard` v4.1.1 (the Homie Dashboard fork's upstream, tracked here as a HACS repository even though the deployed copy is pde's own fork, see `docs/homie-dashboard/homie-dashboard-install-plan.md`). Re-check via `hacs/repositories/list` rather than trusting this list; it will go stale.

## Things previously created here

- `automation.fridge_failure_alert`. Fires when `binary_sensor.fridge_power` reads `off` for 3 hours, raising a persistent notification. The threshold is deliberately loose because the longest observed normal off-gap was 51 minutes; it can tighten toward 90 minutes once more history exists.
- `calendar.home` via Local Calendar, installed because the wall clock card's calendar widget needs a calendar entity and none existed.
- A calendar event titled `DEMO EVENT - safe to delete`. If it is still present and the user has not mentioned it, it can go.
- Five `light.*` template entities in the Primary Suite area (`bedroom_perimeter`, `bedroom_diagonals`, `bath_perimeter`, `bath_diagonals`, `hallway`), same template-light pattern as the original two (`bed_light`, `ceiling_lights`). `hallway` carries both the `bath` and `bedroom` labels at once, deliberately; a label list is not exclusive.
- Two labels, `bath` and `bedroom`, used to target sub-area preset groups a nested area can't express (HA areas do not nest). See [references/api-access.md](api-access.md#websocket) for the creation command.
- `script.smart_toggle_lights`, a reusable field-driven script (`target_area_id` / `target_label_id`) that turns a whole group of lights uniformly on or off based on whether any of them is currently on, because the `light.toggle` service does not do that for a multi-entity target. See [references/api-access.md](api-access.md#a-script-or-automation-field-named-after-a-jinja-global-silently-breaks) for the naming bug that cost the most time building it.
- `scene.bedroom_evening` and `scene.bathroom_evening`, both in Primary Suite: a fixed, specific brightness combination per room rather than a uniform level, the thing an area/label-targeted preset structurally cannot express.
- Five `light.*` template entities in the Entry area (`door`, `home_perimeter`, `garage_sconces`, `entry_perimeter`, `entry_center`), same template-light pattern, no scenes and no group-preset labels for this batch.
- Three `light.*` template entities in Dining Room (`table`, `north`, `south`) and five in Kitchen (`range`, `island`, `pathway`, `cabinet`, `powder`), same pattern again, no scenes or group-preset labels for either.
- `light.primary_suite_lights`, a native HA Light Group helper (not a template light) aggregating the five Primary Suite lights into one entity, created by pde through the UI to give the Vision Sample dashboard's repurposed "Kitchen Lights" tile card (now pointed at this entity) a single toggle and brightness slider for the whole suite.
- `light.kitchen_lights`, the same Light Group pattern applied to the five Kitchen lights, new since the last snapshot.
- Two more `light.*` template entities, `pool_bathroom` and `north_sink`, both placeholder-assigned to the Office area pending a Crestron CLX channel inventory that hasn't happened yet (see the project's `crestron-status-refresh` follow-up). Same template pattern as the rest: an `input_boolean` and `input_number` each, real Crestron wiring to come later without changing the entity IDs.
- `lock.poorly_installed_door` and `alarm_control_panel.security`, both backed by their own `input_boolean` (`poorly_installed_door_locked`, `security_armed`) rather than any real hardware integration yet, matching the light-entity-strategy pattern of building the entity ahead of real control.
- The Lennox iComfort S30 integration (`lennoxs30`), bringing in `climate.casasolar_north_zone_1` and `climate.casasolar_south_zone_1` plus a large set of diagnostic binary sensors, selects, and away-mode switches per unit, and two automations (`automation.lennox_thermostat_alert`, `automation.lennox_reduced_airflow_filter_alert`). See `docs/lennox-climate/`.
- The Rachio integration, covering Main Irrigation's 7 named zones plus standby/rain-delay/even-days switches and the separate Back Yard Smart Hose Timer, with four automations (`rachio_zone_or_valve_disabled_alert`, `rachio_standby_mode_engaged_alert`, `rachio_periodic_config_entry_reload`, `rachio_back_yard_hose_timer_health_alert`). See `docs/rachio/`.
- The Roborock integration, covering `vacuum.q5_max` (the Q5 Max+) and its charging/cleaning/dock/mop/water sensors, plus `automation.roborock_integration_periodic_reload` to work around the known MQTT status-freeze bug. See `docs/device-alerts/roborock-status-mqtt-stall.md`.
- Home Assistant Cloud (Nabu Casa), giving `binary_sensor.remote_ui` and internet-reachable remote access. See `docs/nabucasa-remote-access/nabucasa-remote-ui-dns-fragility.md`.
- The Homie Dashboard fork, deployed as the `homie-dash` Lovelace dashboard with its own `Homie Dashboard` user. See `docs/homie-dashboard/homie-dashboard-install-plan.md`.
- Mobile app registration for Pete's iPhone and the Fire HD 10 tablet, enabling real push notifications and device trackers. See the Notifications section above.
- `script.group_compatible_media_players` and `script.ungroup_compatible_media_players`, for Sonos speaker grouping, not otherwise documented in this archive yet.
- The garage EV charger via the `openevse` integration and a Logitech Harmony Hub (`remote.harmony_hub`) both appear live but have no writeup anywhere in this archive; see the Integrations section above.
