# No timeout or safety net on the dialog-open helper getting stuck "on"

If `input_boolean.homie_native_dialog_open` ever gets stuck "on" (a torn-down tab, an unreachable
parent frame after a future HA change), nothing turns it back off until the next dialog open/close
cycle or a page reload, leaving the sidebar and header hidden. Deliberately left unengineered, on
pde's explicit call: it matches the fail-silently-no-fallback approach the cross-frame dialog
dispatch itself already uses, since there is nothing else the code could reliably do, and the
failure mode (a visibly missing sidebar) is easy to notice and self-corrects. See
`docs/homie-dashboard/homie-climate-native-dialog.md`.
