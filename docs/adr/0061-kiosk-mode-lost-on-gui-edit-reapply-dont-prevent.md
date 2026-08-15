# kiosk_mode is silently dropped by the Lovelace UI editor; reapply after edits, don't try to prevent it

`dashboard-office`'s `kiosk_mode` block (root-level, sibling of `views`) disappeared between being
verified live and the next unrelated read, with no `lovelace/config/save` call from any script in
between. Confirmed by pde: he had the dashboard open in the Lovelace UI editor in that window,
just looking at an unrelated card change, not touching `kiosk_mode` itself. See
[office-kiosk-mode.md](../native-dashboards/office-kiosk-mode.md)'s "Recurrence" section for the
full account.

`kiosk_mode` is a HACS frontend plugin's own config namespace; nothing in HA's own dashboard schema
knows it exists. The GUI editor's save path evidently reconstructs the config from its own model
rather than round-tripping the full object the way `lovelace/config/save` does when driven directly
over the WebSocket API, so a key the model doesn't know about doesn't survive a GUI-triggered save.
This applies to every dashboard on this instance carrying a root-level `kiosk_mode` block:
`homie-dash`, the standalone domain dashboards, and `dashboard-office`, not just the dashboard where
it was first noticed.

**Decision: treat this as a fact about how the GUI editor works, and reapply after the fact, rather
than trying to prevent it.**

Rejected: switching the affected dashboards to YAML mode, which is immune to this because YAML-mode
dashboards aren't rewritten by the storage-mode editor at all. Rejected because YAML mode is set in
`configuration.yaml`, and this machine has no filesystem access to the Pi's `/config` and no
documented API for editing `configuration.yaml` (same constraint noted throughout this skill for
anything requiring direct file access). Not reachable from here.

Rejected: telling pde not to open these dashboards in the GUI editor. Not realistic; editing
dashboards through the GUI is the normal way to work, and asking him to route around his own tools
to protect a plugin's config block is a worse trade than just re-running a script afterward.

Deferred, not rejected: a periodic check (an automation or a scheduled script run comparing the
live `kiosk_mode` block against expected) that would catch this without waiting for someone to
notice the chrome is back. Not built now because it wasn't asked for and the instance is still young
enough that "notice it looks wrong, run the script" has been fast in practice; worth reconsidering if
this recurs enough to be annoying rather than rare.

Mitigation that does exist: `scripts/add-kiosk-mode.py` in this skill, promoted from a scratch
one-off specifically because this is expected to happen again. Re-run it with the same dashboard and
display name any time a kiosk_mode-bearing dashboard has been opened in the GUI editor and the chrome
looks wrong afterward.
