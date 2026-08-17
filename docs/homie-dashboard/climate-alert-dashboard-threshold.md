# Climate chip red dot: raising the dashboard threshold to moderate/critical

The Climate chip's red alert dot (Overview A chip, Overview B sidebar list, Overview C sidebar
icon) was lighting continuously even though neither Lennox thermostat had anything above `info`
severity. Not a malfunction: it was the originally agreed threshold doing exactly what it was
built to do. The threshold itself was revised.

See [lennox-thermostat-alerts.md](../lennox-climate/lennox-thermostat-alerts.md) for the alert automation and the
original badge design, and [homie-dashboard-install-plan.md](homie-dashboard-install-plan.md) for
the fork and deployment workflow.

## What was actually happening

Both thermostats' `_alert` sensors read `info` at the time this was raised (South: code 312,
"Reduced Airflow-Indoor Blower Cutback"; North: code 901, "Inconsistent Indoor Temp", the same
code already flagged in [lennox-thermostat-alerts.md](../lennox-climate/lennox-thermostat-alerts.md) as one North seems to sit in more or less
permanently). `lennoxAlertActive()`, the shared helper behind all three Climate entry points, lit
the dot for any state other than `none`/`unavailable`/`unknown` — which by original design
included `info` and `minor`. That was a deliberate, explicit call at the time
([lennox-thermostat-alerts.md](../lennox-climate/lennox-thermostat-alerts.md)'s "Severity mapping" section): the dashboard badge was meant to be
a more permissive, glanceable indicator than the phone/persistent_notification threshold, on the
reasoning that a dashboard dot and an interruption worth a persistent record are different bars.

In practice, with both real thermostats spending most of their time at `info`, that permissive bar
meant the dot stayed lit almost continuously for conditions nobody intended to act on, which
defeated its purpose as a glanceable "something needs attention" signal.

## The fix

`lennoxAlertActive()` now lights only for `critical` or `moderate`, the same "moderate or worse"
bar `automation.lennox_thermostat_alert` already uses for the phone/persistent_notification push.
The dashboard badge and the HA-level notification now agree on what counts as worth surfacing.

```js
return (climateCtrl.subEntities || []).filter(s => {
  if (!s.alertEntity) return false;
  const d = haGetCached(s.alertEntity);
  return d && (d.state === "critical" || d.state === "moderate");
});
```

Single shared function, so Overview A's chip, Overview B's mirrored list, and Overview C's sidebar
icon all picked up the change at once, same as when the function was first introduced.

## What was considered and rejected

**Keep the permissive any-non-none threshold, but suppress specific chronic codes** (312 Reduced
Airflow, 901 Inconsistent Indoor Temp) via a per-code ignore-list. Rejected: it would need
maintaining as new codes settle into a similar chronic-`info` pattern, and it doesn't address the
actual mismatch, which is that the dashboard bar was more permissive than the bar anyone actually
wanted to look at. Raising the threshold to match the notification bar fixes the general case
instead of two specific codes.

## Verification

`test/screen-a.test.cjs`: a new test drives `lennoxAlertActive()`'s exact source against the
`critical`/`moderate` requirement and asserts the old `!== "none"` check is gone; the existing
Climate-badge shape test was updated to match. 63/63 passing.

Deployed live (`HOMIE_ASSET_VERSION` `20260809.5` → `20260809.6`, `homie-dash` Lovelace iframe
`?v=` bumped to match) alongside the unrelated Overview C alert-triangle fix in
[overview-c-alert-triangle-css-bug.md](overview-c-alert-triangle-css-bug.md), bundled into one
commit and one release on pde's call. Confirmed live via Playwright against the instance's real
data at deploy time (South and North both `info`): all four `.ov3-sb-alert-dot` elements, Climate's
included, read `visible: false`, and the same held for the Overview A/B entry points that share the
function.
