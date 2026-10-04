# Homie TV chip: Samsung controls

The TV chip's overlay gained a Samsung section on 2026-10-04, below the Harmony Activity buttons and
the Integra volume row. It shows the screen's real power state, powers the screen alone, and carries
a remote pad. [Issue #31](https://github.com/pdehlke/homeassistant/issues/31) is the PRD.

This document records what was built, what the set was measured to do, the options that were
rejected, and what is still open.

## Status

Deployed to the live instance at `HOMIE_ASSET_VERSION` `20261004.1`, with the `homie-dash` iframe's
`?v=` matching, and committed in the fork after pde confirmed on 2026-10-04 that every pad key works
on the set.

That confirmation is the only evidence the keys land. Home Assistant accepts every key and returns
success, but it also returns success for a key name that does not exist (see below), so success from
the API proves nothing about the screen.

One thing is still open: **the shortcut list is empty.** pde has not yet said which inputs and apps
get buttons, and which per-input key or source this set honours can only be found by watching it.
The row stays hidden until the list has entries. Whether the overlay has been looked at on the wall
tablet itself, as opposed to a browser at its 1280x800 viewport, is not recorded.

## Why Harmony and Samsung both stay

Harmony coordinates several devices in one Activity (the receiver's input, the source box, the
screen) and is the only path to the Integra receiver's volume. The Samsung Smart TV integration is
the only path to the screen's real state and to menu navigation. Neither covers the other's job, so
neither is redundant. The Harmony rows of the overlay were not touched, and their existing tests
pass unchanged.

Two devices in Home Assistant represent this one television. "Living Room TV" is the Samsung
integration's device: `media_player.living_room_tv` and `remote.living_room_tv`. "Samsung QN90BA
85" is the Music Assistant player, `media_player.samsung_qn90ba_85`, which is the set as a speaker
and has no power, source or key control. The chip's `tv` config block names the first pair, and a
test fails if it is pointed at the speaker.

## What was measured on the set

All on 2026-10-04, through the Home Assistant REST API, against the real QN90B.

| Measurement | Result |
| --- | --- |
| `media_player.turn_on` from cold (off for about 12 hours) to state `on` | 11.7 s |
| `media_player.turn_on` a few minutes after switching off | about 5 s |
| `media_player.turn_off` to state `off` | 1.1 s |
| `remote.send_command` round trip, one key | 1.03 s, the same for every key |
| First key after wake (`KEY_HOME`) | 2.5 s |
| Four keys sent concurrently | all four returned in 1.05 s |
| One call carrying a list of two keys | 2.0 s |
| `remote.send_command` with `KEY_NOT_A_REAL_KEY` | HTTP 200 |
| `source_list` with the set on | `TV`, `HDMI`, nothing else |
| State with the set off | `off`, not `unavailable` |

Four consequences follow.

**The pad does not wait on the previous press.** The one-second round trip is a fixed delay inside
the integration, not the set being slow, and concurrent presses do not queue behind each other. A
pad that disabled itself until the call returned would cap navigation at one step a second for no
reason. This is the opposite of the audio zone panel's rule, where a card stays busy for the life of
its call because a zone command really does take seconds.

**A reported failure means the call failed, not that the set ignored the key.** Home Assistant
answers 200 for a key the set does not know. The overlay reports a failed HTTP call, which is the
only failure it can see. Story 13 of the PRD ("a shortcut that failed says so") is met only to that
extent, and cannot be met further from the dashboard.

**The integration does not list installed apps or individual HDMI inputs for this set.** The source
list stayed `TV` and `HDMI`. App shortcuts will need app ids found some other way, and per-input
shortcuts will need a key such as `KEY_HDMI1` tested by eye.

**Wake-on-LAN works, so the power button ships.** pde confirmed it on 2026-10-02 and it was
re-measured here. The Harmony infrared fallback the PRD describes was never needed and was not
explored.

One more finding, about what not to do. The set has its own HTTP API on port 8001. Reading
`/api/v2/` returned device information, but querying `/api/v2/applications/<id>` for a run of app
ids hung, then reset the connection, then refused it, and Home Assistant briefly reported the set as
off while that happened. Do not probe that endpoint.

## What was built

The TV chip's control in the fork's `config.js` gained a `tv` block: `player`, `remote`, a `pad` map
from button to key name, and a `shortcuts` list.

The decisions are four pure functions in `homie-custom.js`:

- `tvIsOn(state)`.
- `tvStateLine(state)`, which returns "TV on", "TV off" or "TV off or unreachable". The last covers
  `unavailable`, `unknown` and a missing entity, so a set that has left the network never reads as
  an error.
- `tvChipIsOn(playerState, harmonyState)`.
- `tvShortcutCall(shortcut, tv)`, which turns a shortcut of kind `key`, `source` or `app` into
  `remote.send_command`, `media_player.select_source` or `media_player.play_media`.

The overlay has a state line with a power button beside it, a pad laid out as a cross with OK in the
centre and Back, Home and Menu in three of the corners, and a shortcut row that is hidden when the
list is empty. Every button reuses the overlay's existing `tv-action-btn` style.

### The chip's glow

The chip is lit when the Samsung entity is on, or when a Harmony Activity is running. The PRD left
the rule to the implementer with one constraint: never dark while the screen is visibly on.

Samsung state alone was rejected. It would leave the chip dark for the several seconds between an
Activity starting and the set reporting on, and dark for good if the Samsung entity ever went
unavailable with the screen lit. Harmony state alone is what the chip had before, and is wrong
whenever someone uses the Samsung remote. The same rule drives the Overview C sidebar icon.

### Power

One button. It reads "TV ON" when the set is off and "TV OFF" when it is on, and calls
`media_player.turn_on` or `media_player.turn_off` on the Samsung entity. It does not touch Harmony.

Nothing about it is optimistic. After a tap the button is busy and the feedback line reads "Waking
TV…" until the Samsung entity reports the new state; the state line keeps saying "TV off" for those
seconds because that is still true. If the state has not arrived after 30 seconds the button comes
back and the line says "TV did not respond". A failed call is reported at once.

### Repainting

`refreshOpenTVControl()` runs on every render pass and is a no-op while the overlay is closed. It
changes text, classes and `disabled` on elements that already exist and never rebuilds a button, so
a state update arriving in the middle of a run of pad presses cannot swallow a tap. The shortcut row
is built once, on open.

Both Samsung entities are named in `CONFIG`, so the relevance filter's static sweep picks them up
with no filter change. A test executes the real sweep and asserts it.

The section adds no animation.

### A change to a shared helper

`haService()` now returns `true` or `false` for whether the call succeeded. It returned nothing
before, and every existing caller ignores the value, so nothing else changes. Without it the overlay
had no way to report a failed press.

## Rejected

- **A separate chip, or rebuilding the chip around the Samsung integration.** pde's call, recorded
  in the PRD.
- **TV volume and mute through the Samsung entity.** The set's volume reads 0 with it on. Sound in
  this room goes through the Integra receiver, which is what the existing volume row drives.
- **Separate On and Off buttons.** One button that shows the real state after it acts takes less
  room and cannot disagree with the state line.
- **An optimistic power button.** Waking takes five to twelve seconds, and a button that lit at once
  would be showing a guess for that long.
- **Blocking the pad on the previous press.** See the measurements.
- **Repeat on hold.** One tap sends one key, as every other stepper on the dashboard does.
- **Shipping guessed app ids or untested HDMI keys as shortcuts.** A button that might do nothing is
  worse than no button, and the dashboard cannot tell whether a key landed.

## Verification

The fork's suite went from 173 to 192 passing. The Samsung tests execute the real extracted block
against a fake state cache and a recording service stub, as the audio zone panel's do. Seventeen
mutations were run against the new code, one per guard (the off-state guards, the closed-overlay
guard, the double-tap guard, each failure report, the glow rule in both directions, the entity
targets), and every one failed at least one test.

Live, at `20261004.1`, in a browser at 1280x800 loading the deployed file:

- With the set off the overlay read "TV off", all eight pad buttons were disabled, the shortcut row
  was hidden and the TV chip was dark. The overlay is 612 px tall, so it fits the tablet without
  scrolling, with room for one or two rows of shortcuts.
- Clicking the power button made it busy with "Waking TV…". About five seconds later the state line
  read "TV on", the button was lit and relabelled "TV OFF", the pad was enabled and the TV chip was
  lit. Home Assistant reported `media_player.living_room_tv` as `on` and `remote.harmony_hub` as
  `off` at `PowerOff`, so the screen came on alone.
- Six pad buttons were clicked 400 ms apart. No error appeared and the pad stayed enabled.
- Clicking power again returned everything to the off state within four seconds, confirmed against
  Home Assistant.

The live files were checked byte-identical to the working copy by the fork's `doctor.py`. Host
backups are `config.js.bak-20261004-082430`, `homie-custom.js.bak-20261004-082430` and
`homie-dashboard.html.bak-20261004-082430`.

## Notes for later

- The TV has a DHCP reservation and is assigned to the Living Room area, both done by pde on
  2026-10-02.
- If the integration ever needs re-pairing, someone has to be at the set with the remote, with
  Access Notification set to First Time Only in the TV's Device Connection Manager. The first
  pairing attempt failed with `auth_missing` because the Allow prompt went unanswered.
- The second Samsung set, the TU7000 60, has no Samsung Smart TV integration entry and is out of
  scope here.
