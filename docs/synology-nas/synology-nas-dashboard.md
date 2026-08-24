# Synology NAS dashboard

The Synology NAS dashboard is a read-only, native Home Assistant dashboard for monitoring the
current Synology appliance's health and capacity. Its primary use is the owner's authenticated
desktop or mobile Home Assistant session. A Homie Dashboard chip may follow after the standalone
dashboard is proven live, but it is not part of the initial implementation.

## Verified baseline

Before deployment, the live Synology DSM integration had 39 registered entities, 29 of them
enabled. They covered system and drive health, capacity, temperature, CPU, memory, throughput, fan
mode, DSM update status, restart, and shutdown. Home Assistant's
[Synology DSM documentation](https://www.home-assistant.io/integrations/synology_dsm) confirms that
the integration polls every 15 minutes by default and that polling wakes a hibernating NAS. The live
integration has no custom polling interval configured, so the default applies.

## Decisions

| Decision | Chosen direction | Alternatives rejected or deferred |
|---|---|---|
| Primary job | Health and capacity at a glance | Performance diagnostics, backup assurance, and operations are not the initial focus. |
| Primary user | Owner on authenticated desktop or mobile HA | Fire HD and Office kiosk use are not the primary context. |
| System boundary | Current Synology appliance only | A broader storage-reliability or home-infrastructure dashboard would expand scope prematurely. |
| Controls | Read-only | Fan-mode, restart, shutdown, and update actions remain outside the dashboard. |
| Dashboard surface | Native storage-mode Home Assistant dashboard | A custom HTML application and a DSM-hosted page would duplicate HA authentication, history, and entity access. |
| Dashboard identity | `Synology NAS`, `dashboard-nas`, and `mdi:nas` | `NAS` is less explicit. A model-specific title would become stale after hardware replacement. |
| Visibility | Show in the sidebar and require an administrator | All-authenticated visibility is unnecessary for the owner-focused use case. A hidden dashboard would be harder to reach. |
| Theme | Inherit the active user's theme | Pinning Noctis would override user preference. A dedicated NAS theme would add unnecessary maintenance. |
| Information architecture | Separate Overview and Trends views | A single scrolling view would bury health below charts; a dense observability grid would weaken hierarchy and mobile readability. |
| Overview hierarchy | Status first: aggregate health, capacity and temperature, supporting checks, then system context | Equal-weight sections would make ordinary metrics compete with health. An evidence-first table would slow the five-second reading goal. |
| Status emphasis | Keep the active theme dominant and give only the aggregate-health hero a restrained semantic state tint | A fully neutral hero would make abnormal states too easy to miss. Repeating semantic color across status cards would overpower the dashboard. |
| Trends hierarchy | Focused two-by-two grid: storage use, drive temperatures, CPU and memory, and network throughput | A health-weighted stack would require more scrolling. A chart-per-metric wall would prematurely become full observability. |
| Interactions | Sensor cards may open read-only more-info and history; the health hero, update row, and fan-mode row are inert | Making every card inert would hide useful history. Native actions on operational entities would violate the read-only boundary. |
| Entity boundary | Enable both drive SMART statuses, maximum disk temperature, volume total size, and NAS uptime | The five remaining disabled CPU and memory breakdowns duplicate enabled diagnostics. Custom collectors and other integrations are deferred. |
| Polling | Keep the default 15-minute interval | More frequent polling is unnecessary for the initial monitoring goal and would query the NAS more often. |
| Health semantics | One HA-owned summary with Healthy, Attention, Critical, and Unknown states | Raw-only presentation and separate frontend calculations would make the standalone dashboard and later Homie chip disagree. |
| Health implementation | One UI-managed `sensor.nas_health`, attached to the Synology device; supporting cards explain its state | YAML-only reason attributes would be harder to maintain. A second explanation helper would duplicate health logic. |
| Summary inputs | Storage integrity, capacity, Security Advisor, and drive temperature | DSM update availability and CPU, memory, and throughput remain visible information but do not change aggregate health. |
| Temperature | Drive temperature produces Attention at 50°C and Critical at 60°C | Display-only temperature was rejected; applying the DS223 ambient limit to its internal temperature sensor was also rejected. |
| History | 24-hour CPU, memory, and throughput trends; a 30-day default window for capacity and temperature | A full observability dashboard is a possible later direction, not part of the initial build. Longer available history remains reachable through sensor details. |
| DSM navigation | Show a conditional DSM link for Attention, Critical, and Unknown | A permanent link would weaken the monitoring focus. Attention and Critical only may replace the initial rule if Unknown proves noisy in long-term use. |
| Live review | Deploy after design approval; validate Overview, mobile responsiveness, and sparse charts before commit; reassess trend usefulness after seven days | Waiting for accumulated history would delay useful monitoring. Treating the initial sparse trend view as final would leave its usefulness untested. |
| Notifications | Reusable attention state now; notifications later | Initial work will not add persistent or mobile alert automations. |

Home Assistant 2026.8.2's
[Template helper configuration](https://github.com/home-assistant/core/blob/2026.8.2/homeassistant/components/template/config_flow.py)
supports the summary's state, availability, and device association, but does not expose arbitrary
attributes. The Overview supporting cards therefore provide the reason evidence without a second
helper.

## Selected implementation

The live implementation uses one UI-managed Template Sensor plus a native storage-mode Lovelace
dashboard. The helper is attached to the existing Synology device and provides the stable
`sensor.nas_health` contract. Dashboard cards consume that state and the integration's raw
entities. Health logic is not repeated in Lovelace. The two-column layout uses Home Assistant's
[Sections view](https://www.home-assistant.io/dashboards/sections/), including a section spanning
both desktop columns.

Two alternatives remain rejected. A YAML Template Sensor could expose reason attributes, but would
move the helper outside Home Assistant's UI-managed configuration. A frontend-only calculation
would avoid the helper, but the later Homie chip would need a second implementation of the same
rules.

The dashboard registration is:

| Property | Value |
|---|---|
| Title | `Synology NAS` |
| URL path | `dashboard-nas` |
| Icon | `mdi:nas` |
| Mode | Storage |
| Sidebar | Shown |
| Access | Administrators only |
| Theme | Inherit the active user theme |

The Overview view follows the approved status-first hierarchy:

1. One full-width `NAS Health` hero. Four conditional copies provide restrained Healthy,
   Attention, Critical, and Unknown tinting through UIX. The hero has no tap or hold action.
2. Neutral Volume used and Maximum drive temperature tiles.
3. One Health checks card showing volume, Security Advisor, both drive statuses, both SMART
   statuses, bad-sector warnings, and remaining-life warnings. Volume used space and total size
   provide capacity context.
4. Neutral system-context cards for CPU, memory, DSM update availability, uptime, fan mode, and
   internal NAS temperature. Update and fan-mode cards are inert.
5. An `Open DSM` button displayed only while `sensor.nas_health` is Attention, Critical, or Unknown.

The Trends view uses a two-by-two desktop grid that stacks on narrow screens:

| Chart | Window | Entities and statistic |
|---|---:|---|
| Storage use | 30 days | Used space, daily mean |
| Drive temperatures | 30 days | Both drives, hourly maximum |
| CPU and memory | 24 hours | Total CPU and real memory use, raw history |
| Network throughput | 24 hours | Upload and download throughput, raw history |

The two 30-day charts use Home Assistant's
[statistics graph](https://www.home-assistant.io/dashboards/statistics-graph/), which requires source
sensors with a supported state class. Live browser review must still confirm that history exists
for enough of the window to make each chart useful.

Sensor cards retain read-only more-info and history actions. No restart or shutdown entity appears.
No card can invoke update installation or change fan mode. UIX styles only the health hero; no new
`card-mod` configuration is allowed.

## DSM investigation link

The conditional link uses the integration's current device-registry configuration URL,
`https://192.168.4.106:5001`. Home Assistant's
[URL action](https://www.home-assistant.io/dashboards/actions/) opens that destination in a new
browsing context. The browser decides whether that context is a tab or window. Browser reachability,
certificate trust, and external-navigation behavior must be verified during live review.

The link is initially visible for Attention, Critical, and Unknown. Reassess that rule after the
dashboard has real operating history. If transient Unknown states create noise without helping
diagnosis, migrate the trigger to Attention and Critical only.

## NAS health summary rules

Required health inputs are Security Advisor status, volume status and percentage used, maximum disk
temperature, each drive's status and SMART status, and each drive's bad-sector and remaining-life
safety sensors. Volume total size and NAS uptime are displayed but do not change health.

State precedence is Critical, Unknown, Attention, then Healthy:

- **Critical**: a known volume, drive, or SMART status other than `normal`; either drive safety
  sensor on; volume use at or above 90%; or maximum disk temperature at or above 60°C.
- **Unknown**: any required input unavailable, unknown, or non-numeric, unless another known input
  is already Critical.
- **Attention**: Security Advisor on, volume use from 80% through 89.9%, or maximum disk temperature
  from 50°C through 59.9°C.
- **Healthy**: all required inputs are available and none meets another state's conditions.

Synology [recommends keeping volume usage below 80%](https://kb.synology.com/en-eu/DSM/tutorial/How_do_I_check_storage_usage).
The 90% Critical threshold is this project's escalation policy. Seagate specifies 65°C as the
[maximum reported operating temperature](https://www.seagate.com/content/dam/seagate/migrated-assets/www-content/product-content/ironwolf/en-us/docs/100807039u.pdf)
for both installed drive models. The 50°C and 60°C thresholds are project warning margins below
that maximum.

## Deferred full-observability direction

The first dashboard will show focused trends rather than every available metric. After it has been
used and reviewed live, reassess whether focused history answers the real diagnostic questions. A
migration to fuller observability remains explicitly possible. No migration criteria or additional
data sources have been selected yet.

## Deployment, rollback, and acceptance

Before changing live state, capture the selected entities' current registry settings, the dashboard
registry, and confirmation that neither `sensor.nas_health` nor `dashboard-nas` exists. Apply changes
in this order: enable the five selected Synology entities, reload the Synology config entry, create
and verify the Template Sensor, create the dashboard registration, then save and read back the full
dashboard configuration.

Rollback deletes the new dashboard, removes the Template helper's config entry, user-disables the
five source entities, and reloads the Synology config entry. Home Assistant's supported entity
registry API accepts `user` or null for `disabled_by`; it rejects attempts to restore the original
`integration` provenance. Exact provenance restoration would require unsupported storage edits and
is deliberately excluded. No credential or token may be written to the repository, backup,
dashboard configuration, screenshot, or command output.

## Live deployment checkpoint, 2026-08-17

Home Assistant 2026.8.2 now has the approved implementation live. API and WebSocket read-back
verified the following state:

- Dashboard `dashboard_nas` is registered at `dashboard-nas` as storage mode, sidebar-visible, and
  administrator-only. Its saved configuration matched the initial generated two-view configuration
  at deployment.
- UI-managed Template Sensor `sensor.nas_health` belongs to Template config entry
  `01M08E5NG7NVP6KTJSW3MW03WR`, is attached to the existing Synology system device, and reported
  `Healthy` at deployment.
- Both SMART status sensors, maximum disk temperature, volume total size, and NAS uptime are
  enabled and available. The SMART states were `normal` at deployment.
- Overview and Trends paths, the four hero states, three DSM-link states, chart windows, UIX-only
  styling boundary, and absence of restart, shutdown, and service actions all passed
  generated-config tests and initial live configuration read-back.

The first transaction exposed a Home Assistant config-flow behavior worth preserving. Attaching a
Template helper to a device automatically prefixed its generated entity ID with the device name.
The transaction waited for `sensor.nas_health`, timed out, deleted the helper, and did not create a
dashboard. Its attempt to restore `disabled_by: integration` then failed because the supported
registry API rejects that value, so the five intended source entities remained enabled. After an
exact live audit, the deployment artifact gained a regression test and now locates the helper by its
returned config-entry ID, then renames it to the stable `sensor.nas_health` contract. The resumed
transaction completed from the audited enabled-source state.

A post-deployment deep audit found a separate read-only interaction defect. Home Assistant tile
cards give their icons an independent default action. The initial configuration disabled card tap
and hold actions on the health hero, DSM update, and fan-mode tiles, but did not explicitly disable
their icon actions or double-tap actions. An icon could therefore open more-info and expose an
operational surface, contrary to the inert-card contract. Regression tests now require all six card
and icon action variants to be `none`, and the generated configuration passes those tests. The live
dashboard now has the hardened configuration. The hardening command verified the exact initial
dashboard hash before saving, read the corrected configuration back, and would have restored the
initial configuration if verification failed. Live read-back confirms all six action variants are
`none` on the three tiles.

The first hardening attempt was incorrectly reported as a rejected valid token. The actual cause
was command context: the temporary client ran with `/tmp` as its working directory, where this
harness did not pass `HA_TOKEN` to the child process. An inline reassignment then passed an empty
value and produced the misleading WebSocket authentication failure. Running the same temporary
client by absolute path with this repository as its working directory authenticated successfully.
The supported operating rule is now recorded in the Home Assistant skill's API-access reference.

Browser verification remains pending. The local Playwright Chromium and WebKit processes both
aborted under the execution sandbox, and the in-app browser reported no available browser instance.
No desktop or mobile rendering, computed UIX style, interaction, DSM navigation, browser console,
or network result is claimed from that environment. The temporary token-derived browser state was
deleted after those attempts. Initial visual acceptance therefore belongs to the owner's live
desktop and mobile review at `https://hass.ehlke.net/dashboard-nas/overview`.

Initial acceptance requires all of the following. Deployment and hardened-action read-back are
complete; browser items remain open:

- The helper reports Healthy, Attention, Critical, or Unknown according to the documented
  precedence and thresholds.
- The dashboard is storage mode, sidebar-visible, administrator-only, and contains Overview and
  Trends views.
- Desktop and mobile layouts have no clipping, overlap, or horizontal overflow.
- Only the hero receives semantic tinting, and it remains legible in the active theme.
- Sensor details open where allowed; the hero, update, and fan-mode cards remain inert.
- The DSM link is hidden when Healthy and opens the configured DSM URL in a new browsing context
  for the other three states.
- Browser console and network inspection show no new dashboard or UIX errors.
- The complete live configuration is read back after save and matches the intended configuration.

The first live review covers Overview, mobile responsiveness, and sparse-chart behavior. A second
review after seven days decides whether the focused trends are useful and whether the DSM link should
stop appearing for Unknown. No commit is made before initial live visual approval.
