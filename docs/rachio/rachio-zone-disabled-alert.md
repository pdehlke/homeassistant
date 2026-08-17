# Rachio zone disabled alert

Four automations. Three alert when a Rachio zone or valve disappears from Home Assistant, when
the Main Irrigation controller's whole-device standby mode turns on, or when the separate Back
Yard Smart Hose Timer goes offline or reports a low battery. The fourth reloads the Rachio config
entry hourly so the others ever have something new to detect.

| Object | Entity |
|---|---|
| Automation | `automation.rachio_zone_or_valve_disabled_alert` (id `rachio_zone_disabled_alert`) |
| Automation | `automation.rachio_standby_mode_engaged_alert` (id `rachio_standby_engaged_alert`) |
| Automation | `automation.rachio_periodic_config_entry_reload` (id `rachio_periodic_reload`) |
| Automation | `automation.rachio_back_yard_hose_timer_health_alert` (id `rachio_back_yard_health_alert`) |
| Helper | `input_text.rachio_known_zone_switches` (baseline, max length 255) |
| Helper | `input_boolean.rachio_zone_or_valve_disabled` (live current-state flag, not diff-based) |
| Helper (Template) | `binary_sensor.main_irrigation_rachio_zone_or_valve_disabled` (`device_class: problem`, mirrors the input_boolean for dashboard red-dot badges) |
| Source | Rachio integration switches on the Main Irrigation controller and the Back Yard Smart Hose Timer |

All four automations are live and enabled. The two Main Irrigation alert automations were verified
working on 2026-08-08 against Home Assistant 2026.7.4, first by calling `automation.trigger`
directly, then later the same day against a real North re-disable that also confirmed push
delivery. See Trigger history below for both. The periodic reload automation was added later the
same day. On 2026-08-10, a reload-driven false-positive race in `rachio_zone_disabled_alert` was
found and fixed, two new indicator entities were added, and the Back Yard automation was built and
verified against a real battery pull. See the dedicated sections below for all three.

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

Back Yard Smart Hose Timer (separate device, already known to be offline, see [project-todo.md](../project-todo.md)
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

Disabling a zone does not flip a flag Home Assistant can watch; it deletes the entity, or (see
below) marks it `unavailable` and strips its attributes until the next full removal. There is no
single state to key a trigger off of that unambiguously means "disabled." Detection has to be a
diff against a remembered set of entities that should exist.

`input_text.rachio_known_zone_switches` holds a comma-separated list of short keys, one per zone
or valve switch last seen present: the Main Irrigation prefix is stripped
(`east_of_garage`, not `switch.main_irrigation_east_of_garage`) to leave headroom under the
255-character state-string limit as more zones come back online. A "real zone" switch is
identified generically, by having a `Zone number` attribute, rather than by a hardcoded name list,
so North reappearing is picked up automatically without an edit here.

The YAML below is the live 2026-08-10 version, after the fixes described in "The reload race
condition, and the fix" and "Live current-state indicator, not just a diff" further down. The
`for: {seconds: 60}` on the state trigger, the split 30-minute fallback, `expected_keys`,
`currently_missing`, the input_boolean actions, and the restored `notify.notify` step are all new;
the `current_keys`/`missing_keys` diff logic itself is unchanged from when it was first built.

```yaml
id: rachio_zone_disabled_alert
alias: Rachio zone or valve disabled alert
triggers:
  - trigger: state
    entity_id:
      - switch.main_irrigation_east_of_garage
      - switch.main_irrigation_east_triangle
      - switch.main_irrigation_emmas_yard
      - switch.main_irrigation_south_of_driveway
      - switch.main_irrigation_north
      - switch.back_yard_irrigation
    for:
      seconds: 60
  - trigger: time_pattern
    minutes: 10
  - trigger: time_pattern
    minutes: 40
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
      expected_keys: "back_yard_irrigation,east_of_garage,east_triangle,emmas_yard,north,south_of_driveway"
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
  - variables:
      currently_missing: >-
        {% set current_list = current_keys.split(',') %}
        {% set exp = expected_keys.split(',') %}
        {% set ns3 = namespace(missing=[]) %}
        {% for k in exp %}
          {% if k not in current_list %}
            {% set ns3.missing = ns3.missing + [k] %}
          {% endif %}
        {% endfor %}
        {{ ns3.missing | join(',') }}
  - if:
      - condition: template
        value_template: "{{ currently_missing | length > 0 }}"
    then:
      - action: input_boolean.turn_on
        target:
          entity_id: input_boolean.rachio_zone_or_valve_disabled
    else:
      - action: input_boolean.turn_off
        target:
          entity_id: input_boolean.rachio_zone_or_valve_disabled
      - action: persistent_notification.dismiss
        continue_on_error: true
        data:
          notification_id: rachio_zone_disabled
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
            have been disabled in the Rachio app, disabled automatically by Rachio (e.g. leak
            detection), or the integration dropped it for another reason. Verify in
            Settings > Devices & Services > Rachio, then in the Rachio app.
      - action: notify.notify
        continue_on_error: true
        data:
          title: Rachio zone or valve may be disabled
          message: >-
            Missing from Home Assistant: {{ missing_keys.replace(',', ', ') }}. Verify in
            Settings > Devices & Services > Rachio, then in the Rachio app.
  - action: input_text.set_value
    target:
      entity_id: input_text.rachio_known_zone_switches
    data:
      value: "{{ current_keys }}"
mode: single
```

`time_pattern` rejects a comma-separated `minutes` value in one trigger (`"10,40"` fails config
validation with "invalid time_pattern value"); it wants a wildcard/`/N` pattern or exactly one fixed
value, hence two separate triggers for `:10` and `:40`.

Both device IDs are stable Home Assistant device registry IDs, not something Rachio assigns;
`1a3374a701b62fe0e05e7faae6e19b50` is the Main Irrigation `CasaSolar Rachio` controller,
`660935a36d62431b1438e2046b428c9f` is the Back Yard Smart Hose Timer.

The baseline is rewritten to the current set on every run, whether or not something was missing.
That makes this a one-shot notice per drop rather than a recurring nag: once fired, the next run
starts from the new, smaller baseline and stays quiet until something changes again. It also means
a legitimate addition, North's switch reappearing, is absorbed silently as growth, never treated
as a false alarm.

### The state trigger, added 2026-08-08

The automation originally ran on the 30-minute `time_pattern` and HA-start triggers alone, since
disabling a zone deletes the entity rather than flipping a state, so there was no single entity
worth putting a `state` trigger on. That was true, but incomplete: a `state` trigger doesn't need
to target the specific state transition that means "disabled", it only needs to fire the check
often enough to catch it, and any state change on a zone/valve switch, including it going
`unavailable`, is a fine reason to re-run the diff. Added a `state` trigger on the six known
zone/valve switches (any change, no `to:` filter) alongside the existing 30-minute fallback.

Two motivations, both from pde directly:

- **Speed.** Detection latency drops from up to 30 minutes to effectively immediate, since the
  Rachio integration reload that clears a disabled zone's attributes fires a state change on that
  entity the moment it happens.
- **Discoverability.** Home Assistant's "Related" card, under Settings > Devices & Services >
  Rachio > a specific device, lists automations by statically scanning their config for literal
  `entity_id`/`device_id` references in triggers, conditions, and actions. It does not evaluate
  Jinja templates, so an automation whose only entity/device references live inside
  `variables:` templates (as this one's `current_keys`/`missing_keys` computation does) was
  invisible there even though it worked correctly, confirmed against `switch.main_irrigation_north`
  and `switch.back_yard_irrigation`'s device pages via the WebSocket `search/related` command,
  the same one that card calls.

This reintroduces exactly the hardcoded zone list the `device_entities()`-based diff logic was
built to avoid, but only as a supplementary fast path: a zone that exists when this automation was
last edited but isn't in the trigger's `entity_id` list still gets caught, just on the next
30-minute tick rather than instantly, since the diff logic itself still walks every entity on both
devices at run time regardless of what triggered it. A newly added zone (as opposed to
enabled/disabled) needs a manual edit here either way, per the maintenance note below.

Every state change on these six entities re-runs the check, including a zone simply switching on
or off for a normal watering cycle. That's expected and harmless: `current_keys` is unaffected by
on/off, only by an entity's `Zone number` attribute disappearing (which happens when it goes
`unavailable`, not when it just turns off), so a scheduled run at 3 AM does not produce a false
positive. It does mean the automation's `last_triggered` timestamp updates far more often than
before; that's cosmetic.

This reasoning turned out to be incomplete in a way that took until 2026-08-10 to find. See "The
reload race condition, and the fix" below.

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
  false positives without a real test against each of those cases. The baseline diff originally
  had a 30-minute detection latency in exchange for being unambiguous about what actually changed;
  the state trigger added later (see above) closed most of that gap without changing the
  underlying diff logic.
- **Scope.** Covers the Main Irrigation controller's zones, the separate Back Yard valve, and
  standby mode engaging, all three, on request. Back Yard is a single valve rather than a set of
  Rachio zones, so it is tracked the same way as a zone switch (present or absent in the entity
  registry) even though "disabled" is not quite the right word for what would make it disappear.
- **Built live, not just specced.** This repo is documentation only and nothing in it deploys
  automatically, but the automation itself lives on the Home Assistant instance, not in this
  repo, so building it directly via the REST API and documenting it here afterward, the same
  split already used for [fridge-failure-alert.md](../device-alerts/fridge-failure-alert.md), was in scope.
- **Delivery.** Both automations originally sent both a persistent notification and `notify.notify`,
  matching the existing `fridge_failure_alert` convention ([fridge-failure-alert.md](../device-alerts/fridge-failure-alert.md)), including
  `continue_on_error: true` on the push step so a notify failure can never block the persistent
  notification. The zone-disabled alert's `notify.notify` step was removed on 2026-08-08, the same
  day the state trigger was added, at pde's request: with `time_pattern` alone, a push could only
  ever mean a real drop, but the new state trigger fires on every zone on/off cycle including the
  Even Days schedule's roughly 3 AM run, and pde wanted to see the wider trigger set behave for a
  while, local-notification-only, before trusting it not to page his phone overnight. The diff
  logic itself does not distinguish on/off from disabled, so in practice a false page from the 3 AM
  schedule was never actually expected, but this was pde's call to make, not an engineering
  necessity. The standby-mode automation's `notify.notify` step is untouched; standby is a real,
  low-frequency state flip, not a per-cycle trigger. Restored 2026-08-10 once "The reload race
  condition, and the fix" identified and closed the actual source of false pages.

## Mobile push actually reaches a phone now

[fridge-failure-alert.md](../device-alerts/fridge-failure-alert.md) recorded that `notify.notify` completed successfully but delivered to
nothing, because no companion app had been registered on this instance. That has since changed:
`notify.mobile_app_pete_iphone` now exists as a registered service. `notify.notify` fans out to
every registered platform. Confirmed end to end on 2026-08-08 during the real North re-disable
test below: pde received the push on his phone in addition to the persistent notification, while
the zone-disabled alert still had its `notify.notify` step (removed later that day; see Design
choices above). The standby-mode automation's push step is unchanged and unverified against a real
device, only against a manual trigger call whose trace showed no step error.

## Trigger history

| When | Automation | What happened |
|---|---|---|
| 2026-08-08T16:03:21Z | `rachio_zone_or_valve_disabled_alert` | Synthetic test: `input_text.rachio_known_zone_switches` was seeded with an extra `phantom_test_zone` key not present in the real current set, then the automation was triggered directly via `automation.trigger`, bypassing the real triggers |
| 2026-08-08T16:04:04Z | `rachio_standby_mode_engaged_alert` | Direct `automation.trigger` call; does not exercise the real `state` trigger condition, only the action sequence |
| 2026-08-08T20:09:44Z | `rachio_zone_or_valve_disabled_alert` | Real test against a real condition: pde disabled North in the Rachio app a second time. HA still showed `switch.main_irrigation_north` as stale `off` at the next scheduled 20:00:00Z run (Rachio's integration hadn't polled the change yet, so nothing was actually missing and correctly no alert fired). Forced a Rachio config-entry reload, which flipped the entity to `unavailable` and dropped its `Zone number` attribute. Then triggered the automation (still only via `automation.trigger` at this point; the state trigger didn't exist yet) and confirmed a clean run: `missing_keys` computed to `north`, the persistent notification and `notify.notify` both fired with no trace error, and pde confirmed the push actually reached his phone |
| 2026-08-10T19:01:03Z | `rachio_zone_or_valve_disabled_alert` | Post-fix verification: forced a real `homeassistant.reload_config_entry` on the Rachio entry. Before the fix this reliably produced a burst of 5-6 runs within milliseconds with intermittent non-empty `missing_keys`; after the fix the automation did not run until ~60s after the last entity settled, ran once per entity, and every run computed `missing_keys: ''` and `currently_missing: ''`. `input_boolean.rachio_zone_or_valve_disabled`'s history for the whole window showed zero transitions |
| 2026-08-10T19:26:11.713Z | `rachio_back_yard_health_alert` | Real test: pde physically removed the Back Yard Smart Hose Timer's batteries at pde's own offer. `switch.back_yard_irrigation` went `unavailable` at 19:25:11.687Z; the `offline` branch fired exactly 60.0s later, created `persistent_notification.rachio_back_yard_offline`, and called `notify.notify` with no trace error. pde confirmed the push reached his phone and the correct red-dot indicators appeared on all three Homie Overview dashboards |
| 2026-08-10T19:31:11.6Z | `rachio_back_yard_health_alert` | Same test, recovery half: pde replaced the batteries. `battery_ok` and `back_online` both fired within milliseconds of each other (no debounce on recovery), correctly dismissing `rachio_back_yard_battery_low` (a harmless no-op, that notification never existed) and `rachio_back_yard_offline` (confirmed actually gone via `persistent_notification/get`, not just attempted) |

The first two rows were synthetic dry runs of the action sequence. The third is the first time
either automation's actual detection logic (not just its actions) ran against a real Rachio
change, and the first confirmed real end-to-end push delivery. The state trigger added afterward
(see above) has not yet fired on an organic zone state change; the entity list is the same
mechanism already exercised here, so this is considered covered rather than untested. The last
three rows are all 2026-08-10, covering the reload-race fix and the new Back Yard automation end to
end, both directions.

## Investigation: does anything besides a forced reload ever surface a real disable? (2026-08-08)

After the state trigger above was added, pde disabled North a second time and reported something
worth revisiting: on the Rachio integration's device page, North didn't disappear from the
Controls list, it showed up greyed out with a generic raindrop avatar in place of its zone photo.
That observation matches `unavailable`/`restored: true` exactly, the same state the diff logic
already keys off (see How it works). The deeper question was whether anything besides the manual
config-entry reload used to test this earlier ever produces that state on its own.

It does not. Investigated directly against this instance and against the Rachio integration's
source pinned to the running version, [`home-assistant/core` tag
`2026.7.4`](https://github.com/home-assistant/core/tree/2026.7.4/homeassistant/components/rachio):

- Zone entities (`RachioZone` in
  [`switch.py`](https://github.com/home-assistant/core/blob/2026.7.4/homeassistant/components/rachio/switch.py))
  are plain, non-polling entities (`_attr_should_poll = False`, not a `CoordinatorEntity`; see
  [`entity.py`](https://github.com/home-assistant/core/blob/2026.7.4/homeassistant/components/rachio/entity.py)).
  There is no periodic refresh for a Main Irrigation zone at all.
- The zone list, including each zone's `enabled` flag, is fetched exactly once, synchronously, in
  [`RachioPerson._setup()`](https://github.com/home-assistant/core/blob/2026.7.4/homeassistant/components/rachio/device.py#L136-L156),
  called only from `async_setup_entry` — HA start, first integration add, or a config-entry reload.
  `list_zones()` defaults to excluding disabled zones
  ([`device.py:314-321`](https://github.com/home-assistant/core/blob/2026.7.4/homeassistant/components/rachio/device.py#L314-L321)),
  so a zone disabled at that one snapshot moment simply isn't (re-)created; the entity that already
  exists for it from before is neither removed nor flagged.
- After creation, a zone's state is driven only by an incoming webhook event
  ([`switch.py:448-464`](https://github.com/home-assistant/core/blob/2026.7.4/homeassistant/components/rachio/switch.py#L448-L464),
  dispatched only for `ZONE_STARTED`/`STOPPED`/`COMPLETED`/`PAUSED`), and this instance's webhook is
  unreachable (no `external_url`; already established in [project-todo.md](../project-todo.md)'s Overview A irrigation
  item). Even a reachable webhook would not help here: Rachio's webhook categories include a
  separate `DELTA` type for exactly this kind of configuration change
  ([rachio.readme.io/reference/webhooks](https://rachio.readme.io/reference/webhooks)), and HA's
  integration never subscribes to it
  ([`webhooks.py`](https://github.com/home-assistant/core/blob/2026.7.4/homeassistant/components/rachio/webhooks.py)
  lists only `DEVICE_STATUS_EVENT, ZONE_STATUS_EVENT, RAIN_DELAY_EVENT,
  RAIN_SENSOR_DETECTION_EVENT, SCHEDULE_STATUS_EVENT`).
- A zone's `available` property is never overridden, so its `enabled` flag plays no role in HA's
  availability computation either.

Confirmed empirically on this instance too: `switch.main_irrigation_north`'s history shows no
write at all between the second disable and the forced reload. A comparison entity that stayed
enabled the whole time, `switch.main_irrigation_east_of_garage`, went over two full days
(2026-08-06 to 2026-08-08) without a single state write before today's forced reload touched it.
Nothing polls these entities, disabled or not.

The Back Yard Smart Hose Timer is a partial exception: it genuinely is coordinator-based
([`RachioUpdateCoordinator`](https://github.com/home-assistant/core/blob/2026.7.4/homeassistant/components/rachio/coordinator.py#L32-L72),
polling every `base_count + 1` minutes, 2 minutes here), and its `available` property does check
live connectivity. But valve entity creation/removal is still the same one-time snapshot as zones,
so a valve permanently disappearing from the account would still need a reload to be reflected in
whether the entity exists at all; only its connectivity readout is genuinely live.

**What this means for the alert as built.** The diff logic itself needs no change; it was
re-confirmed correct on the same real North test (see Trigger history below). But without
something forcing a Rachio config-entry reload, `missing_keys` will never actually go non-empty
from a real-world disable — the 30-minute `time_pattern` fallback and the state trigger added
above both check the same stale, un-refreshed data between reloads, neither is a source of new
information by itself. This is a real gap in the mechanism, and it is not fixable from inside this
automation.

**Recommendation, not yet acted on.** Add a `time_pattern`-triggered
`homeassistant.reload_config_entry` call for the Rachio config entry (`01KZCBXSB0RM5JM99NAJ1V4J19`),
e.g. every 15-30 minutes, ahead of this alert's own checks. A reload costs roughly 8-12 Rachio API
calls; against Rachio's documented 3,500/day cap
([rachio.readme.io/reference/rate-limiting](https://rachio.readme.io/reference/rate-limiting)), a
15-minute cadence (96/day) leaves comfortable headroom, while something closer to every 1-2 minutes
would not, and isn't warranted for an event this rare. The tradeoff: a reload briefly flashes every
Rachio entity through `unavailable` (observed here as a ~2-second gap even on a healthy zone), which
would become a small, regular blip across every Rachio entity in Home Assistant, not just the ones
this alert watches, worth weighing against anything else that might key off Rachio entity state
changes before wiring one up.

**Correction to the state-trigger reasoning above.** The state trigger was added partly so a normal
watering cycle (specifically the roughly 3 AM Even Days schedule) would exercise the check
organically. Per the findings here, that will not happen: a Rachio-app-driven schedule run doesn't
touch Home Assistant at all without the unreachable webhook, so it can neither cause a false alert
nor provide real coverage. The push-removal decision made alongside the state trigger (see Design
choices) was made to guard against exactly that 3 AM scenario; the guard itself is harmless to
keep, but the scenario it guards against turns out not to be reachable on this instance as
currently configured.

## The periodic reload automation, added 2026-08-08

The investigation above concluded that nothing on this instance ever surfaces a real zone disable
without a forced Rachio config-entry reload, and recommended a `homeassistant.reload_config_entry`
automation on a 15-30 minute cadence. pde decided on an hourly cadence instead, explicitly trading
detection latency for fewer reload-triggered `unavailable` blips across every Rachio entity, on the
grounds that a webhook fix (making this instance internet-reachable, see [project-todo.md](../project-todo.md) item 3)
might make the whole reload workaround moot within the week; if that happens this automation can
likely be deleted rather than tuned.

```yaml
id: rachio_periodic_reload
alias: Rachio periodic config entry reload
description: >-
  Forces a reload of the Rachio integration every hour so zone-disable and other config-only
  changes actually get picked up. See rachio-zone-disabled-alert.md.
triggers:
  - trigger: time_pattern
    hours: "/1"
conditions: []
actions:
  - action: homeassistant.reload_config_entry
    data:
      entry_id: 01KZCBXSB0RM5JM99NAJ1V4J19
mode: single
```

`entry_id` is a fixed value, not a template; it will need updating by hand if the Rachio
integration is ever removed and re-added (a new entry gets a new ID). The service accepts
`entry_id` as a `data` field, not under `target`, despite the config entry selector; posting it
under `target` fails config validation with "extra keys not allowed."

Verified end to end the same day it was created: triggered directly via `automation.trigger`, trace
showed a clean `finished` run with no error, and `switch.main_irrigation_east_of_garage`'s
`last_changed` timestamp moved to within two seconds of the trigger, confirming the entity actually
flashed through the reload rather than the service call being a no-op.

An hourly reload costs roughly 8-12 Rachio API calls, well under the documented 3,500/day cap
([rachio.readme.io/reference/rate-limiting](https://rachio.readme.io/reference/rate-limiting)).

This closes the gap the investigation above found: both the zone-disabled alert's state trigger
and its 30-minute fallback now have a real source of new information to react to, at worst one hour
stale.

## The reload race condition, and the fix (2026-08-10)

Found while scoping an unrelated question, whether to fork Home Assistant's `rachio` integration to
add support for Rachio's `DELTA` webhook category (see [rachio-webhook-responsiveness-plan.md](./rachio-webhook-responsiveness-plan.md)).
pde reported being annoyed by frequent false-positive disabled-zone alerts, which turned out to
have nothing to do with webhooks and everything to do with the periodic reload automation directly
above.

**The mechanism.** Every hourly reload tears down and rebuilds every Rachio entity, not just the
one this alert cares about. Entities do not all flip from `unavailable` back to their real state at
the same instant; they repopulate one at a time over several seconds as the integration re-fetches
each zone. The zone-disabled alert's state trigger fires on *any* state change on the six watched
entities, including the transient `unavailable` blip a reload causes, and its baseline
(`input_text.rachio_known_zone_switches`) gets rewritten to whatever `current_keys` computes to on
*every single run*, including ones that fire mid-reload before every entity has repopulated.

Pulled `input_text.rachio_known_zone_switches`'s history for 2026-08-10 to confirm this rather than
inferring it. Every hour, at the top of the hour, the baseline visibly collapses from 6 keys to 1
across five sequential automation runs within about 40-50 milliseconds, then climbs back to 6 over
the following several seconds as zones repopulate:

| Reload (UTC) | First drop to last drop | Full recovery | Elapsed |
|---|---|---|---|
| 00:00 | :00.283 → :00.354 | :00:16.512 | ~16.2s |
| 03:00 | :00.300 → :00.346 | :00:23.289 | ~23.0s (worst observed) |
| 10:00 | :00.400 → :00.437 | :00:07.565 | ~7.2s |
| 18:00 | :00.404 → :00.447 | :00:07.796 | ~7.4s |

(Full hour-by-hour data covers every reload from 00:00 through 18:00 that day; these four rows
span the observed range, 7 to 23 seconds.)

Because the automation reads its baseline, computes the diff, and overwrites the baseline in the
same run, the *first* run of every hourly collapse compares a shrunken `current_keys` (whatever has
repopulated so far, which can be as low as the trigger's own entity) against the still-full
baseline from the end of the *previous* hour's recovery. That comparison is guaranteed to show
something missing. This is not a rare timing coincidence, it is baked into the automation's own
architecture and fires on every single hourly reload, 24 times a day. Separately, the 30-minute
`time_pattern` fallback was scheduled at `:00`/`:30`, so its own tick at `:00` lands exactly inside
the same collapse window.

Recorder history for `persistent_notification.rachio_zone_disabled` itself came back empty for the
full 2026-08-07 through 2026-08-10 window, which is inconclusive rather than exculpatory:
`persistent_notification` entities are not tracked by the recorder or queryable via
`/api/states/<id>` at all (confirmed directly later the same day, see "Reproducing the
measurements" below), so an empty history proves nothing either way. The mechanism above is
confirmed from real production data; whether it actually reached pde's phone every time versus only
some of the time, given the messy multi-entity mixing described next, was not independently
confirmed.

A second, subtler effect: because a genuinely disabled zone and a transiently-flickering healthy
zone look identical mid-reload (both momentarily missing their `Zone number` attribute), a real
disable landing on the same reload as this race would get reported correctly but *mixed in* with
one or more spurious zone names in the same notification. That is arguably worse than a purely fake
alert, since it teaches you to distrust a notification that is sometimes right.

**The fix.** Two changes to `rachio_zone_or_valve_disabled_alert`'s triggers, no change to the
diff logic itself:

- The six-entity state trigger now requires 60 continuous seconds in the new state before firing
  (`for: {seconds: 60}`), comfortably above the worst observed 23-second settle time. A transient
  reload blip never holds `unavailable` for 60 seconds, since it always resolves back to a normal
  state within observed range; a real disable holds it indefinitely, since nothing repopulates it
  until the zone is re-enabled and reloaded. The same debounce that filters out reload noise
  therefore does not filter out real disables, it just adds up to 60 seconds of latency to
  detecting them, negligible against the existing up-to-one-hour reload cadence.
- The 30-minute fallback moved from `:00`/`:30` to fixed `10` and `40` minutes past the hour
  (two separate `time_pattern` triggers; a single trigger with `minutes: "10,40"` is rejected by
  HA's schema, `time_pattern` wants either a wildcard/`/N` pattern or one fixed value per trigger),
  clear of the reload's collapse window with a comfortable margin.

Verified against a real reload, not just deployed: forced `homeassistant.reload_config_entry` on
the Rachio entry and watched the trace. Before the fix, this reliably produced a burst of 5-6 runs
within milliseconds, several with non-empty `missing_keys`. After the fix: the automation did not
run at all until roughly 60 seconds after the last entity settled, ran once per entity, and every
run computed `missing_keys: ''`. `input_boolean.rachio_zone_or_valve_disabled`'s history for the
whole window shows zero transitions, no flicker at all.

**Independent of this fix:** the periodic reload's own hourly cadence was not changed. The original
plan in [rachio-webhook-responsiveness-plan.md](./rachio-webhook-responsiveness-plan.md) to tighten it to 15 minutes was motivated partly by
a hope that more frequent reloads plus the (then-undiagnosed) false-positive risk would balance out;
that plan is now stale on that point. The debounce above absorbs a reload's blip regardless of how
often reloads happen, so tightening the cadence is now a pure detection-latency lever (worst case
one hour down to worst case 15 minutes), fully decoupled from false positives. Still not done, still
pde's call, no longer entangled with the false-positive problem either way.

The `notify.notify` push step, removed 2026-08-08 pending observation of the state trigger, was
restored the same day as this fix, now that the actual cause of false pages is understood and
addressed rather than merely avoided. See "Remaining gaps" below.

## Live current-state indicator, not just a diff (2026-08-10)

The diff logic above answers "did something change since the last check," which is the right
question for a one-shot notification but the wrong one for a persistent "is anything disabled right
now" indicator: because the baseline gets overwritten to `current_keys` on every run regardless of
outcome, a real disable is absorbed into the new "normal" after exactly one cycle. `missing_keys`
reverts to empty on the very next run even though the zone is still gone, since the baseline no
longer expects it either. Confirmed this is architectural, not a bug: the diff was never meant to
answer that question.

pde asked for exactly that indicator, an HA-notification on disable (already covered above) plus a
red-dot dashboard badge that reflects current state, including a zone Rachio disables on its own
(leak detection trips a zone off without pde touching the app; the diff logic already can't tell
that apart from a manual disable and neither can this, by design, since both surface identically as
a zone's `Zone number` attribute disappearing).

The fix adds a second, independent comparison in the same already-debounced automation run: a
fixed, hardcoded roster of the six zone/valve keys that should exist when everything is enabled
(`expected_keys`), diffed against the live `current_keys` computed the same way as before. Unlike
`missing_keys`, this has no memory and no self-healing: it is simply "is the full roster present
right now," recomputed fresh every run. That drives `input_boolean.rachio_zone_or_valve_disabled`
on when something is absent and off when everything is back, and now also dismisses
`persistent_notification.rachio_zone_disabled` on the same transition back to normal, which nothing
previously did.

`binary_sensor.main_irrigation_rachio_zone_or_valve_disabled` is a Template helper
(`device_class: problem`) that just mirrors the input_boolean's state. `problem`-class binary
sensors render as a red indicator automatically wherever Home Assistant shows them as a badge, no
dashboard-specific styling needed. Created via the Template integration's config flow
(`POST /api/config/config_entries/flow`, handler `template`, `next_step_id: binary_sensor`) rather
than YAML, and attached to the Main Irrigation device (`1a3374a701b62fe0e05e7faae6e19b50`) for
grouping; it covers Back Yard too even though it's attached to the other device, this is cosmetic
only.

Both new entities were added as storage-backed helpers rather than YAML, `input_boolean.create` over
the WebSocket API for the input_boolean (HA's input_* helpers have no
`/api/config/<domain>/config/<id>` REST surface the way automations do, confirmed by a 404; the
`GET /api/config/config_entries/entry` / storage-collection WebSocket commands are the only way to
manage them).

Verified live against a real North-style condition is not what happened here (North was already
back before this work); instead verified against the real Back Yard offline test below, whose
`switch.back_yard_irrigation` participates in the same Main Irrigation `current_keys` computation
via its own automation. The Main Irrigation-specific indicator's red-dot path itself was confirmed
by pde directly on all three Homie Overview dashboards during that same test window, since Homie's
existing irrigation status plumbing already surfaces `switch.back_yard_irrigation`'s availability;
building a dedicated Homie badge wired to the new entities was not needed and was not done.

## Back Yard Hose Timer health alert (2026-08-10)

The Back Yard Smart Hose Timer is a battery-operated valve, not a zone on the hard-wired Main
Irrigation controller, and pde considers a dead battery a completely different condition from a
zone being disabled in the Rachio app. It shares the same Rachio config entry as Main Irrigation
(confirmed: its entities update within seconds of the same `homeassistant.reload_config_entry` call
that reloads everything else), so it is exposed to the identical reload-blip risk addressed above,
but it also has something Main Irrigation's zones don't: a real, Rachio-provided low-battery signal,
`binary_sensor.back_yard_irrigation_battery` (`device_class: battery`, `on` means low), not
something inferred from connectivity.

New automation, `rachio_back_yard_health_alert`, watches two genuinely different conditions with
two different mechanisms:

- **Battery low**: direct trigger on `binary_sensor.back_yard_irrigation_battery` going `on`, no
  debounce. It's a computed value Rachio's cloud already decided, not raw connectivity, so there is
  no reload-blip risk to filter out.
- **Offline**: `switch.back_yard_irrigation` going `unavailable` and staying there for 60 continuous
  seconds, same debounce duration and same rationale as the Main Irrigation fix above.

Each condition also has a recovery branch (`battery_ok` on the sensor going back to `off`,
`back_online` on the switch leaving `unavailable`, no debounce on either since recovery doesn't
need protecting from a reload blip the same way), which dismisses the matching notification.
`mode: queued` rather than `single`, so a battery recovery and a connectivity recovery arriving
close together both get to run rather than one dropping the other.

```yaml
id: rachio_back_yard_health_alert
alias: Rachio Back Yard Hose Timer health alert
triggers:
  - trigger: state
    entity_id: binary_sensor.back_yard_irrigation_battery
    to: "on"
    id: battery_low
  - trigger: state
    entity_id: binary_sensor.back_yard_irrigation_battery
    to: "off"
    id: battery_ok
  - trigger: state
    entity_id: switch.back_yard_irrigation
    to: "unavailable"
    for:
      seconds: 60
    id: offline
  - trigger: state
    entity_id: switch.back_yard_irrigation
    from: "unavailable"
    id: back_online
conditions: []
actions:
  - choose:
      - conditions:
          - condition: trigger
            id: battery_low
        sequence:
          - action: persistent_notification.create
            data:
              notification_id: rachio_back_yard_battery_low
              title: Back Yard Hose Timer battery low
              message: >-
                The Back Yard Smart Hose Timer is reporting low battery. Replace soon; once the
                battery fully dies the device also drops offline, which triggers a separate alert.
          - action: notify.notify
            continue_on_error: true
            data:
              title: Back Yard Hose Timer battery low
              message: "Back Yard Hose Timer battery is low. Replace soon."
      - conditions:
          - condition: trigger
            id: battery_ok
        sequence:
          - action: persistent_notification.dismiss
            continue_on_error: true
            data:
              notification_id: rachio_back_yard_battery_low
      - conditions:
          - condition: trigger
            id: offline
        sequence:
          - action: persistent_notification.create
            data:
              notification_id: rachio_back_yard_offline
              title: Back Yard Hose Timer offline
              message: >-
                The Back Yard Smart Hose Timer has been unreachable for over a minute. Likely a
                dead battery or a connectivity issue; check the device and the Rachio app.
          - action: notify.notify
            continue_on_error: true
            data:
              title: Back Yard Hose Timer offline
              message: "Back Yard Hose Timer is offline. Check batteries/connectivity."
      - conditions:
          - condition: trigger
            id: back_online
        sequence:
          - action: persistent_notification.dismiss
            continue_on_error: true
            data:
              notification_id: rachio_back_yard_offline
mode: queued
max: 10
```

**Verified against a real battery pull**, not a synthetic trigger, at pde's offer. Before-state
captured first: all three Back Yard entities healthy (`off`), no existing notifications, automation
armed. Timeline, from Home Assistant's own event-driven trace timestamps (a polling watch script
used to observe this live lagged by tens of seconds due to its own 5-second poll interval and is
not the source of truth here):

| Time (UTC) | Event |
|---|---|
| 19:25:11.687 | `switch.back_yard_irrigation` (and both binary sensors) genuinely go `unavailable`, batteries physically removed |
| 19:26:11.713 | Automation fires, `offline` branch, exactly 60.0 seconds later |
| 19:26:11.715 | `persistent_notification.rachio_back_yard_offline` created |
| (same run) | `notify.notify` called, no error in trace; push confirmed received on phone, correct red-dot indicators confirmed on all three Homie Overviews |
| 19:31:11.608 | Batteries replaced; `binary_sensor.back_yard_irrigation_battery` leaves `unavailable` for `off`, `battery_ok` branch fires, dismisses `rachio_back_yard_battery_low` (a harmless no-op, that notification never existed since battery never actually went low) |
| 19:31:11.613 | `switch.back_yard_irrigation` leaves `unavailable`, `back_online` branch fires, dismisses `rachio_back_yard_offline` |

Confirmed the dismiss was real, not just attempted without error, via `persistent_notification/get`
returning an empty list afterward (see "Reproducing the measurements" below for why `/api/states`
cannot be used for this).

The battery-low branch itself remains unverified. It cannot be tested synthetically: pulling
batteries outright skips straight to the offline condition rather than exercising Rachio's gradual
low-battery reporting, which only happens for real as a battery genuinely runs down over time. That
one only proves itself whenever it actually happens.

**A known, accepted limitation this does not fix**: `current_keys` in the Main Irrigation diff
logic above includes `back_yard_irrigation` unconditionally, by registry presence only, with no
availability check (see "How it works"). That means the *diff-based* alert can never detect Back
Yard going missing, only the *new* health alert can, via `switch.back_yard_irrigation`'s live
availability rather than registry diffing. This was already true before 2026-08-10; not introduced
by this work, and now that the health alert exists to actually cover Back Yard's real failure mode
(dead battery, connectivity), fixing the diff logic's blind spot for the same device is lower
priority than it looked before this alert existed.

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
  and the event schema, not from an observed false positive on this instance. Worth another look
  now that the periodic reload automation (below) makes registry changes happen on a predictable
  hourly cadence instead of only at ad hoc manual reloads, but not revisited yet. Lower priority
  after 2026-08-10: the state-trigger-plus-debounce fix (see "The reload race condition, and the
  fix") solved the reliability problem this event was originally being considered to solve,
  without needing a different trigger source at all.
- No automation clears `rachio_standby_engaged` when standby turns back off, matching the same
  gap already recorded for `fridge_failure_alert`; `notification_id` means a repeat trigger
  overwrites rather than stacks, which is something, not a fix.
- ~~The zone-disabled alert's `notify.notify` step is currently removed~~ Resolved 2026-08-10:
  restored as part of "The reload race condition, and the fix" above. The removal on 2026-08-08
  was pde watching the new state trigger before trusting it not to page overnight; the actual
  cause of false pages (the reload race, not the 3 AM schedule this was originally guarding
  against, which per the investigation above was never actually reachable) is now understood and
  fixed, not just avoided.
- ~~**The open decision**: whether to add a periodic `homeassistant.reload_config_entry`
  automation for the Rachio entry~~ Resolved 2026-08-08: built, hourly. See "The periodic reload
  automation" above.

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
U=http://hass.ehlke.net:8123
HB="Authorization: Bearer $HA_TOKEN"

# Current Rachio integration entities and their config-entry ownership
curl -s -H "$HB" "$U/api/config/config_entries/entry" | jq -r '.[] | select(.domain=="rachio")'

# Zone attributes (Zone number, Shade, Type, Slope confirm a real zone switch)
curl -s -H "$HB" "$U/api/states/switch.main_irrigation_east_of_garage" | jq .

# unique_id shapes, to tell a real zone switch from standby/rain_delay/schedule
python3 scripts/haws.py '{"type":"config/entity_registry/list"}' \
  | jq -r '.result[] | select(.platform=="rachio") | [.entity_id, .unique_id] | @tsv'
```

Read any of the automations' current configuration with:

```bash
curl -s -H "$HB" "$U/api/config/automation/config/rachio_zone_disabled_alert"
curl -s -H "$HB" "$U/api/config/automation/config/rachio_standby_engaged_alert"
curl -s -H "$HB" "$U/api/config/automation/config/rachio_back_yard_health_alert"
```

Inspect a run with `trace/list` then `trace/get` over WebSocket, same as
[fridge-failure-alert.md](../device-alerts/fridge-failure-alert.md).

**`persistent_notification.<id>` is not queryable via `/api/states/<id>`,** confirmed directly
2026-08-10: `GET /api/states/persistent_notification.rachio_back_yard_offline` returned "Entity
not found" even immediately after a trace confirmed `persistent_notification.create` had run
successfully with matching parameters and no error. The full `/api/states` list has no
`persistent_notification.*` entries at all. Use the WebSocket command instead, which does show it:

```bash
python3 scripts/haws.py '{"type":"persistent_notification/get"}'
```

To reproduce the reload-race baseline-collapse data itself, pull `input_text.rachio_known_zone_switches`'s
history across a window spanning several hourly reloads and watch the key count at each timestamp:

```bash
curl -s -H "$HB" \
  "$U/api/history/period/2026-08-10T00:00:00Z?filter_entity_id=input_text.rachio_known_zone_switches&end_time=2026-08-10T23:59:59Z&minimal_response" \
  | jq -r '.[0][] | [.last_changed, .state] | @tsv'
```
