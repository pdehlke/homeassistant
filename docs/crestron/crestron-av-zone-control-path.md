# Room-by-room audio on the AADS, mapped from the same TSW-752 panel project

**Mapped and partly verified live on 2026-09-17.** The six-zone audio system the touch panels
already drive is reachable over CIP by the same panel-impersonation route that gave Home Assistant
every lighting load, and it needs no Cresnet tap and no change to either Crestron program. No
bridge has been built. This document is the map and the live evidence behind it, which is step 1
through step 3 of [issue #20](https://github.com/pdehlke/homeassistant/issues/20).

Read [crestron-tsw-panel-control-path.md](crestron-tsw-panel-control-path.md) first. This document
assumes its method, its `IP-ID` inventory, and its account of how the panel project was retrieved.

## Why audio needed its own map

[crestron-strategy.md](crestron-strategy.md)'s audio plan predates panel impersonation. Its
"Rejected: keeping the AADS as a dumb amp only" section reasons that there is no front door into
the AADS's amp and matrix functions short of replacing the hardware, and recommends a per-zone
smart amp or a matrix amp on that basis. That premise is now false in the same way it turned out to
be false for lighting. Whether the replacement plan should still go ahead is a separate question
that this document does not settle, but it can no longer rest on "there is no way in."

Audio does not reuse the lighting model. Lighting gives every load its own join and needs no zone
selection, proven by pressing a load join cold. Audio has one cursor per panel slot and a single
set of per-zone joins whose meaning follows that cursor. The practical consequence is that a zone's
state is only readable while the cursor is on it.

## Where the map came from

`docs/crestron/dumps/tsw752-favela-v3-environment.xml`, the same 3.5 MB UTF-16 project file the
lighting map came from. It is gitignored rather than committed; the re-fetch command is in
[crestron-tsw-panel-control-path.md](crestron-tsw-panel-control-path.md#getting-the-join-map-without-pressing-anything).

Two mechanical notes for anyone re-running this. The file ends with XMODEM NUL padding after
`</Crestron>`, which makes it invalid XML until the tail is trimmed, and an `ElementTree` parse
fails with a misleading "not well-formed" error at the final line. Indirect text is carried in the
label as `<cips>NNN?</cips>`, not in the `IndirectTextJoin` element, which reads `0` on exactly the
buttons whose captions come from the processor.

## The write surface

| Function | Joins |
|---|---|
| Zone select | `d951` Kitchen, `d952` Outdoor Kitchen, `d953` Master Bed, `d954` Master Bath, `d955` Studio, `d956` Courtyard |
| Source select | `d51`-`d56` reachable on the live panel layout; the project defines `d51`-`d74` |
| Volume | `d44` up, `d45` down, `d48` mute |
| Power | `d42` off current zone, `d40` off all zones |
| Open the zone menu | `d950` |
| AV subsystem entry | `d75` (inferred, not tested; see below) |

Source numbering is regular. Source N takes its press on `d(50+N)`, publishes its name on serial
`s(100+N)`, and raises `d10N1` when it is the selected source. Confirmed live for N=1 and N=5.

## The read surface

This is the part static analysis missed and the live registrations found. All of it is readable
without pressing anything.

| Join | Meaning |
|---|---|
| `s11` | Name of the zone the slot's cursor is on |
| `s16` | Name of the selected source, in AV context |
| `a11` | Volume of the cursor's zone, 0 to 65535 |
| `d51`-`d56` | Selected-source feedback, same joins that take the presses. **This is the per-zone truth** |
| `d1001` | The no-source display page |
| `d10N1` | The display page for source N. Slot state, not zone state; see below |
| `d42` | Latches high on a zone that was explicitly powered off |
| `d46` | Mute feedback, carried by a second stacked button in the bottom banner |
| `a21`-`a41` | Present only with a tuner source selected; see below |

`d41`, `d43`, `d47`, `d901`, `d911` and `d991` also move with zone and power state and have not
been identified. `d901` does not follow the cursor, so it is slot state rather than zone state.

Several of these numbers mean something else in another subsystem. `s16` carries the climate zone
name on the HVAC pages and read `'Lights'` on the slot the lighting bridge holds. `d991` is a press
join on the lighting zone pages. The per-source display pages reuse `d101`-`d109`, `d201`-`d204`
and `d151`-`d157`, which collide with the Dining block, the Patio block and the HVAC schedule
block respectively.

## The cursor is per slot, which is the finding that matters

Registering read-only on all four AADS panel slots and pressing nothing gave four different
cursors:

| Slot | `s11` | `a11` | State |
|---|---|---|---|
| `0x11` | Master Bath | 60981 | `d1021` high, playing AirPlay |
| `0x12` | Studio | 56946 | `d1001` high, off |
| `0x13` (the lighting bridge) | Studio | 56946 | in the Lights subsystem, `d1411` high |
| `0x14` | Courtyard | 59242 | `d1001` high, off |

Then, on `0x12`, pressing `d956` moved `s11` to `Courtyard` and `a11` to **59242**, exactly what
`0x14` reported independently for its own Courtyard cursor, and pressing `d955` returned both to
Studio's 56946. Two slots agreeing on a per-zone value, one of them having reached it by moving its
cursor, establishes both that `a11` is genuine per-zone volume and that each slot carries its own
independent cursor.

That is the good outcome. Home Assistant's impersonated slot gets a cursor of its own and can move
it without dragging the physical panels around. It also fixes the ceiling on what is honest to
build: there is one `a11` per slot, so six simultaneously live zone states cannot be read from one
session no matter how the entities are shaped.

**A cursor move blanks the per-zone joins for about 60 ms before repopulating them.** `d41`, `d43`,
`d47` and `d51`-`d56` all drop to 0 and come back. Anything reading state inside that window sees a
dead zone and will report it with full confidence, which is the same silent-by-construction failure
mode [crestron-lights-subsystem-gating.md](crestron-lights-subsystem-gating.md) diagnosed for
lighting on 2026-09-15.

## What the live tests showed

All of this was done over CIP from a laptop, with no Cresnet tap connected and no panel unplugged.

**Selecting a source powers the zone on.** Pressing `d51` on a Studio cursor that was reading
`d1001` cleared it, raised `d1011`, and brought the zone up. Source select and zone power are one
action, so there is no separate power-on join to look for. Only power-off is separate.

**Some sources apply a volume preset on a source change, and some do not.** Selecting Tuner 1
ramped Studio from about 52000 down to 26214, which is 40.000% of 65535 exactly. The roundness of
that figure says the AADS works internally in percent with 65535 as 100.

That was originally written up here as happening on *every* source change, generalised from the one
source that had been tried. It does not. On 2026-09-22 selecting AirPlay in Studio left the level
at 60365 untouched, and setting all six zones to iPod left every one of their levels exactly where
it was. Only Tuner 1 has ever been seen doing it.

The operational rule is unchanged, because it only takes one source that resets to make ordering
matter: set the volume after the source, never before, and re-read `a11` rather than assuming the
last value survived.

**Volume is a ramp, not a step, and it is linear at about 6570 units per second of hold.** A 0.12 s
tap moves roughly 800. A 4.0 s hold moved 26214 to 52493. Measured on the way up; the way down was
consistent.

Confirmed independently on 2026-09-22 by the ramp the `crestron_cip` service now runs: a 1.00 s
hold moved 6488 units down and 6714 up, so 6570 is good to about 2% in both directions. Open-loop
estimates from that figure landed within 7, 17, 73 and 117 units of four different targets.

**`a11` does not accept a direct write.** Two writes, to 40000 and back, produced no response of
any kind. This is not proof on its own, because the project contains no analog touch join anywhere
to serve as a positive control for the encoding. What supports it is design evidence and pde's own
account: the only two analog joins in all 52 pages, `a11` and `a22`, are both `AnalogFeedbackJoin`
with no touch counterpart, and there is no way to set a level numerically from a physical panel
either. Setting a level therefore means holding `d44` or `d45` for a computed duration and
converging against `a11`.

**Volume resets to zero when the AADS or MC2E reboots**, per pde. A bridge cannot carry a cached
level across a processor restart, and the 2026-09-15 power cut that cleared the lighting subsystem
latch would have zeroed every zone at the same time.

**The speakers are inaudible below roughly 80% of full scale**, per pde, measured on AirPlay. That
is `a11` of about 52400, so the useful span is the top fifth of the nominal range. A `media_player`
mapping `volume_level` 0.0 to 1.0 linearly onto the raw join would be four-fifths dead zone.

**`d42` clears the zone's source selection rather than only silencing it.** Studio began as
`[41, 43, 47, 52, 901, 1001]`, off but still remembering AirPlay on `d52`. After `d42` it read
`[42, 47, 901, 1001]`: source memory gone, `d42` latched. Verified persistent by moving the cursor
to Courtyard and back, with Courtyard still holding its own `d52`. There is no join path back to
"off with a source remembered", because restoring `d52` powers the zone on again.

**The CEN-IDOC is on the network with no iPod docked.** Selecting source 1 populated `s33` through
`s36` with `Not Found` and `On Network`. Source 1 is live hardware reporting an empty dock.

**Tuner 1 is source 5 and produced no audio at 90% volume in Studio.** What it is, however, became
clear from the joins rather than from listening. Selecting it exposes 21 analog joins that no other
source produces:

| Join | Value | Reading |
|---|---|---|
| `a21` | 9370 | Current frequency, 93.70 MHz |
| `a22`-`a29` | 9210, 9290, 9370, 9490, 9610, 9710, 9950, 10750 | Eight configured presets |
| `a30`-`a41` | 8800 | Twelve empty preset slots parked at 88.00, the bottom of the FM band |

So source 5 is an FM tuner that somebody deliberately configured: those are real station
frequencies, not defaults. `a24` matches the current frequency and `d111` is high alongside it,
which most likely makes `d111` the selected-preset indicator for preset 3. That is an inference.

`a22` is the same join the CEN-IDOC page uses for its progress gauge, multiplexed the same way
`s16` and the `d1xx` block are.

**Neither tuner has a display page in the panel project.** The `1-AV` page references subpages for
AppleTV, Blu-ray, the CEN-IDOC dock, AirPlay and Theater only. `d1051` points at a page that does
not exist here, so selecting Tuner 1 leaves the panel showing a blank AV area with no controls.
There is no way to tune, pick a preset, or read the frequency from any touch panel in the house.
This is the first capability found that Home Assistant could expose and the panels never could.

**Powering off a zone sometimes zeroes its volume and sometimes does not.** A `d42` on a zone
playing AirPlay left `a11` at 57141 across a 25 second watch. A later `d42` on the same zone playing
Tuner 1 dropped `a11` from 59046 to 0 within 18 seconds. Source-dependent behaviour is the obvious
guess and it has not been tested. The operational consequence is the same either way: read `a11`,
never assume it.

## What building the services corrected

Steps 1 and 2 of the plan below are done, and driving the joins for real corrected three readings
that static analysis and read-only probing had left wrong.

### `d10N1` is slot state, not zone state

This is the one that would have made a whole entity model lie. Selecting AirPlay in Studio raised
`d1021`, and that join **stayed high as the cursor moved to every other zone**, so all five off
zones read back as playing AirPlay. The `d10N1` family selects the per-source display page, which
belongs to the panel slot and not to the zone under the cursor.

The per-zone truth is `d51`-`d56`, the same joins that take the presses, which is why they appear
in the list of joins a cursor move blanks and repopulates and the `d10N1` family does not. Reading
a zone's source from anything else reports whatever page the slot happens to be showing.

### `s11` is live, unlike `s16`

`s16` was found stale in the round-trip test, still reading `Lights` after the slot had returned to
A/V, and that cast doubt on the serials generally. `s11` is not stale: across two full passes over
all six zones it named each zone correctly the moment the cursor landed, so it is a usable
confirmation that a cursor move took rather than a value to be treated with suspicion.

### `a11` is not blanked by a cursor move, and is not resent when it does not change

Two findings that only show up when something reads the zone immediately after moving to it.

`a11` and `s11` do not arrive together. On the first read of a session the zone name landed first
and the level had not been sent yet, which reported a live zone with no level at all.

Clearing `a11` locally before the cursor press, to guarantee that whatever came back was fresh, is
wrong and made it worse. The 60 ms blank covers the digital joins, `d41`/`d43`/`d47` and
`d51`-`d56`, not the analog, so clearing `a11` discards a value the processor has no reason to
resend. Master Bed and Master Bath both sat at 61018, and moving between them produced no analog
frame at all.

What works is waiting for the processor to say something about the analogs since the press, with a
grace period for the equal-level case, where the value already in hand is the right one because it
is the same number either way.

### Two sources are now named

`s101` reads `iPod` and `s102` reads `AirPlay`, confirmed by setting each live. That is two of the
six identified without having to untangle the Integra wiring, because the processor names them even
where the Integra's own labels do not match.

## The services

Six of them, in the `crestron_cip` integration, all of them taking the same slot lock the lighting
commands use and giving it back between operations.

| Service | What it does |
|---|---|
| `av_status` | Read one zone's source, level and mute state |
| `av_select_source` | Select a source, which also powers the zone on |
| `av_set_volume` | Ramp to a percentage of full scale and converge |
| `av_power_off` | Power one zone off, clearing its remembered source |
| `av_power_off_all` | Power every zone off with one press |
| `av_mute` | Set mute state, consulting the feedback because the button is a toggle |

Volume is a percentage of full scale rather than a raw join value or a rescaling onto the audible
span, because the AADS works in percent internally and that is the unit its own presets land on.
Below about 80% is accepted, acted on, and warned about.

Each service returns the zone's state afterwards rather than only succeeding, because only the
cursor's zone is readable at all and the caller that just moved the cursor is the one caller
guaranteed to be able to see the result.

Measured live on 2026-09-22: a zone read costs about 0.55 s once the slot is already in A/V, and
1.9 s on the first call of a session because that one pays the subsystem entry. Setting all six
zones to one source took **6.5 s end to end**, against the 45 to 60 s this document originally
estimated, because that estimate assumed every zone would also need a full ramp from cold.

## The subsystem gate applies to audio too

The home page offers `d75` AV, `d80` Climate, `d91` Lights and `d93` Alarm, and
[crestron-lights-subsystem-gating.md](crestron-lights-subsystem-gating.md) established that `d91`
is a real gate the AADS requires before it will act on lighting joins for that slot. `d75` is the
AV gate, confirmed live on 2026-09-17.

The join collisions listed above are the reason the gate exists: the AADS multiplexes join meaning
by whichever subsystem the slot last entered. A slot holds exactly one subsystem at a time.

### One slot can do both, by taking turns

An earlier draft of this document concluded that `IP-ID 0x13`, the slot the lighting bridge holds
permanently, could not also carry audio. That was wrong, and the objection that killed it is
obvious in hindsight: every physical panel in the house has both a Lights page and an AV page, so
switching is plainly something a slot can do. What a slot cannot do is hold both subsystems at
once.

Two full round trips on slot `0x14` measured what a switch actually costs:

| Press | Joins sent | First arrival | Last arrival |
|---|---|---|---|
| `d91`, first entry to Lights | 87 (22 digital, 65 serial) | +0.081s | +0.977s |
| `d75`, back to AV | 24 digital | +0.063s | +0.561s |
| `d91`, second entry | 25 digital | +0.077s | +0.528s |
| `d75`, back to AV | 25 digital | +0.064s | +0.560s |

The 65 serials in the first entry are the lighting load names. They arrive once per session rather
than once per entry, which is why every later switch takes about half as long.

**Re-entry re-dumps live state rather than replaying a cache.** This was settled by an accident
that could not have been arranged on purpose. Note the limit of what it settles: the dump is live
rather than cached, but it is **not complete**. On 2026-09-22 a Lights entry omitted a join that was
high, so absence in an entry dump means nothing at all. The reading below, that a second entry
"reported `d243` gone" and therefore that absence reports an off, was an over-read of a single
observation; see
[crestron-subsystem-time-slicing.md](crestron-subsystem-time-slicing.md#what-the-live-deploy-corrected). Between the two Lights entries, East Hall turned off
somewhere in the house. The first entry reported `d243` high; the second reported it gone and
`d225`/`d227`, Goodbye and Good Night, newly high, which is the known all-off tell. Home
Assistant's own bridge on `0x13` recorded the same transition at 17:47:07Z on
`binary_sensor.crestron_guest_suite_east_hall`. Two slots agreeing on a change that happened while
one of them was looking elsewhere is exactly the proof needed.

**AV state survives the round trip.** `s11` stayed `Courtyard` and `a11` stayed 59242 across all
four switches. The zone cursor and volume are not lost by leaving and returning.

So the requirement is a lock rather than a second slot. While the slot sits in AV, the integration
must not emit a lighting join, because `d101` means Dining Room Table in one subsystem and the
AppleTV menu in the other. Queue it, switch back, flush. The reverse holds too.

Two cautions found in the same run. `s16` is not a usable subsystem indicator: it still read
`Lights` after the slot had returned to AV. And returning via `d75` lands the panel on the AV
source menu (`d1251`) rather than whatever page it was showing before, which is cosmetic on a live
panel and irrelevant on an unplugged one.

The AV pages never use `d130`-`d148`, so none of this touches the DSC alarm guard.

## Options for that slot

| Option | Cost |
|---|---|
| Time-slice the existing bridge slot `0x13` | **Preferred.** No hardware cost. Costs about half a second of blindness per subsystem switch and requires a lock in the integration so a lighting join is never emitted while the slot sits in AV. Measured below. |
| Unplug a second panel | A dedicated, quiet slot with no lock and no switching, at the cost of a second working touch panel. Worth it only if the lock turns out to be harder than it looks. |
| Share a live panel slot (`0x11`, `0x12`, `0x14`) | Fine for probing, wrong for a bridge. The slot has one cursor and a person is holding the other end of it, so the bridge's cursor gets moved out from under it and vice versa. |
| Use an app slot (`0x15`, `0x16`) | Rejected. Both run the `Favela-iPhone v1` project, not the TSW-752 one, so the join map in this document does not apply to them. See [crestron-aads-slot-control-path.md](crestron-aads-slot-control-path.md). |

## What an honest Home Assistant entity model looks like

Not decided. The cursor model rules out the obvious shape and leaves two candidates.

A `media_player` per zone reads best and matches how people expect audio to appear, but it would be
lying about liveness. Only the cursor's zone has readable state, so five of the six entities would
be showing a cached value at any moment, and the cache is invalidated by any use of a physical
panel as well as by a processor reboot.

A `select` for the zone plus a `select` for the source plus a `number` for volume is uglier and
mirrors the panel exactly: one cursor, act on the selected room. It cannot misrepresent anything,
because there is only ever one zone in view.

A middle route worth considering is six `media_player` entities backed by a polling loop that walks
the cursor across all six zones on a cycle, accepting a few seconds of staleness and the 60 ms
blank window on each hop. Whether walking the cursor continuously is acceptable depends on whether
it disturbs the physical panels, which is unknown and testable.

## The next step: an all-rooms AirPlay button

Source identity beyond AirPlay is unresolved. Per pde, the wiring and input switching across the
AADS and the Integra has been customised at some point, to the point where the Integra's own input
selection button labels do not match the sources they actually select, and untangling it needs time
with both consumer manuals. That work is not blocking, because one path is known to work today:
**AirPlay can be selected per room and the volume set per room.**

So the first thing built is a Homie Dashboard button that sets every room to AirPlay at 90% volume.

The dashboard button itself is trivial. Nearly all the work is underneath it, because Home
Assistant currently has no AV entities at all. The order is:

1. ~~Subsystem switching plus a write lock in the `crestron_cip` integration.~~ **Done 2026-09-22**,
   and it moved the bridge from slot `0x13` to `0x12` along the way. See
   [crestron-subsystem-time-slicing.md](crestron-subsystem-time-slicing.md).
2. ~~Zone and volume services in the same integration.~~ **Done and verified live 2026-09-22.** See
   [The services](#the-services) above.
3. An HA script that walks the six zones.
4. A Homie chip or button that calls the script.

The walk, per zone, is: press the zone-select join, wait out the blank window, press `d52` for
AirPlay, re-read `a11` because the source change resets it to that source's preset, then ramp to
target and converge.

Target volume is `a11` 58982, which is 90% of 65535.

Five constraints this design has to respect, all of them established above:

- **Volume must be set after the source, never before.** Selecting a source overwrites the level
  with a per-source preset. Tuner 1's preset was exactly 40%.
- **Always read `a11` rather than assuming.** It resets to zero on a processor reboot, it may reset
  to zero on power-off, and a physical panel can move it at any time.
- **Wait out the 60 ms blank after each cursor move** before reading anything, or the zone reads
  dead.
- **Ramp, then verify.** At roughly 6570 units per second of hold, going from a cold zero to 90%
  is about a nine second hold. Open-loop and then correct against `a11`.
- **This is slow when the zones start cold.** Six zones, each needing a cursor move, a source press
  and a multi-second ramp from zero, lands somewhere around 45 to 60 seconds end to end. Measured
  on 2026-09-22 with the zones already near the target it took 6.5 seconds, so the pessimistic case
  is a processor reboot having zeroed every level, not the ordinary one. The button has to be
  fire-and-forget with progress feedback, not something that blocks the dashboard while it runs.
  `script.turn_on` rather than a blocking `script` call, the same pattern the scenes chip uses.
- **The walk must yield to lighting.** A minute-long AV window would mean a minute of lighting
  latency on a shared slot. Since a subsystem round trip costs about a second, the walk should
  interrupt itself when a lighting write arrives: switch to Lights, do it, switch back, resume.
  That caps lighting latency near a second rather than near a minute.

Because the slot is shared, the walk moves the cursor six times in a minute while also leaving and
re-entering the Lights subsystem. On an unplugged slot that disturbs nobody. It is another reason
not to run this on a live panel slot.

## What is still open

- What each source physically is. The AADS and Integra wiring has been customised and the Integra's
  input labels do not match what they select, so this needs time with both manuals before the
  source list can be trusted beyond AirPlay.
- Whether `Tuner 1` produces audio at all. It was silent at 90% in Studio, but it has real
  configured presets, so an absent antenna or an unwired output are both live explanations.
  `Tuner 2` on `d56` is untried.
- Whether power-off zeroes the volume, and if so under what conditions. Observed once, not
  reproduced.
- What `d41`, `d43`, `d47`, `d111`, `d901`, `d911` and `d991` mean.
- Whether source 7, `AppleTV`, is connected to anything. The processor names it on `s107` and the
  project has its display page on `d1071`, but the live six-tile subpage only wires `d51`-`d56`, so
  it is unreachable from this panel layout rather than absent from the AADS. This corrects the
  earlier reading in issue #20 that it was unused boilerplate.
- Whether externally-originated AV changes are visible to a registered slot, the audio counterpart
  of the Garage Sconces result for lighting.

## Living Room is not in scope and cannot be

Living Room, which the panel labels `Great Room`, is not one of the AADS's six zones. Its speakers
are driven by an external Integra receiver that Crestron cannot reach in any form. What the AADS
has is the Integra's output wired in as one fixed line input, which is why selecting `Great Room`
in another room mirrors whatever Living Room is playing, and why the `Theater-pg01-main` page is
static text with no live joins. Moving that feed around the house is in scope for a bridge;
changing what the Integra plays is not, and would need Harmony, which Home Assistant already
integrates as `remote.harmony_hub`. Recorded in issue #20 as a likely requirement, not a decision.

## Tooling

`mac/cip_xpanel.py` in the CresnetMon repo does read-only registration and decodes digital, analog
and serial joins. It defaults to the MC2E at `192.168.4.59`, so AV work needs
`--host 192.168.4.61`.

`mac/poc_panelpress.py`, the obvious tool for the press tests, **cannot run without the Cresnet
tap's dependencies installed** even though its own docstring says it needs no tap. It imports
`poc_joinpress`, which imports `poc_witness`, which imports `serial`. The probe used for this
document inlined the press encoding and receive loop instead. Fixing that import chain would make
the documented tap-free path actually work.

`mac/poc_subsystem_timing.py` does the same inlining deliberately and is stdlib-only. It presses
subsystem-entry joins and nothing else, and reports the per-frame arrival timing of each entry dump.
It exists to settle the one measurement
[crestron-subsystem-time-slicing.md](crestron-subsystem-time-slicing.md) needs before that design
can be coded.
