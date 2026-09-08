# Home Assistant, Crestron, and Apex Destiny 6100 Control Plane

## Status: superseded — the panel it names does not exist in this house

**Do not use this document for planning, and do not quote a programmer from it as written.** Both
the panel name and the mechanism it describes are wrong. pde visually confirmed, 2026-09-08, that
the real alarm panel is a **DSC PC1864** with a **DSC PK5500** keypad — not an Apex Destiny 6100, and
no Ademco/Honeywell hardware has ever been confirmed present in this house. The "visual
confirmation" cited in earlier versions of this document's status note was a misidentification of
the panel model, not of the mechanism. The AADS's live program has always done its arming,
disarming, and status through DSC PowerSeries modules; that was never a contradiction to resolve,
it was the correct answer all along, matching the panel that is actually installed.

Full resolution and sourcing:
[crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#resolved-2026-09-08-direct-visual-confirmation-dsc-not-apex),
which also carries the safety rule that stays in force for any AADS slot work. The corrected,
current research — including the direct-to-DSC-Keybus alternative this document never
considered — is [crestron-alarm-integration-paths.md](crestron-alarm-integration-paths.md).

The rest of this document is left as written, Apex references and all, as the record of a real
(if wrong) hypothesis and the reasoning that supported it at the time. Everywhere below that says
"Apex" or "Destiny 6100," read "the DSC PC1864" instead; everywhere it cites Crestron's official
Destiny 6100 module documentation, read that citation as void — this house's AADS never ran that
module family, per the binary analysis in
[crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#what-the-aads-program-actually-contains).

## Conclusion

The existing equipment appears capable of supporting a complete bidirectional
Home Assistant to Crestron to Apex control plane. Cresnet sniffing, however, is
not the mechanism that unlocks it.

The cleanest route is to add an XSIG interface to the existing AADS program and
expose the AADS's existing Apex arm, disarm, and status signals to Home
Assistant. If reverse engineering is necessary, the useful targets are the
Ethernet connection between the TSW-752 panels and the AADS and, more
importantly, the RS-232 connection between the AADS and the Apex panel—not the
Cresnet bus.

## Existing topology

The available evidence points to this control path:

```text
TSW-752 tap
    │ Ethernet/CIP join
    ▼
AADS SIMPL program
    │ RS-232 commands and status polling
    ▼
Apex Destiny 6100
```

The four TSW-752 touch panels are Ethernet devices registered directly with the
AADS. The AADS descriptor lists them at IP IDs 11 through 14. Its separate
Cresnet leg contains the ST-IO and two obsolete Crestron thermostat definitions,
but no touch panels. See
[`dumps/aads-favela-v4.dsc.txt`](dumps/aads-favela-v4.dsc.txt)
and the AADS findings in [crestron-migration.md](crestron-migration.md).

Crestron's official Destiny 6100 SIMPL module confirms the downstream side of
the path. It controls the Apex through a CNXCOM or ST-COM serial port using
RS-232 at 1200 baud, 8 data bits, no parity, and one stop bit. The module accepts
user number and code digits, Arm Away, Arm Home, Disarm, and a status request. It
returns armed-away, armed-home, and disarmed feedback for as many as eight
partitions.

Sources:

- [Crestron Apex Destiny 6100 module documentation](https://applicationmarket.crestron.com/content/Help/Apex/destiny_6100_arm_disarm.pdf)
- [Crestron Application Market listing](https://applicationmarket.crestron.com/apex-destiny-6100-north-america/)
- [Apex Destiny 6100 RS-232 interface installation instructions](https://manualzz.com/doc/9100604/apex-destiny-6100-rs-232-interface-installation-instructions)

## What Cresnet sniffing can and cannot reveal

Sniffing the MC2E lighting Cresnet leg can reveal traffic between the MC2E, the
CNX-B8 wall keypads, and the CLX lighting modules. That remains relevant to the
lighting migration, but it will not reveal Apex touchscreen commands.

Sniffing the AADS Cresnet leg may reveal ST-IO activity associated with alarm
state changes if the ST-IO is in fact wired to the alarm system. It will not
reveal the TSW-752 button joins or the serial commands sent to the Apex. At
most, it could expose secondary contact or relay effects produced by the AADS
program.

The useful observation points are therefore:

1. Ethernet traffic between a TSW-752 and the AADS, to correlate touch-panel
   actions with Crestron joins.
2. The RS-232 link between the AADS and the Apex interface board, to observe the
   actual Apex requests and responses.

## Option 1: add an XSIG bridge to the AADS

This is the recommended approach.

```text
Home Assistant → TCP/XSIG → AADS → existing Apex module → RS-232 → Apex
                                  ← partition feedback ←
```

A Crestron programmer would add a narrowly scoped XSIG interface to the AADS
program and expose explicit joins for the functions Home Assistant needs:

- Arm Home
- Arm Away
- Disarm
- Arming-status request
- Per-partition armed-away feedback
- Per-partition armed-home feedback
- Per-partition disarmed feedback
- Alarm, trouble, and ready feedback if the existing program already has those
  signals available

Home Assistant could then use the same XSIG integration proposed for lighting.
The AADS would retain responsibility for the known-working Apex protocol and
serial link. No Cresnet decoding or Apex serial-protocol reimplementation would
be required.

This option depends on retaining the AADS as the alarm bridge. If the AADS is
still intended to be removed during the audio migration, this should be treated
as an interim architecture or the Apex serial function must be moved elsewhere
first.

## Option 2: connect Home Assistant directly to the Apex

The Apex RS-232 interface is explicitly designed for bidirectional automation
control, so a direct bridge is technically plausible:

```text
Home Assistant → isolated serial adapter → Apex RS-232 interface
```

This would remove Crestron from the alarm path. It would require:

- The full Apex two-way RS-232 protocol documentation, or a sufficiently
  complete capture of the existing AADS-to-Apex exchanges.
- A Home Assistant integration or local gateway implementing commands,
  checksums, polling, response parsing, reconnect behavior, and failure states.
- Confirmation of whether the Apex interface supports more than one controller.
  Until verified otherwise, assume it permits only one active controller.
- A cutover plan so the existing AADS connection and the new adapter never
  contend for the same serial interface.

The official Crestron module proves that arm-home, arm-away, disarm, status
polling, and partition status are available through the Apex interface. It does
not by itself document the wire-level command strings.

## Option 3: reverse-engineer the current path

If changing the AADS program is unavailable and the full Apex protocol cannot
be recovered, the current installation can be characterized through correlated
captures.

For each test action, record both observation points at the same time:

1. Capture Ethernet traffic between one TSW-752 and the AADS.
2. Passively monitor both directions of the AADS-to-Apex RS-232 link.
3. Tap Arm Home, Arm Away, Disarm, and Status on the touch panel one at a time.
4. Repeat the tests for each configured Apex partition.
5. Record both successful and rejected operations, including not-ready,
   incorrect-code, trouble, and alarm conditions where they can be tested
   safely.
6. Correlate the touch-panel join transitions with each serial request and Apex
   response.

This should be sufficient to reproduce the limited arm, disarm, and status
behavior, provided the capture includes all variable fields and response states.
It is more work and carries more uncertainty than exposing the already-wired
SIMPL module through XSIG.

## Security and safety constraints

Alarm control should not expose the household's ordinary user code as
digit-by-digit Home Assistant entities or joins. Doing so could place the code
in entity states, event history, debug logs, backups, packet captures, and
automations.

Prefer a dedicated automation credential with only the permissions required for
the integration. If the credential must remain inside Crestron, store it in the
AADS program and expose only high-level arm and disarm actions through XSIG.
Home Assistant should also represent unavailable or stale feedback explicitly;
a sent command must not be treated as successful until the Apex reports the
expected partition state.

Any direct serial implementation should preserve normal keypad operation, fire
and life-safety behavior, and the Apex panel's local autonomy. Home Assistant
should be an additional control surface, not a component required for the
alarm panel to function. (Central-station reporting was listed here
originally; the house's alarm is confirmed not professionally monitored, so
there is no central station to preserve reporting to. See
[crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#the-safety-rule).)

## Recommended next verification

Before commissioning programming or building a serial bridge:

1. Locate the Apex RS-232 interface card and identify the cable running to the
   Crestron equipment.
2. Confirm which AADS serial port it reaches.
3. Verify that the current touch-panel alarm page can arm, disarm, and display
   live partition status.
4. Determine how many Apex partitions are actually configured and used.
5. Ask a Crestron programmer whether the existing compiled AADS program can be
   recovered or whether the original source must be obtained from the
   integrator.
6. Scope an XSIG-only change before investing in protocol capture or a custom
   serial implementation.

The result of that verification will determine whether the AADS can serve as a
long-lived alarm gateway or whether the direct RS-232 option should be designed
as part of the planned AADS removal.
