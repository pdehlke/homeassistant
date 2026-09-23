# Homie Dashboard performance audit, 2026-09-22

A deep code-quality audit of the fork, run with a specific question: what makes the dashboard slow
on the low-power wall-mounted Fire HD tablet, and what structural change fixes it?

Two fixes shipped and are live. Several larger findings are written up here and deliberately not
shipped, because they need someone looking at the screen to approve them and nobody was.

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

## Measured but deliberately not shipped

### `subscribe_entities` would cut the wire traffic by 99.3%

Home Assistant's WebSocket API has a better primitive than the `subscribe_events` this dashboard
uses. `subscribe_entities` takes an `entity_ids` filter, applies it **server-side**, and pushes a
compressed delta format (`a` for added, `c` for changed with `+`/`-` attribute deltas) instead of
full state objects.

It was confirmed working on this instance and measured head-to-head over the same 90-second window:

| Subscription | Messages | Bytes |
| --- | --- | --- |
| `subscribe_events(state_changed)` (current) | 90 | 142,192 |
| `subscribe_entities(101 displayed ids)` | 7 | 1,062 |
| **Reduction** | **92.2%** | **99.3%** |

It also pays a one-time ~29 KB seed snapshot at connect that **replaces the current `get_states`
call entirely**, so it is not extra work.

This is the better long-term answer: it moves the filter to the server, so the tablet never
receives, parses, or allocates for the 97% at all, rather than filtering after the parse. It was not
shipped because it rewrites the handshake and the cache-population path, the delta-merge logic is
fiddly, and getting it subtly wrong shows up as a silently stale dashboard rather than an error.
That needs someone watching the screen. The relevance filter that *was* shipped captures most of the
CPU win at a fraction of the risk, and the two compose: the filter stays correct and simply stops
rejecting anything once the server is doing the filtering.

### Overlays that are always laid out

Sixteen full-viewport overlays are alive at all times and none is ever removed from the render tree;
`.open` only flips `opacity` and `pointer-events`. Roughly **1,100 elements that are never seen but
are always measured**, including ~480 in `#settings-overlay` alone. Every style recalculation walks
all of them.

The fix is one shared base class plus `content-visibility: hidden; contain: strict` on the
not-`.open` state, which skips layout and paint of descendants. It is probably the single largest
paint-performance win available here, and it would also neutralise whole categories of the
always-running-animation problem above without touching any JS.

Not shipped: it touches the main popup system used on every interaction, and the failure mode is a
broken or janky fade on every overlay in the app. That is a change to watch happen, not one to
deploy overnight.

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

Deployed 2026-09-22 following the documented procedure: SSH add-on started, live directory backed
up, file uploaded under a temp name and checksum-verified *before* the atomic rename, `homie-dash`
iframe `?v=` bumped to match `HOMIE_ASSET_VERSION`, SSH add-on stopped.

- Asset version `20260922.1` -> `20260922.2`
- Deployed sha256 `ef3ec9cf45594c47636105617a46cf1b9feb17677d34e15175df5df670d9e728`, verified
  byte-identical to the local build and to the file actually served over HTTPS
- Rollback target: `/config/www/community/homie-dashboard/homie-dashboard.html.bak-20260922-perf`,
  byte-identical to commit `8663e1c`

Only `homie-dashboard.html` changed. `config.js` and `homie-custom.js` were untouched, so the
token-splicing step was not needed - which also removed the riskiest part of the deploy.

## Note on the test suite

The suite was **already red** before any of this work: `test/screen-a.test.cjs` asserted the asset
version equalled the literal `"20260910.1"`. Since the deploy procedure requires bumping that
version, the test failed on *every* deploy by construction, which trains everyone to ignore a red
suite. It now asserts the `YYYYMMDD.N` format and that both nested assets are versioned off the one
token, which is what the test was actually named for.

The eight tests added for this work are split by kind: five **execute the real render-scheduling
block** extracted from the HTML in a `vm` with a fake frame clock, rather than asserting on its
source text, because the thing worth protecting is the behaviour. Three pin the animation fixes at
source level, including the assumption the solar gate rests on.

Suite is 145/145 green.
