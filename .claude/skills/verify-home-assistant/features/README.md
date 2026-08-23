# Home Assistant verification map

Maintained source for proving this HA instance's background behavior —
automations, notifications, energy statistics — actually does what it
claims. Read [../SKILL.md](../SKILL.md) first, then use the matching
feature file below.

For the tablet-facing dashboard UI (chips, overlays, screens), use the
sibling `pdehlke/homie-dashboard` repo's `verify-homie-dashboard` skill
instead — that surface is covered there, not here.

## Baseline preconditions

- `python3 ../scripts/doctor.py` passes.
- `$HA_TOKEN` set and authenticating.
- There is one instance, always live. No seeding, no disposable data — every
  recipe below touches the real house. A feature file's Gotchas note
  anything it can't safely re-run without side effects.

## Driving conventions

- REST for automations/scripts/scenes/history; WebSocket
  (`.claude/skills/home-assistant/scripts/haws.py`, same repo) for traces,
  Lovelace, registries, Supervisor, and persistent notifications — see the
  `home-assistant` skill's access-path table for the full split.
- History timestamps need a literal `Z` suffix, not `+00:00` — Python's
  `.isoformat()` produces the wrong one. See
  `../../home-assistant/references/api-access.md`.
- A rejected service call's real error only shows up over WebSocket; REST
  gives a bare `400` with no body.
- Never `$HA_TOKEN` echo it, log it, or interpolate it into anything that
  gets printed. See the `home-assistant` skill's "Never leak the token"
  section — the same discipline applies here.

## Proof and skip reporting

- A config save or a `200` from a service call is not proof by itself.
  Trigger, trace, and independently re-read the effect.
- Record which entity/automation ID and which trigger method (real
  precondition vs. manual `automation.trigger`) produced each artifact.
- Report an untestable feature with the exact call attempted and what
  failed, rather than skipping silently.

## Feature entry contract

Each feature file has an H1 title, one paragraph on the behavior, then
exactly four H2 sections: `Sub-features`, `How to get to it (user POV)`,
`Driving it with REST/WebSocket`, `Gotchas`.

## Features

- [Automation trigger and trace](automation-trigger-and-trace.md) — the
  generic pattern for proving any automation actually ran and did what its
  trace says, not just what its final state suggests.
- [Persistent notifications](persistent-notifications.md) — the notification
  surface most alert automations in this repo actually use, and the one
  place `GET /api/states` silently lies about absence.
- [Energy statistics](energy-statistics.md) — period totals for
  reset-to-zero Sense sensors via `recorder.get_statistics`, the pattern
  behind every energy alert automation in `docs/energy/`.
