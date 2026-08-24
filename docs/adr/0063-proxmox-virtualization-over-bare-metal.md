# Proxmox VE virtualization chosen over bare-metal HAOS, to also host Jellyfin

The Mac mini migration was carried out as a Proxmox VE hypervisor install, not the bare-metal
HAOS install [docs/hardware/mac-mini-migration.md](../hardware/mac-mini-migration.md) planned.
Home Assistant OS runs as VM 100 (3 vCPU, 6144 MB, 48 GB disk); a Jellyfin media server runs
alongside it as its own unprivileged LXC container, with its library reached over a CIFS share
from the Synology NAS. See the sibling `pdehlke/proxmox` repo's `mac-mini-proxmox-plan.md` for
the full build procedure; this repo only records what bears on the Home Assistant instance.

Bare-metal HAOS can only host one operating system. Once Jellyfin needed to live on the same
machine, alongside Home Assistant rather than replacing it, virtualization stopped being optional
and became the only way to run both without a second machine. This doesn't revisit
[ADR-0052](0052-haos-bare-metal-over-container-supervised.md)'s own decision: HAOS `generic-x86-64`
is still the Home Assistant install method, chosen over Container or Supervised for the same
Supervisor/ingress reasons as before. What changed is one level up — whether that HAOS install
sits directly on the hardware or inside a VM.

The migration reused the Mac mini's existing Fusion Drive (a 128 GB PCIe flash blade plus the
original 1 TB SATA HDD) for both the Proxmox host and the guests, rather than following through
on [ADR-0054](0054-ssd-chosen-for-power-loss-protection.md)'s planned SSD purchase; that ADR is
marked superseded by this one. The blade holds the Proxmox host itself and the Home Assistant
VM's disk; the HDD was repurposed for Jellyfin's container disk and bulk/backup storage instead
of being retired.

A fourth guest, a small Caddy LXC, replaced direct `:8123`/`:8095` access with a name-based
reverse proxy on port 80. See
[docs/networking/caddy-reverse-proxy.md](../networking/caddy-reverse-proxy.md) and
[ADR-0064](0064-caddy-reverse-proxy-replaces-direct-ports.md).
