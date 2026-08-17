# Dashboards mirror the Crestron TSW-752's 3-level hierarchy, not HA's own area-centric layout

**Status:** Superseded by [ADR-0062](0062-native-dashboards-retired.md) — the pattern this decision applied to is retired.

Home Assistant's default area page groups everything in a room by domain together. That's wrong
for a keypad replacement: reaching a dimmer by scrolling past media players and door locks is a
regression from a physical button on a wall. Every generated dashboard instead mirrors the
Crestron panels' fixed structure — domain selection, then an area grid, then a single-domain,
single-area leaf — deliberately diverging from HA's own default. See
[docs/native-dashboards/native-dashboards-retired.md](../native-dashboards/native-dashboards-retired.md).
