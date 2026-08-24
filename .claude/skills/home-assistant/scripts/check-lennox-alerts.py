"""Check what Lennox alert codes (if any) are currently active on either
CasaSolar thermostat: South ("Main House") or North ("Office Wing").

Reads the coarse `_alert` severity sensor plus the `_active_alerts` sensor's
`alert_list` attribute for both units directly over REST -- the same two
entities `automation.lennox_thermostat_alert` and the Homie dashboard's
Climate badge use. See lennox-thermostat-alerts.md in the docs repo for why
`_alert` (console-accurate severity) and `_active_alerts` (best-effort
per-code detail) can disagree.

Usage:
  python3 check-lennox-alerts.py                # both units, everything active
  python3 check-lennox-alerts.py --unit south    # one unit only
  python3 check-lennox-alerts.py --code 312      # exit 0 if that code is active
                                                  # on a checked unit, 1 otherwise
"""

import argparse
import asyncio
import os
import sys

import aiohttp

URL = os.environ.get("HA_URL", "http://hass.ehlke.net")
TOKEN = os.environ["HA_TOKEN"]

UNITS = {
    "south": {
        "label": "South (Main House)",
        "alert": "sensor.basement_casasolar_south_casasolar_south_alert",
        "active": "sensor.basement_casasolar_south_casasolar_south_active_alerts",
    },
    "north": {
        "label": "North (Office Wing)",
        "alert": "sensor.basement_casasolar_north_casasolar_north_alert",
        "active": "sensor.basement_casasolar_north_casasolar_north_active_alerts",
    },
}


async def fetch_state(session, entity_id):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    async with session.get(f"{URL}/api/states/{entity_id}", headers=headers) as resp:
        resp.raise_for_status()
        return await resp.json()


async def run(unit_keys, code_filter):
    found_code = False
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
        for key in unit_keys:
            unit = UNITS[key]
            alert = await fetch_state(session, unit["alert"])
            active = await fetch_state(session, unit["active"])
            alert_list = active.get("attributes", {}).get("alert_list", [])

            print(unit["label"])
            print(f"  Severity (_alert): {alert['state']}")
            if not alert_list:
                print("  Active alert codes: none")
            else:
                print("  Active alert codes:")
                for a in alert_list:
                    is_match = code_filter is not None and a.get("code") == code_filter
                    if is_match:
                        found_code = True
                    marker = "  <-- match" if is_match else ""
                    print(f"    {a.get('code')}: {a.get('message')} (priority: {a.get('priority')}){marker}")
            print()

    return 0 if code_filter is None or found_code else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--unit", choices=sorted(UNITS), help="Check only one unit (default: both)")
    parser.add_argument(
        "--code", type=int, help="Exit 0 if this code is active on a checked unit, 1 otherwise"
    )
    args = parser.parse_args()
    keys = [args.unit] if args.unit else list(UNITS)
    sys.exit(asyncio.run(run(keys, args.code)))
