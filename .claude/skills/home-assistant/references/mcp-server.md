# The `home-assistant` MCP server (`ha-mcp`)

Verified live 2026-09-08. This is a different thing from HA's own built-in `mcp_server`
integration (visible in the config-entries list in
[instance-inventory.md](instance-inventory.md)), which only ever exposed the Assist intent
bridge: turn on/off, media transport, volume, shopping list, timers, broadcast,
`GetLiveContext`, no configuration surface at all. That is what the old, read-only
`mcp__HA__*` tools were. The server now registered in this project as `home-assistant` is
[`homeassistant-ai/ha-mcp`](https://github.com/homeassistant-ai/ha-mcp), a Supervisor add-on
(confirmed `serverInfo.version: "8.4.3"` from its own `initialize` response), and it is full
read/write. Its tools appear in a session as `mcp__home-assistant__*`.

## Connection

Configured as a local (this-project-only) HTTP MCP server:

```
claude mcp get home-assistant
```

should show `Status: ✔ Connected` and a URL of the form
`http://192.168.4.141:9583/private_<secret>` — the Home Assistant VM's own LAN address
(same one SSH uses, see [SKILL.md](../SKILL.md)), not `hass.ehlke.net` and not `0.0.0.0`.

**If it shows `ConnectionRefused` against `http://0.0.0.0:9583/private_<secret>`:** that host is
wrong, not the server. `0.0.0.0` as a *connect-to* address resolves to localhost on this Mac,
where nothing listens; the add-on runs on the HA VM, not this machine. Fix it by re-adding the
server with the VM's real LAN IP, keeping the same secret path:

```sh
claude mcp remove home-assistant -s local
claude mcp add-json home-assistant '{"type":"http","url":"http://192.168.4.141:9583/private_<secret>"}' -s local
```

`http://hass.ehlke.net:9583/...` does not work either — confirmed 2026-09-08, connection fails
outright. Caddy proxies only 80/443 to HA core (see
[docs/networking/caddy-reverse-proxy.md](../../../../docs/networking/caddy-reverse-proxy.md));
it does not proxy the add-on's own port, so the add-on has to be reached directly on the VM's
LAN IP.

**Tool schemas load at session start.** Fixing the URL takes effect for the CLI's connection
health immediately, but a session already running when the fix lands won't have
`mcp__home-assistant__*` tools available until it reconnects (a fresh session, or however this
harness exposes an MCP reconnect). When schemas aren't showing up yet but the fix is confirmed
live, either wait for a restart or verify functionally over raw HTTP instead (see Verifying
without tool schemas, below) rather than concluding the server doesn't work.

## Treat the URL like `$HA_TOKEN`

The `/private_<secret>` path segment is the entire auth mechanism — anyone with the full URL
can call every tool below, including `ha_restart` and `ha_manage_backup`'s restore action. Same
discipline as [Never leak the token](../SKILL.md#never-leak-the-token): never print, echo, or
interpolate it into a command whose output gets displayed. If it leaks, rotate it by deleting
`/data/secret_path.txt` inside the add-on (or using its Configuration-tab regenerate control)
and restarting the add-on, then update the stored Claude Code config with the new path the same
way as the connection fix above.

## What it can do

`tools/list` returns 78 tools: 33 read-only, 45 write-capable (confirmed by each tool's
`annotations.readOnlyHint`). Between them they cover essentially everything the REST/WebSocket
recipes in [api-access.md](api-access.md) exist to work around, in one interface:

- Automations, scripts, scenes, helpers, blueprints (import) — full CRUD
- Dashboards and dashboard resources, including a `python_transform` mode on
  `ha_config_set_dashboard` for surgical edits as an alternative to full-config replacement
- Entity registry, device registry, area/floor registry, label registry, category registry,
  group registry, zones — read and write
- Integrations: enable/disable, add (drives the domain's config flow, including multi-step
  forms), update options, or reconfigure an existing entry (`ha_set_integration`)
- HACS (`ha_manage_hacs`, `ha_get_hacs_info`)
- Apps/add-ons (`ha_get_app`, `ha_manage_app` — this add-on's own category)
- Backups, both full snapshots and per-edit auto-backups (`ha_manage_backup`)
- Updates, themes, energy preferences, calendar events, to-do items
- Generic `ha_call_service` / `ha_call_event` for anything without a dedicated tool, plus
  `ha_bulk_control` for batched operations across many entities
- `ha_restart` (requires `confirm: true`, validates config first) and `ha_reload_core`
- `ha_get_history`, `ha_get_logs`, `ha_get_automation_traces`, `ha_eval_template`,
  `ha_get_system_health`, `ha_search`, `ha_get_overview` for read-side diagnosis

This supersedes the routing table's old WebSocket-only/REST-only split for most tasks. Prefer
`mcp__home-assistant__*` first; fall back to REST or WebSocket only for things it genuinely
doesn't cover (browser-based visual verification, SFTP deploys to Homie Dashboard, or a specific
documented gotcha in [api-access.md](api-access.md) that hasn't been re-tested against the MCP
equivalent yet).

Full CRUD does not relax the caution the old docs already established for saves that replace
whole configs, or for anything hard to reverse — verify a write the same way you would over
REST: read back the entity/config, check `check_config` or the tool's own validation error, or
confirm visually when the task is visual.

## Its bundled skill vs. this repo's skill

The server's `initialize` response instructs the client to read a skill it ships as an MCP
resource, `skill://home-assistant-best-practices/SKILL.md`. That is the same content as the
separately-installed Claude Code skill listed as `home-assistant-skills:home-assistant-best-practices`
in this environment — generic Home Assistant configuration best practices (native helpers over
templates, `entity_id` over `device_id`, automation modes, blueprint selectors, and so on) that
apply to any HA instance. It is not a replacement for *this* skill
([SKILL.md](../SKILL.md)) or its reference files, which are specific to pde's instance:
credentials, the access-path routing table, and this instance's own quirks (Sense's dead
detections, the DSC alarm join-write refusal, and the rest). Consult both when the task is
"build or edit an automation/script/dashboard": the bundled skill for HA-general correctness,
this repo's skill for instance-specific facts.

## Verifying without tool schemas

The server speaks standard MCP Streamable HTTP (JSON-RPC over POST, SSE-framed single-message
responses, no session header observed on this deployment). If `mcp__home-assistant__*` tools
aren't loaded in the current session yet, the same `initialize` / `tools/list` / `tools/call`
sequence works directly:

```sh
URL="http://192.168.4.141:9583/private_<secret>"
curl -s -X POST "$URL" -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"ha_get_state","arguments":{"entity_id":"sun.sun"}}}'
```

Responses are `event: message\ndata: <json>\n\n` — parse the line after `data: `. This is how the
2026-09-08 verification confirmed both read (`ha_get_state` on `sun.sun`) and write
(`ha_call_service` `input_boolean.turn_on` / `turn_off` against the inert
`input_boolean.demo_home_boy_present` helper, reverted immediately after) actually reach the
live instance, ahead of the tool schemas being available in-session.
