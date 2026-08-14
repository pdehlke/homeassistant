# Migrating Home Assistant from Raspberry Pi to a Late 2014 Mac mini

**Status: planned, not yet implemented.** Home Assistant currently runs on a Raspberry Pi 4. This
document is the plan for moving it to a surplus Mac mini; nothing below has happened yet.

Target hardware: Mac mini Late 2014 (Macmini7,1), Haswell, 8 GB RAM, 1 TB SATA drive.
Intended deployment: headless, no monitor or keyboard, in a location that is annoying to
reach.

## Which installation method

Home Assistant OS on bare metal, using the `generic-x86-64` image. This is the only option
that preserves the current setup.

| Option | Add-ons | Ingress | Verdict |
|---|---|---|---|
| HAOS `generic-x86-64` | yes | yes | use this |
| Debian + HA Container | no | no | breaks Music Assistant |
| Debian + HA Supervised | yes | yes | unsupported since 2025 |

The Docker container install drops the Supervisor, which means no add-ons and no ingress.
Music Assistant currently runs as an add-on, and the working path to its own API is HA's
ingress proxy. Under a Container install both of those disappear. Music Assistant would
have to be run as a separate container and reached some other way.

Home Assistant Supervised, the old Debian-plus-Supervisor middle ground, is gone. ADR-0014
was reverted, a six month deprecation started in release 2025.6, and it is no longer a
supported method.

HAOS requires UEFI boot with Secure Boot disabled. Macs of this generation have no Secure
Boot, so only the UEFI part matters, and it is satisfied.

## Hardware notes for this specific machine

The Late 2014 mini is a good target. No T2 chip, so unlike the 2018 model the internal
storage is visible to a stock Linux kernel and external boot is not blocked.

RAM is soldered at 8 GB and cannot be upgraded. Home Assistant idles around 2 GB, so this
is not a constraint.

Ethernet works out of the box on the mainline `tg3` driver. Wi-Fi and Bluetooth do not.
The Broadcom BCM43xx parts need proprietary firmware that HAOS does not ship. Plan on a
wired connection. For Bluetooth coverage, use ESP32 Bluetooth proxies, which is the better
design anyway.

Idle power is roughly 7 to 11 W against about 3 W for the Pi. The difference is on the
order of $10 to $20 a year.

Thermals are not a concern at this TDP running a near-idle workload.

## Storage

The 1 TB 5400 rpm drive is the weak point. The recorder database does constant small
writes, the drive is over a decade old, and spinning rust makes the whole UI feel slow.

### Check for a PCIe blade first

The Late 2014 mini has both a 2.5" SATA bay and a PCIe flash slot. Fusion Drive configs
have a 128 GB Apple SSD in that slot. The 2014 blades are AHCI over PCIe rather than NVMe,
and mainline Linux handles them. 128 GB is plenty for Home Assistant.

If a blade is present, install to it. That is the best outcome and requires no
disassembly.

From an Ubuntu live USB:

```bash
lsblk -d -o NAME,SIZE,ROTA,MODEL,TRAN
```

`ROTA=1` marks the spinning disk. Anything else is the blade.

### Options ranked

| Path | Effort | Notes |
|---|---|---|
| Install to existing PCIe blade | none | only if this is a Fusion config |
| Swap SATA HDD for a 2.5" SSD | ~45 min teardown | SATA III, full speed |
| Boot HAOS from a USB 3.0 SSD | none | must be a real SSD in an enclosure, not a thumb drive |
| Leave it on the HDD | none | works, but cut recorder retention and expect the drive to die |

The SSD swap is harder than it sounds on this model. It needs T6 Torx **Security** screws,
the fan removed, and then the logic board pulled out on the iFixit logic board removal tool
(two pins, about $5), because the drive sits underneath the board. Inserting rods into any
holes other than the two correct ones will destroy the logic board. See the
[iFixit guide](https://www.ifixit.com/Guide/Mac+mini+Late+2014+Hard+Drive+Replacement/32815).

HAOS expands its data partition to fill whatever disk it lands on, so there is no
partitioning work to do.

### Which SSD to buy

The internal and external paths take the same drive. A 2.5" SATA SSD either goes in the
mini's drive bay or into a USB 3.0 enclosure, so the drive can be bought before the path is
decided.

The recorder database writes continuously, forever, on a machine that never sleeps. Three
drives worth considering:

| Drive | Capacity | Power loss protection | Why |
|---|---|---|---|
| Crucial MX500 | 500 GB | partial | Cheapest drive still worth owning |
| Samsung 870 EVO | 500 GB | none | The default, best firmware track record |
| Kingston DC600M | 480 GB | full, capacitor backed | Survives unclean shutdowns intact |

All three use TLC NAND with a DRAM cache and carry five year warranties.

#### Endurance is not the deciding factor

SSD datasheets lead with TBW, or terabytes written, the total volume of writes the vendor
warranties. It is the number that gets argued about, and for this workload it is close to
irrelevant.

Home Assistant's recorder on a chatty instance writes on the order of 2 to 5 GB a day. The
lowest rated drive in that table is 180 TBW:

```
180 TBW = 180,000 GB
180,000 / 5 GB per day = 36,000 days, or about 98 years
```

Off by a factor of ten and there is still a decade of headroom, well past the five year
warranty. These drives will fail from controller death, a firmware bug, or simple age long
before the NAND wears out. Do not pay for endurance here.

#### What does matter

Power loss protection. This machine is going somewhere awkward to reach, it will lose power
without warning, and `autorestart` brings it straight back up. An unclean shutdown mid-write
is the realistic way the SQLite recorder database gets corrupted, and corruption on a
headless box in a closet means a physical trip.

The **Kingston DC600M** is the only one of the three with real hardware protection: onboard
capacitors that flush in-flight writes when power disappears. That is the entire argument for
it. It costs more and runs a little warmer. The Micron 5400 PRO and Samsung PM893 are
equivalent if priced better.

The **Crucial MX500** is the value pick. Micron advertises partial power loss immunity,
which protects data already committed but not writes in flight. Better than nothing.

The **Samsung 870 EVO** is the safe default on firmware track record alone, which is the
longest of the three. No power loss protection.

A UPS makes this whole question moot. If the mini ends up behind one, buy on price and stop
thinking about it.

#### Everything else

Avoid DRAM-less and QLC drives, which is most of what shows up at the bottom of a price sort.
The Samsung 870 QVO, Crucial BX500, and Kingston A400 all fall apart under sustained small
writes once the SLC cache fills, and this workload is nothing but sustained small writes.

Capacity is not worth spending on either. Home Assistant needs a few tens of gigabytes even
with generous recorder retention. 500 GB is simply the capacity where the good drives are
cheapest.

Prices move constantly, so check current street prices rather than trusting any figure
written here.

### If going the external route

Use a USB 3.0 enclosure that supports UASP, with an ASMedia ASM1153E or ASM235CM bridge, or
a JMicron JMS578. Unbranded enclosures with no stated bridge chip are the ones that drop off
the bus at three in the morning.

A sealed portable SSD such as a Samsung T7 also works, but it forecloses the option of
moving the drive inside the mini later.

## Booting external, and making the choice stick

The Apple Startup Manager can set a persistent default. Hold Option at the chime, then
**Control-click** the "EFI Boot" entry, or press Control+Return on it. The arrow icon
changes from "boot once" to "make default" and the selection is written to the
`efi-boot-device` NVRAM variable. This mini stores NVRAM in flash with no PRAM battery, so
the setting survives indefinite power loss.

The same thing can be done from macOS while it is still installed:

```bash
sudo bless --mount /Volumes/EFI --setBoot
```

### Why internal is still better for a headless box

The concern is not that the default fails to persist. It is what happens when a boot goes
wrong.

On a cold boot after a power cut, Apple firmware sometimes does not enumerate USB devices
quickly enough and falls through to the next bootable device. If macOS is still on the
internal drive, the machine quietly boots macOS instead of Home Assistant, and there is no
way to tell without carrying a monitor over to it. This machine has no IPMI, no AMT, and no
out-of-band management of any kind. Every boot failure is a physical trip.

If booting external anyway, wipe the internal drive so nothing competes. Confirm the device
identifier first, since the external SSD will also be listed and picking the wrong one
destroys the fresh install:

```bash
diskutil list
sudo diskutil zeroDisk short /dev/diskN
```

That converts a silent wrong-OS boot into a loud nothing-boots failure, which is easier to
diagnose.

Installing to internal storage removes the entire problem. One bootable device, no NVRAM
dependency, no USB enumeration race. Headless and hard to reach is exactly the situation
where that is worth the teardown.

## Set auto power-on before wiping macOS

A headless box has to come back by itself after a power cut. From macOS, before anything
else:

```bash
sudo pmset -a autorestart 1
pmset -g | grep autorestart
```

This is a firmware level setting and survives replacing the operating system. It cannot be
set from Linux. If macOS gets wiped without it, restoring the setting means reinstalling
macOS.

## Destructive step

Writing the HAOS image destroys the entire target disk, partition table included. macOS,
the recovery partition, and any files on that 1 TB drive are gone and not recoverable.
Copy anything worth keeping off the machine before starting.

## Sequence

1. From macOS: `sudo pmset -a autorestart 1`, then verify with `pmset -g`.
2. Boot an Ubuntu live USB. Run the `lsblk` command above and choose the install target.
3. Download `haos_generic-x86-64-*.img.xz` and write it to the target with the Ubuntu Disks
   utility or Balena Etcher. HAOS has no installer; the image is written by hand.
4. If booting external, zero the internal disk.
5. Take a full backup on the Pi (Settings, System, Backups) and download it.
6. Shut the Pi down. Two machines answering to `homeassistant.local` over mDNS is a bad
   afternoon.
7. Boot the mini. Hold Option and pick "EFI Boot" if the firmware does not find the disk on
   its own.
8. Control-click that entry to make it the default.
9. Onboarding, then restore from the backup. Add-ons are re-pulled as x86-64 images, so the
   aarch64 to x86-64 move is fine.
10. Pull the power cord, plug it back in, and confirm the machine comes up on its own.

Step 10 is the one people skip. Do it while the monitor is still attached, not after the
mini is back in its awkward corner.

## After the move

The Music Assistant add-on's ingress entry token and add-on slug hash change on restore.
Anything that looks them up dynamically keeps working; anything that hardcoded them needs
updating. The `config_entry_id` for the Music Assistant integration is preserved by the
backup restore, but it is worth re-reading rather than assuming.

## References

- [Home Assistant: Generic x86-64 installation](https://www.home-assistant.io/installation/generic-x86-64)
- [ADR-0014, Home Assistant Supervised](https://github.com/home-assistant/architecture/blob/master/adr/0014-home-assistant-supervised.md)
- [Discussion: drop support for Supervised](https://github.com/home-assistant/architecture/discussions/1198)
- [iFixit: Mac mini Late 2014 hard drive replacement](https://www.ifixit.com/Guide/Mac+mini+Late+2014+Hard+Drive+Replacement/32815)
- [Kingston DC600M product page, power loss protection details](https://www.kingston.com/en/ssd/dc600m-data-center-solid-state-drive)
