# Music volume resets only on idle-to-on transitions

The literal ask ("volume pre-set to X%") would reset volume on every tap, including a direct
hot-switch between two already-playing stations — the common case once more than one station sees
regular use. Chosen instead: reset volume only when the player wasn't already `"playing"` at the
moment of the tap; a hot-switch leaves volume exactly where it was last set. Applied uniformly to
"was playing anything at all," not specifically one of the chip's own six stations, since a
hot-switch away from unrelated audio shouldn't blast to a fixed volume any more than a hot-switch
between two presets should. See [docs/homie-dashboard/homie-music-chip.md](../homie-dashboard/homie-music-chip.md).
