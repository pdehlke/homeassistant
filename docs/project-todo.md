# Project TODO

A live, ordered backlog for ongoing Home Assistant and Homie Dashboard work.
Unlike most files in this archive, this one is meant to be mutated in place
rather than treated as a historical record: items get reordered, completed, or
added as work happens. When an item is finished, it moves out of this list; the
reasoning behind how it was done belongs in a dedicated document of its own (and
this file links to it once one exists).

New items go at the bottom unless told otherwise. Ask before reordering or
removing an item for any reason other than completing it.

1. Add a temperature/humidity history graph to the Climate chip's thermostat
   overlay, matching the history-graph icon on Home Assistant's native climate
   more-info dialog. Deferred out of the 2026-08-11 native-parity overlay
   rebuild (see `homie-dashboard-install-plan.md`'s checkpoint of that date once
   recorded): needs either a charting library or a hand-rolled sparkline against
   the recorder API, real scope and risk beyond that session.
2. Fix the A/V speaker selection dropdown
3. Fix nabucasa fragility: `hass_nabucasa`'s remote-UI/ACME certificate handler
   has effectively no tolerance for a single transient DNS failure and no
   automatic retry once it gives up, so a brief DNS blip at the wrong moment
   permanently wedges remote UI setup until a manual Core restart happens to
   land outside the bad window. Full timeline, root cause, and open items
   (including filing upstream against `NabuCasa/hass-nabucasa`) in
   `nabucasa-remote-ui-dns-fragility.md`.
4. Fix Overview C calendar entries
5. Overview A irrigation indicator (not a Homie/HA config bug: Rachio's HA
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
6. ~~Tesla inverter integration~~ Cancelled 2026-08-09: not happening. The two
   `— °F` placeholders it was reserved for have been repurposed into "% Green
   Today" and "CO2 Intensity Today"; see `overview-c-solar-today-totals.md`.
7. More complete Energy panel
8. Fix Overview C floors card's uneven spacing (`.ov3-col3`'s
   `justify-content: space-between` stretches an oversized gap between the
   security and floors cards when no purifier entity is configured; cosmetic,
   found while fixing Overview C's vertical overflow, see
   `homie-dashboard-install-plan.md`)
9. Remove Solar from Homie Dashboard's Screensaver rotation options
   (`ssm-solar`). Same trap as the Startup option removed in the fork's
   `4277ee6` (release `20260808.1`): Solar's fullscreen overlay hides its close
   button and exits by gesture only, and an idle tablet/wallscreen could rotate
   into it unattended with no visible way out. Startup was fixed; Screensaver
   rotation was explicitly left out of scope at the time. See the fork's
   `docs/pdehlke-customizations.md`.
10. Investigate lighting scenes. I have two scenes defined but I don't see them
    anywhere in homie.
11. Water meter monitoring: https://github.com/gunnaraas/watermeter.git
12. ~~Decide whether to add a periodic `homeassistant.reload_config_entry`
    automation for the Rachio integration.~~ Done 2026-08-08:
    `automation.rachio_periodic_config_entry_reload` reloads the entry every
    hour, on pde's explicit call (hourly rather than the doc's recommended 15-30
    minutes, since a webhook fix may make this moot soon; see
    `rachio-zone-disabled-alert.md`).
13. Build a remotely accessible Homie Dashboard.
