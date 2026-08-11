# Home: the tabbed kiosk dashboard

The dashboard the `Tablet` kiosk user lands on is Home (`url_path: vision-sample`, titled "Home"
in the UI, the former Vision Sample theme demo). Rather than a separate level 1 root dashboard that
navigates out to four standalone domain dashboards, Home carries the whole hierarchy itself: a
native view-tab strip (Home, Lights, A/V, Alarm, Climate) stands in for level 1, and each tab holds
that domain's level 2 area grid and level 3 leaves as its own content, generated onto Home's own
views rather than read from elsewhere. Retargeted here 2026-08-05, on Home Assistant 2026.7.4; the
generator that builds a tab, `scripts/rebuild-home-tab.py`, followed 2026-08-06.

## Why tabs instead of a root dashboard

Home is meant to be the self-contained kiosk experience for the eventual wall-mounted touch panel
(see [crestron-strategy.md](../crestron/crestron-strategy.md#touch-panels-replacing-the-tsw-752s)), which rules
out leaning on the standalone domain dashboards (`dashboard-lights`, `dashboard-av`,
`dashboard-lennox-home`, `dashboard-alarm-system`) for navigation the way a level 1 root dashboard
did. Every `navigate` action inside Home's tabs and leaves targets `/vision-sample/...`, never one
of those other dashboards, both for the area cards added to a tab and for the leaves' own back
paths.

That leaves the standalone domain dashboards with one job: **generation source**, not a destination.
`rebuild-domain-dashboard.py` still reads the live registries and writes them directly, and
`rebuild-home-tab.py` is built on the same approach for Home's own tabs (it does not read the
standalone dashboard's saved config; both scripts read the same live floor, area, entity and device
registries independently). Nobody is expected to land on `dashboard-lights` or the other three
directly anymore. Their own kiosk chrome (a `hide_header` + `hide_sidebar` `kiosk_mode` block, the
header's home-icon button, each leaf's explicit back button) is still live and still working, but it
is now stale: the home icon navigates to `/tablet-home`, a dashboard that is itself dead (see
below). Cleaning that chrome up, or removing it now that nothing depends on it, is outstanding work,
not done as part of this rewrite. See "Open questions" below.

## Superseded: Tablet Home, the root-dashboard approach

The first attempt at level 1, built 2026-08-05, was its own dashboard: `tablet-home`, titled
"Tablet Home," a 2x2 grid of four plain button cards (A/V, Climate, Lights, Alarm) in Crestron
top-screen order, each navigating to its domain's standalone dashboard. It came with a dedicated
kiosk chrome of its own: a non-admin `Tablet` user, the `NemesisRE/kiosk-mode` plugin hiding the
sidebar and header, a header home-icon and logout-icon pair, and per-leaf back buttons, all built to
compensate for the native chrome `kiosk_mode` was hiding.

It lasted less than a day. Once Home was chosen as the actual kiosk target, `Tablet`'s
`default_panel` was retargeted from `tablet-home` to `vision-sample` (see below), and nothing on
Home links back to Tablet Home. It still exists in Home Assistant, unreachable from anywhere in the
UI, and should be deleted rather than kept around; that cleanup has not been done yet. The
mechanisms it introduced (the kiosk user, the login-session dance for setting personal frontend
data, the kiosk-mode plugin choice, the shared card-based header recipe) all outlived it and are
described below and in [dashboard-header-card.md](dashboard-header-card.md), since Home and the
still-standing domain dashboards continue to use them.

## Setting Tablet's personal dashboard and theme

Two pieces of Tablet's frontend state, which dashboard is the default and which theme is active,
are personal `frontend/set_user_data`, not dashboard config, and Home Assistant exposes no
admin-callable way to set either for another user.

### Why this needs a session as Tablet

`frontend/set_user_data` (the command the frontend's own "set as default" profile option calls,
[`saveFrontendUserData` in `ha-pick-dashboard-row.ts`](https://github.com/home-assistant/frontend/blob/dev/src/panels/profile/ha-pick-dashboard-row.ts))
only ever writes the calling connection's own user; the server-side handler in
[`homeassistant/components/frontend/storage.py`](https://github.com/home-assistant/core/blob/dev/homeassistant/components/frontend/storage.py)
reads `connection.user.id` directly, with no `user_id` field in the command schema.
`frontend/set_system_data` exists and does take an override, but it is instance-wide: writing
`default_panel` there would make Home the default for every user, including pde's own admin login,
which was never the intent. The only path is a short-lived login as Tablet:

1. `POST /auth/login_flow` with `handler: ["homeassistant", null]` to start a username/password
   login.
2. `POST /auth/login_flow/<flow_id>` with the username and password, returning a short-lived
   authorization code.
3. `POST /auth/token` with `grant_type=authorization_code` to exchange the code for an
   `access_token` and `refresh_token`.
4. Open a WebSocket connection authenticated with that `access_token`, read the existing
   `frontend/get_user_data` value, and write back the changed key.
5. `POST /auth/revoke` with the `refresh_token` to end the session immediately rather than leaving a
   long-lived credential from a one-time setup step.

### Resolved dual-stack login issue

The two-step login flow once failed with `IP address changed` when consecutive requests used
`homeassistant.local`. Home Assistant records the requesting client address when a login flow is
created and rejects a later step if that address differs. The client was able to reach the server
over both IPv4 and IPv6, so separate requests could appear to originate from different addresses.

IPv6 has since been disabled for this installation, eliminating that route ambiguity. The literal
IPv4 workaround is obsolete. Use `homeassistant.local` for Home Assistant browser, HTTP API, and
WebSocket connections. Use `mass.local` for direct Music Assistant connections. Do not hardcode a
LAN address for either service.

### `default_panel`: retargeted from `tablet-home` to `vision-sample`

Set to `"tablet-home"` when that dashboard was built, then changed the same day to `"vision-sample"`
once Home became the target, both times via key `core` in `frontend/get_user_data` /
`frontend/set_user_data`. Read-back inside the same Tablet session confirmed both the old and new
values at the time of the change. Confirmed live afterward: logging in as `tablet` lands directly on
`/vision-sample/home`, no manual navigation.

### `theme`: Tablet never had one set, so it fell back to no background

Home's background image comes from the active theme, not the dashboard config. The instance runs
[`Nezz/homeassistant-visionos-theme`](https://raw.githubusercontent.com/Nezz/homeassistant-visionos-theme/refs/heads/master/themes/visionos.yaml),
which sets `lovelace-background: var(--background-image)` and a per-mode `background-image: url(...)`.
Theme selection is personal frontend user data, key `theme` instead of `core`, same
`saveFrontendUserData` mechanism under the hood. pde's own selection read back as
`{"dark": false, "theme": "visionos"}`; Tablet's had never been set (`null`), so Tablet was
rendering the instance's fallback theme, which has no background image, independent of anything
`kiosk_mode` or `hide_header` did. Fixed the same way as `default_panel`: a short-lived Tablet
session, `frontend/set_user_data` on key `theme` with `{"dark": false, "theme": "visionos"}`
mirroring pde's own, session revoked immediately after. Read-back inside that session confirmed
`null` before and the new value after; this was not re-confirmed with a live re-login to watch the
background actually render (see "Open questions" below).

## Kiosk chrome

### The kiosk-mode plugin

Home Assistant has no built-in way to hide the sidebar. The
[`NemesisRE/kiosk-mode`](https://github.com/NemesisRE/kiosk-mode) HACS plugin (v14.0.2, installed
2026-08-05) does, targeted per user rather than per dashboard so it follows the Tablet account
wherever it goes. `NemesisRE/kiosk-mode` is a continuation of `maykar/kiosk-mode`, which was
archived by its owner in 2022 and is no longer updated despite still carrying an "HACS-Default"
badge in its own README; `NemesisRE/kiosk-mode` is the actively maintained fork, still HACS-default
(not a custom repository add), with CI running against Home Assistant nightlies as of the version
installed here. Confirmed by fetching both READMEs directly rather than trusting either badge.

`user_settings` naming `Tablet` explicitly, rather than the also-available `non_admin_settings`
(which applies to every non-admin account with none named), was chosen so a future unrelated
non-admin account does not inherit kiosk behavior by accident; Tablet is currently the only
non-admin user, so the two are equivalent today. kiosk-mode matches `user_settings` entries on the
account's display name, not its username, which is why the block says `Tablet` and not `tablet`.

The `kiosk_mode` block lives at the root of a dashboard's saved config, a sibling of `views`, since
kiosk-mode reads its config per dashboard rather than once globally.

### Home sets `hide_sidebar` only, not `hide_header`

The four standalone domain dashboards, and the now-dead Tablet Home, all set both `hide_header` and
`hide_sidebar`, because each one built a full replacement for what the native header carries: a
card-based clock/date/weather header, a home-icon nav button, and (on leaves) an explicit back
button. Home is a stock multi-view dashboard with no such replacement, and its native header carries
a job those other dashboards don't ask of it: the row of view tabs (Home, Lights, A/V, Alarm,
Climate) is the only navigation between them.

Home originally inherited the same `hide_header: true` / `hide_sidebar: true` block used everywhere
else, copied over without adjusting it for a dashboard that has no replacement header. `hide_header`
doesn't distinguish "the tabs" from "the rest of the header"; it hides the whole native top app bar,
and took the tab strip with it, along with the menu button and everything else native-header.
Fixed by dropping `hide_header` from Home's `kiosk_mode` block and keeping only `hide_sidebar`:

```yaml
kiosk_mode:
  user_settings:
    - users: ["Tablet"]
      hide_sidebar: true
```

This is why Home's own tabs need none of the level 2/3 embellishments
[dashboard-navigation-model.md](dashboard-navigation-model.md) built for the standalone dashboards:
no title-only heading section (the tab strip already shows the current tab's title), and no
in-page back button on a leaf (the native subview back arrow, invisible on the standalone
dashboards, renders normally here since Home never hides its header). Confirmed live: reading the
saved config back showed `hide_header` present nowhere in Home's `kiosk_mode` block, and the same
regeneration removed a redundant "Lights" heading section and a hand-built back-button section from
the Lights tab and its leaves, both dead weight once the native chrome does that job.

## What's on each tab

### Home: the overview tab

The first tab, still titled "Home," carries a mix of live cards rather than one domain's content:
badges for Pete's phone (`device_tracker.pete_iphone`), the Gym media player, the
`alarm_control_panel.security` entity, and current temperature/humidity chips; a weather card and
the shopping-list to-do; a row of device tiles (Harmony Hub activity, the EV charger's connected
state and charge sensors, dryer and washer status); and a section with the North and South Lennox
thermostat cards, the solar-production and grid-export gauges
(see [vision-sample-pergola-solar-gauge.md](vision-sample-pergola-solar-gauge.md)), and the vacuum
tile. All of that is live, current data. The exceptions are the lights tiles (Pool Lights, Front
Door Light, Bedroom Lights, Kitchen Lights) and the front door lock tile, which are placeholders
until the Crestron lighting and lock integration lands; everything else on this tab reflects real
device state today.

### Lights: fully self-contained, generator-built

Home's Lights tab (`path: kitchen`, a leftover view-path name from before the tab had real content)
carries the same content as the standalone `dashboard-lights`, but copied in and made independent of
it rather than linked to it.

**The hand transplant.** The tab's original content, one stray `light.kitchen_lights` tile, was
replaced with `dashboard-lights`'s top-level sections (the area-card grid, `max_columns: 2`) and its
five `subview: true` leaves (Entry, Kitchen, Dining Room, Primary Suite, Office Lights), copied
unchanged. Every `navigation_path` inside the copied content, both the leaves' back paths and the
area cards' tap targets, was rewritten off `dashboard-lights` and onto Home's own path:

| Old | New |
| :--- | :--- |
| `/dashboard-lights/lights` (the leaves' back button) | `/vision-sample/kitchen` |
| `/dashboard-lights/area-<name>` (the area cards' tap targets) | `/vision-sample/area-<name>` |

`dashboard-lights` itself was left untouched; the two dashboards now carry duplicate content that
drifts independently if either is edited by hand. The tab's own title-only "Lights" heading, carried
over from `dashboard-lights`, was then dropped as redundant, per the header discussion above.
`dashboard-lights` keeps its own copy of that heading, since it still needs it.

**`scripts/rebuild-home-tab.py`**, added 2026-08-06, is the repeatable version of that transplant:
it builds a Home tab straight from the live floor/area/entity registries, the same way
`rebuild-domain-dashboard.py` builds a standalone dashboard, rather than by reading another
dashboard's saved config. It is based directly on that script, with everything domain-specific
(presets, entity domains, the tile feature, `AREA_ORDER`, `AREA_GROUP_PRESETS`) copied into its own
`DOMAINS` table, kept in sync with the original by hand. Three things differ, all consequences of
Home needing to stay self-contained and never hide its header:

- No title-only heading section.
- Every `navigate` action targets `/vision-sample/...`, never the standalone dashboard.
- Leaf views are named `<domain>-area-<area_id>` (`lights-area-kitchen`), not `area-<area_id>`:
  `dashboard-lights` only ever hosts its own leaves, so the plain name never collides there; Home
  hosts leaves from more than one domain in one flat `views` list, where `area-kitchen` would
  collide between a Lights leaf and a future A/V leaf.

It preserves the target tab's `badges` (device trackers, the alarm panel, weather chips) exactly as
found, never inventing them, the same principle as the header-preservation behavior in
`rebuild-domain-dashboard.py`, just for a different config key: Home has no per-tab header card, so
badges are its equivalent. It only rebuilds a tab that already exists (`home_view_path` in `DOMAINS`
must match a real view's `path`), and only touches that domain's tab and leaves; every other Home
view is read back and rewritten unchanged, at its original index, so the visible tab order (Home,
Lights, A/V, Alarm, Climate) never shifts.

**Tested against Lights, and a one-time cleanup it exposed.** Running
`python3 rebuild-home-tab.py lights` regenerated the tab and its five leaves correctly, badges
included, but left Home with 15 views instead of the expected 10: the five `area-*` leaves from the
hand transplant predate the script's `lights-area-*` naming, so its dedup logic (which only
recognizes its own prefix) never removed them, and they sat alongside the new ones as dead weight,
unreachable from any card. Fixed with a one-off script that deleted the five `area-*` paths by name,
backed up first, not folded into the generator since it can only ever happen once, right after
adopting the naming scheme. Confirmed by reading Home's config back afterward: 10 views, no
`navigation_path` anywhere referencing `dashboard-lights`, no leaf path under `/area-` missing the
`lights-` prefix, badges unchanged.

**The leaves' redundant back button was next to go.** `build_leaf()` still carried over
`rebuild-domain-dashboard.py`'s full-width back-button section, needed there because `hide_header`
removes the native subview back arrow. Home never hides its header, so every leaf already gets that
arrow for free; the hand-built button was pure duplication. Removed `back_card()` entirely and the
section that held it, so a leaf now opens straight on its title-and-presets row. The dry-run summary
printer's baseline section count was still counting the removed section and had started printing
`-1 scene section(s)`; fixed alongside it. Re-tested against Lights: no `m3rf:arrow-back` card
anywhere in any of the five leaves, section count per leaf down from 3 to 2 (plus one more for
Primary Suite's scene section, unchanged); view count, nav paths, and badges reconfirmed unchanged.

### Shrinking the leaves for a 1280x800 tablet

Verified in an actual browser, not just by reading config back: a short-lived Tablet login, a
Playwright storage-state file built from that session's access token, `resize 1280 800` to match
the wall tablet's assumed screen, then `goto` and `screenshot` on the live leaves.

**Entity tiles.** `rebuild-domain-dashboard.py`'s `columns: 12, rows: 2` (2 tiles per row) was never
checked against 1280x800; screenshotted live, 5 tiles at that size filled nearly the whole 800px
height on their own. Changed to `columns: 8` (3 per row) as new constants `LEAF_TILE_COLUMNS` /
`LEAF_TILE_ROWS` in `rebuild-home-tab.py`, leaving `rows` alone so the brightness-slider feature
keeps its full height. Re-screenshotted: the same leaf now ends around two-thirds of the way down
the screen instead of filling it.

**Preset buttons turned out to be the bigger problem.** The Primary Suite leaf, which has the main
preset row plus two `AREA_GROUP_PRESETS` rows (Bedroom, Bath), pushed the entity tiles below the
fold entirely, worse than the tiles ever were. `grid_options: {rows: 1}` looked like it should
already be as small as a button gets. The DOM had to be inspected directly (admin session, walking
every shadow root to reach inside `hui-button-card`) to find out why: a `rows: 1` button rendered at
120px tall, most of it an `ha-state-icon` with `--mdc-icon-size: 100%`, `hui-button-card`'s built-in
behavior of scaling its icon to fill whatever box it's handed rather than sizing to content.
`grid_options` never had a lever for that.

The first fix, `card_mod` pinning `:host` and `ha-card` to `56px` and capping the icon at `24px`
(`PRESET_BUTTON_HEIGHT`, `PRESET_ICON_SIZE`), looked right when screenshotted: each button row
dropped from roughly 130px to roughly 90px. It turned out to be shrinking the wrong thing. Real
leftover whitespace between rows led to re-inspecting the DOM properly: the button's outer grid
wrapper, a plain `<div>` inside `hui-grid-section`'s own shadow root, one level up from anything a
card's own `card_mod` can reach, reported `grid-row: span 2` and a `120px` computed height,
completely unaffected by shrinking the card inside it. Forcing the inner card down to `30px` live
left the wrapper at exactly `120px`. The `card_mod` fix was real and the button visibly got smaller,
but it was shrinking inside an unchanged 120px cell, not shrinking the cell itself.

The actual cause, found by reading
[`hui-button-card.ts`](https://raw.githubusercontent.com/home-assistant/frontend/dev/src/panels/lovelace/cards/hui-button-card.ts)
directly: its `getGridOptions()` is hardcoded, with no config field reaching it:

```ts
if (config.show_icon && (config.show_name || config.show_state)) {
  return { rows: 2, columns: 6, min_columns: 2, min_rows: 2 };  // icon + text
}
return { rows: 1, columns: 3, min_columns: 2, min_rows: 1 };     // icon only
```

Every preset button showed an icon and a name, so every one landed on `min_rows: 2` regardless of
the `rows: 1` the script asked for. The only way to reach the smaller branch is dropping icon or
name. Given the choice (icon-only vs. keep both and accept the floor vs. both plus merging the
group-preset rows into fewer sections), icon-only was chosen. Added `show_name: False` to
`preset_card()`; the `card_mod` height/icon cap was kept as a supplementary constraint, since the
icon still defaults to filling 100% of whatever smaller box it now gets.

Re-screenshotted both leaves as Tablet: Primary Suite's three preset rows visibly shrank (not just
their contents), and the Scenes section and most of the Lights tile grid are now on-screen, only the
last tile row cut off. Kitchen Lights fits with real room to spare. The `name` field stays in each
button's config even with `show_name: false`; `hui-button-card` uses it as the `aria-label`
regardless of visibility, confirmed in the same DOM inspection, so this isn't an accessibility
regression on that axis. What isn't verified is whether the icon-only buttons (power, moon, sun,
gear for On/Off, Low, Medium, Bright) are legible without labels to someone who hasn't memorized
them, which is the real tradeoff of this fix and separate from the row-height math.

### Climate: hand-copied, generator-pending

The Climate tab carries the North and South Lennox thermostat cards, the same content as the
standalone `dashboard-lennox-home`, copied over by hand the same way Lights was before its own
generator existed. Its title-only heading was already dropped, matching Home's native-header
pattern. It has no area-grid-and-leaves structure, because the Lennox integration doesn't fit that
model: there are two fixed zones (North, South), not an arbitrary set of areas with per-area
fixtures. `climate` is not yet an entry in `rebuild-home-tab.py`'s `DOMAINS` table, so, like
`dashboard-lennox-home` itself, this tab will drift independently from that dashboard if either is
edited by hand, with no generator to reconcile them.

### A/V and Alarm: not yet built

The A/V tab (`path: a-v`) exists with an empty `grid` section, no cards. `rebuild-home-tab.py`
already has an `av` entry in its `DOMAINS` table (added alongside `lights`); running
`python3 rebuild-home-tab.py av` against Home has not been done yet.

The Alarm tab (`path: alarm`) also exists with an empty `grid` section. Unlike A/V, this one is not
a matter of running the generator: there are no `alarm_control_panel` entities yet, the DSC panel's
model is still unidentified (see
[crestron-strategy.md](../crestron/crestron-strategy.md#alarm-system-no-recommendation-yet)), and `alarm` is
deliberately absent from `DOMAINS` for the same reason it is absent from
`rebuild-domain-dashboard.py`'s table: generating an area grid with nothing to populate it would
produce a dashboard where no area is ever tappable.

## What was verified

Confirmed by driving the real dashboard, logged in as Tablet, not just by reading config back:

- Logging in as `tablet` lands directly on `/vision-sample/home`, no navigation needed.
- Home's sidebar is hidden; Home's native header, view tabs, and menu button render normally.
- Tapping an area card on the Lights tab navigates to its leaf inside `/vision-sample/...`; the
  native subview back arrow returns to the Lights tab.
- The Lights tab's leaves show no stray back-button card and no duplicate "Lights" heading.
- No `navigation_path` anywhere in Home's saved config references `dashboard-lights`.
- At 1280x800, the Kitchen Lights leaf fits with room to spare; Primary Suite's preset rows and most
  of its tile grid are on-screen, with only the last tile row cut off.
- Preset button `aria-label`s still carry their full names even with `show_name: false`.

Confirmed only by reading saved config and frontend user data back over the WebSocket API, not by a
live re-login to watch it render: the `default_panel` and `theme` changes for Tablet, and the
removal of `hide_header` from Home's `kiosk_mode` block.

## Open questions

- **Tablet Home should be deleted.** It is dead weight: unreachable from anywhere in the UI, nothing
  links to it, and keeping it around only risks someone finding it and assuming it is still current.
- **The standalone domain dashboards' kiosk chrome is stale.** Their home-icon buttons still
  navigate to the dead Tablet Home, and their `hide_header: true` still hides chrome that nothing
  built a replacement for on a dashboard nobody is meant to visit directly anymore. Worth stripping
  once it's confirmed nothing still depends on visiting them directly.
- **No confirmed logout path on Home for Tablet.** The old logout icon lived in Tablet Home's
  card-based header, which is gone. Home's native header still has its menu (hamburger) button,
  since only `hide_sidebar` is set, but whether that button does anything useful with no sidebar for
  it to open, and whether `/profile` is reachable for Tablet at all from Home, has never actually
  been checked in a browser.
- **A/V tab**: run `rebuild-home-tab.py av` against Home.
- **Alarm tab**: blocked on identifying the DSC panel hardware; no entities to generate from yet.
- **Climate tab has no generator.** It will keep drifting from `dashboard-lennox-home` by hand until
  it either gets a `DOMAINS` entry of its own or that's accepted as permanent.
- **The 1280x800 viewport is still an estimate**, based on a device pixel ratio of about 1.5 that
  matches community reports for older Fire HD 10 generations, not confirmed against the actual
  Amazon Fire HD 10 (13th generation, on order as of 2026-08-05) this is sized for. Worth checking
  `window.innerWidth` / `window.innerHeight` once the physical tablet is in hand.
- **Icon-only preset buttons are unevaluated for legibility.** Whether power/moon/sun/gear read
  clearly without labels to someone who hasn't memorized them is untested.
- **The theme fix for Tablet was never watched render live**, only confirmed by reading the saved
  user data back.

## Related

- [dashboard-navigation-model.md](dashboard-navigation-model.md) for the level 2 area-grid and
  level 3 leaf rules each tab implements, and the generation approach both scripts share.
- [dashboard-header-card.md](dashboard-header-card.md) for the card-based header recipe still used
  by the standalone domain dashboards, and the `card_mod` `!important` rule that recipe depends on.
- [crestron-strategy.md](../crestron/crestron-strategy.md#touch-panels-replacing-the-tsw-752s) for the physical
  wall-panel replacement (Shelly Wall Display or Sonoff NSPanel Pro) this dashboard is meant to end
  up running on.
- [vision-sample-pergola-solar-gauge.md](vision-sample-pergola-solar-gauge.md) and
  [vision-sample-demo-entities.md](vision-sample-demo-entities.md) for other work on Home's content
  from before it took on this role.
