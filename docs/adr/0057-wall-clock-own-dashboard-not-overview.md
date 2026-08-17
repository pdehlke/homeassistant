# Wall clock moved to its own dashboard, not the generated Overview

The obvious place to park the displaced wall clock card was the sidebar's "Overview" dashboard,
but on this HA version that's a generated dashboard (`home` strategy, one view per area) with no
stored config at all. Saving anything to it means taking control of it: freezing the current areas
and summary views as static YAML, so new areas and newly discovered devices stop appearing on
their own. That cost wasn't worth a wall clock, so it went to a new storage dashboard,
`dashboard-clock`, with its original section shape, `grid_options`, and glass layout preserved
unchanged, leaving Overview's automatic per-area generation untouched. See
[docs/music-assistant/homeii-music-flow.md](../music-assistant/homeii-music-flow.md).
