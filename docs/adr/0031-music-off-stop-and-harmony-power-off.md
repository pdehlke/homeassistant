# Music off: explicit stop plus Harmony Hub power-off

Tapping an active Music station's bubble a second time (the "off" direction) calls
`media_player.media_stop` on the Crestron player and then `remote.turn_off` on the Harmony Hub's
Airplay activity, rather than pausing (which would add an implicit "paused on what" state HA
scenes never needed to reason about) or stopping Music Assistant while leaving the receiver
running. Turning off the receiver activity as part of "off," not just stopping playback, was the
explicit ask. See `docs/homie-dashboard/homie-music-chip.md`.
