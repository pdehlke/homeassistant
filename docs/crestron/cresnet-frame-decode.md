# Cresnet frame decode, from live capture

## Status

First real bus capture. Three labeled actions taken 2026-08-31 with the macOS CresnetMon port and
the DSD TECH SH-U14 USB-to-RS-485 adapter. Enough to establish frame structure, to establish that
the CLX level byte is a real magnitude, and to answer the feasibility question in
[GitHub issue #1](https://github.com/pdehlke/homeassistant/issues/1). Not enough to write a bridge.

The three records do not share an origination path, and that difference turns out to matter more
than it first appears. See [Origination paths](#origination-paths) below.

| Record | Action | Origin | Reaches the bus via |
|---|---|---|---|
| 1 | "Sink Area" | Studio CNX-B8 keypad (`0x6D`) | Cresnet directly |
| 2 | "Patio South" | Studio CNX-B8 keypad (`0x6D`) | Cresnet directly |
| 3 | "Living Room Pathway" | TSW-752 touch panel | Ethernet to AADS, ISC to MC2E |

Record 3's `device` field in the capture file reads `0x64` (Kitchen CNX-B8). That attribution is a
labeling-dialog artifact and should be disregarded. The action originated on a touch panel, which
is not a Cresnet device at all, so no Cresnet device is the correct answer to "which device
produced this." The label dialog has no way to express that.

Issue #1 targets the Great Room keypad (Cresnet ID `6A`) and its "Living Room Pathway" button.
Record 3 covers that load but not that button, since the touch panel route never puts a keypad
button report on the bus. The keypad button itself remains uncaptured. Nothing in the analysis
depends on which tap point was used, since Y/Z is a shared multidrop bus and any point on the
segment sees identical traffic.

Source data: `20260831T075334.jsonl`, produced by CresnetMon's labeling mode. Per that tool's
`STRATEGY.md`, capture files are session data from a real house and are not committed; the file
lives in the CresnetMon working tree at `mac/captures/`.

## The capture

Each record is a single action captured as a silence-bounded burst.

```
'Sink Area' on 0x6D CNX-B8 (Studio), cycles 282..287
   c282 ->MASTER 0x6D CNX-B8     Studio           | 00 00 00
   c282 MASTER-> 0x6D CNX-B8     Studio           | 00 00 00
   c283 MASTER-> 0x71 CLX-1DIM8  Garage           | 1D 00 00 00 06 FF
   c283 MASTER-> 0x66 CNX-B8     Master Bedroom   | 00 07 80
   c283 MASTER-> 0x62 CNX-B8     Master Bedroom   | 00 07 80
   c284 MASTER-> 0x6F CNX-B8     Kitchen          | 00 07 80
   c284 MASTER-> 0x67 CNX-B8     Foyer            | 00 07 80
   c287 ->MASTER 0x6D CNX-B8     Studio           | 00 00 80

'Patio South' on 0x6D CNX-B8 (Studio), cycles 309..315
   c309 ->MASTER 0x6D CNX-B8     Studio           | 00 01 00
   c309 MASTER-> 0x63 CNX-B8     Outdoor Kitchen  | 00 01 00
   c310 MASTER-> 0x6D CNX-B8     Studio           | 00 01 00
   c310 MASTER-> 0x71 CLX-1DIM8  Garage           | 1D 00 00 00 05 FF 01 FF
   c310 MASTER-> 0x73 CLX-1DIM4  Garage           | 1D 00 00 00 02 FF
   c312 MASTER-> 0x66 CNX-B8     Master Bedroom   | 00 07 80
   c312 MASTER-> 0x62 CNX-B8     Master Bedroom   | 00 07 80
   c312 MASTER-> 0x64 CNX-B8     Kitchen          | 00 01 00
   c312 MASTER-> 0x67 CNX-B8     Foyer            | 00 06 00
   c312 MASTER-> 0x67 CNX-B8     Foyer            | 00 07 80
   c312 MASTER-> 0x6F CNX-B8     Kitchen          | 00 07 80
   c312 MASTER-> 0x67 CNX-B8     Foyer            | 00 01 00
   c315 ->MASTER 0x6D CNX-B8     Studio           | 00 01 80

'Living Room Pathway' from a TSW-752 touch panel, cycles 1002..1003
   c1002 MASTER-> 0x70 CLX-1DIM8  Garage          | 1D 00 00 00 04 1C
   c1003 MASTER-> 0x6A CNX-B8     Great Room      | 00 07 80
   c1003 MASTER-> 0x66 CNX-B8     Master Bedroom  | 00 07 80
   c1003 MASTER-> 0x62 CNX-B8     Master Bedroom  | 00 07 80
   c1003 MASTER-> 0x6F CNX-B8     Kitchen         | 00 07 80
   c1003 MASTER-> 0x67 CNX-B8     Foyer           | 00 07 80
```

Record 3 contains no keypad-to-master frame. That is not a missed capture. The touch panel is not
on Cresnet, so nothing existed on the wire until MC2E emitted the downstream command, and the burst
correctly opened on that.

Device IDs resolve against the `REPORTCRESNET` inventory in
[crestron-migration.md](crestron-migration.md). Direction comes from CresnetMon's `to_master` flag,
which is true when the frame's destination address is the master (`0x02`).

## Origination paths

The three records do not all reach the Cresnet bus the same way, and the difference shows up
directly in what the capture contains.

```
keypad:      CNX-B8 --Cresnet--> MC2E --Cresnet--> CLX
touch panel: TSW-752 --Ethernet--> AADS --ISC--> MC2E --Cresnet--> CLX
```

The four TSW-752 panels are Ethernet devices registered with the AADS at IP IDs 11 through 14, not
with MC2E, and they are not on the Cresnet bus at all
([crestron-migration.md](crestron-migration.md)). They reach the lighting bus over the Ethernet
Intersystem Communications link to MC2E, which is the processor that actually owns the lighting
Cresnet leg and holds live lighting logic ([crestron-migration.md](crestron-migration.md)).

This is why record 3 has no button frame, and it is also why the two origins are complementary
instruments rather than redundant ones.

A touch panel action isolates the CLX command cleanly. There is no button report, no press and
release pair, and no ambiguity about which frames are the request and which are the effect. That
makes it the better instrument for decoding the command vocabulary, and if any touch panel lighting
page carries a level slider it is the best available way to settle the level scale outright: set a
series of known percentages and read off the resulting level bytes in one sitting.

A keypad press is the only instrument for the button map, because it is the only path that puts a
button report on Cresnet at all.

### Why a touch panel capture does not by itself define an endpoint

Record 3 establishes that MC2E set `0x70` channel 4 to `1C`. It does not establish that "Living
Room Pathway" as a named load is exactly that one channel, for two separate reasons.

If MC2E transmits only channels whose value actually changed, any channel already sitting at its
target would be silent. The observed argument list is therefore a lower bound on what the name
covers rather than a definition of it. A single action taken at unknown prior state cannot
distinguish "this is the whole endpoint" from "this is the part that needed changing."

Separately, a touch panel join and a keypad button join are distinct entries into MC2E's program
even when they carry the same label, and nothing forces them through the same logic. The touch
panel control is plausibly a direct set-level while a keypad button of the same name may be a
toggle or a ramp. Same name and same fixture can still mean different frames.

The experiment that resolves both is a differential: drive the same target from a keypad and from
the touch panel and diff the resulting CLX frames. Byte-identical output means both joins land on
the same logic and the endpoint is confirmed. Divergent output means the shared label hides
different behavior, which is worth knowing before anything is written against it.

## Frame structure

Enumerating the value set at each byte position, grouped by payload length, shows two distinct
families with no positional overlap:

```
len 3:  [0]={00}  [1]={00,01,06,07}  [2]={00,80}
len 6:  [0]={1D}  [1..3]={00 00 00}  [4]={02,04,06}  [5]={1C,FF}
len 8:  [0]={1D}  [1..3]={00 00 00}  [4]={05} [5]={FF} [6]={01} [7]={FF}
```

### Three-byte frames: button and LED state

Read as `00 <index> <state>`. The leading byte is always zero across all thirteen instances. The
index takes values `00`, `01`, `06`, `07`, consistent with a button or join number on an
eight-button keypad. The state byte is only ever `00` or `80`, so it carries a single boolean in
its high bit rather than a magnitude.

The same three-byte format appears in both directions. Keypad to master is a button event; master
to keypad is LED feedback. That split is inferred from direction alone, not from anything in the
payload, but it is the only reading consistent with a master that owns the lighting logic.

This yields a direct button map for the two buttons pressed:

| Keypad | Button label | Index |
|---|---|---|
| `0x6D` Studio | Sink Area | `00` |
| `0x6D` Studio | Patio South | `01` |

Each press produces `00 <index> 00` when the burst opens and `00 <index> 80` three to six cycles
later. A press and release pair is the natural reading. Which of the two is the press and which is
the release is undetermined, and cannot be determined from a capture where every press is a quick
tap. A deliberate long hold would settle it immediately.

### Six and eight-byte frames: the CLX command

Read as a fixed four-byte header followed by a variable-length list of two-byte arguments:

```
1D 00 00 00  <ch> <level>  [<ch> <level>] ...
```

This is the frame [crestron-strategy.md](crestron-strategy.md) names as Path B's actual blocker,
"what bytes actually tell a CLX-1DIM8 to set a channel to a given level."

The evidence for this reading is stronger than byte-pattern eyeballing. The `1D 00 00 00` header is
invariant across four frames spanning three different modules and two module types (`0x70` and
`0x71` CLX-1DIM8, `0x73` CLX-1DIM4) and two different payload lengths. The length itself varies
with argument count: six bytes carries one pair, eight bytes carries two. A structure whose length
tracks its argument count is what a variable-length argument list looks like.

Decoded against the action labels:

| Action | Target module | Decoded arguments |
|---|---|---|
| Sink Area | `0x71` CLX-1DIM8 | ch 6 to `FF` |
| Patio South | `0x71` CLX-1DIM8 | ch 5 to `FF`, ch 1 to `FF` |
| Patio South | `0x73` CLX-1DIM4 | ch 2 to `FF` |
| Living Room Pathway | `0x70` CLX-1DIM8 | ch 4 to `1C` |

**The level byte is a magnitude, not a boolean.** Record 3's `1C` (28 decimal, roughly 11 percent
of full) settles a question the first two records could not, since they transmitted nothing but
`FF`. It also fixes the scale as 8-bit rather than 0 to 100, because a 0 to 100 scale could never
produce the `FF` the other records carry.

`1C` independently confirms the argument order as well. At 28 decimal it exceeds the channel count
of every module in the inventory, the largest of which is an eight-channel CLX-1DIM8, so it cannot
be a channel number. The pairs are (channel, level) and not (level, channel). That conclusion no
longer rests on the length-versus-argument-count reasoning alone.

Both conclusions hold regardless of how the action was originated, because they are properties of
what MC2E emits rather than of what asked it to emit.

### Rejected readings

Two alternative structures for the CLX payload were considered and rejected.

Treating the trailing bytes as a channel bitmask plus a level does not survive contact with the
data. Reading `06 FF` as mask `0b00000110` (channels 2 and 3) leaves a single level byte governing
two channels, and reading `05 FF 01 FF` as mask `0b00000101` followed by mask `0b00000001` produces
overlapping masks addressing channel 1 twice in one frame. The pair reading has neither problem.

Treating `1D 00 00 00` as an opcode plus a three-byte field that means something per-command was
considered and left open rather than rejected. It is indistinguishable from a fixed constant at
this sample size. A fade or ramp time is the most plausible candidate, since Crestron dimmers take
one and `00 00 00` would then mean instant, which matches the observed snap to full. That
hypothesis is testable and untested.

## Byproduct: partial CLX channel map

Independent of whether the level semantics are ever decoded, the capture produces a physical load
map by observation. This fills part of the channel-to-fixture gap that
[crestron-migration.md](crestron-migration.md) records as unknown, and does it without opening the
Garage rack.

| Load | Module | Channel | Level seen |
|---|---|---|---|
| Studio sink area | `0x71` CLX-1DIM8 | 6 | `FF` |
| Patio south (part) | `0x71` CLX-1DIM8 | 5 and 1 | `FF` |
| Patio south (part) | `0x73` CLX-1DIM4 | 2 | `FF` |
| Living Room Pathway | `0x70` CLX-1DIM8 | 4 | `1C` |

Read these as lower bounds rather than complete definitions, per
[the endpoint caveat above](#why-a-touch-panel-capture-does-not-by-itself-define-an-endpoint). Each
row records channels MC2E actually addressed during one action at unknown prior state, which is not
necessarily every channel the named load covers.

The Living Room Pathway row is the load that
[GitHub issue #1](https://github.com/pdehlke/homeassistant/issues/1) targets, and fills the channel
half of that issue's user story 14. The button half is still open, since the capture came from a
touch panel rather than the Great Room keypad the issue names.

## What this data does not determine

Only two level values have been observed, `FF` and `1C`. That is enough to prove the byte is a
magnitude on an 8-bit scale, and not enough to establish whether the mapping to a percentage is
linear. No off command has been observed, so the encoding of zero is unconfirmed, and no ramp has
been observed, so the `00 00 00` header field remains untested. Channel numbering base is also
open: observed values are 1, 2, 4, 5, and 6, with no `00` and no `08` to disambiguate 0-based from
1-based.

The capture contains zero frames from a CLX module back to the master. Nothing here shows how a
dimmer reports its actual level, and a Home Assistant bridge needs either that report or a poll for
it in order to show correct state.

The `00 07 80` frames went to `0x62`, `0x66`, `0x67`, and `0x6F` in the first two records, and to
those four plus `0x6A` Great Room in the third. Two readings still fit, LED refresh driven by a
lighting change or periodic background chatter landing inside a 500ms window, but the varying
recipient set is mild evidence against a fixed heartbeat, which should hit a stable set. The
addition of `0x6A` in the record that changed a Great Room load is suggestive and not conclusive. A
control capture still separates them cleanly.

## Capture-format gaps

These are limitations of the CresnetMon capture format rather than facts about the house, and they
matter more for Path B than the undecoded bytes above, because they are not recoverable by
re-reading existing captures.

Polling is invisible. CresnetMon's `burst.py` discards `PollTick` events by design, and
`protocol.py` counts a polling cycle only for a single reference device. Replicating the master's
poll discipline is the specific risk [crestron-strategy.md](crestron-strategy.md) flags as able to
"leave the CLX modules unresponsive until the software is right," and the JSONL format structurally
cannot show it.

The cycle numbers suggest that risk is real and non-obvious. Within a burst, cycles advance roughly
45 to 55ms apart. Between the two bursts, 22 cycles elapsed over 147 seconds, about 6.7 seconds per
cycle. That is two orders of magnitude, and the plus or minus 50ms of jitter from CresnetMon's tk
polling interval is nowhere near enough to explain it. Either the master polls hard only around
activity, or the reference device is polled irregularly. The capture cannot say which.

There are no per-frame timestamps. Frames carry a `cycle` number and nothing else, so inter-frame
gaps are unmeasurable, and there is no way to tell whether a CLX write is a response to a poll or
an unsolicited master transmission.

Raw framing is discarded. `protocol.py` retains only the payload; the destination address, the size
byte, and any trailing bytes are gone by the time a frame reaches the JSONL. Notably the parser has
no checksum handling at all, so either Cresnet's framing carries none or one is being silently
absorbed into the payload. A bridge that transmits needs that answered.

Source addresses on device-to-master frames are inferred rather than read. CresnetMon's
`_finish_message` uses the last non-master address seen while in its READY state. That is correct
on a well-behaved polled bus and wrong after any resync, and the tool's own `STRATEGY.md` records
this behavior surprising its author once during task 8.

## Assessment for Path B

For the read direction, this data is sufficient. More captures of exactly this kind, with no
changes to the tool, would produce a usable keypad-to-Home-Assistant trigger map and a fuller
button-to-CLX-channel load map.

For the write direction, which is what Path B actually requires, it is not sufficient yet. The
opcode, the argument structure, and the level byte's meaning are all established, but with no off
command, no state feedback, no model of the bus polling, and no confirmation that a named load maps
to a fixed channel set, a bridge cannot be written from this.

The distinction that matters is that every gap is a capture problem rather than an approach
problem. The `1D` frame is legible, consistent across three modules and two module types, and
correlates reliably with known physical actions arriving over two different origination paths.
Issue #1 exists to convert `crestron-strategy.md`'s speculative "weeks of reverse engineering" risk
assessment into evidence, and on the sniffing half the evidence now says the frames are more
tractable than that assessment assumed.

Issue #1's second half, HA-native replay, remains entirely untouched and is the riskier half.
Injecting frames while the MC2E is still master is a two-masters-on-a-polled-bus problem, and
nothing in this capture speaks to it.

## Next captures

Six captures, none of which need any change to CresnetMon. The first two are the highest value.

1. The keypad-versus-touch-panel differential. Drive one load, ideally Living Room Pathway, from
   the Great Room keypad and then from a touch panel, and diff the CLX frames. This resolves both
   halves of the endpoint question at once and captures the keypad button index that issue #1
   needs, which record 3 could not provide.
2. A touch panel level sweep. If a lighting page carries a slider, set a series of known
   percentages against one channel and read the level bytes. This settles whether the 8-bit scale
   is linear and, at the bottom of the sweep, how off is encoded. A slider is a far better
   instrument for this than hunting for keypad presets, because the input value is known exactly.
3. Any load off. Confirms the encoding of zero, which the sweep above may or may not reach.
4. A control burst: arm the capture and press nothing. Whatever opens a burst on its own is
   background chatter, which settles whether `00 07 80` is real LED feedback rather than a
   heartbeat.
5. Patio South from the Outdoor Kitchen keypad (`0x63`). Byte-identical CLX frames would confirm
   the command is origin-independent and the index is per-keypad.
6. All eight buttons on `0x6D`, to confirm the index range and complete one keypad's map.

Worth noting for planning: the touch panel is a measurement instrument with a shelf life. The
TSW-752 panels are explicitly slated for replacement
([crestron-migration.md](crestron-migration.md)), and their path to the bus runs through the AADS
that [crestron-strategy.md](crestron-strategy.md) plans to pull. Captures 1 and 2 should happen
while that route still exists.

## Suggested tool changes

Two changes to CresnetMon, both small, worth making before a long capture session.

Adding per-frame timestamps and the raw frame bytes (destination, size, payload) to the JSONL is
cheap and makes every future capture re-analyzable offline without re-walking the house pressing
buttons.

Adding a raw byte-stream log alongside the labeled JSONL, including poll frames, is the more
important of the two. Everything about the read direction is recoverable from later captures, but
the master's poll discipline cannot be reconstructed from a format that deletes it, and that is the
risk most likely to sink a write-capable bridge.
