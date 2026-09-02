# The AADS app-slot control path

## Status

**Untested hypothesis, 2026-09-02.** Nothing here has been run. It is a proposal assembled from
evidence already gathered for other purposes, written down because it is a serious candidate route
and because the reasoning is easy to lose.

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

## Why the earlier "silent" result does not close this

Both slots were tested on 2026-08-31 and recorded as silent, carrying menu labels only. That test
ran on the `cip_xpanel.py` build with three decoding bugs, since fixed: multi-join digital,
multi-join analog, and serial datatype `0x15`.

The same bugs produced a false negative on MC2E `IP-ID 0x03`, which turned out to be neither silent
nor unwired. And the specific failure mode matters here: a slot whose output is menu labels is
carried on serial joins, which is exactly the decoder path that was broken. "Menu labels only" is
as likely to be an artifact as a finding.

Both slots are therefore unproven, not cleared. The corrected table is in
[crestron-eisc-join-discovery.md](crestron-eisc-join-discovery.md#what-was-ruled-out).

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

## The risk: this is not the MC2E

**Do not carry the MC2E's safety finding across.** That finding was specific and was proven by
searching the retrieved MC2E binary, which contains zero occurrences of alarm, Apex, zone, motion,
siren, passcode, panic, or intrusion. On the MC2E the worst outcome of pressing an unknown join is
that a light changes.

The AADS is the opposite case. It holds the Apex Destiny 6100 serial connection and the alarm
user-interface logic, and `crestron-eisc-join-discovery.md` already records that this same app
interface exposes an `Alarm` subsystem alongside the `Lights` menu label. The join-sweep that
mapped the Kitchen in an afternoon is not safe to repeat here.

Alarm work is explicitly phase 2 for this house, gated on lighting control working first. Blundering
into it by pressing joins on the AADS inverts that ordering in the worst possible way.

## Test plan, in strict order

1. **Retrieve and read the AADS program before pressing anything.** Use `ctp_getfile.py` against the
   CTP console on TCP 41795, the same method that worked on the MC2E. The manifest
   ([`dumps/aads-manifest.txt`](dumps/aads-manifest.txt)) names the file `Favela v4.bin`. Run
   `strings` over it and look for join names. The MC2E binary named its press joins `press21`
   through `press95`, so the same convention should reveal the AADS's lighting joins by name, and
   more importantly reveal which joins are alarm.
2. **Register on `0x15` listen-only, with the fixed decoder.** Watch while someone operates lights
   from a TSW-752. If the slot mirrors panel activity, the join map falls out with nothing pressed.
3. **Only then consider writing**, and only to joins identified by name in step 1. Never sweep.
4. If `0x15` is genuinely empty, repeat with `0x16` before considering a TSW-752 slot.

## What would kill this

- The app slots carry a phone project, which may expose a deliberately reduced function set
  compared with the wall panels. It may reach fewer rooms than a TSW-752 does, or none.
- The `Lights` menu label may turn out to be exactly what the original test said: a page that was
  designed and never connected to a subsystem.
- Lighting joins on the AADS may be inseparable from alarm joins in a way that makes writing to the
  slot unacceptably risky regardless of coverage.

Any of those returns the whole question to
[crestron-xsig-programmer-scope.md](crestron-xsig-programmer-scope.md) and a programmer.

## Loose end

The AADS static IP table in [`dumps/aads-favela-v4.dip.txt`](dumps/aads-favela-v4.dip.txt) lists
the MC2E at `192.168.1.11`, while the MC2E actually lives at `192.168.4.59`. The live EISC
connection is `ONLINE` regardless, so the running configuration has clearly overridden the static
entry. It is a leftover from an earlier subnet and is noted here only so it is not mistaken for a
second processor.
