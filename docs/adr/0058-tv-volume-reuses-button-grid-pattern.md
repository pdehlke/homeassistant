# TV volume/mute controls reuse the existing button-grid row, not a rocker widget

A rocker-style widget would read as more semantically honest for continuous volume
adjustment (a different kind of control than the discrete activity-switch buttons around it), but
it would introduce a new visual language into a popup that otherwise has exactly one: the
icon-plus-label button grid already established by the activity buttons (Watch TV, Watch a Movie,
All Off). A second `tv-action-row` matching that existing grid was chosen instead, needing zero new
CSS beyond a `:disabled` state. See `docs/harmony-hub/homie-tv-volume-mute-controls.md`.
