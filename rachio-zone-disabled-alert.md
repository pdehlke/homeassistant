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
2026.7.4, first by calling `automation.trigger` directly, then later the same day against a real
North re-disable that also confirmed push delivery. See Trigger history below for both.

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
  split already used for `fridge-failure-alert.md`, was in scope.
- **Delivery.** Both automations originally sent both a persistent notification and `notify.notify`,
  matching the existing `fridge_failure_alert` convention (`fridge-failure-alert.md`), including
  `continue_on_error: true` on the push step so a notify failure can never block the persistent
  notification. The zone-disabled alert's `notify.notify` step was removed on 2026-08-08, the same
  day the state trigger was added, at pde's request: with `time_pattern` alone, a push could only
  ever mean a real drop, but the new state trigger fires on every zone on/off cycle including the
  Even Days schedule's roughly 3 AM run, and pde wanted to see the wider trigger set behave for a
  while, local-notification-only, before trusting it not to page his phone overnight. The diff
  logic itself does not distinguish on/off from disabled, so in practice a false page from the 3 AM
  schedule was never actually expected, but this was pde's call to make, not an engineering
  necessity. The standby-mode automation's `notify.notify` step is untouched; standby is a real,
  low-frequency state flip, not a per-cycle trigger. Re-adding the zone-disabled alert's push step
  is a matter of adding back the same `notify.notify` action block shown above.

## Mobile push actually reaches a phone now

`fridge-failure-alert.md` recorded that `notify.notify` completed successfully but delivered to
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

The first two rows were synthetic dry runs of the action sequence. The third is the first time
either automation's actual detection logic (not just its actions) ran against a real Rachio
change, and the first confirmed real end-to-end push delivery. The state trigger added afterward
(see above) has not yet fired on an organic zone state change; the entity list is the same
mechanism already exercised here, so this is considered covered rather than untested.

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
  unreachable (no `external_url`; already established in `project-todo.md`'s Overview A irrigation
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
  and the event schema, not from an observed false positive on this instance. Moot either way
  unless something forces periodic reloads (see the investigation above): that event fires on
  entity registry changes, which on this instance currently only happen at a reload too.
- No automation clears `rachio_standby_engaged` when standby turns back off, matching the same
  gap already recorded for `fridge_failure_alert`; `notification_id` means a repeat trigger
  overwrites rather than stacks, which is something, not a fix.
- The zone-disabled alert's `notify.notify` step is currently removed (see Design choices above).
  pde wants to watch the new state trigger behave for a while, quietly, before deciding whether to
  add push back. Revisit this; it was explicitly framed as "for now." The specific scenario it
  was guarding against (a false page from the 3 AM schedule) turns out not to be reachable on this
  instance at all, per the investigation above, so this is now purely pde's preference, not a
  precaution against an active risk.
- **The open decision**: whether to add a periodic `homeassistant.reload_config_entry` automation
  for the Rachio entry, without which neither the state trigger nor the 30-minute fallback ever
  sees a real disable. See the investigation above for the recommended interval and its tradeoff.
  Not yet built; needs a decision, not just an edit.

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
