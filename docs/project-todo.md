# Project TODO

A live, ordered backlog for ongoing Home Assistant and Homie Dashboard work.
Unlike most files in this archive, this one is meant to be mutated in place
rather than treated as a historical record: items get reordered, added, or
removed as work happens. This is a notepad, not a work tracker: when an item
is done, or cancelled and never coming back, it is deleted outright, not
struck through and left in place with a note. Any reasoning worth keeping
about how or why belongs in a dedicated document elsewhere in the repo, not
in this file.

New items go at the bottom unless told otherwise. Ask before reordering or
removing an item for any reason other than pde saying it's done or cancelled.

1. Fix the A/V speaker selection dropdown
2. More complete Energy panel
3. Fix Overview C floors card's uneven spacing (`.ov3-col3`'s
   `justify-content: space-between` stretches an oversized gap between the
   security and floors cards when no purifier entity is configured; cosmetic,
   found while fixing Overview C's vertical overflow, see
   `homie-dashboard-install-plan.md`)
4. Remove Solar from Homie Dashboard's Screensaver rotation options
   (`ssm-solar`). Same trap as the Startup option removed in the fork's
   `4277ee6` (release `20260808.1`): Solar's fullscreen overlay hides its close
   button and exits by gesture only, and an idle tablet/wallscreen could rotate
   into it unattended with no visible way out. Startup was fixed; Screensaver
   rotation was explicitly left out of scope at the time. See the fork's
   `docs/pdehlke-customizations.md`.
5. Investigate lighting scenes. I have two scenes defined but I don't see them
   anywhere in homie.
6. Water meter monitoring: https://github.com/gunnaraas/watermeter.git
7. Build a remotely accessible Homie Dashboard.
8. `Tablet`'s native more-info dialogs (e.g. from Home's own Lennox thermostat
   cards) have a flat, unblurred backdrop, same root cause as the Pete/Homie
   Dashboard difference documented in `homie-climate-native-dialog.md`:
   `Tablet` is on the `visionos` theme, which sets
   `--ha-dialog-scrim-backdrop-filter: none`. Left alone for now; fix either
   by correcting that theme variable or switching `Tablet`'s theme.
