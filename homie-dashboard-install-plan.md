# Homie Dashboard Installation Plan

## Checkpoint: 2026-08-07

The installation and first customization phase are complete. Custom Homie code is now tracked in
the fork below rather than reconstructed from this plan:

- Working copy: `/Users/pde/src/github.com/pdehlke/homie-dashboard`
- GitHub: `https://github.com/pdehlke/homie-dashboard`
- Origin: `git@github.com:pdehlke/homie-dashboard.git`
- Upstream: `git@github.com:Big-Edge2297/homie-dashboard.git`
- Latest pushed commit: `35bf0f9` on `main`
- Deployed asset release: `20260807.10`
- Live assets: `/config/www/community/homie-dashboard/`
- Lovelace dashboard: `homie-dash`, loading
  `/local/community/homie-dashboard/homie-dashboard.html?v=20260807.10`

Resume work in the fork, directly on `main` unless the user changes that instruction. The next
design area is the remainder of Overview C; Solar and the Overview C A/V sidebar icon are accepted.
The A/V sidebar icon is tied semantically to `action: "media_browser"` and uses the circle-and-play
Now Playing symbol.

Release `20260807.10` is tracked by commit `35bf0f9`. In addition to the five-day OpenWeatherMap
forecast and AQI fallback from `.8`, it reads sunrise and sunset from `sun.sun`, UV index from
`sensor.openweathermap_uv_index`, and moon phase from `sensor.moon_phase`. The native Home
Assistant Moon integration was installed for that last entity. Release `.10` also fixes the `.9`
expanded-view regression where `uvValue` was referenced outside the scope in which it had
accidentally been declared.

Credential handoff files now persist across reboots under `/Users/pde/tmp`, outside both Git
repositories:

- SSH private key: `/Users/pde/tmp/homie-ha-edit-key`
- Homie user password: `/Users/pde/tmp/homie-dashboard-password`
- Homie long-lived token: `/Users/pde/tmp/homie-dashboard-token`

Never print or commit their contents. SSH/SFTP is available as `root@homeassistant.local` on port
`2222`. Use `homeassistant.local` for HA and `mass.local` for Music Assistant; IPv6 is disabled and
all earlier literal-IP workarounds are obsolete.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install and configure Homie Dashboard as a separate, reversible Home Assistant dashboard, tailored to this house and its Music Assistant players, without changing the existing Home dashboard or hiding its top navigation for the Tablet user.

**Architecture:** HACS will manage the upstream Homie files under `/config/www/community/homie-dashboard/`. Home Assistant will expose `homie-dashboard.html` as a separate Webpage dashboard in the sidebar. A dedicated non-admin HA account will own the long-lived token used by Homie's direct WebSocket connection. Temporary, key-only SSH/SFTP access will be used to edit and validate `config.js`; the existing `vision-sample` dashboard will remain untouched until Homie has been evaluated and separately approved.

**Tech Stack:** Home Assistant OS/Supervisor, HACS, Homie Dashboard v4.1.1 or the current reviewed release, Advanced SSH & Web Terminal add-on, SSH/SFTP, Home Assistant WebSocket API, Music Assistant media-player entities.

## Global Constraints

- [ ] Do not modify, replace, or re-save the existing Home dashboard (`vision-sample`) during installation or evaluation.
- [ ] Keep the Home dashboard's top navigation visible for the Tablet user.
- [ ] Install Homie as a separate sidebar dashboard first; do not fold it into the A/V tab without a later, explicit approval.
- [ ] Do not put HA tokens, passwords, SSH private keys, Alarmo PINs, or populated Homie configuration files in this repository, terminal output, chat, or Git history.
- [ ] Do not commit this plan or any implementation artifact unless separately instructed.
- [ ] Take backups before every change with a meaningful rollback consequence.
- [ ] Stop before credential creation if the plaintext-token risk described below is unacceptable.

## Current State and Known Gaps

- The existing Home dashboard and its A/V tab are live and must remain usable throughout this work.
- Music Assistant 2.9.10 is installed.
- No Terminal & SSH, Advanced SSH & Web Terminal, Studio Code Server, File Editor, or Samba add-on is currently installed.
- Existing HA API/WebSocket access is sufficient for dashboard metadata and entity discovery, but not for editing or deleting files beneath `/config/www/`.
- Homie Dashboard's checked-out upstream configuration identifies itself as v4.1.1 and supports an arbitrary list of `media_player` entities, a player selector, Music Assistant media browsing, playback controls, and two full-screen Now Playing views.
- Homie does not provide a documented Music Assistant player-grouping interface. Group creation, membership status, and ungrouping must therefore remain available through the existing native A/V controls unless testing proves otherwise.

## Required Dependencies and User Decisions

### 1. Filesystem access to Home Assistant

Recommended dependency: [Advanced SSH & Web Terminal](https://github.com/hassio-addons/addon-ssh) from the [Home Assistant Community Add-ons repository](https://github.com/hassio-addons/repository).

Why it is needed: Homie's `config.js` must be edited in `/config/www/community/homie-dashboard/`, and upstream specifically requires deletion of `config.js.gz` after editing. The HA dashboard API cannot perform either operation.

Security configuration for the temporary add-on:

- [ ] Bind the published SSH port only on the trusted home LAN; do not expose or forward it through the router.
- [ ] Generate a task-specific Ed25519 key outside the repository:

  ```sh
  ssh-keygen -t ed25519 -f /Users/pde/tmp/homie-ha-edit-key -N '' -C homie-dashboard-install
  ```

- [ ] Configure key-only authentication; leave password authentication unused.
- [ ] Use the add-on's `root` username only because its SFTP/rsync support requires that username; this is the add-on account, not unrestricted SSH into the HA OS host.
- [ ] Enable SFTP only for the installation window; disable agent forwarding, TCP forwarding, and compatibility mode.
- [ ] Verify that the session can read and write `/config/www/community/homie-dashboard/`, and no broader host access is needed.
- [ ] If SSH access is retired, remove the public key from the add-on and securely discard
  `/Users/pde/tmp/homie-ha-edit-key` and its public key.

Alternative: Studio Code Server or File Editor can support user-performed browser editing, but would require the user to make every file change manually. Samba would expose a broader file share and is not recommended for this one-time installation.

### 2. A dedicated Home Assistant identity

Homie stores a long-lived HA token in plaintext inside `config.js`, which is then served as `/local/community/homie-dashboard/config.js`. Anyone able to fetch that URL can recover the token and act with that HA user's permissions. LAN-only HTTP does not remove this risk.

- [ ] Create a dedicated, non-admin HA user named `Homie Dashboard`; do not use the current administrator token.
- [ ] Prefer this new identity over the Tablet identity so its credential can be revoked without affecting tablet login.
- [ ] Log in as that identity and create a long-lived token named `Homie Dashboard`.
- [ ] Transfer the token only through a temporary, permission-restricted file outside the repository. Do not paste it into chat or a shell command.
- [ ] If login automation is required, read the mode-0600 password file at
  `/Users/pde/tmp/homie-dashboard-password` and use `homeassistant.local` consistently.
- [ ] Record the token owner and creation date without recording the token value.
- [ ] Confirm acceptance of the residual risk: standard HA users do not provide fine-grained per-entity authorization, so this token can operate devices exposed to an ordinary user.

If that residual risk is not acceptable, stop the project. Reworking Homie to use the active HA frontend session instead of a plaintext token would require a maintained fork and a separate design plan.

### 3. HACS and browser access

- [ ] Confirm HACS is healthy and the administrator can add a custom Dashboard repository.
- [ ] Confirm the tablet and a desktop browser can reach HA directly at the chosen LAN URL.
- [ ] Have a way to hard-refresh the desktop browser and clear only the HA app/browser cache on the tablet.
- [ ] No separate Music Assistant web login is expected: Homie talks to HA over the HA WebSocket using its token and browses media through HA's `media_player` API. This should avoid the HTTP iframe login problem encountered with Music-Assistant-Lovelace-UI.

## Implementation Plan

### Task 1: Capture a baseline and establish rollback artifacts

- [ ] Export the current `vision-sample` Lovelace configuration and current dashboard/resource registry to timestamped files under a temporary directory outside the repository.
- [ ] Capture screenshots of the Home top navigation and A/V tab as both the administrator and Tablet user.
- [ ] Inventory all enabled Music Assistant `media_player` entities, friendly names, supported features, active grouping attributes, and playback behavior.
- [ ] Record the HA LAN URL that the tablet actually uses; derive the matching WebSocket URL as `ws://<same-host>:8123/api/websocket`.
- [ ] Verify `git status --short` and preserve all pre-existing untracked or modified files.

Expected result: enough evidence exists to prove that the Home dashboard and Tablet navigation did not change, and enough configuration exists to recover any dashboard metadata accidentally affected later.

### Task 2: Establish temporary, auditable file access

- [ ] Add the Community Add-ons repository if it is not already present.
- [ ] Install Advanced SSH & Web Terminal without enabling start-on-boot.
- [ ] Apply the key-only, LAN-only configuration described above and publish a non-default local port such as `2222`.
- [ ] Start the add-on and inspect its logs for authentication, configuration, or permission errors.
- [ ] Connect using the temporary key and verify these paths without changing them:

  ```sh
  ssh -i /Users/pde/tmp/homie-ha-edit-key -p 2222 root@homeassistant.local \
    'ls -ld /config /config/www /config/www/community'
  ```

- [ ] Verify SFTP upload, rename, and removal using a harmless uniquely named file under `/config/www/community/`, then remove that test file.

Expected result: the implementation agent can safely edit Homie's directory, with no password or private key stored on HA or in the repository.

### Task 3: Create the least-privileged Homie credential

- [ ] Create the `Homie Dashboard` non-admin user and establish its password through a secure temporary handoff.
- [ ] Sign in as that user and mint one long-lived token.
- [ ] Save the token in a mode-0600 temporary file outside the repository and verify no command echoes it.
- [ ] Test the token against the HA WebSocket authentication handshake without logging its value.

Expected result: a working non-admin token exists solely for Homie and can be independently revoked.

### Task 4: Install a reviewed Homie release through HACS

- [ ] Add `https://github.com/Big-Edge2297/homie-dashboard` to HACS as a Dashboard custom repository.
- [ ] Review the current release notes and diff against upstream v4.1.1 before selecting a version. Pin the reviewed version for the initial evaluation instead of accepting an unreviewed update.
- [ ] Download the selected release through HACS.
- [ ] Verify that these files exist and are served successfully:

  ```text
  /config/www/community/homie-dashboard/homie-dashboard.html
  /config/www/community/homie-dashboard/homie-dashboard.js
  /config/www/community/homie-dashboard/config.js
  ```

- [ ] Save checksums and a timestamped backup of the pristine installed directory outside the live HACS directory.

Expected result: upstream assets are installed by HACS and a known-good pristine copy is recoverable.

### Task 5: Register Homie without touching Home

- [ ] Add `/local/community/homie-dashboard/homie-dashboard.js` as a JavaScript Module resource if it is not already registered.
- [ ] Create a new Webpage dashboard with title `Homie Dash`, icon `mdi:tablet-dashboard`, and URL `/local/community/homie-dashboard/homie-dashboard.html`.
- [ ] Confirm the new dashboard has its own sidebar entry and `vision-sample` has an identical configuration hash before and after registration.
- [ ] Confirm the Home top navigation is still present for the Tablet user before continuing.

Expected result: Homie opens separately and shows its expected unauthenticated/placeholder state; Home remains byte-for-byte unchanged.

### Task 6: Build a house-specific Homie configuration

- [ ] Back up the pristine `config.js` before editing.
- [ ] Generate the configuration from the selected release's actual `config.js`; do not reuse examples from an older Homie version.
- [ ] Set `HA_TOKEN` from the secure temporary file without printing it.
- [ ] Set `WS_URL` to the exact same host, scheme, and port used to load HA on the tablet.
- [ ] Configure `America/Phoenix`, Fahrenheit units, the actual weather entity, and only those sensors and controls confirmed to exist.
- [ ] Populate `CONFIG.musicPlayers` with every enabled Music Assistant player that should be controllable. Give each a short, unambiguous room label.
- [ ] Remove or disable example entries containing `YOUR_`; do not leave fake security, alarm, garage, camera, solar, or notification controls visible.
- [ ] Configure other useful sections incrementally from the live entity inventory: home status, lights, climate, cameras, calendars, to-do lists, and photos. Leave unsupported sections empty rather than creating speculative helpers.
- [ ] Keep Alarmo PINs and other additional secrets out of the first evaluation configuration.
- [ ] Validate JavaScript syntax locally before upload.
- [ ] Upload by temporary name and atomically rename it to `config.js`.
- [ ] Delete `/config/www/community/homie-dashboard/config.js.gz`, as required by upstream, then verify the served `config.js` matches the intended file without displaying its contents.

Expected result: Homie connects to HA and renders only real, intentionally selected entities. The secret-bearing configuration exists only on HA and in an access-controlled backup outside Git.

### Task 7: Validate functionality and visual fit

- [ ] Hard-refresh and verify that Homie reports a successful HA WebSocket connection with no browser console errors.
- [ ] Validate desktop and tablet layouts at the tablet's actual landscape and portrait dimensions.
- [ ] As the Homie user, verify entity state updates and each enabled control; confirm the user cannot access administrator-only HA functions.
- [ ] Verify every configured Music Assistant player can be selected, played, paused, stopped, skipped, and volume-adjusted where supported.
- [ ] Verify Music Assistant media browsing reaches the configured Pandora and SiriusXM libraries through HA without a second MA login prompt.
- [ ] Verify album art, track metadata, progress, player label, idle behavior, and both full-screen Now Playing screens.
- [ ] Start playback on multiple players and document exactly how Homie indicates the active player. Confirm whether it exposes any existing group membership; do not infer grouping from synchronized playback.
- [ ] Verify the existing native A/V grouping controls still provide group-all, visible membership, ungrouping, and stop controls as the fallback for capabilities Homie lacks.
- [ ] Repeat the Home dashboard regression check as administrator and Tablet user: top navigation visible, existing tabs present, and A/V controls unchanged.
- [ ] Leave Homie running for a normal-use observation period and check for reconnect loops, stale states, cache problems, and unwanted player switching.

Acceptance criteria:

- Homie loads reliably on the tablet over the existing HTTP LAN connection.
- Pandora and SiriusXM can be browsed and played through Music Assistant without maintaining a separate browser login to MA.
- All intended players are controllable and the selected/active player is visually clear.
- Any missing grouping UI is explicitly understood and covered by the existing native A/V controls.
- The Home dashboard and Tablet top navigation are unchanged.
- No administrator credential or secret has entered Git, logs, or chat.

### Task 8: Decide whether to adopt, retain for evaluation, or remove

- [ ] Present screenshots, functional results, known limitations, and the exact rollback state to the user.
- [ ] If accepted for continued evaluation, leave Homie as a separate sidebar dashboard. Do not replace the A/V tab yet.
- [ ] If the user later approves integration, create a separate plan for navigation or A/V-tab changes with a Tablet-user regression test as a release gate.
- [ ] If rejected, execute the rollback below immediately.

## Update and Maintenance Strategy

HACS updates overwrite Homie's `config.js`. Automatic unattended updates are therefore unsafe.

- [ ] Keep Homie updates manual and pinned until each release is reviewed.
- [ ] Before every update, back up the live `config.js` and the installed Homie directory outside the HACS-managed path.
- [ ] After every update, compare the new default `config.js` schema with the prior release and migrate the house configuration deliberately.
- [ ] Restore the token through the secure injection process, delete the regenerated `config.js.gz`, hard-refresh, and repeat the functional and Tablet navigation regression checks.
- [ ] Rotate or immediately revoke the dedicated token if the configuration is exposed, copied to Git, or served beyond the trusted LAN.

## Rollback Plan

- [ ] Remove the `Homie Dash` Webpage dashboard entry.
- [ ] Remove the Homie JavaScript resource if no other dashboard uses it.
- [ ] Uninstall Homie Dashboard from HACS and verify its `/config/www/community/homie-dashboard/` assets are no longer served.
- [ ] Revoke the `Homie Dashboard` long-lived token; delete or disable the dedicated user if it has no other purpose.
- [ ] Remove the temporary SSH authorized key, stop and uninstall the SSH add-on unless retention was explicitly requested, and remove the temporary workstation key files.
- [ ] Confirm the Home dashboard configuration matches the baseline and its top navigation remains visible for the Tablet user.
- [ ] Remove secret-bearing temporary backups when rollback verification is complete.

Expected result: the system returns to its pre-project state, with the existing Home dashboard and native A/V controls intact.

## User Touchpoints

The implementation should require the user only for these decisions or actions:

1. Accept or reject Homie's plaintext non-admin-token risk.
2. Approve installation of the temporary SSH add-on and its LAN-only port.
3. Create or securely provide the password for the dedicated `Homie Dashboard` HA user so its token can be minted.
4. Review Homie on the actual tablet and choose adopt, continue evaluating, or roll back.
5. Decide whether the temporary SSH add-on should be retained after the work.

## References

- [Tracked Homie Dashboard fork](https://github.com/pdehlke/homie-dashboard)
- [Upstream Homie Dashboard repository](https://github.com/Big-Edge2297/homie-dashboard)
- [Advanced SSH & Web Terminal add-on documentation](https://github.com/hassio-addons/addon-ssh/blob/main/ssh/DOCS.md)
- [Home Assistant Community Add-ons repository](https://github.com/hassio-addons/repository)
- [HACS dashboard repository file handling](https://www.hacs.xyz/docs/use/repositories/type/dashboard/#custom-features-for-files-stored-under-hacsfiles)

## Screen A Customization Ledger — 2026-08-07

This section records the proof-of-concept customizations that go beyond upstream `config.js`. These changes are live but remain evaluation work until the tablet view is accepted.

### Native Home Assistant helpers

Nine UI-managed Template Sensor helpers support Screen A without requiring `configuration.yaml` edits or an HA restart:

- `sensor.homie_alarm_status`
- `sensor.homie_lights_status`
- `sensor.homie_media_status`
- `sensor.homie_irrigation_status`
- `sensor.homie_robot_status`
- `sensor.homie_ev_status`
- `sensor.homie_solar_generation`
- `sensor.homie_whole_house_load`
- `sensor.homie_grid_flow`

### Upstream configuration changes

The live `config.js` now defines:

- Eight Screen A status cells in a balanced four-by-two layout.
- Main House conditions from the South thermostat's temperature and humidity sensors.
- Office Wing conditions from the North thermostat's temperature and humidity sensors.
- A three-value Solar pill: generation, whole-house load, and directional grid flow.
- Lights, Climate, A/V, and Irrigation controls in that order.
- Real light entities grouped by HA area, excluding demo and aggregate lights.
- Main House and Office Wing thermostat labels.
- Five irrigation zones, including the temporarily unavailable Back Yard controller.
- Classic Gold, Screen A, vivid gradient, and 12-hour time as one-time browser defaults.

The deployed copy contains a real HA token. Any future repository copy must replace it with `YOUR_LONG_LIVED_ACCESS_TOKEN` before staging.

### Patched Homie behavior

The live installation adds `homie-custom.js` and patches `homie-dashboard.html` to provide behavior not supported by upstream configuration:

- Replace the top-right Pet Stats button with a Lights launcher.
- Keep the Security button visible but report `Alarm Not Configured` without alarm controls.
- Route the A/V chip to Homie's Music Assistant browser/player selector.
- Route the bottom Climate chip to Homie's dedicated thermostat overlay; its generic climate popup assumes a single setpoint and mishandles Fahrenheit heat/cool ranges.
- Require confirmation before starting an irrigation zone; stopping remains immediate.
- Render the Screen A status grid as four columns by two rows.
- Apply the agreed defaults once per browser without overriding later user changes.

HACS updates can overwrite `config.js` and `homie-dashboard.html`, and can omit the added `homie-custom.js`. Do not update Homie through HACS without backing up and reapplying or merging these changes.

### Accepted work and next checkpoint

- The fork is the source of truth. It must commit only a placeholder-bearing `config.js`; deployment
  injects `/Users/pde/tmp/homie-dashboard-token` outside Git.
- Overview A is accepted. Overview B's center grid matches Overview A.
- Overview C Solar uses real Sense and Electricity Maps data, shows hourly history, has no battery,
  and retains two unbound `— °F` placeholders labeled Left Inverter and Right Inverter.
- All temperature-related dashboard displays use Fahrenheit permanently.
- Overview C's A/V sidebar button uses the circle-and-play Now Playing icon rather than the generic
  switch slider.
- Overview C weather uses `weather.openweathermap`, which supplies today plus seven future daily
  entries. The card deliberately excludes today and displays five actual future days. Do not switch
  it to `weather.forecast_home`, whose current Met.no response supplies only two future days.
- Overview C AQI uses the Geronimo, Pima County WAQI station for overall AQI, PM2.5, PM10, CO, and
  NO2. Pollutant readings are unitless sub-indices.
- Expanded Weather reads sunrise and sunset from `sun.sun`, UV index from
  `sensor.openweathermap_uv_index`, and moon phase from the native Moon integration's
  `sensor.moon_phase` entity.
- Cache busting uses one release token at both the Lovelace iframe and nested asset boundaries.
- Next session: continue evaluating and customizing the non-Solar portions of Overview C.
