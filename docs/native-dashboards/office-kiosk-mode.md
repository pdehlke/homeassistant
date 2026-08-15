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
(display name, not username; see [dashboard-home.md](dashboard-home.md)'s "Kiosk chrome" section
for the plugin background). This is the same fix already applied to `homie-dash` for the `Homie
Dashboard` user, see
[homie-dashboard-install-plan.md](../homie-dashboard/homie-dashboard-install-plan.md)'s "Overview C
vertical overflow" section.

## Why both `hide_header` and `hide_sidebar`, not `hide_sidebar` alone

`dashboard-home.md` documents a real exception to the usual both-flags pattern: Home is a
multi-view dashboard whose native header carries the tab strip, so hiding the header there would
have taken the only navigation between tabs with it. `dashboard-office` doesn't have that problem.
Its saved config has exactly one view (confirmed by reading it back over the WebSocket API before
making this change: `views` is a one-element array with a null `title`/`path`, i.e. no tab
navigation for a hidden header to break). It is a single-screen kiosk display, the same shape as
`homie-dash`, so it gets the same both-flags treatment `homie-dash` uses rather than Home's
sidebar-only carve-out.

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
