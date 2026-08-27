# Music chip: radio presets and library playlists on Crestron, adapted from the Scenes chip

A bottom-row "Music" chip that opens a popup of, originally, six labeled bubbles, one per
pre-configured radio station. Tapping a bubble plays that station through Music Assistant on the
Crestron media player and toggles back off (stops) on a second tap, the same on/off chip language
every other control on the dashboard uses. Since 2026-08-26 the popup is a two-category accordion,
"Stations" (the original radio presets) and "Playlists" (Music Assistant library playlists sourced
from Jellyfin), plus a third row, "All Off," that stops whatever is playing without needing to know
which bubble it is; see the Playlists round and the All Off row section near the end of this
document for those additions, the real bugs the first one surfaced, and why Playlists always
shuffle. Since the same day, the Playlists row's contents are no longer hand-maintained in
`config.js` at all — they're synced from Jellyfin via Music Assistant on a schedule; see
[homie-dynamic-playlists.md](./homie-dynamic-playlists.md) for that design and what is and isn't
actually running yet.

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
instead. Originally Stations were a single flat `subGroups` entry with no room-style label, since
there was no grouping dimension yet with six items. The Playlists round below introduced the
grouping dimension pde actually wanted first (content type, not mood or genre): two labeled
`subGroups` entries, "Stations" and "Playlists", rendered as an accordion.

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
instance — see the `home-assistant` skill's [music-assistant.md](../../.claude/skills/home-assistant/references/music-assistant.md)). Only if the player wasn't
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
| AltNation | Alt Nation | `library://radio/40` | SiriusXM (favorited into library) |

The "Original label" column is what `music_assistant.search` returned and what shipped first;
"Label (final)" is pde's shorter relabeling from the same-day follow-up round below. The
label-to-station mapping needed no clarification: each short label is an unambiguous shortening of
its original (genre/mood plus artist or era), and the request explicitly named "1st Wave" as
unchanged.

**Seventh station: AltNation, release `20260824.3`.** pde asked for SiriusXM's AltNation channel
added to the chip. `music_assistant.search` (`name: "AltNation"`, `media_type: ["radio"]`) found it
already resolved and already favorited into the Music Assistant library as `library://radio/40`
("Alt Nation", SiriusXM artwork host), so no `music/favorites/add_item` step was needed this time,
unlike 1st Wave and Blues' original resolution. Added as a seventh bubble using the exact same
config shape and shared icon SVG as the other six, following [ADR 0033](../adr/0033-music-stations-addressed-via-library-uri.md)'s
`library://` addressing convention rather than the station's native `siriusxm://radio/...` URI, for
the same one-scheme-for-every-entry consistency reason that ADR already settled. `HOMIE_ASSET_VERSION`
bumped `20260824.2` → `20260824.3`; `test/screen-a.test.cjs`'s station-list assertion updated to the
seven-entry list. 106/106 tests pass.

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

**AltNation round**, 2026-08-24, release `20260824.3`: added as a seventh station, see the Station
catalog section above for how its `library://radio/40` URI was resolved. Deployed via the same
pattern as every prior `config.js` change: SSH & Web Terminal add-on started, live `config.js` and
`homie-dashboard.html` backed up with a timestamp, both uploaded under temp names, the real
`HA_TOKEN` spliced into the new `config.js` entirely on the HA host (a small remote Python helper
uploaded and run over SSH, not a local shell substitution), atomically renamed into place,
`homie-dash`'s iframe `?v=` bumped `20260824.2` → `20260824.3` via `apply-card.py`
(`HA_MATCH_TYPE=iframe`, dry-run first, one match), add-on stopped again after. `doctor.py` confirmed
live bytes, version, and token all matched post-deploy.

Verified two ways, deliberately without touching Harmony: at the time of this deploy
`remote.harmony_hub` was mid-`Watch TV` activity (not the idle/`PowerOff` baseline every earlier
round assumed), so driving the chip's real tap path would have interrupted whatever the TV was
doing while pde was AFK to notice. Instead: (1) `music_assistant.play_media` called directly on
`media_player.crestron` with `media_id: "library://radio/40"` produced `state: "playing"`,
`media_content_id: "library://radio/40"`, `media_album_name: "Alt Nation"`, exactly the shape
`musicStationIsOn()` matches on, then `media_player.media_stop` returned it to `idle` --
`remote.harmony_hub` never called, confirmed unchanged (`on` / `Watch TV`) before and after; (2) a
Playwright popup screenshot as the `Homie Dashboard` account (`evidence/music-chip-altnation-added.png`
in the sibling `homie-dashboard` repo's `verify-homie-dashboard` skill) showed all seven bubbles,
AltNation last, wrapped to a second row, matching every other bubble's icon and styling, without
tapping it. This proves the new station is correctly wired end to end (config, URI, Music Assistant
playback, on-state matching, and rendering) without exercising the shared Harmony-routing code
path, which is unrelated to this change and was already proven live in the round above.

## Playlists round, 2026-08-26: a second accordion category, real bugs live testing caught, and shuffle

pde's actual ask started as "genre buttons," using MA's browsable Genre concept, and ended up
somewhere else entirely once investigation showed what was and wasn't reachable. Recording the path
because it's the expensive part to reconstruct later.

### What was asked, and what it turned into

The stated goal was genre-driven buttons on the Music chip, modeled visually on how the Climate
chip already lets you pick a category before drilling in. Two things surfaced during grilling that
changed the design before any code was written:

- **MA's Genre objects aren't playable through the API Homie uses.** MA models Genre as a real,
  playable internal type (`library://genre/<n>`, `is_playable: true`, with its own
  `radio_mode_base_tracks` mechanism), but that's only reachable through MA's *native* WebSocket
  API. Both `music_assistant.get_library` and `music_assistant.play_media`, the HA-side services
  Homie already calls, hard-list `media_type` to
  artist/album/track/playlist/podcast/audiobook/radio/folder. Genre isn't in either enum, checked
  directly against the live service schemas, not assumed.
- **pde's actual intent was Jellyfin playlists, not raw MA genres.** He clarified the goal was to
  surface Jellyfin playlists, some of which happen to represent a genre (a large "Alternative"
  playlist already existed, sourced from the same Jellyfin library MA reads). MA already ingests a
  Jellyfin playlist into its regular library, `library://playlist/10` for "Alternative", confirmed
  via `music_assistant.get_library`, so this needed no bridge to MA's native API at all: the exact
  same `music_assistant.play_media` call Stations already use, just `media_type: "playlist"`
  instead of `"radio"`.

### Rejected alternatives, and why

- **Climate's own two-level picker, as the model to copy.** Rejected once its actual mechanism was
  read: `openThermostat()`/`openThermostatNative()` is a bespoke handoff that closes Homie's own
  overlay and dispatches `hass-more-info` into the parent HA frame to open HA's native thermostat
  dialog. There's no HA "more-info dialog" for a station or playlist URI, so nothing about this
  mechanism was reusable; copying it would have meant writing an entirely new, unproven navigation
  system for a distinction (a full second screen with a back button) pde never actually asked for.
- **Raw Jellyfin genre tags as the button source**, bypassing MA. Rejected: it would give Homie a
  second, parallel connection to Jellyfin that has never existed, instead of keeping Music Assistant
  as the single hub the rest of this dashboard already relies on.
- **A dynamic pull of MA's live playlist library**, instead of a hand-curated config list. Rejected:
  `music_assistant.get_library` for playlists returns MA's own 8 built-in smart playlists (500
  Random tracks, Infinite Mix, etc.) alongside real ones, and the item schema has no `provider`
  field, so there is no reliable way to filter "Jellyfin-sourced" from "MA-generated" automatically.
  A hand-picked list, exactly like Stations, sidesteps the filtering problem entirely and matches
  the chip's existing "curated shortcuts, not an exhaustive browser" philosophy.

### Chosen design

**Accordion, not new navigation.** The Lights chip already had a genuinely reusable two-level
pattern: `subGroups` render as category rows inside `openPopup()`, and tapping one expands it in
place via `toggleRoomAccordion()`, one category open at a time, no page navigation. Generalized
that function with an `isMusicControl` branch that renders Music's bubble grid
(`popup-scene-bubble`/`popup-scene-icon`, unchanged markup) instead of a Mushroom card, reusing the
identical CSS the flat popup already used. `dist/config.js`'s Music `subGroups` became two labeled
entries, "Stations" (the existing seven, untouched) and "Playlists" (one entry so far, "Alternative"
→ `library://playlist/10`, `mediaType: "playlist"`). `togglePopupMusic` gained a fourth parameter,
`mediaType`, defaulting to `"radio"` so every Station entry needed no config change at all.

### Two real bugs, found only by driving the deployed page, not by design review

The proof standard this project already holds every Homie change to (`verify-homie-dashboard`'s
"screenshot the real state, independently read the entity, don't trust a save/tap alone") earned
its keep twice in one session:

1. **`refreshOpenAcCards` crashed** (`Cannot read properties of undefined (reading 'startsWith')`)
   the moment the Music popup was left open. Music now shares `c._flatSubs` with every other
   accordion chip as a side effect of the generalization above, but this unrelated function assumed
   every `_flatSubs` owner is entity-keyed (`s.entity.startsWith("climate.")`) and Music's entries
   carry a `uri`, not an `.entity`. One-line guard fix (`!s.entity || !s.entity.startsWith(...)`),
   caught from the browser console during the first live pass, before pde would have seen it.
2. **A playing Playlist could never be detected as "on," and a second tap would restart it instead
   of stopping it.** `musicStationIsOn()` matches `media_content_id === uri`, which works for radio
   because a station never stops being its own URI. Playing "Alternative" live showed MA rewrites
   `media_content_id` to the currently-playing *track's* own URI (`library://track/851`, "Homicide"
   by 999) the instant playback starts, never the playlist's URI again. Checked every other
   candidate attribute on the entity (`active_queue`, `source`, `app_id`); none of them name the
   source playlist either. Fixed with `_lastPlaylistStarted`, an in-memory `entity -> uri` map
   `togglePopupMusic` maintains directly (set on a Playlists start, cleared on any stop or Stations
   switch), the same class of "server state doesn't say what the UI needs" workaround `_acCardState`
   already uses for AC cards. Accepted limitation, same as that precedent: this can drift from truth
   if something outside Homie (another dashboard, an HA automation) redirects the player without
   going through `togglePopupMusic` again.

### Shuffle, added as a same-day follow-up ask

pde asked, after the above shipped and was confirmed live, that Playlists always play shuffled.
`music_assistant.play_media` has no shuffle parameter of its own; the standard HA
`media_player.shuffle_set` service does, and `media_player.crestron`'s `supported_features` bitmask
confirmed it supports `SHUFFLE_SET` (bit `32768`). One live question needed answering before writing
the call: does `shuffle_set` need to run before or after `play_media`, given shuffle is a
player-level setting that might get reset when a new queue starts? Tested directly: setting
`shuffle: true` while idle, then calling `play_media` for the same playlist, kept `shuffle: true`
*and* changed which track played first (a different opening track than the two prior unshuffled
test plays). Setting shuffle after `play_media` would have shuffled everything from the second track
onward, but not the deterministic first pick. Chosen: `shuffle_set` runs immediately before
`play_media`, `true` for a Playlists bubble, explicit `false` for a Stations bubble so a stale
`true` from an earlier Playlists tap can't silently carry over onto radio, where shuffle is
meaningless.

### Verification

`node --test test/screen-a.test.cjs`: 110 → 113 across the two changes (accordion + on-state fix,
then shuffle). New coverage: the accordion's Music branch renders inside `toggleRoomAccordion()`
now, not the old flat `openPopup()` branch; a Playlists bubble's `mediaType` reaches `play_media`
correctly and a Stations bubble still defaults to `"radio"`; a playing Playlist reads "on" via the
tracker even though `media_content_id` never matches its URI, and a second tap stops it rather than
restarting it; switching to a Station clears a stale playlist marker; `shuffle_set(true)` fires
before `play_media` for a Playlists tap and `shuffle_set(false)` fires for a Stations tap.

Deployed across four releases as the bugs surfaced (`20260826.1` through `.4`), same pattern as
every prior round: SSH & Web Terminal add-on started, live `config.js`/`homie-dashboard.html`
backed up with a timestamp, uploaded under temp names, real `HA_TOKEN` spliced into the new
`config.js` on the HA host, atomically renamed into place, `homie-dash`'s Lovelace iframe `?v=`
bumped to match via a direct `lovelace/config/save` (`apply-card.py`'s underlying mechanism, called
directly since only the version query string changed), add-on stopped again after. `doctor.py`
confirmed live bytes, version, and token matched at each step.

Live-verified via Playwright against real `/api/states` reads, restoring state after each check:
opening the Music popup showed the "Stations"/"Playlists" category rows with no bubbles rendered
yet (proving the accordion, not a flat grid, is what's live); expanding "Playlists" and tapping
"Alternative" produced `state: "playing"`, `media_title` naming an actual track from that playlist,
and (after the shuffle round) `shuffle: true`; the bubble's own DOM class read
`"popup-scene-icon on"` while playing, confirming the on-state tracker; tapping it again produced
`state: "idle"` and Harmony `PowerOff`, confirming the stop path actually stops rather than
restarting; expanding "Stations" and playing "Jazz: Hiromi" afterward confirmed radio still works
through the generalized accordion code path, and read `shuffle: false`, confirming a Stations tap
clears a Playlists-tap's shuffle setting. Every mutating check restored the player to its prior
`idle`/Harmony-`PowerOff` state before moving to the next one.

## All Off row, 2026-08-26

Same-day follow-up ask, after the Playlists round above shipped: a way to stop whatever is playing
without having to remember or find which Stations or Playlists bubble started it. The prior design
made this awkward on purpose, by omission: on-state was only ever surfaced on the specific bubble
that was playing, so stopping meant opening the right category first.

### Chosen design

A third row, "All Off," appended below the Stations and Playlists category rows inside the same
accordion popup, not inside either category and not a category itself: no chevron, no expanding
panel, always present regardless of which (if any) category is expanded. Tapping it calls
`stopAllMusic()`, which runs the identical `media_player.media_stop` + `remote.turn_off` sequence
`togglePopupMusic`'s own off branch already used, factored out into a shared `stopPopupMusic()` so
there is exactly one stop sequence in the code, not two that could drift apart. Styling and the
power icon are reused verbatim from the TV control overlay's own pre-existing "ALL OFF" button
(Harmony's built-in `PowerOff` activity), rather than invented fresh, so the same word means the
same thing visually everywhere it appears in the app.

No alternative design was seriously considered: the ask was narrow and the accordion mechanism
already had an obvious, uncontested place to hang a third static row.

### Verification

`node --test test/screen-a.test.cjs`: 113 → 115. New coverage: `stopAllMusic` runs the same two
calls in the same order as tapping an active bubble; it clears a playing Playlist's
`_lastPlaylistStarted` marker too, not just a Station's live `media_content_id` match; it no-ops
against an `unavailable` or never-cached target, same guard `togglePopupMusic` already has; and the
accordion's HTML-building code only emits the row when `isMusicControl` is true.

`HOMIE_ASSET_VERSION` `20260826.4` → `20260826.5`, deployed via the same SSH-add-on-start /
backup / upload / splice / rename / add-on-stop pattern as every prior round, `homie-dash`'s
Lovelace iframe `?v=` bumped to match via a direct `lovelace/config/save`. Live-verified via
Playwright against real `/api/states` reads: started "Jazz: Hiromi" (confirmed
`media_player.crestron` `state: "playing"`), tapped the new "All Off" row, confirmed via the real
entity that it returned to `idle` and `remote.harmony_hub`'s `current_activity` returned to
`PowerOff`, and the bubble's on-ring cleared in a follow-up screenshot.
