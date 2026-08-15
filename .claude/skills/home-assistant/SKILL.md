---
name: home-assistant
description: Work with pde's Home Assistant at http://hass.ehlke.net:8123 and the Music Assistant server at http://mass.ehlke.net:8095. Use when asked to inspect or change Home Assistant - entities, states, automations, scripts, scenes, helpers, integrations, Lovelace dashboards and cards, energy or Sense data, calendars, weather, or media playback. Tells you which of the three access paths (HA MCP tools, REST API, WebSocket API) can actually do a given job, and records this instance's quirks. Skip for other smart-home platforms.
---

# Home Assistant (pde's instance)

## Facts that do not change

- Base URL `http://hass.ehlke.net:8123`. Local network only.
- `$HA_TOKEN` is always a valid long-lived access token with **full admin rights**. Read it from the environment. Never echo, log, or paste it. See [Never leak the token](#never-leak-the-token).
- Runs on a Raspberry Pi. Config dir is `/config`, not reachable from this machine.
- Music Assistant runs as an HA add-on at `http://mass.ehlke.net:8095`. Drive it through the HA-side `music_assistant.*` services; its own API rejects `$HA_TOKEN` and needs separate credentials we do not have. **Pandora and SiriusXM are both connected.** Pandora surfaces as 36 library radio stations; SiriusXM is reachable only via `search`, never `get_library`. Artist/album/track counts are 0 because both are station services, not because nothing is configured. Never judge provider presence from `get_library`. Read [references/music-assistant.md](references/music-assistant.md) before touching it.
- IPv6 is disabled. Use `hass.ehlke.net` for HA and `mass.ehlke.net` for Music Assistant, real DNS
  names resolving to the internal LAN address, not the old `.local`/mDNS hostnames, retired
  2026-08-11 because FireOS has no mDNS resolver at all and couldn't reach them. Do not hardcode a
  literal IP either; that was a temporary workaround for the same problem and caused a CORS bug for
  any client other than the device it was targeting. See
  [homie-dashboard-install-plan.md](../../../docs/homie-dashboard/homie-dashboard-install-plan.md)'s
  2026-08-10 and 2026-08-11 checkpoints.

## Pick the right access path

Choosing wrong wastes a turn. The MCP server in particular cannot configure anything.

| Task | Path |
|---|---|
| Read states, call services, control devices | MCP tools (`mcp__HA__*`) or REST |
| Automations, scripts, scenes, helpers (full CRUD) | REST |
| Install an integration (config flow) | REST |
| History, logbook, templates, config check | REST |
| **Lovelace dashboards and cards** | WebSocket only |
| **Area / entity / device / label registry** | WebSocket only |
| HACS repository list | WebSocket only |
| Supervisor / add-ons | WebSocket `supervisor/api`; REST `/api/hassio/*` returns 401 |
| Anything inside an add-on's own API (e.g. MA favorites) | WebSocket, via an HA ingress session |

The `mcp__HA__*` tools are the Assist intent bridge: turn on/off, media transport, volume, shopping list, timers, broadcast, `GetLiveContext`. They expose **no configuration surface at all**, and they only see entities exposed to Assist, which is a small subset. Do not reach for them to build or edit anything.

For REST and WebSocket recipes, including the ready-made `scripts/haws.py` client, read [references/api-access.md](references/api-access.md).

## Before changing anything

- Lovelace saves replace the **entire dashboard config** in one write. Always read, back up to a timestamped file, then save. `scripts/apply-card.py` does this and refuses to write when its target match count is wrong.
- Automations are safe to create and delete freely via REST; verify with `/api/config/core/check_config` and by confirming the entity appears.
- Prefer verifying visually when the task is visual. A saved config that validates can still render broken, which has happened here more than once.

## Never leak the token

This has happened twice: once through `playwright-cli` echoing generated code, once through a
Bash one-liner that interpolated `$HA_TOKEN` into a string meant to only report whether it was
set. Both forced a rotation. **Post-hoc redaction (piping to `sed`/`grep` to strip the value after
the fact) is not a safe strategy** — it depends on guessing the token's shape correctly every
time, and both leaks happened despite a redaction step being present. The rule going forward is to
never let the value enter an output stream at all, not to scrub it afterward.

**Checking whether `$HA_TOKEN` is set — the only safe form:**

```sh
if [ -n "$HA_TOKEN" ]; then echo "HA_TOKEN is set"; else echo "HA_TOKEN is NOT set"; fi
```

This is a test expression; the value itself is never interpolated into anything that gets printed.
Do **not** use `${HA_TOKEN:-fallback}` for this — it substitutes the fallback only when the
variable is *unset or empty*, so when it *is* set (the normal case), that expansion is the literal
token value. That specific mistake caused the second leak. `${HA_TOKEN:+set}` alone is safe (it
substitutes `set` only when the variable has a value, and produces nothing otherwise), but don't
combine it with `:-` on the same variable in the same command.

**General rule for any Bash command touching `$HA_TOKEN` or another secret:** before running it,
check whether the token could appear in stdout/stderr — as an argument being echoed, a variable
interpolated into a string literal, a heredoc, a `set -x` trace, or a redaction pipeline applied
after the fact — not just whether the command "looks like" it prints the token. If a command needs
the token's actual value (curl auth header, a script's `os.environ[...]` read, a file write), pass
it through environment inheritance or a file the shell never echoes, never through a string this
tool constructs and displays.

For `playwright-cli` specifically: use a Playwright storage-state file generated by Python that
reads `os.environ["HA_TOKEN"]`, load it with `state-load`, delete it afterwards, and pipe every
`playwright-cli` invocation through a redaction filter as defense in depth — but that filter is a
backstop, not the primary control; the primary control is never constructing a command that puts
the token in a string headed for output. The exact pattern is in
[references/api-access.md](references/api-access.md).

**If a leak happens anyway:** don't try to scrub the transcript (not possible). Tell pde
immediately, plainly, and completely — what leaked, which token (Homie's dev-only token is a
standing exception that doesn't need flagging; the admin `$HA_TOKEN` and any other credential do),
and recommend rotation. Then keep going with the task once he's acknowledged it; don't let the
incident block unrelated work he's waiting on.

## Instance quirks worth knowing before you diagnose anything

This instance was built on 2026-08-03. Short recorder history, empty automation list, unassigned areas and narrow Assist exposure are all consequences of its age, not neglect. Do not report them as problems.

The real quirk is Sense. Several of its auto-detected devices are stale and read 0 kWh/year, so automations built on them will never fire. Check the yearly counters before trusting any Sense entity.

Full entity inventory, the Sense dead list, installed custom cards, and dashboard paths are in [references/instance-inventory.md](references/instance-inventory.md).

## Lovelace and cards

Dashboard editing, the sections grid math, and hard-won lessons about the `wall-clock-card` are in [references/lovelace.md](references/lovelace.md). Read it before resizing or laying out any card.

### Styling policy

`card-mod` is deprecated and no longer supported on this instance. Do not reach for it, attempt a
backward fix, or recommend changing its version. Home Assistant 2026.8 broke card-mod 4.2.1's
frontend integration path; see [upstream issue #606](https://github.com/thomasloven/lovelace-card-mod/issues/606).
UI eXtension (UIX) is the supported drop-in replacement. Use `uix:` for card styling and
`uix-*` theme keys in all new or edited configuration. Existing card-mod keys are retained only by
UIX compatibility, not as a reason to keep using card-mod. Liquid Glass is development-only for
the dedicated Office user; do not generalize its theme-specific behavior to users who will return
to Noctis.

## Homie Dashboard fork

- Working copy: `/Users/pde/src/github.com/pdehlke/homie-dashboard`
- GitHub fork: `https://github.com/pdehlke/homie-dashboard`
- Git remote: `git@github.com:pdehlke/homie-dashboard.git`
- Live HA assets: `/config/www/community/homie-dashboard/`
- Lovelace dashboard path: `homie-dash`

The fork's `main` branch is the source of truth for custom Homie code and its placeholder-bearing
`dist/config.js`. The live copy injects a real token and must never be copied back into Git. HACS
can overwrite the live directory, so do not update Homie through HACS without first reconciling the
fork and taking a backup.

Persistent credential handoff files live outside both repositories under `/Users/pde/tmp`:

- `/Users/pde/tmp/homie-ha-edit-key`
- `/Users/pde/tmp/homie-dashboard-password`
- `/Users/pde/tmp/homie-dashboard-token`

Never print their contents. SSH/SFTP uses `root@hass.ehlke.net` on port `2222`. Read
`docs/homie-dashboard/homie-dashboard-install-plan.md` in this repository for the current
customization ledger, deployment procedure, backups, and next-work checkpoint.
