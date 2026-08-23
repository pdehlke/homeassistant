# Persistent notifications

The dashboard-visible notification most alert automations in this repo
raise (`fridge_failure_alert`, the Lennox and Rachio alert automations,
etc.). Recent HA versions removed persistent notifications from the state
machine entirely: `GET /api/states` filtered on `persistent_notification.`
returns nothing whether or not one exists, and there is no REST endpoint for
them at all. An empty result here reads exactly like "the automation didn't
fire" and has produced a wrong conclusion in this repo before (2026-08-04).
Read and dismiss them over WebSocket only.

## Sub-features

- `notification-create` — an automation's `persistent_notification.create`
  call is visible over WebSocket immediately, never over REST.
- `notification-dismiss` — REST *does* work for dismissal, asymmetrically
  with read.
- `notification-absence` — confirming a notification does *not* exist
  requires the same WebSocket read; an empty REST states filter proves
  nothing either way.

## How to get to it (user POV)

- Renders as a banner/badge in the HA frontend (bell icon, notification
  drawer) for any logged-in user with access to see it.
- Not surfaced anywhere in Homie Dashboard's own UI — that's a separate gap,
  not a bug in this feature.

## Driving it with REST/WebSocket

Preconditions:

- `doctor.py` passes.
- An automation that raises one, e.g. `automation.fridge_failure_alert`
  (raises `persistent_notification.create`, no phone push — safe to
  manually trigger without alerting anyone's phone). Check the automation's
  actual notify target before picking one to trigger; several of this
  instance's alert automations *do* push to `notify.mobile_app_pete_iphone`
  for their critical tier — don't manually trigger those without expecting
  a real phone notification.

- **Read current notifications** (WebSocket only):

  ```bash
  cd /Users/pde/src/github.com/pdehlke/homeassistant
  export HA_URL=http://hass.ehlke.net:8123
  python3 .claude/skills/home-assistant/scripts/haws.py '{"type":"persistent_notification/get"}'
  ```

- **Trigger the automation** (see
  [automation-trigger-and-trace.md](automation-trigger-and-trace.md) for the
  full trigger+trace recipe), then re-read
  `persistent_notification/get` — the new notification's `notification_id`,
  `title`, and `message` should match what the automation's action step
  sends.

- **Dismiss it** (REST works for this direction):

  ```bash
  HB="Authorization: Bearer $HA_TOKEN"; U=http://hass.ehlke.net:8123
  curl -s -X POST --max-time 8 -H "$HB" -H "Content-Type: application/json" \
    -d '{"notification_id":"<id>"}' "$U/api/services/persistent_notification/dismiss"
  ```

- **Confirm dismissal** with another `persistent_notification/get` — the
  entry should be gone.

## Gotchas

- Do not conclude "the automation didn't fire" from an empty
  `GET /api/states` filter on `persistent_notification.` — that's not what
  it means, ever, for this HA version. Always use the WebSocket read.
- Dismissal is REST, creation/reading is WebSocket-only. This asymmetry is
  real, not a typo in this file.
- Leaving a self-created test notification on pde's real dashboard is worse
  than it looks — dismiss it every time, in the same run that created it,
  not as a separate later cleanup pass that might get skipped.
