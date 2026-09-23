# The AADS moved address and took every non-MC2E load with it, 2026-09-23

An overnight DHCP lease renewal moved the AADS from `192.168.4.61` to `192.168.4.65`. The bridge
kept trying the old address, so every AADS-backed lighting load and all six audio zones went dead
while the three MC2E Kitchen loads kept working. Total outage roughly 85 minutes, ending with a
one-line address change and a Home Assistant restart.

The interesting part is not the fix. It is that the symptom pointed convincingly at something else,
and that chasing the network layer first turned up a safety check that had quietly stopped working.

## The symptom, and why it looked like a slot regression

The report was: the only Crestron controls that work are the three kitchen lights still on the MC2E.
Everything else, lighting and A/V alike, is dead.

The obvious suspect was the panel slot. The bridge had moved from `0x13` to `0x12` the previous day
(see [crestron-subsystem-time-slicing.md](./crestron-subsystem-time-slicing.md)), that move is the
most recent change to the integration, and a slot problem would plausibly take out AADS lighting and
A/V together while leaving the MC2E alone.

It was not the slot, and the reason is worth keeping: **lighting and A/V share the AADS link, and the
MC2E is a separate TCP connection to a separate processor** ([ADR
0066](../adr/0066-crestron-bridge-needs-two-cip-connections.md)). So "everything on one link is
dead, everything on the other link is fine" is a statement about the link, not about anything
layered on top of it. Any explanation that required the slot would also have had to explain why one
of the two connections was completely unaffected.

## Diagnosis

The log said it outright, once looked at:

```
WARNING (MainThread) [custom_components.crestron_cip.cip]
  aads: connection lost ([Errno 113] Connect call failed ('192.168.4.61', 41794))
```

`errno 113` on Linux is `EHOSTUNREACH`. That is a failure to reach the host at all, which sits well
below anything the integration does with slots, subsystems or joins.

Confirmed from pde's laptop on the same segment:

| Check | `192.168.4.61` (expected AADS) | `192.168.4.59` (MC2E) |
| --- | --- | --- |
| ICMP | 100% packet loss | replies, ~5 ms |
| ARP | `(incomplete)` | resolves, Crestron OUI `00:10:7f` |
| CIP port 41794 | no | open |

An `(incomplete)` ARP entry means nothing on the segment claims that address. The host was not
firewalled or wedged, it was simply not there.

A sweep of the subnet found exactly two Crestron OUIs: the MC2E at `.59`, and **a second Crestron
device at `.65`** that had `41794`, `41795`, `80` and `23` open, which is a processor's port
profile. HTTP identified nothing (both processors 404 on `/index.html`), so the confirmation came
from the telnet console banner:

```
AADS Control Console  Connected to Host: AADS
```

against the MC2E's, for contrast:

```
MC2E Control Console  Connected to Host: MC2E
```

That is identification rather than inference, which matters here: acting on "the only other Crestron
device must be the AADS" would have been a guess, and pointing the bridge at the wrong processor is
not a harmless experiment.

## Cause

The AADS's DHCP lease was never reserved. It renewed overnight onto a different address. Nothing in
the control system changed, nothing in the integration changed, and no deploy was involved.

This is the second time an unreserved lease has caused an outage on this instance. The first was the
Lennox S30 South thermostat, written up in
[lennoxs30-integration.md](../lennox-climate/lennoxs30-integration.md), which has its own recovery
section for exactly this. That it happened twice, to two different pieces of infrastructure, is the
argument for reserving every device the configuration names by literal address rather than fixing
them one outage at a time.

## Fix

pde reserved `192.168.4.65` to the AADS's MAC, so the address is now fixed. Then, in `CresnetMon`
(commit `49bc181` on `macos-port-python`):

- `custom_components/crestron_cip/const.py`: the `LINK_AADS` host, the only change needed to end the
  outage. `crestron_cip:` is declared in `configuration.yaml` with no keys, so `DEFAULTS` in
  `const.py` is the single place this address lives for the running bridge.
- Five `mac/` references, for the reason in the next section.

`const.py` was deployed by SFTP to `/config/custom_components/crestron_cip/`, checksum-verified
before the atomic rename, with the other seven files confirmed byte-identical to the repo first so
the deploy carried nothing else. The integration has `config_flow: false`, so there is no config
entry to reload and a Home Assistant restart is required to re-import the module.

## The latent problem this turned up

`mac/cip_xpanel.py` holds the shared guard that refuses to press the joins the DSC alarm keypad
shares on the AADS. It is **keyed on the host**:

```python
def refuse_forbidden(joins, host: str) -> None:
    if host != AADS_HOST:
        return
```

`AADS_HOST` was `192.168.4.61`. With the AADS actually at `.65`, that comparison stops matching, and
the guard returns without checking anything. `poc_joinpress.py` and `poc_joinscan.py`, the two
scripts that rely on it, would have pressed Fire, Medical or Panic joins with no refusal the moment
either was pointed at the real AADS.

Not an active hole on the day, because both default to the MC2E, where the guard is a deliberate
no-op. But it is precisely the shape of problem [issue
#26](https://github.com/pdehlke/homeassistant/issues/26) was about: a check that reads like defence
in depth and cannot fire is worse than no check, because it stops anyone looking. An address change
somewhere else in the system silently disarmed it.

Proven both directions after the fix:

| Host | Join | Refused? |
| --- | --- | --- |
| `192.168.4.65` (AADS now) | `d146` (Fire) | yes |
| `192.168.4.65` | `d93` (enter alarm) | yes |
| `192.168.4.65` | `d101` (ordinary) | no |
| `192.168.4.61` (the stale value) | `d146` | **no** |
| `192.168.4.59` (MC2E) | `d146` | no |

The fourth row is what the stale constant was doing.

**The integration's own alarm guard was never affected.** It keys on the link name, not the host
(`bridge.py` passes `FORBIDDEN_AADS_WRITE if name == LINK_AADS`), so it survived the address change
untouched. The difference between the two guards is the lesson: identity by logical role holds
across a network change, identity by address does not.

`poc_subsystem_timing.py` and `poc_panelpress.py` each carried their own copy of the address as
well. Both now import `AADS_HOST` rather than restating it, since a second copy is how the first one
goes stale unnoticed, which is the same reasoning that consolidated the guard itself.

## Verification

- No `crestron_cip` warning since the restart, in a window where four were due at the observed
  33-second retry interval.
- `crestron_cip.av_status` on Kitchen returned `reported_zone: "Kitchen"`, so the AADS answered and
  confirmed the cursor landed on the real zone rather than the call merely not erroring.
- A discrete on and off on `light.office_pool_bath` moved `binary_sensor.crestron_office_pool_bath`
  in the same instant. That sensor is the AADS's own feedback, so it proves the round trip rather
  than an optimistic local write. The light was left off, as found.

## Worth doing next

- **Reserve the MC2E at `192.168.4.59` too.** It is named by literal address in the same `DEFAULTS`
  table and is exactly as exposed; it simply has not renewed yet. Reserving it is the cheap half of
  never seeing this again.
- **Consider making the bridge fail loudly.** The integration retried a dead address every 33
  seconds for 85 minutes without surfacing anything a person would see. A repair issue, or a
  binary sensor for link health, would have turned "my lights do not work" into "the AADS link is
  down" without anyone reading a log.
