# Liquid Glass dashboards: periodic blur artifacts, fixed by hiding the sidebar

pde reported dark blue vertical and horizontal artifacts appearing and disappearing on several
cards on `dashboard-clock`, roughly every two seconds. Confirmed not specific to that dashboard:
pasting the Clock dashboard's YAML into a new view on `dashboard-office` reproduced the same
artifacts there. Diagnosed and resolved 2026-09-07 on Home Assistant 2026.8.1.

## What the artifacts are

Both dashboards use the "Liquid Glass" theme (`Nezz/homeassistant-visionos-theme` v3.0.7,
HACS-installed). The theme gives every `ha-card` its own frosted-glass look via an
absolutely-positioned `::before` pseudo-element carrying `backdrop-filter: blur(8px)`, confirmed by
reading the theme's own source and by inspecting the live injected CSS in a card's shadow root. At
the time this was investigated, `dashboard-clock`'s single view had 10 of these `ha-card` blur
layers stacked on one page. The theme also applies the same `backdrop-filter` to Home Assistant's
own sidebar and header, via `app-header-backdrop-filter` and drawer/sidebar selectors that inherit
the same CSS variable.

## A wrong turn: diagnosing against the wrong rendering engine

The first diagnostic pass assumed a Chromium browser, since that's what every other verification in
this project's Home Assistant work has used (`playwright-cli`'s bundled Chromium). That produced a
plausible-looking but ultimately wrong answer: Chromium has a well-documented `backdrop-filter`
edge-sampling bug ([Chromium issue 41471914](https://issues.chromium.org/issues/41471914),
[issue 339841685](https://issues.chromium.org/issues/339841685)) where the compositor guesses at
pixel data outside a blurred element's own edges, producing flicker when content near the edge
changes. A partial fix shipped in Chrome 129 (2024), with reports of residual flicker on pages with
many overlapping blurred layers persisting after that.

This turned out not to apply. pde's actual browser is Zen 1.21.15b (Firefox 154.0, aarch64), which
uses Gecko's WebRender compositor, not Chromium's. WebRender implements `backdrop-filter`
completely independently and has its own separate bug history, including reports of literally
"tile"-shaped high-contrast artifacts ([Bugzilla 1741305](https://bugzilla.mozilla.org/show_bug.cgi?id=1741305)),
incorrect blur output from WebRender's own tiled multi-pass blur implementation
([Bugzilla 1573886](https://bugzilla.mozilla.org/show_bug.cgi?id=1573886)), and multiple bugs
specifically about `backdrop-filter` breaking on fixed or sticky-positioned elements
([Bugzilla 1909463](https://bugzilla.mozilla.org/show_bug.cgi?id=1909463),
[Bugzilla 1803813](https://bugzilla.mozilla.org/show_bug.cgi?id=1803813)). None of the specific
Chromium citations above are relevant to what pde is actually running; they're recorded here only
so a future pass doesn't repeat the same wrong assumption.

Lesson for next time: ask which browser is actually rendering the artifact before diagnosing a
rendering bug, rather than assuming Chromium because that's what this project's own tooling
happens to use.

## Confirming this isn't a content/DOM change

Before chasing browser-engine bugs at all, the artifact was confirmed to not correlate with any
actual state or DOM change: a burst of 16 screenshots taken 250ms apart during a period when the
artifact was reportedly flickering showed zero pixel difference across every frame. Screenshot
capture goes through a different rendering path than the live on-screen compositor (in this case,
Chromium's headless screenshot pipeline, which doesn't reproduce GPU/compositor-only glitches at
all), so this ruled out a data or template re-render issue without being able to directly observe
the actual artifact.

## The fix pde found: hide the sidebar

pde independently discovered that setting "Always hide the sidebar" in his Home Assistant profile
makes the artifacts "largely disappear," leaving only a single flash on initial dashboard load
rather than the original recurring flicker.

This tracks with the WebRender bug family above rather than being a coincidental workaround. The
sidebar is `position: fixed`, spans the full viewport height, and carries its own `backdrop-filter`
from the same theme. That combination, a fixed-position blurred element sitting immediately next to
roughly a dozen more blurred cards that are still mounting and resizing during the first few seconds
of dashboard load, matches exactly what Mozilla's fixed/sticky-positioned `backdrop-filter` bugs
describe. Removing the sidebar's blur layer removes the one element in the mix that's both
fixed-position and viewport-spanning; each card's own blur layer still has to render once on its
own initial mount, which is a one-time settle rather than an ongoing recompute, matching the
single-flash-on-load residual pde still sees.

## Decision: accept this as-is

Presented with the choice of accepting the sidebar-hidden state versus continuing to chase the
residual single on-load flash, pde chose to accept it. Reasoning: continuing would mean trying
further CSS containment/`will-change` mitigations on the theme's blur layers with no way to verify
any of them without a live round-trip (this investigator cannot perceive or reproduce the artifact
directly, per the screenshot-burst finding above), against a residual that is already a one-time
settle rather than ongoing flicker.

**Trade-off worth remembering:** "Always hide the sidebar" is a per-user Home Assistant profile
preference, not a per-dashboard setting. It hides the sidebar on every dashboard pde views with that
profile, not only `dashboard-clock`.
