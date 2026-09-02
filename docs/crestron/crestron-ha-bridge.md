# The Home Assistant to Crestron lighting bridge

The daemon that connects Home Assistant's thirty `light.*` entities to the real lighting loads,
using the control path proven in
[crestron-tsw-panel-control-path.md](crestron-tsw-panel-control-path.md).

Written and deployed 2026-09-02. **Live: both links registered, all thirty lights bound to it,
driving real loads.** See [Status](#status) for exactly what is proven and what is not.

## What it is

A Home Assistant custom integration, `crestron_cip`, living in the CresnetMon repo at
`custom_components/crestron_cip/` and deployed by SFTP to `/config/custom_components/`.

It holds two long-lived CIP sessions, keeps a live picture of every lighting load's state, and
exposes that state as entities plus discrete on/off as services.

```
HA light.turn_on
  -> template light action: crestron_cip.turn_on {load: office_pool_bath}
    -> bridge: is d245 already high? yes -> no-op. no -> press d245, await confirm
      -> AADS -> EISC -> MC2E -> Cresnet -> CLX dimmer, and the keypad LED
  <- feedback d245 = 1
  <- binary_sensor.crestron_office_pool_bath
    <- light.office_pool_bath
```

The keypad LED is inherited rather than implemented. The injection point sits upstream of the
MC2E's LED logic, which is what closed [issue #15](https://github.com/pdehlke/homeassistant/issues/15).

## Why an integration rather than a translation layer

The job is not request/response translation. It is holding a socket, answering heartbeats,
maintaining join state, and reconnecting, for as long as Home Assistant is up. That is a daemon,
and a Home Assistant custom integration is a daemon that already has a lifecycle, a config
mechanism, an entity model and a logger.

A `command_line`-style approach was rejected on arithmetic rather than taste: registration plus
state dump takes about 1.1 seconds, so a per-command reconnect would put a second of latency on
every light switch and would re-register on the AADS dozens of times an hour.

## Structure

| File | Role |
| --- | --- |
| `const.py` | the load table, and the forbidden-write set, validated at import |
| `cip.py` | asyncio CIP client: framing, registration, heartbeat, decode, reconnect |
| `bridge.py` | join state, alias resolution, discrete on/off over toggle, write guard |
| `binary_sensor.py` | one feedback entity per load, one per link |
| `__init__.py` | YAML setup, service registration |

`cip.py` is a rewrite of `mac/cip_xpanel.py` onto asyncio, not an import of it: the
proof-of-concept client is blocking and Home Assistant cannot host a blocking socket loop. The wire
format is unchanged and the tests assert against the exact frames recorded in the live transcripts,
so a codec change that still round-trips but no longer matches the wire fails.

## The two decisions that shaped it

Both are recorded as ADRs because they are the parts a future reader would otherwise have to
reconstruct.

[ADR 0066](../adr/0066-crestron-bridge-needs-two-cip-connections.md): two connections, because the
DSC alarm keypad shares `d130`-`d148` and four Kitchen loads have no join outside that range.

[ADR 0067](../adr/0067-discrete-on-off-synthesised-in-the-bridge.md): discrete on/off is
synthesised in the daemon, because the buttons are toggles and doing it in a template light's
action list would race against wall panels.

## Safety

The forbidden set is `range(130, 149)` plus `93`, matching `poc_panelpress.py`. It is enforced in
two places on purpose: `const._validate()` rejects a table containing a forbidden canonical join at
import time, so a bad entry fails at Home Assistant startup rather than lying dormant until someone
turns that light on, and `bridge._guard()` checks again immediately before bytes reach the wire.

The write surface is exactly the twenty-six canonical AADS joins plus, later, the Kitchen joins on
the MC2E. Nothing else is ever sent. `d91`, the Lights subsystem-entry join, was considered as a
way to make the AADS's interpretation of the shared range explicit and deliberately not used: the
bridge never writes that range, so `d91` buys no safety while changing processor state in a way
that has not been characterised.

Receiving a forbidden join is expected and fine. Powder reports on `d142` and Outdoor Kitchen on
`d144`, both inside the range. Only writing is refused.

## Load table

Thirty loads. Twenty-six on the AADS panel slot, four on the MC2E XPanel, together covering all
forty-one load buttons in
[crestron-load-room-worksheet.md](crestron-load-room-worksheet.md).

Where a load appears on several zone pages the canonical join is the one pressed and the rest only
report, which is how Outdoor Kitchen stays one entity across five buttons. Feedback on any alias
is mirrored onto the canonical join, so state has exactly one place to be read from.

The four Kitchen loads carry no join yet and are declared with `join=None`. They report unavailable
and refuse commands rather than guessing. See [Status](#status).

## Status

**Live since 2026-09-02.** Both links registered, all thirty lights bound to it, driving real
loads.

Proven live:

- Both CIP sessions register, sync and hold. On first sync the bridge independently reproduced the
  read-only recon baseline: Garage Sconces high on both `d185` and `d244`, nothing else, which is
  the alias resolution working on real state.
- Writes reach the house. Pool Bath (`d245`), North Sink (`d241`) and Patio North (`d164`/`d188`)
  were each switched on and off from Home Assistant and followed.
- Idempotence holds against real hardware. A second `turn_on` on a load already on presses nothing;
  a second press would have turned the light off.
- `light.turn_on` on the Home Assistant entity drives the load end to end, through the template
  light, the service, the bridge and the whole Crestron chain.

Established before deployment and unchanged by it:

- Registration through end of state dump takes about 1.1s.
- The slot carries no per-load analog level join, so these twenty-six loads are on/off only. Two
  analog joins exist on the whole slot and both are audio gauges.
- The AADS does not drop a client that stops answering heartbeats, at least not within 149s.
- Nineteen offline tests pass, covering the codec against recorded frames, the load table's safety
  invariants, and the toggle logic including idempotence, concurrency, alias resolution and refusal
  on unknown state.

Still open:

- The four Kitchen loads, pending the identification pass described in
  [ADR 0066](../adr/0066-crestron-bridge-needs-two-cip-connections.md).
- An externally-originated change has not been watched live. Garage Sconces proves the bridge reads
  a load it never touched, but no wall-panel or keypad press has been observed arriving while the
  bridge was running. Note that this cannot be told apart from a Home Assistant write after the
  fact: the template light derives its state from the feedback sensor, so the originating context
  is lost and `context_user_id` is `None` either way.

## Two bugs worth remembering

**A service handler must be an `async def`, not a lambda returning a coroutine.** The first live
deploy registered the services as `lambda call: _call(...)`. Home Assistant decides how to invoke a
handler with `asyncio.iscoroutinefunction()`, a lambda fails that check, so HA ran it in an executor
thread, took the coroutine it returned and discarded it. Every service call returned HTTP 200 having
done nothing at all: no press, no error, no state change. The only trace anywhere was a
`coroutine 'async_setup.<locals>._call' was never awaited` RuntimeWarning in `system_log`. It was
found by checking the recorder first, which showed no transition at all and so ruled out "pressed
but mishandled the feedback". A source-level test now fails if `async_register` is handed a lambda.

**A light bound to a feedback entity needs an availability template.** Binding `state` to
`is_state('binary_sensor.crestron_<load>', 'on')` makes the light read `off` whenever that sensor is
`unavailable`, which is a lie in two cases that matter: the four unmapped Kitchen loads, and any CIP
link outage, where all twenty-six AADS loads would claim the house is dark. Fixed by setting
`availability` to `has_value('binary_sensor.crestron_<load>')`, which is false for both unknown and
unavailable.

## Deploying

```
put custom_components/crestron_cip/*.py  /config/custom_components/crestron_cip/
put custom_components/crestron_cip/manifest.json  /config/custom_components/crestron_cip/
put custom_components/crestron_cip/services.yaml  /config/custom_components/crestron_cip/
```

Then add one line to `configuration.yaml`:

```yaml
crestron_cip:
```

Hosts and IP-IDs default to the AADS at `192.168.4.61` on `0x13` and the MC2E at `192.168.4.59` on
`0x03`, and can be overridden per link. Restart Home Assistant; the integration is YAML-configured
and has no config flow, because its addressing is fixed by physical hardware and there is exactly
one house.

Back up `configuration.yaml` first. The SSH & Web Terminal add-on must be running.

Home Assistant caches the `custom_components` listing at startup, so a `check_config` run before
the restart reports `Integration 'crestron_cip' not found` as a warning. That is expected and not a
sign the manifest is wrong.

**`IP-ID 0x13` holds one client at a time.** While the bridge is running, the proof-of-concept
tools in `mac/` cannot register on the same slot, and plugging panel 13 back in takes the slot
away from Home Assistant.
