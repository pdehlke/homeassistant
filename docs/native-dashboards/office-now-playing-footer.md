# Office dashboard: the now-playing footer

`dashboard-office` gained a fourth section, appended below Weather/News, that mirrors Homie
Dashboard's Overview A/B behavior: a pill appears when a Music Assistant player is active and
disappears shortly after it stops. Built 2026-08-14 on Home Assistant 2026.8.1.

## What Homie actually does, and why it can't be copied

Homie Dashboard's now-playing widget is not dashboard config, it is compiled app logic bundled into
`homie-dashboard.html` (the ~900KB minified frontend served by the Homie Dashboard HACS repo). Our
fork's own `dist/config.js` only supplies the widget's inputs: a `musicPlayers` array of eight
`media_player` entities spanning the whole house (including two TVs), and `musicHideDelay: 10_000`,
a 10-second grace period before the widget hides after playback stops. The widget itself, the OR
logic across all eight players and the hide-delay timer, lives in Homie's proprietary bundle and
cannot be extracted or reused. Replicating the behavior on a native Lovelace dashboard meant
rebuilding the same behavior with standard primitives, not porting code.

One fact simplified the scope question: all eight entities in Homie's `musicPlayers` list,
including both TVs, report `source: "Music Assistant Queue"` in their current state, confirmed via
`/api/states` on 2026-08-14. Every player Homie watches is genuinely MA-driven today; there was no
mixed TV-vs-MA distinction to design around.

## Decisions, and what drove them

- **Scope: whole-house, matching Homie exactly**, not scoped to the Office's own speaker
  (`media_player.lsx_ii_045089_2`). Chosen because that is literally what was asked for, and
  narrowing later is a one-line change if it turns out to feel wrong on the real display.
- **Card: `custom:mini-media-player`** (`kalkih/mini-media-player`, HACS default store, not
  previously installed on this instance), over the built-in `tile` card. Chosen for a closer visual
  match to Homie's pill, at the cost of one new frontend dependency, installed by hand through the
  HACS UI rather than any programmatic call. HACS's repository install path is undocumented
  WebSocket API with no public spec and no prior precedent in this skill; every other HACS plugin
  here went in by hand, and this one followed the same path rather than risking a blind call against
  a live, daily-used instance.
- **Anti-flicker delay: exact parity with Homie's 10s hold**, applied per player, not once
  globally. A single shared "is anything playing" helper cannot drive per-pill behavior correctly:
  if the Office speaker stops while the Gym is still playing, a shared helper stays "on" (something
  is still playing) but says nothing about whether the *Office* pill specifically should still be
  showing its own track. Each of the eight players needed its own independent grace signal.
- **Stacking**: multiple pills can render side by side if more than one player is active at once.
  No attempt to collapse to a single generic indicator.
- **Placement**: last section on the page, not a sticky footer. Lovelace has no dashboard/view-level
  footer primitive; header/footer support exists only on the Entity, Entities, and Statistic card
  types, confirmed against current Home Assistant Dashboards docs. "Footer" here means "bottom of
  the page, scrolls with everything else."
- **Non-interactive display**: the physical screen this dashboard runs on cannot be tapped, so every
  transport control (play/pause, next/prev, volume, mute, shuffle, repeat, source, sound mode,
  group) is hidden. Only artwork, name, and track/artist info render. A card full of dead-looking
  buttons on an untouchable screen reads as broken, not decorative.
- **Artwork: compact thumbnail, not full-bleed.** `mini-media-player`'s artwork modes are all named
  around "cover" in a way that is easy to misread: `cover`, `full-cover`, and `full-cover-fit` are
  all members of the same full-bleed-background family (confirmed by reading
  `mini-media-player-bundle.js` directly, the CSS selector is literally
  `ha-card.--has-artwork[artwork*='cover']`), while `default` is the actual small-thumbnail-plus-text
  layout most people picture when they hear "cover art." The first build used `artwork: cover` and
  produced a full-bleed background image that buried the Frosted Glass translucency the rest of the
  dashboard uses; switched to `artwork: default` once the bundle source made the naming clear.
- **Styling**: Frosted Glass theme, matching the rest of `dashboard-office`, not Homie's own gold
  theme.

## Two mini-media-player facts that aren't in the published docs

Both confirmed by reading the installed bundle (`/hacsfiles/mini-media-player/mini-media-player-bundle.js`,
v1.16.12) directly, because the `kalkih/mini-media-player` documentation Context7 serves does not
mention them:

- **`hide.power: true`** hides the power toggle button entirely. The documented `hide.power_state`
  only hides the button's colored active/inactive indicator, not the button itself. The getter is
  literally `get showPowerButton(){return!this.config.hide.power}` in the bundle. Without this, a
  clickable-looking power icon rendered on every pill even with every other `hide.*` flag set, wrong
  for a non-interactive display.
- **Artwork mode naming**, covered above: `cover`/`full-cover`/`full-cover-fit` are full-bleed
  background modes; `default` is the compact thumbnail mode. Worth remembering next time this card
  is configured anywhere else in this instance.

## What got built

- **8 `input_boolean.np_grace_*` helpers**, one per player (Office/LSX II, Crestron/Living Room,
  Carol, Gym, Gymnasium, LG TV, Samsung 85, Samsung 60), created via the `input_boolean/create`
  WebSocket command.
- **8 `automation.now_playing_grace_*`**, one per player, `mode: restart`. Two triggers per
  automation (`to: [playing, paused]` and `from: [playing, paused]`), branching on `trigger.id` via
  `choose`: the start branch turns its `input_boolean` on immediately, the stop branch delays 10s
  then turns it off. `mode: restart` means a resume during the 10s hold cancels the pending
  turn-off and re-fires the turn-on branch instead, with no extra guard condition needed.

  This exists because the modern Template helper config flow (`config_entries/flow`, handler
  `template`, step `binary_sensor`) has no `delay_on`/`delay_off` fields at all, confirmed by
  reading its live `data_schema`. That option only exists on the legacy YAML `template:` platform,
  which is not reachable from this machine (no filesystem access to the Pi's `/config`, and no
  documented API for editing `configuration.yaml`). The automation pair is the API-reachable
  equivalent.
- **1 new dashboard section** on `dashboard-office`, appended after Weather/News: eight
  `type: conditional` cards, each gated on its own `np_grace_*` helper being `on`, each wrapping one
  `custom:mini-media-player` card for that player.

Confirmed live via Playwright: the section collapses to zero height (`getBoundingClientRect().height
=== 0`) when no helper is on, no gap left in the layout; a single active player renders one pill;
two active players render side by side; toggling both `input_boolean`s off returns the page to the
zero-height state.

## Naming note

Each pill's `name` follows Homie's own `musicPlayers` labels, not the HA entity's own name or its
raw `entity_id`. `media_player.crestron` (`friendly_name: "Crestron"`) is labeled **"Living Room"**
on its pill, matching Homie's `{ entity: "media_player.crestron", label: "Living Room" }` entry, not
"Crestron." Surfaced 2026-08-14 when a real Living Room playback session didn't produce a pill
labeled "Crestron" and briefly looked like a bug; it wasn't, the pill was there under the label
Homie itself uses for that entity.

## Verification status

The build itself (helpers, automations, dashboard section) was tested by toggling the
`input_boolean` helpers directly rather than by playing real audio, since starting real playback on
a house speaker is an audible, physical side effect not taken casually. That confirmed the
`input_boolean` → `conditional` → `mini-media-player` layer end to end.

The remaining piece, whether a real MA state transition on `media_player.crestron` actually drives
its automation's `to`/`from: [playing, paused]` trigger the way the config assumes, was confirmed
the same day by a real Living Room playback session producing a real pill (see the naming note
above; that's what surfaced the label question in the first place). Not separately confirmed: the
full 10-second hold after playback stops, versus the automation's `delay` step being read and
trusted by inspection.
