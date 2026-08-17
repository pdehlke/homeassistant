# Home replaces a root dashboard with self-contained view tabs as level 1

**Status:** Superseded by [ADR-0062](0062-native-dashboards-retired.md) — the pattern this decision applied to is retired.

The first level-1 attempt, Tablet Home, was a separate 2x2-button root dashboard navigating out to
four standalone domain dashboards. It lasted under a day. Home's own native view-tab strip (Home,
Lights, A/V, Alarm, Climate) does level 1's job directly instead, with each tab holding that
domain's full level 2/3 content generated onto Home's own views rather than linking out, so the
kiosk experience never depends on navigating to a different dashboard with its own, different
kiosk chrome. See [docs/native-dashboards/native-dashboards-retired.md](../native-dashboards/native-dashboards-retired.md).
