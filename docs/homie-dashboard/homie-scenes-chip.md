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

## Sixth pass: "Visitors", same mechanism over every light in the house (2026-09-03)

pde asked for a second scene, same actions as Dinner, except it turns on every light in the house
instead of just Kitchen/Dining/Pathway — explicitly including the courtyard and outside fixtures.

**Same script shape, bigger target list.** `script.scene_visitors` is `script.scene_dinner`'s exact
sequence — the same TV-off-if-on conditional, the same Jazz: Hiromi sequence through Harmony — with
the `light.turn_on` step's target list swapped for all 30 of the house's `light.*` entities instead
of ten. The list was pulled directly from a live `GET /api/states` read, not typed from the room
worksheet by hand the way Dinner's ten were — with 30 entries across every room, transcription risk
outweighed the worksheet's value, and reading it live is also the only way to be sure the count
actually matches "every light," since the worksheet documents intent while `/api/states` documents
what Home Assistant actually has. That count came back exactly 30, matching the project checkpoint
that Home Assistant now drives all thirty of the house's lighting loads:

```
light.courtyard_patio_north      light.living_room_ambient
light.courtyard_patio_south      light.living_room_east_seating
light.dining_room_north          light.living_room_pathway
light.dining_room_powder         light.living_room_perimeter
light.dining_room_south          light.living_room_west_seating
light.dining_room_table          light.office_north_sink
light.entry_center               light.office_pool_bath
light.entry_door                 light.outdoor_kitchen
light.entry_perimeter            light.outside_garage_sconces
light.guest_suite_east_hall      light.outside_home_perimeter
light.kitchen_cabinet            light.primary_suite_bath_diagonal
light.kitchen_island             light.primary_suite_bath_perimeter
light.kitchen_pathway            light.primary_suite_bed_diagonal
light.kitchen_perimeter          light.primary_suite_bed_perimeter
light.kitchen_range              light.primary_suite_hallway
```

**No dashboard code changed.** The fifth pass's generalization — `sceneAffectedEntities()`
treating any non-`scene.*` entity as self-affecting, `togglePopupScene()`'s optional `activate`
parameter — was already entity-count-agnostic, and every `isSceneChip` render/refresh site
(`openPopup`, `refreshOpenScenePopup`, the chip glow in `refreshControls`, the Overview C sidebar
glow) already iterates `subGroups[].scenes[]` with `.flatMap`/`.forEach` rather than assuming
exactly one bubble. Adding Visitors as a second bubble in the same "Scenes" `subGroups` entry was a
config-only change: a new `{ entities, activate, icon, label, color }` object, same shape as
Dinner's, appended to the same `scenes` array.

Icon: none of the chip's existing unused SVGs (`relax`, `romantic`, `movie`, `fireplace`,
`nightlight`, or the three older hand-authored ones — crescent moon, bath, dresser — mentioned in
the `config.js` comment) read as "guests," so Visitors gets a new hand-authored two-person glyph in
the same stroke style (18×18, `rgba(255,255,255,0.9)` stroke, 1.5 weight, round caps) as the rest of
`ICONS.scenes`, inlined directly in `config.js` rather than added to that shared object — matching
how Dinner's icon is a self-contained literal in `config.js`, not a cross-file reference.

## Verification (sixth pass)

- `script.scene_visitors` created via `POST /api/config/script/config/scene_visitors` and
  `check_config` confirmed valid.
- Run live with Harmony already on a different activity (found already on Airplay from the fifth
  pass's own testing — a real "already on" case, not a contrived one): the service call's own
  response showed `remote.harmony_hub` transition `on/Airplay` → `off/PowerOff` → back to
  `on/Airplay`, confirming the TV-off `if` branch actually fired mid-sequence rather than the
  before/after states merely converging. All 30 lights confirmed `on` via `/api/states` afterward;
  `media_player.crestron` confirmed playing `library://radio/1` ("Hiromi + more"). `haws.py`'s
  formal `trace/list`/`trace/get` confirmation wasn't run a second time for this script — the
  underlying conditional logic is identical to Dinner's, already trace-confirmed in both directions
  in the fifth pass, and the intermediate state transition visible in this run's own response is
  the same category of evidence trace would have added (which branch fired, not just the end
  state). Restored: music stopped, all 30 lights turned back off; Harmony left on Airplay, matching
  the state found before this pass's testing began (it was not off beforehand, unlike the fifth
  pass's from-scratch runs).
- `node --test test/screen-a.test.cjs`: 129/129 unchanged in count — no new function-level tests
  needed, since Visitors exercises the same generalized mechanism the fifth pass's tests already
  cover (a non-scene entity list, an `activate` target). The config-shape mapping test was extended
  in place to assert both bubbles: Dinner's existing ten-entity list, and Visitors' 30-entity list,
  including that all 30 start with `light.`, that there are no duplicates, and that all four
  courtyard/outside entities are present.
- Deployed `dist/config.js` and `dist/homie-dashboard.html` to
  `/config/www/community/homie-dashboard/`, prior copies backed up with a timestamp first.
  `homie-dashboard.html` confirmed byte-identical (MD5) to the fork's local `dist/` after upload.
  `config.js` verified by diffing the newly spliced file against the pre-deploy backup with the
  token line redacted — only the intended Visitors-block addition showed. `homie-dash`'s Lovelace
  iframe `?v=` bumped `20260903.3` → `20260903.4` via a whole-config WebSocket save.
- This pass needed `haws.py` for the SSH add-on start/stop and the Lovelace save, and `haws.py`
  needs `aiohttp`, which this machine didn't have installed. pde approved a one-time `pip install`;
  it went into an isolated venv in the session scratch directory rather than the system
  interpreter, since Homebrew's Python refuses an unscoped `pip install` (PEP 668) and a scratch
  venv avoids the `--break-system-packages` trade-off entirely.
- House left with all 30 lights off and the music stopped after the live test; Harmony left on
  Airplay, matching what was found. Visual, on-device confirmation of the popup and the live
  tap-through is pde's own next step, same convention as the fifth pass.

## Seventh pass: Dinner's ten lights collapsed into one HA group (2026-09-04)

pde created a light group in HA, `light.dinner_lights`, wrapping the fixtures Dinner's
`light.turn_on` step and bubble `entities` had spelled out individually, plus a couple more
(Living Room Cabinet, Reading Nook, Globe Lamp, Kitchen Counter Lamp — the four Zigbee lights
added to the Lights chip the same day, config-only, not covered here). He asked for the chip and
the script to target the group instead of the ten lights directly, so the light list can be
changed later by editing the group in HA rather than editing the dashboard config or the script.

Two edits, both mechanical given the fifth pass's generalization already treats any non-`scene.*`
entity as self-affecting: `script.scene_dinner`'s `light.turn_on` step's target became
`light.dinner_lights` instead of the ten-entity list, and the bubble's `entities` in `config.js`
became `["light.dinner_lights"]`. `sceneIsOn()` now reads the group's own aggregate on/off state
instead of checking ten lights individually, and a tap-while-on calls `homeassistant.turn_off` on
the group, which HA forwards to every member — both directions confirmed live (script trace showed
the group fan out to `crestron_cip.turn_on` for each member; see the eighth pass below for a
fuller live audit of the off-direction and the group's own state-aggregation behavior, done as
part of diagnosing a different report). The Lovelace iframe's own `?v=` was bumped `20260903.4` →
`20260903.5` as usual, but — not caught until the ninth pass below — the *nested*
`HOMIE_ASSET_VERSION` token inside `homie-dashboard.html`, which cache-busts `config.js` and
`homie-custom.js` independently of the iframe's own URL, was not bumped alongside it. It should
have been; see the ninth pass for what that omission actually did. No test changes beyond updating
the Dinner entities assertion to the one-element array — the generalization under test didn't
change, only the input.

## Eighth pass: a real on/off indicator, and a light-group gotcha found while building it (2026-09-04)

pde reported the Scenes chip felt broken: tapping a scene "on" never seemed to show as "off"
again, and asked for a visible on/off state matching Lights/Music/TV, plus the ability to turn a
scene off by tapping it.

**The toggle-off mechanism already existed and already worked.** Before changing any code, the
existing `togglePopupScene()`/`sceneIsOn()` pair (second pass, above) was re-verified live against
the real `light.dinner_lights` group: calling `homeassistant.turn_off` against it (the exact call a
tap-while-on makes) turned off all 13 members and the group itself reported `off` within a few
seconds. This wasn't a logic bug.

**The actual gap was visual.** Every scene bubble's icon circle was always rendered at its
configured `sc.color` (an inline `style="background:..."`, same accent color for every bubble on
this chip), on or off, with the only on-signal a 2px box-shadow ring in the same accent hue family
— a subtle highlight on a circle that was already that color, easy to miss at a glance and easy to
mistake for "stuck on" once tapped. Lights' popup rows, by contrast, sit at a muted
`rgba(255,255,255,0.05)` background when off and get a visibly tinted background plus a
slide-toggle knob when on — a much stronger contrast pde's ask referenced by name.

pde chose, from three options (a starker ring at the same always-colored resting look; matching
Lights exactly with rows and a sliding toggle switch, replacing the icon-bubble grid; or dimming
the resting circle and only showing its real color once on) the third: **dim grey when off, full
color plus the existing ring when on**. Implemented as a CSS custom property,
`--scene-color`, set inline per bubble (`style="--scene-color:${sc.color}"`) in place of the old
`style="background:${sc.color}"`; `.popup-scene-icon`'s base rule now renders a muted
`rgba(255,255,255,0.1)` circle at `opacity: 0.55`, and `.popup-scene-icon.on` swaps the background
to `var(--scene-color, var(--accent))` at full opacity, on top of the pre-existing ring. The
fallback to `var(--accent)` matters because the Music chip's own popup station bubbles
(`togglePopupMusic`'s render site) share this exact same `.popup-scene-icon`/`.popup-scene-bubble`
markup and CSS — they never set `--scene-color` at all (every Station bubble plays through the one
fixed `media_player.crestron`, so there's only ever one color to show), and previously carried the
identical `style="background:var(--accent)"` inline override this pass removed. That inline style
would otherwise have out-specificity'd the new CSS entirely, leaving Music's bubbles always
full-color regardless of on/off — removing it instead of leaving it was a deliberate choice, not an
oversight: it means Music's own popup bubbles get the same dim-off/bright-on legibility fix as a
side effect of fixing the class they already shared with Scenes, rather than the two chips visibly
diverging over an implementation detail neither config author would expect to matter.
`test/screen-a.test.cjs` had no assertions on the literal inline-style string for either chip's
bubbles, so no test changes were needed; 129/129 unchanged.

**A real bug turned up during the live re-verification, in the `light.dinner_lights` group itself,
not the dashboard.** Turning the group off and back on via the exact service calls
`togglePopupScene()` makes showed the group's own aggregate `state` does not follow the "any member
on" convention `sceneIsOn()` assumes (and that every other chip on this dashboard uses): with 11 of
its 13 members confirmed `on` and only two (`light.kitchen_pathway`, `light.kitchen_perimeter`)
still `off`, `light.dinner_lights` itself kept reporting `off`, and only flipped to `on` the instant
the last two members were turned on directly. That is the Group helper's "all entities must be on
for the group to be considered on" option, which HA's Light Group helper supports as a per-group
toggle at creation and which this group apparently has enabled. It was not investigated further
this pass, since it wasn't this pass's ask and fixing it means editing settings on pde's own HA
object rather than dashboard code; flagged to pde directly rather than silently flipped, along with
the fact that two more group helpers already exist alongside `light.dinner_lights` — `Evening
Lights` (9 members) and `Dinner Only` (4 members) — of unclear relationship to the one the chip
actually points at. Whatever "all entities on" is set to on this group directly determines how
reliable Dinner's on/off indicator is: with two of thirteen loads (or any future load added to the
group) occasionally slow or unresponsive over CIP, "all on" means the indicator may rarely or never
show "on" at all, which would look exactly like the "stuck" symptom pde originally reported, just
in the opposite direction from what the visual-contrast fix above addresses.

Deployed `dist/homie-dashboard.html` only (`config.js` untouched this pass) to
`/config/www/community/homie-dashboard/`, prior copy backed up with a timestamp first, diffed
against the backup with only the intended CSS/render-site changes showing. `homie-dash`'s Lovelace
iframe `?v=` bumped `20260903.6` → `20260903.7` via a whole-config WebSocket save. No `playwright-cli`
install exists locally for this change either; pde is checking the new dim/bright contrast and the
tap-to-toggle live himself, same convention as every prior pass on this chip.

### Options considered and rejected (eighth pass)

For how a bubble should look off versus on:

- **Bigger ring, same always-colored resting look.** Smallest possible change, but the underlying
  problem — an already-colored circle with only a thin same-hue ring to distinguish state — doesn't
  go away just because the ring is thicker. Rejected as not actually solving what was reported.
- **Match Lights exactly: replace the icon-bubble grid with rows and a sliding toggle switch.**
  The most literal reading of "like Lights," but scenes would lose the individual icon/color
  identity every bubble on this chip (and Music's) has always had, and the popup would get visibly
  denser for what is still just a handful of bubbles. Rejected as more change than the actual
  complaint (indistinguishable on/off) needed.
- **Dim grey off, full color plus ring on** (chosen). Keeps the existing round-icon-grid layout and
  every bubble's individual identity, while making on/off as unmistakable at a glance as Lights'
  rows are, at the cost of one CSS custom property and a couple of rule changes.

## Ninth pass: a browser-caching bug hiding behind the seventh pass, and two real bugs (2026-09-04)

pde tried the new dim/bright contrast live and reported three things wrong: tapping Dinner on lit
*both* the Dinner and Visitors bubbles and the chip read "2 on"; tapping Dinner off only turned off
the Kitchen and Dining lights, leaving Living Room Perimeter and all four Zigbee lights on (and
Visitors still lit); and tapping Visitors off turned off Perimeter but not the Zigbee lights either.
Music kept playing through all of it. Three separate causes, found by re-running the exact service
calls the taps make and watching real entity states rather than guessing from the symptoms alone.

**The real bug: a browser-caching hole that made the seventh pass's own fix invisible, sitting
behind whatever cached copy of `config.js` pde's browser was already holding.** (The eighth pass's
CSS lives entirely in `homie-dashboard.html`, which the Lovelace iframe's `?v=` already cache-busts
correctly on its own — that fix did take effect. It's specifically `config.js`, loaded as a
separate resource, that this bug affects.)
`homie-dashboard.html` loads `config.js` and `homie-custom.js` via
`` document.write(`<script src="config.js?v=${HOMIE_ASSET_VERSION}">`) ``, a *second*,
independent cache-busting token from the Lovelace iframe's own `?v=` (which only forces a fresh
fetch of `homie-dashboard.html` itself). HA's static file server sends
`Cache-Control: public, max-age=2678400` — 31 days — on everything under `/local/`, confirmed live
via `curl -I`. `HOMIE_ASSET_VERSION` was last actually bumped in the sixth pass, 2026-09-03, to
`20260903.4`, and sat at that exact value through the seventh pass (Dinner's group), the same-day
Zigbee-lights addition, and the eighth pass (this chip's CSS fix) — three consecutive
`config.js`/`homie-dashboard.html` deploys where only the outer Lovelace iframe `?v=` was bumped,
confirmed by grepping the live-served file for the literal string. Any browser that had `config.js`
cached from on or before 2026-09-03 had no reason to ever refetch it — the URL never changed — so it
kept serving that exact stale response for up to 31 days, regardless of how many times the outer
page changed underneath it. That is exactly why Dinner's off-tap only affected Kitchen and Dining:
the *script* (`script.scene_dinner`, server-side, no browser cache involved) correctly used the new
`light.dinner_lights` group, but the *bubble's `entities` field*, read from a stale cached
`config.js`, was still the pre-group ten-light array — kitchen(5) + dining(4, including
`light.dining_room_powder`) + `light.living_room_pathway` — so the on-tap and off-tap of the same
bubble were silently acting on two different light lists. Fixed by giving `HOMIE_ASSET_VERSION` a
real bump (`20260903.4` → `20260904.1`, matched to the Lovelace iframe's own new value rather than
kept as a separate number) and adding a comment at its declaration spelling out why the two tokens
must move together on every `config.js`/`homie-custom.js` deploy from now on. **pde needs to fully
reload the dashboard once** (not just tap around) for this to take effect — a stale tab that never
re-fetches `homie-dashboard.html` won't pick up a new `?v=` either.

**Confirmed independently, not a caching artifact: Visitors' entities list never picked up the
four Zigbee lights.** Both `config.js`'s Visitors bubble and `script.scene_visitors`'s own
`light.turn_on` step were the original 30-entity list from the sixth pass, predating the Zigbee
lights entirely — a real gap, not something the cache fix touches. Since Visitors' own definition
is "every light in the house," both were updated: `config.js` now lists all 34, and
`script.scene_visitors` was updated the same way via
`POST /api/config/script/config/scene_visitors` (so a tap-while-off actually turns the new lights
on too, not just the on/off glow and off-tap). Live-tested end to end: running the script turned on
all four Zigbee lights alongside the rest, and calling `homeassistant.turn_off` on the live 34-entity
list turned all of them, Zigbee included, back off.

**Flagged, not fixed: Dinner and Visitors will keep lighting up together.** Dinner's group members
are a subset of "every light in the house," so `sceneIsOn()`'s any-on-counts convention means
turning on Dinner will always also make Visitors read "on" — and after today's fix, more so, since
Visitors' list is now four entries longer and still fully overlaps Dinner's. This isn't a bug in
the mechanism so much as a consequence of what the two scenes are defined to mean: Visitors as
written asks "is any light in the house on," which is true almost any time the house is in normal
use, not just when someone tapped Visitors specifically. Nothing changed here pending pde's read on
what he actually wants (see the checkpoint in `homie-dashboard-install-plan.md` for the options this
raises: requiring literally all 34 lights on before Visitors reads "on," some other definition, or
leaving it as designed and accepting the overlap).

**Not addressed, by original design, and now worth revisiting given how it read in practice: a
scene's off-tap only undoes lighting, never the music/Harmony a script also started.** This was a
deliberate choice in the fifth pass (see above) — "tapping Dinner off only reverses the lighting" —
but pde's report ("the music continues to play... after I click off either or both of the scenes")
reads as this not matching what he expects from an off-tap now that he's using it for real. Flagged
alongside the Visitors-overlap question above rather than changed unilaterally, since "should off
mean undo everything" is pde's call, not a bug to silently patch.

Deployed `dist/config.js` and `dist/homie-dashboard.html` (both changed this round) to
`/config/www/community/homie-dashboard/`, prior copies backed up with a timestamp, `config.js`'s
token re-spliced and verified with a redacted diff against the backup (only the intended Visitors
entities/comment changes showed), `homie-dashboard.html` diffed the same way (only the
`HOMIE_ASSET_VERSION` change showed). `homie-dash`'s Lovelace iframe `?v=` bumped to `20260904.1`
— matching `HOMIE_ASSET_VERSION` exactly, the new convention this pass adopted.
`test/screen-a.test.cjs` updated for the 30→34 Visitors count and the four new required entities,
plus the hardcoded `HOMIE_ASSET_VERSION` literal the test asserts against; 129/129.

## Tenth pass: off is a full undo, and Visitors' indicator finally means what it says (2026-09-04)

Two explicit, unambiguous decisions from pde on the ninth pass's two open questions: off should
definitely undo everything a scene started, including the music; and Visitors' indicator reading
"any light in the house is on" as a trigger is "completely wrong" — it's specifically supposed to
mean every single light is on.

**Off now stops the music too.** `togglePopupScene()`'s on->off branch, after turning off the
lights, now also calls `stopPopupMusic()` — the exact same `media_player.media_stop` +
`remote.turn_off` (Harmony) sequence the Music chip's own off action and "All Off" row already use
— targeting whichever entity the config's `isMusicChip` control is set to look up
(`(CONFIG.controls || []).find(c => c.isMusicChip)`), rather than a second hardcoded
`media_player.crestron` literal alongside the one already in `script.scene_dinner`/
`script.scene_visitors`. Unconditional: every scene bubble's off-tap runs it, on the theory that
stopping an already-idle player and turning off an already-off Harmony hub are harmless no-ops, not
worth a per-bubble opt-out for a case (a hypothetical scene that never touches music) that doesn't
exist yet on this chip.

**Visitors' on-indicator now requires every one of its 34 lights on, not any one of them.**
`sceneIsOn()` gained a second parameter, `allMustBeOn`, switching its internal `.some()` to
`.every()` over the same `sceneAffectedEntities()` list every other call already uses — an
additive, default-off flag, so every bubble that doesn't pass it (Dinner, and any future one)
keeps the any-on behavior that's still the right reading for a scene that only claims a handful of
lights rather than the whole house. Threaded through all five places that needed it: `sceneIsOn()`
itself, its four read sites (the popup bubble, `refreshControls`'s chip glow/count, the Overview C
sidebar, `refreshOpenScenePopup`), and `togglePopupScene()`'s own direction-deciding `wasOn` check
— all five read from the bubble's own `sc.allMustBeOn`/parameter rather than a second copy of the
flag. `config.js`'s Visitors entry gained `allMustBeOn: true`; Dinner's entry needed no change.
One real behavioral consequence worth knowing, not just an implementation detail: with
`allMustBeOn`, a tap while even one of the 34 lights is off (a bulb that's out, one of the
occasionally-flaky Crestron loads from the ninth pass's own findings, someone having switched a
single light off by hand) reads as "off" and **re-activates** Visitors rather than clearing it —
the same direction a fresh off-tap would take on a scene that's genuinely all the way off. That's
inherent to what "requires literally everything on" has to mean for deciding a tap's direction, not
a bug in the implementation of the ask.

Did not add a music/Harmony requirement to Visitors' `allMustBeOn` check itself — pde's own phrasing
was that the *light* indicator's any-on trigger was "completely wrong," and the fix addresses
exactly that. If Visitors' glow should also require the music mid-playback before showing "on,"
that's a further, separate ask, not assumed here.

### Options considered and rejected (tenth pass)

For how off should reach the music, given a scene bubble has no `media_player` field of its own:

- **Hardcode `media_player.crestron` a third time**, alongside the literal already duplicated in
  both `script.scene_dinner` and `script.scene_visitors`. Works today (there's only one media
  player this whole dashboard ever controls) but is one more place a future rename or a second
  media player would need to be remembered.
- **Look up the Music chip's own configured `entity`** (chosen). One source of truth
  (`config.js`'s Music chip entry), already the pattern `syncDynamicPlaylistsFromHA()` uses to find
  the same chip for an unrelated reason — reusing an established lookup rather than inventing a
  second one.

For whether every scene bubble's off-tap should stop music unconditionally, versus opting in:

- **A per-bubble `stopsMusic` flag**, defaulting to false. More precise if a lighting-only scene
  ever gets added to this chip, but that scene doesn't exist yet, and both real bubbles today
  (Dinner, Visitors) do start music via their scripts. Rejected as speculative config surface for a
  case with no current instance — the same objection this document has already raised for the
  grouped-scenes and script-vs-snapshot questions above.
- **Unconditional** (chosen). Stopping an idle `media_player` and turning off an already-off
  Harmony hub are no-ops, not errors, so there is no real cost to a bubble that never touches music
  running this anyway. Simplest correct behavior for what exists today; add the flag later if a
  scene that must *not* touch music actually shows up.

For how strict Visitors' on-indicator should be:

- **Keep any-on** (rejected, this is the bug pde reported). Reads "on" the instant a single light
  is on anywhere in the house, for any reason — Dinner, a manual switch, another scene entirely —
  which isn't "Visitors is active" by any reading pde was willing to accept.
- **All-on, `allMustBeOn`** (chosen). Matches "every single light in the house is on" literally.
  The tradeoff pde is accepting knowingly: with 34 individually-controlled entities (a few already
  shown in the ninth pass to be occasionally slow or unresponsive over CIP), the indicator will be
  a stricter, rarer "on" than any other chip's — a feature here, not the accidental side effect it
  would be if any-on had just been left in place with a bigger list.

### Verification (tenth pass)

- `node --test test/screen-a.test.cjs`: 132/132 (3 new: `allMustBeOn` requiring every affected
  entity — including the empty-list edge case, where `.every()` on nothing is vacuously true and
  needs an explicit guard to still read "off" — and `togglePopupScene` picking the activate branch
  instead of the clear branch when `allMustBeOn` reads a partially-lit bubble as off). Every
  existing on->off test (`scene.bedroom_evening`, the grouped Primary-Suite-shaped case, Dinner's
  `activate` case) updated to expect the two additional full-undo calls after the lights, via one
  shared assertion helper rather than repeating the same two lines three times. The `loadSceneToggle`
  test harness gained a minimal `CONFIG` stub (one `isMusicChip` control) so `togglePopupScene`'s new
  lookup resolves inside the sandboxed `vm` context the same way it does in the real page.
- Live-tested the full-undo path directly: ran `script.scene_dinner` (lights on, Harmony on
  Airplay, `media_player.crestron` playing `library://radio/1`), then issued the exact three calls
  `togglePopupScene`'s off-branch now makes — `homeassistant.turn_off` on `light.dinner_lights`,
  `media_player.media_stop`, `remote.turn_off` on `remote.harmony_hub` — and confirmed all three
  landed: lights off, player `idle`, Harmony `off`. Two of the group's thirteen members
  (`light.kitchen_pathway`, `light.kitchen_perimeter` — the same pair flagged as occasionally
  unresponsive in the ninth pass) again didn't respond to the on-command within several seconds,
  independent of anything this pass changed; confirmed harmless to this test by checking the other
  eleven members directly rather than relying on the group's own aggregate state.
- Deployed `dist/config.js` and `dist/homie-dashboard.html` to
  `/config/www/community/homie-dashboard/`, prior copies backed up with a timestamp, `config.js`
  re-spliced and diff-verified (only the `allMustBeOn` addition showed). `HOMIE_ASSET_VERSION`
  bumped `20260904.1` → `20260904.2` for real this time (both files changed, so per the ninth pass's
  new convention both cache-busting tokens moved together), matched exactly by `homie-dash`'s
  Lovelace iframe `?v=`.
- House left with all lights off, music idle, and Harmony off after live testing, matching a clean
  state rather than whatever partial state the flaky pair left behind.
