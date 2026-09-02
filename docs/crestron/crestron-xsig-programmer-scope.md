# Crestron programmer scope of work

## Status, 2026-09-01

This document was originally written on the assumption that a Home Assistant interface to the
lighting system had to be designed and built from nothing. That assumption is now wrong, and the
document has been cut down accordingly.

Three findings changed it:

- **2026-08-31.** Every lighting command and state change crosses the MC2E-AADS EISC link, in both
  directions, with feedback that originates from real device state rather than from an echo of the
  command. See [crestron-eisc-join-discovery.md](crestron-eisc-join-discovery.md).
- **2026-09-01.** A free XPanel slot on the MC2E gives a working read *and* write path to lighting
  with no reprogramming at all, but it reaches only the Kitchen. See
  [crestron-xpanel-control-path.md](crestron-xpanel-control-path.md).
- **2026-09-01.** The MC2E's compiled program was retrieved and searched. It contains no alarm
  logic of any kind, which moves the Apex work out of this document.

An earlier version stated that three unoccupied panel and app slots had been tested and none
carried lighting feedback, and that any proposal assuming otherwise was mistaken. That was a false
negative caused by decoder bugs since fixed. The statement has been removed.

## Terminology

Two Crestron terms used here are easy to confuse and mean different things.

**XSIG** is a serial encoding that packs digital, analog, and serial joins into a byte stream over
TCP or RS-232. It is the Home Assistant-facing transport.

**EISC**, Ethernet Intersystem Communications, is the processor-to-processor link that already
exists between the MC2E and the AADS at IP-ID 05. It is context for the job, not a deliverable.

Where this document says "Intersystem Communications symbol" it means the SIMPL symbol terminating
the Home Assistant connection. That is a separate instance from the symbol carrying the existing
MC2E-AADS link.

## What already works, with no programmer

A bidding programmer should be told this exists, because pricing the mechanism as new work is
pricing work already done. The mechanism is the hard part and it is finished.

Registering on the MC2E's unoccupied XPanel at `Slot-05.IP-ID-03` over CIP (TCP 41794) yields:

- A full state dump on connect: 42 digital joins, 2 analog, 4 serial.
- Live per-light state changes, including brightness as a 16-bit analog join whose high byte is the
  8-bit Cresnet dimmer level, directly usable as a Home Assistant brightness value.
- A working write path. The processor accepts digital join presses and drives the Cresnet dimmers
  itself. Lights were physically switched this way and confirmed in the room.

**The limit is coverage, not capability.** All 75 press joins were scanned. Joins 21-35 address
five Kitchen loads; joins 36-95 drive no dimmer at all. The `.dsc` describes the panel as
`101-Kitchen` and that is exactly what it is.

## The actual job

Extend lighting control from the Kitchen to the remaining thirteen rooms, and put the result on a
documented, stable join contract.

Everything else in this document is either a precondition for that, a constraint on how it is done,
or work the owner wants priced separately.

Two candidate routes, both requiring program changes:

1. **Widen the existing XPanel at `IP-ID-03`.** The symbol already carries the Kitchen, and joins
   36-95 are defined but unwired, so there is headroom. This is the preferred route.
2. **Free or duplicate the EISC at `IP-ID-05`.** It already carries whole-house joins (`d58` Entry
   Center, `d99` Sink Area, `d103` Pool Bath, confirmed 2026-08-31). It is held by the AADS, and
   displacing it breaks audio and removes the ST-IO's Cresnet bus master.

The MC2E's `.dsc` lists only `IP-ID-03` and `IP-ID-05`, so there is no third slot waiting to be
used. A programmer proposing a new slot must say where it comes from.

## The gating question: is the source recoverable?

**Nothing below can be quoted accurately until this is answered.** It decides whether the job is a
contained edit or a rewrite of the house's lighting program.

The compiled program was retrieved from the processor and its header reads:

```text
Source File:  C:\ASI\Client Folders\Favela\Crestron\D3Pro\Gale Favela 11-14-08\Programs\...
Program File: Gale Favela 11-14-08.smw
Programmer:   D3 Pro 2.8.29
Compiled On:  8/23/2011 3:07 PM
Source Env:   SIMPL Windows v3.02.04
Target Rack:  MC2E
```

Three consequences.

**The compiled program cannot be turned back into source.** A `.bin` holds "SMW compiled code which
will be interpreted by LogicEngine.exe", so it is interpreter bytecode. Crestron's Series-3 package
format (`.lpz`) can optionally carry an archive of the source when the archive option was set at
compile time; the Series-2 package format (`.spz`) has no such provision, and the MC2E is a
2-Series processor. There is no supported decompiler and no vendor path back to editable logic.

**What can be recovered is names, not logic.** The binary yields the device table, signal names,
load names, and the eight house scene names (`A-Welcome`, `B-Good Bye`, `C-House On`, `D-House
Off`, `E-Good Morning`, `F-Good Night`, `G-Security`, `H-Entertain`). That is a useful inventory
head start and it is not source. A signal-name listing alone is not accepted as sufficient basis
for modifying the live system.

**The real source is a D3 Pro job, not a `.smw`.** D3 Pro generates the SIMPL program, the VT Pro-e
panel projects, and the compiled output from a room-and-load database. Hand-editing generated
`.smw` output breaks the round trip back to D3 Pro. The editable artifact is the D3 Pro job at the
path above, which belongs to the original integrator, ASI. D3 Pro reached end of feature life on
31 March 2025, so a programmer must also confirm they can still open a 2.8.29 job.

Actions, in order:

1. Contact ASI for the D3 Pro job, the `.smw`, and the VT Pro-e projects for this address.
2. If ASI cannot produce them, ask Crestron whether a dealer program archive exists for this system.
3. Try to pull a `.sig` signal file off the MC2E, which the compiler produces for the Toolbox
   debugger and which would give signal names against numbers.
4. Only if all three fail, treat the job as reconstruction and price it separately.

## Owner's objectives

1. Replace all four TSW-752 touch panels with Home Assistant wall panels without losing any control
   function currently available on those panels.
2. Preserve all existing CNX-B8 keypad behavior exactly.
3. Give Home Assistant direct control of every lighting load plus the ability to invoke every
   existing scene or programmed button action.
4. Allow Home Assistant to observe physical keypad and panel activity during the transition.
5. Make the AADS a removable subsystem boundary, so replacing it later does not remove lighting.
6. Keep the AADS and its panels functional until the Home Assistant replacements pass acceptance.
7. Leave the owner with complete, editable source and a documented interface another programmer can
   maintain.

Moving the Apex alarm integration off the AADS remains an owner objective, but it is no longer part
of this document. See [Separately priced work](#separately-priced-work).

## Verified existing system

### MC2E, lighting

Cresnet master for the keypads and garage lighting modules. Holds the live lighting program.

| Device | Cresnet IDs | Qty | Location |
| --- | --- | ---: | --- |
| CNX-B8 keypad | 62, 63, 64, 65, 66, 67, 6A, 6D, 6F | 9 | Seven rooms |
| CLX-1DIM8 | 70, 71, 72 | 3 | `106 - Garage` |
| CLX-1DIM4 | 73, 75, 76 | 3 | `106 - Garage` |
| CLX-4HSW4 | 74 | 1 | `106 - Garage` |

Keypad rooms: 62 and 66 `201 - Master Bed`; 63 `104 - Outdoor Kitchen`; 64 and 6F `101 - Kitchen`;
65 `202 - Master Bathroom`; 67 `103 - Foyer`; 6A `105 - Great Room`; 6D `203 - Studio`.

The MC2E is the IP master of the EISC to the AADS at CIP ID 05. It provides two bidirectional COM
ports, neither of which is required unless the Apex work is added back in.

### AADS, audio and panels

Runs its own live program and owns the four TSW-752 panels at IP-IDs 11-14, a CEN-IDOC at IP-ID 51,
the audio matrix and amplifier, the Apex serial connection, an ST-IO at Cresnet ID `0A` on a
physically separate AADS-owned Cresnet leg, and two stale offline `CHV-TSTAT` definitions at `E1`
and `E2`.

The TSW-752 panels are write-only for lighting: they send commands and display no state. Panel room
assignments are Primary Bedroom, Kitchen, Office, and Guest Room, which the `.dsc` does not record,
so panel identity must be verified against the recovered projects.

### Evidence supplied to the programmer

- [crestron-xpanel-control-path.md](crestron-xpanel-control-path.md), the working control path
- [crestron-eisc-join-discovery.md](crestron-eisc-join-discovery.md), the whole-house join method
- [crestron-migration.md](crestron-migration.md) and [crestron-strategy.md](crestron-strategy.md)
- [`dumps/`](dumps/), the `.dsc` descriptors and manifests from both processors

These establish hardware and topology. They are not a substitute for the original D3 Pro, SIMPL
Windows, and VT Pro-e projects.

## Phase 1: source recovery and decision gate

No production program may be overwritten in this phase.

Retrieve and archive, where they exist: the D3 Pro job, editable SIMPL Windows source and all
dependencies, the four VT Pro-e panel projects, the compiled programs currently loaded, firmware
and IP tables and Cresnet reports, nonvolatile values and presets, and a full restore-to-current
backup of every processor and panel.

The MC2E is retained only if all of the following hold, per
[ADR 0007](../adr/0007-cp3n-mandatory-fallback.md):

1. Complete editable source and dependencies are available.
2. The current program compiles reproducibly before modification.
3. The program has memory, signal, Ethernet, and runtime headroom for the full signal inventory and
   the Home Assistant connection.
4. Processor firmware and the Home Assistant integration hold a stable connection under expected
   signal volume.
5. Existing Cresnet operation is healthy and within power and network limits.
6. A bidirectional COM port is available for Apex, **only if** the separately priced Apex work is
   included.
7. The programmer will deliver and support the modified 2-Series source.

If any condition fails, migrate to a CP3N: recreate the complete lighting and keypad program,
preserve every CNX-B8 button behavior and LED indication, preserve every CLX channel behavior and
scene and ramp, move the Cresnet bus without electrically joining it to the AADS/ST-IO leg,
recreate the EISC to the AADS, host the Home Assistant endpoint, and regression-test all
pre-existing behavior before enabling Home Assistant control. The owner must approve the documented
decision and the CP3N price before any processor replacement begins.

## Phase 2: lighting inventory

Produce a machine-readable signal schedule. One row per control or feedback item, with: stable ID,
room or `global`, existing UI reference (panel/page/button, or keypad Cresnet ID and button
number), existing SIMPL signal name, plain-language description, data type, direction, behavior
(pulse, press/release, maintained, level, ramp), range and units, final join, authoritative
feedback source, test procedure, and notes on dependencies or interlocks.

Cover:

- Every populated CLX channel: Cresnet ID, channel, load name, room, dimmable or switched, current
  state and level feedback signals, and supported operations including ramp timing.
- Every scene, preset, all-off, pathway, room-off, and house-state action.
- Every CNX-B8 button: number, engraving, room, LED feedback, and tap, hold, and conditional
  behavior.
- Every TSW-752 lighting control, with the same command and feedback detail.

Direct load control and programmed actions are separate requirements. Exposing a load level does
not satisfy the requirement to expose a scene, and exposing a button action does not satisfy the
requirement for authoritative load state.

The five Kitchen loads and their joins are already mapped in
[crestron-xpanel-control-path.md](crestron-xpanel-control-path.md) and should be treated as a
worked example of the required detail, not re-derived.

## Phase 3: the Home Assistant interface

### Transport

A TCP/IP Client on the selected processor connects to the Home Assistant host and port required by
the installed Crestron integration. Verify compatibility against the actual installed integration
version, not an old example program.

The connection is local-LAN only and must not be exposed to the Internet. Legacy XSIG transport has
no application authentication, so access is restricted by network segmentation and firewall rules
to the Home Assistant host and the selected processor.

### Symbols

Use separate Intersystem Communications symbols for digital and for analog/serial signals on the
same transport, if the integration supports it. This avoids the join-number offset ambiguity that
occurs when digital joins follow analog/serial joins on one symbol. `dN`, `aN`, and `sN` must be
unambiguous in both the source and the delivered schedule. No dynamic, undocumented, or wildcard
mappings; every join explicitly wired and documented.

### Join stability

Join numbers are a public API. Once accepted they are not repurposed. See
[ADR 0008](../adr/0008-xsig-join-numbers-are-public-api.md).

Required logical grouping: system (connectivity, heartbeat, schema version, resync, online states);
lighting loads (per-channel commands and hardware-derived feedback); lighting actions (callable
scenes and separately observed physical button events); reserved capacity after each group.

Within each group, keep commands distinct from feedback, never drive a feedback join directly from
a command signal, keep stable IDs even when display labels change, mark deprecated joins reserved
rather than recycling them, and leave at least 25 percent expansion room where processor limits
allow.

### Signal naming

Names identify subsystem, room, object, operation, and direction:

```text
HA_SYS_MC2E_ONLINE_FB
HA_LGT_KITCHEN_ISLAND_ON_CMD
HA_LGT_KITCHEN_ISLAND_ON_FB
HA_LGT_KITCHEN_ISLAND_LEVEL_SET
HA_LGT_KITCHEN_ISLAND_LEVEL_FB
HA_LGT_KITCHEN_KEYPAD_64_BTN_03_INVOKE
HA_LGT_KITCHEN_KEYPAD_64_BTN_03_PHYSICAL_FB
```

Avoid names that depend on an old panel page or an unexplained numeric signal.

### Semantics

Digital: stateless actions use momentary press/release or a documented one-shot pulse. Where an
existing action distinguishes press, hold, and release, carry the full state. Do not retrigger
because a TCP connection reconnected while a join was high. Physical-button observation uses
separate joins from the joins Home Assistant uses to invoke the same action, and invoking from Home
Assistant must not report a physical press.

Analog: document raw range, engineering range, units, scaling, and rounding. Brightness needs a
documented conversion between Crestron's 0-65535 range and the integration's brightness range; note
that the observed encoding is the 8-bit dimmer level scaled to 16 bits. Setpoint and measured
feedback use separate joins. Ramping terminates on release, explicit stop, disconnect, or a safe
timeout.

Serial: document encoding, maximum length, termination, and empty behavior. No secrets on serial
joins. Enumerated states may use serial labels only alongside a stable machine-readable identifier.

### Authoritative feedback

Every stateful function needs feedback derived from the controlled module or existing state logic.
This is not acceptable:

```text
HA command join -> copied directly to HA feedback join
```

This is required:

```text
HA command join -> existing control logic -> real device state -> HA feedback join
```

Where a result cannot be confirmed, expose it as an action and document that it has no confirmed
state. Do not synthesize success. The existing program already publishes state on real device
change, including changes originating at a physical keypad, so this property does not need to be
invented.

### Connection and resynchronization

Expose at minimum: processor online/ready, connection online, schema version, lighting Cresnet
healthy, and last command result where available.

On connect and reconnect, send a complete snapshot of all feedback joins and replay no momentary
commands. If the standard symbol behavior cannot produce a snapshot, add and document an explicit
resynchronization mechanism. Home Assistant going offline must not interrupt local keypad, panel,
or lighting operation.

### Required lighting interface

Per populated dimmer channel: on, off, toggle, absolute level setpoint, current level feedback,
on/off feedback derived from real state, raise press/release, lower press/release, stop if distinct
from release, and fault feedback where available. Per switched channel: on, off, toggle, on/off
feedback, fault feedback where available.

Per CNX-B8 and TSW-752 lighting control: a Home Assistant invoke input entering the same existing
logic as the original button including hold behavior, a separate output reporting real user
interaction with the physical control, LED feedback where it conveys programmed state, and
documentation of every load and scene affected. The original UI signal and the Home Assistant
invoke signal converge before the existing action logic rather than duplicating it.

## Security requirements

1. Restrict the transport to the Home Assistant host and the selected processor on the trusted LAN.
2. Do not forward the port through the Internet-facing router.
3. Set and document administrative passwords on both processors. The current unauthenticated
   Telnet access must not remain the long-term state.
4. Disable unnecessary legacy remote-access services where supported and where doing so does not
   prevent required maintenance.
5. A network or Home Assistant outage must fail locally: keypads, lighting, alarm panel, and AADS
   operation continue without Home Assistant.

Alarm credential handling is governed by
[ADR 0009](../adr/0009-alarm-credentials-stay-in-crestron.md) and applies to the separately priced
Apex work.

## Change and cutover

Work from backups and never modify the only copy. Bench-compile and validate before loading.
Schedule production loads with the owner present. Change one processor role at a time with a tested
rollback path. Preserve current panel and keypad operation until acceptance is signed. Do not
electrically combine the MC2E lighting Cresnet leg with the AADS/ST-IO leg. Label moved cables and
photograph before and after. Record firmware changes and do not upgrade for convenience without a
documented compatibility reason and rollback plan.

## Acceptance testing

Programmer and owner execute the delivered test procedure together. Every row in the signal
schedule needs a recorded result; sampling a few devices is insufficient.

**Baseline regression, before enabling Home Assistant control.** Every CNX-B8 button retains its
original tap, hold, LED, scene, and conditional behavior. Every TSW-752 retains its original
operation. Every CLX load responds and reports correctly. AADS audio remains operational in every
active zone. Processor restarts issue no unintended commands.

**Lighting.** For every populated load: on, off, toggle, and level commands operate the correct
channel only; real load state updates Home Assistant feedback whether the change originated in Home
Assistant, at a keypad, at a panel, or from a scene; raise and lower start on press, stop on
release, and cannot remain ramping after disconnect. For every keypad and panel control: Home
Assistant can invoke the existing action, physical press and release are observable, an invocation
is not reported as a physical press, and existing LED and scene feedback stays correct.

**Connection and failure.** Home Assistant restart, TCP disconnect and reconnect, processor
restart, and loss and restoration of LAN connectivity. No test may replay a stale momentary
command. Every subsystem returns to an accurate state or an explicit unavailable state.

## Deliverables

1. Unmodified pre-work backups of both processors and all four panel projects.
2. Complete editable post-work source and all dependencies, including the D3 Pro job if the work
   was done through D3 Pro.
3. Compiled programs exactly matching the delivered source.
4. If a CP3N is used, complete CP3N source, configuration, firmware record, and the retired MC2E
   backup.
5. The final machine-readable signal schedule with every field named in Phase 2.
6. A human-readable join map grouped by room.
7. Home Assistant connection parameters and a sample configuration covering one example of each
   signal pattern used.
8. A network and processor diagram of the final topology.
9. Completed acceptance-test results covering every signal-schedule row.
10. A written rollback procedure and the files needed to execute it.
11. A list of unresolved, unused, offline, or obsolete devices and signals found during the work,
    without silently removing them.
12. A maintenance guide covering how to add a future load or button without renumbering joins.

The owner must have unrestricted use of the delivered source for this residence. No source-code
password, dealer lock, or dependency on an undisclosed custom module is acceptable.

## Completion criteria

- One Home Assistant endpoint on the MC2E or approved CP3N exposes the complete accepted schedule.
- Every populated lighting load in all fourteen rooms is controllable with authoritative feedback.
- Every existing CNX-B8 action is preserved, observable, and callable through the documented
  interface.
- Every existing TSW-752 lighting control can be reproduced on a Home Assistant wall panel.
- Every stateful command has authoritative feedback or is documented as an action without feedback.
- All regression, lighting, reconnect, and failure tests pass.
- Source, join map, test record, and rollback package delivered and verified.

## Separately priced work

Removed from this document on 2026-09-01. Both remain owner objectives and neither is cancelled.

**Apex alarm migration.** The MC2E's compiled program was searched and contains zero occurrences of
alarm, Apex, zone, motion, siren, passcode, panic, or intrusion. The only "security" hit is
`G-Security`, a lighting scene. The alarm lives entirely on the AADS, so moving it is an AADS-side
job with its own risks, its own test regime, and a monitoring-company test window. It is scoped in
[crestron-apex-control-plane.md](crestron-apex-control-plane.md). Folding it into the lighting job
made both harder to price.

**A/V proxying.** Exposing every AADS zone, source, tuner, and metadata function through the
durable processor is a large inventory job against a subsystem the owner intends to replace. It
should be quoted on its own, once the lighting interface is proven.

The consequence of this split: the ST-IO stays on the AADS Cresnet leg and the AADS cannot be
decommissioned until the alarm work is done. That dependency is recorded in
[crestron-migration.md](crestron-migration.md#what-this-changes-in-the-plan).

## Reference documentation

- [Crestron MC2E product documentation](https://www.crestron.com/Products/Catalog/Inactive/Discontinued/M/MC2E)
- [Crestron CP3N product documentation](https://www.crestron.com/Products/Catalog/Inactive/Discontinued/C/CP3N)
- [Crestron SIMPL Windows Symbol Guide: Intersystem Communications](https://www.crestron.com/getmedia/39357ef1-4169-4e0f-82c3-d1f0958dcaa5/mg_sw-simpl_symbols_guide_1)
- [Crestron file extension reference](https://github.com/RBSystems/Crestron-Documentation/blob/master/FileExtensions.md), for `.bin`, `.spz`, and `.lpz` package contents
- [Transitioning from D3 Pro to Crestron Home](https://www.crestron.com/News/Blog/January-2025/Transitioning-D3-Pro-Software-to-Crestron-Home), D3 Pro end of feature life
- [Home Assistant Crestron XSIG integration](https://github.com/npope/home-assistant-crestron-component)
