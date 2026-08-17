# Home Assistant OS bare metal, not Container or Supervised

Migrating off the Raspberry Pi, HAOS `generic-x86-64` was chosen over a Debian + HA Container
install (drops the Supervisor entirely, meaning no add-ons and no ingress — Music Assistant runs
as an add-on and its working API path is through HA's ingress proxy, so both disappear) and Debian
+ HA Supervised (the old middle ground, unsupported since a six-month deprecation starting release
2025.6). HAOS bare metal is the only option that preserves the current setup, including Music
Assistant, unchanged. See [docs/hardware/mac-mini-migration.md](../hardware/mac-mini-migration.md).
