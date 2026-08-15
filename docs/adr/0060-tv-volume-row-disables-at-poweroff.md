# TV volume row disables when the activity is off, rather than staying always-tappable

A physical remote's volume button does nothing when nothing is on, but a dashboard button that
visibly greys out at `current_activity === "PowerOff"` communicates that directly instead of
leaving a tap to silently do nothing. `refreshTVControlUI`, already responsible for the activity
badge, was extended to also toggle the three volume buttons' native `disabled` attribute, tracking
activity state with no separate subscription. See
`docs/harmony-hub/homie-tv-volume-mute-controls.md`.
