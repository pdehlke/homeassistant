# Time-slicing one panel slot between Lights and A/V

This is the design for step 1 of [issue #20](https://github.com/pdehlke/homeassistant/issues/20):
subsystem switching plus a write lock in the `crestron_cip` integration, so the single AADS panel
slot the lighting bridge already holds at `IP-ID 0x13` can carry audio as well. It is the
load-bearing piece. Zone and volume services, the six-zone script, and the Homie button are steps
2 through 4 and are out of scope here.

The facts this design rests on were established in
[crestron-av-zone-control-path.md](crestron-av-zone-control-path.md) and
[crestron-lights-subsystem-gating.md](crestron-lights-subsystem-gating.md). Nothing below
re-derives them.

## What the integration does today

The code lives in the CresnetMon repo at `custom_components/crestron_cip/`, on branch
`macos-port-python`, at `4434da2`.

`CipClient` holds one registered CIP session. It carries a single optional `entry_join` and a
one-shot `_entered` boolean. `_mark_synced()` presses the entry join once per session, resets the
quiet-window baseline, and only calls the session `synced` after the dump that press shakes loose
has landed. `_session()` clears `_entered` and `digital` on every new connection, so entry is per
session rather than once per process.

`CrestronBridge` owns both links, keeps `digital` per client as the authority for load state, and
guards every load command with `_guard()` against `FORBIDDEN_AADS_WRITE`. It holds one
`asyncio.Lock` per link across the whole of `_async_set()`, including both confirmation attempts.

## Why the current model cannot carry A/V

### One boolean cannot express three states

`_entered` says only "the entry press has been sent this session". With two subsystems the link
needs to answer "which one is the slot in right now", and the honest answer includes *unknown*,
which is the state a fresh session and a failed entry are both in. Two booleans would allow the
impossible state where both read true.

### The write side is the smaller half

The A/V write joins (`d951`-`d956` zone select, `d51`-`d56` source, `d44`/`d45`/`d48` volume,
`d42`/`d40` power, `d75` entry) do not overlap the lighting write joins (`d101`-`d247`, `d91`).
Pressing a lighting join while the slot sits in A/V therefore does not fire an A/V function. It
does something unknown, probably nothing, and the load never confirms, so the command fails its
retries and reports honestly. Wasted presses, not damage.

The one genuinely destructive write surface, `d130`-`d148` and `d93`, is refused unconditionally in
both subsystems already, and [the A/V pages never use that range at
all](crestron-av-zone-control-path.md#the-subsystem-gate-applies-to-audio-too).

### The receive side is where state gets corrupted

This is the dangerous half, and issue #20's build order does not name it.

`CipClient._handle_data()` writes every incoming digital join into one flat `self.digital` dict,
and `CrestronBridge._on_digital()` maps a join straight to a load with no notion of which subsystem
produced it. `is_on()` then reads `self._clients[link].digital.get(load.join)` at `bridge.py:116`.

The A/V pages reuse `d101`-`d109`, `d201`-`d204` and `d151`-`d157`, which collide with the Dining
block, the Patio block and the HVAC schedule block. So while the slot is in A/V, an incoming `d101`
means the AppleTV menu and today would turn `binary_sensor.crestron_dining_room_table` on, resolve
any waiter on that key, and notify every listener. Six of the Courtyard scene macros and the whole
Dining block are exposed the same way.

### Absence does not mean off, which is what breaks a rebuild on re-entry

The dump reports only high joins, which is why `bridge.py:114` can treat a join the processor never
mentioned as off. That is sound at session start because `_session()` clears `digital` first.

It is not sound mid-session, and the reason is not the one this document originally gave. An entry
dump is **not** a complete re-assertion of the subsystem's high joins. Measured live on 2026-09-22:

- One Lights entry omitted `d241` while that join was high, logged as
  `lights entry dump omitted 1 join(s) that were high: [241]`.
- Three read-only registrations in a row reported 23 high joins; a fourth, minutes later with no
  physical change, reported 24.

So absence carries no information at all, and a rebuild that reads it as off will publish a lit
load as dark. Merging is the only safe reading of an entry dump.

The initial registration dump is different, and that difference is the fix for the one case where
absence genuinely does mean off. Re-sending the registration-time update request mid-session
returns the full state, about 149 frames in 0.86s, and ends with the explicit end-of-query marker.
Bring-up therefore enters the subsystem and then re-polls, because at bring-up the bucket starts
empty and a partial dump would leave a lit load reading off for the life of the session.

## The design

### Subsystem becomes first-class state on the link

`CipClient` gains a map of subsystem name to entry join, a default subsystem, and a
`current_subsystem` that starts as `None` and means "unknown, press before writing". The MC2E link
gets an empty map and a `None` default, so every path below is a no-op there and the Kitchen is
untouched.

```
SUBSYSTEM_LIGHTS = "lights"
SUBSYSTEM_AV = "av"
ENTRY_JOINS = {SUBSYSTEM_LIGHTS: 91, SUBSYSTEM_AV: 75}
```

`LIGHTS_ENTRY_JOIN` stays as it is so nothing that reads it breaks, and `_validate()` grows an
assertion that no entry join is in `FORBIDDEN_AADS_WRITE`, which currently covers `d91` alone.

### Every write names the subsystem it needs

`async_press()` is replaced at every call site by a form that takes the join and the subsystem that
join belongs to, and refuses if `current_subsystem` is not that subsystem. The check sits
immediately before bytes reach the wire, the same placement and the same reasoning as the existing
alarm guard. The point is that a future A/V code path cannot emit a lighting join by forgetting to
switch; it is prevented by construction rather than by discipline.

### Per-subsystem receive buckets

`digital` and `analog` become per-subsystem dicts, keyed by whatever subsystem the slot was in when
the join arrived, with the pre-entry menu dump landing under the `None` bucket. `is_on()` reads the
Lights bucket and can never see an A/V join. `a11` and the zone joins land in the A/V bucket, ready
for step 2.

Serial joins stay session-wide rather than per-subsystem. The sixty-five lighting load names arrive
once per session, not once per entry, so bucketing them would lose them on the first switch.

### Re-entry merges rather than rebuilds

**Corrected 2026-09-22, after the first version of this shipped and was wrong.** The original design
argued that entry should rebuild: treat a join absent from the dump as off, because the dump reports
only high joins and absence is therefore how an off arrives. Deployed, that reported North Sink off
while the light was on. The entry dump had simply not mentioned `d241`, and nothing followed to
correct it. The section below is the corrected design; the reasoning that failed is kept in
[What the live deploy corrected](#what-the-live-deploy-corrected).

An entry dump is a statement about the joins it contains and says nothing about the ones it omits.
So entry merges: every join in the dump is applied, and a join not in it keeps whatever it had.

`async_enter(subsystem)` does:

1. Return immediately if `current_subsystem` already matches.
2. Set `current_subsystem` to `None` and open a fresh collection dict for the target subsystem.
3. Press the entry join.
4. Wait for the dump to complete (see the measurement question below).
5. Merge the collected dict into the subsystem's bucket, firing `_on_digital` only for joins the
   dump actually mentioned and whose value changed. Log any join that was high and went unmentioned,
   which is the evidence trail for how partial these dumps really are.
6. Set `current_subsystem`.
7. On timeout, leave `current_subsystem` as `None` and return failure.

The accepted cost is the case that motivated the rebuild: a load switched off at a wall panel while
the slot was away keeps reading on until a later frame corrects it. That is a stale reading.
Synthesising an off from silence produced a wrong one, and the wrong direction here is a lit load
reading off, which is the exact signature of the 2026-09-15 outage this integration exists to stop
repeating.

`_mark_synced()` becomes one caller of this rather than its own mechanism, which removes `_entered`.

### One lock per slot, held briefly

The existing per-link `asyncio.Lock` becomes the slot lock and takes on a second job. Every
operation acquires it, calls `async_enter()` for the subsystem it needs, does its work, and
releases.

Issue #20 proposed that the six-zone walk "interrupt itself when a lighting write arrives". No
interrupt machinery is needed. `asyncio.Lock` wakes waiters in FIFO order, so the same behaviour
falls out of a rule about hold time: **no operation holds the slot lock for longer than one press
or one ramp segment.** The walk becomes a sequence of short lock-held units with the lock released
between them. A lighting write queued behind one unit waits at most that unit, pays one entry to
Lights, and runs.

| Step | Cost |
|---|---|
| Worst case wait for the current A/V unit | 1.0s |
| Entry to Lights, including the quiet window that confirms it | ~0.88s |
| **Worst-case added lighting latency** | **~1.9s** |

Shortening the A/V hold from the 1.5s originally proposed to 1.0s is what keeps this under two
seconds once the measured quiet window is included. It costs nothing: a shorter unit means more
lock acquire and release cycles, and those are free. Nothing switches subsystem between two A/V
units when no lighting write is waiting.

Chopping the ramp is safe because `s11` and `a11` both survived four subsystem switches unchanged,
so a ramp resumed after a lighting excursion picks up where it left off rather than starting over.
It also happens to be the right shape anyway: the ramp has to be open-loop then corrected against
`a11`, and a segmented ramp is a closed loop for free.

### Idle return to Lights

While the slot sits in A/V, lighting state is frozen at whatever the last Lights dump said, and a
light changed at a wall panel is invisible. That is fine for two seconds and wrong for an hour, and
nothing in the A/V path would otherwise ever switch back.

So a watchdog returns the slot to its default subsystem once the lock has been idle for
`IDLE_RETURN_SECONDS`. The threshold has to exceed the longest gap between two units of a running
walk, or the walk pays a pointless round trip between every zone.

### Entity availability does not change

Lighting entities keep their last known state during an excursion rather than going unavailable.
Flapping thirty binary sensors to unavailable and back every time somebody sets the volume would be
worse than a two-second stale read, would churn the recorder, and would break any automation that
tests for `unavailable`. Every switch is logged at INFO so the excursions are visible.

### The guard moves into the client

`FORBIDDEN_AADS_WRITE` is currently checked at table-import time and in `CrestronBridge._guard()`.
Adding a second and third write surface (entry joins, then A/V joins in step 2) means the bridge is
no longer the only door to the wire. The client takes a `forbidden` set and checks it inside the
press path, so every write on that link is covered including entry presses and anything step 2
adds. The existing two checks stay; this is a third, not a replacement.

## What issue #25 gets for free

[Issue #25](https://github.com/pdehlke/homeassistant/issues/25) asks for re-entry into Lights when
a press goes unconfirmed, to escape the state where `_entered` is stuck true and every command
fails forever. In this model that is one line in `_async_set()`'s timeout branch: set
`current_subsystem` to `None`. The next attempt's `async_enter()` re-presses the entry join,
rebuilds state, and retries. No special case, no extra code path, and it cannot be forgotten
because the same invalidation is what a failed entry already does.

It also answers the open question in that issue about whether re-entry should refresh cached join
state. It does, by rebuilding, which is stronger than what the issue contemplated.

The `wontfix` outcome that issue offers is no longer attractive. The machinery exists regardless
once the slot is shared, so the marginal cost of the recovery is a single assignment.

## Confirming an entry landed, measured 2026-09-22

`async_enter()` needs to know when the entry dump is complete. Two signals were candidates and the
measurement settled it: **no end-of-query frame follows a subsystem entry, so the quiet window is
the only signal available.**

`mac/poc_subsystem_timing.py` in the CresnetMon repo took the measurement. Run it from `mac/`, which
is where that repo's `pyproject.toml` lives; there is none at its root, so `uv run` from there falls
back to an interpreter too old for the script, which the script says rather than failing obscurely.

```
cd mac && uv run python poc_subsystem_timing.py
```

It registers on slot `0x14`, presses `d91`, `d75`, `d91`, `d75`, `d91`, and reports per press how
many frames arrived, the offset of the first and last, the largest gap between two consecutive
arrivals, and whether an end-of-query frame came with it. Heartbeat traffic is excluded from the gap
statistics, because counting it would invent gaps a real dump does not have. It needs no Cresnet tap
and no unplugged panel, and it is stdlib-only for that reason: the obvious existing tool,
`mac/poc_panelpress.py`, cannot run without the tap's dependencies despite its own docstring saying
it needs none.

| Window | Frames | Records | First | Last | Largest gap | End-of-query |
|---|---|---|---|---|---|---|
| Registration dump | 153 | 169 | +0.025s | +0.964s | 0.205s | +0.926s |
| `d91` Lights | 7 | 39 | +0.128s | +0.529s | 0.144s | none |
| `d75` A/V | 6 | 24 | +0.092s | +0.523s | 0.352s | none |
| `d91` Lights | 6 | 25 | +0.093s | +0.514s | 0.155s | none |
| `d75` A/V | 6 | 25 | +0.088s | +0.517s | 0.349s | none |
| `d91` Lights | 6 | 24 | +0.104s | +0.525s | 0.166s | none |

### The end-of-query marker is not available, and would not have been sufficient anyway

Only the registration dump produced one. Five subsystem entries produced none, so the exact
confirmation `cip.py:298` already knows how to handle never arrives for an entry.

That is worth knowing about the bridge as it stands today, not only about this design.
`_mark_synced()` presses `d91` and is then reachable from the end-of-query branch or from the
two-second quiet check at `cip.py:191`. It has always been the quiet path that fires. The
`SYNC_QUIET_SECONDS` wait is load-bearing rather than a fallback that never runs, and session
startup has been paying a full two seconds for it since 2026-09-15.

Even where the marker does fire it is not the last word: the registration dump's final frame
arrived at +0.964s, 38 ms *after* its end-of-query at +0.926s. Waiting on the marker alone would
have truncated the dump it was supposed to certify.

### A/V dumps have a structural pause that Lights dumps do not

The two A/V entries produced largest gaps of 0.352s and 0.349s. The three Lights entries produced
0.144s, 0.155s and 0.166s. A four-millisecond spread across two independent A/V samples is not
jitter, so the pause is a property of the A/V dump rather than of the network.

This argues for a threshold per subsystem rather than one shared number. Lighting latency is the
number a person actually feels, and tying it to the A/V dump's pause would make every light slower
for no reason.

### What the numbers make the threshold

A quiet-window detector resets its baseline when it sends the entry press, so the threshold has to
clear the wait for the first frame as well as every gap inside the dump. Press to first arrival
ranged 0.088s to 0.128s, comfortably below both gap figures, so the gaps are the binding constraint.

| Subsystem | Largest gap seen | Threshold | Entry completes | Total switch cost |
|---|---|---|---|---|
| Lights | 0.166s | 0.35 | ~0.53s | ~0.88s |
| A/V | 0.352s | 0.70 | ~0.52s | ~1.22s |

Both thresholds are a little over twice the largest gap measured for that subsystem. The dumps
themselves finish in 0.514s to 0.529s across all five entries, which corroborates the 0.528s to
0.561s the earlier round-trip run on the same slot reported for its later switches.

| Constant | Value | Basis |
|---|---|---|
| `AV_ENTRY_JOIN` | 75 | Panel project home page, confirmed live 2026-09-17 |
| `ENTRY_QUIET_SECONDS[lights]` | 0.35 | Twice the 0.166s largest gap measured over three Lights entries |
| `ENTRY_QUIET_SECONDS[av]` | 0.70 | Twice the 0.352s largest gap measured over two A/V entries |
| `ENTRY_TIMEOUT` | 3.0 | Slowest dump to finish was 0.964s, and that was the registration dump |
| `IDLE_RETURN_SECONDS` | 5.0 | Longer than the longest gap between two A/V units |
| `MAX_AV_HOLD_SECONDS` | 1.0 | Chosen to keep worst-case lighting latency under 2s, see below |

## Failure behaviour

A failed entry must abort the operation, never fall through to the press. Pressing a lighting join
into an A/V slot is the wasted-press case above, which is survivable, but reporting success for it
is not. `async_enter()` returning false raises `CrestronError`, which `__init__.py` already
converts into a `HomeAssistantError` visible to whoever called the service.

This is strictly safer than today, where a failed entry leaves `_entered` true and the bridge
pressing into a gated slot indefinitely. That is the 2026-09-15 failure mode minus the restart that
cleared it.

## Rejected alternatives

| Option | Why not |
|---|---|
| Unplug a second panel for a dedicated A/V slot | Costs a second working touch panel. Only worth it if the lock proves harder than this design suggests, and the round-trip test says it does not |
| Explicit preemption: interrupt the walk when a lighting write arrives | Needs a cancellation protocol and a resume point. A bounded lock hold plus FIFO waiter order gets the same latency with no new machinery |
| Merge the re-entry dump into existing state | Absence means off, so a load switched off while away would read on forever |
| Two booleans, `_in_lights` and `_in_av` | Permits the impossible both-true state and cannot express unknown, which is what a fresh session and a failed entry both are |
| Mark lighting entities unavailable during an A/V excursion | Flaps thirty entities for a sub-second window, churns the recorder, breaks `unavailable` checks |
| Read `s16` to learn the current subsystem | Proven unreliable: it still read `Lights` after the slot had returned to A/V |
| Fixed sleep after the entry press | Either too short for the 0.98s first entry or wasteful on every 0.53s one. The quiet window adapts and the end-of-query marker, if it fires, is exact |
| Share a live panel slot instead | A slot has one cursor and a person is holding the other end of it |

## Test plan

Extend `tests_ha/test_crestron_cip.py` at the end, next to the existing gating tests, which already
provide `_client()` and a `FakeClient` with a `reply` flag for modelling a silent processor.

- A lighting write while the slot is in A/V presses the Lights entry join first, then the load join.
- A lighting write while the slot is already in Lights presses no entry join.
- The MC2E link never presses an entry join, in either direction. This is the Kitchen regression.
- An entry dump that drops a previously-high join fires an off for that load.
- An entry dump that re-asserts identical values fires nothing.
- `d101` arriving while the slot is in A/V leaves `dining_room_table` untouched.
- A press the processor never confirms invalidates the subsystem, and the retry re-presses the
  entry join. This is issue #25's acceptance test.
- A failed entry raises rather than pressing the load join.
- Two concurrent operations wanting different subsystems serialize, and the second re-enters.
- Idle return switches back to the default subsystem and only when the lock is idle.
- `d93` is still refused; `d91` and `d75` are not in the forbidden set.
- No write path reaches the wire without passing the forbidden check, asserted the way
  `test_services_are_not_registered_with_lambdas` asserts over source text.

## Live verification plan

Step 1 ships one developer service, `crestron_cip.enter_subsystem`, so the switch can be exercised
before any A/V service exists. It takes the subsystem name, acquires the lock, switches, and
returns the resulting state as service response data. It is also the thing step 2 builds on.

Deploy by SFTP to `/config/custom_components/crestron_cip/`. The SSH add-on is manual-boot: start
it first, stop it after.

1. Record every `binary_sensor.crestron_*` state.
2. Call `enter_subsystem` for A/V. Confirm the log shows the switch and that no lighting entity
   changed state.
3. While the slot is in A/V, toggle a light through `crestron_cip.toggle`. Confirm it enters Lights,
   the load confirms, and the round trip lands inside the latency budget.
4. Switch to A/V again, change a light at a wall panel, and confirm the change appears in Home
   Assistant on the next re-entry rather than being lost.
5. Confirm idle return fires and the slot ends up back in Lights with nothing further called.
6. Confirm `crestron_cip.turn_on` on a load whose press join is in the alarm range is still refused.
7. Leave it running and confirm no entity flapping and no unexpected entries in the log.

## Live verification, 2026-09-22

Deployed to `/config/custom_components/crestron_cip/` by SFTP and verified against the running
house. The five changed files checksummed identically on both ends, and the files they replaced
matched CresnetMon `4434da2` exactly, so nothing on the instance was lost.

| Check | Result |
|---|---|
| All thirty-eight Crestron entities present, both links connected | Yes, unchanged across the restart |
| `enter_subsystem` into A/V | 1.25s, against 1.22s predicted |
| Lighting entities while the slot sat in A/V | None moved |
| `turn_on` issued from inside A/V | 1.09s, entered Lights first, load confirmed |
| Redundant `turn_on`, already in Lights | 0.03s, no entry press and no load press |
| `turn_off`, already in Lights | 0.23s |
| Idle return | Fired 5s after the A/V entry settled, logged at 10:30:47 |
| Lighting state after four subsystem switches | Identical to before, both lit loads still lit |
| Errors in `system_log` | None |

The worst case the latency budget predicts is about 1.9s and the worst case measured was 1.09s,
because the measured case pays one entry rather than an entry behind a full A/V hold.

The four logged transitions are the whole mechanism visible end to end:

```
10:30:09.529  aads: entering the av subsystem on d75 (was lights)      service call
10:30:23.926  aads: entering the lights subsystem on d91 (was av)      a turn_on arrived
10:30:40.779  aads: entering the av subsystem on d75 (was lights)      service call
10:30:47.432  aads: entering the lights subsystem on d91 (was av)      idle return
```

One check in the plan above is not done, because it needs a person at a wall panel: switch the slot
to A/V, change a light by hand, and confirm Home Assistant catches the change on re-entry rather
than losing it. The rebuild that makes this work is unit-tested against the recorded East Hall
transition, and the live state did survive four switches intact, but neither of those is the same
as watching an externally-originated change land.

## What the live deploy corrected

The first version of this design shipped with the rebuild described above, and the house found two
faults in it inside four minutes. Both are recorded here because the reasoning that produced them
was plausible and is worth not repeating.

### A partial dump published a lit load as dark

```
17:30:23.926  entering lights (was av)          entry B
17:30:24.869  office_north_sink -> off          B's rebuild, 0.94s after the press
17:30:47.432  entering lights (was av)          entry D
17:30:47.901  guest_suite_east_hall -> off      D's rebuild, 0.47s after the press
17:30:48.315  office_north_sink -> on           late frames, 0.88s after the press
17:30:48.316  guest_suite_east_hall -> on
```

Entry B's dump did not contain `d241`, so the rebuild treated the absence as off and published it.
The light was on the whole time. The fix is the merge above.

The error was not a coding slip. It was an inference from one observation: the 2026-09-17 round
trip, where a second Lights entry "reported `d243` gone", was read as proof that absence means off.
It is equally consistent with the dump being partial, which is what the evidence now says it is.
One observation that two mechanisms explain is not evidence for either.

### The collection window closed in the middle of a dump

Entry D's rebuild ran 0.47s after the press, on a dump whose last frame lands at about 0.53s.
Everything after that arrived outside the collection and moved the same entities a second time,
0.4s later. The cause is that an entry dump arrives in bursts, and the gap between two bursts on
this slot exceeded the 0.35s quiet threshold measured on slot `0x14`.

Two lessons. The quiet window needs a floor as well as a threshold, so it cannot close before the
dump has had time to finish whatever the silence in the middle looks like; `ENTRY_MIN_SECONDS` is
that floor. And a timing measurement taken on one panel slot does not transfer to another, which
the original measurement had no way to know and this document previously implied it did.

### What the re-deploy verified

Three full A/V round trips with the merge and the floor in place: entry to A/V 1.25s to 1.38s, back
to Lights 0.92s to 0.95s, and across all six entries not one spurious state change. One entry
logged `lights entry dump omitted 1 join(s) that were high: [241]` and correctly left the join
alone, which is the failing case reproduced and handled.

## Entering the Lights subsystem turns a light on

**This is the finding of the day and it is not about Home Assistant.** Pressing `d91` on slot
`0x13` turns North Sink on, about 1.1 seconds after the press.

pde identified it from years of living with the house: waking panel 14 from standby turns East Hall
on, and no other panel does that. The same thing happens per slot, with a different load each time.
`0x13` is North Sink's.

Reproduced deliberately on 2026-09-22, starting from both loads confirmed off at the fixture:

| Trial | Before the entry | After the entry |
|---|---|---|
| Enter A/V, then Lights | North Sink off | **North Sink on, +1.1s** |
| Enter A/V, then Lights | North Sink on | North Sink on |
| Enter A/V, then Lights | North Sink on | North Sink on |
| Enter A/V, then Lights | North Sink on | North Sink on |

It is a turn-on, not a toggle: three repeats from the on state left it on. Registering read-only on
`0x12` and `0x14` turned nothing on, but neither slot was in the Lights subsystem at the time, so
those are not evidence that the effect is confined to `0x13`. Pressing rather than registering is
what has been shown to do it.

### Why it matters more than it looks

The bridge enters Lights on every reconnect, every Home Assistant restart, and every return from
A/V. So the bridge turns North Sink on every time it does any of those. The all-rooms A/V button
this whole design exists to enable would do it on every run.

It also explains most of a confusing day. North Sink kept coming back on with nobody touching it,
because the bridge kept turning it on, and this document previously concluded that `d241` did not
track its fixture. It does. The join was right and the house was doing what the join said.

### It is a program behaviour, and the fix is the slot

Nothing in `crestron_cip` presses `d241`. The AADS runs this on subsystem entry for that slot and
has done for years, long before this integration existed, so no code here can prevent it.

What settled it was pde naming where the panels physically are:

| Slot | Panel's room | Entering Lights turns on | That load's area |
|---|---|---|---|
| `0x12` | Kitchen | nothing observed | — |
| `0x13` | Office | North Sink | Office |
| `0x14` | Guest Suite | East Hall | Guest Suite |

It is a courtesy: wake the panel, light its room. The bridge inherited the Office panel's slot and
therefore inherited its courtesy light.

Three candidate triggers were live until the last test. A read-only registration on `0x12` turned
nothing on, and so did pde pressing that panel's own Lights button by hand, but neither ruled
anything out: the registration pressed nothing, and the button press was not over CIP. Pressing
`d75` then `d91` on `0x12` over CIP, the exact thing the bridge does, also turned nothing on. That
eliminated "a CIP press does it" and left the slot itself.

**So the bridge moved to `0x12`, the Kitchen panel, which pde took offline for the purpose.**
Nothing in the integration changed except the IP-ID. Rejected alternatives:

| Option | Why not |
|---|---|
| Restore the load's prior state after every entry | A press per entry, and it fights a person who deliberately turned that light on |
| Accept and document | A light comes on at every restart and every return from A/V, forever |
| Fix the AADS program | Correct at the source, and needs Crestron tooling plus the SIMPL source |

Verified after the move: bring-up on `0x12` turns nothing on, two full A/V round trips turn nothing
on, and a lighting command still works in 0.14s. Panel 13 is free again and could be plugged back
in, which is a better outcome for the Office than it had this morning.

## Entry dumps really are partial, confirmed separately

The turn-on above could have explained the partial-dump evidence away as a timing race, so it was
tested on a load the entry does not touch. East Hall was switched on, then a full A/V round trip
run:

```
11:10:57.336  aads: lights entry dump omitted 7 join(s) that were high: [41, 43, 47, 52, 225, 227, 241]
```

`d243` was in that dump and East Hall stayed on correctly. Seven other high joins were not,
including `d41`, `d43`, `d47` and `d52`, which appear in the high list of every read-only
registration ever taken from this processor. An entry dump is partial, and the merge above is what
keeps that from turning into a wrong reading.

## What this leaves open

- Whether `0x11` has an entry-triggered load of its own, and which room that panel is in. The
  bridge no longer cares, but it would confirm the courtesy-light reading.
- Whether the Kitchen panel slot has a courtesy load that simply never showed because it is one of
  the three Kitchen loads on the MC2E rather than the AADS. Nothing moved in any of the four tests,
  including the MC2E-backed entities, so this is unlikely rather than excluded.
- What an entry dump actually covers, given that it is demonstrably partial. The
  `entry dump omitted N join(s) that were high` message logs the evidence at debug level, so
  turning that on for a while would answer it without any new instrumentation.
- What the A/V dump's reproducible 0.35s internal pause is waiting for. The threshold above clears
  it either way, so this does not block step 1, but step 2 reads `a11` and needs to know whether the
  late frame carries it. One rerun with `-v` would say.
- Whether walking the zone cursor repeatedly disturbs the physical panels. It does not affect this
  step, which never moves the cursor, but it gates step 3.
- Whether externally originated A/V changes are visible to a registered slot at all, the audio
  counterpart of the Garage Sconces result for lighting. It decides whether the A/V bucket can ever
  be trusted between entries.
- The entity model for A/V, still undecided between six `media_player` entities and the
  panel-mirroring `select`/`select`/`number` arrangement. Step 1 does not depend on the answer.
