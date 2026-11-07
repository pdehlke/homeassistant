# Office wall display: rebuilding the Raspberry Pi kiosk

The Office wall display is a Raspberry Pi 5 whose desktop session opens Chromium full screen on the
Clock dashboard, `dashboard-clock`. On 2026-10-09 the Pi crashed with no backup of its SD card, and
the steps that had originally set it up turned out never to have been written down anywhere in this
repo. This document is the replacement. The card has since kept failing every couple of months, so
on 2026-11-06 the procedure was turned into a ready-to-flash image that configures itself on first
boot and runs with its root filesystem on a RAM overlay.

**Status: image built and checked offline, not yet booted.** The manual procedure was assembled
on 2026-10-09 from Raspberry Pi's documentation and this instance's live configuration, and pde
confirmed its autostart line at the display. The image was built on 2026-11-06 from the
`2026-10-06` Raspberry Pi OS (Trixie) desktop release. Its configuration was validated against
that image's own cloud-init schema and netplan, as described under "How the image was checked".
Nobody has flashed it to a card and booted it yet. The "Still open" section lists what remains.

## What the display needs

Four things have to be true for the panel to come up on the dashboard with nobody touching it:

1. The Pi's user logs into the desktop automatically at boot.
2. That desktop session starts Chromium in kiosk mode on the Clock dashboard.
3. The Pi answers at `192.168.4.136`, because that address is what logs it into Home Assistant.
4. The panel switches off at 18:00 and back on at 05:00, Arizona time.

The third is easy to forget during a rebuild because nothing on the Pi configures it. Home
Assistant's trusted networks auth provider grants the `office` identity to exactly that one
address, with no login screen. See
[trusted-networks-auto-login.md](../auth/trusted-networks-auto-login.md) and
[ADR-0065](../adr/0065-trusted-networks-auto-login-for-office-wall-display.md). A Pi that comes up
on any other address shows a login screen on a panel with no keyboard.

## The image

The build lives outside this repo, in the private
[pdehlke/office-display-image](https://github.com/pdehlke/office-display-image) repository, cloned
at `~/src/office-display-image/` on pde's laptop. It is kept separate because this repo takes no
deployable configuration and the finished image contains the Wi-Fi password. That repository
holds:

| File | What it is |
| --- | --- |
| `user-data.template` | The cloud-init configuration, reproduced in full below. |
| `build.sh` | Downloads and verifies a stock image, then writes the configuration onto its boot partition. macOS only. |
| `docs/build/image-build.md` | How the build works, including how it picks the stock image. |

It has been under git since 2026-11-07 and on GitHub since the same day. Disk images are ignored
by its `.gitignore`, so the stock image and the built image exist only on the laptop. `build.sh`
can download the stock image again and rebuild the output from it.

### Building it

`build.sh` reads three values from the environment. Run it in your own terminal rather than
through an agent, so the Wi-Fi password never lands in a transcript:

```sh
cd ~/src/office-display-image
export KIOSK_SSH_PUBKEY="ssh-ed25519 AAAA..."   # one line, e.g. from `ssh-add -L`
export KIOSK_WIFI_SSID="..."
export KIOSK_WIFI_PSK="..."
./build.sh              # the current Raspberry Pi OS release
./build.sh 2026-10-06   # a specific release
```

With no argument it builds from the current 64-bit desktop release, which it finds by following
the `raspios_arm64_latest` redirect on `downloads.raspberrypi.com`. A release date picks the image
from `raspios_arm64/images/raspios_arm64-<date>/` instead. The stock `.img.xz` is saved in the
build directory, checked against its published `.sha256` with `shasum -a 256 -c`, and reused on
later runs once it passes the same check.

It decompresses the stock image and attaches it with `hdiutil` without mounting the Linux
partition. It mounts the FAT boot partition, writes `user-data` from the template with the key
substituted in, and writes a `network-config` holding the Wi-Fi network. Then it detaches the
image, leaving `office-display-2026-10-06-raspios-trixie-arm64.img` for the 2026-10-06 release,
and prints its SHA-256. Recompressing to `.img.xz` is in the script but commented out, so the
output is the raw `.img`. `meta-data` is left as the stock image ships it. The output is created
mode `0600` because of the password inside it. Keep it out of git and cloud storage.

Flash the output with Balena Etcher. Do not customise it in Raspberry Pi Imager: Imager 2.0 writes
its own cloud-init files to the boot partition
([Raspberry Pi blog](https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/)) and would
replace these.

A newer Raspberry Pi OS release that changes how the first-boot user rename or `raspi-config`
works would need the checks below repeated before its image is trusted.

### What happens on first boot

Raspberry Pi OS runs cloud-init from the boot partition, using the `NoCloud` datasource seeded
from `/boot/firmware`. The order below comes from the stock image's `/etc/cloud/cloud.cfg`:

1. Raspberry Pi OS's cloud-init distro class renames the image's stock uid-1000 `pi` user to
   `kiosk` through `/usr/lib/userconf-pi/userconf`. The user keeps `pi`'s groups, gets the SSH
   key and passwordless sudo, and has its password locked.
2. The timezone is set to `America/Phoenix`. Wi-Fi comes up from `network-config`.
3. The final stage installs `overlayroot` and writes the labwc autostart file, then runs three
   commands: a `chown` of `~/.config`, `raspi-config` to turn on desktop autologin for `kiosk`,
   and `raspi-config` to enable the overlay file system.
4. cloud-init reboots the Pi. From then on it boots straight to the dashboard with root on a RAM
   overlay.

Two parts of that are less obvious than they look:

- **Autologin has to be set explicitly.** The rename calls `/usr/bin/cancel-rename`, which sets
  desktop autologin only if `/var/lib/userconf-pi/autologin` exists and otherwise sets "desktop,
  login required". The stock `lightdm.conf` autologs into `rpi-first-boot-wizard`, which the same
  script deletes. Without the `do_boot_behaviour B4` line the display stops at a login screen.
- **The `chown` is there because `write_files` creates missing parent directories as root.**
  Without it, `~/.config` would belong to root and neither the desktop session nor Chromium could
  write their settings.

### The user-data

This is `user-data.template` as of 2026-11-06. `@KIOSK_SSH_PUBKEY@` is the only placeholder.

```yaml
#cloud-config
#
# First-boot configuration for the Office wall display, a Raspberry Pi 5 on Raspberry Pi OS
# (Trixie). build.sh substitutes the SSH key placeholder and writes this to the image's boot
# partition as user-data. Rationale and verification are in pdehlke/homeassistant,
# docs/hardware/office-display-pi-kiosk.md.

timezone: America/Phoenix

# Raspberry Pi OS renames its stock uid-1000 "pi" user to the first user listed here, keeping
# pi's groups. The password is locked: the desktop logs in automatically and SSH takes the key.
users:
  - name: kiosk
    shell: /bin/bash
    lock_passwd: true
    ssh_authorized_keys:
      - @KIOSK_SSH_PUBKEY@
    sudo: ALL=(ALL) NOPASSWD:ALL

enable_ssh: true
ssh_pwauth: false

# overlayroot is what raspi-config's overlay file system option needs. raspi-config would
# install it itself, but listing it here makes a failed install show up in cloud-init's log.
package_update: true
packages:
  - overlayroot

write_files:
  # Deferred so it is written after the kiosk user exists.
  - path: /home/kiosk/.config/labwc/autostart
    owner: kiosk:kiosk
    permissions: '0644'
    defer: true
    content: |
      chromium https://hass.ehlke.net/dashboard-clock/0 --kiosk --force-device-scale-factor=2 --noerrdialogs --disable-infobars --no-first-run --enable-features=OverlayScrollbar --start-maximized --password-store=basic &

  - path: /usr/local/bin/office-display-power
    permissions: '0755'
    content: |
      #!/bin/sh
      # Usage: office-display-power on|off
      # Powers the display's outputs on or off with wlopm, the tool Raspberry Pi OS's own screen
      # blanking uses. Run as the desktop user. Cron has no session environment, so this finds
      # the user's Wayland socket itself rather than assuming its name.
      set -e
      case "$1" in
        on|off) ;;
        *) echo "usage: $0 on|off" >&2; exit 2 ;;
      esac
      XDG_RUNTIME_DIR="/run/user/$(id -u)"
      export XDG_RUNTIME_DIR
      for socket in "$XDG_RUNTIME_DIR"/wayland-*; do
        if [ -S "$socket" ]; then
          WAYLAND_DISPLAY="${socket##*/}"
          export WAYLAND_DISPLAY
          exec wlopm --"$1" '*'
        fi
      done
      echo "office-display-power: no Wayland socket in $XDG_RUNTIME_DIR" >&2
      exit 1

  # Times are in the system timezone, America/Phoenix, which has no daylight saving time.
  - path: /etc/cron.d/office-display-power
    permissions: '0644'
    content: |
      0 18 * * * kiosk /usr/local/bin/office-display-power off
      0 5 * * * kiosk /usr/local/bin/office-display-power on

runcmd:
  # write_files creates missing parent directories as root, which would leave ~/.config
  # unwritable by the desktop session and by Chromium.
  - [chown, -R, 'kiosk:kiosk', /home/kiosk/.config]
  # The OS's first-boot rename sets "desktop, no autologin" unless told otherwise.
  - [env, SUDO_USER=kiosk, raspi-config, nonint, do_boot_behaviour, B4]
  # Root on a RAM overlay from the next boot on, so nothing the session writes reaches the card.
  - [raspi-config, nonint, do_overlayfs, '0']

# Reboot once so autologin and the overlay take effect.
power_state:
  mode: reboot
  condition: true
```

The `network-config` that `build.sh` writes follows the Wi-Fi example in
[Raspberry Pi's cloud-init post](https://www.raspberrypi.com/news/cloud-init-on-raspberry-pi-os/),
with `regulatory-domain: US` and one change: `optional: false`. That makes `network-online.target`
wait for Wi-Fi, so the first boot's package install does not run before there is a network to
install from. The same post says this file goes to netplan unmodified.

### The autostart line

The Chromium line is the one confirmed at the display on 2026-10-09 with two changes: it opens
`dashboard-clock` rather than `dashboard-office`, and it adds `--password-store=basic`. The flags
are otherwise unchanged. The `kiosk` user has no password, so its login keyring cannot be
unlocked, and Chromium would otherwise ask for a keyring password on a panel with no keyboard.
That flag was added on reasoning, not observation, and has not been seen working.

| Flag | What it does |
| --- | --- |
| `--kiosk` | Full screen with no browser chrome. |
| `--force-device-scale-factor=2` | Draws the page at twice its size. Not from the tutorial. |
| `--noerrdialogs` | Suppresses error messages. |
| `--disable-infobars` | Disables notification infobars. |
| `--no-first-run` | Skips the first-run setup experience. |
| `--enable-features=OverlayScrollbar` | Scrollbars appear only when necessary. |
| `--start-maximized` | Starts the browser maximised. |
| `--password-store=basic` | Stores passwords unencrypted instead of in the login keyring. Added 2026-11-06. |

The trailing `&` matters. The autostart file is a shell script run by the compositor, and a
foreground Chromium would hold it open.

### The overlay file system

`raspi-config`'s overlay option prepends `overlayroot=tmpfs` to `cmdline.txt`. From the next boot
on, every write to the root filesystem goes to RAM and is discarded at shutdown, which is the
point. Chromium's cache and the system logs are the usual SD card killers, and they no longer
reach the card. The display keeps no state worth saving. Home Assistant identifies it by address,
and the `kiosk_mode` block lives in the dashboard config, so a fresh session at every boot costs
nothing.

It changes how the Pi is maintained:

- **Nothing changed over SSH survives a reboot**, package upgrades included. To make a lasting
  change, run `sudo raspi-config nonint do_overlayfs 1`, reboot, make the change, then
  `sudo raspi-config nonint do_overlayfs 0` and reboot again. Or rebuild the image, which is the
  better answer for anything that should outlive the next card.
- **The overlay lives in RAM**, so whatever Chromium writes accumulates until the next reboot.
  Nothing reboots this Pi on a schedule.

### Turning the panel off at night

`/etc/cron.d/office-display-power` runs `office-display-power off` at 18:00 and `on` at 05:00 as
`kiosk`. Cron uses the system timezone, which cloud-init sets to `America/Phoenix`. Arizona does
not observe daylight saving time, so the times never shift.

The script uses `wlopm`, which is what `raspi-config`'s own screen blanking puts in the labwc
autostart file (`swayidle -w timeout 600 'wlopm --off \*' resume 'wlopm --on \*'`). It
DPMS-blanks the outputs without removing them, so Chromium's window and layout are untouched when
the panel comes back. Cron runs without the desktop session's environment, so the script sets
`XDG_RUNTIME_DIR` from the user's uid and finds the Wayland socket by looking for it. It does not
hardcode `wayland-0` or `wayland-1`. The configuration documentation's own example uses
`wayland-1` for this display, and the name is not something this build controls.

Cron jobs are fixed times, not a state. A Pi that boots between 18:00 and 05:00, after a power
cut for instance, shows the dashboard until the next 18:00. Nothing turns the panel off at boot
during the off hours.

## How the image was checked

Everything here was checked on 2026-11-06 without booting the image. The stock image's root
filesystem was read with `debugfs` in a Debian container, without mounting it.

- **cloud-init order and the Raspberry Pi OS specifics** were read from the image itself:
  `/etc/cloud/cloud.cfg` for module order (`write_files_deferred` and package install run before
  `runcmd`), `cloudinit/distros/raspberry_pi_os.py` for the user rename, and
  `/usr/lib/userconf-pi/userconf` and `/usr/bin/cancel-rename` for the autologin behaviour
  described above.
- **The tools the configuration calls are in the stock image**: `wlopm`, `cron`, `chromium` and
  `/etc/init.d/lightdm`, which `do_boot_behaviour` needs. `overlayroot` is not, hence the package
  install.
- **`raspi-config`'s functions** were read from its
  [source](https://github.com/RPi-Distro/raspi-config): `do_boot_behaviour B4` takes the user
  from `SUDO_USER`, `do_overlayfs 0` enables the overlay, and labwc screen blanking is only on
  when `swayidle` appears in the user's autostart file. The image's autostart file has no
  `swayidle`, so the session does not blank on its own.
- **A test build with dummy credentials** went through `build.sh` end to end. Its `user-data`
  passed `cloud-init schema` using the image's own schema files. Stock Debian cloud-init rejects
  `enable_ssh`, which is a Raspberry Pi OS extension. Its `network-config` passed
  `netplan generate`, and the generated NetworkManager profile had the SSID right, apostrophe
  included. The embedded power script and `build.sh` both pass `shellcheck`. The test image was
  deleted afterwards.
- **The Wi-Fi MAC address is not randomised**, so the `192.168.4.136` reservation keeps matching.
  The image's NetworkManager configuration disables only scan-time MAC randomisation and sets no
  `cloned-mac-address`.

## Manual procedure

This is the 2026-10-09 procedure, kept as the fallback if the image fails. It follows Raspberry
Pi's
[kiosk mode tutorial](https://www.raspberrypi.com/tutorials/how-to-use-a-raspberry-pi-in-kiosk-mode/),
which targets Raspberry Pi OS (64-bit) with the labwc compositor. The tutorial's example URLs are
replaced with the Clock dashboard, and its tab-rotation script is left out, since this display
shows one page. It sets up neither the overlay nor the night-time schedule.

1. Flash Raspberry Pi OS (64-bit), the desktop image, with Raspberry Pi Imager. In the Imager's
   OS customisation, set a username and password, configure wireless LAN, and enable SSH on the
   Services tab.
2. Run `sudo raspi-config` and set two entries under `1 System Options`, as named in the
   [raspi-config documentation](https://www.raspberrypi.com/documentation/computers/configuration.html):
   `S5 Boot` to `B2 Desktop Desktop GUI`, and `S6 Auto Login` to yes.
3. Put the autostart line above in `~/.config/labwc/autostart` as the display's user.
4. `sudo reboot`.

Steps 1, 2 and 4 were never individually confirmed. Whether auto-login came from step 2 or was
already the default on the fresh image was not recorded.

## Resolution and magnification

A fresh Raspberry Pi OS install drives this display at 3840x2160, read back with `wlr-randr` on
2026-10-09. That is a much higher resolution than the previous install used, and at it the
dashboard is too small to read from across the room.

`--force-device-scale-factor=2` in the autostart line fixes that inside Chromium. The page lays out
as though the screen were 1920x1080 and is drawn at twice the size. pde confirmed `2` by eye at the
display. The flag accepts decimals, so `1.5` or `2.5` are available if the display or the viewing
distance changes.

To check what the display is doing, over SSH as the display's user:

```sh
export WAYLAND_DISPLAY=wayland-1
wlr-randr
```

It lists each output with its supported modes, marks the one in use as current, and prints the
desktop scale. The `WAYLAND_DISPLAY` export is how the
[configuration documentation](https://www.raspberrypi.com/documentation/computers/configuration.html)
shows `wlr-randr` being run from outside the desktop session. The same page documents the
graphical route: Preferences > Control Centre, on the Screens tab.

Two other ways to get the same magnification were available and not used:

| Option | Why it was not used |
| --- | --- |
| Desktop scaling of 2.0 in Control Centre > Screens | Magnifies the whole session. It lives in desktop settings on the SD card, away from the one line this document already has to restore, so a rebuild has a second thing to remember. |
| Dropping the output mode to 1920x1080 | Gives up the panel's sharpness. It is the lighter load on the Pi, which renders a quarter of the pixels, so it is the thing to try if the dashboard ever feels sluggish at 3840x2160. Not tried. |

## The URL

The display shows `dashboard-clock`, the Clock dashboard
([ADR-0057](../adr/0057-wall-clock-own-dashboard-not-overview.md)). pde confirmed on 2026-11-07
that this is the right dashboard. The 2026-10-09 version of this document named `dashboard-office`,
the Office user's own dashboard, which is not the one the display shows. The Clock dashboard has
exactly one view with no title or `path`, read back from its config on 2026-09-07
([clock-kiosk-mode.md](../native-dashboards/clock-kiosk-mode.md)), so `/0` addresses it by index.
That was not re-read from the live instance when the URL was corrected.

Use the `hass.ehlke.net` name, never a literal address or the retired `homeassistant.local`. Every
request reaches Home Assistant through the Caddy proxy
([caddy-reverse-proxy.md](../networking/caddy-reverse-proxy.md)), and the direct `:8123` port no
longer answers.

## Two layers called "kiosk"

Chromium's `--kiosk` flag and the dashboard's `kiosk_mode` block are separate things and the
display needs both.

- `--kiosk` removes the browser's own window frame, tabs and address bar. It is set on the Pi, in
  the autostart line above, and is what this document restores.
- `kiosk_mode` removes Home Assistant's header and sidebar inside the page. It lives in the
  dashboard's saved config, scoped to the `Office` user, and survived the crash because it was
  never on the Pi. It can be lost separately, when the dashboard is saved from the graphical
  editor ([ADR-0061](../adr/0061-kiosk-mode-lost-on-gui-edit-reapply-dont-prevent.md)). The
  Clock dashboard's block is described in
  [clock-kiosk-mode.md](../native-dashboards/clock-kiosk-mode.md), along with the command that
  reapplies it.

If the rebuilt display shows the dashboard with a Home Assistant header above it, the Pi is
correct and the `kiosk_mode` block is what went missing.

## If it does not come up right

Over SSH as `kiosk`, `sudo cloud-init status --long` and `/var/log/cloud-init-output.log` show
what the first boot did. With the overlay on, that log is the one written at first boot, because
it reached the card before the overlay existed.

| Symptom | Likely cause |
| --- | --- |
| Home Assistant login screen | The Pi is not at `192.168.4.136`, so the trusted networks provider does not match it. Check the DHCP reservation. |
| "Your computer is not allowed" | The address matches but Home Assistant's trusted proxy setting has been widened to include it. See the reverse proxy section of [trusted-networks-auto-login.md](../auth/trusted-networks-auto-login.md). |
| Desktop login screen | `do_boot_behaviour B4` did not run or ran before the rename. Check the cloud-init log. |
| Raspberry Pi first-run wizard | The `users` section was not applied, so the rename and `cancel-rename` never ran. |
| Desktop appears, no browser | The autostart file is missing, in the wrong user's home, or owned by root. Or the session is not labwc. |
| A keyring password prompt | `--password-store=basic` is missing from the autostart line. |
| Console login prompt, no desktop | Boot behaviour is set to console. |
| No network on first boot, nothing configured | `network-config` did not match the network. With `optional: false` the boot waits for it before giving up. |
| Panel stays on at night | Check `/etc/cron.d/office-display-power`, then run `office-display-power off` as `kiosk` by hand to see its error. |
| Dashboard with Home Assistant's header and sidebar | `kiosk_mode` was dropped from the dashboard config. Reapply it per ADR-0061. |

## Alternatives not taken

| Option | Why it was not used |
| --- | --- |
| Cloning a working card with `dd` and PiShrink | The simplest image to make, and it captures whatever drift the card has accumulated, SSH host keys and machine id included. Nobody can say what is in it, which is how the 2026-10-09 rebuild came to be undocumented. |
| Building a custom image with [rpi-image-gen](https://github.com/raspberrypi/rpi-image-gen) | Raspberry Pi's own image builder, fully reproducible and shipped with a web-kiosk example. Overkill for one display, and it runs best on a Pi host. Seeding cloud-init on a stock image gets the same result from a laptop. |
| A dedicated kiosk OS image (FullPageOS and similar) | Adds a third-party image to keep current for a job stock Raspberry Pi OS does in one line. |
| A systemd user unit that launches Chromium | More moving parts than a one-line autostart file, and it buys restart-on-crash, which has not been needed. Worth revisiting if Chromium ever exits and leaves a bare desktop on the wall. |
| A long-lived token injected into the browser | Already rejected for this display in [trusted-networks-auto-login.md](../auth/trusted-networks-auto-login.md): it has to be re-injected on every reimage, which is precisely the situation this document covers. |
| `wlr-randr --output ... --off` for the night schedule | Removes the output from the compositor rather than blanking it, so Chromium's window would be rearranged when the output came back. It also needs the output's name, which this build cannot know in advance. |
| HDMI-CEC standby with `cec-ctl` | Would turn the monitor itself off, but only if this monitor honours CEC, which nobody has checked. |
| A password on the `kiosk` user | The hash would be a secret, and the user-data could no longer be recorded here verbatim. Nothing needs one: the desktop logs in automatically and SSH takes the key. |

## Still open

- **The image has never been booted.** Flash it, boot it, and confirm the dashboard comes up
  after the first-boot reboot. Then confirm `office-display-power off` and `on` work over SSH and
  `findmnt /` shows the overlay. Record the results here.
- **`--password-store=basic` is unobserved.** It answers a keyring prompt that may or may not
  appear for a passwordless autologin user.
- **RAM growth under the overlay is unmeasured.** If the display freezes after weeks of uptime, a
  scheduled reboot during the off hours is the obvious fix. One would also turn the panel off
  correctly after a night-time power cut.
- **The DHCP reservation for `192.168.4.136` has not been checked.** ADR-0065 describes the
  address as reserved and
  [trusted-networks-auto-login.md](../auth/trusted-networks-auto-login.md) lists that as
  unconfirmed. The display is on Wi-Fi, so the reservation has to be keyed to the Wi-Fi
  interface's MAC.
- **The mouse cursor is not addressed.** If it shows over the dashboard, that needs its own fix,
  and the fix belongs in the user-data.
- **The power supply has not been checked.** The Pi 5 wants 5V at 5A, and undervoltage is a
  common cause of SD card corruption that the overlay would only partly mask.
- **The previous install's resolution is unknown.** It was lower than 3840x2160, and that is all
  that is recorded. The scale factor of 2 was chosen by eye and may not match the old layout
  exactly.
