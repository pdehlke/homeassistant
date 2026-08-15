# Rachio reload-race false positives fixed via trigger timing, not the diff logic

An hourly config-entry reload tears down and repopulates every Rachio entity over several seconds
(7-23 seconds observed), and the disabled-zone alert's state trigger fired on every transient blip
mid-reload, overwriting its own baseline with a partially-repopulated entity set on the very first
run of each collapse — a false positive baked into the automation's own architecture, firing on
every single hourly reload. Fixed with two trigger-level changes only, no change to the diff logic
itself, which was already correct: a 60-second `for:` debounce on the state trigger (comfortably
above the worst observed settle time) and moving the 30-minute fallback off `:00`/`:30` to `:10`/
`:40`, clear of the reload's collapse window. See `docs/rachio/rachio-zone-disabled-alert.md`.
