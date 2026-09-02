# Alarm integration: open questions, parked

## Status

**Parked 2026-09-02, deliberately.** Lighting comes first and the alarm is picked up only if and
when lighting is finished. Nothing here is a task. It is written down so the findings are not lost
and so nobody re-derives them.

One thing in this document stays in force while it is parked: the safety rule below. Everything
else can wait.

## The safety rule

This is the only alarm content that belongs in day-to-day lighting work.

**Do not press unknown joins on the AADS.** Not to explore, not to map, not "just one to see."

The reasoning is specific rather than general caution. On the MC2E the join-sweep that mapped the
Kitchen in an afternoon was safe, and provably so: its compiled program was retrieved and searched
and contains zero occurrences of alarm, Apex, zone, motion, siren, passcode, panic, or intrusion.
The worst outcome of a wrong press there is that a light changes. That finding is about the MC2E
and does not transfer.

The AADS is the opposite case. Its program carries a full alarm integration including a virtual
keypad across eight partitions, so a wrong press there can be a keypad digit or a partition
command. The panel interface exposes an `Alarm` subsystem next to the `Lights` menu label, which
is recorded in
[crestron-eisc-join-discovery.md](crestron-eisc-join-discovery.md#cautions).

Working rules for any AADS slot work:

- Registering on a slot listen-only is safe. Do that first, and learn from watching.
- Before writing to any join, identify it by name from the retrieved program.
- Never sweep a join range on the AADS.
- If alarm behavior is ever deliberately tested, the monitoring company goes on test mode first.

## What the AADS program actually contains

From `Favela v4.bin`, retrieved 2026-09-02 over the CTP console. The binary is not committed; see
[crestron-xpanel-control-path.md](crestron-xpanel-control-path.md) for how to re-fetch it.

Header:

```text
Source File:  C:\Users\JustinR\Dropbox\Technicians\Programming\Simpl\Favela\New folder\Favela v4
Program File: Favela v4.smw
Programmer:   Justin R
Compiled On:  11/15/2019 5:06 PM
Source Env:   SIMPL Windows v4.11.06
Target Rack:  AADS.
```

Justin R worked for ASI, the same integrator as the MC2E's 2011 job, confirmed by the house owner.
Unlike the MC2E, this program is hand-written SIMPL Windows rather than D3 Pro output, so its
editable source is an ordinary `.smw` with no D3 Pro round trip to preserve.

The alarm modules, all under symbol path `S-7.19`:

| Module | Instances |
|---|---:|
| `S2_DSC_PowerSeries_Partition_Control_v1_0` | 8 |
| `S2_DSC_PowerSeries_Serial_Queue_v1_0` | 1 |
| `S2_DSC_PowerSeries_Zone_Status_v1_0` | 1 |
| `S2_DSC_PowerSeries_System_Status_v1_0` | 1 |
| `S2_DSC_PowerSeries_Virtual_Keypad_Feedback_v1_1` | 1 |
| `S2_DSC_PowerSeries_LED_to_Text_v1_0` | 1 |

There are **zero occurrences of `apex` or `destiny`** anywhere in the 1.1 MB binary.

## The puzzle

The house owner has visually confirmed that the alarm control panel is an Apex Destiny. The
DSC-branded unit in the pantry is a keypad, a user interface, not the panel.

But the AADS's live program does its arming, disarming, and status entirely through DSC PowerSeries
modules over a serial queue. So the AADS's alarm logic is pointed at DSC hardware, while the panel
the owner can see is an Apex.

Three readings, unresolved:

1. **Two systems coexist.** DSC PowerSeries on RS-232 and the Apex tied to Crestron by some other
   route. This would explain the ST-IO, whose four inputs are all in contact-closure mode with
   Input 1 already reading closed, and which
   [crestron-migration.md](crestron-migration.md#alarm-system-status-unknown) calls exactly the
   kind of dry-contact interface an alarm panel uses for a Crestron tie-in. Apex on contacts, DSC
   on serial, both landing in the AADS, nothing contradictory.
2. **The DSC arrived later.** A 2019 alarm install would explain a program recompiled on
   2019-11-15, eight years after the MC2E's. The Apex chassis would remain mounted and visible.
3. **The DSC modules are dead code.** This program has form for that. It still carries
   `CHV-TSTAT` definitions at Cresnet `E1` and `E2` for thermostats replaced by the Lennox units
   years ago, and the AADS was observed polling those two dead addresses on 2026-09-01.

## How to settle it, when the time comes

Cheapest first. None of these requires pressing a join.

1. **Does the DSC keypad show live status?** Backlit, displaying Ready or zone text. A DSC
   PowerSeries keypad is a proprietary Keybus device that only speaks to DSC panel hardware, so a
   live display implies live DSC hardware behind it. Purely visual.
2. **Where does the AADS's COM-A cable physically land?** The program puts the alarm on
   `Slot-02 / COM-A`.
3. **`SDEBUG` the AADS COM port, read-only.** Same technique that mapped the EISC on the MC2E,
   flags scoped narrowly and torn down in a `finally` block. If the DSC serial queue is transacting
   and receiving answers, the integration is live. If it has been timing out since 2019, it is dead
   code and reading 3 above as correct.

## What this corrects elsewhere

[crestron-apex-control-plane.md](crestron-apex-control-plane.md) proposes exposing "the AADS's
existing Apex arm, disarm, and status signals." The panel named in that document is right. The
mechanism is not: the signals in the program are DSC module signals, and the Destiny 6100 serial
parameters quoted there come from Crestron's generic module documentation rather than from anything
observed in this house. A programmer quoting that job from the document as written would be quoting
the wrong integration.

That document should not be rewritten until the puzzle above is resolved, because the correct
rewrite depends on which of the three readings is true.

## The terminology trap

Recorded because it has now caught a reader once.

`crestron-migration.md` says "Brand confirmed: DSC. Visible on the faceplate of the pantry wall
panel." That sentence is about the **keypad**. It is easy to read as identifying the alarm panel,
and doing so leads straight to the conclusion that the Apex references across the documentation are
wrong, which is itself wrong.

[CONTEXT.md](../../CONTEXT.md) already draws the distinction correctly, with an `_Avoid_` line on
the **Alarm keypad** entry warning not to call it the alarm panel. Trust the glossary over the
prose.
