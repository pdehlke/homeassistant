# Discrete on/off is synthesised in the bridge, not in Home Assistant

Every lighting button in the TSW-752 panel project is a momentary toggle. One press flips the load,
and no per-load discrete off exists anywhere in the project; the only discrete actions are the
group-off buttons (`Area Off`, `Living Off`). Home Assistant's `light.turn_on` and `light.turn_off`
are discrete by contract, so something has to bridge the two.

That something is the daemon. Each command reads the load's live feedback state, presses only when
the current state differs from the one asked for, and then waits for the processor to confirm
before returning. Presses are serialized per connection behind a lock, because each decision
depends on the state the previous press produced.

The alternative was to express this in Home Assistant, as a condition inside each template light's
`turn_on` and `turn_off` action list. That was rejected because it races. Between the template
reading the feedback entity and the service call landing on the wire, a wall panel or keypad can
change the same load, and a template light has no way to serialize against thirty other entities
or against feedback arriving asynchronously. The failure mode is not a stale reading, it is a
press that turns the light off when the user asked for on.

## Consequences

`turn_on` on a load that is already on is a no-op that presses nothing, which is what makes the
operation idempotent and safe to call from an automation that does not track state. This is
covered by a test, because it is the single easiest thing to regress: a change that presses
unconditionally still passes a naive on/off test while turning lights off in the house.

A command whose confirmation never arrives is retried once and then fails loudly to the caller as
a `HomeAssistantError`, rather than being reported as success. A light that did not change is
exactly what an automation needs to hear about.

A load whose state is unknown refuses rather than pressing blind. State is seeded from the
registration dump, which reports only high joins, so a load the processor never mentions is off
rather than unknown; that inference is only valid once the session is synced, which is why an
unsynced link makes its loads unavailable instead of guessing.
