# Crestron to Home Assistant Migration

This document consolidates the current hardware inventory, evaluates three prior AI-generated notes
found uncommitted in this repo, and lays out a plan for moving control of lighting, audio, the alarm
system, and HVAC from Crestron to Home Assistant.

The goal is not to remove Crestron everywhere. The CLX-* lighting modules stay. The AADS and the
TSW-752 touch panels are explicitly being replaced. The wall keypads are staying for now but are
expected to be replaced eventually, once a later phase gets to them. Everything else in this document
follows from those constraints.

## Status as of 2026-08-04, for picking this back up

Everything confirmed so far came from two sources: Telnet access to the MC2E and AADS consoles (no
SIMPL, Toolbox, or any paid programmer visit needed for any of it), and the homeowner's own physical
inspection of the living room AV cabinet. Full detail is in "Direct verification" below; this is the
short version of where things stand and what's left.

**Settled, don't re-check:**

- Keypads: 9 units, model CNX-B8, across 7 rooms (two rooms have two keypads each, which is where the
  original "seven" came from).
- Lighting modules: 3x CLX-1DIM8, 3x CLX-1DIM4, 1x CLX-4HSW4 (not two), all seven physically racked in
  the garage.
- The MC2E and AADS both hold live, independent programs and are linked by a confirmed, named
  Ethernet Intersystem Communications (XSIG/ISC) connection, currently online.
- The AV cabinet holds two separate, independently-powered Cresnet buses, not one: MC2E's own leg
  (keypads and garage lighting), and a second leg powered by its own brick that reaches the ST-IO via a
  passive distribution strip. This is the AADS's leg physically extending into the same cabinet.
- Touch panels: all 4 TSW-752s confirmed live and distinct (Primary Bedroom, Kitchen, Office, Guest
  Room). A CID collision from a prior SD card recovery was found and fixed during this investigation.
- Alarm panel brand: DSC. HVAC: Lennox, fully separate from Crestron, confirmed stale Crestron
  thermostat definitions in the AADS's program from before Lennox, not a live dependency.
- Neither console has a password. Known, not yet fixed.

**Next physical steps, roughly in the order they'd naturally happen:**

1. The ST-IO input test: disarm the alarm (put it on test with the monitoring company first if it's
   monitored), trigger one zone at a time, watch the ST-IO's front-panel INPUT LEDs for a reaction.
   Baseline recorded: PWR green, NET yellow, Input 1 red. This is now confirmed safe to do without any
   risk to the lighting bus, since the ST-IO's leg is electrically separate from MC2E's.
2. Alarm panel model number, without prying the faceplate off: check for a label inside the door if it
   opens without full removal, or ask the monitoring company if it's monitored.
3. Lennox thermostat model: hasn't been started, this is pure homework, look at the unit itself.
4. AADS zone/input count: read the zone/source list off a TSW-752's audio screen, then check the AADS's
   own rear terminal blocks in the living room cabinet for what's actually wired.
5. Console passwords: set one on both the MC2E and the AADS. Low effort, hasn't been done yet.
6. Get quotes from an independent Crestron programmer for the Path A join-mapping job. Doesn't require
   being home, can happen anytime.

**Open questions only the homeowner can answer**, not resolvable by more telnet digging: what the
ST-IO's 8 relay outputs actually drive (needs the empirical test or a look inside the alarm panel),
whether the alarm is professionally monitored and by whom, and the Lennox thermostat's exact model.

See "Plan of attack" and "Open verification checklist" near the end of this document for the full,
detailed list.

## Current inventory

- One MC2E control processor.
- One ST-IO input/output expansion module.
- One AADS (Adagio Audio Distribution System), which is also the whole-house amplifier and audio
  matrix switcher.
- Four TSW-752 touch panels.
- Seven wall plates with eight labeled switches each, model unknown.
- Three CLX-1DIM8 dimmer modules.
- One CLX-4HSW4 switch module (originally remembered as two; corrected below).
- A Lennox HVAC system, confirmed to run on its own thermostat and not wired into Crestron at all.
- An alarm system of unknown make, with an unknown tie-in to Crestron (or lack of one).

This is the inventory as originally described, from memory, before any device was queried directly.
"Direct verification" below corrects several of these counts against what the bus itself reports: the
wall plate count and model, and the CLX-4HSW4 count.

The touch panels are known to talk to the AADS rather than directly to the MC2E. There is no SIMPL
Windows, VTPro-e, or Crestron Toolbox license or access available, and none is assumed anywhere in this
plan except where explicitly called out as a one-time paid task.

**Physical locations, per the homeowner (this is not one rack):**

- The garage rack holds only the CLX-* lighting modules and their CLT-* terminal blocks. Nothing else
  physically lives there, despite all of it also being logically grouped under "106 - Garage" in the
  MC2E's program.
- The AADS sits in an audio cabinet in the living room.
- The MC2E and the ST-IO share a different AV cabinet, also in the living room, next to the audio
  cabinet. Note that this splits physical co-location from logical bus membership: the ST-IO sits right
  next to the MC2E but is wired onto the AADS's separate Cresnet leg (confirmed via `REPORTCRESNET`
  above), meaning there is a physical Cresnet cable running between the two adjacent living room
  cabinets to reach it, not just within one.
- The alarm panel is a wall panel in the kitchen pantry, not rack-mounted anywhere. Wire runs between
  the living room AV cabinet and the pantry are inside walls and not something the homeowner can trace
  by hand; any confirmation of an alarm tie-in has to come from both ends independently (labels,
  visible characteristics, or the panel's own documentation), not a continuous wire trace.

## Evaluating the three prior notes

Three uncommitted markdown files were found in this repo, written by a different LLM in an earlier
session: a migration guide, a Cresnet bus-sniffing walkthrough, and a note on what is lost by removing
the AADS. Before building on them, each concrete claim was checked against Crestron's own published
documentation and against what is actually findable on GitHub and the Home Assistant community forum.
The results split cleanly into confirmed claims, reasonable but unverifiable claims, and one claim that
appears to be fabricated outright.

### Confirmed

| Claim | Verdict | Source |
| :--- | :--- | :--- |
| The AADS has its own onboard 2-Series control engine, not just a dumb amp/matrix | Confirmed | [AADS product page](https://www.crestron.com/Products/Inactive/Discontinued/A-M/AADS), [AADS operations guide](https://www.crestron.com/getmedia/2f8dd352-bbd8-49d3-9dbf-a55ff7c8f44a/mg_og_aads_1) |
| The AADS is a 12-channel amp at roughly 45W/channel into 8 ohms, with a base capacity of 6 stereo zones, expandable in 6-zone increments via AAE expander units | Confirmed | Same AADS sources above |
| A mature, actively used XSIG-based Home Assistant integration exists | Confirmed | [home-assistant-crestron-component](https://github.com/npope/home-assistant-crestron-component), [HA community thread, 1000+ posts](https://community.home-assistant.io/t/crestron-custom-component-to-integrate-a-crestron-control-system-via-xsig/233182) |
| Cresnet's physical layer is RS-485 half-duplex at 38,400 baud, 8-N-1, over Y (Data+) / Z (Data-) with separate 24V/GND | Confirmed as general Cresnet knowledge, consistent with public installation documentation | General Cresnet physical-layer documentation |
| The ST-IO provides 8 relay outputs and 4 analog/digital inputs over Cresnet | Confirmed | [ST-IO product page](https://www.crestron.com/products/model/ST-IO), [ST-IO operations guide](https://www.crestron.com/getmedia/9eb070a7-8abe-4b65-9b3e-f42b5d9fc5e4/mg_st-io_1) |
| CLX-1DIM8 and CLX-4HSW4 specs (8-channel dimmer vs. 4-channel high-inrush non-dimming switch, both Cresnet) | Confirmed | [CLX-1DIM8 spec sheet](https://www.crestron.com/getmedia/4b579869-a6d7-436f-a0ed-f86ac140d08b/ss_clx-1dim8_1), [CLX-4HSW4 product page](https://www.crestron.com/Products/Catalog/Lighting-and-Environmental/Integrated-Lighting-Systems/CLX-Modules/CLX-4HSW4) |
| TSW-752 runs on standard 802.3af PoE, not a Crestron-proprietary power scheme | Confirmed | [TSW-752 spec sheet](https://www.crestron.com/getmedia/d886c3af-faeb-4ed0-91d3-64eea1a1bad7/ss_tsw-752_1), [PWE-4803RU PoE injector guide](https://www.crestron.com/getmedia/c51e20e1-9f3d-4be5-8166-f3bda5f6de09/mg_ig_pwe-4803ru_1) |

### Reasonable but unverified

The claim that touch panel commands are IP-targeted at the AADS and cross to the MC2E via XSIG/ISC is
architecturally plausible and consistent with how Adagio-plus-lighting systems were commonly built,
but it had not been confirmed against this specific installation. The same went for the claim that the
AADS holds the primary SIMPL logic rather than the MC2E. Both were testable without any Crestron
software: 2-Series processors expose a Telnet console (standard commands like `ver` and `iptable`)
that needs only network access, not a Toolbox license.

**Update:** both were checked directly. See "Direct verification" below. The touch panel/XSIG claim
turned out to be correct in substance, though the specifics (which box holds "primary" logic) turned
out more nuanced: both processors hold real, independent, live logic, and the IP link between them is
confirmed by name in both programs' own device tables, not just plausible.

### Fabricated

The bus-sniffing note describes a tool called `cresnet2mqtt`, complete with a specific YAML
configuration format and a byte-level packet decode table (`0x05` as a packet header, `0x12` as a
Cresnet ID, and so on). No trace of a project by that name exists on GitHub, in Home Assistant's
integration ecosystem, or anywhere else searched. The packet decode table is presented with the same
confidence as the AADS specs above, but it has no source and cannot be verified, which makes it very
likely invented to make the "Option 2" bypass plan look further along than it is.

The one real tool in this space is [CresnetMon](https://github.com/StephenGenusa/CresnetMon), a
Windows Forms application that sniffs Cresnet traffic over a USB-to-RS-485 adapter and displays raw
hex frames. It is read-only. It does not decode the protocol, and it cannot send commands. Building a
bridge that both understands Cresnet frames and can drive the CLX modules is a from-scratch reverse
engineering and software project, not a matter of configuring an existing daemon. Anywhere the prior
notes implied otherwise, that implication does not hold up.

### Gaps

Despite the alarm system and HVAC both being explicit goals, none of the three prior notes mentions
either one. This document treats both as open tracks that need their own investigation rather than
extensions of the audio/lighting work.

## Direct verification: what's actually on the wire (2026-08-04)

Telnet access to both the MC2E and the AADS confirmed several things the
evaluation above could only flag as unverified. Both consoles are reachable on port 23 with no password
prompt at all, despite `INFO` reporting password support as enabled on both units. Anyone with LAN
access can currently reach either console unauthenticated. That is worth fixing independently of
everything else in this plan.

The raw `.dsc`/`.dip`/manifest text pulled from both consoles via `TYPE` is saved as-is in
[`crestron-dumps/`](crestron-dumps/), for reference beyond the excerpts and tables below.

### MC2E

- A real, named, actively running program is loaded: `Gale Favela 11-14-08`, present on flash since
  8-23-11, using 21,280 of 131,072 bytes of NVRAM. This settles the open question from the evaluation
  above: the MC2E is not a blank box waiting for logic, it holds live lighting logic today, and has been
  running continuously for 22+ days as of this check.
- MC2E reports itself as the IP master (`IP Masters: 1`), with a live, `ONLINE` CIP connection to the
  AADS over port 41794. The intersystem link between the two boxes exists and is active right now, not
  merely plausible.
- `REPORTCRESNET` enumerates MC2E's Cresnet leg directly, no sniffing hardware required:

  | Cresnet ID | Model | Count | Notes |
  | :--- | :--- | :--- | :--- |
  | 62, 63, 64, 65, 66, 67, 6A, 6D, 6F | CNX-B8 | 9 | The wall plates. Model identified: **CNX-B8**. |
  | 70, 71, 72 | CLX-1DIM8 | 3 | Matches original inventory. |
  | 73, 75, 76 | CLX-1DIM4 | 3 | Not in the original inventory; discovered here. |
  | 74 | CLX-4HSW4 | 1 | The correct count; two was a misremembering of the rack layout. |

  This bus-reported inventory supersedes the memory-based counts used earlier in this document. No
  ST-IO appears on this leg; see below for where the ST-IO actually lives.
- The program's descriptor file (`TYPE <program>.dsc` at the console) goes further and names a room for
  every device, resolving the keypad count discrepancy in the process:

  | Cresnet ID | Room |
  | :--- | :--- |
  | 62, 66 | 201 - Master Bed (2 keypads) |
  | 63 | 104 - Outdoor Kitchen |
  | 64, 6F | 101 - Kitchen (2 keypads) |
  | 65 | 202 - Master Bathroom |
  | 67 | 103 - Foyer |
  | 6A | 105 - Great Room |
  | 6D | 203 - Studio |

  Seven rooms, two of them with two keypads each, which is exactly where the original "seven wall
  plates" came from: that was a room count, not a unit count, and both turn out to be correct.

  Every one of the seven lighting modules (all three CLX-1DIM8s, all three CLX-1DIM4s, and the one
  confirmed CLX-4HSW4) is labeled **106 - Garage**. All lighting control hardware is centralized in one
  physical location, which matters directly for Path B: there is one place to go to tap the bus, not a
  run through the whole house.
- The same descriptor also defines an XPanel (Crestron's software/virtual touch panel) assigned to
  IP-ID 3 and the Kitchen, currently `OFFLINE` per the live IP table. It exists as a defined option, not
  a live one.

### AADS

- A separate, newer program is loaded: `Favela v4`, dated 11-16-19, eight years after the MC2E's load.
  Same integrator name, later job. The `.ird` (IR driver database) and `.fp2` (front-panel data) files
  loaded alongside it match Crestron's own documentation of the AADS using its IR/RS-232 ports and LCD
  front panel.
- AADS reports `IP Masters: 0`. It is not the master of the intersystem IP relationship; that role
  belongs to the MC2E, per the MC2E's own report above. AADS runs its own local program on its own
  separate Cresnet leg, but the earlier notes' framing of the AADS as the "primary" logic location does
  not hold up on its own: it is a peer with local logic, not the master of the pair.
- AADS's IP table has 8 entries. One is the live MC2E link (mirrored from the MC2E side, same CIP_ID 5),
  labeled `Ethernet Intersystem Communications` in both programs' own descriptor files. That label,
  present on both ends and both `ONLINE`, is the confirmation that the earlier notes' XSIG/ISC
  hypothesis was correct in substance. The `WHO` console command and the program descriptor together
  identify the other seven entries, which are real devices, not internal placeholders as first guessed
  from the loopback addresses in the static IP table:

  | IP-ID | Device type | Room | Notes |
  | :--- | :--- | :--- | :--- |
  | 11 | TSW-752 | Primary Bedroom | Confirmed live via `WHO`. Room per homeowner; not recorded in the AADS's own `.dsc`, which only labels these four generically as `TSW-752` with no location field. |
  | 12 | TSW-752 | Kitchen | See "SD card restore" note below. |
  | 13 | TSW-752 | Office | Confirmed live via `WHO`. |
  | 14 | TSW-752 | Guest Room | Confirmed live via `WHO`. |
  | 15, 16 | Crestron App | - | Virtual touch panel slots for the Crestron mobile/tablet app, defined but not confirmed still in use. |
  | 51 | CEN-IDOC | - | A Crestron iPod dock, an audio source not previously known about. |

  This directly confirms, from the program's own device table rather than architectural inference, that
  the four TSW-752 panels register with the AADS over Ethernet, not with the MC2E. The room labels
  above are not part of that confirmation; they came from the homeowner, since the AADS's program does
  not record them the way the MC2E's keypad entries record room names.

  **SD card restore incident:** two of the four TSW-752s had failed SD cards, restored by `dd`-cloning
  one of the two surviving working panels' card onto the dead ones. That cloned the source panel's CID
  (IP-ID) setting along with it: for over a day after the restore, `WHO` showed two distinct physical
  panels both registered live as IP-ID 14 simultaneously (192.168.4.83 and 192.168.4.100), while IP-ID
  12 never showed a live connection at all. Moving the intruding panel's CID to 12, the empty slot,
  resolved it; all four IDs now show distinct live addresses with no collision. Worth remembering for
  any future SD card recovery on these panels: the network identity travels with the card image, and
  restoring from a clone will need a manual CID fix afterward, not just a card swap.
- `REPORTCRESNET` on the AADS's leg returns exactly one live device:

  ```
  0A: ST-IO [v5.2], INPUT MODE: IN1=C, IN2=C, IN3=C, IN4=C
  ```

  The ST-IO's Cresnet leg is driven by the AADS, not the MC2E. All four of its inputs are configured in
  contact-closure mode, consistent with the alarm/dry-contact hypothesis in the evaluation above, though
  which physical contacts are wired to which input, and what the eight relay outputs drive, is still
  unknown and still requires physical tracing. Pulling the AADS's IR driver file for a named alarm-panel
  driver string was a dead end; it is a compiled binary format, not readable as text from the console.
- The AADS's program also defines two Crestron thermostats, `CHV-TSTAT`/`CHV-THSTAT`, at Cresnet IDs E1
  and E2, on the same leg as the ST-IO. Neither showed up in `REPORTCRESNET`, so neither is live right
  now. Confirmed with the house's owner: these are leftovers from Crestron-native thermostats that
  predated the current Lennox iComfort setup and were since replaced. They are not a live dependency,
  but the stale device definitions are still sitting in the compiled program and could be removed
  whenever the program is next touched, purely for cleanliness.

Only one CLX-4HSW4 exists. The originally remembered count of two was a misremembering of the garage
rack layout, confirmed with the house's owner. One CLX-4HSW4 is the correct, closed count.

### What this changes in the plan

The Cresnet lighting bus and the ST-IO turn out to be on two physically separate legs with two separate
bus masters. Decommissioning the AADS does not just remove audio functionality: it removes the ST-IO's
bus master, and whatever the ST-IO is wired to (most likely alarm-related, still unconfirmed) goes dark
with it, unless the ST-IO is rewired onto the MC2E's Cresnet leg before the AADS is pulled, or given some
other replacement I/O path. This is now a hard dependency of the AADS replacement work below, not an
optional follow-up.

## Lighting: what to do about the Cresnet bus

The CLX-1DIM8 and CLX-4HSW4 modules are staying, and they only speak Cresnet. That means something
has to remain (or be built) as a Cresnet bus master. There are two real paths here, and given the
answer that the wall keypads are expected to be replaced eventually, they interact with each other
more than they first appear to.

### Path A: keep the MC2E, add a one-time XSIG bridge

Hire a Crestron programmer for a single, narrowly scoped job: load a minimal program onto the MC2E
that maps every keypad button and every CLX channel to XSIG joins over TCP, with no logic beyond that
mapping. Home Assistant then talks to those joins using the same
[home-assistant-crestron-component](https://github.com/npope/home-assistant-crestron-component) that
the community has been running for years, exposing the CLX channels as HA lights and switches and the
keypad buttons as HA binary sensors or automation triggers.

That integration's own setup notes confirm the shape of the work: it needs a TCP/IP Client device and
an XSIG symbol wired up in the SIMPL program, with join numbers assigned explicitly (no wildcard
listener), and it recommends separate XSIG symbols for digital versus analog/serial signals to avoid
join numbering confusion. This matches the "static routing, no dynamic join" description in the prior
migration guide, so that part of the earlier analysis holds up.

The MC2E and the Cresnet bus itself are untouched. The bus keeps running exactly as designed, with its
existing master doing whatever polling and bus management it already does. This is the lowest-risk,
most reversible option: if it doesn't work out, native Crestron control still works underneath it.

The costs are a one-time programming fee (scope should be small since there's no logic to write, only
join mapping, which should keep the quote well below a full system reprogram), and the dependency that
any future change to the join map (adding a device, changing a mapping) needs another paid visit,
unless the program is written generically enough to leave headroom.

### Path B: bypass the MC2E, decode Cresnet directly

Tap the Cresnet bus Y/Z lines with a USB-to-RS-485 adapter, use CresnetMon (the real tool, not the
fabricated one) to observe traffic, and reverse engineer enough of the frame format to build a
from-scratch bridge that can both read keypad/module status and write dimmer/switch commands to the
CLX modules. This removes the MC2E and the AADS entirely and gives Home Assistant sole authority over
the bus, with no ongoing Crestron software dependency of any kind. The device inventory itself, which
Cresnet ID maps to which model, no longer needs to be discovered by sniffing; it is already known from
`REPORTCRESNET` above. What is still unknown, and still requires real sniffing, is the command frame
format: what bytes actually tell a CLX-1DIM8 to set a channel to a given level.

The risk profile is real, not theoretical. Cresnet is not publicly documented at the frame level, only
at the physical layer (RS-485, baud rate, wiring). CresnetMon confirms the traffic is observable but
does not tell you what it means. A polled bus that expects a master to periodically address each
device is a plausible architecture for Cresnet given how other Crestron bus protocols work, and a
naive bridge that doesn't replicate that polling correctly could leave the CLX modules unresponsive
until the software is right. This is weeks of reverse engineering and driver-writing, not a weekend of
YAML configuration, regardless of what the fabricated `cresnet2mqtt` note implied.

Here is where the keypad-replacement answer changes the calculus. If the keypads were staying forever,
Path B would mean permanently owning the reverse-engineered decode for both keypad events and CLX
commands, indefinitely, as a support burden. Since the keypads are planned for replacement, that half
of the protocol surface has a shelf life: once keypads are swapped for something HA-native, the bridge
only ever needs to talk to the CLX modules, a much smaller and more stable protocol surface than the
full mixed bus.

### Recommendation: Path A now, Path B folded into the keypad replacement phase

Do Path A first. It is cheap, low-risk, and unlocks Home Assistant control of lighting almost
immediately. Treat Path B as the endgame that happens at the same time the wall keypads actually get
replaced, not before, since that is the point where the low-voltage wiring at each switch location is
already being disturbed and the CLX modules are the only thing left on the bus worth decoding. Doing
the bus bypass at that point also means the reverse engineering effort only has to cover CLX command
frames, not the full keypad event vocabulary that would otherwise become dead weight.

Verified: the MC2E does hold live lighting logic today (see "Direct verification" above), so replacing
the AADS will not sever lighting control. The `REPORTCRESNET` output also already provides the full
device inventory for MC2E's leg (model and Cresnet ID for every keypad and CLX module), which is the
same bus-mapping step the prior notes' sniffing walkthrough proposed doing with a USB-to-RS-485 adapter.
That step is done; what remains for Path A is scoping and hiring the join-mapping program itself.

### Rejected: replacing the CLX modules too

Not evaluated as an option because it was ruled out by the constraint that the CLX modules stay. Worth
recording anyway: if that constraint ever changes, a full lighting rip-and-replace (Lutron Caseta/RA3,
Z-Wave switches, etc.) would remove the Cresnet dependency entirely without any bus reverse engineering.
That tradeoff only makes sense if the CLX hardware itself becomes a liability (failure, unavailable
parts), which is not the current situation.

## Audio: replacing the AADS

The AADS is being replaced outright, which was already the more clear-cut decision of the two. Its
real specs, per Crestron's own documentation, are a 12-channel Class G amplifier at roughly 45W/channel
into 8 ohms, a matrix switcher accepting up to 10 stereo line inputs, a base capacity of 6 stereo
zones (expandable via AAE units), dual AM/FM tuners, and IR/RS-232 ports used to interface non-Crestron
gear including security equipment. Removing it without replacement means dead speakers: no
amplification and no input routing.

Confirmed via direct verification above: the ST-IO's Cresnet leg is driven by the AADS, not the MC2E.
Pulling the AADS without a plan for the ST-IO takes down whatever the ST-IO's 8 relays and 4 inputs are
wired to, alarm-related or not. The options are to physically move the ST-IO onto the MC2E's Cresnet
leg before the AADS comes out, or to replace the ST-IO's function with something HA-native (a relay/
contact board on GPIO or ESPHome, for instance) at the same time. Either way, this has to be resolved
before, not after, the AADS is decommissioned.

| Option | Hardware | Zone model | Fit |
| :--- | :--- | :--- | :--- |
| Distributed smart amps | Sonos Amp, WiiM Amp, or similar per zone | One amp per zone, each with native streaming and native HA integration | Best fit if the number of active zones is small (roughly matches the AADS's base 6-zone capacity) and each zone should be independently addressable with no shared matrix |
| Multi-zone matrix amp | Dayton Audio DAX88, Monoprice 6-zone amplifier, or similar | One box, several zones, matrix source switching | Closer to a like-for-like replacement of the AADS's own matrix-plus-amp design, and cheaper per zone if most zones are in use |

Either option lets Home Assistant own per-zone volume, mute, source routing, and scenario automations
(the AADS's own DSP tone/volume compensation and radio tuners do not carry over, but that functionality
was tied to hardware being removed anyway, not to Crestron control specifically).

The right choice depends on how many zones are actually landed on the AADS today and how source
routing is actually used. This is not answerable remotely; see the verification checklist below for
the practical method (read the zone/source list off a TSW-752, then check the AADS's own rear terminals
in its living room cabinet).

### Rejected: keeping the AADS as a dumb amp only

Considered and rejected. The AADS's amplifier and matrix functions are not separable from its control
processor in a way that would let Home Assistant drive the amp/matrix hardware while ignoring the
Crestron logic; the only front door to those functions is the same 2-Series engine being removed for
lighting reasons. Once the decision was made to stop depending on Crestron's control layer, there is no
version of "keep the AADS hardware, replace only the software" available.

## Touch panels: replacing the TSW-752s

Confirmed that the TSW-752 runs on standard 802.3af PoE, not a Crestron-only power scheme, which means
the existing PoE cable runs and any 802.3af-capable switch or injector can be reused as-is for
replacement hardware. No rewiring should be needed, only a mounting and form-factor match at each
existing panel location.

Reasonable current options, both with native Home Assistant support:

- **Shelly Wall Display (X2i or XL)**: in-wall PoE-capable touch panel with direct HA/MQTT support.
  Announced and shipping as of the [Wall Display XL](https://www.notebookcheck.net/Shelly-quietly-launches-new-Wall-Display-XL-smart-home-hub.1190942.0.html)
  and [Wall Display X2](https://www.notebookcheck.net/Shelly-launches-new-Wall-Display-X2-smart-home-hub.982677.0.html)
  releases, with active discussion of real-world HA setups on the
  [Home Assistant community forum](https://community.home-assistant.io/t/shelly-wall-display-with-other-devices/759211).
- **Sonoff NSPanel Pro**: dedicated in-wall Android panel aimed at the same niche.

Avoid generic, unbranded Android wall panels regardless of price. The recurring failure mode reported
across the smart-home community is a panel that never receives an Android OS update past version 8 or
9, which breaks Home Assistant's companion app or dashboard rendering within a year or two. Both named
options above have a vendor with a track record of shipping updates, which is the deciding factor over
raw spec sheets.

Since the panels will be driven by Home Assistant directly rather than by Crestron or by the AADS,
this replacement does not depend on the outcome of the Path A/Path B lighting decision above, and can
proceed on its own schedule.

## Wall keypads: deferred

Confirmed via direct verification above: there are 9 keypads (model **CNX-B8**) across 7 rooms, two
rooms with two keypads each, which is exactly where the original "seven" came from. The room map for
each keypad is in "Direct verification" above; nothing here required opening a wall box. The keypads
stay for now. When the replacement phase happens, it should be combined with the Path B Cresnet bypass
discussed above, since both involve disturbing the same low-voltage wiring at the same locations, and by
that point the model, count, and room assignments are already known well enough to scope replacement
hardware per room.

## Alarm system: status unknown

Not yet known whether the alarm system is wired into Crestron at all. Two plausible tie-in points exist
in the current hardware. The alarm panel itself is a wall panel in the kitchen pantry, not rack-mounted,
and the wire runs between it and the living room AV cabinet are inside walls and not traceable by hand.
Confirming a tie-in means checking both ends independently, not following one continuous wire:

- The ST-IO's 8 relay outputs and 4 analog/digital inputs, which are exactly the kind of dry-contact
  interface an alarm panel would use for a Crestron tie-in (arm/disarm relay, zone status contacts).
  Confirmed present, powered, and on the AADS's Cresnet leg (not the MC2E's); all four inputs are
  configured in contact-closure mode, which is consistent with this hypothesis but does not confirm it.
  What is still unknown is which physical contacts land on which of the four inputs, and what the eight
  relay outputs actually drive.

  **Field notes from the AV cabinet (2026-08-04):** front-panel LED baseline at time of inspection was
  PWR green, NET yellow (confirms healthy Cresnet comms, consistent with the telnet findings above),
  and Input 1 red (that input is reading a closure right now; worth remembering as a baseline when the
  zone-trigger test happens later). The wiring behind the ST-IO is dense and unlabeled with tags,
  though there may be sharpie markings on individual cable jackets not yet found. The integrator
  appears to have run Cat5e for signal wiring generally rather than single-purpose cable: roughly two
  Cat5e cables land on the ST-IO itself (plausibly one carrying the 4 digital inputs plus common, one
  carrying some or all of the 8 relay pairs, riding spare pairs of the same cable rather than one wire
  per signal, but this is a guess to verify once untangled, not confirmed). There is also a passive
  RS-485 distribution strip nearby, no electronics, with five or six additional cables landing on it.

  **Resolved (2026-08-04): this cabinet holds two separate, independently-powered Cresnet buses, not
  one.** There are two Cresnet 24VDC power bricks in the cabinet. One feeds MC2E's own built-in NET
  terminal block directly (the bus carrying the 9 keypads and 7 garage lighting modules). The other
  feeds the passive distribution strip, and the ST-IO's NET cable lands on that same strip. This
  physically confirms what the console data already proved logically: the ST-IO sits on a Cresnet
  segment that belongs to the AADS, electrically separate from MC2E's, even though it's racked right
  next to the MC2E. It is very likely the physical continuation of the AADS's own Cresnet leg into this
  cabinet, with one of the strip's cables running back through the wall to the AADS itself.

  One loose thread this doesn't resolve: the strip has five or six cables, but AADS's own
  `REPORTCRESNET` only shows the ST-IO as a live device on that leg. Expected count for "ST-IO plus a
  link back to AADS" is more like two. The other three or four are either Cresnet devices not currently
  recognized by AADS's program (the hardware-side version of the stale thermostat definitions found
  earlier) or something not yet accounted for. Not urgent, but worth a look if the strip ever gets fully
  untangled.

  **Do not bridge or rewire anything on that strip without knowing what's already tied together** - the
  two buses are confirmed separate now, and joining them would combine two systems that were
  deliberately kept apart.
- The AADS's RS-232 and IR ports, which Crestron's own documentation calls out as intended for
  "non-Crestron devices ranging from CD changers to security systems." The AADS's currently loaded
  program includes an `.ird` IR driver database file, so this port is plausibly in active use for
  something, not just present unused.

**Brand confirmed: DSC.** Visible on the faceplate of the pantry wall panel. The exact model is still
unknown; the faceplate doesn't come off easily and identifying it further is deferred for now. DSC
covers a wide range of panels (PowerSeries, Neo, and older lines) with different Home Assistant
integration stories, so the recommendation below still waits on the model.

Until the exact model is known and the ST-IO's wiring is worked out, no integration recommendation can
be made here. Other common panel families (Honeywell/Resideo, Qolsys, Interlogix/GE) are ruled out now
that the brand is confirmed. This is the top verification item below because it blocks a decision, not
because it is hard.

## HVAC: independent of Crestron

Confirmed the Lennox HVAC system runs on its own thermostat, with no Crestron tie-in. This makes it the
most decoupled item in this whole plan: it can be worked on immediately, in parallel with everything
else, since removing the AADS or touching the Cresnet bus has no bearing on it.

The AADS's program does still define two Crestron-native thermostats (see "Direct verification" above)
from before the Lennox system was installed. They are confirmed stale, not live, and not a dependency
of anything in this section.

If the installed thermostat is a Lennox iComfort S30, S40, E30, or M30, the
[lennoxs30](https://github.com/PeteRager/lennoxs30) custom integration (installable via HACS) supports
both local LAN and Lennox cloud connections and is the direct path into Home Assistant. If the
installed equipment is an older, non-connected Lennox thermostat instead, this integration does not
apply and the fallback is a smart thermostat swap (e.g., an Ecobee or similar with native HA support)
or a dry-contact relay approach through a device like the ST-IO, if it turns out to be free.

## Plan of attack

1. **Finish verifying before spending anything.** MC2E/AADS telnet access and the keypad model are done
   (see "Direct verification" above). Still open: identify the alarm panel make/model and trace its
   wiring, including the ST-IO; identify the actual Lennox thermostat model; count the AADS's actively
   used audio zones and inputs; decide how the ST-IO survives the AADS's removal; put a password on both
   consoles.
2. **Start the HVAC integration immediately.** It is fully decoupled and low-risk; install and
   configure `lennoxs30` (or the appropriate alternative once the thermostat model is confirmed).
3. **Commission the Path A XSIG bridge.** Scope and hire a one-time programming job for the MC2E,
   confirmed to be small in scope since it is a join-mapping task, not new logic. Bring up the
   `home-assistant-crestron-component` integration against it.
4. **Replace the AADS.** Choose distributed smart amps or a matrix amp based on the zone count found in
   step 1, land the existing speaker wiring on the new hardware, and integrate with Home Assistant.
5. **Replace the TSW-752 panels.** Independent of the above; can happen in parallel with steps 3-4.
   Choose Shelly Wall Display or Sonoff NSPanel Pro based on size/placement per panel location.
6. **Resolve the alarm system**, once its wiring and panel identity are known from step 1. This may
   turn into its own follow-up document once there is something concrete to evaluate.
7. **Replace the wall keypads and fold in the Path B Cresnet bypass** as a later, combined phase, once
   the earlier phases have proven out Home Assistant as the daily driver for lighting and audio.

## Open verification checklist

- [x] Telnet into the MC2E and the AADS to confirm where lighting logic resides. Done 2026-08-04; see
      "Direct verification" above. Both hold live, independent programs; MC2E is the IP master and owns
      the lighting Cresnet leg, AADS is a peer and owns the ST-IO's Cresnet leg.
- [x] Get a keypad model number. Confirmed **CNX-B8**, 9 units, via `REPORTCRESNET`, no wall box opened.
- [x] Get a room map for the keypads and lighting modules. Confirmed via each program's `.dsc`
      descriptor file: 9 keypads across 7 rooms, all 7 lighting modules centralized in the garage.
- [ ] Identify what lands on each of the ST-IO's 4 inputs (confirmed all in contact-closure mode) and 8
      relay outputs, in the living room AV cabinet. A continuous wire trace to the pantry isn't
      possible, the run is inside walls, so this means checking both ends independently rather than
      following one physical cable. For the 4 inputs, the practical method is empirical, not a trace:
      disarm the system (put it on test with the monitoring company first if it's monitored), then
      trigger one zone at a time and watch which of the ST-IO's front-panel INPUT LEDs reacts. Baseline
      before any testing: PWR green, NET yellow, Input 1 red, recorded 2026-08-04. Confirmed safe to
      poke at without risking the lighting bus: the ST-IO's leg is a separate, independently-powered
      Cresnet bus from MC2E's, not a shared one. The 8 relays are harder since nothing can trigger them
      remotely; rely on labels, wire characteristics, and what's visible inside the alarm panel's own
      cover, or call the monitoring company for install records if it's monitored.
- [ ] Identify the alarm panel's exact model. Brand confirmed DSC (2026-08-04) from the faceplate; the
      faceplate doesn't come off easily so the model is still unknown. Need a way to read it without
      prying the cover off - check for a label inside the door if it opens without full removal, or ask
      the monitoring company if it's monitored, they'll have it on file.
- [ ] Identify the exact Lennox thermostat model installed.
- [ ] Count how many audio zones and line inputs are actually in active use on the AADS today. Not
      answerable via telnet: the `.fp2` front-panel data file turned out to be generic firmware menu
      strings, not project-specific zone names. The practical path is to read the zone/source list
      directly off a TSW-752's audio page (fastest, shows what the live program has configured), then
      check the AADS's rear terminal blocks, in its living room audio cabinet, for which zone and line-input terminals
      actually have wire landed on them (configured vs. physically wired can differ), and ideally test
      each zone end to end for actual sound before finalizing a replacement BOM.
- [ ] Decide how the ST-IO keeps functioning once the AADS, its current Cresnet bus master, is
      decommissioned: rewire it onto the MC2E's leg, or replace it with something else entirely.
- [ ] Get quotes from at least one independent Crestron programmer for the scoped Path A join-mapping
      job, to confirm the one-time cost assumption in this plan.
- [ ] Set a console password on both the MC2E and the AADS, or otherwise restrict access to port 23;
      both are currently reachable with no authentication at all despite password support being
      available.
