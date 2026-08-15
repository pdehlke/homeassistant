# Dialog backdrop blur fixed via a per-account theme switch, not a shared-theme fix

The native more-info dialog's backdrop was blurred and dimmed on the `Homie Dashboard` account but
only dimmed, with sharp background text, on `Pete`. Traced to the `visionos` theme never setting
`--ha-dialog-scrim-backdrop-filter`/`--mdc-dialog-scrim-color`, while `noctis` (Homie Dashboard's
theme) does. Rather than fix `visionos` itself (affects every dialog on that theme, everywhere,
not just Homie) or scope a CSS override to just Homie's dialog-open flow, pde resolved it by
switching his own personal account theme from `visionos` to `noctis` — a personal preference
change, not a fix to this fork, `homie-dash`, or the `visionos` theme itself. See
`docs/homie-dashboard/homie-climate-native-dialog.md`.

## Consequences

The `Tablet` kiosk account is still on `visionos` and still has the same flat, unblurred backdrop
on any native dialog it opens, unrelated to anything Homie does. Left open since the fix was
scoped to Pete's own account only.
