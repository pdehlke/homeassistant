# dashboard-sound uses a panel view, not sections

HOMEii Flow's own card code hardcodes `max_columns: 12` in its `getGridOptions()`, so no external
`grid_options` can push it past 12 of the Sound dashboard's 36-column section width — confirmed
live, the card rendered stuck in its cramped mobile layout at 431px inside a 1310px section
regardless of config. Switching the view from `sections` to `panel` sidesteps the clamp entirely,
giving the one card full width with no grid sizing, and the card then renders its full desktop
layout. The tradeoff, accepted: a panel view holds exactly one card, so nothing else can share the
Sound dashboard's main view without a second view added alongside it. See
`docs/music-assistant/homeii-music-flow.md`.
