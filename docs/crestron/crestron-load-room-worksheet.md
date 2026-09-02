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
whoever is standing at the panel. `Pathway` and `Perimeter` are that case,
confirmed by pde: four separate loads, one pair in the Kitchen and one in the
Living Room, sharing two labels between them. The rooms in this table are the
authority, so two rows with the same name and different rooms are two loads.

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
| `d103` | Perimeter       | load  | `d125`                         | Kitchen         |
| `d104` | Outdoor Kitchen | load  | `d144`, `d187`, `d206`, `d247` | Outdoor Kitchen |
| `d105` | North           | load  | -                              | Dining Room     |
| `d106` | Living Off      | group | `d146`                         | Living Room     |
| `d107` | South           | load  | -                              | Dining Room     |
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
| `d183` | Home Perimeter  | load | `d246`                         | Outside         |
| `d184` | Entry Perimeter | load | -                              | Entry           |
| `d185` | Garage Sconces  | load | `d244`                         | Outside         |
| `d186` | Patio South     | load | `d126`, `d166`                 | Courtyard       |
| `d187` | Outdoor Kitchen | load | `d104`, `d144`, `d206`, `d247` | Outdoor Kitchen |
| `d188` | Patio North     | load | `d164`                         | Courtyard       |

## Patio (`LIGHT-pg01-zn06`)

| Join   | Name            | Kind  | Also                           | Room            |
| ------ | --------------- | ----- | ------------------------------ | --------------- |
| `d201` | Path            | scene | -                              |                 |
| `d202` | Night           | scene | -                              |                 |
| `d203` | Fiesta          | scene | -                              |                 |
| `d204` | Patio (All On)  | scene | -                              |                 |
| `d205` | Club            | scene | -                              |                 |
| `d206` | Outdoor Kitchen | load  | `d104`, `d144`, `d187`, `d247` | Outdoor Kitchen |
| `d207` | Pool            | scene | -                              |                 |
| `d208` | Area Off        | group | `d108`, `d128`, `d148`, `d168` |                 |

## Modes (`LIGHT-pg01-zn07`)

| Join   | Name       | Kind  | Also   | Room |
| ------ | ---------- | ----- | ------ | ---- |
| `d221` | Holiday    | scene | -      |      |
| `d222` | Security   | scene | `d242` |      |
| `d223` | Vacation   | scene | -      |      |
| `d224` | Party      | scene | -      |      |
| `d225` | Goodbye    | scene | -      |      |
| `d226` | (blank)    | blank | -      |      |
| `d227` | Good Night | scene | -      |      |
| `d228` | (blank)    | blank | -      |      |

## Others (`LIGHT-pg01-zn08`)

| Join   | Name            | Kind  | Also                           | Room            |
| ------ | --------------- | ----- | ------------------------------ | --------------- |
| `d241` | North Sink      | load  | -                              | Office          |
| `d242` | Security        | scene | `d222`                         |                 |
| `d243` | East Hall       | load  | -                              | Guest Suite     |
| `d244` | Garage Sconces  | load  | `d185`                         | Outside         |
| `d245` | Pool Bath       | load  | -                              | Office          |
| `d246` | Home Perimeter  | load  | `d183`                         | Outside         |
| `d247` | Outdoor Kitchen | load  | `d104`, `d144`, `d187`, `d206` | Outdoor Kitchen |
| `d248` | (blank)         | blank | -                              |                 |

## Distinct load names

28 names across 41 load buttons. Fill the tables above rather than this list; it
is here to show the size of the job.

`Ambient`, `Bath Diagonal`, `Bath Perimeter`, `Bed Diagonal`, `Bed Perimeter`,
`Cabinet`, `Door`, `East Hall`, `East Seating`, `Entry Center`,
`Entry Perimeter`, `Garage Sconces`, `Hallway`, `Home Perimeter`, `Island`,
`North`, `North Sink`, `Outdoor Kitchen`, `Pathway`, `Patio North`,
`Patio South`, `Perimeter`, `Pool Bath`, `Powder`, `Range`, `South`, `Table`,
`West Seating`.
