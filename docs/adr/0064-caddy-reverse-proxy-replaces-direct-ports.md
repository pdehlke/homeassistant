# Caddy name-based reverse proxy replaces direct `:8123`/`:8095` access

Home Assistant and Music Assistant used to be reached directly, each on its own port
(`hass.ehlke.net:8123`, `mass.ehlke.net:8095`). As part of the Proxmox migration
([ADR-0063](0063-proxmox-virtualization-over-bare-metal.md)), a small Caddy LXC now sits in front
of both, routing by hostname on plain HTTP port 80. The direct ports no longer answer at all;
every client goes through the proxy, tablet and browsers alike. See
[docs/networking/caddy-reverse-proxy.md](../networking/caddy-reverse-proxy.md) for what was
verified live and what changed downstream.

Name-based routing was chosen over continuing to expose each service's own port because a single
Mac mini now hosts more than Home Assistant and Music Assistant — Jellyfin joined as a third
service in the same migration — and one port per service does not scale the way one hostname per
service, all on 80, does. It also sets up a single place to add TLS later: Caddy's automatic
HTTPS activates per site address, so terminating TLS for all three hostnames becomes a Caddyfile
change at the proxy, not a per-service reconfiguration. TLS was not part of this change; the proxy
is plain HTTP only, same as the ports it replaced.

This does not change any hostname. `hass.ehlke.net` and `mass.ehlke.net` are the same names
[ADR-0055](0055-real-dns-over-literal-ip.md) established; only the port disappeared, and the LAN
address they resolve to changed as a side effect of the Proxmox migration.

**Update, 2026-08-24 (same day):** the "add TLS later" option this ADR left open was taken.
Caddy's automatic HTTPS is now enabled for all three site addresses. This ADR's own text above
("TLS was not part of this change; the proxy is plain HTTP only") describes the state as it was
at the time this decision was made, not the current state. See
[docs/networking/caddy-reverse-proxy.md](../networking/caddy-reverse-proxy.md) for what was
verified live; the reasoning behind enabling it now isn't captured here.
