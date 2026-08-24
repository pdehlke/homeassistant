# SSD choice: capacitor-backed power-loss protection, not endurance (TBW)

**Status:** Superseded by [ADR-0063](0063-proxmox-virtualization-over-bare-metal.md) — the
migration reused the Mac mini's existing Fusion Drive components instead of buying a drive. The
reasoning below is preserved; it would apply again if a drive purchase ever becomes necessary.

SSD datasheets lead with TBW (total terabytes written), the spec everyone compares, but it's
close to irrelevant for this workload: even the lowest-rated candidate drive gives roughly a
century of headroom at the recorder database's actual write volume (2-5 GB/day). What actually
matters for a headless box in an awkward-to-reach location that loses power without warning and
auto-restarts: an unclean shutdown mid-write is the realistic way the SQLite recorder database
gets corrupted, and corruption means a physical trip. The Kingston DC600M was chosen specifically
because it's the only evaluated drive with real hardware protection — onboard capacitors that
flush in-flight writes when power disappears — over cheaper or better-endurance alternatives with
partial or no such protection. See [docs/hardware/mac-mini-migration.md](../hardware/mac-mini-migration.md).
