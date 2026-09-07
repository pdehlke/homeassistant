# Clock dashboard: kiosk chrome

`dashboard-clock` gained a `kiosk_mode` block, scoped to the `office` user (display name "Office"),
hiding both the native top app bar and the sidebar, matching `dashboard-office`'s own treatment.
Built 2026-09-07 on Home Assistant 2026.8.1.

## What changed

```yaml
kiosk_mode:
  user_settings:
    - users: ["Office"]
      hide_header: true
      hide_sidebar: true
```

Added at the root of `dashboard-clock`'s saved config, the same shape as
[office-kiosk-mode.md](office-kiosk-mode.md) and `homie-dash`. `dashboard-clock` has exactly one
view with no title or path, confirmed by reading its config back before making this change, so
there's no tab strip in the header for hiding it to break, the same reasoning that justified both
flags for Office rather than Home's sidebar-only carve-out.

## A wrong scope, caught and fixed same day

First attempt scoped this to `Pete` (the owner admin account) rather than `Office`, misreading
"wrap the Clock dashboard in the same kiosk_mode thing we did for Office" as "hide chrome for
whoever actually views Clock" rather than "extend Office's own no-chrome treatment to this
dashboard too." Caught and corrected immediately: swapped `user_settings[0].users` from `["Pete"]`
to `["Office"]`, verified via config read-back, and re-confirmed live that Pete's own view of
`dashboard-clock` has its header and sidebar back (screenshotted before and after the fix).

Scoping this to `Pete` would have meant paying the same admin-navigation cost noted for the (now
corrected) trade-off: losing his own header/sidebar entry points into editing and navigation while
on the one account he uses for everything else on this instance. Scoping to `Office` avoids that
entirely, matching the reasoning that already justified `Office`'s own dedicated kiosk account:
it's never used for anything else, so hiding chrome for it costs nothing.

Not yet verified live as the `office` user, for the same reason noted in
[office-kiosk-mode.md](office-kiosk-mode.md): no stored password or long-lived token exists for
that account. The read-back confirms the block is saved correctly; whoever next has physical or
credentialed access to `office` should confirm the header and sidebar are actually gone for that
account on `dashboard-clock`, the same outstanding check `office-kiosk-mode.md` already flags for
`dashboard-office` itself.

## Recurrence risk

Same exposure as Office and Homie Dashboard: `kiosk_mode` lives at the root of the saved config,
outside the schema the Lovelace GUI editor knows about, so opening `dashboard-clock` in the
graphical editor for any reason can silently drop this block on save (see
[ADR-0061](../adr/0061-kiosk-mode-lost-on-gui-edit-reapply-dont-prevent.md)). Re-run
`scripts/add-kiosk-mode.py dashboard-clock Office` to restore it if that happens; the script
refuses to run if the block is already present, so it's safe to re-run speculatively as a check.

## Verification

Confirmed by reading `dashboard-clock`'s saved config back over the WebSocket API immediately after
the save: the `kiosk_mode` block round-tripped exactly as written, `users: ["Office"]` with both
flags `true`. Confirmed live in a browser as `Pete` via `playwright-cli` (storage-state file built
from `$HA_TOKEN`, loaded and deleted per this skill's token-safety pattern): with the block scoped
to `Office`, Pete's own view of `dashboard-clock` renders with its header and sidebar present,
unaffected by a `kiosk_mode` block that no longer names his account.
