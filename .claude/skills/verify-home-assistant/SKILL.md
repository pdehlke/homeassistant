---
name: verify-home-assistant
description: >
  Drive pde's live Home Assistant instance (hass.ehlke.net) the way its own
  automations, scripts, and background effects actually run, and prove one
  fired: trigger it for real, read its trace, and confirm the resulting
  entity state or notification, not just that a save succeeded. Use after
  building or changing an automation/script/notification, or whenever a
  doc in this repo claims something works and that claim needs re-proving
  against live state. For Homie Dashboard's own UI, use the sibling
  `pdehlke/homie-dashboard` repo's `verify-homie-dashboard` skill instead;
  for general API/WebSocket access patterns and this instance's quirks, see
  this repo's own `home-assistant` skill, which this one assumes.
---

# Verify Home Assistant

This is not a general HA reference — that's `.claude/skills/home-assistant/`,
and this skill assumes it. This skill is narrower: proving a specific
automation, script, or notification actually does what it claims, live,
with evidence, the way this repo's own docs (`docs/*/`) have always been
required to before a checkpoint gets written.

There is one instance, always running, real house. No staging copy. Verify
against real entities freely (see this repo's `ha-instance-still-in-setup`
memory note: real hardware, no household dependency yet), but never leave a
mutating check in a state you didn't put it in — read the before-state,
verify, and restore.

## Launch

Nothing to launch. HA is always up at `hass.ehlke.net`, reached through the
Caddy reverse proxy on port 80 (plain HTTP, no TLS); the old direct `:8123`
port no longer works. Runs as a VM under Proxmox VE on a Mac mini, not the
Raspberry Pi 4 this instance used to run on — see
[CONTEXT.md](../../../CONTEXT.md) and
[docs/hardware/mac-mini-migration.md](../../../docs/hardware/mac-mini-migration.md).
Skip straight to Doctor.

## Doctor

```bash
python3 .claude/skills/verify-home-assistant/scripts/doctor.py
```

Stdlib only. Checks `$HA_TOKEN` authenticates, core is up and reports a
version, automations are registered (and flags a suspicious *drop* in count,
not growth — this instance is young and its automation list is expected to
keep growing), and lists any of the known-permanently-dead Sense detections
that are present, so a verification run doesn't mistake a sensor that never
moves by design for a bug in whatever it's actually testing.

Real output, run 2026-08-23:

```
OK    HA_TOKEN authenticates: HTTP 200
OK    core up: version 2026.8.2, timezone America/Phoenix, units °F
OK    19 automation(s) registered (instance-inventory.md's 2026-08-11 snapshot recorded 8 -- expect growth, investigate a drop)
NOTE  7 known-dead Sense detection(s) present and reading near-zero by design ...

All required checks passed. Safe to drive.
```

19 vs. the inventory doc's last-recorded 8 is real growth, not a doctor bug —
`references/instance-inventory.md` is due a refresh, separate from this
skill.

## Drive

Pick the access path from the `home-assistant` skill's own table — REST for
automations/scripts/scenes/history, WebSocket for Lovelace/registries/traces/
Supervisor, `scripts/haws.py` (same repo, `.claude/skills/home-assistant/
scripts/haws.py`) for anything WebSocket-only. Reuse it rather than
reimplementing a WebSocket client here.

For anything with a visible UI effect (a dashboard render, a notification
banner), drive a real browser with `playwright-cli` the same way
`verify-homie-dashboard` does in the sibling repo: generate a storage-state
file with `scripts/make-auth-state.py` (below), `state-load` it, `goto` the
target dashboard (`/lovelace/0` for the default Overview,
`/dashboard-office/0` for Office, etc. — see `references/instance-inventory.md`
for the current list), screenshot, close.

```bash
python3 .claude/skills/verify-home-assistant/scripts/make-auth-state.py HA_TOKEN /path/to/scratch/ha-auth-state.json
playwright-cli open
playwright-cli state-load /path/to/scratch/ha-auth-state.json
playwright-cli goto "http://hass.ehlke.net/lovelace/0"
playwright-cli screenshot --filename=/path/to/evidence/whatever.png
playwright-cli close
```

For anything with no UI effect (most automations — they run headless), skip
Playwright entirely and drive REST/WebSocket directly; a screenshot of
nothing happening is not evidence.

## Evidence

API reads, traces, and any screenshots go to
`.claude/skills/verify-home-assistant/evidence/` (gitignored — do not commit
real house state; this repo may go public per its own `CLAUDE.md`). Name
files `<feature>-<what>`.

Proof standard, matching how every automation in this repo's `docs/*/` has
actually been verified:

- **Trigger for real**, `POST /api/services/automation/trigger` (or the
  entity's real precondition, when trigger-testing would skip logic worth
  proving), not just a config save.
- **Read the trace**, not just the resulting state — `trace/list` then
  `trace/get` over WebSocket. `script_execution`, every `variables:` value,
  and errors `continue_on_error` would otherwise swallow are all visible
  there and nowhere else. A wrong outcome and a wrong trace are different
  bugs; conflating them wastes the next diagnosis.
- **Confirm the real effect**, not the automation's own report of success:
  the entity state it was supposed to change, or — since persistent
  notifications are not entities and `GET /api/states` returns nothing for
  them whether or not one exists — `persistent_notification/get` over
  WebSocket.
- **Distinguish an API-triggered run from a real one.** A logbook/trace
  entry carrying a `context_user_id` marks this verification run's own
  trigger, not a real-world firing. Don't report a manually triggered
  automation as proof it fires under its real trigger condition too — that
  still needs its own check (or an honest note that it wasn't exercised).
- **Restore.** Dismiss any notification this run created
  (`persistent_notification/dismiss`), and put back any entity state a
  trigger changed.

## Cleanup

- `playwright-cli close` if a browser was opened; delete the auth-state file
  immediately after.
- Dismiss every persistent notification this run created.
- Restore any entity state a trigger changed, using the before-read Doctor
  or the drive step captured.
- Never delete anything under `evidence/`.

## Helpers

- `scripts/doctor.py` — read-only instance health check. `python3
  .claude/skills/verify-home-assistant/scripts/doctor.py`. No arguments, no
  dependencies beyond the stdlib.
- `scripts/make-auth-state.py` — Playwright storage-state generator, same
  pattern and same safety rationale as `verify-homie-dashboard`'s copy in
  the sibling repo. `python3
  .claude/skills/verify-home-assistant/scripts/make-auth-state.py <ENV_VAR>
  <output-path>`.

## Feature map

See [features/README.md](features/README.md).
