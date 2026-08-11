# Rachio webhook responsiveness: revisit limitations now that home.ehlke.net exists

## Context

Every prior Rachio decision in this repo (`rachio-zone-disabled-alert.md`,
`project-todo.md` item 4) was made under one hard constraint: this Home
Assistant instance had no `external_url` and was not reachable from the
internet, so Rachio's cloud could never deliver the webhook its integration
depends on for zone state. That constraint is now gone: Home Assistant Cloud
(Nabu Casa) is connected (`remote_connected: true`, certificate issued,
confirmed in `nabucasa-remote-ui-dns-fragility.md`) and the instance is
reachable at `https://home.ehlke.net`. This is not the same problem as the Homie
dashboard's `WS_URL` misconfiguration; that is explicitly out of scope and
untouched here.

This plan revisits the two Rachio limitations that were previously written off
as permanent, and lays out what's now achievable in `homie-dashboard`:

1. **Zone on/off state staleness** (`project-todo.md` item 4): caused directly
   by the unreachable webhook. Should now resolve itself once confirmed live,
   since `homie-dashboard`'s WebSocket pipeline already reflects HA state
   changes within milliseconds; no dashboard code changes are needed for this
   half.
2. **Disabled-zone detection latency/hackiness**
   (`rachio-zone-disabled-alert.md`): investigated at the source level and found
   to be **independent of the webhook problem**. HA's Rachio integration
   (`webhooks.py` in `home-assistant/core`) never subscribes to Rachio's `DELTA`
   webhook category, the one that would report a zone being disabled/enabled. It
   only listens for `ZONE_STARTED/STOPPED/COMPLETED/PAUSED`. So a live webhook
   fixes (1) but does nothing for (2). The existing hourly forced-reload
   automation is not a stopgap that the webhook fix retires, it is the only
   mechanism that will ever exist unless something changes specifically on the
   detection side.

pde has not decided whether to keep the Nabu Casa Cloud subscription long-term,
so nothing here should assume the webhook is permanent. Rollback posture
(confirmed): don't build a separate teardown checklist for cancelling Cloud,
that's pde's own call to make later. Instead, everything built here must degrade
gracefully on its own if the webhook goes quiet again, the same way it already
did before this work existed.

## Status update, 2026-08-10

None of this plan's "Work items" below were executed as scoped. A later session opened by asking
whether it was feasible to fork HA core's `rachio` integration to add native `DELTA` handling, which
led to actually querying Rachio's API directly (pde's own developer key, obtained and used for the
first time this session) instead of relying on doc fetches, and that answered the open question
below plus turned up something more consequential:

- **The `DELTA` blocker is resolved.** `GET /1/public/notification/webhook_event_type`, the
  authenticated endpoint Rachio's own docs point to as authoritative, confirms `DELTA` (id 14) and
  `ZONE_DELTA` (id 12) both exist as live, registerable event types today, alongside the five HA's
  `rachio` integration already subscribes to. The public docs page not showing them (what the
  "Real fix" bullet below couldn't resolve) was a documentation gap, not evidence they'd been
  removed.
- **But `DELTA` payloads carry no field-level diff.** Rachio's own sample-JSON reference for
  `DEVICE_DELTA` (`rachio.readme.io/reference/sample-webhook-json`) shows only
  `{"action":"UPDATED","category":"DEVICE","deviceId":"...",...}`, no data on *what* changed. This
  means Track B below (a native `trigger: webhook` automation reloading the config entry) is now
  unblocked and still architecturally sound, but its value is narrower than "Real fix" implied: it
  would only speed up detection, from up to an hour down to seconds, not provide better information.
  The response to a `DELTA` event is necessarily still "call Rachio's API and diff," the same thing
  the periodic reload already does. Forking the integration to handle `DELTA` natively (the question
  that started this) buys the same thing Track B does, at the cost of permanently shadowing a core
  HA component and manually re-syncing it against upstream forever; not worth it for a benefit this
  narrow. Neither was built.
- **What actually happened instead**: while chasing the `DELTA` question, pde reported the
  disabled-zone alert's false positives (unrelated to any of this, and not something webhooks would
  have fixed even if built) were genuinely bothering him. That turned out to be a real, structural
  race condition in the existing reload/diff automation, found from real production data and fixed
  the same day, plus a new live current-state indicator and a second automation covering the Back
  Yard Smart Hose Timer's own failure modes (dead battery, offline). Full writeup in
  `rachio-zone-disabled-alert.md`'s "The reload race condition, and the fix" and the two sections
  after it. That fix also has two knock-on effects on this plan, noted inline below: it decouples
  the 15-minute reload-cadence idea from false positives entirely (that reasoning is now stale), and
  it builds the "standalone staleness indicator" this plan rejected below, just scoped to
  disabled-zone status specifically rather than general entity staleness.

The Context and Graceful degradation reasoning below is unaffected and still accurate; this file is
being revised in place rather than superseded by a new one, since nothing in it turned out wrong,
just unfinished and partly overtaken by the disabled-zone fix.

## Decisions made in this session

- **Scope: both the doc/backlog cleanup and new dashboard UX** (not just closing
  the loop on old docs). The dashboard should surface new information that
  wasn't trustworthy enough to show before.
- **Rollback: graceful degradation only**, no explicit "undo Nabu Casa Cloud"
  runbook. See "Graceful degradation" section below for what happens
  automatically vs. what needs documenting.
- **Verification of the webhook itself**: an active test (start a real zone
  briefly from the Rachio app, bypassing Homie, and watch
  `switch.main_irrigation_*` flip within seconds, the same method that
  originally proved the bug in `project-todo.md` item 4). Explicitly **not** a
  blocker for the rest of this plan; pde may run it later today. Record the
  result in `rachio-zone-disabled-alert.md` or the new doc (see below) once run.
- **New dashboard UX in scope**: a rain-delay/standby banner surfaced on the
  Irrigation control's card face (currently only visible inside the zone popup),
  and a next/last scheduled run display sourced from
  `calendar.rachio_base_station_ca358975`, which is fetched by the Rachio
  integration today but has never been wired into any dashboard. A "remaining
  time while watering" feature was considered and **rejected**: checked live,
  `switch.main_irrigation_*` attributes carry only static zone metadata (zone
  number, shade, soil type, slope, photo), no duration or progress data exists
  anywhere in the Rachio integration to build this from, webhook or not.
- **A standalone staleness indicator was considered and rejected**, not because
  it's unneeded but because tightening the disabled-zone reload cadence (see
  below) already provides the same safety property for free: every Rachio entity
  gets refreshed at worst every 15 minutes regardless of whether the webhook is
  working, since a config-entry reload re-fetches everything, not just the zone
  list. That reload cadence is the graceful-degradation floor; a separate "as of
  HH:MM" badge would be redundant with it. Worth revisiting only if pde finds
  the 15-minute floor insufficient in practice.

  Partially overtaken 2026-08-10: this was about a general "as of HH:MM"
  staleness badge, still not built and still reasoned about the same way above.
  What did get built is narrower and different in kind, a live current-state
  indicator (`input_boolean.rachio_zone_or_valve_disabled` plus a
  `device_class: problem` binary_sensor) for disabled-zone status specifically,
  requested directly by pde for a dashboard red-dot, not a staleness measure.
  See `rachio-zone-disabled-alert.md`.
- **Disabled-zone detection: pursue both the incremental fix and the real fix.**
  - Incremental (build now): tighten
    `automation.rachio_periodic_config_entry_reload` from hourly to 15 minutes.
    The hourly choice was made explicitly on the hope that a webhook fix might
    make the whole reload workaround moot "within the week," reasoning now known
    to be wrong for this specific problem. Rachio's API budget has enormous
    headroom for this (15 min ≈ 96 calls/day against a 3,500/day cap), so the
    real tradeoff is just a ~2 second `unavailable` flicker on every Rachio
    entity, more often. Also restore the `notify.notify` push step on
    `automation.rachio_zone_or_valve_disabled_alert` (removed 2026-08-08 pending
    observation); the scenario that motivated removing it, a false page from the
    3 AM schedule, was already confirmed unreachable in the same investigation.

    Not built this way. `notify.notify` was restored 2026-08-10, but as part of
    fixing the actual cause of false pages (see status update above), not as a
    standalone step. The 15-minute retiming itself was never done: it was
    motivated by trading a bit more `unavailable` flicker for less false-positive
    risk, and 2026-08-10 found that flicker frequency was never really the
    variable that mattered, the diff automation's own architecture was. With that
    fixed, tightening the cadence is now a pure detection-latency choice (worst
    case one hour down to worst case 15 minutes), fully decoupled from false
    positives either way, still open, still pde's call.
  - Real fix (research spike, build if feasible): register a **second,
    independent** Rachio webhook scoped to config-change events, delivered to a
    plain HA automation using a native `trigger: webhook`, whose only action is
    `homeassistant.reload_config_entry`. Confirmed via Rachio's API docs that
    multiple independent webhooks can be registered per resource (up to 10), so
    this is architecturally possible in principle. Not yet confirmed: whether a
    `DELTA` (or equivalent config-change) event type still exists in Rachio's
    current API, the existing investigation cites it from the same docs page a
    fetch just failed to surface it, needs a careful manual read, not another
    quick fetch. This also needs pde's own Rachio developer API key to actually
    register the webhook; the agent can build and test the HA-side automation
    once that registration exists, but cannot create it. If it ships, it does
    not replace the 15-minute reload, it's an additive fast path; the reload
    stays as the graceful-degradation floor regardless.

    Resolved, not built. See "Status update, 2026-08-10" above: `DELTA` and
    `ZONE_DELTA` are both confirmed live, so the blocker is gone, but their
    payload carries no field-level diff, only "something changed, go re-fetch."
    That caps this idea's value at detection speed, not better data, so it
    remains a real but lower-priority option than it looked when written. Still
    needs pde's own API key to register the webhook regardless of when it's
    built.
- **New backlog item**: add a `project-todo.md` entry reminding pde to actually
  fix the root cause upstream, HA core's `rachio` integration never subscribing
  to Rachio's config-change webhook category at all. This is a separate,
  longer-horizon item (patch or upstream PR against `home-assistant/core`),
  independent of the workarounds above, in the same spirit as the
  `hass_nabucasa` upstream-issue prep work in
  `nabucasa-remote-ui-dns-fragility.md`.

## Graceful degradation (what "rollback: A" means concretely)

Document this explicitly in the new doc (see below) so it doesn't need to be
re-derived if Cloud is ever cancelled:

- **If the webhook stops being delivered** (Cloud cancelled or otherwise): zone
  on/off state goes back to updating only on reload, exactly as before this
  work, no error states, no manual cleanup. Worst-case staleness is bounded by
  the reload cadence (15 minutes after this plan, same mechanism as
  disabled-zone detection).
- **If the second (Track B) webhook stops being delivered**: the automation it
  triggers simply stops firing; the 15-minute reload continues covering the same
  ground on its own schedule. No dependency the other direction.
- **Nothing in `homie-dashboard` should assume the webhook is permanent.** The
  new UX (rain-delay banner, next/last run) reads from HA state/calendar
  entities the same way everything else does; if those entities go stale, they
  show stale data the same way any other entity would, not an error. No new
  failure mode is introduced.

## Work items

**Status, 2026-08-10: none of this section was executed as scoped.** Line-item status below;
see "Status update, 2026-08-10" above for the full story of what happened instead.

### 1. Home Assistant side (this repo documents it, changes happen live via REST, same pattern

already used for `rachio-zone-disabled-alert.md`)

- Update `automation.rachio_periodic_config_entry_reload`: `time_pattern` from
  `hours: "/1"` to `minutes: "/15"`. **Not done.** Still hourly; now a pure
  latency choice, decoupled from false positives, see above.
- Update `automation.rachio_zone_or_valve_disabled_alert`: restore the
  `notify.notify` action step (same block already documented, currently only on
  the standby-mode automation). **Done, 2026-08-10**, but as part of the
  reload-race fix, not as an isolated step.
- Verify both via `automation.trigger` and a trace check, same method already
  used in `rachio-zone-disabled-alert.md`'s Trigger history table. N/A, nothing
  here to verify since the retiming wasn't done; the `notify.notify` restoration
  was verified as part of the reload-race fix instead.
- Research spike (read-only): fetch and actually read Rachio's webhook docs
  (`rachio.readme.io/reference/webhooks`) in full for current event-type
  categories, confirm whether a config-change/`DELTA`-equivalent category still
  exists and what its payload looks like. Document the finding either way.
  **Done, 2026-08-10**, but by querying Rachio's authenticated API directly
  rather than re-fetching the public docs page that had already failed twice;
  see "Status update" above for the finding.
- If feasible: draft the native `trigger: webhook` automation (action: reload
  the Rachio config entry, `entry_id: 01KZCBXSB0RM5JM99NAJ1V4J19`), but do not
  attempt to register it with Rachio directly, that needs pde's own API key.
  Hand off the registration step explicitly. **Not done.** Now unblocked
  (feasibility confirmed) but not drafted; still needs pde's API key to
  register regardless of when it's built.
- Run pde's active webhook-liveness test (zone start/stop) whenever he's ready,
  non-blocking; record the result. **Not done, still open.** Unrelated to
  everything else that happened 2026-08-10.

### 2. Documentation (this repo)

- Update `rachio-zone-disabled-alert.md`: close out "Remaining gaps" items that
  this plan resolves (reload cadence, notify restoration), correct the "might
  make this moot" framing now that it's known the webhook doesn't affect
  disabled-zone detection, and note the `entity_registry_updated` open item as
  superseded/no longer worth pursuing if Track B ships (a native
  webhook-triggered reload is a strictly better event source than that event
  ever would have been). **Done, 2026-08-10, but for different reasons than
  scoped here.** The gaps closed were the reload-race false positives this plan
  never diagnosed, not the ones this plan expected to resolve. The
  `entity_registry_updated` note was updated too, marked lower priority since
  the debounce fix solved its underlying reliability concern directly.
- New file, e.g. `rachio-webhook-responsiveness.md`: records this decision
  (webhook now live via Nabu Casa Cloud), the two-track disabled-zone-detection
  fix, the graceful-degradation posture, the webhook verification test and its
  result once run, and the new dashboard UX. Add it to `README.md`'s contents
  list. **Done differently**: revised this file in place at pde's explicit
  instruction rather than spinning off a new one, since nothing in the original
  Context/Graceful-degradation reasoning turned out wrong. Added to `README.md`
  under this file's existing name.
- Update `project-todo.md`: resolve/update item 4 (webhook limitation, now fixed
  for on/off state), add the Track B research-spike/build item, and add the new
  upstream-fix reminder item for HA core's `rachio` integration never
  subscribing to config-change webhooks. **Not done.** Not asked for this
  session; item 4 still describes the pre-Nabu-Casa-Cloud state.

### 3. `homie-dashboard` (separate repo, working copy

`/Users/pde/src/github.com/pdehlke/homie-dashboard`)

**Not started.** Entirely unaffected by everything else in "Status update, 2026-08-10"; still
fully open, still scoped as below.

- Rain-delay/standby banner: surface `switch.main_irrigation_rain_delay` and
  `switch.main_irrigation_standby` on the Irrigation control's card face. Reuse
  the existing disabled-zone badge pattern (`irrigationDisabledZones()`,
  `updateIrrigationZoneCard()` in `dist/homie-dashboard.html`) as the closest
  existing precedent for a card-face status badge rather than inventing a new
  one.
- Next/last scheduled run: subscribe to `calendar.rachio_base_station_ca358975`
  and surface its `message`/`start_time`/`end_time`/`description` attributes on
  the Irrigation control. This entity has never been referenced anywhere in
  `homie-dashboard`; follow the existing WebSocket state-subscription pattern
  (`_wsConnect`, `stateCache`) rather than adding a separate poll. Nothing
  time-sensitive depends on this being real-time; it updates on the same cadence
  as everything else.
  - Note: this needs `sensor.homie_irrigation_status` and/or `dist/config.js`
    extended to reference the calendar entity, since it's currently entirely
    absent from Homie's config; check `docs/pdehlke-customizations.md`'s
    existing conventions for how entities get added to a control before wiring
    this in.
- No changes needed for zone on/off responsiveness itself, that's automatic once
  the webhook is confirmed live, per the existing WS-first pipeline
  (`dist/homie-dashboard.html` ~L8963-9192).
- Update `docs/pdehlke-customizations.md` with a changelog entry once shipped,
  per that file's existing convention.
- Do not touch `WS_URL` or anything related to the currently-broken dashboard
  connection; that is explicitly out of scope for this work.

## Verification

**Status, 2026-08-10**: none of the below was run, since the work it verifies wasn't built. The
reload-race fix and the new Back Yard automation were both verified instead, against real
conditions (a forced config-entry reload, a real battery pull), documented in
`rachio-zone-disabled-alert.md`'s Trigger history table.

- HA automations: `automation.trigger` + `trace/get` over WebSocket showing a
  clean run, and `switch.main_irrigation_east_of_garage`'s `last_changed` moving
  to within seconds of the trigger (same method already used when the reload
  automation was first built).
- Webhook liveness: pde's deferred active zone test; watch the zone switch flip
  in HA within seconds of starting/stopping it from the Rachio app directly.
- `homie-dashboard` UX: Playwright screenshot of the Irrigation control showing
  the new banner and schedule display, plus whatever test coverage matches the
  existing pattern in `test/screen-a.test.cjs` (which already covers the
  disabled-zone badge at similar card-face locations).
- Re-run the doc's own reproduction queries (`rachio-zone-disabled-alert.md`'s
  "Reproducing the measurements" section) after the cadence change to confirm
  the new interval is actually in effect.
