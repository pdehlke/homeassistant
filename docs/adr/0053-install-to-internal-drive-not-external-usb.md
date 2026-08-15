# Install to the internal drive, not boot from external USB

Booting HAOS from an external USB SSD works and needs no teardown, and the boot-order choice
persists fine in NVRAM. Internal installation was chosen anyway: on a cold boot after a power cut,
Apple firmware can fail to enumerate USB devices quickly enough and silently falls through to the
next bootable device — if macOS is still on the internal drive, the machine quietly boots macOS
instead of Home Assistant, with no way to tell short of a physical trip, since this machine has no
IPMI, AMT, or any other out-of-band management. Installing internally removes the failure mode
entirely: one bootable device, no NVRAM dependency, no USB enumeration race. See
`docs/hardware/mac-mini-migration.md`.
