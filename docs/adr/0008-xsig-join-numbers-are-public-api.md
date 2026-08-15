# Crestron XSIG join numbers are a stable public API

Once a join number is accepted, it may not be repurposed — a deprecated join is marked reserved,
not recycled — and each subsystem/data-type range must reserve at least 25% expansion headroom.
This treats the join map as a durable interface contract between Crestron and Home Assistant
rather than an implementation detail that can be casually renumbered, since renumbering would
break both sides of an integration that's expensive to touch (a paid programmer visit). See
`docs/crestron/crestron-xsig-programmer-scope.md`.
