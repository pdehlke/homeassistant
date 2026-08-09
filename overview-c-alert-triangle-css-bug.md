# Overview C's alert triangle showed with no active alerts: a CSS specificity bug

Overview A and B correctly hide the bottom-left HA alert-messages triangle when there are no active
`persistent_notification`s. Overview C's copy of the same indicator, pinned to the bottom of its
sidebar, showed constantly regardless of whether any notification existed; tapping it opened the
overlay to "No active alerts."

See [homie-dashboard-install-plan.md](homie-dashboard-install-plan.md) for the fork and deployment
workflow.

## Diagnosis

All three surfaces (the corner button on Overview A/B and Overview C's sidebar button) are meant to
be hidden by default and shown only via a `.visible` class, toggled together by one function:

```js
function refreshAlertIndicator() {
  const has = pnCache.size > 0;
  document.getElementById("alert-indicator-corner")?.classList.toggle("visible", has);
  document.getElementById("ov3-alert-btn")?.classList.toggle("visible", has);
}
```

Confirmed live via `persistent_notification/get` that `pnCache` was genuinely empty (`[]`) at the
time this was reported, so `has` was `false` and both toggles were correctly clearing `.visible`.
The JS logic was never the problem.

The corner button's CSS has no competing rule: `.alert-indicator-corner { display: none; }` is the
only thing that sets its `display`, so `.visible`'s `display: flex` is the only way to show it.

Overview C's button carries two classes, `ov3-sb-btn ov3-alert-btn`. `.ov3-alert-btn { display:
none; }` was meant to do the same job, but `.ov3-sb-btn` — the base style shared by every sidebar
button, setting `display: flex` unconditionally — is declared later in the stylesheet. Both
selectors are single classes, so they carry identical specificity, and CSS resolves a specificity
tie by source order: whichever rule comes last in the file wins. `.ov3-sb-btn`'s `display: flex`
came after `.ov3-alert-btn`'s `display: none`, so it always won, regardless of the `.visible`
class. The corner button had no such competing rule at all, which is why only Overview C showed the
bug.

## The fix

Changed the hidden-by-default selector to `.ov3-sb-btn.ov3-alert-btn { display: none; }`. Two
classes gives it higher specificity than the single-class `.ov3-sb-btn` base rule, so it wins
regardless of which block comes first in the file. `.ov3-alert-btn.visible { display: flex; }` was
already two classes and needed no change; it now wins the tie against the hidden rule the same way
it always did against the single-class version, by source order between two equally-specific rules.

## What was considered and rejected

**Reorder the CSS blocks** so `.ov3-alert-btn { display: none; }` comes after `.ov3-sb-btn`
instead. Would have worked, but leaves the fix fragile: the next person to reorganize this
stylesheet (or add another selector that happens to match) could silently reintroduce the same bug
with no test catching it until someone notices the triangle again. Fixing the specificity instead
means the rule wins on its own terms, independent of file order.

## Verification

`test/screen-a.test.cjs`: a new test asserts `.ov3-sb-btn.ov3-alert-btn { display: none; }` exists
as its own rule, which fails against the pre-fix source (the compound selector doesn't exist yet)
and passes once the selector is bumped. 63/63 passing.

Deployed live (`HOMIE_ASSET_VERSION` `20260809.5` → `20260809.6`, `homie-dash` Lovelace iframe
`?v=` bumped to match) alongside the unrelated Climate alert-threshold fix in
[climate-alert-dashboard-threshold.md](climate-alert-dashboard-threshold.md), bundled into one
commit and one release on pde's call. Confirmed live via Playwright, against the instance's actual
state (`pnCache.size === 0`): `#ov3-alert-btn`'s computed `display` reads `none` on Overview C, and
a live screenshot of Overview C's sidebar shows no triangle at the bottom.
