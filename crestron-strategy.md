# Crestron to Home Assistant: Migration Strategy

This document is the plan: what stays, what gets replaced, the options considered for each
subsystem, and why. The supporting evidence (hardware inventory, telnet verification, evaluation
of prior AI-generated notes, raw device dumps) lives in
[crestron-migration.md](crestron-migration.md). When a claim here depends on something confirmed
over telnet or by physical inspection, it links back there rather than repeating the evidence.

The goal is not to remove Crestron everywhere. The CLX-* lighting modules stay. The AADS and the
TSW-752 touch panels are explicitly being replaced. The wall keypads are staying for now but are
expected to be replaced eventually, once a later phase gets to them. Everything below follows
from those constraints.

For where the investigation currently stands and what physical verification is still open, see
["Status as of" and "Open verification checklist" in crestron-migration.md](crestron-migration.md#status-as-of-2026-08-04-for-picking-this-back-up).

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
fabricated one, see [crestron-migration.md](crestron-migration.md#fabricated)) to observe traffic, and
reverse engineer enough of the frame format to build a from-scratch bridge that can both read
keypad/module status and write dimmer/switch commands to the CLX modules. This removes the MC2E and the
AADS entirely and gives Home Assistant sole authority over the bus, with no ongoing Crestron software
dependency of any kind. The device inventory itself, which Cresnet ID maps to which model, no longer
needs to be discovered by sniffing; it is already known from `REPORTCRESNET`
(see [crestron-migration.md](crestron-migration.md#mc2e)). What is still unknown, and still requires
real sniffing, is the command frame format: what bytes actually tell a CLX-1DIM8 to set a channel to a
given level.

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

Verified: the MC2E does hold live lighting logic today
(see [crestron-migration.md](crestron-migration.md#mc2e)), so replacing the AADS will not sever
lighting control. The `REPORTCRESNET` output also already provides the full device inventory for
MC2E's leg (model and Cresnet ID for every keypad and CLX module), which is the same bus-mapping step
the prior notes' sniffing walkthrough proposed doing with a USB-to-RS-485 adapter. That step is done;
what remains for Path A is scoping and hiring the join-mapping program itself.

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

Confirmed via direct verification (see [crestron-migration.md](crestron-migration.md#aads)): the
ST-IO's Cresnet leg is driven by the AADS, not the MC2E. Pulling the AADS without a plan for the ST-IO
takes down whatever the ST-IO's 8 relays and 4 inputs are wired to, alarm-related or not. The options
are to physically move the ST-IO onto the MC2E's Cresnet leg before the AADS comes out, or to replace
the ST-IO's function with something HA-native (a relay/contact board on GPIO or ESPHome, for instance)
at the same time. Either way, this has to be resolved before, not after, the AADS is decommissioned.

| Option | Hardware | Zone model | Fit |
| :--- | :--- | :--- | :--- |
| Distributed smart amps | Sonos Amp, WiiM Amp, or similar per zone | One amp per zone, each with native streaming and native HA integration | Best fit if the number of active zones is small (roughly matches the AADS's base 6-zone capacity) and each zone should be independently addressable with no shared matrix |
| Multi-zone matrix amp | Dayton Audio DAX88, Monoprice 6-zone amplifier, or similar | One box, several zones, matrix source switching | Closer to a like-for-like replacement of the AADS's own matrix-plus-amp design, and cheaper per zone if most zones are in use |

Either option lets Home Assistant own per-zone volume, mute, source routing, and scenario automations
(the AADS's own DSP tone/volume compensation and radio tuners do not carry over, but that functionality
was tied to hardware being removed anyway, not to Crestron control specifically).

The right choice depends on how many zones are actually landed on the AADS today and how source
routing is actually used. This is not answerable remotely; see the
[verification checklist in crestron-migration.md](crestron-migration.md#open-verification-checklist)
for the practical method (read the zone/source list off a TSW-752, then check the AADS's own rear
terminals in its living room cabinet).

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

There are 9 keypads (model CNX-B8) across 7 rooms, two rooms with two keypads each
(see [crestron-migration.md](crestron-migration.md#mc2e) for the room map). The keypads stay for now.
When the replacement phase happens, it should be combined with the Path B Cresnet bypass discussed
above, since both involve disturbing the same low-voltage wiring at the same locations, and by that
point the model, count, and room assignments are already known well enough to scope replacement
hardware per room.

## Alarm system: no recommendation yet

The alarm panel's brand is confirmed DSC, but the exact model and the ST-IO's wiring are still open
(see [crestron-migration.md](crestron-migration.md#alarm-system-status-unknown) for the field notes and
what's been ruled out so far). DSC covers a wide range of panels with different Home Assistant
integration stories, so no recommendation can be made here until the model is known. This is the
top-priority verification item precisely because it blocks a decision, not because it is hard.

## HVAC: independent of Crestron

The Lennox HVAC system runs on its own thermostat, with no Crestron tie-in
(see [crestron-migration.md](crestron-migration.md#aads) for the confirmation that the AADS's two
Crestron-native thermostat definitions are stale leftovers, not a live dependency). This makes it the
most decoupled item in this whole plan: it can be worked on immediately, in parallel with everything
else, since removing the AADS or touching the Cresnet bus has no bearing on it.

If the installed thermostat is a Lennox iComfort S30, S40, E30, or M30, the
[lennoxs30](https://github.com/PeteRager/lennoxs30) custom integration (installable via HACS) supports
both local LAN and Lennox cloud connections and is the direct path into Home Assistant. If the
installed equipment is an older, non-connected Lennox thermostat instead, this integration does not
apply and the fallback is a smart thermostat swap (e.g., an Ecobee or similar with native HA support)
or a dry-contact relay approach through a device like the ST-IO, if it turns out to be free.

## Plan of attack

1. **Finish verifying before spending anything.** MC2E/AADS telnet access and the keypad model are done
   (see [crestron-migration.md](crestron-migration.md#direct-verification-whats-actually-on-the-wire-2026-08-04)).
   Still open: identify the alarm panel make/model and trace its wiring, including the ST-IO; identify
   the actual Lennox thermostat model; count the AADS's actively used audio zones and inputs; decide how
   the ST-IO survives the AADS's removal; put a password on both consoles. Full list in
   [crestron-migration.md's open verification checklist](crestron-migration.md#open-verification-checklist).
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
