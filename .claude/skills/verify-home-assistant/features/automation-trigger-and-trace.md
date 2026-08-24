# Automation trigger and trace

Any automation can be proven live: fire it for real, read what it actually
did action-by-action from its trace, and confirm the resulting effect
independently. This is the generic recipe every automation-specific
checkpoint in `docs/*/` already follows in practice — this file names it
once instead of re-deriving it each time.

## Sub-features

- `trigger-manual` — `automation.trigger` fires the automation immediately,
  regardless of its real trigger condition.
- `trace-read` — `trace/list` then `trace/get` shows `script_execution`,
  every rendered `variables:` value, and any error a `continue_on_error`
  step would otherwise swallow silently.
- `effect-confirm` — the automation's actual effect (an entity state change,
  a notification, a service call downstream) is read back independently,
  not inferred from the trigger call's own `200`.
- `context-distinguish` — a trace/logbook entry carrying a `context_user_id`
  marks this verification's own manual trigger, not evidence the automation
  fires under its real-world condition.

## How to get to it (user POV)

- There is no UI entry point most users touch directly — automations run
  in the background. The nearest user-visible surface is whatever they
  produce (a notification, a light change, a pushed alert).
- Developer Tools → YAML/Automations in the HA UI can also manually
  trigger one, for a human doing this by hand instead of via API.

## Driving it with REST/WebSocket

Preconditions:

- `doctor.py` passes.
- Know the automation's `entity_id` (`automation.<slug>`) and read its
  current `last_triggered` first, so the trigger you cause is unambiguous.

- **Baseline.**

  ```bash
  HB="Authorization: Bearer $HA_TOKEN"; U=http://hass.ehlke.net
  curl -s --max-time 8 -H "$HB" "$U/api/states/automation.<slug>" | \
    python3 -c "import json,sys; d=json.load(sys.stdin); print(d['state'], d['attributes'].get('last_triggered'))"
  ```

- **Trigger for real.**

  ```bash
  curl -s -X POST --max-time 8 -H "$HB" "$U/api/services/automation/trigger" \
    -d '{"entity_id": "automation.<slug>"}'
  ```

- **Read the trace.** WebSocket only.

  ```bash
  cd /Users/pde/src/github.com/pdehlke/homeassistant   # HA_TOKEN must be in this process's env; see api-access.md's warning about /tmp cwd stripping it
  export HA_URL=http://hass.ehlke.net
  python3 .claude/skills/home-assistant/scripts/haws.py \
    '{"type":"trace/list","domain":"automation","item_id":"<slug>"}'
  # take the newest run_id from that list, then:
  python3 .claude/skills/home-assistant/scripts/haws.py \
    '{"type":"trace/get","domain":"automation","item_id":"<slug>","run_id":"<run_id>"}'
  ```

  Confirm `script_execution: "finished"` (not `"error"` or a value that
  stops mid-sequence), and check each `variables:` step's
  `changed_variables` matches what the action logic actually needed.

- **Confirm the real effect.** Whatever the automation is supposed to do —
  re-read the target entity, or see
  [persistent-notifications.md](persistent-notifications.md) if the effect
  is a notification.

- **Distinguish real vs. manual.** The trace/logbook entry from this run
  carries a `context_user_id` (this verification's own token). A trigger
  fired by the automation's actual condition later will not. Don't collapse
  the two into one claim.

## Gotchas

- REST gives a bare `400: Bad Request` with no explanation on a rejected
  service call; reissue the identical call through `haws.py` to get the
  real voluptuous validator message.
- A published `/api/services` schema can advertise fields the validator
  rejects anyway. Trust the validator's error, not the schema.
- `continue_on_error` on an action step suppresses the *automation's own*
  failure signal, not the underlying error — the trace still shows it under
  that step's own result. Don't conclude "it handled the error" from the
  automation completing; read the step.
- A script field name that collides with a Jinja global (`area_id`,
  `label_id`, `device_id`, etc.) resolves to that built-in function instead
  of `Undefined` when not supplied — `check_config` reports this as valid
  because it is, and nothing raises at runtime. If a trace shows a
  suspiciously wrong branch taken with no error, check for this before
  looking anywhere else.
