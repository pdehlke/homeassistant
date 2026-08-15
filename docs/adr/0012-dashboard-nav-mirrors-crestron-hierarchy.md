# Dashboards mirror the Crestron TSW-752's 3-level hierarchy, not HA's own area-centric layout

Home Assistant's default area page groups everything in a room by domain together. That's wrong
for a keypad replacement: reaching a dimmer by scrolling past media players and door locks is a
regression from a physical button on a wall. Every generated dashboard instead mirrors the
Crestron panels' fixed structure — domain selection, then an area grid, then a single-domain,
single-area leaf — deliberately diverging from HA's own default. See
`docs/native-dashboards/dashboard-navigation-model.md`.
