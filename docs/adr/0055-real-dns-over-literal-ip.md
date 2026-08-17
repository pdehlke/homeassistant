# Real DNS names for every client, retiring the literal-IP hardcode

A Fire HD tablet joining the house needed `homie-dash` reachable without mDNS, since FireOS has no
mDNS resolver at all. The first fix hardcoded a literal LAN IP for the tablet, which worked for
that one client but silently broke every other client: any browser loading the same dashboard via
`homeassistant.local` while Homie's own `fetch()` calls targeted the literal IP hit a same-origin
mismatch, blocked by CORS with no error surfaced anywhere obvious — confirmed the hard way via a
misdiagnosed "History Unavailable" chart. The actual problem was never "the tablet needs an IP," it
was "the tablet's OS can't do mDNS." Fixed by giving every client, tablet included, one real DNS
hostname (`hass.ehlke.net`/`mass.ehlke.net`) that resolves without mDNS, so the outer page and
every inner `fetch()` call always share an origin regardless of which client asks. See
[docs/networking/hostname-migration-to-ehlke-net.md](../networking/hostname-migration-to-ehlke-net.md).
