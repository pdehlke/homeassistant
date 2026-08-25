# Trusted-networks auto-login over a provisioned token for the Office wall display

The Office wall display, a Raspberry Pi at a reserved LAN address running a browser against this
instance's own frontend, authenticates through Home Assistant's `trusted_networks` auth provider,
mapped to the single `office` account with `allow_bypass_login: true`. It holds no credential of
its own. See [docs/auth/trusted-networks-auto-login.md](../auth/trusted-networks-auto-login.md)
for the configuration, the reverse-proxy interaction it depends on, and what was verified live.

The alternative already in use elsewhere in this instance is a provisioned long-lived token, the
Homie Dashboard pattern from [ADR-0027](0027-homie-token-plaintext-dedicated-user.md). It was
rejected here because the two clients are not the same kind of thing. Homie Dashboard is a
standalone app talking to the WebSocket API, so it has to carry a credential; the Office display is
an ordinary browser session against HA's own frontend, where a token would have to be injected into
browser storage and re-injected after every rotation or reimage. Logging in by hand once and
relying on the stored refresh token was rejected for the same class of reason: it works until the
profile is cleared or the token is revoked, and then a panel with no keyboard in front of it shows
a login screen.

What this decision accepts is that the IP address becomes the credential. Anything answering at
that address gets the Office identity with no secret at all, and LAN addresses are spoofable from
inside the network. The grant is deliberately a `/32` rather than the `192.168.4.0/24` that would
have been less work, and `office` is a non-admin `local_only` account, so the identity is both
narrow and useless from outside the LAN.

This decision is only viable because Home Assistant's trusted proxies list
([ADR-0064](0064-caddy-reverse-proxy-replaces-direct-ports.md) put a Caddy proxy in front of
everything) is scoped to the proxy's own address alone. Home Assistant refuses to authenticate any
client that falls inside a trusted proxy range, so widening that list to the LAN would silently
disable trusted-networks auth for every device on it.
