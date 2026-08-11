# Homie TV chip: volume and mute controls

The Homie Dashboard TV chip's overlay (Harmony Hub control, see
[harmony-hub-integration.md](harmony-hub-integration.md) for the full integration inventory) gained
a second row of buttons: VOL DOWN, MUTE, VOL UP. Each relays one raw button press to the Integra
AV receiver, the device that owns audio in both configured activities. See
[homie-dashboard-install-plan.md](../homie-dashboard/homie-dashboard-install-plan.md) for the fork
location and deployment workflow this change went through.

## The request

pde asked, before any code was written, whether Home Assistant had enough access to the Harmony
remote's volume up/down and mute controls to put them on a panel. That was answered as a pure
capability question first (see the "Available actions" section of
[harmony-hub-integration.md](harmony-hub-integration.md)): `remote.send_command` can target any of
Harmony's six devices with a raw button command, and volume/mute buttons almost certainly exist for
the Integra receiver since Harmony hubs are paired against the real remote's original codesets. What
wasn't knowable without asking is the exact command strings, since Home Assistant exposes no
per-device button list through any state attribute; the only way to find out is to actually send a
command and watch what happens.

pde confirmed live, in the room, before any UI existed: `remote.send_command` with `device: "Integra
AV Receiver"` and `command: "VolumeUp"`, `num_repeats: 5`, moved the real receiver from volume 50 to
55 (exactly one step per repeat). `command: "Mute"` toggled mute both directions on repeated taps.
Both confirmed by ear against the real device, not inferred from a 200 response, since HTTP 200 from
Home Assistant's services API only means the call was accepted, not that the target device did
anything.

## Options considered and rejected

Grilled before implementation, per the usual pattern for anything with a real design choice:

- **Layout: a second `tv-action-row` matching the existing activity buttons, versus a compact
  rocker-style widget.** Chose the second row. A rocker would read as a different kind of control
  (continuous adjustment vs. discrete mode switch), which is arguably more honest to what it does,
  but it introduces a new visual language into a popup that otherwise has exactly one: the icon +
  label button grid already established by Watch TV / Watch a Movie / All Off. Reusing that grid
  needed zero new CSS beyond a `:disabled` state.
- **Mute feedback: the shared `tv-feedback` Sending…/Done line, versus an optimistic toggle
  highlight on the Mute button itself.** Chose the shared line. Harmony reports no volume level or
  mute state back for any device, so a persistent "muted" highlight would be a guess rendered as a
  fact. It would also drift silently the moment anyone used the physical remote or the receiver's
  own front panel, since nothing here observes real state, only the last button this dashboard
  itself pressed.
- **Off-state: disable the row at `current_activity === "PowerOff"`, versus always leaving it
  enabled.** Chose disabling it. The physical remote has the same problem, a volume button does
  nothing when nothing is on, but a dashboard button that visibly greys out communicates that
  directly instead of leaving a tap to silently do nothing.

## How it works

`tvVolumeAction(command)` in `dist/homie-dashboard.html` calls
`haService("remote", "send_command", { entity_id: CONFIG.harmonyEntity, device: TV_VOLUME_DEVICE,
command })`, where `TV_VOLUME_DEVICE` is the hardcoded string `"Integra AV Receiver"`, the same
pattern the three activity names already use elsewhere in this file (Harmony doesn't expose a
per-activity "volume device" concept to Home Assistant, so there's nothing to read this from). Each
tap is a single, discrete press; there is no repeat-on-hold, matching how every other stepper-style
control in this dashboard behaves (see `nudgeAcTemp`'s `"light"` haptic, reused here for the same
reason: a small repeatable nudge, not a room-wide mode change like `tvControlAction`'s `"medium"`).

`refreshTVControlUI`, already responsible for the activity badge and highlight, now also toggles the
three volume buttons' native `disabled` attribute based on `current_activity`. This runs on overlay
open (fetched live) and after every optimistic update from an activity button tap, so the volume row
tracks activity state without its own subscription.

## Verification

- `node --test test/screen-a.test.cjs`: added coverage for the new markup (buttons exist, correct
  classes, correct `onclick` targets, distinct row from the activity buttons), the `send_command`
  call shape (`device`/`command` fields, `"light"` haptic), and `refreshTVControlUI`'s disable/enable
  behavior across `"PowerOff"`, an active activity, and no activity at all. Full suite 75/75.
- Deployed live: `homie-dashboard.html` re-uploaded by temporary name and atomically renamed,
  checksum-verified against the fork's working tree before and after. `homie-dash`'s Lovelace
  iframe `?v=` bumped alongside the nested `HOMIE_ASSET_VERSION` token, both to `20260811.7`, per
  the two-layer cache-busting convention this dashboard already uses. Both the prior HTML and the
  prior Lovelace config were backed up before either write.
- Playwright, against the live deployed page, with "Watch TV" the real active activity at the time:
  screenshot confirmed the volume row renders correctly and is enabled. Separately exercised
  `refreshTVControlUI("PowerOff")` directly in that same live page (no `haService` calls involved,
  so it never touched the real hub) and confirmed all three buttons report `disabled === true` and
  the badge reads "OFF", then screenshotted that state too.
- pde confirmed live, after deploy: VOL DOWN, MUTE, and VOL UP on the actual TV chip all produced
  the expected audible result on the real receiver.

## What this doesn't cover

- **No volume level readback.** Harmony gives buttons, not state, so this can only ever be
  fire-and-forget up/down/mute, never a slider reflecting an actual position. That would need the
  Integra receiver on its own network integration, which it isn't; today it's reachable only through
  Harmony.
- **No hold-to-repeat.** Each tap is exactly one button press. A physical remote lets you hold for a
  continuous ramp; this dashboard doesn't attempt to simulate that.
- Everything else `harmony-hub-integration.md` records as unused, direct control of the other five
  devices, `harmony.change_channel`, `harmony.sync`, the Universal media-player wrapper idea, and
  state-driven automation off `current_activity`, remains unused. This change only touches volume
  and mute on the one device that carries audio.
