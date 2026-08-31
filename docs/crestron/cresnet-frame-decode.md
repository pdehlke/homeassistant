# Cresnet frame decode, from live capture

## Status

First real bus capture. Two labeled button presses, both from the Studio CNX-B8 keypad, taken
2026-08-31 with the macOS CresnetMon port and the DSD TECH SH-U14 USB-to-RS-485 adapter. Enough to
establish frame structure and to answer the feasibility question in
[GitHub issue #1](https://github.com/pdehlke/homeassistant/issues/1). Not enough to write a bridge.

The capture diverged from issue #1's plan in one respect worth recording: the issue targets the
Great Room keypad (Cresnet ID `6A`, "Living Room Pathway"), and this capture is from the Studio
keypad (Cresnet ID `6D`, buttons "Sink Area" and "Patio South"). Nothing in the analysis below
depends on which keypad it came from, since Y/Z is a shared multidrop bus and any tap point on the
segment sees identical traffic. The Great Room button remains uncaptured.

Source data: `20260831T075334.jsonl`, produced by CresnetMon's labeling mode. Per that tool's
`STRATEGY.md`, capture files are session data from a real house and are not committed; the file
lives in the CresnetMon working tree at `mac/captures/`.

## The capture

Both records are a single button press on `0x6D`, captured as a silence-bounded burst.

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
```

Device IDs resolve against the `REPORTCRESNET` inventory in
[crestron-migration.md](crestron-migration.md). Direction comes from CresnetMon's `to_master` flag,
which is true when the frame's destination address is the master (`0x02`).

## Frame structure

Enumerating the value set at each byte position, grouped by payload length, shows two distinct
families with no positional overlap:

```
len 3:  [0]={00}  [1]={00,01,06,07}  [2]={00,80}
len 6:  [0]={1D}  [1..3]={00 00 00}  [4]={02,06}  [5]={FF}
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
invariant across three frames spanning two different module types (`0x71` CLX-1DIM8 and `0x73`
CLX-1DIM4) and two different payload lengths. The length itself varies with argument count: six
bytes carries one pair, eight bytes carries two. A structure whose length tracks its argument count
is what a variable-length argument list looks like.

Decoded against the button labels:

| Button | Target module | Decoded arguments |
|---|---|---|
| Sink Area | `0x71` CLX-1DIM8 | ch 6 to `FF` |
| Patio South | `0x71` CLX-1DIM8 | ch 5 to `FF`, ch 1 to `FF` |
| Patio South | `0x73` CLX-1DIM4 | ch 2 to `FF` |

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

| Load | Module | Channel |
|---|---|---|
| Studio sink area | `0x71` CLX-1DIM8 | 6 |
| Patio south (part) | `0x71` CLX-1DIM8 | 5 and 1 |
| Patio south (part) | `0x73` CLX-1DIM4 | 2 |

## What this data does not determine

`FF` is the only level value ever transmitted. That single fact blocks several questions at once.
There is no way to distinguish a level byte from a boolean on-flag, no way to establish the scale
(8-bit 0 to 255, 0 to 100, or a truncated 16-bit Crestron analog), no observation of an off
command, and no observation of a ramp. Channel numbering base is also open: the observed values are
1, 2, 5, and 6, with no `00` and no `08` to disambiguate 0-based from 1-based.

The capture contains zero frames from a CLX module back to the master. Nothing here shows how a
dimmer reports its actual level, and a Home Assistant bridge needs either that report or a poll for
it in order to show correct state.

The `00 07 80` frames sent to `0x62`, `0x66`, `0x67`, and `0x6F` appear identically in both bursts.
Two readings fit: LED refresh triggered by any lighting change, or periodic background chatter that
happens to land inside a 500ms burst window. No control capture exists to separate them.

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
opcode and argument structure are established, but with one level value, no off command, no state
feedback, and no model of the bus polling, a bridge cannot be written from this.

The distinction that matters is that every gap is a capture problem rather than an approach
problem. The `1D` frame is legible, consistent across two module types, and correlates reliably
with a known physical action. Issue #1 exists to convert `crestron-strategy.md`'s speculative
"weeks of reverse engineering" risk assessment into evidence, and on the sniffing half the evidence
now says the frames are more tractable than that assessment assumed.

Issue #1's second half, HA-native replay, remains entirely untouched and is the riskier half.
Injecting frames while the MC2E is still master is a two-masters-on-a-polled-bus problem, and
nothing in this capture speaks to it.

## Next captures

Five captures, none of which need any change to CresnetMon:

1. Sink Area off. A resulting `1D 00 00 00 06 00` confirms both the pair reading and the level byte
   in a single press.
2. The same load at a partial level. This separates a level byte from a boolean and establishes the
   scale. If a dim-ramp button exists, holding it distinguishes a stream of `06 xx` values from a
   single command with a non-zero header field, which also resolves the `00 00 00` question.
3. A control burst: arm the capture and press nothing. Whatever opens a burst on its own is
   background chatter, which settles whether `00 07 80` is real LED feedback.
4. Patio South from the Outdoor Kitchen keypad (`0x63`). Byte-identical CLX frames would confirm
   the command is keypad-independent and the index is per-keypad.
5. All eight buttons on `0x6D`, to confirm the index range and complete one keypad's map.

The Great Room "Living Room Pathway" button that issue #1 actually names should be folded into this
set, since it is the button the spike's replay phase targets.

## Suggested tool changes

Two changes to CresnetMon, both small, worth making before a long capture session.

Adding per-frame timestamps and the raw frame bytes (destination, size, payload) to the JSONL is
cheap and makes every future capture re-analyzable offline without re-walking the house pressing
buttons.

Adding a raw byte-stream log alongside the labeled JSONL, including poll frames, is the more
important of the two. Everything about the read direction is recoverable from later captures, but
the master's poll discipline cannot be reconstructed from a format that deletes it, and that is the
risk most likely to sink a write-capable bridge.
