# Lennox thermostat alerts

Forwards each Lennox S30 thermostat's own console alert into Home Assistant, with critical
alerts also pushed to a phone, and a red-dot indicator on every Homie dashboard entry point that
already carries one for Irrigation. Built after the South thermostat's console started showing
Error 434 (`OU Inverter Communication Error To Main Control`, per the integration's own error
table) with nothing in Home Assistant surfacing it.

See [lennoxs30-integration.md](lennoxs30-integration.md) for how the two thermostats were brought
into Home Assistant in the first place, and
[homie-dashboard-install-plan.md](homie-dashboard-install-plan.md) for the fork and deployment
workflow the dashboard half of this change went through.

## Two alert signals, and why only one of them is trustworthy right now

The `lennoxs30` integration exposes two different entities per thermostat, and they can disagree:

| Entity | What it is |
| :--- | :--- |
| `sensor.basement_<system>_<system>_alert` | A raw status field from the thermostat itself. Values, per the integration's own docs: `critical`, `moderate`, `minor`, `info`, `none`. Mirrors the console directly. |
| `sensor.basement_<system>_<system>_active_alerts` | A count plus an `alert_list` attribute of structured alert objects (`code`, `message`, `priority`, `isStillActive`, and others), derived from a separate `alerts.active` array in the same status payload. |

Confirmed by reading the integration's source
([`sensor.py`](https://github.com/PeteRager/lennoxs30/blob/2026.6.0/custom_components/lennoxs30/sensor.py))
and the underlying API library
([`s30api_async.py`](https://github.com/PeteRager/lennoxs30api/blob/master/lennoxs30api/s30api_async.py)):
`alert` is copied straight from a `status.alert` field, while `active_alerts` is built by filtering
a separate `alerts.active` array for `isStillActive` entries. They come from different sections of
the same device payload and are not derived from each other.

At the time this was built, South's `_alert` sensor read `critical`, matching the physical
console, but South's `_active_alerts` sensor read an empty `alert_list` (`alerts_num_cleared: 16`,
one more than the prior check), even though Error 434 is a real code in the integration's own
[`lennox_errors.py`](https://github.com/PeteRager/lennoxs30api/blob/master/lennoxs30api/lennox_errors.py)
table (`OU Inverter Communication Error To Main Control`). North, meanwhile, had both sensors
agree: `_alert` read `info` and `_active_alerts` held a matching entry (code 901, "Inconsistent
Indoor Temp"). The likely explanation: many Lennox alerts, including transient inverter comm
errors, clear themselves from the structured queue once the underlying condition passes, while the
console's own status field stays at whatever level it last reported until the unit re-evaluates or
someone acknowledges it on the panel. The two fields are allowed to be transiently inconsistent by
design, not a bug in the integration.

Consequence for this automation: `_alert` is the trigger, because it is the one confirmed to match
what is actually on the console right now. `_active_alerts` is used only as best-effort
enrichment, looked up by matching `priority` against the current `_alert` value. When, as with
South's Error 434, the detail has already rotated out of `_active_alerts`, the notification says so
plainly rather than guessing or omitting the discrepancy.

## Severity mapping

Agreed with pde before writing anything, since the literal ask ("HA alert whenever Lennox
generates an alert, critical also to iPhone") left the exact thresholds open:

| Lennox severity | Home Assistant | iPhone push |
| :--- | :--- | :--- |
| `critical` | `persistent_notification` | Yes, `notify.notify` |
| `moderate` | `persistent_notification` | No |
| `minor` | Nothing | No |
| `info` | Nothing | No |
| `none` | Existing notification for that thermostat is dismissed | — |

The Homie dashboard badge originally used a separate, more permissive threshold: any state other
than `none` (including `minor` and `info`) lit the red dot. That was pde's explicit call at the
time, distinct from the HA-notification threshold above: a glanceable dashboard indicator and an
interruption worth a persistent record are different bars.

**Revised 2026-08-09**: with both real thermostats spending most of their time at `info`, the
permissive threshold meant the dot stayed lit almost continuously for conditions nobody intended to
act on. The dashboard badge now uses the same "moderate or worse" bar as the notification above.
See [climate-alert-dashboard-threshold.md](climate-alert-dashboard-threshold.md) for the change and
what was rejected. The rest of this section, including the severity mapping table above, is
unchanged and still describes the current automation.

## The automation

`automation.lennox_thermostat_alert`, created via the REST config API, `mode: queued`. Both
thermostats are recomputed on every run regardless of which one triggered it, the same
diff-everything-every-time approach `rachio-zone-disabled-alert.md` uses, rather than branching on
`trigger.entity_id`. This also makes it directly testable with a plain `automation.trigger` call,
with no fabricated trigger context required.

```yaml
id: lennox_thermostat_alert
alias: Lennox thermostat alert
triggers:
  - trigger: state
    entity_id:
      - sensor.basement_casasolar_south_casasolar_south_alert
      - sensor.basement_casasolar_north_casasolar_north_alert
conditions: []
actions:
  - repeat:
      for_each:
        - name: South
          key: south
          alert_entity: sensor.basement_casasolar_south_casasolar_south_alert
          active_entity: sensor.basement_casasolar_south_casasolar_south_active_alerts
        - name: North
          key: north
          alert_entity: sensor.basement_casasolar_north_casasolar_north_alert
          active_entity: sensor.basement_casasolar_north_casasolar_north_active_alerts
      sequence:
        - variables:
            severity: "{{ states(repeat.item.alert_entity) }}"
            severity_rank: >-
              {% set order = ['critical','moderate','minor','info','none'] %}
              {{ order.index(severity) if severity in order else 99 }}
            alert_list: "{{ state_attr(repeat.item.active_entity, 'alert_list') or [] }}"
            matches: "{{ alert_list | selectattr('priority','eq', severity) | list }}"
            detail: >-
              {{ (matches[0].message ~ ' (code ' ~ matches[0].code ~ ')') if matches | length > 0
              else 'No further detail available from Home Assistant right now; check the
              thermostat console or Lennox app.' }}
        - if:
            - condition: template
              value_template: "{{ severity_rank | int <= 1 }}"
          then:
            - action: persistent_notification.create
              data:
                notification_id: "lennox_alert_{{ repeat.item.key }}"
                title: "{{ repeat.item.name }} thermostat: {{ severity }} alert"
                message: "{{ detail }}"
            - if:
                - condition: template
                  value_template: "{{ severity == 'critical' }}"
              then:
                - action: notify.notify
                  continue_on_error: true
                  data:
                    title: "{{ repeat.item.name }} thermostat: critical alert"
                    message: "{{ detail }}"
          else:
            - action: persistent_notification.dismiss
              data:
                notification_id: "lennox_alert_{{ repeat.item.key }}"
mode: queued
max: 10
```

`severity_rank` maps the five-level ladder to `0..4` (`unavailable`/`unknown` map to `99`, treated
as "no alert" rather than raising a template error); `<= 1` is "moderate or worse." An
`unavailable` alert sensor, meaning the integration itself has lost contact with the thermostat,
deliberately does not raise a Lennox alert notification here; that is a different failure mode
than the one this automation covers, matching the DHCP/connectivity gap already tracked in
`lennoxs30-integration.md`.

`persistent_notification.dismiss` on a `notification_id` that was never created is a no-op, so the
`else` branch is safe to run unconditionally on every pass rather than needing to track whether a
notification previously existed.

Per-thermostat `notification_id`s (`lennox_alert_south` / `lennox_alert_north`) so both can be
visible in Home Assistant at once without one overwriting the other, and so each clears
independently when its own thermostat recovers.

### Naming: South/North, not Main House/Office Wing

The notification text uses `South`/`North`, matching `lennoxs30-integration.md`, the entity IDs,
and this repo's naming throughout. The Homie dashboard's Climate chip labels the same two zones
`Main House` and `Office Wing`. Deliberately not reused here: the notification lives in Home
Assistant, not on the dashboard, and every other document about these thermostats already uses
South/North.

### Why a normal push, not iOS's Critical Alert feature

"Critical" in the ask was Lennox's own severity word, not necessarily a request for iOS's Critical
Alert feature (the one that bypasses silent mode and Do Not Disturb, which the HA companion app
does support with a special sound payload). Confirmed directly with pde: a normal notification is
correct here, same delivery mechanism `fridge-failure-alert.md` and the Rachio alerts already use.

## Verification

Created via `POST /api/config/automation/config/lennox_thermostat_alert`, then `POST
/api/config/core/check_config` returned `"result": "valid"`. Triggered manually with
`automation/trigger` (`skip_condition: true`) against the instance's real live data (South
`critical`, North `info`): the trace (`trace/get`) showed a clean `finished` run with per-iteration
variables confirming `severity_rank` 0 for South and 3 for North, `persistent_notification.create`
and `notify.notify` both called for South with no error recorded on either step, and
`persistent_notification.dismiss` called for North (a no-op, since North had no existing
notification). `persistent_notification/get` afterward showed exactly the expected
`lennox_alert_south` notification. pde confirmed the push landed on his phone.

## The dashboard badge

Extends the same three entry points `rachio-zone-disabled-alert.md` built for Irrigation's
disabled-zone indicator, reusing their existing DOM elements and CSS rather than adding new ones:
the Overview A/B chip dot (`chip-alert-${i}` / `ov2-alert-${i}`) and the Overview C sidebar icon
dot (`ov3-sb-alert-${i}`). Each toggle site already special-cased `c.label === "Irrigation"`; a new
`else if (c.label === "Climate")` branch was added alongside it in all three places, driven by a
new `lennoxAlertActive()` helper mirroring `irrigationDisabledZones()`.

The Climate control's `subEntities` in `dist/config.js` gained an `alertEntity` field pointing each
`climate.*` entity at its paired `_alert` sensor:

```js
{
  label: "Climate",
  action: "thermostat",
  showCount: true,
  subEntities: [
    { label: "Main House", entity: "climate.casasolar_south_zone_1",
      alertEntity: "sensor.basement_casasolar_south_casasolar_south_alert" },
    { label: "Office Wing", entity: "climate.casasolar_north_zone_1",
      alertEntity: "sensor.basement_casasolar_north_casasolar_north_alert" },
  ],
},
```

`lennoxAlertActive()` filters those `subEntities` down to the ones whose `alertEntity` currently
reads anything other than `none`/`unavailable`/`unknown`. Verified live via Playwright against
South's real critical state: the red dot renders on Overview A's Climate chip, Overview B's
sidebar list, and Overview C's thermometer sidebar icon (the existing amber "on" glow and the new
red alert dot render in opposite corners simultaneously, same layout Irrigation already used).

56 existing tests plus 3 new ones (`test/screen-a.test.cjs`): the `Climate` control's `subEntities`
now carry the right `alertEntity` values, and the badge wiring at all three entry points reuses the
existing elements and helper pattern rather than duplicating it. 57/57 passing.

### A second cache-busting bump this change needed

`homie-dashboard.html` itself changed (the three `else if` branches), on top of `homie-custom.js`
being untouched this time and `config.js` gaining the `alertEntity` fields. `HOMIE_ASSET_VERSION`
was bumped `20260809.1` → `20260809.2`, and the `homie-dash` Lovelace iframe strategy's `?v=` was
bumped to match, same two-boundary requirement recorded in
[overview-c-solar-home-green-percentage.md](overview-c-solar-home-green-percentage.md). A test
(`"Homie HTML loads config and helpers with one release token"`) asserts the literal version
string, which is what caught that the previous session's version bump had gone out without updating
this test's expectation; fixed as part of this change.

`config.js` carries the live long-lived token and is never committed with a real value in Git. The
deployed copy was built by taking the tracked (placeholder) `dist/config.js`, substituting the live
token line pulled directly from the already-deployed live file entirely over the SSH session (never
printed, never touched this machine), and verifying byte-for-byte equality with the tracked file
on every other line via a token-line-stripped SHA-256 comparison before deploying.

## Filter-change alert for code 312 (Reduced Airflow-Indoor Blower Cutback)

A second, independent automation, `automation.lennox_reduced_airflow_filter_alert`, watches for one
specific code rather than a severity level: Lennox code 312, "Reduced Airflow-Indoor Blower
Cutback," Lennox's own shorthand for "the blower can't move the air it wants to, most commonly
because the filter needs changing." Both South and North have sat at `info` severity for a while
(see "Two alert signals" above), which the severity-based automation and dashboard badge correctly
ignore now that [climate-alert-dashboard-threshold.md](climate-alert-dashboard-threshold.md)
narrowed their threshold to moderate/critical. Code 312 needed its own path because it is
actionable at `info` severity specifically: "change the filter" is a real, useful thing to tell pde
even though it never rises to a level either the phone push or the dashboard dot cares about.

### Why a separate automation rather than extending the existing one

`automation.lennox_thermostat_alert` triggers on the `_alert` severity sensor and branches on
severity level; it does not look at `_active_alerts`' code list at all except as enrichment once
already triggered. Code 312 needed to be found regardless of what `_alert` currently reads, which
means triggering directly on the `_active_alerts` entity instead. Different trigger entity,
different question being asked ("is this specific code present" vs. "how bad is the current
severity"), so a second automation kept the two concerns from tangling in one automation's
branching logic.

### The automation

Same `repeat`/per-thermostat/dismiss-safety-net shape as `automation.lennox_thermostat_alert`,
built via the REST config API:

```yaml
id: lennox_reduced_airflow_filter_alert
alias: Lennox reduced airflow filter alert
triggers:
  - trigger: state
    entity_id:
      - sensor.basement_casasolar_south_casasolar_south_active_alerts
      - sensor.basement_casasolar_north_casasolar_north_active_alerts
conditions: []
actions:
  - repeat:
      for_each:
        - name: South
          key: south
          active_entity: sensor.basement_casasolar_south_casasolar_south_active_alerts
        - name: North
          key: north
          active_entity: sensor.basement_casasolar_north_casasolar_north_active_alerts
      sequence:
        - variables:
            alert_list: "{{ state_attr(repeat.item.active_entity, 'alert_list') or [] }}"
            has_312: "{{ alert_list | selectattr('code', 'eq', 312) | list | count > 0 }}"
        - if:
            - condition: template
              value_template: "{{ has_312 }}"
          then:
            - action: persistent_notification.create
              data:
                notification_id: "lennox_filter_{{ repeat.item.key }}"
                title: "{{ repeat.item.name }} thermostat: reduced airflow"
                message: >-
                  Code 312 (Reduced Airflow-Indoor Blower Cutback) is active on the
                  {{ repeat.item.name }} unit. Common fix: change the air filter.
          else:
            - action: persistent_notification.dismiss
              data:
                notification_id: "lennox_filter_{{ repeat.item.key }}"
mode: queued
max: 10
```

A plain HA `state` trigger with no `to`/`from` fires on any update to the entity, attribute changes
included, so this catches code 312 appearing or clearing from `alert_list` even on a pass where the
`_active_alerts` entity's numeric `state` (its active-alert count) doesn't itself change. Per-unit
`notification_id`s (`lennox_filter_south` / `lennox_filter_north`), same reasoning as the severity
automation: both can show independently, and `persistent_notification.dismiss` on a nonexistent id
is a no-op, so the `else` branch is safe to run unconditionally every pass.

Display-only on purpose: `persistent_notification.create` only, no `notify.notify` call. Explicit
ask from pde: this condition is common enough (both units have things sitting in `_active_alerts`
at `info` more or less permanently) that a phone push would be noise; the dashboard/HA UI is enough
for something that just means "change the filter when convenient."

### Verification

Created via `POST /api/config/automation/config/lennox_reduced_airflow_filter_alert`, `POST
/api/config/core/check_config` returned `"result": "valid"`. Triggered manually with
`automation/trigger` (`skip_condition: true`) against the instance's real live data at the time
(South carrying code 312, North carrying only code 901): the trace showed `script_execution:
"finished"` with no errors, per-iteration `has_312` of `true` for South and `false` for North, and
`persistent_notification/get` afterward showed exactly one notification,
`lennox_filter_south`, with the expected title and message. North correctly got no notification.

### Checking alert codes without the dashboard

pde asked for a way to check either unit's current alert codes directly, since none of the HA UI's
existing views surface `_active_alerts`' `alert_list` attribute in a readable form.
`.claude/skills/home-assistant/scripts/check-lennox-alerts.py` reads both units' `_alert` and
`_active_alerts` sensors over REST and prints each unit's severity plus every currently active
code, message, and priority:

```
$ python3 check-lennox-alerts.py
South (Main House)
  Severity (_alert): info
  Active alert codes:
    312: Reduced Airflow-Indoor Blower Cutback (priority: info)

North (Office Wing)
  Severity (_alert): info
  Active alert codes:
    901: Inconsistent Indoor Temp (priority: info)
```

`--unit south`/`--unit north` limits the check to one thermostat. `--code 312` highlights a specific
code and sets the exit status (0 if present on a checked unit, 1 otherwise), for scripting against.
Needs `$HA_TOKEN` in the environment, same as every other script in that directory.
