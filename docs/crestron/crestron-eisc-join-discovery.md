# EISC join discovery: reading the lighting control interface that already exists

## Status

Working method, three lights mapped, 2026-08-31. The MC2E and the AADS are linked by an Ethernet
Intersystem Communications symbol, and **every lighting command and every lighting state change
crosses it**, in both directions, with authoritative feedback. The processor's own `SDEBUG` console
command prints that traffic in interpreted form with join numbers and timestamps.

That makes join discovery a passive, repeatable procedure rather than a reverse-engineering
problem. Nothing is written to any processor and nothing is pressed. See
[Method](#method-how-to-reproduce-this).

What is not solved is *use*. The EISC slot is occupied by the AADS and cannot simply be taken over.
See [The use problem](#the-use-problem).

**Update, 2026-09-01.** Use is partly solved, by a route this document dismissed. The unoccupied
XPanel at MC2E IP-ID `0x03` gives a working read *and* write path with no reprogramming at all,
covering the Kitchen's five loads. Read
[crestron-xpanel-control-path.md](crestron-xpanel-control-path.md) alongside this document; where
the two disagree, that one is correct. The discovery method below is unaffected and remains the way
to map the rest of the house.

## Verified topology

Established by read-only `VER`, `IPTABLE`, `WHO`, and `TYPE` on each processor's console.

```text
TSW-752 panels  ->  AADS (192.168.4.61)  ->  MC2E (192.168.4.59)  ->  Cresnet  ->  CLX modules
   IP-ID 11-14        as IP-ID 05, "Exports"          lighting bus
```

The touch panels have no connection to the MC2E at all. A panel's own IP table lists exactly one
entry, the AADS. This confirms, from each device's own report rather than by inference, the
architecture recorded in [crestron-migration.md](crestron-migration.md).

| IP-ID | Device | Address | Status |
|---|---|---|---|
| 05 | EISC to MC2E | 192.168.4.59 | ONLINE |
| 11 | TSW-752 | 192.168.4.124 | ONLINE |
| 12 | TSW-752 | 192.168.4.100 | ONLINE |
| 13 | TSW-752 | 192.168.4.84 | ONLINE |
| 14 | TSW-752 | 192.168.4.83 | ONLINE |
| 15, 16 | Crestron App | - | OFFLINE, unused |
| 51 | CEN-IDOC | - | OFFLINE |

**IP-IDs are hex.** The `16` in that table is `0x16`, not decimal 16, and `51` is decimal 81.
Passing decimal produces a misleading "IP-ID does not exist" refusal.

The MC2E separately has an XPanel definition at its own IP-ID `0x03`, unoccupied, left over from an
eControl PC panel that no longer exists. Unoccupied is not the same as dead: a CIP client can
register on it, and doing so gives a working control path to the Kitchen's lighting
([crestron-xpanel-control-path.md](crestron-xpanel-control-path.md)).

## Confirmed join map

Captured 2026-08-31 18:51-18:52 with the EISC debug output and a Cresnet bus sniffer running
simultaneously, so each row is witnessed on both sides of the processor at once.

| EISC join | Light | CLX module | Channel | Keypad | Button |
|---|---|---|---|---|---|
| `d58` | Entry Center | `0x71` | 1 | Foyer `0x67` | 6 |
| `d99` | Sink Area | `0x71` | 6 | Studio `0x6D` | 0 |
| `d103` | Pool Bath | `0x72` | 6 | driven from a touch panel | - |

`d58` was mapped on the first attempt on a keypad, room, and channel never previously observed,
which is the evidence that the method generalises rather than fitting two lucky cases.

Joins `89` and `91` are probably all-off indicators tracking the same condition as the keypads'
"Good Bye" LED. They moved inversely with `d99` in an 18:43 capture and did not move at all in the
18:52 one. The house owner reports the Sink Area light was left on and never turned off, which
accounts for the later events in that window. It does not obviously account for the first
transition at 18:51:53, where the bus shows Sink Area going from off to on and neither indicator
moved. One clean on/off cycle with the whole house verifiably dark will settle it.

## Protocol semantics

`CTX` is MC2E to AADS. `CRX` is AADS to MC2E.

```text
18:52:04  CRX  Digital Join 99 is High.     panel-side press
18:52:04  CTX  Digital Join 99 is High.     MC2E reports the resulting state
18:52:04  CRX  Digital Join 99 is Low.      release
```

Two properties matter more than the specific numbers.

The joins are **bidirectional on the same number**. The receive direction carries a momentary press,
high then low, which the MC2E treats as a toggle. The transmit direction carries the resulting
level as state.

**Authoritative feedback already exists.** The touch panels are fire-and-forget and display no
state, which is a property of the panel projects rather than of the system. The MC2E publishes
lighting state on the EISC on every change, including changes originating at a physical keypad with
no panel involved:

```text
18:51:53  CTX  Digital Join 99 is High.     keypad press, no panel in the path
18:51:59  CTX  Digital Join 99 is Low.
```

This is state originating from real device state rather than echoed from a command, which is
exactly the property [crestron-xsig-programmer-scope.md](crestron-xsig-programmer-scope.md)
requires and assumes must be built.

## Method: how to reproduce this

Tooling lives in the CresnetMon working tree at `mac/`, in `pdehlke/CresnetMon` on branch
`macos-port-python`. See that repo's `HANDOFF.md` for the full session record.

Enable the debug print on the MC2E, scoped to the EISC slot and nothing else:

```text
SDEBUG -DON E05        sets the flag on Slot-05.IP-ID-05
SDEBUG -RXION          interpreted receive
SDEBUG -TXION          interpreted transmit
SDEBUG -RXF1 / -TXF1   human readable
SDEBUG -STON           timestamps
SDEBUG -S1             show current settings, to confirm
```

and turn every one of them off afterwards. `mac/` has a wrapper that does this with the teardown in
a `finally` block, so a crash or timeout still clears the flags. Verify with `SDEBUG -S1`, which
should report "No Devices being debugged."

Run a Cresnet sniffer at the same time, then press one keypad button per light. Each press yields:

- the join number, from the EISC output
- the CLX module and channel, from the bus `1D` command frame
- the keypad and button index, from the bus frames `02 00 <button> 00` to the master and
  `<keypad> 00 <button> 00` back to the keypad's LED

Start with the house all-off so that the all-off indicators are observable in the same pass.

### Cautions

`SDEBUG` is console printing on a 2009 processor running a live house. Scope it to `E05`, keep
windows short, and turn it off between rounds. The link is silent at idle, verified over two dry
runs, so output volume is not a concern when scoped this way.

Do not sweep joins by pressing them. The same panel interface exposes an `Alarm` subsystem, and the
digital join behind the `Lights` menu label is unknown, so guessing at it means guessing next to the
alarm. Alarm work is explicitly phase 2, gated on lighting control working first, per the house
owner.

## What was ruled out

Recorded so nobody repeats it. Each of these was tested by registering a CIP client against the
slot and watching while lighting changes were made that a bus sniffer independently confirmed.

**Corrected 2026-09-01. Do not rely on this table.** The CIP client used for these tests had three
decoding bugs, since fixed. Every "silent" result below is either a proven false negative or
untrustworthy, and the conclusion drawn from them was wrong. Kept here because the table was cited
elsewhere and because a retracted finding is more useful than a deleted one. Correction recorded in
[crestron-xpanel-control-path.md](crestron-xpanel-control-path.md).

| Slot | Recorded 2026-08-31 | After the decoder fix |
|---|---|---|
| MC2E IP-ID `0x03`, XPanel | Silent. Not wired to lighting. Carries a leftover scheduling page. | **False negative.** Reports state promptly and in detail, accepts writes, and drives five Kitchen loads. |
| AADS IP-ID `0x15`, `0x16`, Crestron App | Silent. Menu labels only, including a `Lights` entry whose subsystem was never connected. | Unproven. Never re-tested with the fixed decoder. |
| AADS IP-ID `0x11`, a real TSW panel slot | Silent. Panel freed by unplugging it. | Unproven. Never re-tested with the fixed decoder. |

The TSW-752 panel projects are write-only for lighting: they send commands and display no state.
That part stands, confirmed independently by the panels' own behavior. The stronger claim made here
originally, that listening at the panel layer cannot work at all, does not survive the `0x03`
result and is withdrawn. What remains true is narrower: the EISC is the only observation point so
far confirmed to carry whole-house joins, and `0x03` reaches one room.

The app slots identify themselves as `Favela-iPhone v1`, the previous homeowner's project. It is on
no device the current owner holds, so those slots can be used freely without displacing anything.
Their `South HVAC` and `North HVAC` entries are dead, since those units are no longer Crestron.

## The use problem

Discovery is solved. Use is not.

IP-ID 05 on the MC2E is held by the AADS. Displacing it would break audio and would also remove the
ST-IO's bus master, which is a hard dependency recorded in
[crestron-migration.md](crestron-migration.md#what-this-changes-in-the-plan).

Open options, none yet investigated:

1. Widening the XPanel at IP-ID `0x03`, which already carries the Kitchen and has defined but
   unwired joins above 35. This is a programmer question and sits inside the existing scope of
   work, but it is now a far better specified one: the transport works, the signals exist, the
   joins are known, and both directions are demonstrated.
2. Relay through the AADS, which already receives all of this and has two unused app slots. Those
   slots carry no lighting today, so this also needs a program change.
3. Cresnet injection, direct to the CLX modules, bypassing both processors. **Abandoned
   2026-09-01.** Transmission itself was proven, but the CLX modules ignore commands arriving
   outside their slot in the master's poll round, and a byte-perfect replay of the processor's own
   frames produced no light. Sustained injection makes all seven modules re-initialise, which is a
   fault response rather than obedience.

**Settled 2026-09-01: the end state is the IP route.** The Cresnet route is closed for the reason
in option 3. The IP route already works for the Kitchen with no program change at all, so the open
question narrows to how the other thirteen rooms reach a slot we can register on.

## What this changes in the programmer scope

[crestron-xsig-programmer-scope.md](crestron-xsig-programmer-scope.md) scopes a programmer to build
an XSIG interface exposing the signals Home Assistant needs. Two findings bear on it.

The unoccupied panel and app slots do not carry lighting state, so there is no client-side shortcut
at that layer. Three were tried and all were silent.

The EISC does carry it, in both directions, with feedback that originates from real device state.
The job may therefore be closer to exposing or duplicating an existing, working, already-wired link
than to designing an interface from nothing. The captures here are worth putting in front of
whoever scopes the work.

The document's arguments for a stable, documented, non-recycled join contract are unaffected. The
joins observed here are the existing program's internal numbering and carry no such guarantee.
