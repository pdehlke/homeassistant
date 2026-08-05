# Home Assistant

Notes, planning, and specs for my Home Assistant buildout.

## Contents

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

- [dashboard-tablet-home.md](dashboard-tablet-home.md)

  The root, level 1 dashboard: four domain cards in Crestron top-screen order, why Alarm stays
  non-tappable until it has entities, the new non-admin Tablet kiosk user and why setting its
  personal default dashboard needed a short-lived login as that user, the kiosk-mode plugin that
  hides the sidebar and header for it, and the home-icon nav added to the shared header so there is
  a way back.

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

- [homeii-music-flow.md](homeii-music-flow.md)

  Replacing the Sound dashboard's cards with the HOMEii Flow Music Assistant card. Why the
  wall clock moved to its own dashboard instead of Overview, why the view had to be `panel`
  instead of `sections`, and why Sendspin and library artwork are blocked in Chrome by Local
  Network Access.

- [mac-mini-migration.md](mac-mini-migration.md)

  Moving Home Assistant off the Raspberry Pi and onto a headless Late 2014 Mac mini.
  Installation method, storage and SSD choices, external boot persistence, and the migration
  sequence.

- [CLAUDE.md](CLAUDE.md)

  Repo conventions for coding agents. Meta, rather than documentation about Home Assistant.
