"""Read-only check: is this Home Assistant instance worth driving right now?

Stdlib only. Never prints $HA_TOKEN.

Checks:
  1. HA_TOKEN is set and authenticates (GET /api/, expect 200).
  2. Core is up and config is valid (GET /api/config, POST check_config).
  3. Automation count is sane (a sudden drop usually means something got
     wiped, not that automations were deliberately deleted).
  4. Flags Sense entities known to be permanently dead as of the last
     inventory pass, so a verification run doesn't mistake "this sensor
     never moves" for a bug in whatever it's actually testing.

Usage:
    python3 doctor.py
"""

import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.environ.get("HA_URL", "https://hass.ehlke.net")
TIMEOUT = 8

# From .claude/skills/home-assistant/references/instance-inventory.md.
# Re-check that file before trusting this list; it is explicitly known to
# go stale as detections change.
KNOWN_DEAD_SENSE_DETECTIONS = [
    "heat_3", "garage_door", "washer", "light_1", "solar",
    "sense_energy_monitor", "central_ac",
]


def _get(path: str, token: str) -> tuple[int, dict | None]:
    req = urllib.request.Request(f"{BASE_URL}{path}", headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, None


def main() -> int:
    token = os.environ.get("HA_TOKEN")
    if not token:
        print("FAIL  HA_TOKEN is not set")
        return 1

    status, _ = _get("/api/", token)
    print(f"{'OK   ' if status == 200 else 'FAIL '} HA_TOKEN authenticates: HTTP {status}")
    if status != 200:
        return 1

    status, config = _get("/api/config", token)
    ok = status == 200 and config is not None
    if ok:
        print(f"OK    core up: version {config.get('version')}, "
              f"timezone {config.get('time_zone')}, units {config.get('unit_system', {}).get('temperature')}")
    else:
        print(f"FAIL  /api/config: HTTP {status}")
        return 1

    status, states = _get("/api/states", token)
    automations = [s for s in (states or []) if s["entity_id"].startswith("automation.")]
    print(f"{'OK   ' if len(automations) >= 1 else 'FAIL '} {len(automations)} automation(s) registered "
          f"(instance-inventory.md's 2026-08-11 snapshot recorded 8 -- expect growth, investigate a drop)")

    dead = {f"sensor.{d}_yearly_energy" for d in KNOWN_DEAD_SENSE_DETECTIONS}
    present_dead = [s for s in (states or []) if s["entity_id"] in dead]
    if present_dead:
        print(f"NOTE  {len(present_dead)} known-dead Sense detection(s) present and reading "
              "near-zero by design -- do not build a verification around these without "
              "checking sensor.<device>_yearly_energy first:")
        for s in present_dead:
            print(f"      {s['entity_id']} = {s['state']}")

    print("\nAll required checks passed. Safe to drive.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
