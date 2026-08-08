# Rachio zone disabled alert

Two automations that alert when a Rachio zone or valve disappears from Home Assistant, or when
the Main Irrigation controller's whole-device standby mode turns on.

| Object | Entity |
|---|---|
| Automation | `automation.rachio_zone_or_valve_disabled_alert` (id `rachio_zone_disabled_alert`) |
| Automation | `automation.rachio_standby_mode_engaged_alert` (id `rachio_standby_engaged_alert`) |
| Helper | `input_text.rachio_known_zone_switches` (baseline, max length 255) |
| Source | Rachio integration switches on the Main Irrigation controller and the Back Yard Smart Hose Timer |

Both automations are live and enabled. Verified working on 2026-08-08 against Home Assistant
2026.7.4 by calling `automation.trigger` directly and confirming the resulting persistent
notification, then dismissing it.

## Why this exists

pde's actual Rachio app defines five zones on the Main Irrigation controller: East of garage,
East Triangle, Emma's yard, south of driveway, and North. North was disabled as of 2026-08-08
pending a leak repair. Noticing that a zone silently went missing from Home Assistant, rather
than only from the Rachio app, was not previously possible here at all: nothing watched for it.

## The starting hypothesis, and why it was wrong

Before writing any automation, the working theory was that Home Assistant's Rachio integration
renames a disabled zone's existing entity to something generic rather than removing it, and that
`switch.main_irrigation_standby` was North's entity wearing that generic name. If true, the alert
could just watch that one entity for a name or attribute change.

Two pieces of evidence ruled this out before any code was written:

1. **`unique_id` shape.** The four real zone switches all follow the pattern
   `<controller>-zone-<zone-uuid>`, for example
   `080ebda8-8f84-4d57-9823-9beb0dd398e1-zone-c9f68027-704b-4f1f-b7de-976adadee357` for East of
   garage. `switch.main_irrigation_standby`'s `unique_id` is
   `080ebda8-8f84-4d57-9823-9beb0dd398e1-standby`, a fixed suffix with no zone UUID in it at all,
   the same shape as `-delay` (rain delay) and `-schedule-<uuid>` (the watering schedule switch).
   It is not a zone entity that got renamed; it was never a zone entity.
2. **The integration's own documentation.** The [Home Assistant Rachio integration
   docs](https://www.home-assistant.io/integrations/rachio/) state plainly that "a switch will be
   added for every zone that is enabled on every controller in the account," alongside separate,
   fixed switches for standby mode, rain delay, and each schedule. A disabled zone is not
   renamed or flagged; it simply has no switch entity in Home Assistant at all.

Confirmed by attribute content, not just the doc: the four real zone switches all carry `Zone
number`, `Summary`, `Shade`, `Type`, `Slope`, and `entity_picture` attributes pulled from Rachio's
own zone data. `switch.main_irrigation_standby` carries none of those, only a bare
`friendly_name`, exactly what a controller-level mode toggle would have and a zone entity would
not.

The corrected model this alert is built on: disabling a zone in the Rachio app removes its switch
entity from Home Assistant on the next integration refresh. Re-enabling North should create a
*new* entity (`switch.main_irrigation_north` is the expected name, unconfirmed until it happens)
rather than renaming Standby back. This is worth re-checking once the leak is fixed, since it is
an inference from the code and docs, not something observed happening on this instance yet.

## Baseline inventory, 2026-08-08, before the leak fix

The full set of entities the Rachio integration's config entry owns, captured before any zone
changes today, for comparison after North is re-enabled.

Main Irrigation controller (device model `GENERATION3_8ZONE`, 8 physical zone capacity):

| Entity | State | Notes |
|---|---|---|
| `switch.main_irrigation_emmas_yard` | `off` | Zone number 2 |
| `switch.main_irrigation_south_of_driveway` | `off` | Zone number 3 |
| `switch.main_irrigation_east_of_garage` | `off` | Zone number 4 |
| `switch.main_irrigation_east_triangle` | `off` | Zone number 5 |
| `switch.main_irrigation_standby` | `off` | controller-wide mode toggle, not a zone |
| `switch.main_irrigation_rain_delay` | `off` | |
| `switch.main_irrigation_even_days_schedule` | `off` | the one configured schedule |
| `binary_sensor.main_irrigation_connectivity` | `on` | |
| `binary_sensor.main_irrigation_rain` | `off` | |
| `calendar.rachio_base_station_ca358975` | — | |

No zone number 1 is present. Given the observed numbering (2 through 5 are the four enabled
zones), zone 1 is the most likely candidate for North, but this is inferred from the gap, not
confirmed.

Back Yard Smart Hose Timer (separate device, already known to be offline, see `project-todo.md`
item 3's sibling notes):

| Entity | State |
|---|---|
| `switch.back_yard_irrigation` | `unavailable` |
| `binary_sensor.back_yard_irrigation_battery` | `unavailable` |
| `binary_sensor.back_yard_irrigation_flow` | `unavailable` |

Back Yard's `unavailable` state is the existing, already-documented offline-controller condition,
not something new. The alert built here tracks whether `switch.back_yard_irrigation` continues to
*exist* in the entity registry, which is unaffected by whether it is currently reachable.

Re-run the queries in [Reproducing the measurements](#reproducing-the-measurements) after the
leak fix and diff against this table.

## How it works

Disabling a zone does not flip a flag Home Assistant can watch; it deletes the entity. There is
nothing to put a `state` trigger on. Detection has to be a diff against a remembered set of
entities that should exist.

`input_text.rachio_known_zone_switches` holds a comma-separated list of short keys, one per zone
or valve switch last seen present: the Main Irrigation prefix is stripped
(`east_of_garage`, not `switch.main_irrigation_east_of_garage`) to leave headroom under the
255-character state-string limit as more zones come back online. A "real zone" switch is
identified generically, by having a `Zone number` attribute, rather than by a hardcoded name list,
so North reappearing is picked up automatically without an edit here.

```yaml
id: rachio_zone_disabled_alert
alias: Rachio zone or valve disabled alert
triggers:
  - trigger: time_pattern
    minutes: "/30"
  - trigger: homeassistant
    event: start
conditions: []
actions:
  - variables:
      current_keys: >-
        {% set prefix = 'switch.main_irrigation_' %}
        {% set ns = namespace(keys=[]) %}
        {% for e in device_entities('1a3374a701b62fe0e05e7faae6e19b50') %}
          {% if e.startswith('switch.') and state_attr(e, 'Zone number') is not none %}
            {% set ns.keys = ns.keys + [e.replace(prefix, '')] %}
          {% endif %}
        {% endfor %}
        {% for e in device_entities('660935a36d62431b1438e2046b428c9f') %}
          {% if e.startswith('switch.') %}
            {% set ns.keys = ns.keys + [e.replace('switch.', '')] %}
          {% endif %}
        {% endfor %}
        {{ ns.keys | sort | join(',') }}
  - variables:
      missing_keys: >-
        {% set baseline = states('input_text.rachio_known_zone_switches').split(',') %}
        {% set current_list = current_keys.split(',') %}
        {% set ns2 = namespace(missing=[]) %}
        {% for k in baseline %}
          {% if k not in current_list and k != '' %}
            {% set ns2.missing = ns2.missing + [k] %}
          {% endif %}
        {% endfor %}
        {{ ns2.missing | join(',') }}
  - if:
      - condition: template
        value_template: "{{ missing_keys | length > 0 }}"
    then:
      - action: persistent_notification.create
        data:
          notification_id: rachio_zone_disabled
          title: Rachio zone or valve may be disabled
          message: >-
            Missing from Home Assistant since the last check:
            {{ missing_keys.replace(',', ', ') }}. A Rachio zone or the Back Yard valve may
            have been disabled in the Rachio app, or the integration dropped it for another
            reason. Verify in Settings > Devices & Services > Rachio, then in the Rachio app.
      - action: notify.notify
        continue_on_error: true
        data:
          title: Rachio zone or valve may be disabled
          message: "Missing: {{ missing_keys.replace(',', ', ') }}. Check the Rachio app."
  - action: input_text.set_value
    target:
      entity_id: input_text.rachio_known_zone_switches
    data:
      value: "{{ current_keys }}"
mode: single
```

Both device IDs are stable Home Assistant device registry IDs, not something Rachio assigns;
`1a3374a701b62fe0e05e7faae6e19b50` is the Main Irrigation `CasaSolar Rachio` controller,
`660935a36d62431b1438e2046b428c9f` is the Back Yard Smart Hose Timer.

The baseline is rewritten to the current set on every run, whether or not something was missing.
That makes this a one-shot notice per drop rather than a recurring nag: once fired, the next run
starts from the new, smaller baseline and stays quiet until something changes again. It also means
a legitimate addition, North's switch reappearing, is absorbed silently as growth, never treated
as a false alarm.

The standby-mode automation is simpler, a direct state trigger, since standby is a real entity
with a real `off`/`on` state rather than something that disappears:

```yaml
id: rachio_standby_engaged_alert
alias: Rachio standby mode engaged alert
triggers:
  - trigger: state
    entity_id: switch.main_irrigation_standby
    to: "on"
conditions: []
actions:
  - action: persistent_notification.create
    data:
      notification_id: rachio_standby_engaged
      title: Rachio irrigation standby mode is on
      message: >-
        The Main Irrigation controller entered standby mode, which pauses all scheduled zone
        watering. Confirm this was intentional; otherwise turn switch.main_irrigation_standby
        back off in Home Assistant or the Rachio app.
  - action: notify.notify
    continue_on_error: true
    data:
      title: Rachio irrigation standby mode is on
      message: "Main Irrigation standby mode is on, pausing all scheduled watering. Confirm intentional."
mode: single
```

It gets its own automation rather than folding into the zone-disabled one because it is a
different condition with a different mechanism (a state flip on an existing entity, not an entity
disappearing) and a different blast radius (every zone paused at once, not one zone gone).

## Design choices made while scoping this

- **Detection mechanism.** A Home Assistant `entity_registry_updated` event (`action: remove`)
  fires when the integration actually drops an entity and would detect a disabled zone with less
  latency than a 30-minute poll. It was set aside in favor of the baseline-diff approach above:
  that event also fires for reasons that are not a disabled zone (an integration reload, a
  reauth, a genuinely deleted rather than merely disabled zone), so trusting it alone risked
  false positives without a real test against each of those cases. The baseline diff has a
  30-minute detection latency in exchange for being unambiguous about what actually changed.
- **Scope.** Covers the Main Irrigation controller's zones, the separate Back Yard valve, and
  standby mode engaging, all three, on request. Back Yard is a single valve rather than a set of
  Rachio zones, so it is tracked the same way as a zone switch (present or absent in the entity
  registry) even though "disabled" is not quite the right word for what would make it disappear.
- **Built live, not just specced.** This repo is documentation only and nothing in it deploys
  automatically, but the automation itself lives on the Home Assistant instance, not in this
  repo, so building it directly via the REST API and documenting it here afterward, the same
  split already used for `fridge-failure-alert.md`, was in scope.
- **Delivery.** Both a persistent notification and `notify.notify`, matching the existing
  `fridge_failure_alert` convention (`fridge-failure-alert.md`), including
  `continue_on_error: true` on the push step so a notify failure can never block the persistent
  notification.

## Mobile push actually reaches a phone now

`fridge-failure-alert.md` recorded that `notify.notify` completed successfully but delivered to
nothing, because no companion app had been registered on this instance. That has since changed:
`notify.mobile_app_pete_iphone` now exists as a registered service. `notify.notify` fans out to
every registered platform, so both automations above should reach that phone. This was not
independently re-verified end to end (the trigger tests below check the trace for a step error,
which `continue_on_error` would suppress even on delivery failure); worth a real device check the
next time a live test runs.

## Trigger history

Neither automation has fired on a real condition yet. Both were tested by calling
`automation.trigger` directly, bypassing the real triggers, on 2026-08-08:

| When | Automation | What was simulated |
|---|---|---|
| 2026-08-08T16:03:21Z | `rachio_zone_or_valve_disabled_alert` | `input_text.rachio_known_zone_switches` was seeded with an extra `phantom_test_zone` key not present in the real current set, then the automation was triggered |
| 2026-08-08T16:04:04Z | `rachio_standby_mode_engaged_alert` | Direct trigger call; does not exercise the real `state` trigger condition, only the action sequence |

Both traces showed `script_execution: finished` with no per-step error. The first test's
resulting notification correctly named `phantom_test_zone` as the missing key and correctly
reset the baseline to the real current set afterward, with no manual cleanup needed. Both test
notifications were dismissed after confirming their content.

## Remaining gaps

- ~~North's re-enablement has not happened yet as of this writing.~~ Resolved 2026-08-08: pde
  fixed the leak and re-enabled North in the Rachio app. Home Assistant picked it up without a
  restart, creating `switch.main_irrigation_north` ("Main Irrigation North") as a new entity.
  `switch.main_irrigation_standby` stayed in place, unrenamed, still `off`. This confirms the
  hypothesis above: disabling a zone deletes its entity, re-enabling it creates a new one, and
  Standby was never a zone wearing a different name. The self-healing baseline absorbed the
  addition silently, as designed, no alert fired.

  North's switch also had to be added by hand to two places that predate this alert and don't
  read from Rachio directly: the Homie Dashboard's Irrigation control (`dist/config.js`, a static
  `subEntities` list) and the `sensor.homie_irrigation_status` template helper's `expand([...])`
  zone list. Both were built when North had no entity and don't rescan the entity registry, so
  neither one would ever have picked North back up on its own. Both were updated live and
  redeployed the same day; see the homie-dashboard fork's `docs/pdehlke-customizations.md` for
  the config.js side.
- The `entity_registry_updated` event, set aside above for reliability reasons, was never
  actually tested against a real zone disablement, so its rejection is reasoned from the docs
  and the event schema, not from an observed false positive on this instance. Worth revisiting
  if the 30-minute detection latency ever turns out to matter.
- No automation clears `rachio_standby_engaged` when standby turns back off, matching the same
  gap already recorded for `fridge_failure_alert`; `notification_id` means a repeat trigger
  overwrites rather than stacks, which is something, not a fix.
- Real end-to-end push delivery (a notification actually arriving on the phone, not just the
  trace showing no step error) has not been separately confirmed.

## Maintenance note: Homie's zone list is static, not a gap to fix

The North incident above is the general case, not a one-off: any time a Rachio zone is added or
permanently deleted (not just disabled and re-enabled), two places outside this alert's own
automations need a manual rebuild, because neither reads the Rachio integration's entity list at
runtime:

- The Homie Dashboard's Irrigation control (`dist/config.js`, the `subEntities` list).
- The `sensor.homie_irrigation_status` template helper's `expand([...])` zone list.

Making either of these dynamic (e.g. by having Homie or the template sensor enumerate zones via
`device_entities()`, the way the alert automations already do) was considered and rejected.
Zone additions or deletions are rare enough, maybe once every few years, that the cost of a
dynamic implementation isn't worth it against the cost of occasionally noticing a zone is missing
and updating two lists by hand. This is a standing decision, not an open TODO.

## Reproducing the measurements

```bash
U=http://homeassistant.local:8123
HB="Authorization: Bearer $HA_TOKEN"

# Current Rachio integration entities and their config-entry ownership
curl -s -H "$HB" "$U/api/config/config_entries/entry" | jq -r '.[] | select(.domain=="rachio")'

# Zone attributes (Zone number, Shade, Type, Slope confirm a real zone switch)
curl -s -H "$HB" "$U/api/states/switch.main_irrigation_east_of_garage" | jq .

# unique_id shapes, to tell a real zone switch from standby/rain_delay/schedule
python3 scripts/haws.py '{"type":"config/entity_registry/list"}' \
  | jq -r '.result[] | select(.platform=="rachio") | [.entity_id, .unique_id] | @tsv'
```

Read either automation's current configuration with:

```bash
curl -s -H "$HB" "$U/api/config/automation/config/rachio_zone_disabled_alert"
curl -s -H "$HB" "$U/api/config/automation/config/rachio_standby_engaged_alert"
```

Inspect a run with `trace/list` then `trace/get` over WebSocket, same as
`fridge-failure-alert.md`.
