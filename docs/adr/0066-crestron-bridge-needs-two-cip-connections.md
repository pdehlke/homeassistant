# The Crestron bridge holds two CIP connections, split by alarm safety

Home Assistant reaches the lighting system through two simultaneous CIP sessions, not one: the
freed TSW-752 panel slot on the AADS at `IP-ID 0x13` for twenty-six loads, and the unoccupied
XPanel on the MC2E at `IP-ID 0x03` for four Kitchen loads.

The split is forced rather than chosen. The DSC alarm keypad page reuses AADS joins `d130`-`d148`,
with Fire, Medical and Panic on `d146`, `d147` and `d148`, and every page in the panel project has
`DigitalJoinOffset` 0, so this is one join space genuinely shared rather than an artifact. Kitchen
Range (`d141`), Island (`d143`), Kitchen Pathway (`d145`) and Cabinet (`d147`) have no join outside
that range, so those four cannot be driven from the panel slot at all. Every other load that
touches the range has a safe alias on another zone page: Powder is pressed at `d102` rather than
`d142`, Outdoor Kitchen at `d104` rather than `d144`, and Kitchen Perimeter was always at `d103` on
the Dining page.

The alternative was to establish that the AADS gates the shared range on the subsystem-entry join
(`d91` Lights versus `d93` Alarm) and then use `d141`-`d147` directly on one connection. That
gating is inferred from the panel project and has never been confirmed against the AADS program's
logic, and the only way to confirm it empirically is to press an unidentified join on the processor
that carries the alarm interface. Rejected outright. A second TCP connection is a small price.

Receiving a forbidden join is fine and necessary; only writing is refused. Several loads report
their state on an alias inside the range, so the guard is on the write path alone.

## Consequences

The bridge has two independent connection lifecycles, two reconnect loops, and two link-health
entities, and a load is unavailable when its own link is down even if the other is up.

The four Kitchen loads are blocked on a separate problem: which XPanel join drives which of them is
not established. The press map records channels (`0x71` ch4, `0x75` ch0, `0x72` ch3, `0x72` ch2)
but ties only `0x71` ch3 to a name, and feedback semantics on those joins are explicitly unmapped.
Until an identification pass resolves it, those four are declared in the load table with no join
and reported unavailable rather than guessed at. See
[crestron-xpanel-control-path.md](../crestron/crestron-xpanel-control-path.md) for the press map
and [crestron-tsw-panel-control-path.md](../crestron/crestron-tsw-panel-control-path.md) for the
alarm collision.
