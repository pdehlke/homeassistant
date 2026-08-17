# Replace the AADS outright, not just its control software

The AADS's amplifier and matrix functions aren't separable from its onboard 2-Series control
processor — the only front door to the amp/matrix hardware is the same control engine being
removed for lighting reasons — so once the decision was made to stop depending on Crestron's
control layer, "keep the AADS hardware, replace only the software" was never an available option.
It's replaced outright with either distributed smart amps (one per zone) or a multi-zone matrix
amp, the choice deferred until the AADS's actual active zone/input count is confirmed. See
[docs/crestron/crestron-strategy.md](../crestron/crestron-strategy.md).

## Consequences

Decommissioning the AADS also removes the ST-IO's Cresnet bus master, since the ST-IO's leg is
driven by the AADS, not the MC2E. Whatever the ST-IO's 8 relays and 4 inputs are wired to goes
dark unless it's rewired onto the MC2E's leg or replaced with an HA-native I/O path first. Which
of those two options to use is still open and needs a Crestron programmer's input; this is a known
dependency of the AADS replacement, not yet resolved by it. See
[docs/crestron/crestron-migration.md](../crestron/crestron-migration.md).
