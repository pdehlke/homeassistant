# Office dashboard: the auto-scrolling News ticker

`dashboard-office`'s News card now advances itself, one article at a time, forever, with no human
input. Built 2026-08-14 on Home Assistant 2026.8.1, for a display in the Office that will not have
a mouse, a touchscreen, or a keyboard reachable by anyone standing in front of it.

## The problem

The News card is `custom:rss-news-card` ([`suxlala/rss-news-card`](https://github.com/suxlala/rss-news-card),
HACS-installed, v1.5.2), fed by `sensor.cnn_top_news`, `sensor.bbc_europe`, and `sensor.ms_now`,
rendered at a fixed `card_height: 400`. Its only scroll behavior, confirmed by reading the
installed bundle (`/hacsfiles/rss-news-card/rss-news-card.js`) directly, is a plain
`overflow-y: scroll` div with touch-scrolling CSS: built for a finger or a mouse wheel. Its full
config surface, enumerated from every `_config.*` and editor `.ed.*` reference in the bundle, is
`title`, `sources`, `max_articles`, `card_height`, `show_description`, `show_source`, `show_date`,
`image_width`/`image_height`, two font sizes, and three colors. Nothing scroll-, interval-, or
animation-related exists anywhere in it.

A search of the full HACS store turned up nothing that combines "RSS feed" with "auto-scrolling
ticker." The two closest hits, `cataseven/Strip-Card` (a horizontal ticker built for generic entity
states, not RSS items with images and descriptions) and `Flybrow/lovelace-kiosk-autoscroll` (which
auto-scrolls an entire dashboard *view*, not one card in place), both solve a different problem.
This card is unique to `dashboard-office`; grepping every other dashboard's saved config
(`vision-sample`, `dashboard-lights`, `dashboard-av`, `dashboard-lennox-home`,
`dashboard-alarm-system`, `homie-dash`) found no other use of `rss-news-card` anywhere on this
instance.

## Decisions, and what drove them

- **Discrete pause-and-advance, not a continuous crawl.** This is an ambient display someone
  glances at, not a stock ticker; a headline that scrolls past mid-sentence before anyone can read
  it defeats the point of putting news on the wall at all. A horizontal single-line marquee was
  also considered and rejected for the same reason, plus it would have meant dropping the
  images and descriptions the card already shows.
- **One article per step, not a "screenful" per step.** Advancing by whatever fits fully inside
  `card_height` without cutting a row looks cleaner in isolation, but makes dwell time meaningless:
  a page holding one long article gets the same time on screen as a page holding four short ones.
  Stepping to exactly the next article's top edge keeps dwell time consistent per article
  regardless of length, at the cost of sometimes showing a partially cut-off next row at the
  bottom edge, which reads as a normal "more below" cue rather than as broken.
- **~6 second dwell per article**, tunable, not derived from anything more precise than "long
  enough to read a headline and a line of description."
- **Seamless wrap from the last article back to the first.** In practice this means the wrap step
  uses the exact same smooth-scroll transition as every other step, just moving backward in one
  jump instead of forward. True seamless infinite-loop motion (content never reverses direction)
  is a real technique but only makes sense for a continuous crawl, which was already rejected
  above; for a discrete list there's no such thing as wrapping without the view moving back to the
  top, so "seamless" here means "not a jarring instant cut," not "never moves backward."
- **Restart cleanly from article 1 whenever the underlying sensors refresh**, rather than trying to
  preserve scroll position against a rebuilt article list. Matching old articles to new ones by URL
  or title, and handling the case where the currently-shown one no longer exists, is real
  complexity for an edge case that fires at most a few times an hour.
- **A new wrapper custom card, not `card-mod` and not a hand-patched fork of `rss-news-card`
  itself.** This was the biggest reversal of the session. The original plan was a `card-mod`
  CSS-only bolt-on: no new custom card, fully reversible in one dashboard-config edit. That
  turned out to be impossible for discrete pause-and-advance specifically. `rss-news-card` renders
  each article at whatever height its description happens to wrap to; there's no `line-clamp`, no
  fixed row height. A pure CSS `@keyframes` animation can express "translate by a constant amount
  forever" (that's how a continuous crawl works, and it wouldn't have cared about variable row
  heights at all), but it cannot express "hold here, then animate to wherever the next row's actual
  top edge happens to be, then hold again." CSS has no mechanism to measure DOM layout at runtime
  or to advance a scroll position autonomously on a timer at all; CSS Scroll Snap only snaps
  scrolling a human already started. That needs JavaScript, which ruled out `card-mod` for the
  chosen scroll style.

  The remaining choice was where that JavaScript lives. Patching `rss-news-card`'s own source was
  the obvious alternative, and arguably the technically cleanest one: its own render code already
  has direct references to each article row as it builds them. It was rejected anyway, for the
  same reason mini-media-player's undocumented options and the Homie Dashboard fork both carry a
  standing risk note in this repo: hand-editing a file HACS actively tracks means a future
  `rss-news-card` update can silently clobber the edit. A separate wrapper card that embeds a real
  `<rss-news-card>` element and drives it from outside touches none of `rss-news-card`'s own files,
  so a HACS update to it can't overwrite anything. It still isn't risk-free: the wrapper reaches
  into `rss-news-card`'s internal DOM (`.rss-scroll`, `.rss-article-row`), which is not a published
  API, so a future `rss-news-card` update that renames those classes would silently stop the
  ticker from advancing (the feed would keep rendering correctly, just static) rather than raising
  an error anywhere visible.
- **One-off, not a reusable pattern.** Nothing else on this instance needs an auto-scrolling
  anything today (confirmed above). Building a general "kiosk ticker" abstraction ahead of a
  second consumer would be speculative scope; easy to extract later if one shows up.

## What got built

`office-news-ticker`, a single custom element (`<office-news-ticker>`, roughly 90 lines) that:

- Takes a config of `{ dwell_seconds, inner_config }`, where `inner_config` is an ordinary
  `rss-news-card` config, unchanged from what was on the dashboard before this change.
- On first `hass` assignment, creates a real `<rss-news-card>` element, calls its `setConfig()`
  with `inner_config`, and appends it to itself (light DOM; `rss-news-card` itself has no shadow
  root, confirmed by the absence of any `attachShadow` call in its bundle, so this needed no
  shadow-piercing).
- Mirrors `rss-news-card`'s own change-detection exactly: the same `entity:state:last_updated`
  join over the same three source sensors that `rss-news-card`'s own `hass` setter already uses to
  decide whether to re-render. This means the wrapper restarts precisely when the inner card
  actually rebuilds its article list, not on every unrelated `hass` tick elsewhere in the house.
- On a restart, reads every `.rss-article-row` inside the inner card, resets `.rss-scroll`'s
  `scrollTop` to 0, and starts a `setTimeout` loop: wait `dwell_seconds`, `scrollTo` the next
  row's `offsetTop` with `behavior: "smooth"`, repeat, wrapping the index with `% rows.length`.

Deployed by hand to `/config/www/office-news-ticker/office-news-ticker.js` on `hass.ehlke.net`
(SSH, `root@hass.ehlke.net:2222`, the same key already used for Homie Dashboard maintenance,
confirmed to reach `/config/www` generally rather than being scoped to Homie's own subdirectory)
and registered as a Lovelace resource at `/local/office-news-ticker/office-news-ticker.js` via
`lovelace/resources/create` over the WebSocket API. Not HACS-managed, not tracked in any git repo;
this document and the deployed file on the Pi are its only copies. The dashboard's News card was
swapped from `custom:rss-news-card` to `custom:office-news-ticker` (wrapping the original
`rss-news-card` config verbatim) with `scripts/apply-card.py`, which refused to run until it
confirmed exactly one match, same read-backup-modify-save discipline as every other dashboard edit
in this skill.

## Verification status

Confirmed live via Playwright against `hass.ehlke.net`, reading the wrapper's internal state
(`_idx`, `.rss-scroll`'s `scrollTop`) directly through HA's nested shadow roots rather than only
inferring behavior from screenshots:

- **Timing accuracy**: sampling `_idx` at known wall-clock intervals showed it advancing at
  exactly one step per ~6 second dwell, matching `dwell_seconds: 6` precisely once actual CLI
  round-trip overhead was accounted for.
- **Row count**: exactly 10 `.rss-article-row` elements, matching `max_articles: 10` (confirms
  the cap is a total across all three sources, not 10 per source).
- **Per-article step distance is genuinely variable**: the first two articles measured 266px tall
  each (one CNN item's description happened to repeat its own URL twice, an artifact of that
  particular feed entry, not of this card), the rest 126-167px. The step from article 0 to article
  1 visually looked like it skipped past several shorter articles in an early screenshot; reading
  `rowOffsets` directly confirmed this was one correct step, just a large one, exactly the
  documented tradeoff of per-article (not per-screenful) stepping.
- **Wrap-around**: watched `_idx` cycle 0 through 9 and back to 0, then confirmed `_idx: 2` on the
  second lap reported the identical `scrollTop` (591px) as `_idx: 2` on the first lap. No drift,
  no corruption, no special-cased jump at the boundary beyond the same smooth-scroll transition
  every other step uses.
- **No console errors** attributable to `office-news-ticker` at any point. One pre-existing,
  unrelated error was surfaced during this check: a stray `/local/community/rss-news-card/rss-news-card.js`
  Lovelace resource (visible in `lovelace/resources`, distinct from the HACS-managed
  `/hacsfiles/rss-news-card/rss-news-card.js` entry) throws
  `DOMException: the name "rss-news-card" has already been used with this registry` on every page
  load, because both resources try to register the same custom element. Harmless (the
  browser keeps whichever definition loaded first) but worth cleaning up separately; it predates
  this change and is unrelated to it.

Not verified: behavior over a real multi-hour sensor refresh (the restart-on-refresh path was
built and reasoned through, but not watched live against an actual feed update, since that would
have meant waiting for `sensor.cnn_top_news` et al. to refresh on their own schedule rather than on
demand).
