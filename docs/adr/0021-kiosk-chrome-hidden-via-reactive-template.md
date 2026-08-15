# Hide HA's chrome only while a native dialog is open, via a reactive kiosk_mode template

Opening HA's native more-info dialog from Homie exposed HA's own sidebar/header behind it for any
account other than the always-hidden `Homie Dashboard` kiosk user (pde's own admin browsing
included), reading as having left the dashboard entirely. Dropping `kiosk_mode`'s per-user
`hide_header`/`hide_sidebar` filter permanently was rejected outright by pde: it would mean losing
admin nav chrome on every visit, not just while a dialog is open. Instead, `NemesisRE/kiosk-mode`'s
support for a live reactive template condition drives the same hide rule for every account: a
dedicated `input_boolean.homie_native_dialog_open` helper, turned on right before the dialog opens
and off when HA's own `dialog-closed` event fires. See
`docs/homie-dashboard/homie-climate-native-dialog.md`.
