# Home's kiosk_mode hides only the sidebar, not the header

**Status:** Superseded by [ADR-0062](0062-native-dashboards-retired.md) — the pattern this decision applied to is retired.

Every other kiosk dashboard here sets both `hide_header` and `hide_sidebar`, because each built
its own replacement header (card-based clock/date/weather, a home-icon nav button, per-leaf back
buttons). Home has no such replacement, and its native header carries the one thing those other
dashboards don't need from it: the row of view tabs is Home's only navigation between domains.
Setting `hide_header: true` on Home, as it briefly was when copied from the other dashboards' kiosk
block, took the tab strip down with the rest of the native chrome; fixed by dropping `hide_header`
and keeping only `hide_sidebar`. See [docs/native-dashboards/native-dashboards-retired.md](../native-dashboards/native-dashboards-retired.md).
