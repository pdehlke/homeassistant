# The Home Assistant to Crestron lighting bridge

The daemon that connects Home Assistant's thirty `light.*` entities to the real lighting
loads, using the control path proven in
[crestron-tsw-panel-control-path.md](crestron-tsw-panel-control-path.md).

Written and deployed 2026-09-02. **Live: both links registered, all thirty lights bound to
it, driving real loads.** See [Status](#status) for exactly what is proven and what is not.

## What it is

A Home Assistant custom integration, `crestron_cip`, living in the CresnetMon repo at
`custom_components/crestron_cip/` and deployed by SFTP to `/config/custom_components/`.

It holds two long-lived CIP sessions, keeps a live picture of every lighting load's state, and
exposes that state as entities plus discrete on/off as services.

```
HA light.turn_on
  -> template light action: crestron_cip.turn_on {load: office_pool_bath}
    -> bridge: is d245 already high? yes -> no-op. no -> press d245, await confirm
      -> AADS -> EISC -> MC2E -> Cresnet -> CLX dimmer, and the keypad LED
  <- feedback d245 = 1
  <- binary_sensor.crestron_office_pool_bath
    <- light.office_pool_bath
```

The keypad LED is inherited rather than implemented. The injection point sits upstream of the
MC2E's LED logic, which is what closed [issue #15](https://github.com/pdehlke/homeassistant/issues/15).

## Why an integration rather than a translation layer

The job is not request/response translation. It is holding a socket, answering heartbeats,
maintaining join state, and reconnecting, for as long as Home Assistant is up. That is a daemon,
and a Home Assistant custom integration is a daemon that already has a lifecycle, a config
mechanism, an entity model and a logger.

A `command_line`-style approach was rejected on arithmetic rather than taste: registration plus
state dump takes about 1.1 seconds, so a per-command reconnect would put a second of latency on
every light switch and would re-register on the AADS dozens of times an hour.

## Structure

| File | Role |
| --- | --- |
| `const.py` | the load table, and the forbidden-write set, validated at import |
| `cip.py` | asyncio CIP client: framing, registration, heartbeat, decode, reconnect |
| `bridge.py` | join state, alias resolution, discrete on/off over toggle, write guard |
| `binary_sensor.py` | one feedback entity per load, one per link |
| `__init__.py` | YAML setup, service registration |

`cip.py` is a rewrite of `mac/cip_xpanel.py` onto asyncio, not an import of it: the
proof-of-concept client is blocking and Home Assistant cannot host a blocking socket loop. The wire
format is unchanged and the tests assert against the exact frames recorded in the live transcripts,
so a codec change that still round-trips but no longer matches the wire fails.

## The two decisions that shaped it

Both are recorded as ADRs because they are the parts a future reader would otherwise have to
reconstruct.

[ADR 0066](../adr/0066-crestron-bridge-needs-two-cip-connections.md): two connections, because the
DSC alarm keypad shares `d130`-`d148` and three Kitchen loads have no join outside that range.

[ADR 0067](../adr/0067-discrete-on-off-synthesised-in-the-bridge.md): discrete on/off is
synthesised in the daemon, because the buttons are toggles and doing it in a template light's
action list would race against wall panels.

## Safety

The forbidden set is `range(130, 149)` plus `93`, matching `poc_panelpress.py`. It is enforced in
two places on purpose: `const._validate()` rejects a table containing a forbidden canonical join at
import time, so a bad entry fails at Home Assistant startup rather than lying dormant until someone
turns that light on, and `bridge._guard()` checks again immediately before bytes reach the wire.

The write surface is exactly the twenty-six canonical AADS joins plus, for the three Kitchen loads
that still need it, the MC2E joins. Nothing else is ever sent. `d91`, the Lights subsystem-entry join, was considered as a
way to make the AADS's interpretation of the shared range explicit and deliberately not used: the
bridge never writes that range, so `d91` buys no safety while changing processor state in a way
that has not been characterised.

Receiving a forbidden join is expected and fine. Powder reports on `d142` and Outdoor Kitchen on
`d144`, both inside the range. Only writing is refused.

## Load table

Twenty-nine loads. Twenty-six on the AADS panel slot, three on the MC2E XPanel, together covering
forty-one of the forty-two load buttons in
[crestron-load-room-worksheet.md](crestron-load-room-worksheet.md). Holiday (`d221`, the Modes
page's "Holiday" button) joined 2026-09-06: categorised as a scene in the original worksheet pass,
reclassified once pde traced it physically to a real fixture. See
[Holiday: a real load hiding on the Modes page](#holiday-a-real-load-hiding-on-the-modes-page)
below. `outside_home_perimeter` left the same day, folded into `entry_door` as an alias rather than
a load of its own; see
[Home Perimeter was never a real load either](#home-perimeter-was-never-a-real-load-either).

The one gap is `d145`, Kitchen's own "Pathway" button: it sits inside the forbidden alarm range and
has gone unreferenced by anything in the load table since `kitchen_pathway` moved onto its safe
alias, `d103`, in its place (2026-09-06, issue #22; see
[Kitchen Pathway moved off the MC2E entirely](#kitchen-pathway-moved-off-the-mc2e-entirely) below).
`d103` itself is not the gap, though it briefly was: reported 2026-09-05 and confirmed by pde, it
turned out to drive the same physical fixture as Kitchen Pathway rather than a load of its own, so
the `kitchen_perimeter` entity built against it was dropped instead of kept as a duplicate. It went
from untracked to `kitchen_pathway`'s own canonical join the very next day, once that same
discovery gave Pathway a safe way off the MC2E. `Load.aliases` can't express either relationship:
it only covers joins on one link, and both `kitchen_perimeter`'s old pairing and the current
arrangement span AADS and MC2E.

Where a load appears on several zone pages the canonical join is the one pressed and the rest only
report, which is how Outdoor Kitchen stays one entity across five buttons. Feedback on any alias
is mirrored onto the canonical join, so state has exactly one place to be read from.

The four Kitchen loads were identified 2026-09-03 (issue #18) and were wired the same as any
other load, though not all as simple toggles. Three (Cabinet, Kitchen Pathway, Range) are ordinary
toggles. Island's channel turned out to be a dimmer rather than a switch, with a separate on join
and off join rather than one toggled both ways; the `Load` dataclass's `press_on`/`press_off`
fields generalize that split for whatever the Phase 2 dimmer pass finds among the other MC2E
channels, all of which are dimmers. See
[crestron-xpanel-control-path.md](crestron-xpanel-control-path.md#kitchen-identification-resolved-2026-09-03)
for the full identification record. Kitchen Pathway no longer needs any of this: see
[Kitchen Pathway moved off the MC2E entirely](#kitchen-pathway-moved-off-the-mc2e-entirely) below.

## Status

**Live since 2026-09-02, at full coverage since 2026-09-03.** Both links registered, all lights
bound to it, driving real loads. Thirty loads at first; twenty-nine since 2026-09-05, when
`kitchen_perimeter` was dropped as a duplicate of Kitchen Pathway rather than a load of its own;
thirty again since 2026-09-06, when Holiday joined as a genuinely new load rather than a duplicate;
twenty-nine again later the same day, when `outside_home_perimeter` turned out to be the same kind
of duplicate `kitchen_perimeter` was, this time of `entry_door`.

Proven live:

- Both CIP sessions register, sync and hold. On first sync the bridge independently reproduced the
  read-only recon baseline: Garage Sconces high on both `d185` and `d244`, nothing else, which is
  the alias resolution working on real state.
- Writes reach the house. Pool Bath (`d245`), North Sink (`d241`), Patio North (`d164`/`d188`),
  Dining Room Powder (`d127` on, `d102` off) and Holiday (`d221`) were each switched on and off
  from Home Assistant and followed. So were all four Kitchen loads after identification, including
  Island's
  `press_on`/`press_off` split (join 27 to turn on, 29 to turn off) exercised through the real
  `light.turn_on`/`light.turn_off` services, not just the identification tooling.
- Idempotence holds against real hardware. A second `turn_on` on a load already on presses nothing;
  a second press would have turned the light off. Confirmed for both a toggle load and, offline,
  for Island's separate-join case.
- `light.turn_on` on the Home Assistant entity drives the load end to end, through the template
  light, the service, the bridge and the whole Crestron chain.

Established before deployment and unchanged by it:

- Registration through end of state dump takes about 1.1s.
- The AADS panel slot carries no per-load analog level join, so the bridge has no way to command a
  specific level for any of its twenty-six loads today. That is not the same as the loads
  themselves being on/off fixtures: all but four of the twenty-nine loads across both links are
  dimmer-capable, AADS ones included, not just the MC2E's Kitchen channels. Toggling one of those
  loads through the panel slot's single digital join recalls whatever level the load's own program
  logic treats as "on," which is not necessarily full brightness. Brightness is still out of scope
  pending the Phase 2 dimmer pass; `level_join` on the `Load` dataclass records what identification
  finds so that pass does not have to re-derive it.
- The AADS does not drop a client that stops answering heartbeats, at least not within 149s.
- Twenty-eight offline tests pass, covering the codec against recorded frames, the load table's
  safety invariants, and the toggle logic including idempotence, concurrency, alias resolution,
  refusal on unknown state, and the on/off-join split.

Still open:

- An externally-originated change has not been watched live. Garage Sconces proves the bridge reads
  a load it never touched, but no wall-panel or keypad press has been observed arriving while the
  bridge was running. Note that this cannot be told apart from a Home Assistant write after the
  fact: the template light derives its state from the feedback sensor, so the originating context
  is lost and `context_user_id` is `None` either way.
- Whether Island's on-join (27) recalls a fixed preset level or ramps proportionally to how long
  it's held. Not resolved during identification; see
  [crestron-xpanel-control-path.md](crestron-xpanel-control-path.md#kitchen-identification-resolved-2026-09-03).

## Powder needed its own on-join, like Island

Reported 2026-09-05: `light.turn_on` on Dining Room Powder lit the `binary_sensor` and confirmed
`d102` high within a second, same as `light.turn_off` always had, but the physical light did not
come on. That asymmetry ruled out a bad join, a guard rejection, and a stale template light in the
same session: pressing `d102` was proven, live, to reliably flip the AADS's own feedback for that
load in both directions, and the load table matched
[crestron-load-room-worksheet.md](crestron-load-room-worksheet.md) exactly. The cause was the gap
already on record above: Powder is dimmer-capable, like all but four of the twenty-nine loads, and `d102`
specifically recalls a level low enough to read as off. Pde confirmed live from real panels that the
Living Rm (`d127`) and Kitchen (`d142`) Powder buttons both turn it on dimmed, where `d102` does not.

`d142` is inside `FORBIDDEN_AADS_WRITE`, so it was never a candidate; `d127` was. Fixed the same way
Island was: `dining_room_powder` now carries `press_on=127`, leaving `join=102` as both the feedback
join and the off-join, unchanged from before. Deployed and confirmed live 2026-09-05: `light.turn_on`
presses `d127` and the light comes on dimmed, `light.turn_off` presses `d102` and it goes dark, both
watched directly on the fixture. Brightness itself is still out of scope pending Phase 2; this only
fixes on/off for one load whose "on" join happened to be a bad pick, the same way Island's did.

## Kitchen Perimeter was never a real load

Reported 2026-09-05: `light.kitchen_pathway` and `light.kitchen_perimeter` are the same physical
fixture, not two loads. `kitchen_perimeter` was built against `d103` ("Perimeter" on the Dining
page) on the strength of
[crestron-load-room-worksheet.md](crestron-load-room-worksheet.md)'s reading of the Pathway/
Perimeter naming collision as four separate loads, one pair per room. That reading was wrong for
the Kitchen half of the pair: `d103` drives the same fixture as `kitchen_pathway` (MC2E join 25),
confirmed by pde. It also retroactively explains the "occasionally unresponsive" pair noted during
Homie Dashboard's scenes-chip work (see
[homie-scenes-chip.md](../homie-dashboard/homie-scenes-chip.md)'s eleventh pass) — commanding one
join and reading the other's independent feedback looks exactly like flakiness.

`kitchen_perimeter` is removed from the load table rather than turned into an alias of
`kitchen_pathway`: `Load.aliases` only covers other joins on the same link, and this pair spans
AADS (`d103`) and MC2E (`kitchen_pathway`'s join 25), which the dataclass has no way to express.
`d103` is simply untracked now — still a real button on a real panel, just one with no HA entity
behind it, the same as any other physical control this project hasn't wired up. Removed from the
bridge, the `Dinner Lights` and `Dinner Only` light groups, the Visitors scene's entity list (both
the dashboard bubble and `script.scene_visitors`), and the "Dinner Lights" HA scene snapshot.

## Kitchen Pathway moved off the MC2E entirely

Done 2026-09-06 ([issue #22](https://github.com/pdehlke/homeassistant/issues/22), asked after pde
questioned whether the MC2E connection was still needed at all now that the AADS panel project
covers the same Kitchen buttons by name). It doesn't, not fully: Range (`d141`), Island (`d143`)
and Cabinet (`d147`) have no safe join anywhere else in the panel project, confirmed by
exhaustively walking every one of its 41 load buttons, so they still need the MC2E and the second
CIP connection stays. Pathway is the one exception. `d103`, the alias described directly above in
["Kitchen Perimeter was never a real load"](#kitchen-perimeter-was-never-a-real-load), was already
proven live on 2026-09-05 to drive Pathway's own fixture and sits outside `FORBIDDEN_AADS_WRITE`,
so it needed no new discovery, only wiring it in as `kitchen_pathway`'s canonical join instead of
leaving it untracked.

`kitchen_pathway` moved from `_MC2E_LOADS` (join 25) to `_AADS_LOADS` (join 103) in `const.py`.
Deployed the same way as every other live change here: backed up the running `const.py`, uploaded
under a temp name, MD5-verified byte-identical, atomic-renamed into place, `check_config` run
before restarting Home Assistant. Confirmed live afterward: `binary_sensor.crestron_kitchen_pathway`
now reports `link: aads, join: 103` instead of `link: mc2e, join: 25`, and a real `light.turn_on`
/ `light.turn_off` round trip through the Home Assistant entity flipped the feedback and the
template light exactly as it did on the MC2E, restoring the load to the `off` state it was found
in. Range, Island, Cabinet and one AADS load were spot-checked after the restart and came back
unaffected.

## Holiday: a real load hiding on the Modes page

The Modes page (`LIGHT-pg01-zn07`) was read as scene buttons across the board in the original
2026-09-02 worksheet pass, on the theory that a page named "Modes" holds macros rather than
individual loads. [Issue #19](https://github.com/pdehlke/homeassistant/issues/19) tested that
theory for Holiday, Security, Vacation and Party together by pressing each from a physical
TSW-752 and watching for any visible effect. None showed one, which left it open whether they were
dead in this installation, did something not visually obvious, or had non-independent feedback the
way Goodbye and Good Night's already-proven-derived indicators do.

pde traced Holiday specifically on 2026-09-06 and found a real, visible effect: it switches the
outdoor eave receptacles used for holiday lights. Reclassified from `scene` to `load` in
[crestron-load-room-worksheet.md](crestron-load-room-worksheet.md) on that basis, added to the
bridge as `outside_holiday` (`d221`, an ordinary single-join toggle, no aliases, the same shape as
`office_pool_bath`), and wired into Home Assistant as a Template Light the same way every other
load is, in the Outside area.

Confirmed live 2026-09-06: `light.turn_on` on `light.outside_holiday` pressed `d221`, the feedback
flipped within about two seconds, and pde confirmed the eave receptacles were physically on.
`light.turn_off` reversed both, confirmed off. A genuine independent toggle, not a derived
indicator like Goodbye or Good Night.

Deliberately left out of the Homie Dashboard's Visitors scene despite that bubble's "every light in
the house" design intent (see [homie-scenes-chip.md](../homie-dashboard/homie-scenes-chip.md)):
pde's call, on the basis that seasonal decorative lighting isn't what "every light on for guests"
means. Added to the Lights chip under Outside instead.

**Correction, 2026-09-07.** `d221`, the join Holiday presses, is also a DSC alarm zone
("Room 4 East Wins") on a panel page this project hadn't read yet when Holiday was wired. Nothing
about Holiday's own behavior changes on the strength of this alone; see
[crestron-alarm-zone-inventory.md](crestron-alarm-zone-inventory.md#d221-holidays-own-join-is-also-a-zone-join-and-it-is-actively-pressed)
and [crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#new-evidence-2026-09-07-the-zone-status-page-and-a-live-collision)
before touching Holiday or the alarm system again.

Security, Vacation and Party moved on independently after this section was first written. Party
turned out real too, driving Door, Entry Center, East Hall and the Primary Suite hallway, confirmed
physically the same way Holiday was. Security and Vacation are the opposite finding: watched
through Home Assistant across the full `light`/`binary_sensor`/`switch`/`alarm_control_panel`
entity set during a live press each, and neither moved anything at all, nor lit a garage dimmer LED
either. Whether they're dead or belong to the DSC alarm's own unmapped logic is still open. None of
the three are in the load table; see [issue #19](https://github.com/pdehlke/homeassistant/issues/19)
for the full record rather than this section, which is Holiday's alone.

## Home Perimeter was never a real load either

The same Foyer-keypad chase that resolved Party turned up a second, unrelated correction. The
bridge's `outside_home_perimeter` (AADS `d183`, alias `d246`) was never a distinct fixture: pde
found the Foyer keypad's actual "Home Perimeter" button and traced it to the same garage dimmer LED
as Door, then separately confirmed pressing `d183`/`d246` lights that same LED too. Same shape as
the Kitchen Perimeter mixup, different pair. `d183` and `d246` are now aliases of `entry_door`
rather than a load of their own.

The real Home Perimeter turned out to be a genuinely different problem than a mislabeled join.
Watching the bridge's own raw digital-join trace on the AADS while the Foyer button was pressed
showed nothing move except the Goodbye/Good Night "everything's off" tell, the signature of a real
load turning on and off with no join of its own visible on that connection. A Cresnet tap capture
(read-only, `mac/poc_foyer_tap.py` in CresnetMon) caught a clean, twice-only burst at the press
moments touching the Foyer keypad's own bus address (`0x67`) and device `0x74`, and a follow-up
SDEBUG capture scoped to `0x74` on the MC2E's console confirmed it directly: "Digital Join 3 is
High" / "Digital Join 3 is Low," six seconds apart, matching the press exactly.

`0x74` is a CLX-4HSW4, a non-dimming switch module rather than a dimmer, and the one lighting
module in the house's inventory that had never been tied to a fixture before this. Fitting, since
Home Perimeter is an exterior floodlight circuit, not something anyone dims.

This join cannot be added to the load table the way Kitchen Pathway's alias was. Every `Load` here
is a join inside the AADS's or MC2E's own program, reached over CIP; `0x74`'s Digital Join 3 is that
module's own internal Cresnet state, and nothing found here shows it relayed into either program's
join space, consistent with both live tests seeing nothing at all. Making it controllable from Home
Assistant needs new SIMPL program logic, the same category of fix issue #22's Phase B already named
for the Kitchen loads, not a code change here. See
[issue #23](https://github.com/pdehlke/homeassistant/issues/23) for the full trace and the options.

**Cleanup completed 2026-09-08.** The code fix above (`entry_door` gaining `183`/`246` as aliases,
`outside_home_perimeter` dropped from the load table) had been written and deployed but the
downstream Home Assistant and Homie Dashboard cleanup that follows from it, same as
[Kitchen Perimeter's](#kitchen-perimeter-was-never-a-real-load) removal from groups and scenes, had
not. Finished now: the orphaned `light.outside_home_perimeter` template light (permanently
`unavailable` once the bridge stopped feeding its backing `binary_sensor`) and the equally orphaned
`binary_sensor.crestron_outside_home_perimeter` entity registry entry are both deleted; the
`Visitors` scene script (`script.scene_visitors`) had `light.outside_home_perimeter` in its
`light.turn_on` target and no longer does; Homie Dashboard's `config.js` dropped it from the Lights
chip's Outside room and from the Visitors bubble's entity list, `HOMIE_ASSET_VERSION` bumped to
`20260908.1` to bust the tablet's cache, and `test/screen-a.test.cjs` updated for the new counts (34
lights and 33 Visitors entities both down by one). The still-uncommitted `custom_components/
crestron_cip/cip.py` diagnostic (a raw per-join debug log, added and explicitly marked "Temporary"
during this same investigation) was reverted rather than kept: its purpose was served once the
Foyer tap capture found the real join, and this project tears down debug instrumentation once used
rather than leaving it running by default. `mac/poc_foyer_tap.py`, the passive Cresnet-tap capture
tool that did find it, is kept as permanent tooling alongside its siblings in `mac/`.

## Two bugs worth remembering

**A service handler must be an `async def`, not a lambda returning a coroutine.** The first live
deploy registered the services as `lambda call: _call(...)`. Home Assistant decides how to invoke a
handler with `asyncio.iscoroutinefunction()`, a lambda fails that check, so HA ran it in an executor
thread, took the coroutine it returned and discarded it. Every service call returned HTTP 200 having
done nothing at all: no press, no error, no state change. The only trace anywhere was a
`coroutine 'async_setup.<locals>._call' was never awaited` RuntimeWarning in `system_log`. It was
found by checking the recorder first, which showed no transition at all and so ruled out "pressed
but mishandled the feedback". A source-level test now fails if `async_register` is handed a lambda.

**A light bound to a feedback entity needs an availability template.** Binding `state` to
`is_state('binary_sensor.crestron_<load>', 'on')` makes the light read `off` whenever that sensor is
`unavailable`, which is a lie in two cases that matter: the four unmapped Kitchen loads, and any CIP
link outage, where all twenty-six AADS loads would claim the house is dark. Fixed by setting
`availability` to `has_value('binary_sensor.crestron_<load>')`, which is false for both unknown and
unavailable.

## Deploying

```
put custom_components/crestron_cip/*.py  /config/custom_components/crestron_cip/
put custom_components/crestron_cip/manifest.json  /config/custom_components/crestron_cip/
put custom_components/crestron_cip/services.yaml  /config/custom_components/crestron_cip/
```

Then add one line to `configuration.yaml`:

```yaml
crestron_cip:
```

Hosts and IP-IDs default to the AADS at `192.168.4.61` on `0x13` and the MC2E at `192.168.4.59` on
`0x03`, and can be overridden per link. Restart Home Assistant; the integration is YAML-configured
and has no config flow, because its addressing is fixed by physical hardware and there is exactly
one house.

Back up `configuration.yaml` first. The SSH & Web Terminal add-on must be running.

Home Assistant caches the `custom_components` listing at startup, so a `check_config` run before
the restart reports `Integration 'crestron_cip' not found` as a warning. That is expected and not a
sign the manifest is wrong.

**`IP-ID 0x13` holds one client at a time.** While the bridge is running, the proof-of-concept
tools in `mac/` cannot register on the same slot, and plugging panel 13 back in takes the slot
away from Home Assistant.
