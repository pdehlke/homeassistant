# Music chip: radio presets on Crestron, the Scenes chip's shape adapted for playback

A bottom-row "Music" chip that opens a popup of six labeled bubbles, one per pre-configured radio
station. Tapping a bubble plays that station through Music Assistant on the Crestron media player
and toggles back off (stops) on a second tap, the same on/off chip language every other control on
the dashboard uses.

## Goal

pde wanted a chip parallel to the just-shipped Scenes chip
([homie-scenes-chip.md](homie-scenes-chip.md)), but for radio listening instead of lighting: a
fixed set of "scenes" in the vernacular sense, each one a radio station rather than an HA `scene.*`
entity, activated on the "Crestron" media player (`media_player.crestron`, a SOUNDFORM AirPlay2
Adapter in the Living Room, integration `music_assistant`) at a controlled starting volume. Six
stations to start: Hiromi + more, 1st Wave, The Jam Radio, Dinner Party Radio, 80s 90s Radio, and
BB King's Bluesville.

This was planned before any code was written: research into the Scenes chip's real implementation,
a live read-only query of Music Assistant's library to resolve each requested station to a real
URI, and a grilling pass over the genuinely ambiguous parts of "on/off toggle" applied to a single
physical player rather than to independent HA entities.

## Design

**Config shape.** A `controls[]` entry mirrors Scenes' `isSceneChip`/`subGroups[].scenes[]` almost
exactly, but as `isMusicChip`/`subGroups[].stations[]`. The one structural difference: every scene
bubble carries its own `entities` (the scene(s) it activates), but every Music bubble targets the
same physical player, so the chip has one fixed `entity: "media_player.crestron"` at the top level
instead. Stations are a single flat `subGroups` entry with no room-style label, since there's no
grouping dimension yet with six items — group by mood or genre later if the list grows enough to
want it, the same way Scenes only introduced multi-scene grouping once a real third case (Primary
Suite) showed up.

**On-state, derived live, not tracked.** `musicStationIsOn(entity, uri)` reads the target player's
own `state` and `media_content_id` directly: "on" means `state === "playing"` and
`media_content_id === uri`, exactly. No separate boolean, no drift risk, same principle
`sceneIsOn()` established for Scenes. `musicChipIsOn(c)` (the chip-level glow) is true only when
the player is mid-playback of one of *that chip's own* configured stations, deliberately narrower
than "is it playing anything" — audio someone else sends to Crestron (AirPlay from a phone, a
different dashboard) shouldn't light the chip up, any more than an unconfigured station would ring
its own bubble. All four read sites (popup bubble ring, chip glow, Overview C sidebar dot, and the
open-popup live refresh) call the same two helpers, the same discipline Scenes' write-up called out
and tested for.

**Toggle logic**, `togglePopupMusic(entity, uri, bubbleId)`: checks `musicStationIsOn` at the
moment of the tap. Off → on: first start the Harmony Hub's `Airplay` activity with
`remote.turn_on` on `remote.harmony_hub`, then play the station via `music_assistant.play_media`
(`media_id`/`media_type: "radio"`, the pattern already confirmed working for radio content on this
instance — see the `home-assistant` skill's `music-assistant.md`). Only if the player wasn't
already `"playing"`, call `media_player.volume_set` first, after Harmony has started the activity.
On → off: call `media_player.media_stop`, then turn off the Harmony Hub with `remote.turn_off`.
The two systems are intentionally sequenced so the receiver is ready for the AirPlay stream before
Music Assistant begins playback, and stopping playback also releases the receiver activity.

**Sidebar icon.** Unlike a Scenes chip, a Music chip does carry a top-level `entity`
(`media_player.crestron`), but `_sbIcon()`'s generic domain-to-icon map has no `media_player` key,
so without an explicit override it would silently fall through to the generic default icon rather
than reading as music. Added `if (ctrl.isMusicChip) return icons.music;`, same pattern as the
existing `icons.scene` override, with a new radio-wave icon (`icons.music`) reused for every
bubble's own inline SVG too.

## Options considered and rejected

Resolved by grilling before any code was written:

- **What tapping the active station's own bubble does (the "off" direction).** Chosen: an explicit
  `media_player.media_stop` followed by `remote.turn_off` for the Harmony Hub's `Airplay`
  activity. Considered and rejected: pause (resumable, but adds a second implicit state — "paused
  on what" — that Scenes never had to reason about, since HA scenes have no pause concept at all);
  stopping Music Assistant without turning off Harmony (leaves the receiver running); no off state
  at all, bubbles as pure launchers (loses the toggle behavior pde explicitly wanted, and the
  visible on-ring would then never mean anything reversible).

- **Volume reset scope.** The literal first ask ("volume pre-set to X%") would reset volume on
  every tap, including a direct switch between two already-playing stations — the common case once
  more than one station is in regular use. Chosen instead: reset only when the player wasn't
  already `"playing"` at the moment of the tap; a hot-switch leaves the volume exactly where the
  user last set it. Applied uniformly to "was playing anything at all," not specifically "was
  playing one of these six" — simpler rule, and a hot-switch away from unrelated audio shouldn't
  blast to a fixed volume any more than a hot-switch between two presets should.

- **Chip badge.** Because at most one of six stations can ever be "on," the shared `showCount`
  mechanism every other chip uses (Lights, Climate, Scenes) would only ever read "0 on" or "1 on."
  Chosen: skip `showCount` entirely, keep the glow. Considered and rejected: reusing the count
  badge anyway (visual consistency, but odd wording); swapping the chip's own label from "Music" to
  the playing station's name (more informative, but no other chip's label changes dynamically like
  this today — a bigger, more novel change than the ask needed).

- **Chip placement.** Between A/V and TV, pde's explicit choice — full row order is Lights,
  Climate, A/V, Music, TV, Irrigation, Scenes.

- **URI choice for the two SiriusXM-backed stations.** 1st Wave and BB King's Bluesville each
  resolved to both a `library://radio/<n>` URI (favorited into Music Assistant's library) and a
  native `siriusxm://radio/<slug>` URI. Chosen: `library://` for all six, including these two, for
  consistency (every entry addressed the same way, matched against the same field
  `musicStationIsOn()` reads). Risk, documented rather than engineered around: a `library://`
  favorite-list id isn't a content-stable identifier — if either station is ever unfavorited in
  Music Assistant, its id would need re-resolving via `music_assistant.search`. Rejected switching
  those two to their native URI to avoid that risk, since it would mean two of six entries address
  their station differently from the other four for a risk that only materializes if pde edits his
  own MA favorites, which he'd notice.

- **Which HA service plays the station.** `music_assistant.play_media` (already confirmed working
  for radio content on this instance) over the dashboard's own generic `media_player.play_media`
  (used by the existing media browser, but only proven there for whatever `browse_media` hands it,
  not specifically for a `library://radio/...` URI).

## Station catalog

Resolved via `music_assistant.search` on 2026-08-12, all six already existing as favorited Music
Assistant library items:

| Label (final) | Original label | URI | Provider |
|---|---|---|---|
| Jazz: Hiromi | Hiromi + more | `library://radio/1` | Pandora |
| 80s/90s | 80s 90s Radio | `library://radio/2` | Pandora |
| Dinner Party | Dinner Party Radio | `library://radio/4` | Pandora |
| The Jam | The Jam Radio | `library://radio/5` | Pandora |
| 1st Wave | 1st Wave | `library://radio/38` | SiriusXM (favorited into library) |
| Blues | BB King's Bluesville | `library://radio/39` | SiriusXM (favorited into library) |

The "Original label" column is what `music_assistant.search` returned and what shipped first;
"Label (final)" is pde's shorter relabeling from the same-day follow-up round below. The
label-to-station mapping needed no clarification: each short label is an unambiguous shortening of
its original (genre/mood plus artist or era), and the request explicitly named "1st Wave" as
unchanged.

## Verification

**Initial round**, release `20260812.5`:

- `node --test test/screen-a.test.cjs`: 83/83 (7 new: `musicStationIsOn`'s exact-match-plus-playing
  requirement, `musicChipIsOn`'s narrower-than-"playing anything" behavior, `togglePopupMusic`'s
  three directions — idle-start-with-volume-reset, hot-switch-without-volume-reset, and stop — the
  sidebar icon override, and a discipline test confirming all four on-state read sites call the
  same two shared helpers). Also updated the control-row index assertions for the new Lights,
  Climate, A/V, **Music**, TV, Irrigation, Scenes order.
- Deployed to `/config/www/community/homie-dashboard/` via SFTP, prior copies backed up first, real
  `HA_TOKEN` spliced into the placeholder-bearing `config.js` entirely on the HA host (BusyBox
  `sed`, no `-P`) so the token was never captured or printed locally. `homie-dashboard.html`
  confirmed SHA-256-identical to the fork's local `dist/` after upload. `homie-dash`'s Lovelace
  iframe `?v=` bumped to `.5` via `apply-card.py`, prior dashboard config backed up automatically.
- Live-verified via Playwright, authenticated as the Homie Dashboard account, against real
  `/api/states` reads rather than screenshots alone: tapping a station from idle produced
  `state: "playing"`, `volume_level: 0.5`, and the correct `media_content_id`/`media_title`/
  `media_album_name`; manually setting volume to `0.72` and then tapping a different station bubble
  left `volume_level` at `0.72` (hot-switch case); tapping the active bubble again produced
  `state: "idle"`, not `"paused"` (confirms stop, not pause); the popup ring and the bottom chip's
  glow both reflected the real state live, including clearing correctly on stop. The Overview C
  sidebar icon override was unit-tested but not separately live-screenshotted — same code path
  already proven live for Scenes, low incremental risk.

**Follow-up round**, same day, release `20260812.6`: pde reviewed the live result and asked for two
changes, both applied and redeployed the same way (backup, token splice, SHA-256 check, iframe
version bump): volume reset target lowered from 50% to 40% (not re-tested live per pde's explicit
instruction — he'll tune further later if needed), and five of six labels shortened as in the table
above. Regression suite re-run at 83/83 after both edits. New labels confirmed live via a fresh
Playwright screenshot of the popup.

**Harmony routing round**, 2026-08-13, release `20260813.1`: every station start now turns on the
Harmony Hub's `Airplay` activity before the existing Crestron volume/play actions; tapping the
active station stops Music Assistant playback and turns the Harmony activity off. Regression suite
passed 85/85, including idle start, hot-switch, and active-station stop ordering. The updated
`homie-dashboard.html` was backed up and deployed atomically to
`/config/www/community/homie-dashboard/`; its live SHA-256 matched the fork's local `dist/` file,
and `homie-dash`'s iframe URL was updated to `?v=20260813.1`. The Lovelace configuration backup is
`/tmp/backup-homie-dash-20260813-070101.json`. Deployment integrity was verified; interactive
browser approval was intentionally left for pde after deployment.
