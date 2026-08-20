# API access recipes

All examples assume:

```bash
HB="Authorization: Bearer $HA_TOKEN"; U=http://hass.ehlke.net:8123
```

## REST

Confirmed working on this instance:

| Endpoint                                             | Use                                          |
| ---------------------------------------------------- | -------------------------------------------- |
| `GET /api/`                                          | Auth check, returns 200                      |
| `GET /api/config`                                    | Version, components, config dir, unit system |
| `GET /api/states`                                    | All entity states                            |
| `GET /api/states/<entity_id>`                        | One entity                                   |
| `POST /api/services/<domain>/<service>`              | Call a service                               |
| `GET /api/services`                                  | Every service domain                         |
| `GET /api/config/config_entries/entry`               | Installed integrations                       |
| `GET/POST/DELETE /api/config/automation/config/<id>` | Automation CRUD                              |
| `POST /api/config/core/check_config`                 | Validate config                              |
| `GET /api/history/period/<start>`                    | History, see the gotcha below                |
| `POST /api/template`                                 | Render a Jinja template                      |

`GET /api/error_log` returns **404** here. Do not rely on it.

### History timestamps must use `Z`

An ISO timestamp with a `+00:00` offset silently returns `[]`. Python's
`.isoformat()` produces exactly that, which cost real debugging time. Use:

```bash
START=$(python3 -c "import datetime;print((datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(hours=28)).strftime('%Y-%m-%dT%H:%M:%SZ'))")
curl -s -H "$HB" "$U/api/history/period/$START?filter_entity_id=binary_sensor.fridge_power"
```

Also note the API may return a series whose data starts later than the requested
window, so measure the actual span of returned points rather than assuming you
got what you asked for.

**A start time earlier than the recorder's oldest row also returns `[]`, not the
subset that does exist.** Asking for 48h on an instance holding 24h gets you
nothing at all, which reads exactly like "this entity has no history". Confirmed
2026-08-04: a 48h query on `binary_sensor.fridge_power` returned `[]` while a
24h query returned 86 events. When a history query comes back empty, halve the
window and retry before concluding the entity is unrecorded.

### The former dual-stack login failure is resolved

A multi-request login flow once failed with `{"message": "IP address changed"}`
because consecutive requests could take different IPv4 and IPv6 routes. IPv6 is
now disabled for this installation, so the literal-IP workaround is obsolete.
Use `hass.ehlke.net` consistently for login flows, REST, WebSocket, browser, and
SSH access. Use `mass.ehlke.net` for direct Music Assistant access.

### Install an integration via config flow

Two POSTs. This is how Local Calendar was installed:

```bash
FLOW=$(curl -s -X POST -H "$HB" -H "Content-Type: application/json" \
  -d '{"handler":"local_calendar","show_advanced_options":false}' \
  "$U/api/config/config_entries/flow")
FID=$(echo "$FLOW" | jq -r '.flow_id')
curl -s -X POST -H "$HB" -H "Content-Type: application/json" \
  -d '{"calendar_name":"Home"}' "$U/api/config/config_entries/flow/$FID"
```

Inspect the first response's `step_id` and `data_schema` to learn what the
second POST needs.

### Create an automation

POST the config to `/api/config/automation/config/<your_id>`. HA reloads
automatically. Use the modern schema (`triggers` / `conditions` / `actions`,
with `trigger:` and `action:` keys inside them). Verify by checking that
`automation.<slug>` appears in `/api/states`, then confirm behavior with
`POST /api/services/automation/trigger` and reading `last_triggered`.

To verify an automation ran, read `last_triggered` and the run trace. Do not
verify by looking for its notification over REST; see below.

### Create a scene

Same shape as an automation: POST the config to
`/api/config/scene/config/<your_id>`.

```bash
curl -s -X POST -H "$HB" -H "Content-Type: application/json" \
  "$U/api/config/scene/config/bedroom_evening" \
  -d '{
    "name": "Bedroom Evening",
    "entities": {
      "light.bedroom_perimeter": {"state": "on", "brightness": 76},
      "light.bedroom_diagonals": {"state": "off"}
    }
  }'
```

`entities` values are either a bare state string (`"on"`) or an object of
`state` plus whatever attributes that domain understands (`brightness` 0-255,
`color_temp_kelvin`, not the removed mireds-based `color_temp`). A scene has no
device, so give it an area the same way a template entity gets one:
`config/entity_registry/update` over WebSocket, not anything in the scene config
itself. Activate with `scene.turn_on` targeting the entity, or a `tile` card's
default tap action, which opens a more-info dialog with an Activate button
rather than firing on the first tap.

### Persistent notifications are not entities

Recent HA versions removed persistent notifications from the state machine.
`GET /api/states` filtered on `persistent_notification.` returns **nothing
whether or not notifications exist**, and there is no REST endpoint for them. An
empty result reads exactly like "the automation did not fire" and means nothing
of the kind. This produced a wrong conclusion here once, on 2026-08-04, when a
notification that had in fact been created looked absent.

Read them over WebSocket:

```bash
python3 scripts/haws.py '{"type":"persistent_notification/get"}'
```

Dismiss one over REST, which does work:

```bash
curl -s -X POST -H "$HB" -H "Content-Type: application/json" \
  -d '{"notification_id":"fridge_failure"}' "$U/api/services/persistent_notification/dismiss"
```

### Inspect an automation or script run with traces

More reliable than inferring behavior from side effects. `script_execution` and
per-action errors are both visible, including errors swallowed by
`continue_on_error`, and every rendered `variables:` value along the way.

```bash
python3 scripts/haws.py '{"type":"trace/list","domain":"automation","item_id":"<id>"}'
python3 scripts/haws.py '{"type":"trace/get","domain":"automation","item_id":"<id>","run_id":"<run>"}'
```

`domain` is `"script"` for a script, same two commands otherwise. This is how a
`smart_toggle_lights` script that silently computed the wrong branch got
diagnosed: the outcome alone (wrong lights turned off) looked like a resolution
problem, but the trace's `changed_variables` on the `variables:` step showed the
real cause directly, an empty entity list and a variable that had rendered to
`false` when it should not have.

A logbook entry carrying a `context_user_id` marks an API-initiated trigger
rather than a real one. Check that before reading anything into
`last_triggered`.

### A script or automation field named after a Jinja global silently breaks

Home Assistant registers lookup functions as Jinja globals: `area_id()`,
`area_name()`, `area_entities()`, `area_devices()`, `label_id()`,
`label_name()`, `label_entities()`, `label_devices()`, `label_areas()`,
`device_id()`, and more, all available in any template regardless of what fields
a script or automation defines.

Give a script field the same name as one of these — `area_id`, say — and a call
that does not supply it does not leave that name `Undefined` inside the
template. Jinja resolves the bare name against its own global environment when
no local value shadows it, finds the built-in function instead, and a function
object is truthy. `{{ area_id | default(omit) }}` never falls back, because
`default()` only triggers on `Undefined`, not on some other value that happens
not to be what was meant. Downstream logic that branches on `if area_id` takes
the wrong branch, and nothing raises: no error, no warning, just a quietly wrong
result that looks like a different bug entirely (an empty `area_entities()`
call, a condition that evaluates backwards) until the trace is actually read.

Name fields to not collide: `target_area_id` / `target_label_id` rather than
`area_id` / `label_id`, for instance. There is no validator for this; the field
selector accepts the name fine, and `check_config` reports the config valid,
because it is valid, just wrong once it runs.

### Services that return data

Some services (all four Music Assistant query services, for example) return a
response that is **not optional**. Ask for it explicitly or the call fails:

- REST: append `?return_response` to the service URL, and read
  `.service_response`.
- WebSocket: add `"return_response": true`, and read `.result.response`.

### Debug failed service calls over WebSocket

A rejected service call over REST returns a bare `400: Bad Request` with an
empty body. The **identical** call over WebSocket returns the real voluptuous
validator message naming the offending key, for example
`extra keys not allowed @ data['pagination']`. Whenever a service call 400s and
the reason is not obvious, re-issue it through `scripts/haws.py` before
guessing.

Note also that a published service schema can advertise fields the validator
rejects. Trust the validator, not `/api/services`.

### Read the real keys before concluding anything

`jq` returns null for a field that does not exist, exactly as it does for a
field that exists and is empty. Filtering on an assumed field name and getting
nulls is **not** evidence of absence.

This produced a wrong, confidently-stated conclusion once: querying `.provider`
on Music Assistant library items returned null for all 36, and the report
claimed no music provider was configured. The items simply have no `provider`
key, and Pandora was connected the whole time.

Dump one full object and read its actual keys before drawing a conclusion from
any field query:

```bash
jq -r '.result.response.items[0]' out.json                      # one whole object
jq -r '[.result.response.items[] | keys] | flatten | unique' out.json   # every key present
```

## WebSocket

Required for Lovelace, registries, and HACS. Use the bundled client:

Run authenticated commands with the working directory set to this
`homeassistant` repository. If a temporary client lives under `/tmp`, invoke its
absolute path while keeping the repository as the working directory. In this
harness, changing the command working directory to `/tmp` removes `HA_TOKEN`
from the child environment. Reassigning `HA_TOKEN` from that unset context
passes an empty value and produces a misleading WebSocket authentication failure
even though the launch session's token is valid.

```bash
export HA_URL=http://hass.ehlke.net:8123
python3 scripts/haws.py '{"type":"lovelace/dashboards/list"}'
python3 scripts/haws.py '{"type":"lovelace/config","url_path":"dashboard-sound"}'
python3 scripts/haws.py '{"type":"hacs/repositories/list","categories":["plugin"]}'
python3 scripts/haws.py '{"type":"config/area_registry/list"}'
python3 scripts/haws.py '{"type":"config/label_registry/create","name":"Bath","icon":"mdi:bathtub"}'
python3 scripts/haws.py '{"type":"config/entity_registry/update","entity_id":"light.x","labels":["bath"]}'
```

It authenticates, sends each argument as one command in order, and prints each
result as JSON on its own line. Needs `aiohttp`, which is already installed.

Labels work like a second, non-exclusive area: `config/label_registry/create`
returns a `label_id` slugged from `name`, same as areas do.
`entity_registry/update`'s `labels` field is a full list, not an add/remove
delta, and one entity can carry more than one label at once — a fixture that
legitimately belongs to two logical groups (a hallway light that's part of both
a bedroom's and a bathroom's preset group, say) just gets both label IDs in that
list. Target a label in a service call the same way as an area,
`target: {"label_id": "bath"}` instead of `{"area_id": ...}`.

To write a dashboard, use `scripts/apply-card.py` rather than hand-rolling a
save. It reads the live config, writes a timestamped backup, swaps only the card
you target, and refuses to save unless it matched exactly one.

## Never leak the token

```bash
# LEAKS THE TOKEN. Do not use this pattern.
echo "HA_TOKEN set: ${HA_TOKEN:+yes}${HA_TOKEN:-no}"
```

`${VAR:-fallback}` substitutes `fallback` only when `VAR` is unset or empty.
When it _is_ set, which is the normal case, that expansion is the literal value,
not the word "no". The safe way to check presence without ever interpolating the
value into anything printed is a test expression:

```bash
if [ -n "$HA_TOKEN" ]; then echo "HA_TOKEN is set"; else echo "HA_TOKEN is NOT set"; fi
```

`${HA_TOKEN:+set}` alone (no paired `:-`) is also safe. The general rule: before
running any Bash command that references `$HA_TOKEN`, check whether the value
could reach stdout/stderr — string interpolation into an echoed literal, a
heredoc, `set -x`, or a redaction pipe applied after the fact — not just whether
the command "looks like" a print. Piping through `curl -H "$HB" ...` is fine,
since curl doesn't echo its own headers back unless `-v`/`--trace` is added; the
danger is specifically building a string that contains the token and displaying
it, which redaction can only catch after the fact and imperfectly.

`playwright-cli` prints the code it generates. Passing the token through
`run-code` or `localstorage-set` puts it in the transcript verbatim.

Safe pattern. Generate a storage-state file in Python so the token never appears
on a command line, where `ps` could see it either:

```python
import os, json, pathlib
url = "http://hass.ehlke.net:8123"
tokens = {
    "access_token": os.environ["HA_TOKEN"], "token_type": "Bearer",
    "expires_in": 315360000, "hassUrl": url, "clientId": None,
    "expires": 9999999999999, "refresh_token": "",
}
state = {"cookies": [], "origins": [
    {"origin": url, "localStorage": [{"name": "hassTokens", "value": json.dumps(tokens)}]}
]}
p = pathlib.Path("ha-auth-state.json")
p.write_text(json.dumps(state)); p.chmod(0o600)
```

Then, redacting every invocation and deleting the file when done:

```bash
redact() { python3 -c "import sys,os;t=os.environ['HA_TOKEN'];[sys.stdout.write(l.replace(t,'<REDACTED>')) for l in sys.stdin]"; }
npx playwright-cli open 2>&1 | redact
npx playwright-cli state-load ha-auth-state.json 2>&1 | redact
npx playwright-cli goto "$HA_URL/dashboard-sound/0" 2>&1 | redact
npx playwright-cli screenshot --filename=shot.png 2>&1 | redact
npx playwright-cli close 2>&1 | redact
rm -f ha-auth-state.json
```

This injects the token into `localStorage` under `hassTokens`, which the HA
frontend accepts as a live session. Give the page about 7 seconds before
screenshotting; weather forecasts and background images load late.

`playwright-cli` is not installed globally. `pnpm add -g` fails because pnpm's
global bin is not on PATH and fixing that would edit pde's shell config, which
is off limits. Install it locally in the scratchpad with
`npm install @playwright/cli@latest` and call it with `npx playwright-cli`.

## The other three credentials: $HA_EDIT_KEY, $HOMIE_PASSWORD, $HOMIE_TOKEN

Homie Dashboard's SSH key, HA user password, and long-lived token moved from files under
`/Users/pde/tmp` to environment variables on 2026-08-20; see
[homie-dashboard-install-plan.md](../../../../docs/homie-dashboard/homie-dashboard-install-plan.md)'s
2026-08-20 checkpoint. Same leak discipline as `$HA_TOKEN` above applies to all three: never print,
echo, or interpolate the raw value into a command line that gets displayed.

**`$HOMIE_TOKEN`** is an ordinary HA long-lived access token for the non-admin `Homie Dashboard`
account. Use it exactly like `$HA_TOKEN` (same `Authorization: Bearer` header), over REST or
WebSocket. Expect a 401 on anything admin-only (`POST /api/config/core/check_config` is a good
probe) — that's confirmation it's the right, non-admin account, not a failure.

**`$HOMIE_PASSWORD`** is the login password for HA user `homie`. Verify it without ever creating a
session: POST to `/auth/login_flow`, then POST the username/password to the returned `flow_id`, and
stop there. A `type: create_entry` response means the password is correct; `type: form` with
`errors` means it isn't. Redeeming the returned code at `/auth/token` is the step that actually
mints a session/refresh-token — skip it for a check, only do it if you want a live login.

```python
import json, os, urllib.request
U = "http://hass.ehlke.net:8123"

def post(path, payload):
    req = urllib.request.Request(f"{U}{path}", data=json.dumps(payload).encode(),
                                  headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=10).read())

flow = post("/auth/login_flow",
            {"client_id": U + "/", "handler": ["homeassistant", None], "redirect_uri": U + "/"})
result = post(f"/auth/login_flow/{flow['flow_id']}",
              {"client_id": U + "/", "username": "homie", "password": os.environ["HOMIE_PASSWORD"]})
# result["type"] == "create_entry" -> correct password, no session created yet
```

**`$HA_EDIT_KEY`** is the SSH private key for `root@hass.ehlke.net:2222`. Write it to a mode-0600
temp file, pass `-i <file>` to `ssh`/`sftp`, and delete the file in a `finally` block so it's gone
even if the connection fails:

```python
import os, pathlib, tempfile, subprocess
fd, path = tempfile.mkstemp(prefix="ha-edit-key-")
keyfile = pathlib.Path(path)
try:
    key = os.environ["HA_EDIT_KEY"]
    os.write(fd, (key if key.endswith("\n") else key + "\n").encode())
    os.close(fd)
    keyfile.chmod(0o600)
    subprocess.run(["ssh", "-i", str(keyfile), "-p", "2222",
                     "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
                     "root@hass.ehlke.net", "ls -ld /config/www/community/homie-dashboard"],
                   check=True, timeout=20)
finally:
    keyfile.unlink(missing_ok=True)
```

`Connection refused` on port 2222 means the SSH & Web Terminal add-on isn't running — it's
manual-boot, stopped between uses by design, see
[media-player-restart-recovery.md](../../../../docs/device-alerts/media-player-restart-recovery.md#gotchas-hit-while-building-this)
— not a bad key. `Permission denied (publickey)` means the key itself doesn't authenticate.
