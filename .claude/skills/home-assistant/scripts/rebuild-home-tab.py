"""Rebuild one tab (view) on the Home dashboard: an area grid plus one leaf per
populated area, generated from the live HA registries the same way
rebuild-domain-dashboard.py builds a standalone domain dashboard. This script
is based directly on that one; the differences all come from Home being meant
as the self-contained main kiosk dashboard (see dashboard-tablet-home.md and
the home-dashboard-main-kiosk memory), not a single-domain dashboard of its
own:

  - Home shows its native top app bar (kiosk-mode only hides the sidebar for
    the Tablet user, not the header, see dashboard-tablet-home.md), so there
    is no title-only heading section here the way there is on
    rebuild-domain-dashboard.py's level 2 view; the tab strip already says
    which tab you're on. Instead of a hand-authored header *card* to
    preserve, this preserves the view's *badges*, whatever hand-picked chips
    pde puts at the top of the tab (device trackers, the alarm panel,
    weather, ...). Never invented here, same as the header on the original
    script: read from the live view and carried forward untouched, empty if
    there are none yet.
  - Every navigate action targets /vision-sample/... instead of the domain's
    own standalone dashboard (/dashboard-lights/..., /dashboard-av/...), so
    Home never sends a viewer somewhere with different kiosk-mode chrome and
    a home icon that points back to Tablet Home instead of Home.
  - Leaf views are namespaced <domain>-area-<area_id>, not area-<area_id>.
    dashboard-lights and dashboard-av each host only their own leaves, so the
    plain name never collides; Home hosts leaves from more than one domain in
    one flat views list, and area-kitchen would otherwise collide between a
    Lights leaf and an A/V leaf.
  - Only the target domain's own tab and its leaves are touched. Every other
    Home view (the other tabs, other domains' leaves) is read back and
    written out unchanged, in its original position, so the visible tab
    order never shifts. The standalone domain dashboard is only ever read,
    never written, by this script.

The DOMAINS table is copied from rebuild-domain-dashboard.py's, minus the
`dashboard`/`view_path` fields (Home never navigates to the standalone
dashboard) and plus `home_view_path`, the path of the existing Home tab this
domain targets. Keep the two tables' domain-specific values in sync by hand;
nothing enforces it, the same drift risk dashboard-tablet-home.md already
notes for Tablet Home's and the domain dashboards' duplicated content.

Only domains with a DOMAINS entry can be rebuilt. Climate and Alarm are not
here because dashboard-lennox-home and dashboard-alarm-system are
hand-authored with no generator of their own to base a Home version on (see
dashboard-tablet-home.md); Home's Climate and Alarm tabs are not touched by
this script.

Usage:
    export HA_URL=http://homeassistant.local:8123   # optional, this is the default
    export HA_TOKEN=...                             # required
    export HA_BACKUP_DIR=/path/to/scratchpad        # optional, defaults to cwd
    python3 rebuild-home-tab.py lights --dry-run
    python3 rebuild-home-tab.py lights
"""

import asyncio
import datetime
import json
import os
import pathlib
import sys

import aiohttp

URL = os.environ.get("HA_URL", "http://homeassistant.local:8123")
TOKEN = os.environ["HA_TOKEN"]
WS = URL.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
BACKUP_DIR = pathlib.Path(os.environ.get("HA_BACKUP_DIR", "."))

HOME_DASHBOARD = "vision-sample"

# Per-domain configuration, copied from rebuild-domain-dashboard.py's DOMAINS
# table (see the note above about keeping the two in sync) with home_view_path
# added: the path of the Home tab this domain fills in, which must already
# exist as a view on Home before this script will touch it.
DOMAINS = {
    "lights": {
        "home_view_path": "kitchen",
        "view_title": "Lights",
        "view_icon": "m3rf:lightbulb",
        "entity_domains": ("light",),
        "leaf_suffix": "Lights",
        "area_control": "light",
        "tile_feature": "light-brightness",
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
        "home_view_path": "a-v",
        "view_title": "A/V",
        "view_icon": "m3rf:surround-sound",
        "entity_domains": ("media_player",),
        "leaf_suffix": "A/V",
        "area_control": None,
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

# Same area-group presets as rebuild-domain-dashboard.py; see that script's
# comment on why these are label-targeted rather than entity-targeted.
AREA_GROUP_PRESETS = {
    "primary_suite": [
        {"name": "Bedroom", "label_id": "bedroom", "icon": "m3rf:bed"},
        {"name": "Bath", "label_id": "bath", "icon": "m3rf:bathtub"},
    ],
}

CARD_COLUMNS = 4
CARD_ROWS = 3
MAX_COLUMNS = 2  # with column_span == MAX_COLUMNS each section fills a row and stacks

# Leaf entity tiles, sized down from rebuild-domain-dashboard.py's columns: 12,
# rows: 2 (2 tiles per row). That sizing was never checked against the actual
# target: the wall tablet's 1280x800 screen. Screenshotted live there on
# 2026-08-06 (logged in as Tablet): 5 tiles at columns: 12 filled nearly the
# whole 800px height on their own. columns: 8 (3 per row) noticeably shrinks
# them without touching rows, so the brightness slider feature keeps its full
# height, still an easy touch target.
LEAF_TILE_COLUMNS = 8
LEAF_TILE_ROWS = 2

# Preset buttons. grid_options: {rows: 1} does not bound their actual height:
# hui-button-card's own getGridOptions() (home-assistant/frontend,
# src/panels/lovelace/cards/hui-button-card.ts) hardcodes min_rows: 2 whenever
# a button shows both an icon and a name or state, with no config override,
# so the card's outer grid cell is pinned to 2 row-tracks (~120px measured
# live) no matter what rows/grid_options says. A card_mod that shrinks the
# button's own rendered height (tried first) only shrinks the content inside
# that still-120px cell, confirmed by inspecting the wrapper element's own
# `grid-row` directly (`span 2`, unaffected by any card_mod height): it looks
# smaller but leaves the same dead space behind, which is the "wasted space
# between rows" pde flagged after the first pass. The only way to actually
# reach the smaller getGridOptions() branch (min_rows: 1) is show_name: false,
# which is set on the card itself below, not something CSS can do from
# outside the card. card_mod stays as a supplementary cap on the icon, which
# still defaults to `--mdc-icon-size: 100%` of whatever box it ends up with.
PRESET_BUTTON_HEIGHT = 56
PRESET_ICON_SIZE = 24

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


# ---------------------------------------------------------------- the tab


def area_card(area, cfg, domain, populated):
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
            "navigation_path": f"/{HOME_DASHBOARD}/{leaf_path(domain, area['area_id'])}",
        }
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


def build_home_tab(floors, areas, by_area, cfg, domain, badges):
    # No title-only heading here: Home never hides its header, so the tab
    # strip already carries the title. Compare rebuild-domain-dashboard.py's
    # build_level2, which adds one for exactly the opposite reason.
    sections = []

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
                [area_card(a, cfg, domain, bool(by_area.get(a["area_id"]))) for a in group]))

    orphans = by_floor.get(None)
    if orphans:
        sections.append(section(
            "Other areas", None,
            [area_card(a, cfg, domain, bool(by_area.get(a["area_id"]))) for a in orphans]))

    view = {
        "title": cfg["view_title"],
        "path": cfg["home_view_path"],
        "icon": cfg["view_icon"],
        "type": "sections",
        "max_columns": MAX_COLUMNS,
        "sections": sections,
        "cards": [],
    }
    if badges:
        view["badges"] = badges
    return view


# ---------------------------------------------------------------- leaves


def leaf_path(domain, area_id):
    return f"{domain}-area-{area_id}"


def preset_card(preset, target):
    """Button targeting an area or a label. See rebuild-domain-dashboard.py's
    version of this function for why script.* actions remap target to
    target_area_id/target_label_id data instead of a target: block."""
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
        "show_name": False,
        "show_state": False,
        "tap_action": tap,
        "card_mod": {
            "style": (
                f":host {{ height: {PRESET_BUTTON_HEIGHT}px !important; }}\n"
                f"ha-card {{ height: {PRESET_BUTTON_HEIGHT}px !important; "
                f"min-height: {PRESET_BUTTON_HEIGHT}px !important; padding: 4px 0 !important; }}\n"
                f"ha-state-icon {{ --mdc-icon-size: {PRESET_ICON_SIZE}px !important; }}\n"
            )
        },
        "grid_options": {"columns": 6, "rows": 1},
    }


def build_leaf(area, entity_ids, scene_ids, cfg, domain):
    """A subview: presets, any group presets, real scenes, then tiles.

    No back-button section here, unlike rebuild-domain-dashboard.py's leaves.
    Those exist for the kiosk-moded domain dashboards, where hide_header
    removes HA's native subview back arrow along with the rest of the header
    (see dashboard-tablet-home.md). Home never hides its header, so the
    native back arrow is there for every leaf without this script adding one.
    """
    title = f"{area['name']} {cfg['leaf_suffix']}"
    sections = [
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
            "grid_options": {"columns": LEAF_TILE_COLUMNS, "rows": LEAF_TILE_ROWS},
        }
        for eid in entity_ids
    ]))

    return {
        "title": title,
        "path": leaf_path(domain, area["area_id"]),
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

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(WS, heartbeat=30) as ws:
            assert (await ws.receive_json())["type"] == "auth_required"
            await ws.send_json({"type": "auth", "access_token": TOKEN})
            if (await ws.receive_json())["type"] != "auth_ok":
                print("auth failed")
                return 1

            reads = {
                "config": {"type": "lovelace/config", "url_path": HOME_DASHBOARD},
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
            views = config.get("views") or []

            target = next((v for v in views if v.get("path") == cfg["home_view_path"]), None)
            if target is None:
                print(f"no existing Home view with path {cfg['home_view_path']!r}; "
                      f"this script only rebuilds a tab that's already there, it never "
                      f"creates one")
                return 1

            # Badges are hand-picked by pde and never invented here, same as the
            # header on rebuild-domain-dashboard.py. Carried forward as-is.
            badges = target.get("badges") or []
            print(f"preserving {len(badges)} badge(s) from the live '{target['title']}' tab: "
                  f"{[b.get('entity', b.get('type')) for b in badges]}")

            by_area = group_by_area(got["entities"], got["devices"],
                                     set(cfg["entity_domains"]))
            scenes_by_area = group_by_area(got["entities"], got["devices"], {"scene"})

            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = BACKUP_DIR / f"backup-{HOME_DASHBOARD}-{stamp}.json"
            backup.write_text(json.dumps(config, indent=2))
            print(f"backup written: {backup}")

            areas = got["areas"]
            new_tab = build_home_tab(got["floors"], areas, by_area, cfg, domain, badges)

            ordered = sorted(areas, key=lambda a: (rank(a["floor_id"], FLOOR_ORDER),
                                                    rank(a["area_id"], AREA_ORDER),
                                                    a["name"].lower()))
            new_leaves = [
                build_leaf(a, by_area[a["area_id"]],
                           scenes_by_area.get(a["area_id"], []), cfg, domain)
                for a in ordered if by_area.get(a["area_id"])
            ]

            # Rebuild in place: keep every other view (other tabs, other domains'
            # leaves) untouched and in its original position, so the visible tab
            # order never shifts. Drop only this domain's old tab and old leaves,
            # reinsert the rebuilt tab at the same index, append the fresh leaves.
            leaf_prefix = f"{domain}-area-"
            kept = []
            target_index = None
            for v in views:
                if v.get("path") == cfg["home_view_path"]:
                    target_index = len(kept)
                    continue
                if v.get("subview") and v.get("path", "").startswith(leaf_prefix):
                    continue
                kept.append(v)

            new_views = kept[:target_index] + [new_tab] + kept[target_index:] + new_leaves

            # A Lovelace save replaces the whole config, so anything hand-authored
            # at the config root (kiosk_mode, for one) has to be carried forward
            # explicitly or it silently disappears on the next regeneration, the
            # same lesson rebuild-domain-dashboard.py's comment and
            # dashboard-navigation-model.md's postmortem already recorded once.
            updated = {**config, "views": new_views}

            for sec in new_tab["sections"]:
                names = [f"{c['area']}{'*' if 'tap_action' in c else ''}"
                         for c in sec["cards"][1:]]
                print(f"  {sec['cards'][0]['heading']}: {', '.join(names)}")
            print("  (* = populated, tappable, has a leaf)")
            for leaf in new_leaves:
                area_id = leaf["path"].removeprefix(leaf_prefix)
                n_groups = len(AREA_GROUP_PRESETS.get(area_id, []))
                baseline = 2 + n_groups  # presets + N group-preset rows + entities, no back-nav
                n = len(leaf["sections"][-1]["cards"]) - 1
                s = len(leaf["sections"]) - baseline
                extra = f", {n_groups} group preset row(s)" if n_groups else ""
                print(f"  leaf /{HOME_DASHBOARD}/{leaf['path']}: {n} entities, "
                      f"{s} scene section(s){extra}")

            unlisted = [a["area_id"] for a in areas if a["area_id"] not in AREA_ORDER]
            if unlisted:
                print(f"note: not in AREA_ORDER, appended: {', '.join(unlisted)}")

            other_view_count = len(new_views) - 1 - len(new_leaves)
            print(f"other Home views left untouched: {other_view_count}")

            if dry_run:
                print("dry run, not saving")
                return 0

            saved = await request(ws, 90, {
                "type": "lovelace/config/save",
                "url_path": HOME_DASHBOARD,
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
