# Synology NAS Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and live-verify the approved read-only Synology NAS dashboard and shared NAS health
sensor in Home Assistant.

**Architecture:** Enable five existing Synology integration entities, then create one UI-managed
Template Sensor attached to the existing Synology device. Register a native storage-mode Lovelace
dashboard whose Overview consumes the shared health state and whose Trends view uses native history
and statistics cards. Live Home Assistant owns all deployable configuration; this repository keeps
only the design, plan, and verified operational record.

**Tech Stack:** Home Assistant 2026.8.2 REST and WebSocket APIs, Template integration config flow,
storage-mode Lovelace, native cards, UIX 8.0.1, Python 3 standard-library tests, Playwright CLI.

## Global Constraints

- Use `http://hass.ehlke.net:8123` for Home Assistant API, WebSocket, and browser access.
- Read `$HA_TOKEN` from the environment. Never print or persist it.
- Keep the Synology integration's 15-minute default polling interval.
- Enable only both SMART statuses, maximum disk temperature, volume total size, and uptime.
- Do not expose restart, shutdown, update installation, or fan-mode changes.
- Use UIX for the health hero. Do not add or restore `card-mod`.
- Create `sensor.nas_health` with Critical, Unknown, Attention, Healthy precedence.
- Back up live state before mutation and read back every saved object.
- Do not commit until pde approves the live dashboard visually.
- Do not change the Homie Dashboard fork in this implementation.

---

### Task 1: Finalize the recorded design

**Files:**

- Modify: `docs/synology-nas/synology-nas-dashboard.md`
- Modify: `CONTEXT.md`
- Modify: `README.md`

**Interfaces:**

- Consumes: all approved grilling decisions through Q28.
- Produces: the authoritative design, terminology, alternatives, rollback contract, and acceptance
  criteria used by every later task.

- [x] **Step 1: Record selected implementation and exact view contract**

  Add the UI-managed helper architecture, Overview card order, Trends chart windows, UIX boundary,
  conditional DSM link, and read-only interactions to the design record.

- [x] **Step 2: Record deployment and rollback contract**

  State the mutation order, required backups, supported rollback operations and entity-registry
  provenance limitation, token-handling rule, live verification requirements, seven-day trend
  review, and pre-approval commit stop.

- [x] **Step 3: Verify documentation**

  Run: `git diff --check`

  Expected: exit 0 with no output.

---

### Task 2: Build a tested deployment artifact outside the archive

**Files:**

- Create temporarily: `/tmp/synology-nas-dashboard-*/test_deployment.py`
- Create temporarily: `/tmp/synology-nas-dashboard-*/deployment.py`
- Create temporarily: `/tmp/synology-nas-dashboard-*/pre-state.json`

**Interfaces:**

- Consumes: exact Synology entity IDs, config entry ID, system device ID, DSM configuration URL, and
  design acceptance criteria.
- Produces: `health_for(values) -> str`, `health_template() -> str`,
  `dashboard_config() -> dict[str, object]`, preflight validation, deployment, read-back, and rollback
  functions.

- [x] **Step 1: Write failing health-policy tests**

  Cover Healthy, volume Attention and Critical, Celsius and Fahrenheit temperature thresholds,
  abnormal status, safety binary, Security Advisor Attention, missing evidence, and Critical over
  Unknown.

  ```python
  self.assertEqual(health_for(healthy_values()), "Healthy")
  self.assertEqual(health_for(healthy_values(volume_used=80)), "Attention")
  self.assertEqual(health_for(healthy_values(max_temp=140, temp_unit="°F")), "Critical")
  self.assertEqual(
      health_for(healthy_values(volume_status="degraded", drive_2_smart="unknown")),
      "Critical",
  )
  ```

- [x] **Step 2: Write failing dashboard-contract tests**

  Assert two views, Overview before Trends, admin-only registration, four hero conditions, DSM-link
  states exactly `Attention`, `Critical`, and `Unknown`, 30-day capacity and temperature charts,
  24-hour performance charts, no restart or shutdown entities, no service actions, no `card_mod`,
  and inert update and fan-mode cards.

- [x] **Step 3: Run tests and verify RED**

  Run: `python3 -m unittest -v /tmp/synology-nas-dashboard-*/test_deployment.py`

  Expected: assertions fail because stub functions raise `NotImplementedError`.

- [x] **Step 4: Implement the minimal artifact**

  Implement health policy, the equivalent Home Assistant Jinja template, dashboard JSON, safe
  authenticated API clients, backup/read-back validation, and supported rollback operations.
  Keep token access inside `os.environ["HA_TOKEN"]`; never serialize request headers.

- [x] **Step 5: Run tests and verify GREEN**

  Run: `python3 -m unittest -v /tmp/synology-nas-dashboard-*/test_deployment.py`

  Expected: every test passes with no warnings or errors.

---

### Task 3: Enable source entities and create the shared health sensor

**Files:**

- Modify live: Home Assistant entity registry and Template integration storage.
- Write backup: `/tmp/synology-nas-dashboard-*/pre-state.json`

**Interfaces:**

- Consumes: the tested deployment artifact and the five integration-disabled entities.
- Produces: five enabled source entities and `sensor.nas_health` attached to Synology system device
  `7c49b5101b0ab6e4161b3b6d4aeec184`.

- [x] **Step 1: Run read-only preflight and capture backup**

  Require `dashboard-nas` and `sensor.nas_health` to be absent, all five selected entities to be
  integration-disabled, and the Synology config entry to be loaded. Write only sanitized registry
  state, IDs, and existing dashboard metadata to the backup.

- [x] **Step 2: Enable exactly five entities**

  Update registry `disabled_by` to `null` for:

  - `sensor.nas01_drive_1_status_smart`
  - `sensor.nas01_drive_2_status_smart`
  - `sensor.nas01_volume_1_maximum_disk_temp`
  - `sensor.nas01_volume_1_total_size`
  - `sensor.nas01_uptime`

- [x] **Step 3: Reload and verify source states**

  Reload config entry `01M088PV009PDJRXYVF0SNX672`. Require all five entities to exist with states
  other than `unavailable` before creating the helper.

- [x] **Step 4: Create the Template Sensor through config flow**

  Start handler `template`, choose `sensor`, then submit name `NAS Health`, the tested state template,
  and device ID `7c49b5101b0ab6e4161b3b6d4aeec184`. Do not add availability, unit, device class, or state class.

- [x] **Step 5: Read back and verify the helper**

  Require entity ID `sensor.nas_health`, device association to the Synology system device, platform
  `template`, and a current state in the four-state contract. Locate the new entity by the returned
  Template config-entry ID and rename Home Assistant's device-prefixed generated ID when necessary.
  On failure, run supported rollback and stop.

---

### Task 4: Register and save the dashboard

**Files:**

- Modify live: Home Assistant Lovelace dashboard registry and `dashboard-nas` storage configuration.
- Write backup: `/tmp/synology-nas-dashboard-*/post-state.json`

**Interfaces:**

- Consumes: `sensor.nas_health`, enabled Synology entities, and tested dashboard JSON.
- Produces: sidebar-visible, administrator-only `dashboard-nas` with Overview and Trends.

- [x] **Step 1: Save post-helper rollback state**

  Record the helper config-entry ID and the exact five enabled registry states without credentials.

- [x] **Step 2: Create dashboard registration**

  Send `lovelace/dashboards/create` with title `Synology NAS`, URL path `dashboard-nas`, icon
  `mdi:nas`, storage mode, `show_in_sidebar: true`, and `require_admin: true`.

- [x] **Step 3: Save full dashboard configuration**

  Send `lovelace/config/save` for `dashboard-nas` with the complete two-view tested configuration.

- [x] **Step 4: Read back and verify**

  Read both `lovelace/dashboards/list` and `lovelace/config`. Compare the saved configuration to the
  generated configuration and rerun dashboard-contract validation against the read-back object. On
  failure, run rollback and stop.

- [x] **Step 5: Harden every inert tile action**

  Explicitly set card tap, hold, and double-tap plus icon tap, hold, and double-tap to `none` for
  the health hero, DSM update, and fan-mode tiles. Before saving, require the live dashboard hash to
  match the initial post-deployment hash. Read the corrected configuration back; restore the initial
  configuration if verification fails.

---

### Task 5: Verify the deployed dashboard in the browser

**Files:**

- Create temporarily: `/tmp/synology-nas-dashboard-*/ha-auth-state.json`
- Create temporarily: `/tmp/synology-nas-dashboard-*/desktop.png`
- Create temporarily: `/tmp/synology-nas-dashboard-*/mobile.png`

**Interfaces:**

- Consumes: live `dashboard-nas` and a temporary token-derived Playwright storage state.
- Produces: runtime layout, interaction, console, network, and computed-style evidence for visual
  approval.

- [x] **Step 1: Create token-safe browser state**

  Generate a mode-0600 Playwright storage-state file without putting the token on a command line or
  in Playwright output. In one named session, run open, state-load, goto, and snapshot in that order.

- [ ] **Step 2: Verify desktop Overview and Trends**

  At 1440 by 900, require visible hero, two policy metrics, health evidence, system context, both
  view tabs, and four trend charts. Check document width against viewport width and save a screenshot.

- [ ] **Step 3: Verify representative mobile rendering**

  At 390 by 844, require stacked content with no horizontal overflow, clipped text, or overlapping
  cards. Save a screenshot.

- [ ] **Step 4: Verify styling and interactions**

  Confirm the current hero's computed background differs from a neutral card through a success,
  warning, error, or neutral theme token. Confirm allowed sensor cards open more-info. Confirm the
  health hero, update card, and fan-mode card do not open a dialog or invoke a service.

- [ ] **Step 5: Verify current-state DSM-link behavior and browser health**

  When health is Healthy, require no `Open DSM` control. Validate the saved conditional state list
  and URL action structurally for the other states. Check console and failed network requests for new
  dashboard or UIX errors.

- [x] **Step 6: Remove temporary authentication state**

  Delete only the exact mode-0600 auth-state file when browser verification completes or the browser
  attempt ends. Preserve screenshots and sanitized rollback material until pde completes live
  review.

---

### Task 6: Record live results and stop for visual approval

**Files:**

- Modify: `docs/synology-nas/synology-nas-dashboard.md`
- Modify: `CONTEXT.md`

**Interfaces:**

- Consumes: API read-back and Playwright evidence.
- Produces: exact live-state checkpoint, known verification limits, rollback location, and visual
  review handoff.

- [x] **Step 1: Record deployment evidence**

  Add deployment date, live helper state, dashboard registration, enabled entities, and the untested
  browser and abnormal-state link caveats. Record unavailable browser evidence explicitly rather
  than treating it as passed.

- [x] **Step 2: Update terminology from planned to live**

  Change the Synology dashboard glossary entry after API read-back proves deployment. Record browser
  verification limits separately.

- [x] **Step 3: Run final repository checks**

  Run: `git diff --check`

  Run: `git status --short`

  Expected: only Synology design, plan, glossary, README, and Home Assistant API-access-reference
  changes are present. Remove the temporary visual-companion directory before proposing a commit.

- [x] **Step 4: Stop before commit**

  Give pde the exact live dashboard URL and ask for visual approval. Do not commit or push.
