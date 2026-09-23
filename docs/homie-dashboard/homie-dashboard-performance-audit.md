# Homie Dashboard performance audit, 2026-09-22

A deep code-quality audit of the fork, run with a specific question: what makes the dashboard slow
on the low-power wall-mounted Fire HD tablet, and what structural change fixes it?

Five fixes shipped and are live, across two passes on the same day. The first pass took only what
could fail safely unattended; pde then asked for the two large remaining items to go out the same
night, accepting morning triage if they broke. The CSS consolidation findings are written up here
and still not shipped, because they are pure refactors with visual-regression risk and no
proportional performance win.

**Nothing here has been looked at on the tablet.** Playwright is not installed on this machine, so
every claim below is verified by test, checksum, parse, or live WebSocket measurement, and none of
it by eye.

## What was reviewed

The fork is 81 commits ahead of `Big-Edge2297/homie-dashboard`, about 10,500 added lines. The code
is four files:

| File | Lines | Status in the fork |
| --- | --- | --- |
| `dist/homie-dashboard.html` | 23,025 | 4,268 lines changed |
| `dist/config.js` | 694 | 1,133 lines changed |
| `dist/homie-custom.js` | 432 | entirely new |
| `test/screen-a.test.cjs` | 3,059 | entirely new |

The HTML is one file holding a ~7,900-line `<style>` block, ~1,000 lines of body markup, a
~12,150-line main `<script>` block, and sixteen more overlay `<div>`s interleaved between later
script blocks.

## The headline finding: 96.9% of full re-renders were for nothing

`refreshAllUI()` re-renders every subsystem on the page: home stats, sensors, weather,
notifications, timers, Waze, greeting bubbles, controls, music, and both prebuilt overviews. It was
called **synchronously from the WebSocket `state_changed` handler, once per event, for every entity
in Home Assistant**, with no filter on whether the changed entity was displayed anywhere and no
coalescing of bursts.

That was measured, not assumed. Subscribing to the live instance for two minutes:

| Measure | Value |
| --- | --- |
| `state_changed` events in 120 s | 96 |
| From entities referenced *anywhere* in the dashboard source | 3 (3.1%) |
| From entities referenced nowhere | **93 (96.9%)** |
| Peak burst in any one second | 13 |

The top talkers were `lennoxs30.conn_192_168_4_126` and `lennoxs30.state` (integration internals)
and four `sensor.third_reality_inc_3rsp02064z_*` Zigbee smart-plug voltage sensors. None of them is
on screen. Each one triggered a full re-render of roughly 81 loop-driven DOM lookups, derived from
the real config scale: 8 chips, 13 sub-groups, 47 flattened sub-entities, 4 scene bubbles, 7 music
stations, 7 floor sensors.

Note this was a *quiet* window: no lights in use, no music, nobody home. Active use is worse.

### The fix

Two guards, in `dist/homie-dashboard.html`:

1. **Relevance.** Only render when the changed entity is one the UI actually reads. `stateCache`
   still updates on every event, so nothing goes stale; only the render is skipped. Every
   entity-specific handler (alarm badge, todo reload, pet stats, doorbell) still fires
   unconditionally, because those are cheap `if`s on one entity id each.
2. **Coalescing.** Collapse a burst into one render on the next animation frame.

The admissible set is the **union of two sources**, and the union is what makes it safe:

- A static sweep of `CONFIG` for anything matching an entity-id pattern (101 entities). This covers
  cold start and branches not currently taken: a popup that has never been opened has read nothing,
  but its entities must still trigger a render so the chip behind it updates.
- The set of entities read during the **last render pass**. This covers anything reached at runtime
  that `CONFIG` does not name by literal id, and it cannot go stale as popups open and close.

Neither alone is sufficient; either alone would eventually drop a render that mattered.

### Why the read set is captured by subclassing the Map

The obvious place to instrument reads is `haGetCached()`, the canonical accessor. That would have
been wrong: **16 call sites read `stateCache.get()` directly**, bypassing it, and a relevance filter
that silently missed them would freeze parts of the UI with no error. Subclassing `Map` and
overriding `get()` captures all 108 read sites with no call-site churn.

```js
class StateCache extends Map {
  get(entityId) {
    _readsThisPass.add(entityId);
    return super.get(entityId);
  }
}
```

Reads that happen outside a render pass (a button handler, say) land in the same set and are folded
in at the next swap. That only ever makes the filter *more* permissive, never less, so it cannot
cause a missed update.

Those 16 bypasses are themselves a finding: a canonical helper exists and is not universally used.
Routing them through `haGetCached()` is worth doing, but it was not needed for this fix and would
have added 16 unreviewed edits to a change that needed to stay small.

### Coalescing on rAF gives visibility gating for free

There are **30 `setInterval` sites in the file and zero `visibilitychange` or `document.hidden`
gating anywhere**. That looked like a finding in its own right, and for the periodic timers it still
is. But for the render path specifically, coalescing on `requestAnimationFrame` rather than a timer
means the browser itself suspends renders while the page is backgrounded. No separate
`visibilitychange` handler is needed, and adding one would have been redundant machinery.

Renders are additionally dropped while the blank screensaver covers the screen, with a dirty flag
replaying a single render on the way out. The screensaver is on by default and blanks to opaque
black, so before this the dashboard was re-rendering at full rate behind a black rectangle.

### Verified live, against the deployed file

The deployed render-scheduling block was extracted from the served HTML, driven with a simulated
60fps frame clock, and fed the real live event stream for two minutes:

| Measure | Value |
| --- | --- |
| Events received | 118 |
| Admitted by the relevance filter | 6 |
| Rejected | 112 |
| Actual `refreshAllUI()` calls | **2** |
| Old behaviour would have rendered | 118 times |
| **Reduction in full re-renders** | **98.3%** |

The entities still admitted were the Sense energy sensors, which genuinely drive Overview C. The
rejected ones were the Zigbee plug and Lennox chatter.

## Second finding: animations that run forever behind hidden overlays

Every overlay in this dashboard hides itself with `opacity: 0`, not `display: none`. **CSS
animations keep running on an `opacity: 0` element.** On a panel that never reboots, anything
infinite and ungated runs for the life of the device.

Three concrete cases, all verified against the file:

- **Weather particles leaked outright.** `openWeatherFS()` injects up to ~190 elements (80
  raindrops, 55 snowflakes, 90 stars, 18 dust streaks, plus clouds), each carrying an infinite
  animation. `closeWeatherFS()` only removed `.open`. One visit to the weather screen left all of
  them animating at 60fps for the rest of uptime, behind an invisible layer, behind the screensaver.
  Now the seven wrappers are emptied on close; `_wfsLastCondition` was already nulled, so the next
  open rebuilds them.
- **Solar flow dots never stopped.** Eight `.sfs-flow-dot` paths animate `stroke-dashoffset`, which
  **cannot be composited** - every frame costs main-thread SVG geometry plus a re-raster. The markup
  is static, so they ran from first paint whether or not the Solar screen had ever been opened. Now
  gated behind `#solar-fs-overlay.open`.
- **Two dead rules.** `.sfs-dot-battery` and `.sfs-dot-battery-2` match no markup at all.

Worth recording: the other 33 `animation:` declarations in the file are fine. They animate `opacity`
and `transform` only, which composite correctly. The raw count of 35 animations is not the problem;
the one non-compositable property is.

Also removed: two `backdrop-filter: blur(8px)` declarations that cost a full render surface and
produce nothing visible.

- `.popup-overlay` sits under `rgba(0,0,0,0.85)`, so only 15% of the blur ever reaches the eye, and
  **eight of these exist in the DOM at once**.
- `.daily-header` blurs `#daily-overlay`'s flat opaque `--bg-overlay` (`#0a0a0a`). Blurring a flat
  colour returns that same colour, so this was provably a no-op.

The other nine `backdrop-filter` uses were checked and kept: `.ov3-sidebar` and `.history-backdrop`
sit over 25% and 55% black respectively, where the blur is the actual effect, and the rest are small
pill-sized chips where the area is negligible.

## Shipped in the second pass, 2026-09-22 evening

pde asked for the remaining two large items to go out the same night, accepting that they might need
triage in the morning. Both are live.

### `subscribe_entities` replaced `subscribe_events`, unfiltered

Home Assistant's WebSocket API has a better primitive than the `subscribe_events` this dashboard
used. `subscribe_entities` pushes a compressed delta format (`a` added, `c` changed with `+`/`-`
attribute deltas, `r` removed) instead of full state objects, and its **first message is a full
snapshot of every entity**, so the separate `get_states` round trip is gone.

Measured on the live instance over one 90-second window:

| Subscription | Messages | Bytes |
| --- | --- | --- |
| `subscribe_events(state_changed)` (before) | 88 | 133,690 |
| `subscribe_entities`, no filter (now) | 88 | 18,303 |
| **Reduction** | 0% | **86.3%** |

**It is deliberately unfiltered, and this is the important decision.** `subscribe_entities` accepts
an `entity_ids` list, and filtering to the 101 entities `CONFIG` names cuts bytes by 99.3% instead
of 86.3%. That was the number quoted in the first pass. It was not taken, because any entity the UI
resolves at runtime rather than by literal id - a light group's members, for one - would then be
absent from the cache entirely, and the failure mode is a silently wrong dashboard rather than an
error. Render-skipping is already handled by `entityAffectsUI()`, so the filter would buy bytes that
are not needed at a risk that does not have to be taken. The remaining 13% is available later if it
ever matters.

Two helpers expand the wire format back into the full state object shape every other call site
already expects, so nothing downstream changed. Two details in them are load-bearing:

- **`last_changed` is converted from the wire's float unix seconds to an ISO string.**
  `_camMotionPoll()` feeds it straight into `new Date()`, and a raw seconds value is read as
  milliseconds, which would have dated every "last motion" label to 1970.
- **Attribute deltas are merged onto the cached state, never replace it.** The wire carries only
  what changed, so rebuilding from the delta alone would silently drop every attribute that stayed
  the same.

Three things the switch forced, each of which would have been a real bug:

- `StateCache` grew a `peek()` that reads **without** recording a UI read. The merge path has to read
  the previous state, and going through `get()` there would file every changed entity as "something
  the UI reads" - the admissible set would grow to cover everything and **the relevance filter would
  quietly stop filtering**.
- The `if (!_wsReady) break` guard at the top of the event case had to go. The seed snapshot now
  arrives *as an event* and is what *sets* `_wsReady`, so the guard would have blocked the very
  message it was waiting for and the dashboard would never have loaded.
- The doorbell edge check reads the previous `last_triggered` off the cache before the write,
  because the compressed format carries no `old_state`.

Verified against the live instance, using the bytes actually being served: **764 snapshot entities
expanded with zero mismatches** against `/api/states` on state, attribute keys and timestamps, and
37 real delta merges with no dropped attributes and no invalid dates.

### `content-visibility` on closed overlays

Fourteen overlays now carry `content-visibility: hidden` in their `:not(.open)` state, taking
roughly 1,100 permanently-laid-out elements (about 480 of them the settings panel) out of every
style recalculation and layout pass. It also stops animations inside a closed overlay from producing
rendering work, which is the same class of problem the weather-particle and solar-flow-dot fixes
addressed directly.

`#overview2` and `#overview3` are excluded on purpose. They are not `.open`-gated (they switch on a
body class), and they are pre-built at startup precisely so the first swipe is instant, so skipping
their layout is the one case here that would trade a real cost for a visible one.

### The loader no longer uses `document.write`

`config.js` and `homie-custom.js` still have to load and run before the main script, so their tags
are still blocking. What changed is *discovery*: the preload scanner reads ahead through the raw
bytes and can start fetching a literal `src` immediately, but it cannot see inside a
`document.write()` string. Written the old way those two requests could not begin until the parser
had chewed through ~9,000 lines including a 7,900-line stylesheet, and then ran serially.

The tags stay where they were rather than moving to `<head>`, because `config.js` references
`ICONS`, which the inline block just above it defines. That dependency is the reason the obvious
"just move them up" version does not work.

## Review of `config.js` and `homie-custom.js`

Both were reviewed in the second pass. Neither needed restructuring.

`homie-custom.js` is the healthiest code in this repository. It is a UMD module of 32 pure
functions with **zero DOM access, zero global reads, and dependency injection where it needs
platform state** (`installDefaults(storage, defaults, version)` takes `localStorage` as a
parameter rather than reaching for it). 31 of the 32 functions are exported and the suite tests
them directly. No changes made.

`config.js` is data, as it should be. The only logic in it is a `welcomeText` getter with a loop
over greeting slots, and that is upstream, not something the fork added. The `HA_TOKEN` placeholder
discipline is sound: the checked-in copy carries the placeholder and the real value is spliced on
the host. No changes made.

The one real finding in this area was the `document.write` loader above, which is a property of how
the HTML loads them rather than of either file.

### Structural findings in the CSS

- **Four byte-identical progress-bar rules** (`.np-progress-fill`, `.np-fs-progress-fill`,
  `.np-ls-progress-fill`, `.ov3-music-progress-fill`) each transition `width`, which forces layout
  every frame. JS updates them once a second, so each update runs a 1-second, 60-frame
  layout-and-paint on the main thread. "Music is playing" is the second most common steady state on
  a wall panel after idle, so this is continuous. `transform: scaleX()` with
  `transform-origin: left` is visually identical and runs entirely on the compositor.
- **Seven `max-height` accordions** transition `max-height` *and* `padding`, forcing a full layout of
  the expanding subtree every frame. These fire on every tap on a light, AC, purifier, or cover card.
- **The `.mush-*` family is 594 lines expressing one component five times** (`ac`, `purifier`,
  `cover`, `switch`, `light`). Five `*-name` rules share seven identical declarations; three
  `*-track` rules and three `*-input` rules likewise. Adding a sixth device type means a sixth
  transcription; fixing a card bug means finding five sites.
- **The neutral colour scale is not tokenized.** 336 hardcoded `rgba(255,255,255,X)` across 34
  distinct alpha steps, many differing by 0.01 and visually indistinguishable, plus 84 `#fff` and 15
  `#ffffff`. The accent side is done properly with tokens; the neutral side, which is most of the
  file's colour, is not. `--text-primary` and `--text-secondary` are defined and consumed at exactly
  one site in 7,935 lines.

Two things worth recording because they were checked and are *not* problems: `!important` appears
only 10 times in the whole file, which is unusually disciplined, and selector depth is shallow
throughout. There is no `* { transition }` blanket rule.

A consolidation pass would delete roughly 1,200 CSS lines (~15%), of which ~630 is a hard measured
floor from rules sharing identical property signatures and ~90 is 36 dead classes.

### Document structure

A `<style>` block appears at line 22,860, near the end of `<body>`, and a **third stylesheet is
injected at runtime** via `document.head.appendChild`. Both force a full style recalculation and
layout at a point where the page has already been computed, on a device where startup is already
slow. The late block was checked for collisions against the main one and has none, so folding it in
is a pure move.

## Housekeeping noticed in passing

`/config/www/community/homie-dashboard/` on the Home Assistant host holds **over 100 `.bak` files**
going back to 2026-08-08, roughly 90 MB of superseded copies of `homie-dashboard.html` alone. The
deploy procedure creates one every time and nothing prunes them. Worth a one-line cleanup keeping
the last few.

## Deployment

Two deploys, both following the documented procedure: SSH add-on started, live directory backed up,
file uploaded under a temp name and checksum-verified *before* the atomic rename, `homie-dash`
iframe `?v=` bumped to match `HOMIE_ASSET_VERSION`, SSH add-on stopped.

| Pass | Version | Deployed sha256 | Rollback target |
| --- | --- | --- | --- |
| First | `20260922.2` | `ef3ec9cf…f670d9e728` | `homie-dashboard.html.bak-20260922-perf` (= `8663e1c`) |
| Second | `20260922.3` | `51d143db…4d49be0f5ee` | `homie-dashboard.html.bak-20260922-se` (= `05703aa`) |

Both were verified byte-identical to the local build and to the file actually served over HTTPS,
and after the second the two nested assets were confirmed to resolve at the new version (`config.js`
and `homie-custom.js`, both HTTP 200).

Only `homie-dashboard.html` changed in either pass. `config.js` and `homie-custom.js` were untouched,
so the token-splicing step was never needed - which also removed the riskiest part of the deploy.

Five commits on the fork's `main`, **not pushed**, each independently revertable:
`ea7ac99` render scheduling, `05703aa` always-running animations, `b969b8b` `subscribe_entities`,
`786c668` `content-visibility`, `ee75b7a` the loader.

## Note on the test suite

The suite was **already red** before any of this work: `test/screen-a.test.cjs` asserted the asset
version equalled the literal `"20260910.1"`. Since the deploy procedure requires bumping that
version, the test failed on *every* deploy by construction, which trains everyone to ignore a red
suite. It now asserts the `YYYYMMDD.N` format and that both nested assets are versioned off the one
token, which is what the test was actually named for.

The fifteen tests added across both passes are split by kind. Five **execute the real
render-scheduling block** extracted from the HTML in a `vm` with a fake frame clock, and six
**execute the real wire-format helpers** against fixtures reproducing live payloads, rather than
asserting on source text, because the thing worth protecting is the behaviour. Four pin things at
source level that are easy to regress by accident: the animation gates, the `content-visibility`
rule and its two deliberate exclusions, the static script tags, and the absence of a `_wsReady`
guard that would deadlock the seed snapshot.

One recurring trap worth knowing before adding more: these blocks run in their own `vm` realm, so
`instanceof` and `deepStrictEqual` fail on prototype identity alone even when the values match.
Compare keys and fields, not objects.

Suite is 152/152 green.
