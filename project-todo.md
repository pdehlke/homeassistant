# Project TODO

A live, ordered backlog for ongoing Home Assistant and Homie Dashboard work.
Unlike most files in this archive, this one is meant to be mutated in place
rather than treated as a historical record: items get reordered, completed, or
added as work happens. When an item is finished, it moves out of this list; the
reasoning behind how it was done belongs in a dedicated document of its own (and
this file links to it once one exists).

New items go at the bottom unless told otherwise. Ask before reordering or
removing an item for any reason other than completing it.

1. Fix the A/V speaker selection dropdown
2. Fix Overview C calendar entries
3. Overview A irrigation indicator (not a Homie/HA config bug: Rachio's HA
   integration needs an inbound webhook to learn real-world zone state, this
   instance has no `external_url` and isn't internet-reachable, so zone switches
   never update after the initial toggle. Confirmed live: a zone run triggered
   directly from the Rachio app, bypassing Homie entirely, still left
   `switch.main_irrigation_east_of_garage` reporting stale `off` in HA
   throughout the run. Fix requires making HA internet-reachable. Options: Nabu
   Casa Cloud (paid, auto-configures the webhook, no open port), a self-hosted
   tunnel like Cloudflare Tunnel (no open port, more DIY/maintenance), manual
   port-forward + `external_url` (free, opens an inbound port), or leave zone
   control one-way and just document the limitation)
4. ~~Tesla inverter integration~~ Cancelled 2026-08-09: not happening. The two `— °F`
   placeholders it was reserved for have been repurposed into "% Green Today" and "CO2
   Intensity Today"; see `overview-c-solar-today-totals.md`.
5. More complete Energy panel
6. Investigate empty weather card
7. Fix Overview C floors card's uneven spacing (`.ov3-col3`'s
   `justify-content: space-between` stretches an oversized gap between the
   security and floors cards when no purifier entity is configured; cosmetic,
   found while fixing Overview C's vertical overflow, see
   `homie-dashboard-install-plan.md`)
8. Remove Solar from Homie Dashboard's Screensaver rotation options
   (`ssm-solar`). Same trap as the Startup option removed in the fork's
   `4277ee6` (release `20260808.1`): Solar's fullscreen overlay hides its close
   button and exits by gesture only, and an idle tablet/wallscreen could rotate
   into it unattended with no visible way out. Startup was fixed; Screensaver
   rotation was explicitly left out of scope at the time. See the fork's
   `docs/pdehlke-customizations.md`.
9. Investigate lighting scenes. I have two scenes defined but I don't see them
   anywhere in homie.
10. Water meter monitoring: https://github.com/gunnaraas/watermeter.git
11. ~~Decide whether to add a periodic `homeassistant.reload_config_entry` automation for the
    Rachio integration.~~ Done 2026-08-08: `automation.rachio_periodic_config_entry_reload`
    reloads the entry every hour, on pde's explicit call (hourly rather than the doc's recommended
    15-30 minutes, since a webhook fix may make this moot soon; see `rachio-zone-disabled-alert.md`).
