# CSS specificity bug fixed by raising specificity, not reordering the stylesheet

Overview C's alert triangle stayed visible because its hidden-by-default rule
(`.ov3-alert-btn { display: none; }`) and the shared sidebar-button base rule
(`.ov3-sb-btn { display: flex; }`) carried identical single-class specificity, so the
later-declared rule in the file silently won regardless of the `.visible` toggle. Fixed by
changing the hidden rule to the compound selector `.ov3-sb-btn.ov3-alert-btn`, giving it strictly
higher specificity, rather than reordering the stylesheet blocks so the existing rule happened to
come last — reordering would have left the fix fragile against the next person to reorganize the
file. See [docs/homie-dashboard/overview-c-alert-triangle-css-bug.md](../homie-dashboard/overview-c-alert-triangle-css-bug.md).
