# The AADS gates lighting on a subsystem-entry press

A house power cut on 2026-09-15 took every Crestron load in Home Assistant offline except the three
Kitchen loads on the MC2E, while the wall keypads went on working normally. The cause was not the
bridge, the network, or either processor: the AADS admits a registered panel slot to the lighting
subsystem only after that slot presses `d91`, the panel project's `Lights` button on the home page.
The bridge had never needed to press it, because the AADS program had been running continuously
since before panel 13 was unplugged and still held that panel latched inside the subsystem. The
power cut restarted the program and cleared the latch.

This document records the diagnosis in the order the evidence came in, because several plausible
explanations survived a long way and each one had to be killed with a measurement rather than an
argument.

## Symptoms

- Every wall keypad worked. Lights went on and off from them all morning.
- `light.kitchen_range`, `light.kitchen_island` and `light.kitchen_cabinet` worked from Home
  Assistant. Those are the three loads the bridge drives over the MC2E XPanel slot at `IP-ID 0x03`.
- Every other load failed with `pressed 2 times without the processor confirming on`, the bridge's
  own error for a press it sent and got no feedback for.
- `binary_sensor.crestron_link_aads` read `on` throughout, so the bridge believed the AADS session
  was healthy.
- Every AADS-backed load read `off`, and none of them ever changed, including while the keypads
  were visibly switching those same lights.
- Restarting Home Assistant did not help. This mattered: it ruled out anything that a fresh
  process, a fresh socket or a fresh registration would fix, and it is the fact that made the
  first several hypotheses wrong.

## What was ruled out, and how

| Hypothesis | Killed by |
|---|---|
| The bridge's TCP socket was a zombie the AADS had stopped servicing | The AADS's own `WHO` listed `Gateway (ID 13): 192.168.4.141` with an uptime matching the last Home Assistant restart. The session was real and registered. |
| The AADS was refusing or ignoring connections from the Home Assistant VM | A read-only CIP registration run from the VM itself, on spare slot `IP-ID 0x16`, was prompted, registered and dumped 149 frames in under a second. |
| The AADS's CIP server or its program was wedged | Read-only registrations on `0x15` and `0x13` from a laptop both registered in ~20 ms and received the full menu dump. `PROGUPTIME` showed the program running. |
| The AADS-to-MC2E EISC link was down | `IPTABLE` on both processors showed `IP-ID 05` `ONLINE`, and the AADS's error log recorded `CIP device 5: back ONLINE` at 07:14:48, with nothing after it. |
| The MC2E had lost its Cresnet lighting modules | `REPORTCRESNET` on the MC2E listed all seven CLX modules and all nine CNX-B8 keypads online. It is slow: the reply landed well after a 45-second drain window and showed up inside the *next* command's output. |
| The AADS program was in a bad state after booting before its Ethernet came up | `PROGRESET` on the AADS restarted the program cleanly. The fault survived it unchanged. |
| Only the press direction was broken | Home Assistant's history showed `binary_sensor.crestron_kitchen_pathway` going on at 13:51 UTC and off at 13:58 UTC, before the outage, and then **no AADS feedback of any kind** afterwards, across a morning of keypad use. Both directions were dead. |

## What the measurements showed

Two `SDEBUG` captures settled it. `SDEBUG -DON E<n>` takes the Ethernet ID in **decimal**, so the
panel slot at `IP-ID 0x13` is `E19`, not `E13`; `E13` is rejected with `No Device exists at Ethernet
ID`, which is easy to mistake for a silent capture.

Watching the AADS's panel slot and its EISC to the MC2E at the same time, while Home Assistant
pressed `d101` (Dining Room Table):

```text
<09/15/2026 08:22:36>CRX:Slot-06.IP-ID-13    : Digital Join 101 is High.
<09/15/2026 08:22:37>CRX:Slot-06.IP-ID-13    : Digital Join 101 is Low.
<09/15/2026 08:22:40>CRX:Slot-06.IP-ID-13    : Digital Join 101 is High.
<09/15/2026 08:22:40>CRX:Slot-06.IP-ID-13    : Digital Join 101 is Low.
```

The press arrived. Both attempts arrived. Nothing left the AADS in response: no `CTX` line to the
MC2E, no `CTX` line back to the panel.

The same capture with a *working* path exercised, toggling a Kitchen load through the MC2E instead:

```text
<09/15/2026 08:24:15>CRX:Slot-06.IP-ID-05    : Digital Join 29 is High.
<09/15/2026 08:24:15>CRX:Slot-06.IP-ID-05    : Digital Join 36 is Low.
<09/15/2026 08:24:15>CRX:Slot-06.IP-ID-05    : Digital Join 91 is Low.
<09/15/2026 08:24:15>CRX:Slot-06.IP-ID-05    : Digital Join 89 is Low.
```

So the EISC was alive and carrying lighting state from the MC2E into the AADS the whole time. The
AADS was receiving everything and forwarding nothing. That is not a transport fault; it is program
logic declining to act.

## The gate

[crestron-tsw-panel-control-path.md](crestron-tsw-panel-control-path.md) already recorded the
mechanism, as an inference about the alarm collision rather than as an operational requirement:

> The panel signals which subsystem it entered on `d91` for Lights and `d93` for Alarm, and the AADS
> program presumably gates the meaning of `d130`-`d148` on that.

The gate is real, it is per slot, and it governs the entire lighting subsystem rather than only the
ambiguous join range. Pressing `d91` from a freshly registered read-only session on `IP-ID 0x13`
produced this:

```text
[  2.40] FEEDBACK d146 = 1 (was None)
[  2.40] FEEDBACK d148 = 1 (was None)
[  2.40] FEEDBACK d153 = 1 (was None)
...
[  4.87] PRESS d101
[  4.99] FEEDBACK d101 = 1 (was None)
[ 12.99] PRESS d101
[ 13.24] FEEDBACK d101 = 0 (was 1)
```

Twenty-odd lighting joins arrived within a fifth of a second of the entry press, having been
completely absent from the registration dump. The load press that had been ignored four times over
the preceding hour then worked on the first attempt, on and off, with feedback.

This also corrects a claim in
[crestron-aads-slot-control-path.md](crestron-aads-slot-control-path.md), which concluded that a
TSW-752 slot *is not* page-gated because pressing load joins on `0x13` worked without any page
select. That test was accurate and its conclusion was wrong: the slot was already inside the
subsystem, latched there by the program, and nothing in the session had put it there.

## Why it broke now and not before

The latch lives in the running AADS program, not in NVRAM and not on the Home Assistant side. It
had been set since before panel 13 was physically unplugged in mid-August, which is why five weeks
of bridge operation never needed the entry press and why nobody knew the requirement existed.

The 2026-09-15 outage restarted the AADS program, which cleared it. Everything else about the
failure follows from that:

- The keypads kept working because CNX-B8 keypads are Cresnet devices on the MC2E and never touch
  the AADS.
- The Kitchen kept working because the MC2E's own XPanel slot at `IP-ID 0x03` is ungated.
- Restarting Home Assistant could not help, because the state that was missing was in the AADS.
- A `PROGRESET` on the AADS could not help either, for the same reason: it clears the latch again.
- The bridge reported every load `off` rather than `unavailable`, because a gated slot is
  indistinguishable from a quiet house from inside a CIP session. The dump is empty either way.

## The fix

In the `crestron_cip` integration, in the `pdehlke/CresnetMon` repo:

- `const.py` gains `LIGHTS_ENTRY_JOIN = 91` and an `entry_join` field on each link's defaults, set
  for the AADS and `None` for the MC2E. `_validate()` refuses an entry join inside
  `FORBIDDEN_AADS_WRITE`, so this can never become a way to press `d93` by accident.
- `cip.py` makes coming up a two-phase operation on a link that has an entry join. The session
  presses it when the registration dump ends, resets its quiet-window baseline, and only calls
  itself `synced` once the subsystem's own dump has landed behind that. Syncing on the menu dump
  alone would have the bridge report thirty loads `off` with complete confidence and no evidence,
  which is exactly what it did for four hours on 2026-09-15.
- Entry is per session, not once per process. A reconnect re-enters, because a new session is a new
  slot as far as the AADS is concerned.
- `cip.py` also logs a warning when a gated link reports no digital joins at all after the entry
  press. This failure mode is silent by construction and looks identical to a dark house, so it
  needs to announce itself.

Verified live on 2026-09-15 after deploying to `/config/custom_components/crestron_cip/` and
restarting: Dining Room Table, Office North Sink, Courtyard Path and Primary Suite Hallway each
turned on and off from Home Assistant with the processor confirming every transition, and the two
Kitchen loads on the MC2E still worked unchanged.

## Operational notes for next time

- `SDEBUG -DON E<n>` wants the Ethernet ID in decimal. `E19` is `IP-ID 0x13`.
- `REPORTCRESNET` on the MC2E takes far longer than a console drain window expects. Send a cheap
  command after it and read the reply out of *that* window.
- `mac/crestron_console.py` in the CresnetMon repo talks to either processor over telnet on port 23
  with no password. `VER`, `IPTABLE`, `WHO`, `ERR`, `PROGUPTIME` and `PROGCOMMENTS` are all
  read-only and all of them earned their place in this diagnosis.
- The AADS tolerates a second client registering on an IP-ID that is already held, and does not
  disturb the incumbent. Do not read "my registration succeeded" as "the other session is dead".
- A CIP session that is connected, registered and quiet proves nothing about whether the processor
  will act on it.
