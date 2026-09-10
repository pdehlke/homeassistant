# Lighting load to room worksheet

Every button on the TSW-752 lighting pages against the Home Assistant area its
load belongs to. Filled in by pde on 2026-09-02. The joins and names come from
the panel project and the AADS's own serial dump, recorded in
[crestron-tsw-panel-control-path.md](crestron-tsw-panel-control-path.md).

Every `Room` value is a real Home Assistant area, matched by exact string against
the live registry. `Outdoor Kitchen` was created on 2026-09-02 to complete the
set; the other nine already existed.

## How to read it

The `Room` column is the physical room, not the Crestron zone page. The pages are
groupings of what is reachable from a given panel rather than rooms, which is why
`Master Suite` carries two patio loads and `Entry` carries the outdoor kitchen.
Ten areas span eight pages and the two sets do not line up anywhere.

Rows marked `scene`, `group` or `blank` need no room. Only `load` rows do.

The `Also` column lists the other joins carrying the same name, and a repeated
name means one of two different things.

Sometimes it is one load surfaced on several pages. `Outdoor Kitchen` is that
case and it is proven: on 2026-09-02 pressing `d104` drove `d144`, `d187`, `d206`
and `d247` high in the same instant. Five buttons, one load, one room.

Sometimes it is two loads sharing a label that the page header disambiguates for
whoever is standing at the panel. `Pathway` and `Perimeter` were read as that
case on 2026-09-02: four separate loads, one pair in the Kitchen and one in the
Living Room, sharing two labels between them. The rooms in this table are the
authority, so two rows with the same name and different rooms are two loads --
**except that the Kitchen half of this specific pair was wrong.** Confirmed by
pde 2026-09-05: `d103` ("Perimeter" on the Dining page) drives the same fixture
as the Kitchen's own Pathway. There is no distinct "Kitchen Perimeter" load.
The Living Room's own Pathway/Perimeter pair (`d121`/`d125`) is unaffected --
this correction is specific to `d103`.

`d103`'s row below is kept for the historical record, but as of 2026-09-06
([issue #22](https://github.com/pdehlke/homeassistant/issues/22)) it is no
longer merely "kept" -- it is exactly the join the bridge presses for Kitchen
Pathway. `d145`, Kitchen's own "Pathway" button, still sits inside the
forbidden alarm range and is still never pressed; `d103` is the safe alias
that replaced the MC2E as Pathway's control path entirely. See
[crestron-ha-bridge.md](crestron-ha-bridge.md#kitchen-pathway-moved-off-the-mc2e-entirely)
for the migration.

`d183`/`d246`'s "Home Perimeter" rows below have the same problem the original
Pathway/Perimeter read did. Confirmed by pde 2026-09-06
([issue #23](https://github.com/pdehlke/homeassistant/issues/23)): pressing
either one lights the same garage dimmer LED as Door (`d181`), not a distinct
Outside fixture. They are folded into `entry_door` as aliases in the bridge
now, the same treatment `d103` got. The real Home Perimeter is a genuinely
different physical control, a Foyer keypad button that turned out to operate
Cresnet device `0x74` (a CLX-4HSW4) directly, entirely outside the digital join
numbering this whole worksheet is built from. See
[crestron-ha-bridge.md](crestron-ha-bridge.md#home-perimeter-was-never-a-real-load-either)
for the full trace.

Four Home Assistant areas carry no row here: Garage, Gym, Garage Mechanical
Closet and North Mechanical Closet. Confirmed 2026-09-02 as genuinely having no
Crestron lighting rather than as a gap in this map.

Naming note. Three names in this table differ from what the Crestron hardware
reports, and the hardware strings were left alone so captures stay verifiable.
The panel sends `s11 = 'Studio'` and the MC2E descriptor says `203 - Studio` for
keypad `0x6D`, but the room is the Office. The Cresnet captures label a load
`Sink Area`; it is `North Sink`. The panel room list says `Guest Room`; it is the
Guest Suite.

## Dining (`LIGHT-pg01-zn01`)

| Join   | Name            | Kind  | Also                           | Room            |
| ------ | --------------- | ----- | ------------------------------ | --------------- |
| `d101` | Table           | load  | -                              | Dining Room     |
| `d102` | Powder          | load  | `d127`, `d142`                 | Dining Room     |
| `d103` | Perimeter       | load* | `d125`                         | Kitchen         |
| `d104` | Outdoor Kitchen | load  | `d144`, `d187`, `d206`, `d247` | Outdoor Kitchen |
| `d105` | North           | load  | -                              | Dining Room     |
| `d106` | Living Off      | group | `d146`                         | Living Room     |
| `d107` | South           | load  | -                              | Dining Room     |

\* Not a load of its own; drives the Kitchen's own Pathway fixture. See the note above.
| `d108` | Area Off        | group | `d128`, `d148`, `d168`, `d208` | Dining Room     |

## Living Rm (`LIGHT-pg01-zn02`)

| Join   | Name         | Kind  | Also                           | Room        |
| ------ | ------------ | ----- | ------------------------------ | ----------- |
| `d121` | Pathway      | load  | `d145`                         | Living Room |
| `d122` | West Seating | load  | -                              | Living Room |
| `d123` | Ambient      | load  | -                              | Living Room |
| `d124` | East Seating | load  | -                              | Living Room |
| `d125` | Perimeter    | load  | `d103`                         | Living Room |
| `d126` | Patio South  | load  | `d166`, `d186`                 | Courtyard   |
| `d127` | Powder       | load  | `d102`, `d142`                 | Dining Room |
| `d128` | Area Off     | group | `d108`, `d148`, `d168`, `d208` |             |

## Kitchen (`LIGHT-pg01-zn03`)

| Join   | Name            | Kind  | Also                           | Room            |
| ------ | --------------- | ----- | ------------------------------ | --------------- |
| `d141` | Range           | load  | -                              | Kitchen         |
| `d142` | Powder          | load  | `d102`, `d127`                 | Dining Room     |
| `d143` | Island          | load  | -                              | Kitchen         |
| `d144` | Outdoor Kitchen | load  | `d104`, `d187`, `d206`, `d247` | Outdoor Kitchen |
| `d145` | Pathway         | load  | `d121`                         | Kitchen         |
| `d146` | Living Off      | group | `d106`                         | Living Room     |
| `d147` | Cabinet         | load  | -                              | Kitchen         |
| `d148` | Area Off        | group | `d108`, `d128`, `d168`, `d208` |                 |

## Master Suite (`LIGHT-pg01-zn04`)

| Join   | Name           | Kind  | Also                           | Room          |
| ------ | -------------- | ----- | ------------------------------ | ------------- |
| `d161` | Bed Perimeter  | load  | -                              | Primary Suite |
| `d162` | Hallway        | load  | -                              | Primary Suite |
| `d163` | Bed Diagonal   | load  | -                              | Primary Suite |
| `d164` | Patio North    | load  | `d188`                         | Courtyard     |
| `d165` | Bath Perimeter | load  | -                              | Primary Suite |
| `d166` | Patio South    | load  | `d126`, `d186`                 | Courtyard     |
| `d167` | Bath Diagonal  | load  | -                              | Primary Suite |
| `d168` | Area Off       | group | `d108`, `d128`, `d148`, `d208` |               |

## Entry (`LIGHT-pg01-zn05`)

| Join   | Name            | Kind | Also                           | Room            |
| ------ | --------------- | ---- | ------------------------------ | --------------- |
| `d181` | Door            | load | -                              | Entry           |
| `d182` | Entry Center    | load | -                              | Entry           |
| `d183` | Home Perimeter  | load* | `d246`                         | Outside         |
| `d184` | Entry Perimeter | load | -                              | Entry           |
| `d185` | Garage Sconces  | load | `d244`                         | Outside         |
| `d186` | Patio South     | load | `d126`, `d166`                 | Courtyard       |
| `d187` | Outdoor Kitchen | load | `d104`, `d144`, `d206`, `d247` | Outdoor Kitchen |
| `d188` | Patio North     | load | `d164`                         | Courtyard       |

\* Not a load of its own; drives the same fixture as Door (`d181`). See the note above.

## Patio (`LIGHT-pg01-zn06`)

Filled in as `scene` for every non-load button 2026-09-02, on the same "grouped
programming, not loads" theory used for the Modes page. A CIP-only trace on 2026-09-10
(registering on the freed TSW-752 slot and watching which digital joins responded to each
press) undercounted what these buttons actually do, and its raw findings are kept below only
as a record of that gap, not as the final answer. **pde confirmed by direct, on-site
observation what each button actually drives:**

| Join   | Name           | Drives, per pde's direct observation |
| ------ | -------------- | ------------------------------------- |
| `d201` | Path           | Entry Center + Patio Pathway (the south-pathway subset of the Patio South circuit) |
| `d202` | Night          | The courtyard's four corners |
| `d203` | Fiesta         | The four corners, Patio Sconces, the south pathway, and Entry Center + Perimeter |
| `d204` | Patio (All On) | Every patio light, but not the entry lights or Outdoor Kitchen |
| `d205` | Club           | Entry Perimeter, Patio Sconces, and a subset of the east/west/north corners |
| `d207` | Pool           | Entry Center, Patio Sconces, and a subset of the east/west/north/south corners |

Several of the fixtures named above (the four corners, Patio Sconces, the south pathway) have
no button of their own anywhere in the panel project and no existing Load in
`custom_components/crestron_cip/const.py`, and most of the six buttons above never produced a
correlated join in the CIP-only trace at all — see "What the CIP-only trace saw" below for why.
**pde's call: wire each button up as one opaque macro Load rather than chase down every
individual fixture inside it**, since he expects to use these as whole scenes in future
automations rather than address their contents separately. Done 2026-09-10: all six are real
`Load` entries in `const.py` now (`courtyard_path`, `courtyard_night`, `courtyard_fiesta`,
`courtyard_patio_all_on`, `courtyard_club`, `courtyard_pool`), wired into Home Assistant as
Template Lights in the Courtyard area exactly like every other load, and added to the Homie
Dashboard's Lights chip under Courtyard.

| Join   | Name            | Kind  | Also                           | Room            |
| ------ | --------------- | ----- | ------------------------------ | --------------- |
| `d201` | Path            | load  | -                               | Courtyard       |
| `d202` | Night           | load  | -                               | Courtyard       |
| `d203` | Fiesta          | load  | -                               | Courtyard       |
| `d204` | Patio (All On)  | load  | -                               | Courtyard       |
| `d205` | Club            | load  | -                               | Courtyard       |
| `d206` | Outdoor Kitchen | load  | `d104`, `d144`, `d187`, `d247` | Outdoor Kitchen |
| `d207` | Pool            | load  | -                               | Courtyard       |
| `d208` | Area Off        | group | `d108`, `d128`, `d148`, `d168` | -               |

Each button's own indicator join (`d201`-`d205`, `d207`) doubles as its feedback: it clears on
Area Off or when a different button in the same mutually-exclusive scene-selector group takes
over, the same behavior Goodbye/Good Night have always shown on the Modes page. Verified live
2026-09-10 for all six: `light.turn_on` through Home Assistant correctly activated each macro
(confirmed against every CIP-visible correlate below) and `light.turn_off` on the same join
cleanly reversed it, including the courtyard's own known loads Fiesta and Patio (All On) had
turned on. No `press_on`/`press_off` split needed; ordinary toggle behavior throughout.

**What the CIP-only trace saw**, incomplete and superseded by pde's direct observation above:
Path (`d201`) correlated with Entry Center (`d182`) turning on; Patio Pathway never surfaced on
any join. Fiesta (`d203`) correlated with Patio South (`d126`/`d166`/`d186`) and Entry
Perimeter (`d184`); the four corners, Patio Sconces and south pathway it also drives never did.
Patio (All On) (`d204`) correlated with Patio North (`d164`/`d188`). Night (`d202`), Club
(`d205`) and Pool (`d207`) produced no correlated digital-join change in an 8-second watch
window each, despite each one genuinely driving real fixtures per pde.

The likely reason a CIP-only trace missed real fixtures: it only sees what the AADS panel
project reports back to a registered panel client. `outside_home_perimeter`'s history in
this same document is the precedent — the real Home Perimeter circuit turned out to be a
direct Cresnet command to `0x74`, never visible on any digital or analog join the panel
reports at all, findable only via SDEBUG on the Cresnet bus. Some or all of Night, Club, Pool
and the uncorrelated parts of Path/Fiesta most likely work the same way. Nobody has chased
those down to real Cresnet device/join numbers, and per pde's call above, nobody needs to:
the macro Loads work end to end without it.

Patio's own Area Off (`d208`) turned off Patio North and Patio South but did not reach Entry
Center or Entry Perimeter, left on by Path and Fiesta during testing and turned off afterward
via Home Assistant (`light.turn_off`) instead. Its feedback join is aliased with the other
four Area Off buttons (the `Also` column above), but its press action is scoped to this page's
own loads, not a house-wide reset.

## Modes (`LIGHT-pg01-zn07`)

Filled in as `scene` for every button 2026-09-02, on the theory that a page called
"Modes" holds macros rather than loads. That held for six of the eight, but not
Holiday: pde traced it physically 2026-09-06 and found it switches a real
fixture, the outdoor eave receptacles used for holiday lights, not a macro over
other loads. Reclassified below on that basis
([issue #19](https://github.com/pdehlke/homeassistant/issues/19)). Security,
Vacation and Party are unresolved, not confirmed either way: pde saw no visible
effect from any of them at a physical panel, tested before Holiday's own
button was traced separately.

| Join   | Name       | Kind  | Also   | Room    |
| ------ | ---------- | ----- | ------ | ------- |
| `d221` | Holiday    | load  | -      | Outside |
| `d222` | Security   | scene | `d242` |         |
| `d223` | Vacation   | scene | -      |         |
| `d224` | Party      | scene | -      |         |
| `d225` | Goodbye    | scene | -      |         |
| `d226` | (blank)    | blank | -      |         |
| `d227` | Good Night | scene | -      |         |
| `d228` | (blank)    | blank | -      |         |

## Others (`LIGHT-pg01-zn08`)

| Join   | Name            | Kind  | Also                           | Room            |
| ------ | --------------- | ----- | ------------------------------ | --------------- |
| `d241` | North Sink      | load  | -                              | Office          |
| `d242` | Security        | scene | `d222`                         |                 |
| `d243` | East Hall       | load  | -                              | Guest Suite     |
| `d244` | Garage Sconces  | load  | `d185`                         | Outside         |
| `d245` | Pool Bath       | load  | -                              | Office          |
| `d246` | Home Perimeter  | load* | `d183`                         | Outside         |
| `d247` | Outdoor Kitchen | load  | `d104`, `d144`, `d187`, `d206` | Outdoor Kitchen |
| `d248` | (blank)         | blank | -                              |                 |

\* Not a load of its own; drives the same fixture as Door (`d181`). See the note above.

## Distinct load names

35 names across 48 load buttons, since the Patio page's six scene buttons were wired up as
opaque macro Loads (above). Fill the tables above rather than this list; it is here to show
the size of the job.

`Ambient`, `Bath Diagonal`, `Bath Perimeter`, `Bed Diagonal`, `Bed Perimeter`,
`Cabinet`, `Club`, `Door`, `East Hall`, `East Seating`, `Entry Center`,
`Entry Perimeter`, `Fiesta`, `Garage Sconces`, `Hallway`, `Holiday`,
`Home Perimeter`, `Island`, `Night`, `North`, `North Sink`, `Outdoor Kitchen`,
`Path`, `Pathway`, `Patio (All On)`, `Patio North`, `Patio South`, `Perimeter`,
`Pool`, `Pool Bath`, `Powder`, `Range`, `South`, `Table`, `West Seating`.
