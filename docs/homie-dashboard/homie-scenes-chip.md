# Scenes chip: stock mechanism, a service-domain mismatch, a real on/off toggle, and grouping

Why the lighting scenes pde defined in Home Assistant never appeared as a bottom-row chip in
Homie, the automation.trigger vs scene.turn_on mismatch that would have made a naive config entry
silently do nothing, why the first working version (fire-and-forget) wasn't the end of it, and
how the config was refactored to let one bubble activate and clear more than one scene at once,
since that grouping need was already visible with just two rooms and will only grow.

## Symptom

pde defined two scenes in Home Assistant (`scene.bedroom_evening`, `scene.bathroom_evening`)
and expected them to surface automatically as a bottom-row chip, based on the dashboard's docs
and screenshots. Nothing appeared. `docs/project-todo.md` item 6.

## Investigation

The Homie Dashboard fork
([`/Users/pde/src/github.com/pdehlke/homie-dashboard`](https://github.com/pdehlke/homie-dashboard))
already has a working Scenes-chip renderer in `dist/homie-dashboard.html`: a `controls[]` entry
with `isSceneChip: true` and `subGroups: [{ label, scenes: [{ entities, icon, label, color }] }]`
opens a popup of round icon bubbles grouped by room, each bubble firing its scene(s) on tap.
Traced to commit `5a39b12` ("Add files via upload") in the fork's history, the pristine
pre-customization upstream drop, so this is stock Homie Dashboard functionality, not something
pde built and forgot about. (The stock shape uses a single `entity` field; `entities`, plural, is
this fork's own generalization — see "Grouping multiple scenes into one bubble" below.)

It was simply never added to `dist/config.js`. There is no discovery mechanism from HA's
`scene.*` domain; every other chip (Lights, Climate, A/V, TV, Irrigation) is a hand-authored
entry in that same array, and Scenes is no different.

The chip row itself (`buildControls`) is fully generic: label, optional active-count badge,
`›` chevron whenever `subEntities` or `subGroups` is present. No per-domain icon lookup happens
at that level, so nothing there needed to change.

One real gap needed closing before the entry would work at all: Overview C's dynamic sidebar
(`_buildOv3SidebarControls` / `_sbIcon`) derives an icon from the represented entity's domain,
falling back to the generic "switch" icon when it can't. A scene chip has no top-level `entity`
and its `subGroups[].scenes[]` isn't the `subEntities` shape that lookup expects, so without an
explicit override it would silently render the switch icon. The icon map already had an unused
`scene` entry (a star) sitting there for exactly this case; it was just never wired to anything.
Fixed with `if (ctrl.isSceneChip) return icons.scene;`, added after `icons` is defined (a check
before it would hit its temporal-dead-zone).

## First pass: fire-and-forget, and why that wasn't enough

The stock popup's `triggerPopupScene()` fires the `automation.trigger` service, not
`scene.turn_on`. pde's scenes are native `scene.*` entities. Pointing a chip config straight
at `scene.bedroom_evening` would have called `automation.trigger` against an entity that isn't an
automation, which HA accepts as a no-op rather than an error — it would have looked configured
and done nothing when tapped, with no signal anything was wrong.

The first working version bridged this by wrapping the scene in a new HA automation
(`automation.bedroom_evening_lights`: empty trigger, single action `scene.turn_on` targeting
`scene.bedroom_evening`) and pointing the chip's `entity` at the automation instead of the scene.
Deployed and live-verified — tapping the bubble did activate the real scene, confirmed against
`last_triggered`, `last_updated`, and the real light states changing.

pde's review of that live version caught two things a one-way "fire the scene" button doesn't
have, that every other chip on the dashboard does: a visible on/off state (Lights shows "N on"
and glows; this showed nothing) and a way to reverse it (Lights toggles back off; this only ever
turned things on, PoC-only, not the final design). Both needed a real rewrite, not a patch,
because a fire-and-forget popup and a stateful toggle need different information: the toggle
needs to know what "on" means for a scene and what "off" should actually do to the same entities,
neither of which the automation wrapper was built to answer.

## Second pass: explicit on/off toggle

**What "on" means.** A scene has no state of its own — `scene.*`'s HA state is just a
last-activated timestamp, not an on/off signal. `sceneIsOn()` (module scope,
`homie-dashboard.html`) defines it instead as *any entity the scene controls is currently on*,
the same any-on-counts convention `refreshControls()`'s generic branch and `climateIsActive()`
already use for every other chip. The entity list itself is read live from the scene entity's own
`attributes.entity_id` (`sceneAffectedEntities()`) rather than duplicated in config, so it can't
drift from what the scene actually does in HA if pde edits the scene later.

**What tapping does.** `togglePopupScene()` replaced `triggerPopupScene()`. It checks
`sceneIsOn()` at the moment of the tap: off → `scene.turn_on` (activates the real snapshot); on →
`homeassistant.turn_off` targeting every entity `sceneAffectedEntities()` returns (domain-agnostic,
so a future scene mixing lights with covers or switches still works). This also **removed the
automation indirection entirely** — the config entry now points straight at the real scene.
`automation.bedroom_evening_lights` was no longer referenced by the dashboard after this; pde
deleted it.

**Where "on" is shown**, all reading the same `sceneIsOn()`:
- The popup bubble: `.popup-scene-icon.on` gets a `box-shadow` ring (`var(--ac-6)`/`var(--ac-4)`,
  the theme's own accent-alpha ramp) and the label brightens to `var(--accent-hi)`, the same
  visual language `.chip.on` already uses elsewhere rather than a new one invented for this.
  Computed once when the popup opens, and kept live afterward (below).
- The bottom chip: `refreshControls()` gained an `isSceneChip` branch (scene bubbles aren't
  `subEntities`, so the existing generic branch always saw zero of them) computing an active
  count and glow from `sceneIsOn()` across all scenes in the chip, same "N on" badge shape as
  Lights/Climate. `showCount: true` added to the config entry so the badge span exists at all.
- The Overview C sidebar dot: `_refreshOv3SidebarControls()` gained the same `isSceneChip`
  branch, for the same reason.

**Staying live while the popup is open.** `refreshAllUI()` only calls `refreshControls()` when no
popup is open (an existing, pre-scenes design choice — see `refreshOpenAcCards()` for the same
pattern already in place for AC cards), so the popup's own bubble needed a dedicated live-refresh
path or its ring would only ever reflect the instant it opened. `refreshOpenScenePopup()` mirrors
`refreshOpenAcCards()`'s approach exactly: walk every `isSceneChip` control's bubbles and patch
the DOM element if it exists, using DOM presence rather than a separately tracked "which popup is
open" index as the signal that a bubble is currently rendered. Called from `refreshAllUI`'s
popup-open branch alongside `refreshOpenAcCards()`. The tap itself also flips the bubble's own
class optimistically before the network round-trip, same instant-feedback pattern
`toggleControl()` uses for every other simple on/off chip; the live-refresh path then reconciles
it from real state on the next poll regardless of what triggered the change (this dashboard, a
different device, someone flipping a physical switch).

## Third pass: grouping multiple scenes into one bubble

pde asked for a Bathroom scene and a third, "Primary Suite Evening," that activates and clears
both Bedroom and Bathroom together, and to refactor the config shape to support that generally
rather than one-off, since more grouped scenes are coming as the house's scene library grows.

Every scene entry's single `entity: "scene.x"` field became `entities: ["scene.x", ...]`, always
an array — a single-scene bubble is just the one-element case, not a separate shape from a
grouped one. `sceneAffectedEntities()` now flat-maps across every scene entity in the array and
de-duplicates the result, since `light.hallway` genuinely is shared between the Bedroom and
Bathroom scenes here and shouldn't be turned off twice or double-counted. `sceneIsOn()` and
`togglePopupScene()` needed no new logic beyond that, because "any entity across N scenes is on"
and "turn off the union" are already what a single scene's version of those functions did with
N=1; generalizing the input was the whole change. The on-direction fires one `scene.turn_on` call
with all of the bubble's scene entity_ids as the target, not one call per scene — HA applies a
multi-entity target to every entity in the list itself, so there was nothing to loop over.

The popup's `onclick` attribute needed care serializing an array into an inline HTML attribute:
`JSON.stringify` produces double-quoted strings, which would collide with the onclick attribute's
own double-quote delimiter. Built as a single-quoted JS array literal by hand instead
(`sc.entities.map(e => \`'${e}'\`).join(",")`), safe here since HA entity_ids never contain a
quote or backslash.

Config now has three groups under the Scenes chip: **Bedroom** (Evening → `scene.bedroom_evening`
alone), **Bathroom** (Evening → `scene.bathroom_evening` alone), and **Primary Suite** (Evening →
both scenes together), following the existing group = room, bubble = scene-within-room convention
rather than inventing a new visual pattern for the grouped case. Bathroom's bubble icon is the
existing `ICONS.scenes.candle` markup (inlined, same as Bedroom's `nightlight`); Primary Suite
uses `ICONS.scenes.relax`, deliberately a third icon so the grouped bubble doesn't read as a
duplicate of either room's.

Release token bumped `20260812.1` -> `20260812.4` across all three rounds, matched in the
`homie-dash` Lovelace iframe URL each time.

## Options considered and rejected

For the automation.trigger/scene.turn_on mismatch:

- **Wrap the scene in an automation** (first pass, superseded). No fork code change needed, but
  turned out to be the wrong foundation once a real toggle was needed, since the automation only
  ever fires the scene forward — reversing it would have meant a *second* automation per scene, or
  bypassing the wrapper for the off path only, at which point the wrapper was buying nothing.
- **Patch the trigger function to branch on entity domain, calling `scene.turn_on` directly**
  (chosen, in its final form). No extra HA object per scene, one place (`sceneAffectedEntities`)
  to derive both "is it on" and "what does off mean" from the same source of truth.

For what a scene chip's on-state should mean, given HA scenes don't track one themselves:

- **Track a separate boolean per scene** (an `input_boolean`, or purely in-browser state).
  Rejected: would drift from reality the moment anything outside the dashboard changed the
  scene's lights (a physical switch, a different app, another automation), and needs an extra HA
  object or per-browser state that a second device wouldn't share.
- **Match the exact scene snapshot** (every controlled entity at precisely its scene-defined
  state/brightness) before showing "on". Rejected: too strict for a light that's drifted a few
  percent brightness from a dimmer, or that another automation nudged — would read "off" for a
  scene a person would call active.
- **Any entity the scene controls is on** (chosen). Matches the any-on-counts convention already
  used everywhere else on this dashboard (Lights, the generic branch of `refreshControls()`), and
  self-corrects: a deliberate off-tap always fully clears every controlled entity regardless of
  partial drift, and a deliberate on-tap always reapplies the exact snapshot from scratch, so
  there's no partial or ambiguous state a user can get stuck in from the dashboard's own controls.

For how to represent a bubble backed by more than one scene:

- **A separate `isGroup`/`groupEntities` field alongside the existing singular `entity`.** Two
  shapes to keep in sync in every function that reads a scene, and every future single-scene
  entry would still need to remember which field it uses. Rejected as needless special-casing.
- **Always an array, `entities`** (chosen). One shape everywhere; a single-scene bubble is the
  one-element case rather than a distinct kind of bubble. The only cost was a small,
  mechanical field rename across config and every function that reads it.

## Verification

- `node --test test/screen-a.test.cjs`: 76/76 (11 new across all three rounds: the Scenes entry
  shape including the three-group/grouped-entities layout, the sidebar icon override,
  `sceneAffectedEntities`/`sceneIsOn` against a fake state cache for both single and grouped
  scenes — including the de-duplicated-union case — `togglePopupScene`'s on- and off-direction
  service calls and optimistic class flip via a `vm` sandbox loader for both cases, and a
  discipline test confirming all four on-state read sites — the popup bubble, `refreshControls`,
  the Overview C sidebar, and `refreshOpenScenePopup` — call the one shared `sceneIsOn()` rather
  than reimplementing it).
- Deployed `dist/config.js` and `dist/homie-dashboard.html` to
  `/config/www/community/homie-dashboard/` for all three rounds, backing up the previous copies
  first each time (`homie-custom.js` untouched throughout). `homie-dashboard.html` confirmed
  byte-identical (SHA-256) to the fork's local `dist/` after each upload. `config.js` isn't
  checked by full-file hash since the live copy carries the real HA token the fork's copy
  deliberately doesn't; confirmed instead by checking the spliced token's length against the
  pre-deploy backup and grepping for the placeholder (absent) and the new content (present).
- **Deploy mistake caught and fixed live, first round only:** the token-splice step first
  extracted the token with `grep -P`, which doesn't exist in the HA host's BusyBox grep (no PCRE
  support) and failed silently, so the first `mv` into place left live `config.js` with an
  **empty** `HA_TOKEN` for roughly a minute. Caught immediately by checking the spliced token's
  length rather than trusting the "placeholder gone" check alone (an empty replacement also makes
  the placeholder gone). Fixed by re-extracting the token from the pre-deploy backup with a
  BusyBox-compatible `sed` expression and re-splicing. No token was ever printed to a transcript.
  Every later round's deploy used the corrected `sed`-only method from the start and needed no
  fix. Worth remembering for future deploys: this HA host's `grep` is BusyBox, not GNU, and
  doesn't support `-P`.
- `homie-dash`'s Lovelace iframe `?v=` bumped to `.2`, `.3`, then `.4` via `apply-card.py`
  (`HA_MATCH_TYPE=iframe`), prior config backed up automatically first each time.
- Live-verified via Playwright, authenticated as the Homie Dashboard account, final round: with
  all five Primary Suite lights confirmed off first, opened the popup and confirmed all three
  groups (Bedroom, Bathroom, Primary Suite) render with distinct icons and no on-ring. Tapped
  Primary Suite Evening: `light.bedroom_perimeter`, `light.hallway`, and `light.bath_perimeter`
  all turned on at each scene's own configured brightness in one round trip (confirmed via
  `/api/states`), and — without closing the popup — Bedroom, Bathroom, *and* Primary Suite's
  bubbles all showed the on-ring, since each independently reads "on" once its own affected
  entities include something lit. Tapped Primary Suite Evening again: all five lights (the
  full de-duplicated union of both scenes, `light.hallway` included only once despite being in
  both) turned off in one round trip, and all three rings cleared live. Earlier rounds already
  covered the single-scene bubble end-to-end (chip glow/count, popup ring, live refresh without
  reopening); this round confirmed the grouped case behaves identically, just over a larger,
  de-duplicated entity set.

## Fourth pass: emptied, mechanism kept (2026-09-03, issue #16)

Both scenes this chip pointed at, `scene.bedroom_evening` and `scene.bathroom_evening`, were
deleted 2026-09-02 along with the rest of the placeholder Crestron-PoC fleet, so every bubble
above went from a working toggle to a silent no-op: the popup rendered normally, the tap fired
`scene.turn_on` at a deleted entity, and Home Assistant answered `200` with an empty
changed-entity list. No console error either side, in the browser or in Homie's own code.

[Issue #16](https://github.com/pdehlke/homeassistant/issues/16) emptied `dist/config.js`'s Scenes
chip to `subGroups: []`, keeping the chip, `isSceneChip`, and `showCount`, and left `openPopup`'s
scene branch to render an explicit "No scenes configured" message
(`.popup-scene-empty`, styled like `.alert-popup-empty`) rather than a silently blank popup.
Everything documented above this section — `sceneIsOn`, `sceneAffectedEntities`,
`togglePopupScene`, `refreshOpenScenePopup`, the grouping design, all of it — is unchanged and is
exactly what the next phase (a real scene catalogue on top of the Crestron-backed lights) refills.
Full record of the emptying itself: the
[2026-09-03 checkpoint in homie-dashboard-install-plan.md](homie-dashboard-install-plan.md#checkpoint-2026-09-03-the-scenes-chip-goes-quiet-issue-16).

**The three bubble icons, preserved here since config no longer carries them:**

Bedroom (crescent moon):

```html
<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.9)" stroke-width="1.5" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
```

Bathroom (bath):

```html
<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.9)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="12" width="6" height="9" rx="1"/><path d="M12 12V9"/><path d="M12 9 C13.5 7 13.5 5 12 3.5 C10.5 5 10.5 7 12 9Z" fill="rgba(255,200,80,0.85)" stroke="rgba(255,160,40,0.9)" stroke-width="1"/><line x1="9" y1="15" x2="9" y2="17" stroke="rgba(255,255,255,0.35)" stroke-width="1"/></svg>
```

Primary Suite (dresser, deliberately a third icon rather than a repeat of either room's, per the
third pass above):

```html
<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.9)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="4" r="1.5"/><path d="M9 9 Q8 13 10 15 L8 21"/><path d="M9 9 L15 9 Q17 9 17 12 L17 15"/><path d="M10 15 L17 15 L19 21"/><path d="M6 21 L20 21"/></svg>
```

All three used `color: "var(--accent)"` as the bubble background. Every one of them is verbatim
from the emptied config, byte for byte, so the next phase can paste rather than re-author.

## Fifth pass: refilled with "Dinner", a script-backed scene (2026-09-03)

pde asked for a real scene: turn off the TV if it's on, turn on all the Kitchen and Dining Room
lights plus Living Room Pathway, then start "Jazz: Hiromi" through the Music chip's own sequence.

**Why this can't be a `scene.*` entity.** A native HA scene is a pure entity-state snapshot — it
has no conditional (there's no way to express "only if the TV is on") and no way to call an
arbitrary service like `music_assistant.play_media` with a specific station. Every prior scene on
this chip (Bedroom/Bathroom/Primary Suite Evening) fit the snapshot model exactly; Dinner doesn't.
It's backed instead by a Home Assistant **script**, `script.scene_dinner`, created via
`POST /api/config/script/config/scene_dinner` (the same "config editor" REST family already used
for automations and scenes on this instance):

```yaml
alias: Dinner
sequence:
  - if:
      - condition: state
        entity_id: remote.harmony_hub
        state: "on"
    then:
      - action: remote.turn_off
        target: { entity_id: remote.harmony_hub }
  - action: light.turn_on
    target:
      entity_id:
        - light.kitchen_cabinet
        - light.kitchen_island
        - light.kitchen_pathway
        - light.kitchen_perimeter
        - light.kitchen_range
        - light.dining_room_north
        - light.dining_room_powder
        - light.dining_room_south
        - light.dining_room_table
        - light.living_room_pathway
  - action: remote.turn_on
    target: { entity_id: remote.harmony_hub }
    data: { activity: Airplay }
  - if:
      - condition: not
        conditions:
          - condition: state
            entity_id: media_player.crestron
            state: playing
    then:
      - action: media_player.volume_set
        target: { entity_id: media_player.crestron }
        data: { volume_level: 0.4 }
  - action: media_player.shuffle_set
    target: { entity_id: media_player.crestron }
    data: { shuffle: false }
  - action: music_assistant.play_media
    target: { entity_id: media_player.crestron }
    data: { media_id: library://radio/1, media_type: radio }
mode: single
```

The TV-off step and the Jazz: Hiromi sequence are copied, not reinvented, from the dashboard's own
live code, traced before writing a line of the script: the TV chip's "All Off" button
(`tvControlAction('PowerOff')`) is exactly one call, `remote.turn_off` on `remote.harmony_hub`,
with no built-in "is it on" guard of its own — the script supplies that guard itself, since a
conditional is exactly what a scene couldn't do. The Music chip's "Jazz: Hiromi" preset
(`togglePopupMusic`) is `remote.turn_on` (Harmony, activity `Airplay`) → conditionally
`media_player.volume_set` → `media_player.shuffle_set` → `music_assistant.play_media` with
`media_id: "library://radio/1"`. No artificial delay was added between the Harmony power-off and
the later Harmony Airplay-activate; the dashboard's own code already accepts an equivalent race
elsewhere (it doesn't wait for Harmony's activity switch before calling `play_media` either — see
[music-chip.md](../../../homie-dashboard/.claude/skills/verify-homie-dashboard/features/music-chip.md)
in the fork), so this follows the same convention rather than inventing new plumbing. If real usage
ever shows the physical hub needs a beat between the two Harmony calls, add a short `delay:` step
then.

**The light list**, cross-checked against the load-room worksheet, `const.py`, the live
`config.js`, and a live `/api/states` read (all confirmed `off` before every test run):

| Room | Entities |
|---|---|
| Kitchen | `light.kitchen_cabinet`, `light.kitchen_island`, `light.kitchen_pathway`, `light.kitchen_perimeter`, `light.kitchen_range` |
| Dining Room | `light.dining_room_north`, `light.dining_room_powder`, `light.dining_room_south`, `light.dining_room_table` |
| Living Room | `light.living_room_pathway` |

Worth recording so a future pass doesn't re-derive it wrong: "Powder" physically wires through the
Kitchen zone page's panel but is a Dining Room light, and "Perimeter" wires through the Dining zone
page but is a Kitchen light. The Crestron load-room worksheet's Room column is authoritative, not
the zone page a join happens to be wired through — the table above already reflects that.

**The generalization.** `sceneAffectedEntities()` and `togglePopupScene()` were built entirely
around `scene.*` snapshot semantics. Two small, additive changes made them work for a script too,
without touching `sceneIsOn()` or any of its four callers:

- `sceneAffectedEntities()` now treats any entity whose domain isn't `scene` as self-affecting
  (returns it directly) instead of trying to expand it via `attributes.entity_id`, which a
  non-scene entity doesn't have. This alone makes a plain `light.*` list work as a bubble's
  on/off-defining entities.
- `togglePopupScene()` gained an optional third parameter, `activate`, defaulting to `entities`.
  The on-direction now calls `homeassistant.turn_on` — HA's generic dispatcher, confirmed live on
  this instance to forward correctly to `script.turn_on` for a script entity, the same way it
  already forwards to `scene.turn_on` for a scene entity — targeting `activate` when given,
  `entities` otherwise. Every scene bubble that predates this pass doesn't set `activate`, so it
  turns on exactly what it always did.

Dinner's bubble: `entities` is the ten lights above (what the glow follows, what a tap-while-on
turns off — `homeassistant.turn_off`, unchanged); `activate` is `"script.scene_dinner"` (what a
tap-while-off actually runs). **Tapping Dinner off only reverses the lighting.** It does not stop
the music or touch `remote.harmony_hub` — a deliberate choice, since the script's on-effect and the
bubble's off-effect are different actions by design here, not a mirror pair the way a snapshot
scene's on/off is.

Icon: `ICONS.scenes.candle` (already existed, unused since the Bathroom bubble that used it was
deleted) reused verbatim as a self-contained inline SVG literal in `config.js`, matching every
other `subGroups.scenes` icon in that file rather than referencing the HTML's global `ICONS`
object across files.

## Options considered and rejected (fifth pass)

For how the bubble should decide what counts as "on":

- **Track the script's own transient running-state** (`sceneIsOn` reading `script.scene_dinner`
  itself). Rejected: a script that finishes in a few seconds would glow almost never, and a
  tap-while-on would mean "cancel the script," not "undo what it did" — not what pde asked for.
- **Track the lights the script turns on** (chosen). Consistent with every prior scene's
  any-on-counts convention, and a tap-while-on reverses the actually-visible effect (the lighting)
  rather than a script's internal execution state nobody but this dashboard would otherwise see.

For how the on-direction should target something other than `entities` itself:

- **A second, parallel scene-config shape just for script-backed bubbles.** Rejected: two shapes to
  keep in sync in every function that reads a scene bubble, the same objection this document
  already raised (and resolved the same way) for the grouped-scenes question in the third pass.
- **An optional `activate` field, defaulting to `entities`** (chosen). One shape, additive, zero
  behavior change for every bubble that doesn't need it.

## Verification (fifth pass)

- `script.scene_dinner` created and `check_config` confirmed valid. Run cold (Harmony and all ten
  lights off): `remote.harmony_hub` ended on Airplay, all ten lights on, `media_player.crestron`
  playing `library://radio/1` — confirmed via `/api/states`, and via
  `trace/get` (`scripts/haws.py` in the `pdehlke/homeassistant` skill) that the TV-off `if`
  evaluated `false` and correctly skipped `remote.turn_off`, not just that the end state happened
  to look right either way. Re-run with Harmony already on a different activity ("Watch a Movie"):
  the trace confirmed the same `if` evaluated `true` and `remote.turn_off` fired this time, before
  the script moved on to lights and Airplay. Restored to the starting all-off state after each run.
- Confirmed live, before touching any dashboard JS, that `homeassistant.turn_on` targeting
  `script.scene_dinner` actually runs the script (not just a documented HA behavior taken on
  faith), and that `homeassistant.turn_off` targeting the ten lights turns them off while leaving
  Harmony/the music untouched — exactly the mechanism the generalized `togglePopupScene()` needed.
- `node --test test/screen-a.test.cjs`: 129/129 (5 new: a non-scene entity treated as
  self-affecting, `sceneIsOn` over a plain light list, `togglePopupScene` running `activate` on the
  on-tap and only the entities on the off-tap, the `activate`-omitted fallback, and the updated
  config-shape assertion for the new Dinner bubble). The existing scene-domain tests needed only
  their on-direction assertion updated from `scene`/`turn_on` to `homeassistant`/`turn_on` — no
  scene-domain behavior actually changed, since `homeassistant.turn_on` forwards to `scene.turn_on`
  for a `scene.*` target.
- Deployed `dist/config.js` and `dist/homie-dashboard.html` to
  `/config/www/community/homie-dashboard/`, prior copies backed up with a timestamp first.
  `homie-dashboard.html` confirmed byte-identical (MD5) to the fork's local `dist/` after upload.
  `config.js` verified by diffing the newly spliced file against the pre-deploy backup with the
  token line redacted — only the intended Scenes-block change showed. `homie-dash`'s Lovelace
  iframe `?v=` bumped `20260903.2` → `20260903.3` via a whole-config WebSocket save (this dashboard
  is an iframe strategy, not a card, so `apply-card.py` doesn't apply to it).
- House left with all ten lights, Harmony, and the music off/idle after every live test, matching
  the state found. Visual, on-device confirmation of the popup and the live tap-through is pde's
  own next step, per this project's usual review convention, rather than a Playwright pass — no
  local `playwright-cli` install existed at the time and pde chose to check it live himself instead
  of having one installed for this change.
