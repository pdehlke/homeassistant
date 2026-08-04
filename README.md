# Home Assistant

Notes, planning, and specs for my Home Assistant buildout.

## Contents

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
