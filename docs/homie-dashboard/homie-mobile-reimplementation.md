# Mobile-first Homie Dashboard reimplementation: paused design

> **Resume the actual session**: `5c9b2b50-d809-4ddc-be34-f0697c809ef2`. This is the live Claude
> Code session the original `/grill-with-docs` conversation ran in; resuming it directly carries
> the full conversation, not just this summary.

This records an in-progress `/grill-with-docs` design session (2026-08-16) for a mobile-first
rebuild of Homie Dashboard's functions, paused mid-round at pde's request while he was away from
keyboard. It is not a finished decision: no ADR exists yet, and several open questions below are
still unanswered. Tracked as [GitHub issue #13](https://github.com/pdehlke/homeassistant/issues/13).
Resume from the open questions below rather than re-litigating what's already settled.

## Why

Homie Dashboard (the wall-tablet fork tracked at `pdehlke/homie-dashboard`) was built for one
fixed target, the Fire HD 10 kiosk tablet, and it shows. A code audit plus Playwright screenshots
across Overview A/B/C at an iPhone 16 Pro viewport, done as part of this session, found:

- `dist/homie-dashboard.html` (22,750 lines as of 2026-08-27) has zero `@media` queries anywhere.
- A fixed four-column, no-wrap stat grid that doesn't reflow at phone width.
- A title/weather-icon pair with no vertical coordination at narrower viewports.
- A swipe/"pull to dismiss" gesture system (`OV3_SWIPE_EXCLUDE_SELECTOR`) that doesn't even reach
  the chip overlay: `#popup-overlay` dismisses only via a backdrop tap (`closePopup(event)`,
  fired on the overlay's own `onclick`), and the overlay itself renders at 90% width, leaving
  almost no backdrop to tap on a phone screen.

The fork's own `README.md` states this plainly as a non-goal: "❌ Phones", "❌ Small screens". The
overlap and clipping this produces reproduced in a plain WebKit browser at iPhone width,
independent of Home Assistant's own Companion App and its iframe-in-webview wrapper; Overview B
and C fared worse than Overview A, not better. (The screenshots taken during this investigation
lived in a session-scratchpad path and were shown to pde directly at the time; that path is
ephemeral and no longer exists.)

## Settled so far

- **Coexists with the existing wall-tablet dashboard; does not replace it.** The Fire HD 10 kiosk
  keeps running Homie Dashboard exactly as it does today.
- **A new build, not a retrofit of the existing fork.** Given the zero-`@media`-query, fixed-grid,
  and gesture-system findings above, patching the existing 22k-line file toward responsiveness was
  weighed against starting fresh and rejected: the existing dashboard was never architected with a
  second viewport in mind, and the fork's own stated non-goals confirm that was deliberate, not an
  oversight to patch around.
- **Decoupled from the "remotely accessible Homie Dashboard" backlog item**, now
  [issue #13](https://github.com/pdehlke/homeassistant/issues/13) itself, which is exactly this
  thread. The earlier, now-retired `project-todo.md` phrasing of that ask ("build a remotely
  accessible Homie Dashboard") and this "mobile-first reimplementation" framing were confirmed by
  pde to be the same effort, not two separate ones. Remote access (reaching the mobile build from
  outside the LAN) is explicitly kept as a separate future grilling topic; v1 is LAN-only, the same
  trust model as the existing dashboard.
- **Built for pde now, and his wife eventually, both as full HA admin accounts, not a restricted
  or kiosk-style tier.** The design must not assume a single user anywhere: the auth model needs
  to support multiple independent admin logins from day one, even though her onboarding happens
  later.
- **Sync cost is an explicit decision-matrix factor pde wants weighed going forward**: the ongoing
  cost of keeping a separate mobile build in feature sync as Homie Dashboard itself keeps growing.
  This mostly resolved in favor of a new build over a retrofit for now, but it stays relevant to
  how much feature parity the new build should chase (see Q8 below).

## Open questions, unanswered when paused

- **Q8, deferred by pde**: what "essential features" actually means for the mobile build, a
  glance-and-act subset of Homie's functions or fuller parity with the wall tablet. Pde said this
  should become clear as later rounds land, so don't push on it independently before then.
- **Q11, asked, unanswered**: what phone platform does pde's wife use, iOS or Android? This
  matters directly because of the no-single-user-assumption decision above: it rules out a
  true-native-iOS-only build if she's on a different platform.
- **Q12, asked, unanswered**: reopens pde's original "native" framing. Since the investigation
  found the actual bug class is pure CSS/gesture code, not the Companion App's iframe wrapper, a
  PWA (home-screen install, standalone display mode, no Companion App involved) would fix that bug
  class at a fraction of native's cost, and covers both platforms identically. The open question
  for pde: does "native" carry real requirements a PWA can't meet (home-screen widgets, Lock
  Screen/Dynamic Island, a Face ID gate, push notifications, Shortcuts/Siri integration), or was it
  shorthand for "not the broken iframe-in-app situation", which a PWA also solves?

## Resume action

Ask Q11 and Q12 again; verbatim is fine, since nothing about them has gone stale, before anything
else. Don't re-litigate the settled items above without new evidence.

## Not yet true, don't assume on resume

No ADR exists for any of this yet. "New build over retrofit," and whichever way the eventual
native-vs-PWA question resolves, are real ADR candidates once this design tree closes out (hard to
reverse, surprising, a genuine trade-off): write them then, not now, per this repo's
domain-modeling conventions ([docs/agents/domain.md](../agents/domain.md)).
