# Tablet Home: the root dashboard

The level 1 screen that [dashboard-navigation-model.md](dashboard-navigation-model.md) deferred
when the lights and A/V dashboards were built: one card per domain, standing in for the top
screen of the Crestron TSW-752 panels this whole hierarchy replaces. Built 2026-08-05 on Home
Assistant 2026.7.4, together with a dedicated kiosk user and a kiosk-mode plugin so a wall-mounted
device can show it with no Home Assistant chrome at all.

## The four domain cards

Tablet Home carries exactly four cards, in the same order the Crestron top screen used: A/V,
Climate, Lights, Alarm. Sound and Clock are deliberately left off. They are utility dashboards
(the Music Assistant flow card and a wall clock respectively), not part of the domain hierarchy
this navigation model is built around, so they stay reachable only through the sidebar for
whoever is not on the kiosk account.

Each card is a plain Lovelace `button` card, icon and label only, no entity, `tap_action: navigate`
to the domain dashboard's default view:

| Card | Icon | Navigates to |
| :--- | :--- | :--- |
| A/V | `m3rf:surround-sound` | `/dashboard-av` |
| Climate | `m3rf:thermostat` | `/dashboard-lennox-home` |
| Lights | `m3rf:lightbulb` | `/dashboard-lights` |
| Alarm | `m3rf:shield-lock` | none, see below |

Laid out as a 2x2 grid in a single `sections` view, `grid_options: {columns: 12, rows: 4}` per
card inside a `column_span: 2` section (24 internal columns, so two 12-wide cards fill a row).
The Lovelace sections grid math recorded in the `home-assistant` agent skill documents
`columns: 12, rows: 7` as producing a roughly square 427x439px card, but that
measurement was taken on the Sound dashboard's `column_span: 3` section (36 internal columns, so
`columns: 12` there is a third of the width). At `column_span: 2` here, `columns: 12` is half the
width, nearly double what the Sound dashboard case was. Using `rows: 7` unchanged produced cards
tall enough that the bottom row scrolled off an 800px-tall viewport; `rows: 4` was the fix,
confirmed by screenshot to show all four cards with no scrolling.

### Alarm is not tappable, matching the level 2 rule

[dashboard-navigation-model.md](dashboard-navigation-model.md) established that an area with
nothing in it gets a card but not a `tap_action`, so the dashboard cannot dead-end. The Alarm
System dashboard is in the same position one level up: it exists and carries the standard header,
but has no `alarm_control_panel` entities yet, so there is nowhere useful to send a tap. The Alarm
card omits `tap_action` entirely (confirmed live: clicking it leaves the URL on `/tablet-home/home`)
and gets `card_mod: {style: "ha-card { opacity: 0.45; }"}` so it reads as visibly inert rather than
just quietly broken. Whoever wires up the DSC panel and updates
[crestron-strategy.md](crestron-strategy.md#alarm-system-no-recommendation-yet) should also flip
this card back to tappable.

The alternative, making all four cards tappable regardless, was rejected for consistency with the
level 2 precedent: a dashboard with nothing behind it should not pretend otherwise.

## Who sees it: the Tablet kiosk user

A new Home Assistant user, name and username `Tablet`, non-admin (`group_ids: ["system-users"]`),
`local_only: true` so it can never authenticate from outside the LAN. Tablet Home is set as this
user's personal default dashboard, not the instance-wide default, so pde's own account and any
future user keep whatever default they already have.

### Setting a personal default for another user needs a session as that user

Home Assistant exposes no admin-callable "set this other user's default dashboard" command.
`frontend/set_user_data` (the command the frontend's own "set as default" profile option calls,
[`saveFrontendUserData` in `ha-pick-dashboard-row.ts`](https://github.com/home-assistant/frontend/blob/dev/src/panels/profile/ha-pick-dashboard-row.ts))
only ever writes the calling connection's own user; the server-side handler in
[`homeassistant/components/frontend/storage.py`](https://github.com/home-assistant/core/blob/dev/homeassistant/components/frontend/storage.py)
reads `connection.user.id` directly, with no `user_id` field in the command schema.
`frontend/set_system_data` exists and does take an override, but it is instance-wide: writing
`default_panel` there would make Tablet Home the default for every user without a personal
override of their own, which was explicitly the rejected option (see "Default status" below).

The only path left is to briefly authenticate as Tablet and call `frontend/set_user_data` from
that session:

1. `POST /auth/login_flow` with `handler: ["homeassistant", null]` to start a
   username/password login.
2. `POST /auth/login_flow/<flow_id>` with the username and password, returning a short-lived
   authorization code.
3. `POST /auth/token` with `grant_type=authorization_code` to exchange the code for an
   `access_token` and `refresh_token`.
4. Open a WebSocket connection authenticated with that `access_token`, read the existing
   `frontend/get_user_data` key `core` (empty, for a brand new user), and write it back with
   `default_panel: "tablet-home"` added.
5. `POST /auth/revoke` with the `refresh_token` to end that session immediately rather than
   leaving a long-lived credential lying around from a one-time setup step.

Confirmed live: logging in as Tablet through the actual UI afterward landed directly on
`/tablet-home/home` with no manual navigation.

### Rejected: instance-wide default, or leaving pde as the default

Setting `frontend/set_system_data` would have been one call instead of five, but makes Tablet
Home the landing page for every account on the instance, including pde's own admin login, which
was never the intent (see "Default status" below); this dashboard is for one mounted device, not
a replacement for Overview. Leaving the instance default alone and only adding Tablet Home to the
sidebar was also considered and rejected, because a kiosk device that has to be pointed at a URL
by hand on every reboot is not actually a kiosk.

## Kiosk chrome: the kiosk-mode plugin

Home Assistant has no built-in way to hide the sidebar. The
[`NemesisRE/kiosk-mode`](https://github.com/NemesisRE/kiosk-mode) HACS plugin (v14.0.2, installed
2026-08-05) does, targeted per user rather than per dashboard so it follows the Tablet account
wherever it goes:

```yaml
kiosk_mode:
  user_settings:
    - users: ["Tablet"]
      hide_header: true
      hide_sidebar: true
```

This block is placed at the root of the dashboard config (a sibling of `views`, not inside any
view), because kiosk-mode's own config is read per dashboard, not once globally. It is present on
Tablet Home and on all four domain dashboards (Lights, A/V, Lennox Home, Alarm System), since the
Tablet user reaches all of them. Sound, Clock and Map do not carry it and were not touched; if the
Tablet user ever ended up on one of those by URL, HA's own chrome would still show, but nothing in
Tablet Home links there.

Confirmed live at 1280x800: logged in as Tablet, the entire top app bar and left sidebar are gone
on both Tablet Home and the Lights dashboard, leaving only the custom clock/date/weather header
and the dashboard's own content.

### `NemesisRE/kiosk-mode` vs. the archived original

The plugin was originally authored by `maykar` (`maykar/kiosk-mode`); that repository was archived
by its owner in 2022 and is no longer updated, despite still carrying an "HACS-Default" badge in
its README. `NemesisRE/kiosk-mode` is the actively maintained continuation, still HACS-default
(not a custom repository add), with CI running against Home Assistant nightlies as of the version
installed here. Confirmed by fetching both READMEs directly rather than trusting either badge,
since HACS default status does not by itself say which fork is current.

### Rejected: `non_admin_settings` instead of naming the user

kiosk-mode also supports `non_admin_settings`, which would apply to every non-admin account
without listing any by name. Tablet is currently the only non-admin user on this instance, so the
two options behave identically today, but `non_admin_settings` would silently kiosk-lock any
future non-admin account too (a guest login, a second read-only device), which is a broader effect
than intended. `user_settings` naming `Tablet` explicitly was chosen so a later, unrelated
non-admin account does not inherit this behavior by accident. kiosk-mode matches `user_settings`
entries on the account's display name, not its username, which is why the block says `Tablet` and
not `tablet`.

## Getting back: the header home icon

Sidebar gone means there was nothing to return to Tablet Home from inside Lights, A/V, Lennox Home
or Alarm System; the subview back button documented in
[dashboard-navigation-model.md](dashboard-navigation-model.md#level-3-the-leaf) only ever goes
from level 3 back to level 2, and level 1 never existed before today. Fixed by prepending a small
icon-only `button` card to the shared header's `horizontal-stack`, ahead of the clock/date
`vertical-stack`:

```yaml
- type: button
  icon: m3rf:home
  show_name: false
  show_state: false
  tap_action:
    action: navigate
    navigation_path: /tablet-home
  card_mod:
    style: |
      :host { flex: 0 0 64px !important; }
      ha-card { height: 100% !important; }
```

`horizontal-stack` gives each child card `flex: 1` by default, which would have made a bare icon
button grow to a third of the header's width. `card_mod`'s `:host` selector targets the card's own
custom element, which is exactly the flex item `horizontal-stack` placed it in, so overriding
`flex` there pins the button to 64px wide while `height: 100%` lets it stretch to match its taller
siblings. Both need `!important`: [dashboard-header-card.md](dashboard-header-card.md#card-mod-loses-ties-against-a-cards-own-stylesheet)
already found that a card's own stylesheet, attached via `adoptedStyleSheets`, wins any tie against
a plain card-mod rule.

This touches the same shared header recipe that document describes, so it now has two variants:
Tablet Home's own header (unmodified, clock/date/weather only, since tapping home from home would
be pointless) and the four domain dashboards' header (home icon prepended). Lennox Home and Alarm
System are hand-authored with no generator, so like the rest of that shared header, their copies
will drift independently if this recipe changes again; Lights and A/V get theirs preserved
verbatim by `rebuild-domain-dashboard.py`'s existing header-preservation behavior, so a future
regeneration keeps the home icon automatically.

Confirmed live: tapping the home icon from the Lights dashboard, logged in as Tablet, returned to
`/tablet-home/home`.

## `hide_header` hides more than the header: three more gaps found by actually using it

Pete tested this logged in as Tablet before a physical tablet existed to mount, using a resized
desktop browser (see "Testing without the physical tablet" below), and found things the home-icon
fix didn't cover. All three come from the same root cause: `hide_header` and `hide_sidebar` in
kiosk-mode hide HA's entire native top app bar and sidebar, and between them those two pieces of
chrome were quietly carrying more jobs than just navigation.

**No way to tell domain dashboards apart.** The view's title (`Lights`, `A/V`, ...) only ever
rendered in that native bar. With it gone, every domain dashboard's content starts with a floor
heading ("Main Floor", "Garage") that says nothing about which domain you're in. Fixed with a
title-only heading section at the top of every level 2 page; full detail in
[dashboard-navigation-model.md](dashboard-navigation-model.md#level-2-the-area-grid).

**No way back from a leaf.** A subview's back arrow (level 3 to level 2, e.g. "Office Lights" back
to "Lights") is also native-bar-only, and `rebuild-domain-dashboard.py` never gave leaves a header
of their own to carry a replacement. Fixed with an explicit full-width back button as the first
thing on every leaf; full detail in
[dashboard-navigation-model.md](dashboard-navigation-model.md#level-3-the-leaf).

Both fixes live in `rebuild-domain-dashboard.py` itself, not hand-patched into the live Lights and
A/V configs, for the same reason the header is preserved rather than recreated: a hand patch would
have been silently overwritten by the next regeneration. Lennox Home and Alarm System have no
generator, so their equivalent title headings were added by hand directly, the same drift caveat as
the rest of their hand-authored content.

**No way to log out.** The sidebar carries the profile menu, and with it gone there is no path to
`/profile` at all, which is where HA's only "Log out" control lives; there is no logout affordance
anywhere in Lovelace itself. Fixed the same way as the home icon: a `mdi:logout` button prepended
to Tablet Home's own header, `tap_action: navigate` to `/profile/general`. `mdi:` rather than
`m3rf:` deliberately, after `m3rf:cube-outline` 404'd on the Vision Sample dashboard's icon for the
same underlying reason: `m3rf` is Material Symbols Rounded Filled, not MDI, and does not carry
every MDI name. `mdi:logout` is guaranteed to exist without needing to guess at that pack's naming.

This one has a wrinkle the other two didn't. `kiosk_mode` config lives on a Lovelace *dashboard*,
and `/profile` is a core HA panel, not a dashboard, so it has no `kiosk_mode` block and nothing to
hide it. Confirmed live: navigating there from Tablet's session renders the sidebar and top bar in
full, "Log out" reachable and working, tokens actually cleared, landing back on the login screen.
Kiosk-mode's hiding is real but narrower than "hide chrome everywhere for this user"; it is scoped
to whatever dashboards carry the config block, and every other panel on the instance is unaffected.

### The regeneration that followed dropped `kiosk_mode` itself

Running the newly-fixed `rebuild-domain-dashboard.py` against `lights` and `av` to pick up the two
fixes above had a side effect: both dashboards lost their `kiosk_mode` block entirely, and Tablet's
session went back to showing full HA chrome. The generator built its save payload as a bare
`{"views": [...]}`, which is correct right up until something else starts living at the config
root, which `kiosk_mode` had, added by hand after the generator was originally written. Nothing in
the generator knew that key existed, so it vanished on the next whole-config save. Caught by
re-testing as Tablet immediately after regenerating, not by reading the saved config back, which
would have looked complete. Fixed in the generator by spreading the live config before overwriting
`views`, and `kiosk_mode` was restored by hand once. Full account in
[dashboard-navigation-model.md](dashboard-navigation-model.md#generation).

## An undocumented HA quirk found while minting the Tablet session

The two-step login flow (`POST /auth/login_flow` then `POST /auth/login_flow/<id>`) failed
consistently with `IP address changed` (HTTP 400 over plain `curl`, surfacing as a 403 from the
browser) when both requests were made against `homeassistant.local`, even seconds apart from the
same machine. The handler in `homeassistant/components/auth/login_flow.py` stores the requesting
IP address on the flow at creation and rejects any later step if the apparent remote address
differs. `homeassistant.local` is mDNS and resolved consistently to `192.168.4.125` when checked
directly, so the mismatch is not the server's address changing; the more likely explanation is
this machine's own dual-stack resolution picking a different local route (IPv4 vs. a link-local
IPv6 form of the same interface) across two separate connections to the same mDNS name. Repeating
both requests against the literal IP, `http://192.168.4.125:8123`, instead of the hostname made
the failure disappear immediately and consistently, in both a raw `curl` reproduction and the
actual browser login. Worth knowing for any future script or automation that authenticates in more
than one request against `homeassistant.local`: use the LAN IP for that specific exchange.

## Testing without the physical tablet

The wall-mount hardware itself (see
[crestron-strategy.md](crestron-strategy.md#touch-panels-replacing-the-tsw-752s)) is still
unresolved; testing so far has used an Amazon Fire HD 10 (13th generation, 2023: 1920x1200
physical, 224ppi, 10.1", on order as of 2026-08-05) as the intended device and a resized desktop
browser as a stand-in until it arrives.

No official CSS-viewport figure was found for that specific generation. The estimate used, 1280x800
landscape, comes from a device pixel ratio of about 1.5, which matches community reports for older
Fire HD 10 generations at similar ppi; it has not been confirmed against the real device's Silk
browser. Once the tablet is in hand, checking `window.innerWidth` / `window.innerHeight` (or any
viewport-size page) against this number is worth doing before trusting the 2x2 grid's fit on the
real hardware.

Logging in as Tablet from a browser has to go through the literal LAN IP,
`http://192.168.4.125:8123`, not `homeassistant.local`, or the login form 403s; see "An
undocumented HA quirk" below. Worth checking whether Fire OS's Silk browser resolves the hostname
the same flaky way; if the real device hits the same wall, it needs pointing at the IP too, or
DNS/mDNS resolution on this network needs a more durable fix than working around it per script.

## What was verified

Confirmed by driving the real dashboard on 2026-08-05, logged in as Tablet, not by reading config
back:

- Logging in as `tablet` lands directly on `/tablet-home/home`, no navigation needed.
- No sidebar and no top app bar render anywhere in the Tablet session, on any of Tablet Home,
  Lights, A/V, Lennox Home or Alarm System.
- Tapping Lights navigates to `/dashboard-lights/lights`; tapping the header's home icon from
  there returns to `/tablet-home/home`.
- Tapping Alarm does not navigate anywhere; the URL stays on `/tablet-home/home`.
- The 2x2 grid renders with no scrolling at 1280x800.
- Each domain dashboard shows its own title ("Lights", "Climate", ...) as in-page content.
- From Office Lights (a level 3 leaf), the back button reads "Lights" and returns to
  `/dashboard-lights/lights`.
- All five dashboards (Tablet Home plus the four domain dashboards) carry a `kiosk_mode` block,
  re-confirmed after the regeneration that briefly dropped it from Lights and A/V.
- Tapping Tablet Home's logout icon reaches `/profile/general` with full chrome and a working
  native "Log out" control; confirming it actually ends the session and returns to the login
  screen.

Not verified: kiosk-mode's behavior for any other non-admin account, since Tablet is the only one
that exists. A stray Tablet session from this verification pass was revoked, but the browser-based
UI login used to confirm the default-dashboard behavior created its own separate session that was
not individually revoked afterward; this is a low-privilege, local-only account, and the real
device will create and keep its own session the same way, so it was left alone rather than chased
down.

## Default dashboard retargeted to Home

Later the same day, Tablet's personal default dashboard was changed again, from Tablet Home to the
dashboard titled Home (`url_path: vision-sample`, the former Vision Sample demo dashboard; see
[vision-sample-demo-entities.md](vision-sample-demo-entities.md)). The mechanism was identical to
the one described above under "Setting a personal default for another user needs a session as that
user": a short-lived login as Tablet, `frontend/set_user_data` on key `core` with `default_panel`
changed from `"tablet-home"` to `"vision-sample"`, then the refresh token revoked. The read-back
inside that same Tablet session confirmed both the old and new values.

Home had no `kiosk_mode` block of its own, since it predates this whole kiosk setup. It first got
the same block already present on Tablet Home and the four domain dashboards, `hide_header: true`
and `hide_sidebar: true`, copied over without adjusting it for a dashboard that, unlike those five,
has no custom-built replacement header.

### `hide_header` broke the view tabs, fixed by dropping it

Home is a stock multi-view dashboard (Home, Lights, A/V, Alarm, Climate, five separate views, not
to be confused with the domain dashboards of the same names), and its native top app bar carries a
job the five kiosk dashboards don't ask of it: the row of view tabs is the only navigation between
those five views. kiosk-mode's `hide_header` and `hide_sidebar` are independent toggles that each
hide one whole region; `hide_header` doesn't distinguish "the tabs" from "the rest of the header",
so it took the tabs with it, along with the menu button and everything else native-header. Tablet
Home and the four domain dashboards get away with `hide_header: true` only because
[dashboard-navigation-model.md](dashboard-navigation-model.md) and the sections above built them a
full replacement: their own header, their own home-icon nav, their own back buttons. Home has none
of that, so hiding its native header just broke navigation between its views.

Fixed by dropping `hide_header` from Home's `kiosk_mode` block and keeping only `hide_sidebar`:

```yaml
kiosk_mode:
  user_settings:
    - users: ["Tablet"]
      hide_sidebar: true
```

This leaves Home's header and view tabs rendering exactly as they do for every other user; only
the sidebar stays hidden for Tablet. The dashboard config was backed up before both saves.

The background image was assumed to be part of the same header region, on the theory that it was
lost at the same time the tabs were. That theory was wrong (see below); the background is untouched
by anything `kiosk_mode` does and was never working for Tablet regardless of the header setting.

### The background was never a `kiosk_mode` problem: it is a per-user theme setting Tablet never had

The background image on Home comes from the active theme, not the dashboard config. The instance
runs [`Nezz/homeassistant-visionos-theme`](https://raw.githubusercontent.com/Nezz/homeassistant-visionos-theme/refs/heads/master/themes/visionos.yaml),
which sets `lovelace-background: var(--background-image)` and a per-mode `background-image: url(...)`.
Like `default_panel`, theme selection is personal frontend user data, not part of the dashboard:
the profile theme picker calls `saveThemePreferences`, which is `saveFrontendUserData(connection,
"theme", data)` under the hood, the same self-only `frontend/set_user_data` mechanism as
`default_panel`, just under key `theme` instead of `core`. Reading pde's own selection back
(readable directly with `$HA_TOKEN`, since that only ever reads the calling connection's own data)
returned `{"dark": false, "theme": "visionos"}`. Tablet's `theme` key had never been set at all
(`null`), because nothing had ever set it, so Tablet was rendering the instance's fallback theme,
which has no background image, on every dashboard, independent of `kiosk_mode`, `hide_header`, or
which dashboard is the default.

Fixed the same way as `default_panel`: a short-lived login as Tablet, `frontend/set_user_data` on
key `theme` with value `{"dark": false, "theme": "visionos"}` (mirroring pde's own), refresh token
revoked immediately after. Read-back inside that same Tablet session confirmed `null` before and
the new value after.

Confirmed by reading the saved dashboard config and the Tablet session's own user data back over
the WebSocket API, not by driving a browser session; this pass did not include a live re-login as
Tablet to watch the tabs and background actually render, or to check whether the header's menu
(hamburger) button, still present since only `hide_sidebar` is set, does anything visible now that
there's no sidebar for it to open. Worth a real check once there is a browser or the physical
tablet in hand.

Tablet Home itself was left untouched: it still exists, still carries its `kiosk_mode` block, and
is still where the four domain dashboards' home-icon nav points. It is no longer reachable from
Home, though, since Home's cards (inherited from the Vision Sample demo dashboard) do not link to
it and the sidebar that would otherwise offer it is hidden for Tablet. If Tablet Home is meant to
stay reachable, something on Home would need to link to it explicitly.

## Home's Lights tab got the real Lights dashboard's content

Home's own "Lights" view (`path: kitchen`, a leftover from the Vision Sample demo it was built
from) carried one stray `light.kitchen_lights` tile and nothing else. It was replaced with the
actual Lights dashboard's top-level content: the same three sections (the "Lights" title heading,
the Main Floor area-card grid, and the Basement/second-floor grid below it), `max_columns: 2`, and
the `m3rf:lightbulb` icon, copied from `dashboard-lights`'s `lights` view. `max_columns` and the
sections came together because the sections grid math is tuned to a specific `max_columns`, the
same fragility [dashboard-header-card.md](dashboard-header-card.md) and this document's own 2x2
grid section ran into.

One thing was deliberately left behind: that source view's own header card (home icon, clock/date,
weather, the shared recipe documented above and in
[dashboard-header-card.md](dashboard-header-card.md)). Home already has its own native header now
that `hide_header` is off for it, so carrying the card-based one over would have stacked two
headers, and its home icon navigates to `/tablet-home`, which is the wrong destination from inside
Home. Only the `sections` content moved.

At this point the area cards' `tap_action` still pointed at `/dashboard-lights/area-entry`,
`/dashboard-lights/area-kitchen`, and so on, the real Lights dashboard's own leaf views. Tapping an
area left Home for `dashboard-lights`, which carries its own `kiosk_mode` (`hide_header` and
`hide_sidebar` both true) and whose header's home icon points back to `/tablet-home`, not to Home.
Fixed below.

### Making Lights fully self-contained: the leaf views copied over too

Home is meant to become the main kiosk dashboard for wall-mounted touch panels (see
[crestron-strategy.md](crestron-strategy.md#touch-panels-replacing-the-tsw-752s) for the hardware
this targets), which means it can't lean on `dashboard-lights` for navigation the way the plan
above did. The fix: copy `dashboard-lights`'s five `subview: true` leaf views (Entry, Kitchen,
Dining Room, Primary Suite, Office Lights) onto Home unchanged, then rewrite every
`navigation_path` inside the copied content, both the leaves and the area cards added earlier, that
pointed at `dashboard-lights`:

| Old | New |
| :--- | :--- |
| `/dashboard-lights/lights` (the leaves' back button) | `/vision-sample/kitchen` (Home's own Lights tab) |
| `/dashboard-lights/area-<name>` (the area cards' tap targets) | `/vision-sample/area-<name>` |

`dashboard-lights` itself was left untouched, this only copies content into Home; the two
dashboards now carry duplicate leaf views that will drift independently if either is edited later.
Home went from 5 views to 10. The five new ones keep `subview: true`, so, same as on
`dashboard-lights`, they don't add clutter to the visible tab strip; they're reachable only by
tapping an area card or a leaf's own back button.

Confirmed by reading the saved config back and searching every `navigation_path` value in it: none
still reference `dashboard-lights`. Not confirmed in a browser; worth checking that the leaves'
`display_type: compact` sizing and `column_span: 2` grid math, tuned on `dashboard-lights` at its
own `max_columns: 2`, look right on Home too.

### The bare "Lights" heading section is redundant here, and gone

The Lights tab's first section was a title-only heading card reading "Lights", carried over from
`dashboard-lights`'s own top view. That heading exists there for a reason:
[dashboard-navigation-model.md](dashboard-navigation-model.md#level-2-the-area-grid) added it
because `hide_header: true` removes the native top app bar, and with it the only other place a
domain dashboard's title would show. Home doesn't hide its header, so the Lights tab's title
already shows in the native tab strip, making the in-page heading a duplicate. Removed, leaving the
Main Floor and Garage area-card sections as the tab's first content. `dashboard-lights` keeps its
own copy; the two dashboards' Lights content will keep drifting apart the same way noted above.

## `rebuild-home-tab.py`: a generator for Home's tabs

The hand transplant above (copy content, rewrite paths, drop the heading) was a one-time fix, not
something that survives pde re-running `rebuild-domain-dashboard.py` against `dashboard-lights`
later and expecting Home to still match. `scripts/rebuild-home-tab.py`, added 2026-08-06, is the
repeatable version: it builds a Home tab straight from the live floor/area/entity registries, the
same way `rebuild-domain-dashboard.py` builds a standalone domain dashboard, rather than by reading
another dashboard's saved config. It is based directly on that script; everything domain-specific
(presets, entity domains, the tile feature, `AREA_ORDER`, `AREA_GROUP_PRESETS`) is copied into its
own `DOMAINS` table, which needs to be kept in sync by hand if the original ever changes.

Three things differ from `rebuild-domain-dashboard.py`, all consequences of Home being meant as the
self-contained kiosk dashboard rather than one domain's own:

- No title-only heading section, matching the fix directly above: Home never hides its header, so
  there is nothing for a heading to stand in for.
- Every `navigate` action targets `/vision-sample/...`, never the standalone dashboard, the same
  self-containment fix from the section above, now generated instead of hand-applied.
- Leaf views are named `<domain>-area-<area_id>` (`lights-area-kitchen`), not `area-<area_id>`.
  `dashboard-lights` only ever hosts its own leaves, so the plain name never collides there; Home
  hosts leaves from more than one domain in one flat `views` list, where `area-kitchen` would
  collide between a Lights leaf and a future A/V leaf.

Home's own hand-picked badges (the device trackers, alarm panel, and weather chips pde added to the
top of the Lights tab, see the view's `badges` key) are never invented by the script, only read from
the live tab and carried forward, the same principle as the header the original script preserves
for the domain dashboards, just for a different piece of config: Home has no per-tab header card,
badges are its equivalent.

The script only rebuilds a tab that already exists on Home (`home_view_path` in `DOMAINS` must match
a real view), and only touches that domain's tab and leaves; every other Home view is read back and
rewritten unchanged, at its original index, so the visible tab order (Home, Lights, A/V, Alarm,
Climate) never shifts.

### Tested against Lights, and a one-time cleanup it exposed

Running `python3 rebuild-home-tab.py lights` regenerated the tab and its five leaves correctly,
badges included, but left Home with 15 views instead of the expected 10: the five `area-*` leaves
from the hand transplant above predate this script's `lights-area-*` naming, so its dedup logic
(which only recognizes its own prefix) never removed them, and they sat alongside the new ones as
dead weight, unreachable from any card. Not a bug worth handling inside the generator, since it can
only ever happen once, right after adopting the naming scheme; fixed with a one-off scratchpad
script that deleted the five `area-*` paths by name, backed up first. Confirmed by reading Home's
config back afterward: 10 views, no `navigation_path` anywhere referencing `dashboard-lights`, no
leaf path under `/area-` missing the `lights-` prefix, and the Lights tab's badges unchanged
(`device_tracker.pete_iphone`, `media_player.gym`, `alarm_control_panel.security`,
`sensor.openweathermap_temperature`, `sensor.openweathermap_humidity`).

### The leaves' breadcrumb back button was next to go

`build_leaf()` still carried over `rebuild-domain-dashboard.py`'s full-width back-button section, a
`bare_section([back_card(cfg)])` ahead of the presets. That button exists on the domain dashboards
because `hide_header: true` removes HA's native subview back arrow along with the rest of the
header, so without it there is no way off a leaf at all (see
[dashboard-navigation-model.md](dashboard-navigation-model.md#level-3-the-leaf)). Home never hides
its header, so every leaf already gets that native back arrow for free; the hand-built button was
pure duplication. Removed `back_card()` entirely and the section that held it, so a leaf now opens
straight on its title-and-presets row. The dry-run summary printer's `baseline` section count, used
to report how many scene sections a leaf has, was still counting the removed section and had started
printing `-1 scene section(s)`; fixed alongside it.

Re-tested against Lights: the Kitchen Lights leaf's first section now starts with the heading and
preset buttons directly, no `m3rf:arrow-back` card anywhere in any of the five leaves, section count
per leaf down from 3 to 2 (plus one more for Primary Suite's scene section, unchanged). View count,
nav paths, and badges all reconfirmed unchanged from the check above.

Not confirmed in a browser, same caveat as the rest of this document's Home work.

## Shrinking the leaves for a 1280x800 tablet, actually confirmed in a browser this time

Every earlier change in this document was verified by reading saved config back over the WebSocket
API, with a repeated caveat that it hadn't been checked in an actual browser. This one was: a
short-lived Tablet login (the same mechanism used to set `default_panel` and `theme`), a Playwright
storage-state file built from that session's access token, `resize 1280 800` to match the wall
tablet's actual screen, then `goto` and `screenshot` on the live leaves. Session revoked and every
credential file deleted immediately after, same discipline as the other Tablet-session scripts.

**Entity tiles.** `rebuild-domain-dashboard.py`'s `columns: 12, rows: 2` (2 tiles per row) was never
checked against 1280x800; screenshotted live, 5 tiles at that size filled nearly the whole 800px
height on their own. Changed to `columns: 8` (3 per row) as new constants `LEAF_TILE_COLUMNS` /
`LEAF_TILE_ROWS` in `rebuild-home-tab.py`, leaving `rows` alone so the brightness-slider feature
keeps its full height. Re-screenshotted: same leaf now ends around two-thirds of the way down the
screen instead of filling it.

**Preset buttons turned out to be the bigger problem, and grid_options couldn't fix them.**
Screenshotted the Primary Suite leaf, which has the main preset row plus two `AREA_GROUP_PRESETS`
rows (Bedroom, Bath): three rows of buttons pushed the entity tiles below the fold entirely, worse
than the tiles ever were. `grid_options: {rows: 1}` looked like it should already be as small as a
button gets, so the DOM had to be inspected directly (admin session, same page, walking every shadow
root to reach inside `hui-button-card`) to find out why: a `rows: 1` button rendered at 120px tall,
most of it an `ha-state-icon` with `--mdc-icon-size: 100%`, `hui-button-card`'s built-in behavior of
scaling its icon to fill whatever box it's handed rather than sizing to content. `grid_options` never
had a lever for that.

Fixed (or so it seemed at the time, see the correction directly below) with `card_mod` on each
preset button, live-tested by injecting the CSS into the running page before touching the script:
pinning both `:host` and `ha-card` to a fixed `56px` height (new `PRESET_BUTTON_HEIGHT` constant)
and capping the icon at `24px` (`PRESET_ICON_SIZE`). Applied in `preset_card()`, which both the main
presets and the `AREA_GROUP_PRESETS` rows already shared, so the fix covers both without touching
`build_leaf()`.

Re-screenshotted Primary Suite: each button row dropped from roughly 130px to roughly 90px. Three
rows still didn't leave the tile section fully on-screen without scrolling, matching pde's framing
that the leaf doesn't have to completely fit, only that the elements be smaller than before, which
they measurably were. Re-screenshotted Kitchen Lights too, the simpler leaf: it fit with room to
spare.

## The button shrink was mostly cosmetic: the wrapper cell never actually got smaller

pde flagged real leftover whitespace between rows after the change above, and it led to a wrong
conclusion getting corrected. "The section below moved up to close the gap" was true, but for the
wrong reason: that observation was made on the *tile* change earlier the same session, not the
button one, and got attributed to the wrong fix in the writeup above. Re-inspected properly this
time, admin session, same live page, walking every shadow root: the button's outer grid wrapper (a
plain `<div>` inside `hui-grid-section`'s own shadow root, one level up from anything a card's own
`card_mod` can reach) reports `grid-row: span 2` and a `120px` computed height, completely
unaffected by shrinking the card inside it. Forcing the inner card down to `30px` live, wrapper
stayed at exactly `120px`. The card_mod fix above was real, the button visibly got smaller, but it
was shrinking inside an unchanged 120px cell, not shrinking the cell, which is exactly the dead space
pde was pointing at.

The actual cause, found by reading [`hui-button-card.ts`](https://raw.githubusercontent.com/home-assistant/frontend/dev/src/panels/lovelace/cards/hui-button-card.ts)
directly rather than guessing further: its `getGridOptions()` is hardcoded, no config field reaches
it:

```ts
if (config.show_icon && (config.show_name || config.show_state)) {
  return { rows: 2, columns: 6, min_columns: 2, min_rows: 2 };  // icon + text
}
return { rows: 1, columns: 3, min_columns: 2, min_rows: 1 };     // icon only
```

Every preset button shows an icon and a name (`show_state` was already off), so every one landed on
`min_rows: 2` regardless of the `rows: 1` this script asks for. The only way to reach the smaller
branch is dropping one of icon or name. Given the choice (icon-only vs. keep both and accept the
floor vs. both plus merging the group-preset rows into fewer sections), pde chose icon-only. Added
`show_name: False` to `preset_card()`; `card_mod` was kept as a supplementary cap on the icon, which
still defaults to filling 100% of whatever smaller box it now gets.

Re-screenshotted both leaves as Tablet. Primary Suite: all three preset rows visibly shrank (not
just their contents), the Scenes section and most of the Lights tile grid are now on-screen, only
the last tile row is cut off. Kitchen Lights, the simpler leaf, now fits with real room to spare.
The `name` field stays in each button's config even with `show_name: false`; `hui-button-card` uses
it as the `aria-label` regardless of visibility, confirmed in the same DOM inspection, so this isn't
an accessibility regression, just a visual one. Not verified: whether the icon-only buttons (power,
moon, sun, gear for On/Off, Low, Medium, Bright) are actually legible without their labels to someone
who hasn't memorized them, which is the real tradeoff of this fix, not the row height math.

## Related

- [dashboard-navigation-model.md](dashboard-navigation-model.md) for the three-level hierarchy
  this is the top of, and the rule about not letting an empty destination be tappable.
- [dashboard-header-card.md](dashboard-header-card.md) for the shared clock/date/weather header
  this document adds a second variant of.
- [crestron-strategy.md](crestron-strategy.md#touch-panels-replacing-the-tsw-752s) for the
  physical wall-panel replacement (Shelly Wall Display or Sonoff NSPanel Pro) this dashboard is
  meant to end up running on.
