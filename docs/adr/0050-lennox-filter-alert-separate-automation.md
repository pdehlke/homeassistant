# Lennox filter/airflow alert (code 312) is a separate automation, not folded into severity

Lennox code 312 ("Reduced Airflow-Indoor Blower Cutback," most commonly a filter that needs
changing) is actionable at `info` severity specifically, the same level the severity-based alert
and dashboard badge deliberately ignore. The severity automation triggers on `_alert` and only
consults `_active_alerts`' code list as enrichment after it already fired; catching code 312
regardless of current severity means triggering directly on `_active_alerts` instead, a different
entity answering a different question ("is this specific code present" vs. "how bad is the current
severity"). A second, independent automation kept the two concerns from tangling in one
automation's branching logic. Display-only by explicit request: no phone push, since both units sit
at this code often enough that a push would be noise. See
[docs/lennox-climate/lennox-thermostat-alerts.md](../lennox-climate/lennox-thermostat-alerts.md).
