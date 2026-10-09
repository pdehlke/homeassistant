# Office wall display: rebuilding the Raspberry Pi kiosk

The Office wall display is a Raspberry Pi whose desktop session opens Chromium full screen on the
Office dashboard. On 2026-10-09 the Pi crashed with no backup of its SD card, and the steps that
had originally set it up turned out never to have been written down anywhere in this repo. This
document is the replacement.

**Status: reconstructed, partly confirmed.** The procedure below was assembled on 2026-10-09 from
Raspberry Pi's own documentation and from this instance's live configuration. The same day, pde
reinstalled the OS and confirmed at the display that the autostart line in step 3, with its
`--force-device-scale-factor=2`, gives a dashboard readable from across the room. The other steps
have not been individually confirmed. The "Still open" section at the bottom lists what remains.

## What the display needs

Three things have to be true for the panel to come up on the dashboard with nobody touching it:

1. The Pi's user logs into the desktop automatically at boot.
2. That desktop session starts Chromium in kiosk mode on the Office dashboard.
3. The Pi answers at `192.168.4.136`, because that address is what logs it into Home Assistant.

The third is easy to forget during a rebuild because nothing on the Pi configures it. Home
Assistant's trusted networks auth provider grants the `office` identity to exactly that one
address, with no login screen. See
[trusted-networks-auto-login.md](../auth/trusted-networks-auto-login.md) and
[ADR-0065](../adr/0065-trusted-networks-auto-login-for-office-wall-display.md). A Pi that comes up
on any other address shows a login screen on a panel with no keyboard.

## Procedure

This follows Raspberry Pi's
[kiosk mode tutorial](https://www.raspberrypi.com/tutorials/how-to-use-a-raspberry-pi-in-kiosk-mode/),
which targets Raspberry Pi OS (64-bit) with the labwc compositor. The tutorial's example URLs are
replaced with the Office dashboard, and its tab-rotation script is left out, since this display
shows one page.

### 1. Image the card

Flash Raspberry Pi OS (64-bit), the desktop image, with Raspberry Pi Imager. In the Imager's OS
customisation, set a username and password, configure wireless LAN if the display is not wired,
and enable SSH on the Services tab so the remaining steps can be done from another machine.

### 2. Log into the desktop automatically

Run `sudo raspi-config` and set two entries under `1 System Options`, as named in the
[raspi-config documentation](https://www.raspberrypi.com/documentation/computers/configuration.html):

- `S5 Boot`: choose `B2 Desktop Desktop GUI`.
- `S6 Auto Login`: answer yes to "Would you like to automatically log in to the desktop?"

### 3. Start Chromium from the labwc autostart file

Edit `~/.config/labwc/autostart` as the display's user, creating it if it does not exist, and put
this one line in it:

```sh
chromium https://hass.ehlke.net/dashboard-office/0 --kiosk --force-device-scale-factor=2 --noerrdialogs --disable-infobars --no-first-run --enable-features=OverlayScrollbar --start-maximized &
```

Every flag but one is the tutorial's, unchanged. `--force-device-scale-factor=2` was added for this
display and is explained in the next section.

| Flag | What it does |
| --- | --- |
| `--kiosk` | Full screen with no browser chrome. |
| `--force-device-scale-factor=2` | Draws the page at twice its size. Not from the tutorial. |
| `--noerrdialogs` | Suppresses error messages. |
| `--disable-infobars` | Disables notification infobars. |
| `--no-first-run` | Skips the first-run setup experience. |
| `--enable-features=OverlayScrollbar` | Scrollbars appear only when necessary. |
| `--start-maximized` | Starts the browser maximised. |

The trailing `&` matters. The autostart file is a shell script run by the compositor, and a
foreground Chromium would hold it open.

### 4. Reboot

```sh
sudo reboot
```

The Pi should come back up on the Office dashboard with no login screen, no Home Assistant header
and no sidebar.

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

`dashboard-office` is the dashboard's `url_path`, confirmed against the live instance's dashboard
list on 2026-10-09. The dashboard has a single view with no `path` of its own
([office-kiosk-mode.md](../native-dashboards/office-kiosk-mode.md)), so `/0` addresses it by
index.

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
  editor ([ADR-0061](../adr/0061-kiosk-mode-lost-on-gui-edit-reapply-dont-prevent.md)).

If the rebuilt display shows the dashboard with a Home Assistant header above it, the Pi is
correct and the `kiosk_mode` block is what went missing.

## If it does not come up right

| Symptom | Likely cause |
| --- | --- |
| Home Assistant login screen | The Pi is not at `192.168.4.136`, so the trusted networks provider does not match it. Check the DHCP reservation. |
| "Your computer is not allowed" | The address matches but Home Assistant's trusted proxy setting has been widened to include it. See the reverse proxy section of [trusted-networks-auto-login.md](../auth/trusted-networks-auto-login.md). |
| Desktop appears, no browser | The autostart file is in the wrong user's home, or the session is not labwc. |
| Console login prompt, no desktop | Step 2 was not applied. |
| Dashboard with Home Assistant's header and sidebar | `kiosk_mode` was dropped from the dashboard config. Reapply it per ADR-0061. |

## Alternatives not taken

None of these was tried. They are recorded so the choice of method is not mistaken for the only
one available.

| Option | Why it was not used |
| --- | --- |
| A systemd user unit that launches Chromium | More moving parts than a one-line autostart file, and it buys restart-on-crash, which has not been needed. Worth revisiting if Chromium ever exits and leaves a bare desktop on the wall. |
| A dedicated kiosk OS image (FullPageOS and similar) | Adds a third-party image to keep current for a job stock Raspberry Pi OS does in one line. |
| A long-lived token injected into the browser | Already rejected for this display in [trusted-networks-auto-login.md](../auth/trusted-networks-auto-login.md): it has to be re-injected on every reimage, which is precisely the situation this document covers. |

## Still open

- **Steps 1, 2 and 4 have not been individually confirmed.** The display is up and showing the
  dashboard, which is what step 3 was confirmed against. Whether auto-login was set through
  `raspi-config` as written, or was already the default on the fresh image, was not recorded.
  Correct whichever step turns out wrong on the next rebuild.
- **What the crashed Pi was actually running is unknown.** The OS release, the compositor and the
  original Chromium flags were not recorded, so this is a working rebuild rather than a faithful
  restoration. If the replacement image does not use labwc, the autostart path above does not
  apply.
- **The DHCP reservation for `192.168.4.136` has not been checked** as part of this rebuild.
  ADR-0065 describes the address as reserved and
  [trusted-networks-auto-login.md](../auth/trusted-networks-auto-login.md) lists that as
  unconfirmed. A reservation is keyed to the Pi's network interface, so the same board on the same
  interface should keep it across a new SD card, but a different board, or a move between wired
  and wireless, will not.
- **Screen blanking and the mouse cursor are not addressed.** The tutorial says nothing about
  either. If the panel goes dark after a period of inactivity or shows a cursor over the
  dashboard, that needs its own fix, and the fix belongs in this document.
- **The previous install's resolution is unknown.** It was lower than 3840x2160, and that is all
  that is recorded. The scale factor of 2 was chosen by eye and may not match the old layout
  exactly.
- **There is still no backup.** The SD card image is the thing that was lost. This document makes
  a rebuild short, and it is the only copy of the configuration.
