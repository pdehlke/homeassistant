# Overview C calendar card: Google Calendar added, SYSTM deferred

`docs/project-todo.md` item 2 ("Fix Overview C calendar entries") was really "the calendar card
only ever shows Rachio's irrigation schedule." This document covers adding pde's Google Calendar
to the same card, shipped 2026-08-12, and the record of why Wahoo SYSTM's workout calendar was
investigated and set aside rather than built.

## Result

Overview C's calendar card and the My Day overlay now interleave Rachio's irrigation schedule with
three real Google calendars: pde's primary calendar, Birthdays, and Holidays in United States.
Verified live: "Clean the house" (an all-day personal event) and "Pete: Dyson Dermatology" (a timed
appointment) both rendered correctly alongside Rachio's "Even Days" entries, sorted and grouped by
day, with no layout overflow and no new console errors. `calendar.home`, the always-empty Local
Calendar placeholder, was dropped from the array; the entity itself is untouched since the
wall-clock widget elsewhere still uses it.

SYSTM was investigated and deferred rather than built. See that section below for why.

## Starting state

Overview C's calendar card is pure configuration, not a code problem. Homie Dashboard's fork reads
a flat `calendarEntities` array in `dist/config.js`, which before this change read:

```js
calendarEntities: [
  "calendar.home",
  "calendar.rachio_base_station_ca358975",
],
```

`_fetchOv3CalEvents` (in `dist/homie-dashboard.html`) fetches each listed entity's events for the
next 30 days from HA's calendar REST API, merges and sorts them, and `_renderOv3CalCard` groups
them by day. Adding a source is adding its entity ID to the array; nothing else changes. The same
array also feeds the full "My Day" overlay (`_dailyLoadEvents`, a 365-day fetch), so both views
pick up new sources at once.

The card's event list is internally scrollable (`.ov3-events-list { flex:1; overflow-y:auto }`)
inside a fixed-height card (`.ov3-events-card { grid-row: 3 / 5; overflow:hidden }`). A busier
calendar makes the list scroll further, not grow the card, so this doesn't reopen the vertical
overflow bug class Overview C hit before (see [homie-dashboard-install-plan.md](./homie-dashboard-install-plan.md)'s Overview C
overflow section).

Before this change, HA had no Google Calendar integration configured. The instance had only two
calendar entities: `calendar.home` (an empty Local Calendar, installed only because the wall-clock
widget needed some calendar entity to exist) and Rachio's schedule.

## Decisions

- All calendars in the linked Google account show on Overview C, not a filtered subset.
- `calendar.home` is dropped from Overview C's array now that real calendars are live. The entity
  itself is untouched; the wall-clock widget elsewhere still needs it.
- SYSTM is deferred. See below.
- pde's Google account is a legacy free Google Workspace domain (the old free "Google Apps for
  your domain" tier), not a personal Gmail account. That changed which OAuth consent screen type
  to try first, covered below.

## Google Cloud OAuth setup (pde's part, needed his own Google login)

This half couldn't be done by an agent; it needed pde signed into his own Google account and
Workspace admin console. Steps followed (kept here as reference for any future Google-integration
setup on this instance):

1. **Google Cloud Console**: create a project (e.g. "Home Assistant") at console.cloud.google.com.
   Under APIs & Services > Library, enable the **Google Calendar API**.
2. **OAuth consent screen**: APIs & Services > OAuth consent screen. Try **Internal** first
   ([Google Cloud: Manage App Audience](https://support.google.com/cloud/answer/15549945)):
   - Internal is only offered when the Cloud project is associated with a Google Cloud
     Organization resource, which a Workspace domain (including legacy free) normally gets
     automatically once the domain is verified and Cloud is enabled for it. If the "Internal"
     option doesn't appear, the domain has hit a known org-resource provisioning gap that some
     Workspace admins report even with valid super-admin access and no documented self-service
     fix short of a Google Cloud support ticket ([Google developer forum
     thread](https://discuss.google.dev/t/no-organization-in-google-cloud-console/365589)). If
     that happens, fall back to External below rather than spending more time chasing it.
   - Internal's payoff: no publish step, no verification review, and no "unverified app" warning
     shown during consent, since it's scoped to the Workspace domain's own members
     ([source](https://support.google.com/cloud/answer/15549945)). It also isn't subject to the
     Testing-mode 7-day refresh-token expiry described below, since Internal apps have no
     Testing/Production distinction to begin with.
   - If Internal isn't available, use **External**. User type External, fill in app name, support
     email, and developer contact. Then, critically, go to **Publishing status** and click
     **Publish App** before finishing. Home Assistant's own docs call this out directly:
     "Otherwise, your credentials will expire every 7 days"
     ([home-assistant.io/integrations/google](https://www.home-assistant.io/integrations/google/)).
     Publishing doesn't trigger Google's formal verification review for a personal-use app with
     under 100 users
     ([source](https://support.google.com/cloud/answer/13464323)); the only visible cost is a
     one-time "Google hasn't verified this app" warning during the first authorization, which is
     safe to click through (Advanced > "Go to [app] (unsafe)").
3. **Create the OAuth client**: APIs & Services > Credentials > Create Credentials > OAuth client
   ID. Application type **Web application**, per HA's current docs. Under Authorized redirect URIs
   add exactly:

   ```text
   https://my.home-assistant.io/redirect/oauth
   ```

   This is the same fixed redirect URI regardless of Internal vs. External, and regardless of
   whether the HA instance is reached only over LAN or also through Home Assistant Cloud remote
   access: `my.home-assistant.io` is a free helper domain Google will trust that redirects the
   browser back to whatever local HA URL is already open, entirely client-side
   ([home-assistant.io/integrations/my](https://www.home-assistant.io/integrations/my/)).
4. Save; copy the Client ID and Client Secret somewhere temporary. Not into this repo, not pasted
   into chat.
5. **In Home Assistant**: Settings > Devices & Services > Add Integration > "Google Calendar" >
   paste the Client ID and Secret directly in that flow (no separate Application Credentials setup
   step needed) > it opens Google's consent screen > sign into the Workspace account > authorize >
   confirms back to HA.
6. HA auto-creates one `calendar.*` entity per calendar in the account's "My Calendars" list.
   There's no in-flow picker; filtering which ones actually show on Overview C happens on Homie's
   side, in its `calendarEntities` array.

Once pde confirmed this was done, `/api/states` showed three new entities:
`calendar.pde_rfc822_net`, `calendar.birthdays`, `calendar.holidays_in_united_states`, backed by a
single `google` config entry titled `pde@rfc822.net`, state `loaded`.

## Deploying the config change

1. Queried HA for the resulting `calendar.*` entity IDs, since Google's entity naming isn't
   predictable in advance.
2. Edited `dist/config.js` in the homie-dashboard fork: `calendarEntities` became
   `calendar.rachio_base_station_ca358975` plus the three new Google calendar entities, with
   `calendar.home` removed. Validated with `node --check` before touching HA.
3. Deployed following the same pattern used for every prior Homie config change (Scenes chip,
   Music chip, the original install; see [homie-dashboard-install-plan.md](./homie-dashboard-install-plan.md)): SSH/SFTP to
   `root@hass.ehlke.net:2222`, backed up the live `config.js` with a timestamp, spliced the real
   `HA_TOKEN` out of that backup with a BusyBox-safe `sed` expression into the new file (entirely
   inside one remote script over SSH stdin, so the token never touched a local shell variable or
   command-line argument), uploaded under a temp name, atomically renamed to `config.js`, deleted
   `config.js.gz`. Verified by token length (183 characters before and after) and
   placeholder-absence, never by printing it. Then bumped `homie-dash`'s Lovelace iframe `?v=` from
   `20260812.7` to `20260812.8` via `scripts/apply-card.py` (`HA_MATCH_TYPE=iframe`, dry-run first
   to confirm exactly one match) so the tablet picks up the change past caching.
4. Verified live via Playwright. Homie's own HTML page authenticates to HA using its own baked-in
   token, so this didn't need any HA login or session state at all: navigating straight to
   `http://hass.ehlke.net:8123/local/community/homie-dashboard/homie-dashboard.html?v=20260812.8`
   loaded Homie directly. Confirmed Overview C's calendar card and the My Day overlay both show
   Rachio's schedule interleaved with the new Google events, grouped by day, no overflow, no new
   console errors (four pre-existing, unrelated errors remained: a blocked `navigator.vibrate`
   call before any tap, a `favicon.ico` 404, and two `/api/states/` 404s from an empty entity ID
   elsewhere in the page, none touching calendar fetches).
5. Showed pde the live screenshots; he approved.
6. Committed the fork's `dist/config.js` change (`80431bc`). The live copy's spliced token was
   never copied back to git, same as every prior deploy.
7. Updated this document with what shipped, removed item 2 from `docs/project-todo.md`, confirmed
   this file's entry is in [README.md](../../README.md).

## Verification

No existing automated test covers the calendar card (`test/screen-a.test.cjs` has no calendar
cases), so this was a config change verified visually, matching how pde reviews Homie changes:

- Playwright screenshots of Overview C's calendar card and the My Day overlay confirmed both
  Rachio and Google events render, sorted and grouped correctly, with no layout regression.
- No new browser console errors in Homie's iframe after the change.
- Dropping `calendar.home` from the array didn't touch the entity itself; nothing else on this
  instance references it besides the wall-clock widget, which is unaffected.

## SYSTM: investigated and deferred

SYSTM (Wahoo's indoor training platform) has no built-in calendar export. This has been requested
on Wahoo's own forum for years with no resolution: ["Expose the SYSTM training
calendar"](https://wahoox.forum.wahoofitness.com/t/expose-the-systm-training-calendar/31098) and
["Sync SYSTM plan to third party
calendar"](https://wahoox.forum.wahoofitness.com/t/sync-systm-plan-to-third-party-calendar/20059),
where a user describes it as "one of the most requested features for years" with direct Google
Calendar sync "not an option under 3rd party apps." SYSTM's Authorized Apps integrations
(Strava, Garmin Connect, TrainingPeaks, Final Surge, Today's Plan) only push *completed* workouts
after the fact; planned/future sessions don't sync anywhere automatically, confirmed in
["Training Peaks Calendar use with
SYSTM"](https://wahoox.forum.wahoofitness.com/t/training-peaks-calendar-use-with-systm/28848).

Unofficial routes exist: a reverse-engineered GraphQL client
([`joaodrp/wahoo-systm-mcp`](https://github.com/joaodrp/wahoo-systm-mcp)) and a credential-based
scraper plus companion Chrome extension
([`bakermat/suffersync`](https://github.com/bakermat/suffersync)) that can pull the planned
calendar and push it into [intervals.icu](https://intervals.icu), which does have its own native
ICS export. Both rejected: Wahoo's [API
Agreement](https://www.wahoofitness.com/wahoo-api-agreement) explicitly prohibits reverse
engineering its platform, both tools are small, lightly-maintained side projects vulnerable to
breaking on any Wahoo API change, and the whole chain (SYSTM to intervals.icu to ICS to a HACS ICS
component) is a lot of fragile infrastructure for a ToS violation.

Decision: skip SYSTM integration entirely rather than build something that breaks Wahoo's terms.
If pde wants specific planned SYSTM sessions to show on Overview C, the lowest-effort and only
ToS-clean path is to log them onto a Google Calendar himself (a dedicated "Workouts" calendar,
for instance); since Google Calendar is being wired up anyway, anything added there shows up on
Overview C automatically with no extra engineering. Revisit only if Wahoo ever ships real export.
