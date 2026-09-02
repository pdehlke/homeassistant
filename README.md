# Home Assistant

Notes, planning, and specs for my Home Assistant buildout.

## Contents

### Areas and Entities

- [area-floor-layout.md](docs/areas-and-entities/area-floor-layout.md)

  The area and floor structure of the instance. Why the Garage is modelled as a floor (areas
  cannot nest), why HVAC equipment sits in its own mechanical-closet areas, the areas the Lennox
  integration invented on its own, and why entity IDs still contain old area names.

- [light-entity-strategy.md](docs/areas-and-entities/light-entity-strategy.md)

  How light entities are built before Crestron control exists: template lights backed by an
  `input_boolean` and an `input_number`, created entirely through the config flow. Why
  `switch_as_x` and the `demo` integration were rejected, and what changes when real control
  arrives.

### Crestron

- [crestron-strategy.md](docs/crestron/crestron-strategy.md)

  The migration plan for lighting, audio, the alarm system, and HVAC from the existing Crestron
  system (MC2E, AADS, CLX-* lighting modules, TSW-752 panels) to Home Assistant. Options
  considered per subsystem, what was rejected and why, and the phased plan of attack.

- [crestron-migration.md](docs/crestron/crestron-migration.md)

  The investigation behind the strategy above: hardware inventory, evaluation of a prior
  AI-generated set of notes against Crestron's own documentation (separating confirmed claims
  from a fabricated tool reference), and direct verification done over telnet and by physical
  inspection.

- [cresnet-frame-decode.md](docs/crestron/cresnet-frame-decode.md)

  What the Cresnet bus frames actually mean, decoded from the first live capture: the three-byte
  keypad button and LED format, the `1D` CLX channel command with its (channel, level) arguments,
  the readings that were rejected, and the partial CLX channel map that fell out of it. Why a
  keypad press and a touch panel press put different things on the wire, and why that means a
  touch panel capture alone cannot define a load's endpoint. Assesses whether this class of
  capture is sufficient to start Path B, and what is still missing.

- [crestron-eisc-join-discovery.md](docs/crestron/crestron-eisc-join-discovery.md)

  How to read the lighting control interface that already exists. The MC2E-AADS EISC link carries
  every lighting command and every state change in both directions, with feedback originating from
  real device state rather than echoed from a command. The passive, repeatable discovery method
  using the processor's own `SDEBUG` output alongside a bus sniffer, the confirmed join map, and
  why the EISC rather than the panel layer is the right observation point.

- [crestron-xpanel-control-path.md](docs/crestron/crestron-xpanel-control-path.md)

  The working read and write path into the lighting system, found on an unoccupied XPanel slot on
  the MC2E. What it exposes, why it reaches only the Kitchen, the CIP digital-join encoding, the
  corrected `1D` frame format, and why Cresnet frame injection was abandoned even though
  transmission itself was proven.

- [crestron-aads-slot-control-path.md](docs/crestron/crestron-aads-slot-control-path.md)

  An untested proposal for driving lights outside the Kitchen, valid only if the AADS is kept
  rather than retired: register on one of the AADS's two abandoned Crestron App slots the way the
  MC2E's abandoned XPanel slot was used. Why the earlier "silent" verdict on those slots does not
  hold, why write-only stops being a defect once the goal is control rather than observation, and
  why join-sweeping the AADS is dangerous in a way it was not on the MC2E.

- [crestron-apex-control-plane.md](docs/crestron/crestron-apex-control-plane.md)

  Feasibility of a bidirectional Home Assistant to Crestron to Apex Destiny 6100 alarm control
  plane. Why Cresnet sniffing is not the mechanism that unlocks it, why an XSIG interface added
  to the existing AADS program exposing its Apex arm/disarm/status signals is the cleanest
  route, and where the fallback reverse-engineering targets are if that's not enough. Parked, and
  its mechanism is now known to be wrong; read the next entry before quoting it to anyone.

- [crestron-alarm-open-questions.md](docs/crestron/crestron-alarm-open-questions.md)

  Alarm findings parked until lighting is finished, plus the one alarm rule that stays in force
  meanwhile: never press unknown joins on the AADS, because its program carries a virtual keypad
  across eight partitions. Records what the AADS's compiled program actually contains, why its DSC
  PowerSeries modules sit oddly against a visually confirmed Apex Destiny panel, the three readings
  of that contradiction, and the read-only tests that would settle it.

- [crestron-xsig-programmer-scope.md](docs/crestron/crestron-xsig-programmer-scope.md)

  The scope of work for the Crestron programming contractor, cut down once a working control path
  was found: extend lighting control from the Kitchen to the remaining thirteen rooms on a stable,
  documented join contract. Why source recoverability is the gating question, what a compiled
  2-Series program can and cannot give back, and why the alarm and A/V work is now priced
  separately.

### Device Alerts

- [fridge-failure-alert.md](docs/device-alerts/fridge-failure-alert.md)

  The automation that alerts when the fridge stops drawing power. How it works, why it
  measures accumulated running time instead of using a state trigger, and what is still
  needed to get the alert onto a phone.

- [roborock-status-mqtt-stall.md](docs/device-alerts/roborock-status-mqtt-stall.md)

  Why the Q5 Max+'s charging/status entities freeze for hours after the vacuum actually finishes
  charging: a known upstream bug where the integration's MQTT push channel stalls while its
  separately-polled entities (battery, consumables) keep updating fine. The periodic-reload
  automation tried first, and the strategy change that replaced it: deriving Overview A/B's status
  pill from battery and cleaning state instead of trusting the fields proven to get stuck.

- [roborock-maintenance-alerts.md](docs/device-alerts/roborock-maintenance-alerts.md)

  Separate in-app reminders for the Q5 Max+'s main brush, side brush, air filter, and sensor-cleaning
  countdowns. Covers stable notification IDs, automatic dismissal after counter reset, unavailable
  sensor handling, and why dock maintenance is excluded.

- [media-player-restart-recovery.md](docs/device-alerts/media-player-restart-recovery.md)

  Automation and helper script that reload any `media_player` left `unavailable` after an HA
  restart and notify in-app if that doesn't fix it. Covers the 2026-08-15 outage that prompted it,
  and a `continue_on_error` dead end that looked right and wasn't: some integrations reject reload
  in a way that flag doesn't catch, fixed with a fire-and-forget helper script instead.

### Energy

- [low-grid-export-alert.md](docs/energy/low-grid-export-alert.md)

  A daily 7 AM automation checking net solar export (Sense's `to_grid` minus `from_grid`) for the
  prior day: a persistent notification when net export is under 20 kWh, plus a push to Pete's
  iPhone when the house was a net importer for the day. Why `daily_to_grid` alone can never go
  negative and the net figure was used instead, and why `recorder.get_statistics` was used over
  a Utility Meter helper, which isn't installed on this instance.

### Rachio

- [rachio-zone-disabled-alert.md](docs/rachio/rachio-zone-disabled-alert.md)

  Four automations: three that alert when a Rachio zone or valve disappears from Home Assistant,
  when the Main Irrigation controller's standby mode turns on, or when the separate battery-powered
  Back Yard Smart Hose Timer goes offline or reports low battery, and one that reloads the Rachio
  config entry hourly so the others ever have something new to detect. Why a disabled zone's entity
  goes stale rather than flagging itself, the baseline-diff detection design, a source-level
  investigation into why the mechanism needs a periodic forced reload to ever see a real disable at
  all, a reload-driven race condition that caused recurring false-positive alerts and its fix, a
  live current-state red-dot indicator distinct from the diff logic, and the Back Yard automation's
  verification against a real battery pull.

- [rachio-webhook-responsiveness-plan.md](docs/rachio/rachio-webhook-responsiveness-plan.md)

  Revisiting two Rachio limitations once Home Assistant Cloud made this instance internet-reachable:
  zone on/off staleness (fixed by the webhook becoming deliverable) and disabled-zone detection
  latency (not fixed by it, since HA's `rachio` integration never subscribes to Rachio's
  `DELTA`/`ZONE_DELTA` config-change webhooks). Confirms those event types are live via Rachio's
  authenticated API but carry no field-level diff, only a "something changed, go re-fetch" signal,
  which caps how much a native webhook integration would actually buy over the existing reload.
  Records what was scoped, what shipped instead (the false-positive fix in
  [rachio-zone-disabled-alert.md](./docs/rachio/rachio-zone-disabled-alert.md)), and what's still open (the homie-dashboard UX, the 15-minute
  reload retiming, the native webhook automation).

### Lennox and Climate Integration

- [lennoxs30-integration.md](docs/lennox-climate/lennoxs30-integration.md)

  How the two Lennox iComfort S30 thermostats (North and South) were brought into Home Assistant
  via the `lennoxs30` HACS integration. IP identification method, the local-mode config used, and
  the recovery steps for when South's un-reserved DHCP lease renews with a new address.

- [lennox-thermostat-alerts.md](docs/lennox-climate/lennox-thermostat-alerts.md)

  Forwarding each Lennox S30 thermostat's own console alert into Home Assistant, with critical
  alerts pushed to a phone and a red-dot indicator added to the Homie dashboard's Climate entry
  points. Why the integration's two alert entities can disagree (the console-accurate `_alert`
  sensor versus the detail-bearing but sometimes-empty `_active_alerts` list), the severity
  thresholds agreed with pde, and the automation and dashboard verification. Also covers a second,
  code-specific automation for reduced-airflow filter reminders (display-only, no phone push) and
  the CLI script for checking either unit's active alert codes directly.

### Native Dashboards

- [native-dashboards-retired.md](docs/native-dashboards/native-dashboards-retired.md)

  Retrospective on Home (`vision-sample`) and the standalone domain dashboards (`dashboard-lights`,
  `dashboard-av`, `dashboard-lennox-home`, `dashboard-alarm-system`): the Crestron-mirrored
  three-level hierarchy they implemented, the presets/scenes/labels/generator design behind them,
  and why the whole pattern was retired in favor of Homie Dashboard. See ADR-0062.

- [office-now-playing-footer.md](docs/native-dashboards/office-now-playing-footer.md)

  A now-playing footer on `dashboard-office` that mirrors Homie Dashboard's Overview A/B widget:
  appears when a Music Assistant player is active, disappears 10s after it stops. Why Homie's
  version can't be copied (compiled app logic, not config), the eight-player-independent-helper
  design the anti-flicker delay actually required once the Template helper UI turned out to have no
  `delay_off` field, and two `mini-media-player` behaviors missing from its published docs.

- [office-news-ticker.md](docs/native-dashboards/office-news-ticker.md)

  An auto-scrolling News card on `dashboard-office` for a display nobody can touch. Why a
  CSS-only styling turned out to be impossible once discrete pause-and-advance was chosen
  (variable article-row heights defeat pure-CSS timed scrolling), why the fix is a small wrapper
  custom card rather than a hand-patched fork of `rss-news-card` itself, and the Playwright
  verification that watched it advance and wrap.

- [office-thermostat-overlay-cards.md](docs/native-dashboards/office-thermostat-overlay-cards.md)

  Replacing `dashboard-office`'s two `thermostat` cards with `custom:more-info-card`, so the
  dial-plus-humidity-plus-chips overlay a `thermostat` card's top-right icon normally hides behind
  a click renders inline instead. Why no native card combination reproduces that layout, the HACS
  install, and the cosmetic wart (a duplicated state-summary row) later fixed with a UIX rule
  hiding `state-card-content`.

- [office-kiosk-mode.md](docs/native-dashboards/office-kiosk-mode.md)

  A `kiosk_mode` block on `dashboard-office`, scoped to the `office` user, hiding the native header
  and sidebar. The same fix already applied to `homie-dash` for the Homie Dashboard user, why it
  gets both `hide_header` and `hide_sidebar` rather than Home's sidebar-only carve-out, and how it
  was silently dropped by the Lovelace UI editor and had to be reapplied (see ADR-0061).

- [office-clock-card.md](docs/native-dashboards/office-clock-card.md)

  Swapping `dashboard-office`'s clock from the native `type: clock` card to `custom:wall-clock-card`
  to get text bigger than the native card's capped `large` size. Why a UIX font-size override was
  rejected in favor of the swap, the sizing chosen by eye against a live screenshot, and a
  console-noise quirk in the installed card version that isn't a real bug.

- [office-upcoming-events-font.md](docs/native-dashboards/office-upcoming-events-font.md)

  Enlarging the event rows on `dashboard-office`'s Upcoming Events card via a UIX rule targeting
  `.single-event-container`, a class found by reading the card's live shadow DOM rather than
  guessed from its docs, and why it grows the event text without touching the card's own header.

### Synology NAS

- [synology-nas-dashboard.md](docs/synology-nas/synology-nas-dashboard.md)

  Design and live-deployment record for the read-only native Home Assistant dashboard monitoring
  the current Synology appliance's health and capacity, including its shared health-summary
  boundary, focused-trend starting point, and deferred full-observability direction.

- [synology-nas-dashboard-implementation-plan.md](docs/synology-nas/synology-nas-dashboard-implementation-plan.md)

  Ordered implementation, rollback, testing, live deployment, and visual-verification plan for the
  standalone dashboard and shared health sensor.

### Music Assistant

- [genre-browse-misclassification.md](docs/music-assistant/genre-browse-misclassification.md)

  Why the Genres browse page filed Front 242, Patti Smith, and other new-wave/goth/post-punk
  artists under Classical and Experimental: a bundled alias table wrongly mapped the bare tag
  "Alternative" to both. Fixed live via Music Assistant's Promote Alias feature; includes the
  before/after verification and the API calls used to build, then delete, the playlist-based
  workaround that preceded the real fix.

- [homeii-music-flow.md](docs/music-assistant/homeii-music-flow.md)

  Replacing the Sound dashboard's cards with the HOMEii Flow Music Assistant card. Why the
  wall clock moved to its own dashboard instead of Overview, why the view had to be `panel`
  instead of `sections`, and why Sendspin and library artwork are blocked in Chrome by Local
  Network Access.

- [music-assistant-dashboard-scratchpad.md](docs/music-assistant/music-assistant-dashboard-scratchpad.md)

  Candidate community Lovelace cards considered for a Music Assistant dashboard beyond HOMEii
  Flow: the Music Assistant Player Card, Yet Another Media Player, Mediocre Media Player Cards,
  and Maxi Media Player, with what each offers and where to find it.

### Homie Dashboard

- [homie-dashboard-install-plan.md](docs/homie-dashboard/homie-dashboard-install-plan.md)

  The installed Homie Dashboard architecture, security model, fork location, deployment workflow,
  accepted Overview customizations, cache-busting strategy, and checkpoint for continuing work.

- [climate-chip-activity-count.md](docs/homie-dashboard/climate-chip-activity-count.md)

  Fixing the Climate chip's "N on" count on Overview A/B, which counted both thermostats as on
  almost permanently because they stay in `heat_cool` mode nearly always. Now counts only units
  actually heating or cooling, reusing the `hvac_action`-based check Overview C's sidebar glow
  already had, and why the AC card's own on/off toggle deliberately keeps its separate,
  mode-based meaning.

- [climate-alert-dashboard-threshold.md](docs/homie-dashboard/climate-alert-dashboard-threshold.md)

  Raising the Climate chip's red-dot threshold from "any severity other than none" to "moderate or
  critical," matching the phone/persistent_notification bar. Why the original, more permissive
  threshold left the dot lit almost continuously once both real thermostats settled into a
  near-permanent `info` state, and why a per-code ignore-list was rejected in favor of the
  across-the-board fix.

- [overview-c-solar-home-green-percentage.md](docs/homie-dashboard/overview-c-solar-home-green-percentage.md)

  Changing the full-screen Solar view's "Low Carbon" stat from the raw TEP grid green percentage
  to the green share of the home's own consumption, blending solar production with imported grid
  power weighted by each source's share of live usage. The formula, the alternatives rejected
  during a grilling session, and a cache-busting deployment gap the change caught before it shipped.

- [overview-c-solar-today-totals.md](docs/homie-dashboard/overview-c-solar-today-totals.md)

  Adding "% Green Today" and "CO2 Intensity Today" to the full-screen Solar view: an hourly
  time-weighted extension of the instantaneous Low Carbon formula above, why a single current
  reading misrepresents a whole day, the recorder long-term statistics that make the calculation
  possible, and repurposing the two permanently-unbound inverter-temperature placeholders to show
  them.

- [overview-c-alert-triangle-css-bug.md](docs/homie-dashboard/overview-c-alert-triangle-css-bug.md)

  Why Overview C's bottom-left alert triangle showed with no active alerts while Overview A/B
  correctly stayed hidden: a CSS specificity tie between two equally-specific selectors, resolved
  by source order rather than the intended `.visible` toggle. The fix, and why reordering the CSS
  instead of raising specificity was rejected as more fragile.

- [homie-thermostat-control-fix.md](docs/homie-dashboard/homie-thermostat-control-fix.md)

  Post-mortem on the Main House thermostat launcher and overlay, which displayed plausible values
  and moved an on-screen number without ever reaching the real Lennox thermostats. What was
  actually wrong (a Home Assistant service-schema requirement and a silently-dropped step size,
  both invisible to normal error handling), the fixes rejected along the way, and two mistakes the
  fix itself made that only live browser verification caught.

- [climate-idle-target-fallback.md](docs/homie-dashboard/climate-idle-target-fallback.md)

  Why the Climate overlay showed Main House's target as 70°F instead of the real 78°F: a
  dual-setpoint band with no actively reported bound (hvac_action idle, the normal resting state)
  fell back to the band's midpoint instead of a real setpoint. The fix (nearest bound to current
  temperature) and the alternatives rejected, including why the same fallback in the temperature
  *adjustment* path was deliberately left alone.

- [climate-history-graph-feasibility.md](docs/homie-dashboard/climate-history-graph-feasibility.md)

  Feasibility analysis for project-todo item 1's temperature/humidity history graph, superseded
  by [homie-climate-native-dialog.md](./docs/homie-dashboard/homie-climate-native-dialog.md) below: confirmed no charting library was needed, since
  Overview C's Weather and Solar cards already had two proven hand-rolled SVG charts to combine,
  but the item turned out not to need building at all once the Climate overlay opens HA's real
  dialog, which already has the graph. Kept as the record of what combining those two charts
  would have taken under the approach in place at the time.

- [homie-climate-native-dialog.md](docs/homie-dashboard/homie-climate-native-dialog.md)

  Why the Climate overlay's hand-rolled dial/+-/mode/preset/fan/humidity controls, a
  reimplementation of Home Assistant's own climate more-info dialog, silently broke their own
  +/- twice in five days, and why the fix was to stop reimplementing that dialog and instead
  open the real one: Homie's iframe is same-origin with the parent HA frontend, so it dispatches
  the same `hass-more-info` event HA's own cards use internally. What was deleted, the options
  rejected (a nested iframe to a dedicated dashboard, continuing to hand-roll), and how this
  resolved project-todo item 1's history-graph request for free.

- [homie-scenes-chip.md](docs/homie-dashboard/homie-scenes-chip.md)

  Why pde's HA scenes never showed up as a bottom-row chip, and why the first working version
  wasn't the end of it: a stock Homie Dashboard Scenes mechanism that was simply never
  configured, a service-domain mismatch (the popup fires `automation.trigger`, not
  `scene.turn_on`) worked around first with a wrapping automation, then removed entirely once a
  real toggle was needed. The design derives a scene's on/off state live from the entities it
  controls, shown with the same glow/count Lights and Climate already use at the chip, the
  Overview C sidebar, and the popup bubble itself, and toggling off turns those entities off
  directly since HA scenes have no reverse action of their own. Every scene entry was then
  refactored from a single entity to an array so one bubble ("Primary Suite Evening") can group
  and toggle multiple scenes (Bedroom, Bathroom) at once, with their affected entities
  de-duplicated. A missing sidebar icon override and a live token-splice deploy mistake, both
  found and fixed along the way.

- [overview-c-calendar-google-sync.md](docs/homie-dashboard/overview-c-calendar-google-sync.md)

  Plan for adding pde's Google Calendar to Overview C's calendar card alongside Rachio's
  schedule: the OAuth consent-screen setup for his legacy free Google Workspace account
  (Internal vs. External, and the 7-day refresh-token trap in Testing status), the config-only
  deploy once entities exist, and why the Wahoo SYSTM workout calendar was investigated and
  deferred rather than built, since every route found relies on reverse engineering that Wahoo's
  API Agreement prohibits.

- [homie-music-chip.md](docs/homie-dashboard/homie-music-chip.md)

  A "Music" chip parallel to the Scenes chip above, but for radio listening: six pre-configured
  station bubbles that play through Music Assistant on the Crestron media player and toggle back
  off (stop) on a second tap. On-state is derived live from the player's own state and
  `media_content_id`, the same no-separate-tracking principle Scenes established. Decisions from
  grilling before any code was written: off means stop, not pause; volume only resets when the
  player wasn't already playing, so switching directly between two stations leaves the volume
  alone; no "N on" count badge, since at most one station can ever be on; and why every station
  uses its `library://` URI rather than mixing in the native SiriusXM form for two of them. Includes
  a same-day follow-up round lowering the reset volume and shortening five of six station labels.

- [homie-dynamic-playlists.md](docs/homie-dashboard/homie-dynamic-playlists.md)

  Replaces the Music chip's hand-maintained Playlists array with a periodically-synced list of
  Jellyfin-sourced Music Assistant playlists. Why the Jellyfin-vs-MA-builtin distinction needs MA's
  own `provider_mappings` field (not the HA-side `get_library` service, which has no provider
  field at all), the sync script and dashboard-side merge that are built and verified, and the
  still-unsolved scheduling problem: a first attempt scheduled it via cron inside the SSH & Web
  Terminal add-on, which turned out to do nothing at all, since no `crond` process actually runs
  in that container.

- [homie-nas-chip.md](docs/homie-dashboard/homie-nas-chip.md)

  An admin-only "NAS" chip reproducing the live native `dashboard-nas` Overview inside Homie Dash:
  health hero, capacity/temperature tiles, a health-checks list, system context, and a conditional
  Open DSM link. Visibility is a live cross-frame read of the real logged-in HA user's admin flag,
  not a device toggle, since the chip must never appear on the shared kiosk tablet. Chip glow reuses
  the existing `.chip.on` mechanic but with a fixed color rather than the active theme's accent, so
  a real Attention/Critical state can't render as reassuring green. Verified live both directions
  (admin and the kiosk account) against the real instance; a real popup-overflow bug was found and
  fixed before pde's review, not after.

- [homie-mobile-reimplementation.md](docs/homie-dashboard/homie-mobile-reimplementation.md)

  Paused mid-design record of a mobile-first rebuild of Homie Dashboard's functions: the code
  audit and Playwright evidence showing the existing fork was never architected for a phone
  viewport, why a new build was chosen over a retrofit, the no-single-user auth requirement, and
  the still-unanswered questions (wife's phone platform, and whether "native" needs more than a
  PWA can give) it's waiting to resume from. Tracked as issue #13.

### Cloud and Remote Access

- [nabucasa-remote-ui-dns-fragility.md](docs/nabucasa-remote-access/nabucasa-remote-ui-dns-fragility.md)

  Why Home Assistant Cloud's remote UI setup got permanently stuck after one DNS hiccup: a
  mistyped fallback nameserver (fixed) plus a source-level fragility in `hass_nabucasa`'s
  certificate handler, which has no retry and no backoff and gives up for good on the first
  transient failure. Includes the exact file/line locations worth reporting upstream and an
  independent reproduction that caught real, brief DNS packet loss during Core's own startup
  burst.

### Authentication

- [trusted-networks-auto-login.md](docs/auth/trusted-networks-auto-login.md)

  How the Office wall display Pi logs itself in as the `office` user with no login screen, using
  the `trusted_networks` auth provider mapped to one `/32`. Why each key in the block matters,
  including the one that would have removed password login for everyone if left out, how the
  setting hinges on Home Assistant's trusted proxies list being scoped to the Caddy proxy alone,
  the token-provisioning and manual-login alternatives that were rejected, and the trade-off of
  making an IP address the credential.

### Networking

- [hostname-migration-to-ehlke-net.md](docs/networking/hostname-migration-to-ehlke-net.md)

  Retiring `homeassistant.local`/`mass.local` (mDNS) for `hass.ehlke.net`/`mass.ehlke.net` (real
  DNS to the same LAN address), after a literal-IP workaround for a Fire HD tablet's missing mDNS
  resolver caused a cross-origin CORS bug that broke Overview C's Solar card, and Music Assistant
  image proxying, for any client other than that one tablet. The wrong first diagnosis, the
  screenshot that corrected it, and what's still open.

- [caddy-reverse-proxy.md](docs/networking/caddy-reverse-proxy.md)

  Home Assistant and Music Assistant moved behind a name-based Caddy reverse proxy, landing
  alongside the Proxmox migration below; the old `:8123`/`:8095` ports no longer work at all.
  Launched on plain HTTP, then automatic HTTPS (real Let's Encrypt certificates) went live the
  same day. What was verified live, every doc/skill/homie-dashboard file it touched, and what's
  still open.

### Hardware

- [mac-mini-migration.md](docs/hardware/mac-mini-migration.md)

  Superseded plan for moving Home Assistant off its Raspberry Pi 4 onto a surplus headless Late
  2014 Mac mini via a bare-metal HAOS install. The migration happened, but as a Proxmox VE
  virtualized install instead (see [caddy-reverse-proxy.md](docs/networking/caddy-reverse-proxy.md) above); this document's
  own storage and SSD research is preserved, annotated with which parts turned out to matter and
  which didn't.

### EV Charger

- [ev-charger-integration.md](docs/ev-charger/ev-charger-integration.md)

  Inventory of the garage OpenEVSE charger's `openevse` integration: what's live, the 22
  disabled-by-default diagnostic and load-shaper entities, and capabilities like solar-aware
  divert charging and peak-rate throttling that the integration supports but nothing in this
  instance uses yet.

### Harmony Hub

- [harmony-hub-integration.md](docs/harmony-hub/harmony-hub-integration.md)

  Inventory of the Living Room Logitech Harmony Hub's `harmony` integration: the two-entity
  activity/remote setup actually live, and capabilities like a Universal media player wrapper,
  direct per-device commands to the five devices other than the Integra receiver, and the
  `harmony.change_channel`/`harmony.sync` actions that nothing in this instance uses yet.
- [homie-tv-volume-mute-controls.md](docs/harmony-hub/homie-tv-volume-mute-controls.md)

  How Homie Dash's TV chip got volume up/down and mute buttons: the live capability check that
  confirmed `remote.send_command` reaches the Integra receiver's volume before any UI was
  written, the layout/feedback/off-state decisions made and rejected, and how it was verified.

### Meta

- [CONTEXT.md](CONTEXT.md)

  The domain glossary for this instance: canonical terms for the native dashboards, the Homie
  Dashboard fork, and the Crestron, Lennox, Rachio, Music Assistant, Harmony Hub, EV charger, and
  networking subsystems, with explicit `Avoid` entries where two documents used the same word
  differently. Built via a `/grill-with-docs` session; see [docs/agents/domain.md](./docs/agents/domain.md) for how agent
  skills are expected to consume it.

- [docs/adr/](docs/adr/)

  Architecture decision records: short, sequentially numbered writeups of individual hard-to-reverse
  decisions from across every subsystem, each citing the fuller topic document it was drawn from.
  Backfilled from a [CONTEXT.md](./CONTEXT.md) domain-modeling session; genuinely open questions are deliberately
  left out rather than recorded as settled.

- [CLAUDE.md](CLAUDE.md)

  Repo conventions for coding agents. Meta, rather than documentation about Home Assistant.

- [docs/agents/issue-tracker.md](docs/agents/issue-tracker.md)

  Where issues for this repo live (GitHub Issues, via `gh`) and the conventions agent skills use
  to read and write them.

- [docs/agents/triage-labels.md](docs/agents/triage-labels.md)

  Maps the five canonical triage roles used by the `triage` skill to this repo's actual label
  strings. Currently the defaults, unchanged.

- [docs/agents/domain.md](docs/agents/domain.md)

  Consumer rules for this repo's domain docs ([CONTEXT.md](./CONTEXT.md), `docs/adr/`) and the single-context
  layout in use.

- [.claude/skills/home-assistant/](.claude/skills/home-assistant/SKILL.md)

  The coding-agent skill for working with this instance and its Music Assistant add-on: which
  of the REST, WebSocket, and MCP access paths to use for a given job, instance quirks, and
  scripts for safe Lovelace edits and dashboard regeneration. Repo-scoped rather than a
  user-scoped dotfiles skill, since it is specific to this instance.

- [.claude/skills/verify-home-assistant/](.claude/skills/verify-home-assistant/SKILL.md)

  The coding-agent skill for proving an automation, script, or notification actually works on
  this live instance: trigger it for real, read its trace, and confirm the effect, with a
  read-only doctor check and a maintained feature map. Companion to `home-assistant` above;
  covers verification specifically, not general access. The equivalent skill for Homie
  Dashboard's own tablet UI, `verify-homie-dashboard`, lives in the sibling
  `pdehlke/homie-dashboard` repo instead, since it is that repo's own code being verified.
