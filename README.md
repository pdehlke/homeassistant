# Home Assistant

Notes, planning, and specs for my Home Assistant buildout.

## Contents

- [project-todo.md](project-todo.md)

  A live, ordered backlog for ongoing work, unlike the rest of this archive which records
  finished reasoning. Check it for what's next.

- [area-floor-layout.md](area-floor-layout.md)

  The area and floor structure of the instance. Why the Garage is modelled as a floor (areas
  cannot nest), why HVAC equipment sits in its own mechanical-closet areas, the areas the Lennox
  integration invented on its own, and why entity IDs still contain old area names.

- [crestron-strategy.md](crestron-strategy.md)

  The migration plan for lighting, audio, the alarm system, and HVAC from the existing Crestron
  system (MC2E, AADS, CLX-* lighting modules, TSW-752 panels) to Home Assistant. Options
  considered per subsystem, what was rejected and why, and the phased plan of attack.

- [crestron-migration.md](crestron-migration.md)

  The investigation behind the strategy above: hardware inventory, evaluation of a prior
  AI-generated set of notes against Crestron's own documentation (separating confirmed claims
  from a fabricated tool reference), and direct verification done over telnet and by physical
  inspection.

- [fridge-failure-alert.md](fridge-failure-alert.md)

  The automation that alerts when the fridge stops drawing power. How it works, why it
  measures accumulated running time instead of using a state trigger, and what is still
  needed to get the alert onto a phone.

- [rachio-zone-disabled-alert.md](rachio-zone-disabled-alert.md)

  Three automations: two that alert when a Rachio zone or valve disappears from Home Assistant or
  when the Main Irrigation controller's standby mode turns on, and one that reloads the Rachio
  config entry hourly so the other two ever have something new to detect. Why a disabled zone's
  entity goes stale rather than flagging itself, why the "Standby" switch was never a renamed zone
  despite the name, the baseline-diff detection design, and a source-level investigation into why
  the mechanism needs a periodic forced reload to ever see a real disable at all.

- [lennoxs30-integration.md](lennoxs30-integration.md)

  How the two Lennox iComfort S30 thermostats (North and South) were brought into Home Assistant
  via the `lennoxs30` HACS integration. IP identification method, the local-mode config used, and
  the recovery steps for when South's un-reserved DHCP lease renews with a new address.

- [dashboard-navigation-model.md](dashboard-navigation-model.md)

  How dashboards are organised: a three-level hierarchy copied from the Crestron touch panels,
  domain then area then a single domain in a single area. Why every area gets a card but only
  populated ones are tappable, why presets target areas rather than entities, how the generator is
  parameterised per subsystem, and what A/V needed that the parameterisation could not express.

- [dashboard-header-card.md](dashboard-header-card.md)

  The date, time and weather banner shared by the domain dashboards. Why the clock and date swapped
  places without the slots changing size, why a view header renders only on `sections` views and is
  silently ignored by `masonry`, and why card-mod rules need `!important` to beat a card's own
  stylesheet.

- [dashboard-home.md](dashboard-home.md)

  Home, the tabbed dashboard the Tablet kiosk user actually lands on: why a native tab strip
  replaced the short-lived Tablet Home root dashboard, the session dance needed to set another
  user's default dashboard and theme, why Home hides only the sidebar and not the header, and the
  build status of each tab (Lights self-contained and generator-built, Climate hand-copied and
  generator-pending, A/V and Alarm not yet built).

- [light-entity-strategy.md](light-entity-strategy.md)

  How light entities are built before Crestron control exists: template lights backed by an
  `input_boolean` and an `input_number`, created entirely through the config flow. Why
  `switch_as_x` and the `demo` integration were rejected, and what changes when real control
  arrives.

- [vision-sample-demo-entities.md](vision-sample-demo-entities.md)

  Populating the Vision Sample dashboard's placeholder entities so its cards show live controls
  instead of the theme's demo-integration stand-ins. Which entities were actually missing, why
  the real `demo` integration and the newly-installed Blueprint Studio HACS integration were
  both set aside, and the tilt-support gap in config-flow template covers.

- [vision-sample-pergola-solar-gauge.md](vision-sample-pergola-solar-gauge.md)

  Replacing the Vision Sample dashboard's Pergola Roof placeholder with a live solar/grid-export
  gauge sourced from the Sense energy monitor. Other real entities considered for the spot, why
  the unnamed `sense_287516` node is actually the mains meter, and why the second gauge reads
  gross daily export rather than a net figure that doesn't exist as its own sensor.

- [homeii-music-flow.md](homeii-music-flow.md)

  Replacing the Sound dashboard's cards with the HOMEii Flow Music Assistant card. Why the
  wall clock moved to its own dashboard instead of Overview, why the view had to be `panel`
  instead of `sections`, and why Sendspin and library artwork are blocked in Chrome by Local
  Network Access.

- [homie-dashboard-install-plan.md](homie-dashboard-install-plan.md)

  The installed Homie Dashboard architecture, security model, fork location, deployment workflow,
  accepted Overview customizations, cache-busting strategy, and checkpoint for continuing work.

- [climate-chip-activity-count.md](climate-chip-activity-count.md)

  Fixing the Climate chip's "N on" count on Overview A/B, which counted both thermostats as on
  almost permanently because they stay in `heat_cool` mode nearly always. Now counts only units
  actually heating or cooling, reusing the `hvac_action`-based check Overview C's sidebar glow
  already had, and why the AC card's own on/off toggle deliberately keeps its separate,
  mode-based meaning.

- [lennox-thermostat-alerts.md](lennox-thermostat-alerts.md)

  Forwarding each Lennox S30 thermostat's own console alert into Home Assistant, with critical
  alerts pushed to a phone and a red-dot indicator added to the Homie dashboard's Climate entry
  points. Why the integration's two alert entities can disagree (the console-accurate `_alert`
  sensor versus the detail-bearing but sometimes-empty `_active_alerts` list), the severity
  thresholds agreed with pde, and the automation and dashboard verification.

- [climate-alert-dashboard-threshold.md](climate-alert-dashboard-threshold.md)

  Raising the Climate chip's red-dot threshold from "any severity other than none" to "moderate or
  critical," matching the phone/persistent_notification bar. Why the original, more permissive
  threshold left the dot lit almost continuously once both real thermostats settled into a
  near-permanent `info` state, and why a per-code ignore-list was rejected in favor of the
  across-the-board fix.

- [overview-c-solar-home-green-percentage.md](overview-c-solar-home-green-percentage.md)

  Changing the full-screen Solar view's "Low Carbon" stat from the raw TEP grid green percentage
  to the green share of the home's own consumption, blending solar production with imported grid
  power weighted by each source's share of live usage. The formula, the alternatives rejected
  during a grilling session, and a cache-busting deployment gap the change caught before it shipped.

- [overview-c-solar-today-totals.md](overview-c-solar-today-totals.md)

  Adding "% Green Today" and "CO2 Intensity Today" to the full-screen Solar view: an hourly
  time-weighted extension of the instantaneous Low Carbon formula above, why a single current
  reading misrepresents a whole day, the recorder long-term statistics that make the calculation
  possible, and repurposing the two permanently-unbound inverter-temperature placeholders to show
  them.

- [overview-c-alert-triangle-css-bug.md](overview-c-alert-triangle-css-bug.md)

  Why Overview C's bottom-left alert triangle showed with no active alerts while Overview A/B
  correctly stayed hidden: a CSS specificity tie between two equally-specific selectors, resolved
  by source order rather than the intended `.visible` toggle. The fix, and why reordering the CSS
  instead of raising specificity was rejected as more fragile.

- [homie-thermostat-control-fix.md](homie-thermostat-control-fix.md)

  Post-mortem on the Main House thermostat launcher and overlay, which displayed plausible values
  and moved an on-screen number without ever reaching the real Lennox thermostats. What was
  actually wrong (a Home Assistant service-schema requirement and a silently-dropped step size,
  both invisible to normal error handling), the fixes rejected along the way, and two mistakes the
  fix itself made that only live browser verification caught.

- [roborock-status-mqtt-stall.md](roborock-status-mqtt-stall.md)

  Why the Q5 Max+'s charging/status entities freeze for hours after the vacuum actually finishes
  charging: a known upstream bug where the integration's MQTT push channel stalls while its
  separately-polled entities (battery, consumables) keep updating fine. The periodic-reload
  automation tried first, and the strategy change that replaced it: deriving Overview A/B's status
  pill from battery and cleaning state instead of trusting the fields proven to get stuck.

- [mac-mini-migration.md](mac-mini-migration.md)

  Moving Home Assistant off the Raspberry Pi and onto a headless Late 2014 Mac mini.
  Installation method, storage and SSD choices, external boot persistence, and the migration
  sequence.

- [CLAUDE.md](CLAUDE.md)

  Repo conventions for coding agents. Meta, rather than documentation about Home Assistant.

- [.claude/skills/home-assistant/](.claude/skills/home-assistant/SKILL.md)

  The coding-agent skill for working with this instance and its Music Assistant add-on: which
  of the REST, WebSocket, and MCP access paths to use for a given job, instance quirks, and
  scripts for safe Lovelace edits and dashboard regeneration. Repo-scoped rather than a
  user-scoped dotfiles skill, since it is specific to this instance.
