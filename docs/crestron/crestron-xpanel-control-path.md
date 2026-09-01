# The XPanel control path

Findings from 2026-09-01. This supersedes the Cresnet-injection strategy for
writing to the lighting system, and largely settles how a Home Assistant bridge
should talk to this house.

## Summary

The MC2E's running program contains an XPanel at `Slot-05.IP-ID-03` that nothing
occupies. Registering on it over CIP (TCP 41794) gives:

- a full state dump on connect: 42 digital joins, 2 analog, 4 serial;
- live per-light state changes, including brightness as a 16-bit analog join;
- **a working write path**: the processor accepts digital join presses from us
  and drives the Cresnet dimmers itself in response.

No SIMPL reprogramming, no Crestron programmer, and no fight with Cresnet bus
timing. The processor does the transmitting.

One thing is unresolved: the single press we tried moved the program's state and
put a command on the wire, but the lamp did not light. See "The open question".

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

## The open question

Pressing digital join 24 was received by the processor, which then sent
`71 06 1d 00 00 c8 03 ff` to dimmer `0x71` channel 3. Our independent Cresnet tap
caught that frame on the wire. The lights did not come on.

Two differences from a keypad press, which does work:

| | keypad | XPanel join 24 |
|---|---|---|
| frame to `0x70` | `70 06 1d 00 00 00 04 c3` | none sent |
| frame to `0x71` | `71 06 1d 00 00 00 03 c3` | `71 06 1d 00 00 c8 03 ff` |

Living Pathway is two dimmer channels. The keypad drives both; our press drove
only one. Digital join 35 also went high alongside 24, and may be the other half.
Byte 5 differing (`00` versus `C8`, plausibly a fade rate) is the other lead.

Next test: press join 35 alone and see whether it drives `0x70` channel 4.

## Safety: there is no alarm in this processor

The compiled program was retrieved and searched. It contains zero occurrences of
alarm, Apex, zone, motion, siren, passcode, panic, or intrusion. The single
"security" hit is `G-Security`, a **lighting scene**, letter G in a set of eight:

```
A-Welcome   B-Good Bye   C-House On   D-House Off
E-Good Morning   F-Good Night   G-Security   H-Entertain
```

The worst outcome of pressing an unknown join on this processor is that lights
change. The caution in `crestron-apex-control-plane.md` about not putting alarm
functions on joins still applies to the TSW-752 panels and the AADS, which are a
separate system; it does not apply to the MC2E.

## Retrieving the program

`XGETFILE` is blocked on the telnet console ("Command Blocked from this console
type") but works on the CTP console at TCP 41795, which is the same plain-text
console without telnet option negotiation, so binary passes through unescaped.
The filename must be **unquoted**.

`CresnetMon/mac/ctp_getfile.py` implements this. The binary is deliberately not
committed to either repo, both of which are public; it is the complete control
program for a private residence. It re-fetches in about four seconds.

## What this changes for the programmer scope

`crestron-xsig-programmer-scope.md` should be read with this in mind: a working
read *and* write interface to the lighting now exists, reachable from a free
XPanel slot, with authoritative state feedback and brightness. Any proposal that
prices in building that from scratch is pricing work already done.

## Correction to the record

An earlier session tested `IP-ID-03` and concluded it was silent through
bus-confirmed lighting changes. That was a false negative, caused by three
decoding bugs in the CIP client that were fixed afterwards. The slot reports
state promptly and in detail. Anything else cleared with that decoder deserves
a re-test.
