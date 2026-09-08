# Real alarm integration: Crestron-relay vs. direct-wire, and reimplementing the panel UI

Written 2026-09-08 in response to a direct question from pde: [issue #24](https://github.com/pdehlke/homeassistant/issues/24)'s
actual intent was never the virtual Alarmo layer alone — that was the achievable slice, built and
verified the same day (see [alarmo-configuration.md](../alarmo/alarmo-configuration.md) and that
issue's own comments). The real goal is Home Assistant control of the house's **real** alarm
hardware. This document researches how, without touching the live system.

Two things distinguish this document from every prior alarm document in this repo: it identifies
the Apex Destiny 6100's actual manufacturer for the first time, and it evaluates a path — wiring
directly to the DSC panel, bypassing Crestron — that no prior document considered.

**Resolved, same day.** Everything below through "The hedge" was written against the
strong-but-unconfirmed reading that DSC PowerSeries is the real, live system. It is no longer
unconfirmed: pde visually identified the actual panel later the same day. It is a **DSC PC1864**,
with a **DSC PK5500** keypad in the pantry — not an Ademco Destiny 6100, which was never actually
present in this house. See
[crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#resolved-2026-09-08-direct-visual-confirmation-dsc-not-apex)
for the resolution. The Ademco research directly below is kept for the record; it was the
best-supported reading right up until the direct check ran, and the hardware options and
recommendation it leads to (Path B, DSC Keybus) are the ones that turned out correct. Only the
[hedge section](#the-hedge-if-its-actually-the-ademco-system) at the end is now fully moot.

## New evidence: the Apex Destiny 6100 is an Ademco/Honeywell panel, not DSC

This alone reframes [crestron-alarm-open-questions.md](crestron-alarm-open-questions.md)'s central
puzzle. The Apex Destiny 6100 was manufactured by **Ademco** (later absorbed into Honeywell), the
company behind the Vista panel line — a direct competitor to DSC, not a DSC product or a DSC OEM
rebrand. Sources: [Moore Protection's Destiny 6100 reference guide](https://www.mooreprotection.net/wp-content/uploads/2014/05/Apex-Density-Reference-Guide.pdf),
[the Destiny 6100 user manual](https://www.armsecuritysystems.com/app/uploads/2015/01/Apex-Destiny-6100-User-Manual.pdf),
and the [Destiny 6100 installation instructions](https://www.safe-tech.net/HONNEWELL/INSTALL%20MANUAL/DESTINY6100_EI.pdf)
(hosted, tellingly, under a Honeywell-branded path). Ademco/Honeywell panels use their own
proprietary keypad bus and their own RS-232 automation interface, wired and programmed nothing
like DSC's Keybus — Crestron's own official module for it, cited in
[crestron-apex-control-plane.md](crestron-apex-control-plane.md), is a completely separate module
family (`Destiny_6100_Arm_Disarm`) from what the AADS's compiled program actually runs
(`S2_DSC_PowerSeries_*`, confirmed by binary analysis in
[crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#what-the-aads-program-actually-contains)).

That distinction was already implicit in the existing documents — `crestron-apex-control-plane.md`
says outright "the Destiny 6100 serial parameters below come from Crestron's generic module
documentation rather than from anything observed in this house" — but nothing had identified Destiny
6100's manufacturer before now, and doing so changes which of the three parked readings is most
likely:

- **Reading 1 (subsystem gating: one system, two module sets)** now reads as far less likely. DSC
  and Ademco are different companies with incompatible protocols; a single physical panel cannot
  natively speak both, and Crestron's own module catalog treats them as entirely separate
  integrations, not two faces of one job.
- **Reading 2 (the DSC arrived later, as a real second system)** is now the best-supported reading.
  It requires nothing unusual: an older Ademco Destiny 6100 installed with the original 2008-era
  Crestron job (matching the MC2E's 2011 compile date — plausibly older still, since Destiny 6100 is
  1990s/2000s-era Ademco hardware), later replaced or supplemented by a DSC PowerSeries system
  whose Crestron integration was compiled 2019-11-15 — exactly the date on file for the AADS's live
  program. Two real, physical panels from two different eras and two different companies, the
  older one's chassis still visible and correctly identified by the owner, the newer one's Crestron
  integration the one actually running.
- **Reading 3 (the DSC modules are dead code)** is now less likely, though not eliminated — a full
  DSC module set (partition control ×8, serial queue, zone status, system status, virtual keypad
  feedback, LED-to-text) is a lot of dead weight to carry for a system never live, and it costs
  nothing to disprove with the read-only checks below.

**This still isn't fully settled.** What would settle it, cheaply and safely, exactly as
[crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#how-to-settle-it-when-the-time-comes)
already laid out:

1. Whether the DSC-branded keypad in the pantry shows live status (backlit, "Ready" or zone text).
   Purely visual — this is the fastest confirmation and needs pde at the panel, not a live
   connection.
2. An `SDEBUG` capture of the AADS's COM-A traffic (`Slot-02/COM-A`, where the program puts the DSC
   serial queue), read-only, using the existing `mac/sdebug.py` in CresnetMon exactly as it was used
   for the Home Perimeter investigation. **Attempted this session and blocked by the harness's
   permission classifier before it could run** — this specific action (a live diagnostic session
   against the AADS's console) needs pde's explicit go-ahead, either to grant it directly or to run
   `uv run python sdebug.py --host 192.168.4.61 --seconds 20` himself from `CresnetMon/mac/`. It's
   read-only with respect to the house (SDEBUG only toggles console print flags, never sends bus or
   serial commands) and self-tears-down in a `finally` block even on failure.

**Update, same day: settled by direct inspection instead.** Item 1 above turned out unnecessary in
the form written — pde didn't need to check the keypad's live status, he read the panel itself. It
is a DSC PC1864 with a DSC PK5500 keypad. There is no Ademco Destiny 6100 in this house and never
has been; the original visual identification that started this whole line of research was simply
wrong. The SDEBUG capture (item 2) is still unrun and still blocked by the harness's permission
classifier, but it was only ever needed to confirm *which brand*, and that question is now closed by
a stronger form of evidence than SDEBUG would have produced. What SDEBUG would still tell us, if
run, is narrower: whether the AADS's serial link to the panel is actively transacting today, not
which panel it's wired to.

Everything below was written planning against the strong-but-unconfirmed reading that DSC
PowerSeries is the real, live, currently-integrated system. That reading is now confirmed rather
than merely strong-but-unconfirmed, so [the hedge](#the-hedge-if-its-actually-the-ademco-system) at
the end is moot and left only for the record.

## Path A: integrate via Crestron

Extend `crestron_cip` (the same bridge already driving all thirty lighting loads) to also expose the
AADS's real alarm-related joins: arm home, arm away, disarm, per-partition status, and the 24 zone
joins already inventoried in
[crestron-alarm-zone-inventory.md](crestron-alarm-zone-inventory.md). Mechanically this is the same
CIP connection, the same `bridge.py` join-state pattern lighting already uses — no new hardware, no
new network path.

What it actually requires, in order:

1. **Both prerequisites are now settled.** The panel identity (DSC PC1864, above) no longer blocks
   this path, and the other gate — confirming the AADS's serial link to the panel is actually live,
   not just wired to matching hardware — is also done: an SDEBUG capture of `Slot-02` on 2026-09-08
   caught live DSC keypad LCD traffic in real time (a `901`/LCD-Update message decoding to a plain
   idle-screen clock display, timestamped to the second it was captured). See
   [crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#how-to-settle-it-when-the-time-comes)
   for the capture detail. Writing into `d130`-`d148`/`d93`, the range `FORBIDDEN_AADS_WRITE`
   currently refuses categorically, is still gated by
   [crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#the-safety-rule)'s safety
   rule, but the rule's own precondition for relaxing it, a real and transacting integration behind
   it, is now met. The remaining work on this path is entirely the join-identification and
   ADR-revision steps below, not further confirmation.
2. **Identify every join by name from the retrieved program**, the same standard the lighting work
   held itself to for all twenty-nine loads. The zone joins (`d201`-`d224`) are already named; the
   arm/disarm/status joins inside `d130`-`d148`/`d93` are not — that range is currently known only as
   "the DSC alarm keypad's shared range," never individually mapped the way the zone page was.
3. Formally revise `FORBIDDEN_AADS_WRITE` and the two ADRs that constrain it
   ([ADR 0066](../adr/0066-crestron-bridge-needs-two-cip-connections.md) references the
   `d130`-`d148` range directly), not just add a narrow exception, so the write-safety model stays
   coherent for whoever reads it next.

The house's alarm is not professionally monitored (confirmed by pde, 2026-09-08), so a wrong press
here has no false-dispatch consequence and there's no monitoring company to arrange a test window
with. The join-identification discipline above stays for its own reasons regardless — a wrong press
into an alarm-subsystem join can still trigger a local siren or leave the alarm's own state
corrupted, neither of which is anything to do with monitoring.

What it buys: the existing TSW-752 alarm page's actual "Arm To Home"/"Arm To Away" logic, chime
handling, and Fire/Medical/Panic buttons, exactly as programmed today, without needing to re-derive
DSC's protocol or trust a from-scratch reimplementation of arm/disarm semantics. If the AADS's DSC
integration turns out to be genuinely dead (reading 3), this path is not just risky, it's pointless —
there would be nothing live to expose.

This is the same shape of work `crestron-xsig-programmer-scope.md` already priced separately as
"Apex alarm migration," and the same one `crestron-apex-control-plane.md`'s Option 1 (add an XSIG
bridge to the AADS) describes — both written before the DSC finding, both still structurally correct
once "Apex" is read as "the DSC PC1864 that's actually installed."

## Path B: wire directly to the (real) DSC panel

Skip Crestron's mediation of the alarm entirely. Add a Home Assistant-facing interface directly to
the DSC panel's own Keybus — the same 4-wire bus (`Red`/`Black` power, `Yellow`/`Green` clock/data)
every DSC keypad and expansion module already uses.

### Does this require disconnecting the DSC from the AADS? No.

DSC PowerSeries Keybus is an explicitly multi-drop bus: PowerSeries panels support **up to 8
keypad-class devices** simultaneously, gated mainly by a combined 700 mA current budget and wire-run
length, not by device count alone
([source](https://www.alarmsystemstore.com/pages/dsc-pc1616-pc1832-pc1864-how-many-keypads-can-be-used)).
Crestron's own DSC integration almost certainly runs through a
[DSC IT-100](https://www.dsc.com/alarm-security-products/IT-100%20-%20PowerSeries%20Integration%20Module/22)
or equivalent module — a small board with "a 4-wire hook-up to KEYBUS" and a bidirectional RS-232
output — which is itself just one more device on that same bus, identical in kind to a keypad. Adding
a second, independent Keybus interface for Home Assistant is the same category of change as adding
another wall keypad: supported by design, not a rewiring or a cutover. Nothing about it touches the
pantry keypad, the IT-100-equivalent feeding Crestron, or any existing zone wiring.

**Caveat, since this repo's own discipline is "verify, don't guess":** this is standard DSC
architecture and well-precedented across the DSC/Home-Assistant hobbyist community, not something
specific to this house that's been confirmed here. Before wiring anything, physically confirm how
many keypad-class devices are already on this house's Keybus (a DSC installer or the panel's own
programming menu reports this) and check remaining current headroom, per the source above. That's a
five-minute check at the panel, not a redesign.

### Hardware options

| Option | Cost | Effort | Notes |
|---|---:|---|---|
| **[EyezOn EnvisaLink EVL-4EZR](https://www.eyezon.com/evl4.php)** | ~$110-120 | Plug into Keybus terminals, no soldering | Built into Home Assistant core (`envisalink` integration, [docs](https://www.home-assistant.io/integrations/envisalink/)). TCP/IP module that emulates a keypad. Some reported reliability issues with intermittent zone updates ([HA core issue #80441](https://github.com/home-assistant/core/issues/80441)). Also supports Honeywell/Ademco panels — see the hedge below. |
| **[esphome-dsckeybus](https://github.com/Dilbert66/esphome-dsckeybus)** (ESP32 + level-shifting circuit) | ~$15-25 in parts | DIY: basic soldering, no official assembled board sold — community members have shared PCB designs but there's no vendor to just buy one from | Produces a native Home Assistant `alarm_control_panel` (states: armed_away/armed_home/armed_night/pending/disarmed/triggered), per-zone `binary_sensor`s, low-battery/bypass/alarm status sensors, PGM relay outputs, and **`alarm_trigger_panic`/`alarm_trigger_fire`** services — the panel's own Panic and Fire keypad functions, reachable from Home Assistant. Supports up to 8 partitions and 64 zones. Users report it as more reliable than Envisalink for zone updates. |

### Network connectivity: EnvisaLink needs wired Ethernet, ESPHome doesn't

Asked directly, 2026-09-08: there's no Ethernet near the panel and no viable way to run a line
there. This matters, because the two hardware options above aren't equivalent on this axis.

The EnvisaLink EVL-4EZR is **wired Ethernet only**. Its own spec page lists "100BaseT Ethernet
Support" and an RJ45 connector as its sole network interface, with no WiFi mentioned anywhere
([source](https://www.eyezon.com/evl4.php)). The only workaround the EnvisaLink community reports is
adding a separate WiFi-to-Ethernet bridge next to it
([source](https://www.alarmsystemstore.com/pages/envisalink-4-use-with-wifi-ethernet)) — which
doesn't remove the constraint, it just adds a second device that also needs power and signal at the
panel.

`esphome-dsckeybus` doesn't have this problem. It runs on an ESP32, which has WiFi built in, so it
was never going to need a wired network in the first place — it only needs 12V/aux power (already
present at the Keybus terminals it wires into) and WiFi coverage reaching the panel's physical
location, not a data line.

Given the no-Ethernet constraint, `esphome-dsckeybus` is the only one of the two options that doesn't
need a workaround to be viable in this house at all. It was already the cheaper, more-featured option
in the table above; this makes it the clearer pick specifically for this installation, not just in
general. **Superseded by the next section**: this reasoning assumed building the ESP32 device was an
acceptable ask. It isn't, for this installation.

### No pre-made ESP32 board exists — back to EnvisaLink, with a WiFi bridge

Asked directly, 2026-09-08: pde wants to buy a finished device, not build one. Checked, rather than
assumed: **no vendor sells an assembled `esphome-dsckeybus`/`dscKeybusInterface` board.** The
project's own maintainer said so directly when a user asked the identical question: "No there isnt
one for the esp32... It's a very simple circuit so most people just build it on a piece of proto
board" ([source](https://github.com/Dilbert66/esphome-dsckeybus/discussions/140)). The community
PCB designs referenced there (WT32-ETH01, ESP32-C3 Super Mini + a level shifter) are bare board
files, not something orderable pre-assembled. This removes the ESP32 DIY option from consideration
entirely, not just as a preference — there's nothing to buy.

That reopens the EnvisaLink EVL-4EZR, with the no-Ethernet problem solved a different way: pair it
with an off-the-shelf **WiFi-to-Ethernet bridge** (a commodity WiFi range extender with an Ethernet
port, roughly $20-30) sitting next to it. Plug the bridge into the EnvisaLink with a short Ethernet
cable, power both, done — two retail boxes and one cable, no soldering, no code. This is a real
product category (used routinely to get smart-home hubs and game consoles onto WiFi when they only
have an Ethernet jack), not a novel workaround specific to this problem.

A second pre-assembled option surfaced in this research, with real caveats: **AlarmDecoder** sells
finished hardware (AD2USB, AD2Serial, and an "AD2pHAT" bundle that ships with a Raspberry Pi,
pre-flashed SD card, and case) that supports DSC PowerSeries, and the Raspberry Pi-based bundle has
WiFi built into the Pi itself. Not independently verified enough to recommend over EnvisaLink: their
store had a documented stretch of being effectively unpurchaseable (a Home Assistant Community
thread tracks reports of it being unavailable from late 2024 into November 2025, then coming back)
([source](https://community.home-assistant.io/t/status-of-alarmdecoder/811073)), their DSC
PowerSeries support was historically added via beta firmware rather than being the primary target
(Ademco/Honeywell Vista is), and current pricing could not be confirmed — their storefront is a
JS-rendered Square site this session's tooling couldn't read past the page title. Worth pde checking
directly if EnvisaLink-plus-bridge doesn't appeal, not ruled out, just unverified.

**Recommendation, updated:** EnvisaLink EVL-4EZR plus a commodity WiFi bridge, not
`esphome-dsckeybus`. It's a mature, official Home Assistant core integration from a stable dedicated
vendor, and the bridge workaround is a five-minute plug-together job rather than a project. The rest
of this document's Path B reasoning (multi-drop Keybus, no disconnection required, PC1864
compatibility) is unaffected by which hardware option is chosen.

### PC1864 specifically, not just "a DSC PowerSeries panel"

Written against the generic "DSC PowerSeries" category when this document was first researched;
confirmed against the exact model once pde identified it, 2026-09-08. Two things worth knowing now
that weren't knowable before:

- **This rules out the one real remaining risk to the hardware options above.** DSC's current
  lineup spans three incompatible families: the old **Classic** series, **PowerSeries** (what the
  PC1864 is), and **PowerSeries Neo**. Neo panels use a newer, encrypted Keybus variant ("Corbus")
  that neither hobbyist library below can speak — `taligentx/dscKeybusInterface`'s own README states
  plainly that Neo "use[s] a higher speed encrypted data protocol (Corbus) that is not currently
  possible to support." Until the model was confirmed, "DSC PowerSeries" could in principle have
  meant Neo, which would have made the whole EnvisaLink/ESPHome hardware section moot. It doesn't:
  PC1864 is a classic PowerSeries panel, squarely in the supported family.
- **Both hardware options above name the PC1864 explicitly**, not just the PowerSeries family
  generically: the EnvisaLink EVL-4 series lists "PC5020 (864)... and PC1864" in its own compatible-panel
  list ([source](https://www.alarmsystemstore.com/pages/envisalink-4-what-alarm-systems-are-compatible)),
  and `taligentx/dscKeybusInterface` (the library `esphome-dsckeybus` wraps) lists it among the
  panels "tested with," alongside PC1616 and PC1832
  ([source](https://github.com/taligentx/dscKeybusInterface)).

A second, independent corroboration: DSC's own spec sheet gives the PC1864 a maximum of **8
partitions**
([source](https://www.dsc.com/alarm-security-products/PC1864%20-%20PowerSeries%20Control%20Panel%20PC1864/2606)),
exactly matching the eight instances of `S2_DSC_PowerSeries_Partition_Control_v1_0` in the AADS's
compiled program (see
[crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#what-the-aads-program-actually-contains)).
That's not proof the AADS's serial link to the panel is presently transacting, but it's one more
data point that the program was written for this specific panel rather than some generic template.

Net effect on the recommendation below: none of the reasoning changes, but the risk it used to carry
("this needs to actually be classic PowerSeries once the model is known") is now closed rather than
assumed.

Either option gives Home Assistant a **genuine, hardware-backed `alarm_control_panel` entity** — not
a placeholder, not something virtual. At that point Alarmo becomes optional rather than load-bearing:
it could stay as the UI layer, with its zone list pointed at the real DSC-derived `binary_sensor`s
(dropping the current placeholder zones the moment real ones exist) and its arm/disarm actions
replaced by automations that call the DSC integration's own services directly — or Homie Dashboard's
`ALARM_ENTITY` could simply point straight at the DSC integration's own `alarm_control_panel`,
skipping Alarmo's indirection entirely. Either is a config-only decision once the hardware and base
integration are in place; nothing built for issue #24 today (the popup, the topbar buttons, the
Home Status tile) needs to change either way, since all of it already reads `CONFIG.alarmEntity`
generically.

### What this doesn't require

No Crestron programmer, no touching `FORBIDDEN_AADS_WRITE` or the AADS's live program at all, and no
dependency on the DSC PowerSeries Crestron modules being live code rather than dead code — this path
wires straight to the panel's own Keybus and never asks Crestron anything. This was already the one
path here that didn't need the blocked SDEBUG capture to proceed, and now that the panel identity is
directly confirmed (DSC PC1864), nothing about Path B is still waiting on anything.

## Reimplementing the panel design in Home Assistant

The photographed TSW-752 alarm page maps onto Home Assistant/Alarmo concepts reasonably directly,
whichever backend (Path A or B) feeds it:

| Panel element | HA/Alarmo equivalent |
|---|---|
| `READY` / `TROUBLE` status text | Alarmo's own status badge, or a dedicated `sensor` templated off the real DSC integration's status text sensor (the ESPHome component exposes this directly) |
| `Chime` toggle | A `switch`/`input_boolean` wired to the real panel's chime command, or the ESPHome component's own chime control if it exposes one |
| `Arm To Home` / `Arm To Away` | Alarmo's `alarm_arm_home`/`alarm_arm_away`, already wired in Homie Dashboard's security popup |
| Numeric keypad | Alarmo's own PIN entry (already built), or the real alarm's code if bypassing Alarmo entirely |
| `East Garage` / `West Garage` (lock icons, status only) | Already covered as two of the 22 wired Alarmo zones (`binary_sensor.alarm_zone_east_garage_ohd`/`west_garage_ohd`) once real data flows; these are status contacts, not actuators — see [alarmo-configuration.md](../alarmo/alarmo-configuration.md) |
| `Fire` / `Medical` / `Panic` | The house isn't monitored, so there's no central station these would notify either way — the design question is narrower than it first looks, but still real: a button in Home Assistant that doesn't reach the real panel at all is misleading next to controls that look like emergency controls. Path B's ESPHome component genuinely reaches these (`alarm_trigger_fire`, `alarm_trigger_panic` — real virtual-keypad presses, indistinguishable to the panel from a press at the physical keypad, which still means a locally sounding siren and the panel's own fire/panic state). Path A could too, if those joins are identified and the AADS's program genuinely relays them. Either way, these three buttons should not be built in Homie Dashboard until whichever backend is chosen actually reaches the real panel — a decorative panic button is worse than none. |
| Bottom bar (power, phone, settings, mute, vol±) | AV/Crestron-page chrome unrelated to the alarm function itself; not part of this scope |

Nothing here needs new dashboard code beyond what already exists for the virtual Alarmo layer —
`homie-dashboard.html`'s security popup and Overview C card already render arm/disarm/status
generically off `CONFIG.alarmEntity`. The work is entirely on the backend side (Path A or B), not the
frontend.

## The hedge: if it's actually the Ademco system (moot, kept for the record)

**This section no longer applies.** It was written while the panel's identity was still an inference
rather than a direct observation. pde has since read the panel itself: it is a DSC PC1864, not an
Ademco Destiny 6100, and no Ademco hardware has ever been confirmed present in this house. Kept
below unedited because the reasoning was sound given what was known at the time, and because it's
the record of why Path B's hardware research didn't have to wait on the puzzle either way.

If the pantry keypad turns out dark (no live status) and/or the SDEBUG capture shows COM-A silent —
i.e., reading 3 is confirmed and the DSC integration really is dead code — the live system is the
Ademco Destiny 6100 after all, and the direct-wire target changes accordingly. Ademco/Honeywell Vista
panels use a different keypad bus and a different automation interface than DSC, but the same
category of solution exists:

- **EnvisaLink EVL-4EZR again** — the same board explicitly supports "DSC and Honeywell/Ademco
  security systems" ([source](https://slickdeals.net/f/17480571-eyezon-envisalink-evl-4ezr-ip-security-interface-module-for-dsc-and-honeywell-ademco-security-systems-compatible-with-alexa-58-98)),
  so the hardware decision doesn't have to wait on the puzzle if EnvisaLink is the chosen route
  either way.
- **AlarmDecoder (AD2USB/AD2PI)**, an Ademco/Honeywell Vista-specific keybus interface with its own
  Home Assistant integration, is the DSC-side ESPHome project's closest Ademco equivalent — not
  independently researched in depth for this document, since the DSC reading is currently
  better-supported; worth a proper look only if the SDEBUG/visual check flips the reading.

The Destiny 6100's own RS-232 automation port (used to install a Path-A-equivalent connection
directly to the panel, not through Crestron) is also a genuine option if it's still functional after
however many years — `crestron-apex-control-plane.md`'s "Option 2: connect Home Assistant directly to
the Apex" already scoped this for the Crestron-relay context, and the same reasoning applies to a
non-Crestron adapter.

## Recommendation

**Path B, direct DSC Keybus interface**, is the better starting point. On hardware, EnvisaLink
EVL-4EZR plus a WiFi bridge is the pick — see
[the hardware-options update above](#no-pre-made-esp32-board-exists--back-to-envisalink-with-a-wifi-bridge)
for why the ESPHome DIY route dropped out once "buy, don't build" and "no Ethernet at the panel"
were both on the table at once. Path B itself doesn't wait on a Crestron programmer and doesn't
touch the AADS's live program or its forbidden-write range. Path A remains available later — nothing
about building Path B forecloses it, and Path A's own remaining blockers are now down to ordinary
implementation work (the SDEBUG capture that used to gate it is done, see above) — but it still
inherits the Crestron-programmer cost for a capability Path B gets more directly and without a
programmer at all.

The panel identity question that used to gate ordering hardware is now settled: DSC PC1864, DSC
PK5500 keypad, confirmed by direct inspection. What's still worth a five-minute check before
ordering, per [the Keybus section above](#does-this-require-disconnecting-the-dsc-from-the-aads-no),
is how many keypad-class devices are already on this house's Keybus and the remaining current
headroom — routine DSC installation hygiene, unrelated to which panel brand this house has.
