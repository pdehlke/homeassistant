# Crestron XSIG Interface for Home Assistant

## Programmer scope of work

This document specifies the Crestron programming work required to make Home
Assistant a complete replacement user interface for the existing Crestron wall
touch panels while preserving the existing CNX-B8 wall keypads, centralized
CLX lighting modules, Apex Destiny 6100 alarm system, and AADS audio system.

The required end state has one durable Home Assistant XSIG connection terminating
on the lighting control processor. The existing MC2E should be retained if it
passes the suitability tests in this document. If it does not, the programmer
must quote and implement the same interface on a used CP3N after migrating the
MC2E program.

This is not a request for a few representative joins. The interface must expose:

- Every connected CLX lighting load, with command and authoritative feedback.
- Every lighting action currently available from every CNX-B8 keypad and every
  TSW-752 touch-panel button.
- Every A/V function currently available on any TSW-752.
- Every alarm function and status currently available on any TSW-752, using a
  dedicated credential retained inside Crestron.
- Connection health, synchronization, and command-result information sufficient
  for Home Assistant never to mistake a sent command for a confirmed state.

The programmer must inventory the existing programs and user interfaces before
assigning final joins. The inventory, signal schedule, editable source, compiled
programs, backups, test results, and rollback package are contractual
deliverables.

## Owner's objectives

1. Replace all four TSW-752 touch panels with Home Assistant wall panels without
   losing any control function presently available on those panels.
2. Preserve all existing CNX-B8 keypad behavior.
3. Give Home Assistant both direct control of every lighting load and the
   ability to invoke every existing lighting scene or programmed button action.
4. Allow Home Assistant to observe physical keypad and touch-panel button
   activity during the transition period.
5. Move the Apex alarm integration off the AADS so future removal of the AADS
   does not remove alarm control.
6. Keep the AADS and its present touch panels functional until the Home
   Assistant replacements have passed acceptance testing.
7. Make the AADS a removable A/V subsystem boundary. When it is eventually
   replaced, lighting and alarm control must remain operational without a
   Crestron rearchitecture.
8. Leave the owner with complete, editable source and a documented interface
   that another Crestron or Home Assistant programmer can maintain.

## Verified existing system

### MC2E lighting processor

The MC2E currently holds the live lighting program and is the Cresnet master for
the wall keypads and garage lighting modules.

| Device | Cresnet IDs | Quantity | Existing descriptor location |
| --- | --- | ---: | --- |
| CNX-B8 keypad | 62, 63, 64, 65, 66, 67, 6A, 6D, 6F | 9 | Seven rooms |
| CLX-1DIM8 | 70, 71, 72 | 3 | `106 - Garage` |
| CLX-1DIM4 | 73, 75, 76 | 3 | `106 - Garage` |
| CLX-4HSW4 | 74 | 1 | `106 - Garage` |

The keypad room assignments are:

| Cresnet ID | Room |
| --- | --- |
| 62, 66 | `201 - Master Bed` |
| 63 | `104 - Outdoor Kitchen` |
| 64, 6F | `101 - Kitchen` |
| 65 | `202 - Master Bathroom` |
| 67 | `103 - Foyer` |
| 6A | `105 - Great Room` |
| 6D | `203 - Studio` |

The MC2E and AADS have an existing, live Ethernet Intersystem Communications
connection at CIP ID 05. The MC2E is the IP master for that connection.

The MC2E provides two bidirectional COM ports. One must be confirmed available
and suitable before choosing the MC2E end state.

### AADS audio and user-interface processor

The AADS runs its own live program and currently owns:

- The four Ethernet TSW-752 touch panels at IP IDs 11, 12, 13, and 14.
- A CEN-IDOC at IP ID 51.
- The AADS audio matrix, amplifier, tuners, source control, and associated logic.
- The current alarm user-interface logic and presumed Apex serial connection.
- An ST-IO at Cresnet ID 0A on a physically separate AADS-owned Cresnet leg.
- Two stale, offline CHV-TSTAT/CHV-THSTAT definitions at Cresnet IDs E1 and E2.

The TSW-752 room assignments are Primary Bedroom, Kitchen, Office, and Guest
Room. The existing `.dsc` descriptor does not contain those room names, so the
programmer must verify the identity of each panel in the recovered projects.

### Alarm panel

The installed panel is an Apex Destiny 6100. Crestron's published module for
this panel uses bidirectional RS-232 at 1200 baud, 8 data bits, no parity, and
one stop bit through a CNXCOM or ST-COM interface. The published module supports
user number/code entry, Arm Away, Arm Home, Disarm, status requests, and
armed-away/home/disarmed feedback for as many as eight partitions.

The programmer must verify the actual physical serial path, existing module,
panel firmware, partition configuration, and all alarm functions used by the
current AADS program. The ST-IO wiring must also be identified; it must not be
assumed to be the Apex serial interface or disconnected as part of this work.

### Repository evidence supplied to the programmer

- [`crestron-migration.md`](crestron-migration.md)
- [`crestron-strategy.md`](crestron-strategy.md)
- [`crestron-apex-control-plane.md`](crestron-apex-control-plane.md)
- [`crestron-dumps/mc2e-gale-favela-11-14-08.dsc.txt`](crestron-dumps/mc2e-gale-favela-11-14-08.dsc.txt)
- [`crestron-dumps/aads-favela-v4.dsc.txt`](crestron-dumps/aads-favela-v4.dsc.txt)
- [`crestron-dumps/aads-favela-v4.dip.txt`](crestron-dumps/aads-favela-v4.dip.txt)
- [`crestron-dumps/aads-manifest.txt`](crestron-dumps/aads-manifest.txt)

These files establish hardware and topology. They are not substitutes for the
original SIMPL Windows and VT Pro-e source projects.

## Required end-state architecture

### Preferred MC2E architecture

```text
                              Home Assistant
                                    ▲
                                    │ TCP/XSIG
                                    ▼
CNX-B8 keypads ── Cresnet ──► MC2E lighting/alarm gateway
CLX modules     ◄─ Cresnet ──┤   │
Apex 6100       ◄── RS-232 ──┘   │ existing Ethernet ISC
                                  ▼
                             AADS A/V system
                                  │
                         TSW-752 panels during transition
```

The MC2E is the only Home Assistant XSIG endpoint. It continues to own the
lighting bus, gains the Apex serial module and physical connection, and carries
all current AADS A/V commands and feedback over the existing MC2E-AADS
intersystem connection.

Removing the AADS later is permitted to remove only A/V functions and the old
TSW-752 panels. It must not remove lighting, keypad, alarm, or the Home
Assistant XSIG endpoint.

### Mandatory CP3N fallback

The programmer must use a CP3N instead of the MC2E if any MC2E suitability test
fails. In that case:

```text
                              Home Assistant
                                    ▲
                                    │ TCP/XSIG
                                    ▼
CNX-B8 keypads ── Cresnet ──► CP3N consolidated gateway
CLX modules     ◄─ Cresnet ──┤   │
Apex 6100       ◄── RS-232 ──┘   │ Ethernet ISC
                                  ▼
                             AADS A/V system
```

The CP3N must replace the MC2E as the Cresnet master, reproduce all existing
lighting and keypad behavior, host the Apex integration, host the Home Assistant
XSIG endpoint, and maintain an intersystem link to the AADS until the AADS is
removed.

## Phase 1: source recovery and non-destructive survey

No production program may be overwritten during this phase.

The programmer must retrieve and archive, where present:

- Complete MC2E and AADS processor projects, including editable SIMPL Windows
  source, SIMPL+ modules, user modules, device modules, IR drivers, and all
  supporting files.
- Compiled processor programs currently loaded on both processors.
- All four editable VT Pro-e TSW-752 projects and the compiled projects loaded
  on each panel.
- Current firmware, IP tables, Cresnet reports, processor configuration,
  passwords/access settings, and program checksums.
- Nonvolatile values, presets, and configuration data needed to reproduce the
  current behavior.
- A full backup that can restore each processor and panel to its pre-work state.

If editable source is not recoverable, the programmer must stop and provide a
separate written estimate for reconstruction. A compiled program or signal-name
file alone is not accepted as sufficient source for modifying the live system.

## Phase 2: complete functional inventory

The programmer must create a spreadsheet or CSV signal schedule covering every
current control and feedback item. Each row must include:

| Required field | Meaning |
| --- | --- |
| Stable ID | Permanent machine-readable identifier independent of join number |
| Subsystem | `system`, `lighting`, `alarm`, or `av` |
| Room/zone | Physical room, A/V zone, alarm partition, or `global` |
| Existing UI | Panel/project/page/button or keypad/Cresnet ID/button number |
| Existing signal | Original SIMPL signal name and module/symbol location |
| Description | Plain-language behavior visible to the owner |
| Data type | Digital, analog, or serial |
| Direction | HA to Crestron, Crestron to HA, or paired command/feedback |
| Behavior | Pulse, press/release, maintained, level, ramp, text, or enumeration |
| Range/units | Boolean, 0-65535, percent, dB scale, source ID, text encoding, etc. |
| XSIG join | Final type-prefixed join such as `d123`, `a45`, or `s12` |
| Feedback source | Hardware/module signal that authoritatively determines state |
| Test procedure | Exact action and expected command/feedback result |
| Notes | Dependencies, delays, lockouts, mutually exclusive states, or hazards |

Discovery must cover all four TSW-752 projects, even if they appear identical.
Differences among rooms or panel revisions must be recorded rather than assumed
away.

### Lighting inventory

Inventory all populated channels on every CLX module and record:

- Cresnet ID and channel number.
- Load name, room/area, load type, and dimmable versus switched behavior.
- Current on/off and level feedback signals.
- Direct on, off, toggle, absolute-level, raise, lower, and stop behavior where
  supported.
- Ramp rates or timing behavior currently used.
- Every scene, preset, all-off, pathway, room-off, house-state, and other
  programmed lighting action.
- Every CNX-B8 button press and release, including button number, engraving,
  room, LED feedback, tap behavior, hold behavior, double-tap behavior, and any
  conditional or mode-dependent behavior.
- Every TSW-752 lighting button or slider with the same command and feedback
  semantics.

Direct load control and programmed actions are separate requirements. Exposing
a load level does not satisfy the requirement to expose a scene or button
action, and exposing a button action does not satisfy the requirement for
authoritative load state.

### A/V inventory

Inventory every function presently available on any TSW-752, including every
active AADS zone, source, and controlled source device. At minimum, inspect for:

- Zone power and power feedback.
- Source selection and selected-source feedback.
- Volume setpoint, volume feedback, volume up/down/stop, mute, and mute feedback.
- Bass, treble, balance, loudness, mono, tone presets, and any other audio DSP
  function exposed by the current project.
- Global and grouped commands such as all off, party mode, paging, zone linking,
  or source sharing.
- AADS tuner band, frequency, preset, seek, tune, station text, and metadata.
- CEN-IDOC browsing, transport, selection, and metadata if still functional.
- Every controlled source-device function: power, digits, channel, guide, menu,
  navigation, transport, record, colored/function keys, favorites, and any
  device-specific commands shown on a panel.
- All serial text, metadata, cover-art references, now-playing information,
  errors, and availability feedback displayed by the existing panels.
- All conditional behavior, source-specific page behavior, interlocks, and
  macros triggered by a panel action.

Page navigation and purely decorative UI elements do not need XSIG joins.
Every button, slider, selector, or displayed state that controls or represents
the real system does.

### Alarm inventory

Inventory every function and state presently available on any TSW-752 and every
configured Apex partition. At minimum, inspect for:

- Arm Home, Arm Away, Disarm, and status request.
- Per-partition ready/not-ready, armed-home, armed-away, disarmed, alarm,
  trouble, entry-delay, exit-delay, and chime states where available.
- Fire, panic, medical, police, silence, reset, and cancel controls if and only
  if they are present and functional on the existing Crestron interface.
- Zone open/closed, bypassed, alarm, trouble, and descriptive text where shown.
- Zone bypass/unbypass controls where shown.
- Command accepted, rejected, timed out, or failed status.
- ST-IO inputs and relays, their physical wiring, and their relationship to the
  alarm system or any other subsystem.

No life-safety function may be inferred from a screen label alone. Trace each
signal to the existing program logic and test it with the alarm monitoring
provider placed in the appropriate test mode.

## Phase 3: processor decision gate

### Retain the MC2E only if all conditions pass

The programmer must document that:

1. Complete editable MC2E source and all dependencies are available.
2. The current program compiles reproducibly before modification.
3. At least one bidirectional MC2E COM port is available for the Apex connection,
   or an appropriate supported expansion interface is included in the quote.
4. The program has sufficient memory, signal capacity, Ethernet resources, and
   runtime headroom for the complete signal inventory, Apex module, expanded
   intersystem traffic, and Home Assistant XSIG connection.
5. The processor firmware and Home Assistant XSIG implementation can maintain a
   stable connection under the expected signal volume.
6. Existing Cresnet operation is healthy and remains within power and network
   limits.
7. The programmer is willing to deliver and support the modified 2-Series
   source.

### Use the CP3N if any condition fails

The CP3N migration must include:

- Recreating the complete MC2E lighting/keypad program on the CP3N.
- Preserving every CNX-B8 button behavior and LED indication.
- Preserving every CLX channel behavior, scene, preset, ramp, and feedback.
- Moving the MC2E Cresnet bus to the CP3N without joining it electrically to the
  separate AADS/ST-IO Cresnet leg.
- Moving the Apex module and serial connection to a CP3N COM port.
- Recreating the AADS intersystem interface on the CP3N.
- Hosting the Home Assistant XSIG endpoint on the CP3N.
- Regression-testing all pre-existing behavior before enabling HA control.

The owner must approve the documented decision gate and CP3N price before a
processor replacement begins.

## Phase 4: Apex migration

The Apex integration must be moved from the AADS to the selected durable
processor. The programmer must:

1. Identify the existing Apex serial module and preserve all currently used
   behavior.
2. Identify and label the existing AADS-to-Apex cable at both ends.
3. Move or extend the physical serial connection to the selected processor using
   the correct DCE/DTE wiring and without creating two active serial controllers.
4. Configure and verify the existing 1200-baud, 8-N-1 connection or document the
   actual verified settings if the installation differs.
5. Create a dedicated Apex automation user number/code with only the required
   permissions, if the panel supports that separation.
6. Store that credential only inside the Crestron program/nonvolatile
   configuration. It must not be placed on an XSIG digital, analog, or serial
   join, written into the signal schedule, printed in debug logs, or supplied to
   Home Assistant.
7. Expose high-level commands and authoritative feedback, never keypad digits or
   the credential itself.
8. Retain local Apex keypad operation, central-station communication, fire and
   life-safety behavior, and autonomous panel operation if Crestron or Home
   Assistant is offline.

Disarm and other security-sensitive requests must be edge-triggered commands,
not maintained signals. A request must clear after processing and must not be
replayed automatically after a reconnect or processor restart.

## Phase 5: AADS intersystem expansion

Until the AADS is replaced, all A/V logic remains on the AADS. The programmer
must expand the existing Ethernet Intersystem Communications link so the durable
processor can proxy every inventoried A/V command and feedback item.

Requirements:

- Preserve the current intersystem behavior between the processors.
- Add new signals without renumbering or breaking existing signals unless both
  programs are changed and fully regression-tested together.
- Use separate, clearly named signal groups for A/V commands, A/V feedback, and
  connection/synchronization state.
- Prevent feedback loops between HA commands, panel commands, and feedback.
- Preserve current TSW-752 control during the transition.
- On intersystem reconnect, resynchronize actual AADS state without replaying
  stale commands.
- Expose an explicit `aads_online` status to Home Assistant.
- When AADS is offline, mark A/V functions unavailable; do not retain misleading
  last-known states as current.

## Phase 6: Home Assistant XSIG contract

### Transport

The selected processor must use a TCP/IP Client configured to connect to the
Home Assistant host and port required by the selected Home Assistant Crestron
XSIG integration. The final IP address, port, reconnect timing, and network
policy will be supplied during commissioning.

The connection must be local-LAN only. It must not be exposed directly to the
Internet. Because legacy XSIG transport does not provide modern application
authentication, access must be restricted by network segmentation and firewall
rules to the Home Assistant host and selected Crestron processor.

The programmer must verify compatibility against the actual integration version
installed by the owner, not merely against an old example program.

### XSIG symbols

Use separate Intersystem Communications symbols for digital signals and for
analog/serial signals, connected to the same TCP/IP Client transport if the
selected integration supports that arrangement. This avoids the join-number
offset ambiguity that occurs when digital joins follow analog/serial joins on a
single symbol.

The final design must make `dN`, `aN`, and `sN` unambiguous in both the SIMPL
source and the delivered signal schedule. Configure each symbol's Offset and
Option parameters according to the current SIMPL symbol documentation and the
tested Home Assistant integration requirements.

Do not use dynamic, undocumented, or wildcard mappings. Every join must be
explicitly wired and documented.

### Join stability and allocation

Join numbers are a public API. Once accepted, they may not be repurposed.

The programmer may propose the final numeric ranges after completing discovery,
but the following logical grouping is required:

| Group | Contents |
| --- | --- |
| System | Connectivity, heartbeat, schema version, resync, processor/AADS/Apex online states |
| Lighting loads | Direct per-channel commands and hardware-derived feedback |
| Lighting actions | Callable scenes/macros and separate observed physical-button events |
| Alarm | High-level commands, per-partition/zone feedback, command result |
| A/V zones | Power, source, volume, mute, tone/DSP, availability |
| A/V sources | Device commands, transport, navigation, tuner and metadata |
| Reserved | Documented unused capacity after each subsystem for future additions |

Within each group:

- Keep HA-to-Crestron commands distinct from Crestron-to-HA feedback/events.
- Never drive a feedback join directly from the HA command signal.
- Use stable IDs and signal names even if display labels later change.
- Mark deprecated joins as reserved; do not recycle them.
- Reserve at least 25 percent expansion capacity in each data type and subsystem
  range where processor limits permit.

### Signal naming

Use deterministic names such as:

```text
HA_SYS_AADS_ONLINE_FB
HA_LGT_KITCHEN_PENDANTS_ON_CMD
HA_LGT_KITCHEN_PENDANTS_ON_FB
HA_LGT_KITCHEN_PENDANTS_LEVEL_SET
HA_LGT_KITCHEN_PENDANTS_LEVEL_FB
HA_LGT_KITCHEN_KEYPAD_64_BTN_03_INVOKE
HA_LGT_KITCHEN_KEYPAD_64_BTN_03_PHYSICAL_FB
HA_ALM_PARTITION_01_ARM_AWAY_CMD
HA_ALM_PARTITION_01_ARMED_AWAY_FB
HA_AV_GREAT_ROOM_POWER_CMD
HA_AV_GREAT_ROOM_POWER_FB
HA_AV_GREAT_ROOM_VOLUME_SET
HA_AV_GREAT_ROOM_VOLUME_FB
```

Names must identify subsystem, room/zone, object, operation, and direction.
Avoid names that depend only on an old panel page or an unexplained numeric
signal.

### Digital command semantics

- Stateless actions use momentary press/release or a documented one-shot pulse.
- If an existing action distinguishes press, hold, and release, XSIG must carry
  the full press/release state so Home Assistant can reproduce it.
- Do not trigger commands repeatedly merely because a TCP connection reconnects
  while a join is high.
- Maintained commands are permitted only where the real device semantics are
  maintained and documented.
- Physical-button observation must use separate feedback/event joins from the
  joins used by Home Assistant to invoke the same action.
- Triggering an action from Home Assistant must not falsely report that a
  physical keypad button was pressed.

### Analog semantics

- Document raw range, engineering range, units, scaling, and rounding for every
  analog join.
- Lighting brightness exposed to HA must have a documented conversion between
  Crestron's 0-65535 analog range and the integration's HA brightness range.
- A/V volume must state whether it represents raw AADS level, percentage, or dB
  and must define minimum, maximum, and mute behavior.
- Command setpoints and measured/current feedback must use separate joins.
- Raise/lower ramping must terminate on release, explicit stop, disconnect, or a
  safe timeout.

### Serial semantics

- Document encoding, maximum length, termination, and empty/null behavior.
- Serial joins must not contain alarm credentials, access tokens, or other
  secrets.
- Enumerated states may use serial labels only when a stable machine-readable
  identifier or documented enumeration is also available.
- Source names, station text, track metadata, zone names, alarm zone text, and
  error descriptions must update when their authoritative source changes.

### Commands and authoritative feedback

Every stateful function must have independent authoritative feedback derived
from the controlled module or existing Crestron state logic. The following is
not acceptable:

```text
HA command join → copied directly to HA feedback join
```

The required pattern is:

```text
HA command join → existing control logic → real device/module state → HA feedback join
```

If a subsystem cannot confirm the result, expose the command as an action and
document that it has no confirmed state. Do not synthesize success.

### Connection, startup, and resynchronization

Expose at least:

- Selected processor online/ready.
- XSIG connection online.
- XSIG schema version as an integer or serial semantic version.
- AADS intersystem online.
- Apex serial online/communicating.
- Lighting Cresnet healthy.
- Last command result or subsystem error where available.

On initial connection and reconnect, send a complete state snapshot for all
feedback joins. Do not replay momentary commands. If a complete snapshot cannot
be generated by the standard symbol behavior, add an explicit status-request or
resynchronization mechanism and document it.

Home Assistant going offline must not interrupt local keypad, touch-panel,
lighting, A/V, or alarm operation.

## Required subsystem interfaces

### Lighting loads

For every populated dimmer channel, expose where supported:

- On command.
- Off command.
- Toggle action.
- Absolute level setpoint.
- Current level feedback.
- On/off feedback derived from current state.
- Raise press/release.
- Lower press/release.
- Stop action if distinct from release.
- Online/fault feedback if available.

For every populated non-dimming switch channel, expose:

- On command.
- Off command.
- Toggle action.
- On/off feedback.
- Online/fault feedback if available.

### Lighting buttons and actions

For every CNX-B8 and TSW-752 lighting control:

- A Home Assistant invoke input that enters the same existing logic as the
  original button, including hold/release behavior where applicable.
- A separate physical-button/event output that reports actual user interaction
  with the original keypad or panel.
- LED/indicator feedback where it conveys a meaningful programmed state.
- Documentation of every load, scene, condition, or macro affected.

The original UI signal and HA invoke signal should converge before the existing
action logic, not duplicate that logic in parallel.

### Alarm

For every configured partition, expose all supported existing functions and
states. The minimum accepted interface is:

- Arm Home command.
- Arm Away command.
- Disarm command using the processor-held automation credential.
- Status request.
- Ready feedback.
- Armed Home feedback.
- Armed Away feedback.
- Disarmed feedback.
- Alarm feedback.
- Trouble feedback.
- Entry-delay and exit-delay feedback where available.
- Apex communication online feedback.
- Last-command result: accepted, rejected, timeout, or communication error.

Also expose every additional alarm zone, bypass, panic, reset, silence, status,
or text function proven to exist on the current TSW-752 interface. High-risk
functions must remain protected by the same deliberate interaction or safety
logic as the existing interface.

### A/V

For every active zone and source, expose every current TSW-752 function found in
the inventory. The delivered schedule must be complete enough for the owner to
reconstruct every operational TSW-752 A/V page in Home Assistant without
reverse-engineering the SIMPL or VT Pro-e source.

Command joins must enter the same existing AADS logic used by the panels.
Feedback joins must originate from the existing AADS state signals. Source
device commands that lack feedback must be identified as actions rather than
stateful controls.

## Security requirements

1. Do not place the Apex user number/code on XSIG, in the delivered join map, in
   logs, or in Home Assistant.
2. Use a dedicated automation credential rather than the household's normal
   keypad credential where supported.
3. Restrict the XSIG TCP path to the Home Assistant host and selected processor
   on the trusted local network.
4. Do not forward the XSIG port through the Internet-facing router.
5. Set and document administrative passwords on the processors; the current
   unauthenticated Telnet access identified during discovery must not remain the
   long-term state.
6. Disable unnecessary legacy remote-access services where doing so is supported
   and does not prevent required maintenance.
7. Do not log secrets or full alarm command payloads.
8. A network or HA outage must fail locally: keypad, alarm panel, lighting, and
   existing AADS operation continue without HA.
9. HA must not be able to alter installer programming, alarm user codes, central
   station configuration, or life-safety configuration through XSIG.

## Change and cutover requirements

- Work from backups and editable source, never by modifying the only copy.
- Bench-compile and validate each program before loading it.
- Schedule production loads and alarm tests with the owner present.
- Place the monitored alarm account in test mode before alarm signaling tests.
- Change one processor role at a time and retain a tested rollback path.
- Preserve current panel and keypad operation until HA acceptance is signed.
- Do not electrically combine the MC2E lighting Cresnet leg with the separate
  AADS/ST-IO Cresnet leg.
- Label all moved cables and provide before/after photographs.
- Record firmware changes and do not upgrade solely for convenience without a
  documented compatibility reason and rollback plan.

## Acceptance testing

The programmer and owner must execute the delivered test procedure together.
Passing a few sample devices is insufficient; every row in the signal schedule
must have a recorded result.

### Baseline regression

Before enabling Home Assistant control:

- Every CNX-B8 button retains its original tap, hold, release, LED, scene, and
  conditional behavior.
- Every TSW-752 retains its original lighting, alarm, and A/V operation.
- Every CLX load responds and reports correctly.
- AADS audio remains operational in every active zone.
- Apex local keypads, central-station communication, and existing Crestron alarm
  controls remain operational.
- Processor restarts do not issue unintended commands.

### Home Assistant lighting tests

For every populated load:

- On, off, toggle, and level commands operate the correct channel only.
- Actual load state updates HA feedback whether the change originated from HA,
  a keypad, a touch panel, a scene, or other Crestron logic.
- Raise/lower starts on press, stops on release, and cannot remain ramping after
  disconnect.

For every keypad and touch-panel lighting control:

- HA can invoke the exact existing action.
- Physical press and release are observable in HA.
- An HA invocation is not reported as a physical press.
- Existing LED and scene feedback remains correct.

### Home Assistant alarm tests

For every configured partition and current touchscreen alarm function:

- Commands are tested from a safe initial state.
- Not-ready and invalid transitions are rejected and reported as failures.
- HA state changes only after authoritative Apex feedback.
- Disarm uses the processor-held dedicated credential and exposes no digits or
  code through packet capture, joins, logs, or delivered files.
- Serial disconnect produces unavailable/error feedback, not a false success.
- Reconnect resynchronizes actual partition state and does not replay a command.
- HA and Crestron outages do not impair standalone alarm operation.

### Home Assistant A/V tests

For every active zone, source, and current TSW-752 function:

- HA command behavior matches the original panel behavior.
- State and metadata changes made from HA, a TSW-752, the AADS front panel, or
  another source appear correctly in HA where feedback exists.
- AADS or intersystem disconnect marks affected entities unavailable.
- Reconnect restores actual state without changing zone power, source, or
  volume unexpectedly.

### Connection and failure tests

Test at least:

- Home Assistant restart.
- XSIG TCP disconnect and reconnect.
- Selected processor restart.
- AADS restart and intersystem reconnect.
- Apex serial disconnect and reconnect.
- Loss and restoration of LAN connectivity.

No test may cause a stale momentary command to replay. Every subsystem must
return to an accurate state or an explicit unavailable/error state.

## Deliverables

The job is not complete until the owner receives:

1. Unmodified pre-work backups of the MC2E, AADS, and all TSW-752 projects.
2. Complete editable post-work SIMPL Windows source and all dependencies.
3. Complete editable post-work VT Pro-e source for all panels, including any
   changes needed during transition.
4. Compiled programs exactly matching the installed source.
5. If CP3N is used, complete CP3N source, configuration, firmware record, and
   the retired MC2E backup.
6. The final machine-readable CSV or spreadsheet signal schedule with every
   required field from this document.
7. A human-readable join-map PDF or Markdown export grouped by subsystem and
   room/zone.
8. Home Assistant connection parameters and a sample configuration covering at
   least one example of each signal pattern used.
9. A network and processor diagram showing the final topology.
10. Photographs and labels for the Apex serial connection and any moved wiring.
11. Completed acceptance-test results, including every signal-schedule row.
12. A written rollback procedure and all files needed to execute it.
13. A list of unresolved, unused, offline, or obsolete devices/signals discovered
    during the work, without silently removing them.
14. A brief maintenance guide explaining how to add a future load, button,
    A/V function, or alarm status without renumbering existing joins.

The owner must have unrestricted use of the delivered source for this residence.
No source-code password, dealer lock, or dependency on an undisclosed custom
module is acceptable.

## Completion criteria

The work is complete only when:

- One Home Assistant XSIG endpoint on the MC2E or approved CP3N exposes the
  complete accepted signal schedule.
- Lighting and alarm remain on the durable processor and no longer depend on
  the continued presence of the AADS.
- A/V remains fully controllable through the AADS for as long as it is retained.
- Every existing functional TSW-752 control can be reproduced on a Home
  Assistant wall panel.
- Every existing CNX-B8 lighting action is preserved, observable, and callable
  through the documented interface.
- Every stateful command has authoritative feedback or is explicitly documented
  as an action without feedback.
- All regression, subsystem, reconnect, and failure tests pass.
- The complete source, join map, test record, and rollback package have been
  delivered and verified.

## Reference documentation

- [Crestron MC2E product documentation](https://www.crestron.com/Products/Catalog/Inactive/Discontinued/M/MC2E)
- [Crestron CP3N product documentation](https://www.crestron.com/Products/Catalog/Inactive/Discontinued/C/CP3N)
- [Crestron SIMPL Windows Symbol Guide: Intersystem Communications](https://www.crestron.com/getmedia/39357ef1-4169-4e0f-82c3-d1f0958dcaa5/mg_sw-simpl_symbols_guide_1)
- [Crestron Apex Destiny 6100 module documentation](https://applicationmarket.crestron.com/content/Help/Apex/destiny_6100_arm_disarm.pdf)
- [Home Assistant Crestron XSIG integration](https://github.com/npope/home-assistant-crestron-component)
