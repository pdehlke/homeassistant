# Sequence Path A now, defer Path B to the keypad-replacement phase

Reaching Home Assistant control of Cresnet lighting has two paths: Path A (hire a programmer to
add a scoped XSIG join-mapping bridge to the existing MC2E, bus and keypads otherwise untouched)
or Path B (physically tap the Cresnet bus and reverse-engineer its frame format to remove the
MC2E/AADS from the lighting bus entirely). Do Path A first — cheap, low-risk, unlocks HA lighting
control almost immediately — and treat Path B as the endgame that happens only once the wall
keypads are actually replaced, since that's the point where the low-voltage wiring is already
being disturbed and the reverse-engineering effort only has to cover CLX command frames rather
than the full keypad event vocabulary too. See [docs/crestron/crestron-strategy.md](../crestron/crestron-strategy.md).

## Consequences

Path B's frame-format reverse engineering is undocumented at the protocol level and estimated at
weeks of work, not a weekend of YAML configuration. Deferring it avoids paying that cost before
it's actually needed, but means lighting stays dependent on the MC2E and its XSIG bridge until the
keypad-replacement phase happens.
