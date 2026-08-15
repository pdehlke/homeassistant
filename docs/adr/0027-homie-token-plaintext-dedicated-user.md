# Homie's HA token stored in plaintext in config.js, under a dedicated non-admin user

Homie Dashboard stores its long-lived HA token in plaintext inside `config.js`, served over HTTP
at a predictable path — anyone able to fetch that URL recovers the token and can act with its
user's permissions, and LAN-only HTTP does not remove the risk. Accepted with mitigation rather
than blocked on: a dedicated non-admin `Homie Dashboard` HA user owns the token (never the
administrator account or the `Tablet` kiosk identity, so it can be revoked independently), and pde
explicitly confirmed acceptance of the residual risk that a standard HA user has no fine-grained
per-entity authorization. See `docs/homie-dashboard/homie-dashboard-install-plan.md`.

## Consequences

Reworking Homie to use an active HA frontend session instead of a plaintext token would require a
maintained fork and a separate design plan; not pursued.
