# Home and the standalone domain dashboards are retired; Homie Dashboard is the sole kiosk target

The native three-level dashboard pattern (Home's tabs, plus the standalone `dashboard-lights`,
`dashboard-av`, `dashboard-lennox-home`, and `dashboard-alarm-system`) is retired outright, not one
of the four directions weighed in [GitHub issue #2](https://github.com/pdehlke/homeassistant/issues/2),
which tracked drift risk between Home's tabs and the standalone dashboards without committing to a
fix. None of that issue's four candidates were chosen. The pattern was an experiment built before
Homie Dashboard existed, and the physical Fire HD tablet has been running Homie exclusively since
the `kiosk_mode` fix in the 2026-08-07 checkpoint of
[homie-dashboard-install-plan.md](../homie-dashboard/homie-dashboard-install-plan.md); nothing has
depended on Home or the standalone dashboards since. Continuing to maintain two independently
regenerated copies of the same dashboard content, for a pattern nobody uses, was pure upkeep with no
payoff.

## What was removed

- Live Lovelace dashboards: `vision-sample` (Home), `tablet-home` (Tablet Home, already dead before
  this), `dashboard-lights`, `dashboard-av`, `dashboard-lennox-home`, `dashboard-alarm-system`.
- The `Tablet` HA user account, `script.smart_toggle_lights`, and the `bath`/`bedroom` labels — all
  existed only to serve this pattern.
- The generator scripts `rebuild-domain-dashboard.py` and `rebuild-home-tab.py`.
- Five detailed docs (`dashboard-home.md`, `dashboard-navigation-model.md`, `dashboard-header-card.md`,
  `vision-sample-demo-entities.md`, `vision-sample-pergola-solar-gauge.md`), consolidated into one
  retrospective, [native-dashboards-retired.md](../native-dashboards/native-dashboards-retired.md),
  rather than deleted without a trace — this repo's own convention is to keep the reasoning behind a
  decision, not just its outcome.

## What was not touched

`dashboard-office` and its own docs (the `office-*.md` files), `dashboard-sound`, `dashboard-clock`,
`dashboard-test`, the `Homie Dashboard` and `Office` HA users, and `homie-dash` itself. None of these
are part of the retired pattern.

## Superseded ADRs

ADR-0012 through ADR-0018 recorded decisions specific to this pattern (the Crestron-mirrored
hierarchy, area-grid presets, group presets via labels, `smart_toggle_lights`, Home's tab strip, and
Home's sidebar-only `kiosk_mode`). They are marked superseded by this ADR rather than deleted; the
reasoning they captured is still worth having even though the pattern it applied to is gone.
