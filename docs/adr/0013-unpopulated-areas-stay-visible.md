# Unpopulated areas stay visible, not tappable, on level-2 grids

A finished Crestron panel would only show areas that actually contain something. This instance's
domain dashboards show every area regardless, with tapping disabled by omitting `tap_action`
entirely (HA's area card falls back to `{action: "none"}`, and its own `hasAction()` check reports
false for that, so the card renders with no ripple or pointer cursor). Showing only populated
areas was rejected because it would currently collapse a domain dashboard to a single card: the
dashboard doubles as a live migration checklist, with cards lighting up one at a time as Crestron
channels get mapped, and hiding empty areas would hide exactly that information. See
`docs/native-dashboards/dashboard-navigation-model.md`.
