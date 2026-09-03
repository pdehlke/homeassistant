# The XPanel control path

Findings from 2026-09-01, extended 2026-09-02. This supersedes the
Cresnet-injection strategy for writing to the lighting system, and largely
settles how a Home Assistant bridge should talk to this house.

## Summary

The MC2E's running program contains an XPanel at `Slot-05.IP-ID-03`. It was
unoccupied when this was written; it is not now (see the end). Registering on it
over CIP (TCP 41794) gives:

- a full state dump on connect: 42 digital joins, 2 analog, 4 serial;
- live per-light state changes, including brightness as a 16-bit analog join;
- **a working write path**: the processor accepts digital join presses from us
  and drives the Cresnet dimmers itself in response.

No SIMPL reprogramming, no Crestron programmer, and no fight with Cresnet bus
timing. The processor does the transmitting. Lights were physically turned on and
off this way, confirmed in the room.

**The limit: this panel reaches only the Kitchen.** All 75 press joins were
scanned by pressing each one and recording what the processor drove. Joins 21-35
address five Kitchen loads; joins 36-95 drive no dimmer at all. The `.dsc`
describes the panel as `101-Kitchen`, and that is exactly what it is.

That limit was confirmed to apply to observation as well as control on
2026-09-02, by a controlled test rather than by inference from the press scan.
See [the mirroring test](#the-slot-mirrors-the-wall-panels).

## Why Cresnet injection was abandoned

Writing frames directly onto the RS-485 bus does not work, and the reason is not
fixable with better hardware or timing.

Transmission itself is proven. The MC2E logged our probe bytes verbatim
(`[5A][06][5A]...`, a value that has never occurred in 937,118 bytes of captured
traffic), and the bus roll call's conformance dropped from 100.0% to 80.2% while
we transmitted and recovered afterwards.

But the CLX modules do not act on commands that arrive outside their slot in the
master's poll round. A byte-perfect, verbatim replay of the exact frames the
processor itself sends produced no light and no reaction. Sustained injection
makes all seven modules issue Update Requests and re-initialise, which is a fault
response rather than obedience.

The processor does not override us either; it issued no level command of its own
in any injection run. That hypothesis is disproved.

## The protocol

Registration and join traffic follow standard CIP. The digital-join encoding,
identical in both directions:

```
datatype 0x00, then the 0-based join low byte,
then a byte whose top bit is SET for low and CLEAR for high
```

So pressing digital join 24 is `05 00 06 00 00 03 00 17 00`, releasing it is
`05 00 06 00 00 03 00 17 80`. The processor renders the same thing in its debug
output as `[03][03][00][17][00]`.

Buttons **toggle**, and ramp rather than snapping: one press drove analog join 21
through 81 steps from 327 to 65535 over roughly two seconds; a second press faded
it back to 0.

## Brightness

Analog join 21 carries Living Pathway's level. When the Great Room keypad turned
that light on, the join read 50069 = `0xC395`, whose high byte is exactly the
`0xC3` level the Cresnet bus carries in the corresponding `1D` frame. So the
analog join is the 8-bit dimmer level scaled to 16 bits, which is directly usable
as a Home Assistant brightness value.

Confirmed again 2026-09-02 on a second join and a second load. Island switched
from a wall panel put `a22` at 7471 = `0x1D2F`, high byte `0x1D` = 29 of 255 =
11.4%.

That number is also the only trustworthy statement of the level. Neither the
TSW-752 panels nor the keypads display a brightness readout anywhere, so there
is no on-panel figure to reconcile against and no possibility of the two
disagreeing in front of a user. A human estimate of "about 25%" made in the room
was checked against this and withdrawn: the lights are simply very dim, and eye
estimates of low-end dimmer output run high. Treat the wire value as
authoritative.

## The Kitchen join map

| join | drives | effect |
|---|---|---|
| 21 | `0x71` ch4 | on, instant |
| 22 / 23 | `0x71` ch3 | raise / lower |
| 25 | `0x75` ch0 | on |
| 26 | `0x72` ch3 | on |
| 27 / 28 / 29 | `0x72` ch2 | raise / lower / off |
| 30 | all five | full (`FF`) |
| 31 | all five | off (`00`) |
| 32 / 33 / 34 | all five | 75% / 50% / 25% |
| 35 | all five | toggle |

The five loads are Island, Range, Kitchen Pathway, Powder and Cabinet. `0x71`
ch3 is almost certainly Powder: it is the only channel appearing in both the
Kitchen group and the Great Room keypad's Living Pathway pair, which is why
pressing join 24 lit a lamp that could not be seen from the living room and was
briefly mistaken for a failure.

## Kitchen identification, resolved 2026-09-03

[Issue #18](https://github.com/pdehlke/homeassistant/issues/18) named each
channel above. With the bridge's MC2E link stopped to free `IP-ID 0x03`,
`mac/poc_panelpress.py` pressed each candidate join in turn against
`192.168.4.59`, one at a time, with someone in the Kitchen confirming which
light responded each time.

| load | channel | join(s) | behavior |
|---|---|---|---|
| Cabinet | `0x71` ch4 | 21 | toggle |
| Kitchen Pathway | `0x75` ch0 | 25 | toggle |
| Range | `0x72` ch3 | 26 | toggle |
| Island | `0x72` ch2 | on: 27, off: 29 | not a toggle |

Cabinet, Pathway and Range are ordinary toggles despite the "on, instant" and
"on" labels the original scan gave joins 21, 25 and 26: a second press of each
turned its light back off, one for one, the same as every AADS load.

Island is not a toggle, and its channel turned out to be a dimmer rather than
a switch. Join 27 (documented above as "raise") brought Island on to a low,
nonzero level on a single brief press, `a22` rising from 0. Join 29
(documented as "off") ran the level smoothly down to 0 over about 1.9 seconds
on a single press, and its own digital feedback dropped to 0 only once the
level actually reached 0, meaning **29 is both the off button and the on/off
status join** for this channel. There is no separate plain "on" join: turning
Island on discretely means pressing 27, not toggling 29.

Two things observed during identification but not fully characterized, left
for the Phase 2 dimmer pass rather than resolved here, since brightness stays
out of scope for issue #18:

- Whether a brief tap of 27 always recalls a fixed preset level, or whether
  the level reached is proportional to how long 27 is held (a real hold-to-
  raise). The one live sample (a brief ~120ms tap landing at `a22` = 1703, well
  short of the `a22` = 7471 a wall-panel switch-on produced earlier) is
  consistent with either theory.
- `d35`, documented above as "toggle all five," moved in lockstep with `d26`
  during the Range tests (both went 1→0 when Range turned off, both None→1
  when it turned back on) without ever being pressed. That fits an aggregate
  "something in this group is on" status join better than a literal group
  toggle, but only one load in the group was ever exercised while watching it,
  so this is not confirmed against Island or Powder being on at the same time.

`0x71` ch3 (raise 22 / lower 23) was left untouched. It is Powder by
elimination once the other four channels were named, and Powder is already
driven from the AADS at `d102`; pressing it here would create a second entity
for one light.

Recorded in code as `custom_components/crestron_cip/const.py`'s `_MC2E_LOADS`
in the CresnetMon repo, `press_on`/`press_off` on the `Load` dataclass
generalizing Island's on/off split for whatever the Phase 2 dimmer pass finds
next among the other MC2E modules (`0x70`-`0x73`, `0x75`, `0x76`), all of which
are dimmers.

## The slot mirrors the wall panels

Established 2026-09-02. The slot does not merely echo feedback for joins we
press ourselves. It reports lighting activity that originates at a TSW-752, with
nothing sent from our side.

The test registered listen-only and pressed nothing. `cip_xpanel.py` sends only
the registration handshake, the update request, the end-of-query ack, and
heartbeats; the join-write path lives in `poc_joinpress.py` and was not used.
Island was then switched from the Studio TSW-752, and the slot reported:

```
[336.481]   a22 = 0
[336.493] CHANGE a22 = 7471 (was 0)
[336.501] CHANGE d29 = 1 (was None)
[336.509] CHANGE d35 = 1 (was None)
```

**Why this needed a control.** The same listener had already run for several
minutes while Pool Bath, Entry Center and Entry Perimeter were switched from the
same panel, and reported nothing at all. On its own that silence was ambiguous:
it fits a slot that ignores other panels entirely just as well as it fits a slot
that mirrors faithfully but carries no joins for those three loads. Island is
certainly inside the slot's join space, so switching it separates the two.

With mirroring proven, the earlier silence becomes a real negative. Pool Bath,
Entry Center and Entry Perimeter have no feedback presence on this slot. The
`101-Kitchen` boundary is exact and it is not an artifact of how the press scan
was done.

Do not read the digital joins through the press map below. That table records
what each join *does when pressed*; `d29` and `d35` appearing as feedback does
not mean the processor executed "0x72 ch2 off" and "toggle all five". Feedback
semantics on these joins are unmapped.

## The `1D` frame, corrected

`<dest> <size> 1D 00 <fade hi> <fade lo> <channel> <level>`, channel/level
repeating for multi-channel loads. The fade field is 16 bits: `00 00` instant
(keypad and XPanel "on"), `00 C8` for presets (about two seconds), `01 F4` for
raise, `00 18` for lower.

## The open question, answered 2026-09-02

How to reach the other thirteen rooms. Their loads answer to keypads and touch
panels, not to this XPanel slot. Four candidate routes. The first three are
closed; the fourth works and is written up in
[crestron-tsw-panel-control-path.md](crestron-tsw-panel-control-path.md).

1. Another free IP-ID with a wider join map. The `.dsc` lists only `IP-ID-03`
   and `IP-ID-05` on the MC2E, so this would require a slot that does not exist.
   **Closed.**
2. The AADS's two abandoned Crestron App slots, `IP-ID 0x15` and `0x16`. The
   AADS program does hold whole-house lighting, 42 named loads and scenes, but
   both slots are page-gated: they send a menu on registration and then nothing,
   including while lights are being switched from a wall panel. **Closed for any
   read-only approach**, and the only way past it is writing unidentified joins
   on the processor that also carries the alarm interface. Full record in
   [crestron-aads-slot-control-path.md](crestron-aads-slot-control-path.md).
3. The EISC at `Slot-05.IP-ID-05`, which carries whole-house joins (`d58` Entry
   Center, `d99` Sink Area, `d103` Pool Bath, confirmed 2026-08-31). It is
   occupied by the AADS and displacing it breaks audio and the ST-IO. Still the
   only route with part of a whole-house join map already in hand, and still
   unpriced in terms of what exactly breaks.

4. A real TSW-752 panel slot, taken by unplugging the panel. **This one works.**
   The panel hands over its own compiled project on request, which yields the
   whole-house join map by name without pressing anything, and the slot then
   accepts writes for every room, returns load and scene feedback, and drives
   the wall keypad LEDs correctly. Proven on `IP-ID 0x13` on 2026-09-02. Full
   record and the join map in
   [crestron-tsw-panel-control-path.md](crestron-tsw-panel-control-path.md).

Whole-house **observation** was never blocked by any of this: the passive Cresnet
tap already sees `1D` command frames for every room. Whole-house **control** now
has a route that avoids a programmer entirely, at the price of one touch panel
held permanently. What remains of the programmer scope is in
[crestron-xsig-programmer-scope.md](crestron-xsig-programmer-scope.md).

## Safety: there is no alarm in this processor

The compiled program was retrieved and searched. It contains zero occurrences of
alarm, Apex, zone, motion, siren, passcode, panic, or intrusion. The single
"security" hit is `G-Security`, a **lighting scene**, letter G in a set of eight:

```
A-Welcome   B-Good Bye   C-House On   D-House Off
E-Good Morning   F-Good Night   G-Security   H-Entertain
```

The worst outcome of pressing an unknown join on this processor is that lights
change.

**This is scoped to the MC2E and must not be generalised.** The caution in
`crestron-apex-control-plane.md` about alarm functions on joins applies fully to
the TSW-752 panels and the AADS. That matters more now than when it was written:
the current integration impersonates a TSW-752, so it operates on exactly the
surface that reaches the Apex. Nothing established about the MC2E licenses blind
join probing there.

## Retrieving the program

`XGETFILE` is blocked on the telnet console ("Command Blocked from this console
type") but works on the CTP console at TCP 41795, which is the same plain-text
console without telnet option negotiation, so binary passes through unescaped.
The filename must be **unquoted**.

`CresnetMon/mac/ctp_getfile.py` implements this. The binary is deliberately not
committed to either repo, both of which are public; it is the complete control
program for a private residence. It re-fetches in about four seconds.

## What this changes for the programmer scope

`crestron-xsig-programmer-scope.md` should be read with this in mind, and with
its limit stated honestly.

What exists: a working read *and* write interface to the **Kitchen**, reachable
from a free XPanel slot, with authoritative state feedback and brightness. A
proposal that prices in inventing that mechanism from scratch is pricing work
already done, and the mechanism is the hard part.

What does not exist: any route to the other thirteen rooms. That is still the
job, and it is the part a programmer is actually needed for — either exposing
the remaining loads on a slot we can reach, or freeing the EISC the AADS holds.

## Correction to the record

An earlier session tested `IP-ID-03` and concluded it was silent through
bus-confirmed lighting changes. That was a false negative, caused by three
decoding bugs in the CIP client that were fixed afterwards. The slot reports
state promptly and in detail. Anything else cleared with that decoder deserves
a re-test.

## Superseded in part

Two things changed on 2026-09-02, in a session not recorded here.

**The open question above is answered.** Reaching the rest of the house is done
by impersonating a TSW-752 touch panel, an approach neither of this document's
two candidate routes anticipated. Disregard both: there is no need for an
additional free IP-ID, and the AADS does not need evicting from the EISC.

**`IP-ID-03` is no longer free.** A Home Assistant add-on at `192.168.4.141`
holds that slot and uses it for live Kitchen control. CIP permits one connection
per IP-ID, so anything else registering there takes the Kitchen offline until it
disconnects. The proof-of-concept tools in `CresnetMon/mac` all default to that
slot and will do exactly that. Check `WHO` on the console before running them.

The add-on is v0.1. Kitchen control still runs through the XPanel path described
above; folding it into the TSW-752 impersonation is a planned enhancement, at
which point this document becomes history rather than reference.

One thing worth confirming and currently only inferred: which host the 752
impersonation registers against. The MC2E's `.dsc` lists only `IP-ID-03` and
`IP-ID-05`, which suggests the AADS at `192.168.4.61` rather than the MC2E. If
so, the Kitchen path and the whole-house path run against two different systems,
and that distinction should be made explicit wherever it matters.
