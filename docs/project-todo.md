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
   [homie-dashboard-install-plan.md](./homie-dashboard/homie-dashboard-install-plan.md))
4. Remove Solar from Homie Dashboard's Screensaver rotation options
   (`ssm-solar`). Same trap as the Startup option removed in the fork's
   `4277ee6` (release `20260808.1`): Solar's fullscreen overlay hides its close
   button and exits by gesture only, and an idle tablet/wallscreen could rotate
   into it unattended with no visible way out. Startup was fixed; Screensaver
   rotation was explicitly left out of scope at the time. See the fork's
   `docs/pdehlke-customizations.md`.
5. Water meter monitoring: https://github.com/gunnaraas/watermeter.git
6. Build a remotely accessible Homie Dashboard.
7. Confirm `sync-homie-playlists.py`'s new cron job (in the SSH & Web Terminal add-on's own
   container, see [homie-dynamic-playlists.md](./homie-dashboard/homie-dynamic-playlists.md))
   actually fires and succeeds on its own at the next 00:00 or 12:00 UTC boundary
   (`/config/.homie-playlists-sync.log`, `sensor.homie_dynamic_playlists`'s `last_updated`) — the
   crontab line is installed but a full unattended run was never observed end to end.
8. Make the playlist-sync cron job durable across an SSH add-on update: add `py3-aiohttp` to that
   add-on's `packages` option and the crontab line to its `init_commands` option (Settings >
   Add-ons > Advanced SSH & Web Terminal > Configuration). Both currently live only in the running
   container's own overlay and would be lost if that container is ever recreated. See
   [homie-dynamic-playlists.md](./homie-dashboard/homie-dynamic-playlists.md).
