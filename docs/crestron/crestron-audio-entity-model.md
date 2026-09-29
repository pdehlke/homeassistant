# What the six audio zones look like in Home Assistant

**Decided and built 2026-09-29, verified live the same day.** The six AADS audio zones had no Home
Assistant entity of any kind until this work: the `crestron_cip` integration exposed them as
services only, which meant nothing in Lovelace could bind a toggle, a dropdown or a slider to them,
and the two Homie Scenes bubbles that drive them carried an empty affected-entity list because
there was no entity for them to glow from.

[crestron-av-zone-control-path.md](crestron-av-zone-control-path.md) parked this question as "Not
decided" and laid out the candidates. This document records which was chosen, what was rejected,
and the four places the hardware's own behaviour forced a decision that looks arbitrary from the
outside. [Issue #30](https://github.com/pdehlke/homeassistant/issues/30) tracked the work.

Read the control-path document first. This one assumes its cursor model, its join map, and its
account of what the services already do.

## The model: four entities per zone, not one

Each of the six zones gets a `switch` for power, a `select` for source, a `number` for volume and a
second `switch` for mute. Twenty-four entities, plus one `button.crestron_audio_refresh`.

### Rejected: six `media_player` entities

This is the obvious answer and it reads better. It was rejected on one concrete ground, not on
taste.

`media_player.volume_level` is normalised 0.0 to 1.0, with no `min`, `max` or `step` anywhere in
the entity contract, and the frontend renders that slider across its whole range. **These speakers
are inaudible below roughly 80% of full scale**, so a full-range slider is four fifths dead travel.
The only way to get a usable slider onto a `media_player` is to map 0-1 across 70-100 internally,
which makes the card read 50% while the amp sits at 85%.

That is the same class of lie this integration has refused twice already: the `d10N1` source-page
family that made every zone report whatever Studio was playing, and the entry-dump rebuild that
published a lit load as dark. A `number` entity takes `native_min_value`, `native_max_value` and
`native_step` directly and shows the figure the processor actually reports.

The secondary ground is that `media_player` is a transport abstraction and this hardware has no
transport. The feature flags can be narrowed to hide play, pause and seek, so this alone would not
have decided it.

### Rejected: one cursor's worth of entities

The control-path document's other candidate was a single `select` for the zone plus a `select` for
the source plus a `number` for volume, mirroring the panel exactly: one cursor, act on the selected
room. It cannot misrepresent anything because there is only ever one zone in view.

It was rejected because the requirement was a dashboard showing all six rooms at once, and a
one-room-at-a-time control cannot express that. The staleness it avoids is handled instead by the
cache being explicit about when it last looked (see below).

## Four things the hardware forced

### There is no power-on, so "on" had to be given a meaning

Source select and power-on are one action on the AADS. Selecting a source also overwrites the
zone's volume with that source's preset. So `switch.turn_on` has to choose a source and a level, and
both choices are arbitrary unless they live somewhere principled.

`Zone` gained an `on_volume` field: **Kitchen 80, every other room 90.** It lives on the zone
rather than in the caller so that every route into "on" agrees about what the Kitchen means: the
switch, the Speakers dashboard, `script.all_rooms_airplay`, and the Homie bubble all resolve to the
same number. The source is AirPlay, which is the one source whose identity is confirmed from the
processor's own `s102` rather than from recollection.

**Turning on a room that is already on is not a no-op.** A room left at 40% by a wall panel is
technically on, and pressing on there has to make it sound the way on sounds. The redundant source
press is skipped inside `async_select_source`, so this costs a read and a ramp rather than a
re-press that would reset the level anyway.

### A source change has to put the level back

Selecting a source replaces the level with the AADS's preset for it, and those presets are not
gentle: **Tuner 1's measured exactly 40%**, which on these speakers is silence. A source change
that leaves a room inaudible reads as broken hardware, so `async_select_source_keeping_volume`
restores the level the room was already at.

A room that was off has no level worth preserving and lands on its own `on_volume` instead, which
is the same thing turning it on would have given it.

Verified live on 2026-09-29: Studio at 90% switched to Tuner 1 and stayed at 90.0% rather than
dropping to the preset.

### Volume and mute go unavailable on a room that is off; source does not

Powering a zone off clears its source rather than silencing it, may zero its level, and whether
`a11` can be ramped at all in that state is untested. So a level and a mute have nothing to
describe on an off room, and offering the controls would invite a press whose behaviour nobody has
established.

The source select stays available, because selecting a source is the only power-on this hardware
has. Withdrawing it would leave an off room with no way back on from the dashboard. It reports
`unknown`, which is true.

Verified live: Studio powered off read `off` / `unknown` / `unavailable` / `unavailable` across its
four controls, and came back to `on` / `AirPlay` / `90.0` / `off`.

### `s16` names the subsystem, not the source

The `select` entity publishes a `processor_source_name` attribute so that the processor's own name
for a source can be compared against ours, which matters because the Integra's input labels are
known not to match what they select.

It was first wired to `s16`, the "selected source name" serial, which is what `_snapshot` calls
`selected_source_name`. **That is wrong and the live test caught it.** Selecting Tuner 1 in Studio
left `s16` reading `'Lights'`, the lighting subsystem's own name, so the attribute presented a
subsystem as a room's source. Serials are not reliably refreshed on a subsystem switch and `s16`
in particular was already recorded misbehaving this way in the control-path document.

It now reads `s(100+N)`, the per-source name serial, which is where `s101` and `s102` were read
from when iPod and AirPlay were identified. A test pins the distinction.

## Freshness: nothing polls, and that is deliberate

A/V state does not arrive by itself. The joins that carry it are dropped before they reach a
listener, deliberately, because `bridge._on_digital` refuses any join arriving from a subsystem
other than the link's default: the A/V pages reuse `d101`-`d109`, `d201`-`d204` and `d151`-`d157`
for things that are not lights, and a join from the wrong subsystem says nothing about a load. So
state moves only when something reads a zone.

Keeping six entities live would therefore mean walking the cursor on a timer. Measured: about
0.55s per zone once the slot is in A/V, about 1.9s for the first because it pays the subsystem
entry. **The slot is shared with lighting, so every second in A/V is a second of frozen lighting
feedback.** A 60-second poll would spend roughly 9% of every minute there for a dashboard nobody is
looking at most of the time.

What was built instead:

- **A seed walk at startup**, so the dashboard is not blank after a restart, which matters because
  the integration has no config flow and new code only loads on one. It waits for the AADS link to
  sync and then holds 15 seconds longer, so lighting bring-up gets the slot first. Failures are
  logged and dropped: a convenience read must not take the lighting bridge down.
- **`async_update` on every zone entity**, so `homeassistant.update_entity` re-reads one room.
- **`button.crestron_audio_refresh`**, which walks all six. One unreachable room costs that room
  and not the other five, because a walk that aborts halfway leaves the dashboard half stale with
  no indication of which half.

A 5-minute background poll would cost about a 2% duty cycle on the slot and remains a one-line
change if refreshing by hand turns out to be annoying. It was not built on the principle of not
spending the shared slot on a guess.

Measured live on 2026-09-29: the startup seed read all six zones in **2.6 seconds**, faster than
the 4.7s estimate above, because the slot had not yet left A/V between zones.

### Staleness is a property of the page, not of a room

`button.crestron_audio_refresh` carries an `oldest_read` attribute, and the Speakers dashboard
shows one line from it. Per-room staleness was rejected: one press refreshes all six, so six copies
of the same complaint is six times the noise for no extra information.

`oldest_read` is **`None` until every zone has been read at least once**, rather than the oldest of
whatever it happens to hold. A page-level freshness line that ignores the zones it knows nothing
about would describe a half-blank dashboard as fresh.

## Where the state actually lives

`AvController` holds a per-zone snapshot cache and a per-zone read timestamp. Every entity reads
from it; nothing reads joins directly.

**The cache is filled in `_snapshot()` and nowhere else.** Every operation on the controller
returns through that method, so there is no path that reads a zone and forgets to file it. The one
operation that changes a zone without reading it is `async_power_off_all`, which presses `d40` and
moves six zones while reading none; it calls `invalidate()` instead. Leaving those six cached would
show six rooms playing after all six were switched off, which is the one failure this cache can
produce that looks like working hardware.

## Areas

| Zone | Crestron name | Home Assistant area |
|---|---|---|
| `kitchen` | Kitchen | Kitchen |
| `outdoor_kitchen` | Outdoor Kitchen | Outdoor Kitchen |
| `master_bed` | Master Bed | Primary Suite |
| `master_bath` | Master Bath | Primary Suite |
| `studio` | Studio | Gym |
| `courtyard` | Courtyard | Courtyard |

Studio and Gym are the same room; per pde on 2026-09-29, Studio is an alias for it. "Studio" was
added as an alias on the Gym area registry entry so search and voice find it either way.

**The dashboard shows Crestron names, not area names.** The physical wall panels are the competing
interface for exactly these six rooms, and a label that disagrees with the panel three feet away is
worse than one that disagrees with a sidebar.

`Zone.name` is not a label and must not be edited for presentation. `av.py` compares it against the
processor's reported `s11` to prove the cursor landed, so changing it breaks cursor verification
rather than changing a caption.

## Living Room is still not here

Living Room, which the panel labels Great Room, is not one of the AADS's six zones and cannot
appear on this dashboard. Its speakers are on an external Integra receiver that Crestron cannot
reach. What the AADS has is the Integra's output wired in as one fixed line input, which is why
**source 4 is called "Great Room"**: selecting it in another room mirrors whatever the Living Room
is playing. Moving that feed around the house is in scope; changing what the Integra plays is not.
