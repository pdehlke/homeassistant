# DSC alarm zone inventory, read statically from the TSW-752 project

## Status

**Inventory only, 2026-09-07.** Twenty-four zones identified by name and AADS digital join,
entirely from the retrieved TSW-752 panel project. No CIP connection was made to produce this
document and none of these joins have ever been pressed. Live zone status (which zone is
currently open) is not wired into Home Assistant yet; see [What is not done](#what-is-not-done).

This is a direct continuation of the alarm work parked in
[crestron-alarm-open-questions.md](crestron-alarm-open-questions.md). Read that document first;
this one adds evidence to its puzzle rather than resolving it.

## Method

The same panel project already retrieved for lighting
([crestron-tsw-panel-control-path.md](crestron-tsw-panel-control-path.md)) has a second alarm page
that document never walked. `Environment.xml` (52 named pages) includes:

| uid | Page name |
|---|---|
| 22 | `5-SEC (ALARM-DSC-pg01-main)` |
| 52 | `5-SEC (ALARM-DSC-pg02-zones)` |

Page 22 is the numeric keypad, Arm To Home/Away, Fire/Medical/Panic and Chime, already covered by
[crestron-tsw-panel-control-path.md](crestron-tsw-panel-control-path.md#the-alarm-collision) and by
`FORBIDDEN_AADS_WRITE` in the bridge, with two corrections below. Page 52 is a status grid: 24
`Advanced Button` children, each with a `DigitalPressJoin` and a two-color label (white normal,
red selected), the same visual pattern the lighting pages use for on/off state. No live connection
was made or needed; every join and label below is read directly out of the XML, the same static
method [crestron-tsw-panel-control-path.md](crestron-tsw-panel-control-path.md) used for the
lighting map and that
[crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#the-safety-rule) requires
before touching anything alarm-adjacent: identify by name before doing anything else.

`Environment.xml` is gitignored, not committed, per this repo's policy against retrieved Crestron
program binaries. It lives at `docs/crestron/dumps/tsw752-favela-v3-environment.xml`; re-fetch with
`mac/ctp_getfile.py` in CresnetMon if it is missing.

## The zone table

| Join | Zone name (panel's own label) | Suggested `device_class` |
|---|---|---|
| `d201` | Front Door | door |
| `d202` | Garage Crtyrd Dr | door |
| `d203` | Garage-Kitchen Dr | door |
| `d204` | Garage Heat | heat |
| `d205` | Kitchen Dr / Wins | opening |
| `d206` | Dining Room Drs | door |
| `d207` | Living Drs / Wins | opening |
| `d208` | Living Motion | motion |
| `d209` | Master Bed Wins | window |
| `d210` | Master Bath Dr | door |
| `d211` | Master Bath Wins | window |
| `d212` | Room 1 Dr / Wins | opening |
| `d213` | Room 2 Dr / Wins | opening |
| `d214` | Room 1 / 2 Bath Dr | door |
| `d215` | Room 2 Motion | motion |
| `d216` | Pool Photobeam | motion |
| `d217` | Room 3 Wins | window |
| `d218` | Room 3 / 4 Dr | door |
| `d219` | Room 3/4 Bath Wins | window |
| `d220` | Room 3 / 4 Motion | motion |
| `d221` | Room 4 East Wins | window |
| `d222` | Room 4 West Wins | window |
| `d223` | East Garage OHD | garage_door |
| `d224` | West Garage OHD | garage_door |

Twenty-four zones, one contiguous join block, `d201`-`d224`, no gaps. "Master" is the panel's own
word; the rest of this project renamed that suite "Primary Suite" once it was reached from the
lighting side, so the two document sets use different words for the same physical rooms. "Wins" is
the panel's own abbreviation for windows, kept verbatim in the table above because
[crestron-tsw-panel-control-path.md](crestron-tsw-panel-control-path.md) already established that
panel labels are worth preserving exactly rather than normalized, in case a future join dispute
needs to match this table back to the source XML by eye.

One artifact worth recording so nobody re-discovers it and worries: the button at `d209` (Master
Bed Wins) has a `Selected` (red/open) state whose label text reads "Front Door" instead of "Master
Bed Wins", a copy-paste slip in the vendor's own VTPro-e project from 2019. It does not affect the
join number, only the color-changed state's tooltip text, and no other button has the same defect.

Which zone is "currently open" per pde's own report has not been independently confirmed from this
document; see [What is not done](#what-is-not-done).

## Two collisions this inventory found, that lighting work did not know about

[ADR 0066](../adr/0066-crestron-bridge-needs-two-cip-connections.md) and every doc that cites it
describe the AADS's shared join space as `d130`-`d148` plus `d93`. That was true of what had been
mapped at the time. It is not the whole alarm subsystem. This inventory adds two more collisions,
both confirmed against the live `_AADS_LOADS` table in CresnetMon's `const.py` as of `10ac882`.

### `d221`: Holiday's own join is also a zone join, and it is actively pressed

`outside_holiday` presses `d221` directly, with no alias, every time `light.turn_on` or
`light.turn_off` is called on it. `d221` is also this inventory's Room 4 East Wins zone. Unlike
every other lighting/alarm collision on record, this one is not a read-only alias sitting inside a
forbidden range: it is a **write**, in current production use, confirmed live on 2026-09-06 (see
[crestron-ha-bridge.md](crestron-ha-bridge.md#holiday-a-real-load-hiding-on-the-modes-page)), to a
join this document now shows doubles as an alarm zone signal.

Three readings, and this document does not choose between them:

1. **Subsystem gating is real**, the same theory already on record for `d130`-`d148`: the AADS
   disambiguates `d221` by which subsystem (`d91` Lights, `d93` Alarm) a client last entered, the
   crestron_cip bridge never sends either, and Holiday's proven, repeatable, lights-only effect is
   itself evidence the gating resolves to Lights by default. This is the reading the rest of this
   project's lighting work has been implicitly operating on for the `d130`-`d148` range already.
2. **The DSC integration is dead code**, reading 3 in
   [crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#the-puzzle). If so, `d221`
   has no alarm meaning to collide with in practice, whatever the panel project's UI implies.
3. **Both meanings are live and genuinely share the wire join**, and every Holiday toggle has been
   silently exercising a zone-related alarm action with no visible effect, because a zone-select or
   bypass state is not something a light or an LED would show.

Nothing here presses a join to distinguish these. Doing so is exactly what
[crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#the-safety-rule) rules out.
The panel-identity puzzle referenced when this section was written is now resolved (the panel is a
DSC PC1864, confirmed 2026-09-08 — see
[crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#resolved-2026-09-08-direct-visual-confirmation-dsc-not-apex)),
but that only narrows which of the three readings above is likely; it does not confirm the AADS's
serial link to the panel is actually transacting, which is what would settle this collision.
**Recorded here for a decision, not resolved:**
`FORBIDDEN_AADS_WRITE` could be widened to `d201`-`d224` on the strength of this document alone,
identifying the range by name exactly as the safety rule asks, but doing so would make
`outside_holiday` fail `const._validate()` at import, since it has no other join anywhere in the
panel project (confirmed by the exhaustive worksheet walk in
[crestron-load-room-worksheet.md](crestron-load-room-worksheet.md)). That trade, disabling a
working, pde-confirmed feature against an unconfirmed risk, is pde's call, not a change made here.

### `d206`: a read-only collision with Outdoor Kitchen's alias

`outdoor_kitchen`'s alias tuple includes `d206`, mirrored (never pressed) onto its canonical join
`d104` whenever it changes. `d206` is this inventory's Dining Room Drs zone. If that zone's contact
ever changes state while the DSC integration is live, the bridge's `_on_digital` would read it as
an Outdoor Kitchen state change and could flip `light.outdoor_kitchen`'s reported (not real) state
in Home Assistant. This is a correctness risk, not a write-safety one: the bridge never presses
`d206`, so nothing physical happens, only what Home Assistant believes about a light already proven
otherwise reliable.

### A smaller gap worth naming while here: `d149` and `d187`/`d188`

Walking page 22 for this document turned up three more alarm-subsystem joins outside the
documented `d130`-`d148` range: `d149` (Chime) and `d187`/`d188` (labeled "West Garage" and "East
Garage" on the keypad page, distinct from this inventory's `d223`/`d224` Garage OHD zone entries,
and distinct from `outdoor_kitchen`'s alias `d187` and `courtyard_patio_north`'s alias `d188` in
the lighting table). None of the three is pressed by any load today, so this is a latent gap in
`FORBIDDEN_AADS_WRITE` rather than an active one: nothing currently presses `149`, and `187`/`188`
are read-only aliases, same shape as `d206` above. Worth knowing before any future identification
pass considers a join in `149` or `187`-`194` "unclaimed and therefore safe."

## What is not done

Live zone status is not read anywhere in Home Assistant. The 24 `binary_sensor.alarm_zone_*`
entities created alongside this document (in `configuration.yaml`'s `template:` block) all report
`unknown` permanently; they exist to hold the name-to-join mapping as real entities rather than
only as this table, not to claim a live reading. Getting a real open/closed reading would mean
either widening what the already-running crestron_cip bridge inspects (a code change to a live,
security-adjacent integration) or a new listen-only registration (which needs a free TSW-752
IP-ID, and the only three besides the one already held by the bridge, `0x11`, `0x12`, `0x14`, are
presumably still driving real physical panels, unverified this session). Neither was attempted.

Which zone is "currently open," per pde's own report when this work was requested, was not
independently confirmed against live processor state for the reason above. If the physical DSC
keypad in the pantry shows live status text, that is the cheapest way to confirm it and doubles as
the answer to the first item in
[crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#how-to-settle-it-when-the-time-comes).

Whether the DSC integration is live at all, the central puzzle in
[crestron-alarm-open-questions.md](crestron-alarm-open-questions.md#the-puzzle), is unchanged by
this document. This inventory is static evidence about what the **panel project** expects to show,
not proof the **processor** is still driving it.
