# TV mute feedback uses the shared status line, not a persistent highlight

Harmony reports no volume level or mute state back for any device, so a persistent "muted"
highlight on the Mute button would be a guess rendered as fact — and it would drift silently the
moment anyone used the physical remote or the receiver's own front panel, since nothing observes
real state, only the last button this dashboard itself pressed. The shared `tv-feedback`
Sending…/Done line was used instead, the same fire-and-forget acknowledgment every other control on
this overlay already gives. See `docs/harmony-hub/homie-tv-volume-mute-controls.md`.
