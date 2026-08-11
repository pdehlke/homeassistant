"""Rebuild a domain dashboard: a level 2 area grid plus one level 3 leaf per area.

This implements the Crestron touch panel navigation model that pde's system uses:

    level 1   cards per domain          (A/V, Climate, Lights, Alarm)
    level 2   cards per area            <- the dashboard's main view
    level 3   one domain in one area    <- a subview per populated area

Level 1 is not built here; it is Tablet Home, a separate hand-authored dashboard, see
dashboard-tablet-home.md in the pdehlke/homeassistant repo. This script's level 2 view
carries a title-only heading and each level 3 leaf a back button for that dashboard's
sake: its kiosk-mode setup hides HA's native top app bar, which used to carry both.

Every area gets a level 2 card so the dashboard doubles as a migration checklist,
but only areas that actually contain entities of the domain are tappable. Omitting
tap_action is genuinely inert: hui-area-card falls back to {action: "none"}, and
hasAction() reports false for that, so the card renders without a ripple.

The DOMAINS table below is the only domain-specific part. Adding a domain means
adding a block there. A/V needed one exception: the area card cannot control
media_player, so area_control is optional and area_card() skips the inline toggle
when it is None.

Usage:
    export HA_URL=http://hass.ehlke.net:8123   # optional, this is the default
    export HA_TOKEN=...                             # required
    export HA_BACKUP_DIR=/path/to/scratchpad        # optional, defaults to cwd
    python3 rebuild-domain-dashboard.py lights --dry-run
    python3 rebuild-domain-dashboard.py lights
"""

import asyncio
import datetime
import json
import os
import pathlib
import sys

import aiohttp

URL = os.environ.get("HA_URL", "http://hass.ehlke.net:8123")
TOKEN = os.environ["HA_TOKEN"]
WS = URL.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
BACKUP_DIR = pathlib.Path(os.environ.get("HA_BACKUP_DIR", "."))

# Per-domain configuration. Everything domain-specific lives here.
#
# presets become area-targeted buttons on the leaf. They deliberately target an
# area rather than named entities, so they need no per-room data and cover any
# fixture added to that room later.
DOMAINS = {
    "lights": {
        "dashboard": "dashboard-lights",
        "view_title": "Lights",
        "view_path": "lights",
        "view_icon": "m3rf:lightbulb",
        "entity_domains": ("light",),
        "leaf_suffix": "Lights",
        "area_control": "light",          # area-controls feature on the level 2 card
        "tile_feature": "light-brightness",  # inline slider on each leaf tile
        "presets": [
            {"name": "On/Off", "icon": "m3rf:power-settings-new",
             "action": "script.smart_toggle_lights"},
            {"name": "Low", "icon": "m3rf:brightness-3",
             "action": "light.turn_on", "data": {"brightness_pct": 25}},
            {"name": "Medium", "icon": "m3rf:brightness-5",
             "action": "light.turn_on", "data": {"brightness_pct": 60}},
            {"name": "Bright", "icon": "m3rf:brightness-7",
             "action": "light.turn_on", "data": {"brightness_pct": 100}},
        ],
    },
    "av": {
        "dashboard": "dashboard-av",
        "view_title": "A/V",
        "view_path": "av",
        "view_icon": "m3rf:surround-sound",
        "entity_domains": ("media_player",),
        "leaf_suffix": "A/V",
        "area_control": None,   # the area card has no media_player control, see area_card()
        "tile_feature": "media-player-volume-slider",
        "presets": [
            {"name": "All Off", "icon": "m3rf:power-settings-new",
             "action": "media_player.turn_off"},
            {"name": "Play", "icon": "m3rf:play-arrow",
             "action": "media_player.media_play"},
            {"name": "Pause", "icon": "m3rf:pause",
             "action": "media_player.media_pause"},
            {"name": "Mute", "icon": "m3rf:volume-off",
             "action": "media_player.volume_mute",
             "data": {"is_volume_muted": True}},
        ],
    },
}

# Floors top to bottom. Unlisted floors are appended, then floorless areas last.
FLOOR_ORDER = ["main_floor", "garage"]

# Areas within a floor, in walk-through order. Unlisted areas are appended.
AREA_ORDER = [
    "entry", "living_room", "kitchen", "dining_room", "primary_suite",
    "guest_suite", "office", "gym", "courtyard", "outside",
    "north_mechanical_closet", "garage", "garage_mechanical_closet",
]

# Optional extra preset rows on a leaf, one row per group, for areas that hold more
# than one logically distinct fixture group HA has no area-nesting to express
# (see area-floor-layout.md on why areas cannot nest). Each group is a label, not
# an entity list, for the same reason room-wide presets are area-targeted rather
# than entity-targeted: it survives fixtures being renamed or added later. Labels
# themselves are created by hand (config/label_registry/create), same one-time
# step as creating the area itself; this table only says which labels get a row
# and on which area's leaf.
AREA_GROUP_PRESETS = {
    "primary_suite": [
        {"name": "Bedroom", "label_id": "bedroom", "icon": "m3rf:bed"},
        {"name": "Bath", "label_id": "bath", "icon": "m3rf:bathtub"},
    ],
}

# columns is out of the section's 12-per-column-span grid, so 4 of 24 puts six
# cards per row. rows 3 measured 163x184px (ratio 0.89) at a 1600px viewport.
CARD_COLUMNS = 4
CARD_ROWS = 3
MAX_COLUMNS = 2  # with column_span == MAX_COLUMNS each section fills a row and stacks

FALLBACK_FLOOR_ICON = "mdi:floor-plan"


def rank(item_id, order):
    """Position in an explicit order list; unlisted items sort to the end, stably."""
    return order.index(item_id) if item_id in order else len(order)


def entity_area(entity, device_area):
    """An entity's area: its own when set, else inherited from its device."""
    return entity.get("area_id") or device_area.get(entity.get("device_id"))


def group_by_area(entities, devices, domains):
    """{area_id: [entity_id, ...]} for entities in the given domains."""
    device_area = {d["id"]: d.get("area_id") for d in devices}
    out = {}
    for e in entities:
        if e["entity_id"].split(".")[0] not in domains:
            continue
        if e.get("disabled_by") or e.get("hidden_by"):
            continue
        area = entity_area(e, device_area)
        if area:
            out.setdefault(area, []).append(e["entity_id"])
    for ids in out.values():
        ids.sort()
    return out


# ---------------------------------------------------------------- level 2


def area_card(area, cfg, populated):
    """Compact area card. Only populated areas are tappable or get a toggle."""
    card = {
        "type": "area",
        "area": area["area_id"],
        "display_type": "compact",
        "vertical": True,
        "grid_options": {"rows": CARD_ROWS, "columns": CARD_COLUMNS},
    }
    if populated:
        card["tap_action"] = {
            "action": "navigate",
            "navigation_path": f"/{cfg['dashboard']}/{leaf_path(area['area_id'])}",
        }
        # area_control is optional because the area card cannot control every domain.
        # AREA_CONTROL_DOMAINS in the frontend is light, fan, cover-* and switch only,
        # so a domain like media_player gets a tappable card with no inline toggle
        # rather than a feature that silently does nothing.
        if cfg.get("area_control"):
            card["features"] = [
                {"type": "area-controls", "controls": [cfg["area_control"]]}
            ]
            card["features_position"] = "inline"
    return card


def bare_section(cards):
    return {"type": "grid", "column_span": MAX_COLUMNS, "cards": cards}


def section(heading, icon, cards):
    return bare_section(
        [{"type": "heading", "heading": heading,
          "heading_style": "title",
          "icon": icon or FALLBACK_FLOOR_ICON}] + cards
    )


def build_level2(floors, areas, by_area, cfg, header):
    # A title-only heading, no cards under it. With kiosk-mode hiding the native
    # HA header (the Tablet user does, see dashboard-tablet-home.md), the view's
    # own title never renders anywhere, and every domain dashboard's floor
    # sections look identical ("Main Floor", "Garage" regardless of domain). This
    # is the only in-page thing that says which domain you're looking at.
    sections = [section(cfg["view_title"], cfg["view_icon"], [])]

    by_floor = {}
    for area in areas:
        by_floor.setdefault(area.get("floor_id"), []).append(area)
    for group in by_floor.values():
        group.sort(key=lambda a: (rank(a["area_id"], AREA_ORDER), a["name"].lower()))

    for floor in sorted(floors, key=lambda f: rank(f["floor_id"], FLOOR_ORDER)):
        group = by_floor.get(floor["floor_id"])
        if group:
            sections.append(section(
                floor["name"], floor.get("icon"),
                [area_card(a, cfg, bool(by_area.get(a["area_id"]))) for a in group]))

    orphans = by_floor.get(None)
    if orphans:
        sections.append(section(
            "Other areas", None,
            [area_card(a, cfg, bool(by_area.get(a["area_id"]))) for a in orphans]))

    return {
        "title": cfg["view_title"],
        "path": cfg["view_path"],
        "icon": cfg["view_icon"],
        "type": "sections",
        "max_columns": MAX_COLUMNS,
        "header": header,
        "sections": sections,
    }


# ---------------------------------------------------------------- level 3


def leaf_path(area_id):
    return f"area-{area_id}"


def preset_card(preset, target):
    """Button targeting an area or a label. No per-fixture entity data needed.

    A `script.*` action is the one exception: scripts take their target as
    ordinary fields, not a service target, so `target` here gets remapped to
    `target_area_id` / `target_label_id` data instead of a `target:` block.
    Not `area_id` / `label_id` — those collide with HA's own built-in Jinja
    lookup functions of the same names (see smart_toggle_lights), so an unset
    field silently resolves to that function object instead of Undefined
    rather than raising anything, and the bug it causes is very quiet.
    """
    action = preset["action"]
    if action.startswith("script."):
        tap = {
            "action": "perform-action",
            "perform_action": action,
            "data": {f"target_{k}": v for k, v in target.items()},
        }
    else:
        tap = {
            "action": "perform-action",
            "perform_action": action,
            "target": target,
        }
        if preset.get("data"):
            tap["data"] = preset["data"]
    return {
        "type": "button",
        "name": preset["name"],
        "icon": preset["icon"],
        "show_state": False,
        "tap_action": tap,
        "grid_options": {"columns": 6, "rows": 1},
    }


def back_card(cfg):
    """Full-width breadcrumb bar back to the level 2 view.

    A subview's native back arrow lives in HA's own top app bar, which
    kiosk-mode hides for the Tablet user (see dashboard-tablet-home.md), along
    with everything else up there. Without this, there is no way off a leaf at
    all for that user. Its own section, not mixed into the preset row, so it
    reads as navigation rather than another device action.
    """
    return {
        "type": "button",
        "name": cfg["view_title"],
        "icon": "m3rf:arrow-back",
        "show_state": False,
        "tap_action": {
            "action": "navigate",
            "navigation_path": f"/{cfg['dashboard']}/{cfg['view_path']}",
        },
        "grid_options": {"columns": MAX_COLUMNS * 12, "rows": 1},
    }


def build_leaf(area, entity_ids, scene_ids, cfg):
    """A level 3 subview: back nav, presets, any group presets, real scenes, then tiles."""
    title = f"{area['name']} {cfg['leaf_suffix']}"
    sections = [
        bare_section([back_card(cfg)]),
        section(title, area.get("icon"),
                [preset_card(p, {"area_id": area["area_id"]}) for p in cfg["presets"]]),
    ]

    for group in AREA_GROUP_PRESETS.get(area["area_id"], []):
        sections.append(section(
            group["name"], group["icon"],
            [preset_card(p, {"label_id": group["label_id"]}) for p in cfg["presets"]]))

    if scene_ids:
        sections.append(section("Scenes", "m3rf:movie", [
            {"type": "tile", "entity": s, "grid_options": {"columns": 6, "rows": 1}}
            for s in scene_ids
        ]))

    sections.append(section(cfg["leaf_suffix"], cfg["view_icon"], [
        {
            "type": "tile",
            "entity": eid,
            "features": [{"type": cfg["tile_feature"]}],
            "features_position": "bottom",
            "grid_options": {"columns": 12, "rows": 2},
        }
        for eid in entity_ids
    ]))

    return {
        "title": title,
        "path": leaf_path(area["area_id"]),
        "icon": area.get("icon") or cfg["view_icon"],
        "type": "sections",
        "max_columns": MAX_COLUMNS,
        "subview": True,
        "sections": sections,
    }


# ---------------------------------------------------------------- driver


async def request(ws, msg_id, payload):
    await ws.send_json({"id": msg_id, **payload})
    while True:
        msg = await ws.receive_json()
        if msg.get("id") == msg_id and msg.get("type") == "result":
            return msg


async def run(domain, dry_run):
    cfg = DOMAINS[domain]
    dashboard = cfg["dashboard"]

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS, heartbeat=30) as ws:
            assert (await ws.receive_json())["type"] == "auth_required"
            await ws.send_json({"type": "auth", "access_token": TOKEN})
            if (await ws.receive_json())["type"] != "auth_ok":
                print("auth failed")
                return 1

            reads = {
                "config": {"type": "lovelace/config", "url_path": dashboard},
                "floors": {"type": "config/floor_registry/list"},
                "areas": {"type": "config/area_registry/list"},
                "entities": {"type": "config/entity_registry/list"},
                "devices": {"type": "config/device_registry/list"},
            }
            got = {}
            for i, (label, payload) in enumerate(reads.items(), start=1):
                msg = await request(ws, i, payload)
                if not msg.get("success"):
                    print(f"could not read {label}: {msg}")
                    return 1
                got[label] = msg["result"]

            config = got["config"]
            if not config.get("views"):
                print("dashboard has no views, refusing to save")
                return 1

            # The header is authored by hand and never generated here.
            header = config["views"][0].get("header")
            if not header:
                print("live view has no header card, refusing to save")
                print("this script only preserves a header, it never creates one")
                return 1

            by_area = group_by_area(got["entities"], got["devices"],
                                    set(cfg["entity_domains"]))
            scenes_by_area = group_by_area(got["entities"], got["devices"], {"scene"})

            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = BACKUP_DIR / f"backup-{dashboard}-{stamp}.json"
            backup.write_text(json.dumps(config, indent=2))
            print(f"backup written: {backup}")

            areas = got["areas"]
            level2 = build_level2(got["floors"], areas, by_area, cfg, header)

            ordered = sorted(areas, key=lambda a: (rank(a["floor_id"], FLOOR_ORDER),
                                                   rank(a["area_id"], AREA_ORDER),
                                                   a["name"].lower()))
            leaves = [
                build_leaf(a, by_area[a["area_id"]],
                           scenes_by_area.get(a["area_id"], []), cfg)
                for a in ordered if by_area.get(a["area_id"])
            ]

            # A Lovelace save replaces the whole config, so anything hand-authored
            # at the config root (kiosk_mode, for one) has to be carried forward
            # explicitly or it silently disappears on the next regeneration. Only
            # "views" is actually this script's to own.
            updated = {**config, "views": [level2] + leaves}

            for sec in level2["sections"]:
                names = [f"{c['area']}{'*' if 'tap_action' in c else ''}"
                         for c in sec["cards"][1:]]
                print(f"  {sec['cards'][0]['heading']}: {', '.join(names)}")
            print("  (* = populated, tappable, has a leaf)")
            for leaf in leaves:
                area_id = leaf["path"].removeprefix("area-")
                n_groups = len(AREA_GROUP_PRESETS.get(area_id, []))
                baseline = 3 + n_groups  # back-nav + presets + N group-preset rows + entities
                n = len(leaf["sections"][-1]["cards"]) - 1
                s = len(leaf["sections"]) - baseline
                extra = f", {n_groups} group preset row(s)" if n_groups else ""
                print(f"  leaf /{dashboard}/{leaf['path']}: {n} entities, "
                      f"{s} scene section(s){extra}")

            unlisted = [a["area_id"] for a in areas if a["area_id"] not in AREA_ORDER]
            if unlisted:
                print(f"note: not in AREA_ORDER, appended: {', '.join(unlisted)}")

            if dry_run:
                print("dry run, not saving")
                return 0

            saved = await request(ws, 90, {
                "type": "lovelace/config/save",
                "url_path": dashboard,
                "config": updated,
            })
            print("save result:", json.dumps(saved))
            return 0 if saved.get("success") else 1


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args or args[0] not in DOMAINS:
        print(f"usage: {sys.argv[0]} <{'|'.join(DOMAINS)}> [--dry-run]")
        sys.exit(2)
    sys.exit(asyncio.run(run(args[0], "--dry-run" in sys.argv)))
