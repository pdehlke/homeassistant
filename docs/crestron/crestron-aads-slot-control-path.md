# The AADS app-slot control path

## Status

**Tested and blocked on a read-only route, 2026-09-02.** The premise holds: the AADS's compiled
program does contain whole-house lighting. Both candidate slots were then registered listen-only
and both stayed completely silent while lights were operated from a wall panel. The slots are
page-gated, so the join map cannot be recovered by watching, and recovering it any other way means
writing joins to the one processor that also carries the alarm interface. Nothing has been written
to any processor. Details in [the 2026-09-02 test](#the-2026-09-02-test-and-what-it-showed).

**Superseded later the same day.** The question this document asks was answered by a different
slot on the same processor. A real TSW-752 panel slot, freed by unplugging the panel, gives
whole-house control with feedback and needs no program change. This document stays because the
app-slot result is a genuine negative worth not repeating, and because the reason it failed, page
gating, turned out to be specific to the phone project rather than a property of the AADS. See
[crestron-tsw-panel-control-path.md](crestron-tsw-panel-control-path.md).

It assumes the AADS is **not** being retired. Every other document in this directory treats the
AADS as a subsystem on its way out, which is why this route was never considered: a control path
that depends on the AADS looked like a dead end by definition. If the AADS stays, it stops being
one.

The question this answers: can we drive lights in rooms beyond the Kitchen the way
[crestron-xpanel-control-path.md](crestron-xpanel-control-path.md) drives the Kitchen, by
registering on an abandoned slot, with no programmer and no program change?

## The premise

The MC2E's XPanel at `Slot-05.IP-ID-03` works because it is a defined but unoccupied user-interface
slot whose joins are already wired to real logic. Register on it over CIP, press a join, and the
processor does the rest. Its only limit is coverage: it reaches five Kitchen loads and nothing else.

The AADS has slots of the same kind. If any of them carries lighting for other rooms, the same
trick works there.

## The candidate slots

From [`dumps/aads-favela-v4.dsc.txt`](dumps/aads-favela-v4.dsc.txt):

| Slot | Type | Verdict |
|---|---|---|
| `IP-ID 0x15` | Crestron App | **Candidate.** Unoccupied, project `Favela-iPhone v1` |
| `IP-ID 0x16` | Crestron App | **Candidate.** Unoccupied, same project |
| `IP-ID 0x11`-`0x14` | TSW-752 | Fallback. Live panels; claiming one costs a working panel |
| `IP-ID 0x51` | CEN-IDOC | Rejected. Offline, but an audio-source symbol with no lighting joins |
| `Slot 5, ID E1`/`E2` | CHV-TSTAT | Rejected. Dead thermostat definitions on Cresnet, not a UI slot |
| `Slot 5, ID 0A` | ST-IO | Rejected. Relay and contact I/O, unrelated to lighting |

`0x15` and `0x16` identify themselves as `Favela-iPhone v1`, the previous homeowner's phone
project. It runs on no device the current owner holds, so claiming a slot displaces nothing. That
is the same condition that made MC2E `IP-ID 0x03` usable, established in
[crestron-eisc-join-discovery.md](crestron-eisc-join-discovery.md).

## Why the earlier "silent" result did not close this

Both slots were tested on 2026-08-31 and recorded as silent, carrying menu labels only. That test
ran on the `cip_xpanel.py` build with three decoding bugs, since fixed: multi-join digital,
multi-join analog, and serial datatype `0x15`.

The same bugs produced a false negative on MC2E `IP-ID 0x03`, which turned out to be neither silent
nor unwired. And the specific failure mode matters here: a slot whose output is menu labels is
carried on serial joins, which is exactly the decoder path that was broken. "Menu labels only" is
as likely to be an artifact as a finding.

Both slots were therefore unproven rather than cleared. The corrected table is in
[crestron-eisc-join-discovery.md](crestron-eisc-join-discovery.md#what-was-ruled-out).

**Resolved 2026-09-02.** The re-test was run with the fixed decoder and reproduced the original
result exactly. The 2026-08-31 reading was accurate about what arrives on these slots. It was
only its significance that was misjudged: menu labels are what a page-gated slot is supposed to
send before it has asked for anything, so the observation never distinguished an unwired slot from
a gated one, and still does not.

## Why write-only stops being a defect

The finding that retired the panel layer as an option was that it is write-only for lighting: the
TSW-752 panels send commands and display no state. That was disqualifying when the goal was an
*observation* point, and it is why the EISC won that argument.

This proposal wants a *control* point. Write-only is not a defect for that. It is the requirement.

State would come from paths that already work and are unaffected: the MC2E XPanel at `IP-ID 0x03`
for Kitchen loads, and the passive Cresnet tap for whole-house `1D` command frames. The result is
two interfaces rather than one clean one, and it needs no cooperation from Crestron.

## Evidence the panel layer reaches past the Kitchen

Two loads outside the Kitchen are already confirmed as touch-panel-originated:

| Load | Module and channel | EISC join | Source |
|---|---|---|---|
| Pool Bath | `0x72` ch6, level `FF` | `d103` | TSW-752 touch panel |
| Living Room Pathway | `0x70` ch4 and `0x71` ch3, level `C3` | - | TSW-752, record 3 |

Pool Bath comes from the confirmed join map in
[crestron-eisc-join-discovery.md](crestron-eisc-join-discovery.md). Living Room Pathway is record 3
in [cresnet-frame-decode.md](cresnet-frame-decode.md), whose whole point was that a touch panel
press reaches the bus by a different route than a keypad press.

Both travel TSW-752 to AADS, across the EISC to the MC2E, then out over Cresnet to the CLX modules.
So the AADS already holds whole-house lighting commands wired into its panel projects. The open
question is only whether an *app* slot exposes them, or some subset.

## What the AADS program holds for lighting

Confirmed 2026-09-02 by retrieving `Favela v4.bin` and running `strings` over it. The program has a
single `Lights` block at symbol path `S-7.17.1` containing 61 name entries, 42 of them unique. It
is emphatically not one room.

**Loads.** Table, Powder, Perimeter, Outdoor Kitchen, North, South, Pathway, West Seating, East
Seating, Ambient, Patio North, Patio South, Range, Island, Cabinet, Bed Perimeter, Bed Diagonal,
Bath Perimeter, Bath Diagonal, Hallway, Door, Entry Center, Home Perimeter, Entry Perimeter, Garage
Sconces, North Sink, East Hall, Pool Bath, Living Off, Area Off.

**Scenes.** Path, Night, Fiesta, Patio (All On), Club, Pool, Holiday, Security, Vacation, Party,
Goodbye, Good Night.

Three independent cross-checks land. Island, Range, Pathway, Powder, and Cabinet are exactly the
five Kitchen loads the MC2E XPanel drives on joins 21-35. Entry Center is EISC join `d58` and Pool
Bath is `d103`, both confirmed on 2026-08-31. The scene set is the AADS's own and differs from the
MC2E's eight, `A-Welcome` through `H-Entertain`.

This proves the AADS program holds whole-house lighting logic. It does not yet prove those loads
are exposed on an app slot, which is what step 2 tests.

One structural caution supports the reduced-function-set worry below. In the program's device
block, each TSW-752 slot carries three sub-slots (`IP-ID-11`, `IP-ID-11.2`, `IP-ID-11.3`) while
`IP-ID-15` and `IP-ID-16` carry two, with `Favela-iPhone v1` named at `Slot-01`. The app slots are
built differently from the wall panels.

## The 2026-09-02 test and what it showed

Both slots were registered listen-only with `cip_xpanel.py`, which sends only the registration
handshake, the update request, the end-of-query ack, and heartbeats. It has no join-write path at
all; that lives in `poc_joinpress.py`. So the test could not press a join even by accident, which
is why it had to come first.

On registration each slot returns the same thing, and it is a whole-house menu rather than a
Kitchen one:

| Join | Value |
|---|---|
| `s10` | `Kitchen` |
| `s100`-`s128` | A/V source list, `iPod` through `Device 29` |
| `s129`-`s131` | `Climate Zones`, `South HVAC`, `North HVAC` |
| `s140` | `Lights` |
| `s142` | `Alarm` |

Beyond the labels there is almost nothing: `5 digital joins reported, 5 high; 2 analog, 2 non-zero;
140 serial`, with digitals high at 41, 43, 47, 52, 1001 and analogs `a11 = 57735`, `a12 = 60`. Both
slots identify as `Favela-iPhone v1`, confirming the `.dsc` reading.

Then a 300-second listen on `0x15` and `0x16` simultaneously, while Pool Bath, Entry Center, and
Entry Perimeter were switched off from the Studio TSW-752:

```
aads-15-watch.txt: [300.474] 0 changes seen after sync
aads-16-watch.txt: [300.145] 0 changes seen after sync
```

Not one join update on either slot. The result is not a tooling artifact: `record()` logs a
`CHANGE` line the instant any value differs, and both listeners set `synced` at 0.9 seconds when
the processor sent end-of-query, so both were armed minutes before anything was pressed.

**The reading is page-gating.** The AADS sends a registered slot its menu and then goes quiet. A
panel has to signal which room and which subsystem it is showing before the processor starts
feeding it state. That is ordinary Crestron practice and it is the opposite of how the MC2E's flat
XPanel behaves, which is exactly why the Kitchen map fell out of `IP-ID 0x03` in an afternoon and
why nothing falls out of `0x15`. The contrast is visible in a single line of each state dump: the
MC2E reports 42 digital joins high, the AADS reports 5.

**What it does not show is that the `Lights` page is unwired.** A gated slot and a dead slot look
identical from outside. Separating them means writing the page-select joins, and no read-only
method of learning which joins those are has survived: step 1 established the AADS carries no
`pressNN` naming, and this test establishes that watching yields nothing. That leaves guessing,
on the processor whose interface spans eight alarm partitions, which
[the safety rule](crestron-alarm-open-questions.md#the-safety-rule) forbids.

## The risk: this is not the MC2E

**Do not carry the MC2E's safety finding across.** That finding was specific and was proven by
searching the retrieved MC2E binary, which contains zero occurrences of alarm, Apex, zone, motion,
siren, passcode, panic, or intrusion. On the MC2E the worst outcome of pressing an unknown join is
that a light changes.

The AADS is the opposite case, and the retrieved program makes it concrete. Its alarm integration
includes `S2_DSC_PowerSeries_Virtual_Keypad_Feedback_v1_1` and eight instances of
`S2_DSC_PowerSeries_Partition_Control_v1_0`, so the interface carries a virtual keypad across eight
partitions. A wrong press there can be a keypad digit or a partition command.
`crestron-eisc-join-discovery.md` separately records that this same app interface exposes an
`Alarm` subsystem alongside the `Lights` menu label.

**The join-sweep that mapped the Kitchen in an afternoon must not be repeated here.** Register
listen-only, identify every join by name before writing to it, and never sweep a range. Alarm work
is explicitly phase 2 for this house, gated on lighting working first; blundering into it by
pressing joins inverts that ordering in the worst possible way. Full rule in
[crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#the-safety-rule).

## Test plan, in strict order

1. ~~Retrieve and read the AADS program before pressing anything.~~ **Done 2026-09-02.**
   `Favela v4.bin`, 1,144,832 bytes, pulled with `ctp_getfile.py` against the CTP console on TCP
   41795. It confirms a single `Lights` block at symbol path `S-7.17.1` holding 42 unique
   whole-house load and scene names, which is the evidence this proposal needed. One technique did
   not transfer: the AADS uses no `pressNN` join naming, so the MC2E's trick of reading a join map
   out of the binary by number does not work here, and join identification has to come from step 2.
   See [the lighting inventory](#what-the-aads-program-holds-for-lighting).
2. ~~Register on `0x15` listen-only, with the fixed decoder.~~ **Done 2026-09-02, negative.** Run
   on `0x15` and `0x16` together for 300 seconds while Pool Bath, Entry Center, and Entry Perimeter
   were switched from the Studio TSW-752. Zero changes on both. See
   [the 2026-09-02 test](#the-2026-09-02-test-and-what-it-showed).
3. ~~Only then consider writing, and only to joins identified by name in step 1.~~ **Blocked.**
   Step 1 found no join naming and step 2 found no observable joins, so there is no way to identify
   a join by name before writing to it. Writing now would be the sweep the safety rule forbids.
4. ~~If `0x15` is genuinely empty, repeat with `0x16`.~~ **Done in the same run, same result.** A
   TSW-752 slot is not a way around this: claiming one costs a working panel and it would be
   page-gated identically. **The second half of that was wrong.** A TSW-752 slot is not page-gated,
   and claiming one is exactly the way around this. It does still cost a working panel.

## What would kill this

Written before the test, and one of them landed:

- **This is what happened.** The slots are page-gated, so no join map can be read out of them
  passively, and no read-only route to the join numbers remains.
- The app slots carry a phone project, which may expose a deliberately reduced function set
  compared with the wall panels. It may reach fewer rooms than a TSW-752 does, or none. Still
  untested, and now untestable without writing.
- The `Lights` menu label may turn out to be exactly what the original test said: a page that was
  designed and never connected to a subsystem. Still open for the same reason.
- Lighting joins on the AADS may be inseparable from alarm joins in a way that makes writing to the
  slot unacceptably risky regardless of coverage. **Half landed.** On the panel project the Kitchen
  block `d141`-`d148` collides with Arm ToHome, Fire, Medical and Panic. The other seven zones are
  clean, and the Kitchen already has a safe route on MC2E `IP-ID 0x03`, so it is survivable rather
  than disqualifying.

The obvious fallback was pulled the same afternoon and it closed too. MC2E `IP-ID 0x03` was
watched listen-only while the same three loads were switched from the same panel, and it reported
nothing; a control test with a Kitchen load then proved the slot does mirror wall-panel activity,
which turns that silence into a real negative rather than an ambiguous one. The `101-Kitchen`
boundary holds for observation as well as control. See
[crestron-xpanel-control-path.md](crestron-xpanel-control-path.md#the-slot-mirrors-the-wall-panels).

That returned the whole question to
[crestron-xsig-programmer-scope.md](crestron-xsig-programmer-scope.md) and a programmer, and it
stayed there for about an hour. The panel-slot route then removed the programmer from the control
path entirely. Whole-house *observation* already worked through the passive Cresnet tap and its `1D`
frames; whole-house *control* now works too, through a slot that costs one touch panel.

## Loose end

The AADS static IP table in [`dumps/aads-favela-v4.dip.txt`](dumps/aads-favela-v4.dip.txt) lists
the MC2E at `192.168.1.11`, while the MC2E actually lives at `192.168.4.59`. The live EISC
connection is `ONLINE` regardless, so the running configuration has clearly overridden the static
entry. It is a leftover from an earlier subnet and is noted here only so it is not mistaken for a
second processor.
