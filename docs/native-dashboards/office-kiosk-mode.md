# Office dashboard: kiosk chrome

`dashboard-office` gained a `kiosk_mode` block, scoped to the `office` user (display name
"Office"), hiding both the native top app bar and the sidebar. Built 2026-08-15 on Home Assistant
2026.8.1.

## What changed

```yaml
kiosk_mode:
  user_settings:
    - users: ["Office"]
      hide_header: true
      hide_sidebar: true
```

Added at the root of `dashboard-office`'s saved config, a sibling of `views`, matching where the
`NemesisRE/kiosk-mode` plugin expects it (per dashboard, not global) and how it matches accounts
(display name, not username; see [native-dashboards-retired.md](native-dashboards-retired.md) for
the plugin background, first established on the now-retired standalone domain dashboards). This is
the same fix already applied to `homie-dash` for the `Homie Dashboard` user, see
[homie-dashboard-install-plan.md](../homie-dashboard/homie-dashboard-install-plan.md)'s "Overview C
vertical overflow" section.

## Why both `hide_header` and `hide_sidebar`, not `hide_sidebar` alone

The now-retired Home dashboard was a real exception to the usual both-flags pattern (see
[native-dashboards-retired.md](native-dashboards-retired.md)): it was a multi-view dashboard whose
native header carried the tab strip, so hiding the header there would have taken the only
navigation between tabs with it. `dashboard-office` doesn't have that problem.
Its saved config has exactly one view (confirmed by reading it back over the WebSocket API before
making this change: `views` is a one-element array with a null `title`/`path`, i.e. no tab
navigation for a hidden header to break). It is a single-screen kiosk display, the same shape as
`homie-dash`, so it gets the same both-flags treatment `homie-dash` uses rather than Home's
sidebar-only carve-out.

## Recurrence: the block was silently dropped by the Lovelace UI editor

Confirmed gone about seven minutes after the "Verification" read-back below, with no
`lovelace/config/save` call from this skill's scripts in between; the only thing that happened to
`dashboard-office` in that window was pde opening it in the Lovelace UI to look at the clock-card
change from [office-clock-card.md](office-clock-card.md). Confirmed by pde directly: that's what
happened.

`kiosk_mode` lives at the root of the saved config, a sibling of `views`, and `NemesisRE/kiosk-mode`
is the only thing that reads it; nothing in Home Assistant's own dashboard schema knows the key
exists. The Lovelace UI editor's save path evidently doesn't round-trip arbitrary top-level keys the
way the WebSocket `lovelace/config/save` command does when driven directly: opening the dashboard in
the graphical editor and working in there, even to look at an unrelated card rather than to change
`kiosk_mode` itself, was enough to trigger a save that reconstructs the config from the editor's own
model, and that model has no slot for `kiosk_mode`, so it isn't in the object that gets written back.
Exactly which editor action inside that session triggered the save (opening edit mode itself, versus
some specific interaction within it) wasn't narrowed down further.

This isn't unique to `dashboard-office`. `homie-dash` carries the same kind of root-level
`kiosk_mode` block, added the same way, and is exposed to the same risk: any dashboard carrying one
can lose its kiosk chrome silently the next time someone opens it in the graphical editor, without
touching YAML mode at all (the now-retired standalone domain dashboards had the same exposure; see
[native-dashboards-retired.md](native-dashboards-retired.md)). Recorded as
[ADR-0061](../adr/0061-kiosk-mode-lost-on-gui-edit-reapply-dont-prevent.md), since the practical
mitigation is procedural (re-check and reapply after any GUI edit to a kiosk_mode-bearing dashboard)
rather than something fixable in the block's own config.

Re-applied with the same script used originally, now promoted from a scratch one-off into
`scripts/add-kiosk-mode.py` in this skill, since ADR-0061's mitigation is exactly "reapply after
every GUI edit" and that deserves a real tool rather than a rewritten one-liner each time. Reverified
present in the same read that confirmed the clock and Upcoming Events changes from the same session
were untouched by the loss.

## Verification

Confirmed by reading `dashboard-office`'s saved config back over the WebSocket API immediately
after the save: the `kiosk_mode` block round-tripped exactly as written, `users: ["Office"]` with
both flags `true`.

Not confirmed live in a browser as the `office` user. There's no stored password or long-lived
token for that account (unlike `Homie Dashboard`, which had its own dev token already on hand for
exactly this kind of check), and generating one wasn't done without asking first. Whoever verifies
this next should either get temporary `office` credentials or watch the physical Office display
directly, and confirm what `homie-dash`'s fix confirmed: the header and sidebar are actually gone
for that account, and an admin session (`Pete`) is unaffected.
