# Whole-house lighting control by impersonating a TSW-752

**Proven end to end on 2026-09-02.** Registering as a physically disconnected TSW-752 touch panel
gives read and write access to every lighting load in the house, with load feedback, scene feedback,
and working keypad LED synchronisation, and it requires no change to either Crestron program.

This is the route that closes the control problem. Every other candidate was eliminated first, and
those eliminations are recorded in [crestron-xpanel-control-path.md](crestron-xpanel-control-path.md)
and [crestron-aads-slot-control-path.md](crestron-aads-slot-control-path.md).

## Why this route was not obvious

It had already been tried once and recorded as a failure. The 2026-08-31 session unplugged a panel,
registered on AADS `IP-ID 0x11`, saw nothing, and wrote it down as silent. That row sits in the
retracted table in
[crestron-eisc-join-discovery.md](crestron-eisc-join-discovery.md#what-was-ruled-out), because the
CIP client used for it had three decoding bugs and produced a proven false negative on MC2E
`IP-ID 0x03` in the same pass.

Silence on a panel slot is also uninformative in a way silence on an app slot is not. Panel projects
were understood to be write-only for lighting, so a listen-only test on a panel slot could not
distinguish a dead slot from a live one. The test had to be a write test, and a write test needs the
join numbers first, which is where the earlier attempt stopped.

## Getting the join map without pressing anything

The panel stores its own compiled VT Pro-e project, and the panel's CTP console will hand it over.
This matters because the alternative, discovering joins by pressing them, means guessing next to an
alarm interface.

The TSW-752 runs the same plain-text console on TCP 41795 that the processors do, with no password,
and it honours `XGETFILE`. `mac/ctp_getfile.py` in the CresnetMon repo already speaks that protocol;
it needs only `--host`.

```
DIR                     ->  \display\
DIR \display            ->  Favela-TSW752 v3.vtx, swf\
DIR \display\swf        ->  Environment.xml, 3583494 bytes
```

`Environment.xml` is the entire project as UTF-16 XML: 52 named pages, 204 buttons, every join
number in the clear. It took 705 seconds to pull at roughly five 1K XMODEM blocks per second, which
is the panel's flash read speed rather than the network's.

All four panels report the identical project, `Favela-TSW752 v3.vtz`. Panels 11, 12 and 14 were
loaded on 2019-11-15 and panel 13 on 2020-07-07, same name and version. The map below is therefore
common to all four.

`PROJECTINFO` on each panel is the cheapest way to confirm that before relying on it.

## The lighting map

Eight zone pages, each with eight buttons. A button's press join is fixed by the project; the label
it displays is a serial join the processor fills in at runtime, which is why no load name appears in
the panel project itself.

Zone selection, on `LIGHT-pg01-zn00-sel`:

| Join | Zone | Load block |
|---|---|---|
| `d992` | Dining | `d101`-`d108` |
| `d993` | Living Rm | `d121`-`d128` |
| `d994` | Kitchen | `d141`-`d148` |
| `d995` | Master Suite | `d161`-`d168` |
| `d996` | Entry | `d181`-`d188` |
| `d997` | Patio | `d201`-`d208` |
| `d998` | Modes | `d221`-`d228` |
| `d999` | Others | `d241`-`d248` |

Zone selection is not a prerequisite for control. Every load button has its own join, and pressing
one cold, with no page or zone join sent first, acts immediately. This was tested rather than
assumed.

The names below came from the processor's own state dump on registration, read as serial joins.

| Dining | | Living Rm | | Kitchen | | Master Suite | |
|---|---|---|---|---|---|---|---|
| `d101` | Table | `d121` | Pathway | `d141` | Range | `d161` | Bed Perimeter |
| `d102` | Powder | `d122` | West Seating | `d142` | Powder | `d162` | Hallway |
| `d103` | Perimeter | `d123` | Ambient | `d143` | Island | `d163` | Bed Diagonal |
| `d104` | Outdoor Kitchen | `d124` | East Seating | `d144` | Outdoor Kitchen | `d164` | Patio North |
| `d105` | North | `d125` | Perimeter | `d145` | Pathway | `d165` | Bath Perimeter |
| `d106` | Living Off | `d126` | Patio South | `d146` | Living Off | `d166` | Patio South |
| `d107` | South | `d127` | Powder | `d147` | Cabinet | `d167` | Bath Diagonal |
| `d108` | Area Off | `d128` | Area Off | `d148` | Area Off | `d168` | Area Off |

| Entry | | Patio | | Modes | | Others | |
|---|---|---|---|---|---|---|---|
| `d181` | Door | `d201` | Path | `d221` | Holiday | `d241` | North Sink |
| `d182` | Entry Center | `d202` | Night | `d222` | Security | `d242` | Security |
| `d183` | Home Perimeter | `d203` | Fiesta | `d223` | Vacation | `d243` | East Hall |
| `d184` | Entry Perimeter | `d204` | Patio (All On) | `d224` | Party | `d244` | Garage Sconces |
| `d185` | Garage Sconces | `d205` | Club | `d225` | Goodbye | `d245` | Pool Bath |
| `d186` | Patio South | `d206` | Outdoor Kitchen | `d226` | *(blank)* | `d246` | Home Perimeter |
| `d187` | Outdoor Kitchen | `d207` | Pool | `d227` | Good Night | `d247` | Outdoor Kitchen |
| `d188` | Patio North | `d208` | Area Off | `d228` | *(blank)* | `d248` | *(blank)* |

Three cautions about reading this as an entity list.

Names repeat across blocks. `Outdoor Kitchen` appears on five pages and `Patio South` on three.
These are one load surfaced on several room pages, which is ordinary for a Crestron interface and
would produce duplicate entities if mapped naively.

Not every button is a load. The Patio and Modes blocks are mostly scenes, and `Area Off` and
`Living Off` are group-off actions rather than loads.

The names are the AADS's, not the keypads'. `North Sink` on `d241` is the load a Studio keypad
button labels `Sink Area`. Confirmed by test, see below.

## The alarm collision

The DSC alarm keypad page reuses the Kitchen lighting joins. Every page in the project has
`DigitalJoinOffset` 0, so this is genuine reuse of one join space and not an artifact.

| Join | Kitchen meaning | Alarm meaning |
|---|---|---|
| `d141` | Range | Arm ToHome |
| `d146` | Living Off | **Fire** |
| `d147` | Cabinet | **Medical** |
| `d148` | Area Off | **Panic** |

`d130`-`d139` are the alarm keypad digits and `d140` is Arm ToAway. `d131`-`d133` also double as the
HVAC Run Schedules, Hold and Away Mode buttons. `d93` enters the alarm subsystem from the home page.

The panel signals which subsystem it entered on `d91` for Lights and `d93` for Alarm, and the AADS
program presumably gates the meaning of `d130`-`d148` on that. **That gating is inferred from the
panel project and has not been confirmed against the AADS program's logic.** Treat the whole range
as unsafe.

This costs nothing in practice. The Kitchen is the one zone already reachable by a safe route: the
MC2E XPanel at `IP-ID 0x03` drives five Kitchen loads on joins 21-35, documented in
[crestron-xpanel-control-path.md](crestron-xpanel-control-path.md). Use that and never send anything
in `d130`-`d148` or `d93` to a panel slot.

## What the tests showed

Panel 13 at `192.168.4.84` was physically unplugged, freeing AADS `IP-ID 0x13`. Registration
succeeded with status `0x03`, and the state dump identified the slot: `s11 = 'Studio'`.

Pool Bath, `d245`:

```
[  6.489] PRESS d245  05 00 06 00 00 03 00 f4 00
[  6.617] CHANGE d245 = 1 (was None)
[  6.651] CHANGE d227 = 0 (was 1)
[  6.684] CHANGE d225 = 0 (was 1)
```

The load came on, confirmed by eye. `d245` stayed high after we sent the release 120 ms later, so
the processor is driving it as feedback rather than echoing our packet. `d225` and `d227` are the
`Goodbye` and `Good Night` scene buttons, which cleared because a load came on underneath them.
They returned to 1 when the load was switched back off at the end of the session.

North Sink, `d241`, chosen because it has a keypad button visible from the same chair:

```
[  6.063] PRESS d241  05 00 06 00 00 03 00 f0 00
[  6.187] CHANGE d241 = 1 (was None)
```

The load came on **and so did the LED on the Studio CNX-B8 keypad `0x6D` button 0**, which
[crestron-eisc-join-discovery.md](crestron-eisc-join-discovery.md) records as the `Sink Area` button
for EISC join `d99`, CLX `0x71` channel 6.

That last result is the important one. A change injected at the panel layer travels the AADS, the
EISC, the MC2E and Cresnet, and the MC2E's keypad LED logic sits upstream of where we inject, so LED
synchronisation is inherited rather than reimplemented. Pool Bath had shown no LED response only
because Pool Bath has no keypad button anywhere in the house. Recorded and closed as
[issue #15](https://github.com/pdehlke/homeassistant/issues/15).

## What this corrects

**Panel slots are not write-only for lighting.** Load state and scene state both come back
unprompted. The narrower claim still holds: no panel or keypad in the house displays a brightness
level anywhere.

**The panels have no individual identity in their projects.** All four run the same file, so panel
identity is physical location only and cannot be read out of a recovered project. The slot does
report its room as a serial join at runtime, which is how panel 13 was identified as the Studio.

## Cost and consequences

One panel is held permanently. Home Assistant would keep a long-lived CIP client registered on that
IP-ID, and the panel it displaces never works again. That is acceptable only because the TSW-752s
are already slated for replacement; see [crestron-strategy.md](crestron-strategy.md).

The integration is a daemon rather than a translation layer. It holds a socket, answers heartbeats,
maintains the join state, and reconnects. That is a smaller and better understood job than the
alternative, which was hiring a Crestron programmer with D3 Pro and SIMPL access to widen an XPanel
symbol.

Reversibility is total up to the point of committing to it. Plugging the panel back in takes the
IP-ID away again and nothing else changes.

## Answered since

**There is no brightness on this slot, and there never was.** Settled 2026-09-02 from two
independent directions.

The panel project settles it without touching hardware. Every lighting load button carries a
`DigitalPressJoin` and an indirect text reference and nothing else; no analog join appears anywhere
near one. The whole project contains exactly two `AnalogFeedbackJoin` values, both on
`Liquid Gauge Horizontal` controls, and no slider, gauge or dimmer control type exists on any
lighting page. The panel has no dimmer interface to offer.

The live processor agrees. A read-only registration on `IP-ID 0x13` reported `2 analog, 2 non-zero`
for the entire slot: `a11 = 63242` and `a12 = 60`, which are the two audio gauges. There is no
per-load level join to read and none to write.

So the twenty-six loads reachable here are on/off only. This is consistent with the narrower claim
already recorded above, that no panel or keypad in the house displays a brightness readout: the
reason is that the lighting interface was never built with one. The four Kitchen loads on the MC2E
XPanel are the exception and do carry 16-bit level joins, which is now the only place in the house
where Home Assistant could offer a brightness slider truthfully.

**The AADS does not drop a silent client, at least not quickly.** Measured 2026-09-02: a registered
session on `IP-ID 0x13` was synced and then went completely silent, sending no heartbeats at all,
and was still connected and still receiving after 149 seconds. Registration through end of state
dump takes about 1.1 seconds, so reconnecting is cheap besides. Reconnect logic can be
unremarkable: heartbeat on the usual 15-second cadence out of politeness, reconnect on socket error
or an explicit disconnect, and re-seed state from the fresh dump rather than trusting anything
carried over.

## What is still open

- Which of the four panels to sacrifice. Room assignments are Primary Bedroom, Kitchen, Office and
  Guest Room per the descriptors, and panel 13 self-reports as Studio, so that list needs checking
  against the `s11` value each panel reports.
- The blank buttons, `d226`, `d228` and `d248`, report the literal string `(nothing)` rather than an
  empty serial. Harmless, but it means an empty label is not the test for an unpopulated button.
