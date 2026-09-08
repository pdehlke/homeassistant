# Alarm integration: open questions, parked

## Status

**Resolved 2026-09-08.** Unparked earlier the same day (parked 2026-09-02 on the condition "picked
up only if and when lighting is finished"; lighting finished, see
[crestron-ha-bridge.md](crestron-ha-bridge.md)'s Status section, and pde asked directly to resume).
The central puzzle this document tracked — DSC modules in the AADS's program against a panel the
owner had identified as an Apex Destiny 6100 — is now closed: pde visually confirmed the real panel
directly, not just the keypad faceplate. It is a **DSC PC1864**, with a **DSC PK5500** keypad in the
pantry. The "Apex Destiny 6100" identification was wrong from the start; no Ademco/Honeywell
hardware has ever been confirmed present in this house. See
[crestron-alarm-integration-paths.md](crestron-alarm-integration-paths.md) for the integration-path
research this unblocks and [issue #24](https://github.com/pdehlke/homeassistant/issues/24) for the
live thread.

The safety rule below was never conditional on parked status and stays in force unchanged.

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
- **The house's alarm is not professionally monitored** (confirmed by pde, 2026-09-08) — no
  monitoring company, no central station, no test window to arrange before a deliberate test. This
  removes the false-dispatch risk specifically; it does not relax the join-identification rules
  above, which exist for other reasons (unknown local effects, corrupting alarm state, an unintended
  siren or relay action).

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
   [crestron-migration.md](crestron-migration.md#alarm-system-dsc-pc1864-confirmed-2026-09-08) calls exactly the
   kind of dry-contact interface an alarm panel uses for a Crestron tie-in. Apex on contacts, DSC
   on serial, both landing in the AADS, nothing contradictory.
2. **The DSC arrived later.** A 2019 alarm install would explain a program recompiled on
   2019-11-15, eight years after the MC2E's. The Apex chassis would remain mounted and visible.
3. **The DSC modules are dead code.** This program has form for that. It still carries
   `CHV-TSTAT` definitions at Cresnet `E1` and `E2` for thermostats replaced by the Lennox units
   years ago, and the AADS was observed polling those two dead addresses on 2026-09-01.

## How to settle it, when the time comes

Cheapest first. None of these requires pressing a join. **All three below are now done** — see the
"Resolved" sections further down for how each actually got settled.

1. **Does the DSC keypad show live status?** Backlit, displaying Ready or zone text. A DSC
   PowerSeries keypad is a proprietary Keybus device that only speaks to DSC panel hardware, so a
   live display implies live DSC hardware behind it. Purely visual. **Superseded, not literally
   run**: pde identified the panel directly instead, a stronger check than this one.
2. **Where does the AADS's COM-A cable physically land?** The program puts the alarm on
   `Slot-02 / COM-A`. **Not run, and no longer needed**: the SDEBUG capture in item 3 confirmed the
   link is live without requiring a physical trace.
3. **`SDEBUG` the AADS COM port, read-only.** Same technique that mapped the EISC on the MC2E,
   flags scoped narrowly and torn down in a `finally` block. If the DSC serial queue is transacting
   and receiving answers, the integration is live. If it has been timing out since 2019, it is dead
   code and reading 3 above as correct. **Run 2026-09-08: transacting, live, confirmed.** See the
   "reading 3 is refuted" update above.

## New evidence, 2026-09-07: the zone status page, and a live collision

[crestron-alarm-zone-inventory.md](crestron-alarm-zone-inventory.md) statically read a second
alarm page in the TSW-752 project, `ALARM-DSC-pg02-zones`, that this document's original pass never
walked. It lists 24 zones on AADS digital joins `d201`-`d224`, entirely by reading the retrieved
panel XML, no live connection made.

That range turns out to collide with the live lighting bridge in a way the `d130`-`d148` range
never did: `outside_holiday` **presses** `d221` directly, in current production use, and `d221` is
also that page's "Room 4 East Wins" zone. Every other lighting/alarm collision on record is a
read-only alias sitting inside a range nothing presses; this is a write. See
[crestron-alarm-zone-inventory.md](crestron-alarm-zone-inventory.md#two-collisions-this-inventory-found-that-lighting-work-did-not-know-about)
for the three unresolved readings of what that means and why nothing here was changed to resolve
it: doing so trades away a working feature (Holiday has no other join in the whole panel project)
against a risk the DSC-vs-Apex puzzle above still hasn't settled. A second, read-only collision
(`d206`, shared with `outdoor_kitchen`'s alias) and two smaller gaps in `FORBIDDEN_AADS_WRITE`
(`d149`, `d187`/`d188`) are recorded there too.

This sharpens why the puzzle above still matters even though lighting is done and stable: if
reading 3 (the DSC modules are dead code) is correct, the `d221` collision is inert. If reading 1
(subsystem gating) or reading 2 (a later, separate DSC install) is correct instead, a
currently-shipping Home Assistant feature has been quietly exercising alarm-adjacent processor
state since 2026-09-06 with no way, from here, to tell.

## New evidence, 2026-09-08: the Apex Destiny 6100 is an Ademco panel, not DSC

Identified for the first time this session, in response to pde asking directly how to get Home
Assistant onto the real alarm hardware: the **Apex Destiny 6100 was manufactured by Ademco**
(later Honeywell), not DSC. DSC and Ademco are separate, competing companies with incompatible
protocols — a single physical panel cannot be both, and Crestron's own module catalog treats them
as entirely different integrations (confirming what `crestron-apex-control-plane.md` already
suspected: its Destiny 6100 serial parameters are real, but for a module family the AADS's compiled
program does not actually run).

This reframes the three readings above. Reading 1 (subsystem gating on one system) now looks
unlikely — DSC and Ademco genuinely can't be the same hardware. Reading 2 (the DSC arrived later,
as a real second system) is now the best-supported: an older Ademco Destiny 6100 from the original
Crestron-era install, later supplemented or replaced by a real DSC PowerSeries system whose
integration was compiled 2019-11-15, matching the AADS's program exactly. Reading 3 (dead code)
is weakened but not eliminated.

Full writeup, sourcing, and — now that lighting is done and this is unparked — the actual
integration paths this unblocks: [crestron-alarm-integration-paths.md](crestron-alarm-integration-paths.md).
The two read-only confirmations this document already named (visual pantry-keypad check, an SDEBUG
capture of the AADS's COM-A) are still the way to settle this for good; the SDEBUG attempt was
blocked by the harness's permission classifier this session and needs pde's explicit go-ahead or his
own hands on `CresnetMon/mac/sdebug.py`.

## Resolved, 2026-09-08: direct visual confirmation (DSC, not Apex)

The cheapest of the two confirmations named above turned out unnecessary: pde didn't need to check
whether the pantry keypad shows live status, because he went and read the panel itself. It is a
**DSC PC1864**. The keypad in the pantry is a **DSC PK5500**.

This closes the puzzle, and closes it more simply than any of the three readings above anticipated.
There is one alarm system in this house, and it is DSC, matching the AADS's compiled
`S2_DSC_PowerSeries_*` modules exactly. The "Apex Destiny 6100" identification that started this
whole investigation was wrong from the moment it was made — not a legacy system later replaced, not
a second system coexisting with DSC, just a misidentification. No Ademco or Honeywell hardware has
ever been confirmed present in this house at any point.

Reading against the three original readings: 1 and 2 both assumed an Ademco panel existed somewhere,
which direct inspection now rules out — there is no second chassis to be the "older install" or the
"gated subsystem." Reading 3 (the DSC modules are dead code) is the only one that survives even in
principle, and it is now the least likely of the three: a full DSC PowerSeries module set, compiled
for the one panel that is actually in this house, is exactly what a live integration looks like.

**Update, same day: reading 3 is refuted, not just unlikely.** The SDEBUG capture named above ran
after all — pde added a scoped Bash permission rule for `sdebug.py`/`crestron_console.py`, which is
all the earlier block needed. `SDEBUG -DON S02` against the AADS (`192.168.4.61`) for 25 seconds
caught 436 bytes of live traffic on `Slot-02`, decoding to a DSC IT-100-style `901` (LCD Update)
message whose payload is plainly readable: `Date     Time SEP 08/26 10:29a`, a DSC keypad's ordinary
idle-screen clock display, timestamped 10:26:28 the same day. The AADS's serial link to the panel is
not dead code sitting unused since 2019; it is actively receiving live keypad display traffic from
the real DSC PC1864, in real time. Full capture command and raw bytes are in the session record; the
narrower "is it actually transacting" question this section left open is now closed alongside the
"which panel" question above it.

The Ademco-manufacturer research immediately above stays in this document rather than being deleted:
it was a real, correctly-sourced finding about the Destiny 6100 as a product, and it is the reasoning
that made this the best-supported open question right up until the direct check ran. It just turned
out the Destiny 6100 was never the panel in this house to begin with.

## What this corrects elsewhere

[crestron-apex-control-plane.md](crestron-apex-control-plane.md) proposes exposing "the AADS's
existing Apex arm, disarm, and status signals." Both the panel and the mechanism named in that
document are now known wrong: there is no Apex panel, and the signals in the program are DSC module
signals for the DSC PC1864 that is actually installed. That document is superseded outright, not
just parked — see its own Status section. The corrected version of the same idea (expose the AADS's
existing DSC integration through XSIG) is Path A in
[crestron-alarm-integration-paths.md](crestron-alarm-integration-paths.md#path-a-integrate-via-crestron).

## The terminology trap, resolved

This section is kept for the record; the trap it describes can no longer catch anyone, now that the
panel itself (not just the keypad) has been directly identified.

`crestron-migration.md` said "Brand confirmed: DSC. Visible on the faceplate of the pantry wall
panel." That sentence was about the **keypad**, and at the time it was written the panel's brand was
still an open question — reading it as identifying the alarm panel would have been premature, even
though, as it turned out, both the keypad and the panel are DSC.

[CONTEXT.md](../../CONTEXT.md) already drew the distinction correctly, with an `_Avoid_` line on the
**Alarm keypad** entry warning not to call it the alarm panel. That distinction remains correct and
worth keeping even now that both components share a brand: keypad and panel are still two different
pieces of hardware, model PK5500 and model PC1864 respectively.
