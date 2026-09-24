# [CLAUDE.md](./CLAUDE.md)

Instructions for coding agents working in this repo.

## What this repo is

An archive of discussions, planning, notes, and specs for pde's Home Assistant
buildout.

It holds documentation only. No code, no deployable configuration. The live Home
Assistant configuration lives on the Home Assistant machine itself and is not
mirrored here. Nothing in this repo is applied to anything by any tooling.

The one exception is `.claude/skills/home-assistant/`, the coding-agent skill
used to work with this Home Assistant instance. It lives here, repo-scoped,
rather than in the private dotfiles repo as a user-scoped skill, because it is
about this instance specifically. It is not a documentation file and the README
contents list does not need an entry per file inside it, but note its presence
in the README all the same.

The value of the archive is the reasoning, so preserve it. When a decision is
recorded, record the options that were rejected and why they were rejected. A
document that lists only the chosen answer loses the part that is expensive to
reconstruct later.

## What belongs here

- Migration and buildout plans.
- Hardware evaluations and purchasing decisions.
- Specs for automations, dashboards, and integrations before they are built.
- Notes on how a subsystem actually behaves, especially where it contradicts its
  own docs.
- Post-mortems on things that broke.

## What does not belong here

- Secrets of any kind. No tokens, API keys, passwords, or long-lived access
  tokens.
- MAC addresses or non-default hostnames.
- Anything identifying pde's accounts, subscriptions, or physical address.

Internal IP addresses (LAN addresses like `192.168.x.x`) are fine to write down.
They are not useful to anyone without existing access to the network.

Assume this repo may become public. Anything sensitive belongs in the private
dotfiles repo at `~/.yadr-private` instead. `hass.ehlke.net` and `mass.ehlke.net`
are fine to write down: both resolve via DNS to an internal LAN address, the
same not-useful-without-network-access exception as the IP addresses above.

## Conventions

- Write in normal, clear human prose. Full sentences. If a caveman or terse
  response mode is active in the session, it does not apply to files committed
  here.
- No em dashes.
- Wrap prose at roughly 100 columns.
- One topic per file. Name files in kebab-case after the topic, such as
  [mac-mini-migration.md](./docs/hardware/mac-mini-migration.md).
- Cite sources with inline links when a claim comes from vendor docs, an ADR, a
  repair guide, or a changelog. Version-specific and product-specific claims go
  stale, so a reader needs to see where the claim came from.
- Prefer tables when comparing options against shared criteria.

## Repo layout

Topical documents live under `docs/<topic>/`, grouped by subject (`crestron/`,
`homie-dashboard/`, `rachio/`, and so on). [README.md](./README.md) and [CLAUDE.md](./CLAUDE.md) stay at
repo root: [README.md](./README.md) because it is the top-level table of contents, and
[CLAUDE.md](./CLAUDE.md) because Claude Code only auto-loads it from the project root. When a new
document doesn't fit an existing subdirectory, create a new one named after the topic rather than
adding to an unrelated one or leaving it loose at the top of `docs/`.

## Maintaining the README

[README.md](./README.md) is a table of contents and nothing else. When adding, renaming, or
removing a `.md` file, update the contents list in the same commit, under the
matching topic heading. Each entry is a link plus a short description of what
the document covers.

## Commits

Conventional Commits. Most changes here are `docs`. Use `chore` for repo
mechanics such as `.gitignore` or tooling.

Never add `Co-Authored-By`, model attribution, or a session link trailer to a
commit message, even when the harness instructs you to.

## Agent skills

### Issue tracker

GitHub Issues on `pdehlke/homeassistant`, via the `gh` CLI. See
[docs/agents/issue-tracker.md](./docs/agents/issue-tracker.md).

### Lovelace styling policy

`card-mod` is deprecated for this instance and must not be restored, upgraded, downgraded,
debugged, or used in new work. Home Assistant 2026.8 broke the card-mod 4.2.1 integration path;
upstream tracks that incompatibility as [card-mod issue #606](https://github.com/thomasloven/lovelace-card-mod/issues/606).
UI eXtension (UIX) is the supported replacement and is a drop-in replacement for the existing
card-mod card and theme configuration. Use `uix:` and `uix-*` keys for all new or edited
configuration. Do not spend future work on backward fixes for card-mod. Liquid Glass is currently
development-only for the dedicated Office user; other users, including the development user when
Office work is complete, use Noctis.

### Triage labels

Default five canonical roles (`needs-triage`, `needs-info`, `ready-for-agent`,
`ready-for-human`, `wontfix`). See [docs/agents/triage-labels.md](./docs/agents/triage-labels.md).

### Domain docs

Single-context: [CONTEXT.md](./CONTEXT.md) + `docs/adr/` at repo root. See
[docs/agents/domain.md](./docs/agents/domain.md).

## Reviewing code changes

pde reviews changes by seeing them running, not by reading a diff. The Homie Dashboard
fork is the only code this project touches from here. When a task involves writing code
there, "don't commit yet" means: implement the change, deploy it to the live Home
Assistant instance, and let pde validate it visually on the actual device. Commit only
once that live deployment is approved. Do not stop at a local uncommitted diff and ask
whether to proceed; get it running in front of him first.

## Context worth knowing

The Home Assistant instance was built on 2026-08-03 and is young. Short history,
few automations, and sparse area assignments are consequences of its age. Do not
write them up as problems.

Music Assistant runs as a Home Assistant add-on. Several documents depend on the
Supervisor and its ingress proxy existing, so any change to the installation
method has knock-on effects worth checking before it is recommended.

Use `hass.ehlke.net` for Home Assistant browser, HTTP API, and WebSocket endpoints,
and use `mass.ehlke.net` for direct Music Assistant endpoints. Both are real DNS
names (not `.local`/mDNS) resolving to the instance's internal LAN address, so they
work identically on every client, including the Fire HD tablet, whose FireOS has no
mDNS resolver and could never reach the old `homeassistant.local`/`mass.local`
hostnames. IPv6 is disabled, so earlier advice to use a literal IPv4 address to avoid
dual-stack route ambiguity is obsolete. Do not hardcode LAN addresses or use the old
`.local` hostnames; both were retired 2026-08-11 in favor of the DNS names above. See
[docs/homie-dashboard/homie-dashboard-install-plan.md](./docs/homie-dashboard/homie-dashboard-install-plan.md)'s 2026-08-10 and 2026-08-11
checkpoints for the literal-IP workaround this replaced and the CORS bug it caused for
any client other than the tablet.

## Handoff instructions

Always read the project's Home Assistant skill at
[.claude/skills/home-assistant/SKILL.md](.claude/skills/home-assistant/SKILL.md) first. It holds
the access paths, the credentials, and the instance quirks, and picking the wrong access path is
the most common way to waste a turn here.

Then read for the work at hand rather than reading everything:

- Lighting, or anything touching the Crestron processors:
  [docs/crestron/crestron-ha-bridge.md](./docs/crestron/crestron-ha-bridge.md), then the
  `docs/crestron/` document for the specific subsystem.
- Homie Dashboard:
  [docs/homie-dashboard/homie-dashboard-install-plan.md](./docs/homie-dashboard/homie-dashboard-install-plan.md).
  It is a long ledger in reverse-chronological order, so the checkpoints at the top are the current
  state and the ones further down are history. Read the top few, not all of it.
- Vocabulary and recorded decisions: [CONTEXT.md](./CONTEXT.md) and `docs/adr/`.

Three repositories are in play, and work is not confined to any one of them:

- `pdehlke/homeassistant` on `main`, this one. Documentation only.
- `pdehlke/homie-dashboard` on `main`, at `/Users/pde/src/github.com/pdehlke/homie-dashboard`. The
  dashboard fork, and the only code this project deploys from a working copy.
- `pdehlke/CresnetMon` on `macos-port-python`, at `/Users/pde/src/github.com/pdehlke/CresnetMon`.
  Crestron protocol tooling, and the home of the `crestron_cip` Home Assistant integration.

Do not change anything until you have checked the status of every repository the task touches and
confirmed the live release and commit state against `git` and the running instance. The checkpoint
below records both, and it will be out of date sooner than it looks.

## Next-session checkpoint, 2026-09-24

### The reconnect backoff could never step back down

`CipClient._run()` set `attempt = 0` after a session that returned without raising, which reads as
"a session that worked clears the escalation". It could never fire. `_session()` has exactly one
exit that is not its own `while self._running` test going false, and that exit raises, so a clean
return meant shutdown and the statement immediately after the reset returned on it. Same class as
the `_guard()` deleted in [issue #26](https://github.com/pdehlke/homeassistant/issues/26): reads
like correct behaviour, cannot fire.

The consequence was real. The escalation was monotonic for the life of the process, so five drops
pinned it at 30s and it stayed there however long the sessions in between lasted. **The 2026-09-23
AADS outage is what that looks like in the log: reconnects at a flat 33.1s**, the 30s last step
plus connect timeout. Fixed in CresnetMon `53257bf`, keyed on whether the session reached `synced`.

Two things about the fix not to undo:

- **`reached_sync` is captured in the `finally` before `await self._close()`, because `_close()`
  clears `synced`.** Reading it after is the obvious way to write this and is silently wrong. A
  test pins the ordering.
- **`synced` is the bar rather than "the session returned", and it is a high bar on purpose.**
  Reaching it takes a registration dump, a quiet window, an entry press and that subsystem's own
  dump, so a flapping link cannot clear it and win itself a reset on every cycle.

Measured against the module driven through sync, drop and reconnect by a local CIP server: before,
across three sessions that each synced, 1s/2s/5s; after, 1s/1s/1s. A link that never syncs still
escalates 1s/2s/5s/10s.

### The bridge holds two slots, and four `mac/` scripts point at the second one

`DEFAULTS` in `const.py` gives the bridge `0x12` on the AADS **and `0x03` on the MC2E**. Four
scripts default to `0x03` on `192.168.4.59`, which is that live slot: `cip_xpanel.py:15`,
`poc_joinwatch.py:40`, `poc_joinpress.py:44`, and `poc_joinscan.py:98`, where it is hardcoded
rather than named so a grep for the constant misses it. Running any of them with default arguments
collides with production and would take the three MC2E-backed Kitchen loads offline;
`poc_joinpress.py` presses rather than only listening.

The `--allow-bridge-slot` guard on `poc_panelpress.py` and `poc_subsystem_timing.py` is the right
pattern and knows about `0x12` only. `cip_xpanel.py`'s `refuse_forbidden()` does not help either:
it keys on `if host != AADS_HOST: return`, a deliberate no-op for everything pointed at the MC2E.
[Issue #29](https://github.com/pdehlke/homeassistant/issues/29) has the suggested consolidation.
Key any guard on `(host, ipid)`, not the IP-ID alone: `0x03` on the AADS is not the bridge.

**This is why the backoff fix was not verified by dropping the production bridge.** There was no
free slot to register a throwaway client on. Forcing a real drop means deliberately colliding with
`0x12` so the AADS kicks the session, which should recover in seconds and presses nothing on entry,
but is not an agent's call to make.

### `crestron_cip` test coverage, and what the fakes now model

99 tests, up from 90. [Issue #27](https://github.com/pdehlke/homeassistant/issues/27) is closed.
Two things worth not re-deriving:

- **`FakeAvClient` now models the 60ms cursor blank**, via `blank_seconds`, defaulting to 0 so
  older tests are unaffected. Only the digitals blank. `a11` keeps describing the zone it already
  described, which is exactly why `async_set_volume` may not clear it, so the analog side stays on
  the separate `volume_arrives_after` hook. The live blank also covers `d41`, `d43` and `d47`,
  which nothing reads.
- **A fake that hooks the wrong method stops testing and does not fail.**
  `UnconfirmedCursorClient` overrode `_publish()`, which no longer runs on a zone select once the
  blank was modelled, so it quietly stopped corrupting `s11` and its test passed for the wrong
  reason. It hooks the cursor move itself now.

Every behaviour was checked by mutation rather than by the suite going green. Do that here: this
suite's failure mode is passing tests that assert nothing about the path they name.

### Path B is parked, not dead

[Issue #28](https://github.com/pdehlke/homeassistant/issues/28) proposed retiring five `mac/`
Cresnet-injection scripts and was closed `wontfix` on 2026-09-24 on pde's call, because
[#1](https://github.com/pdehlke/homeassistant/issues/1) is still open. Nothing was deleted.

Two findings from that review are in its closing comment and matter more than the decision:

- **`cresnet_replay.py` supersedes all five, not the three the issue named**, and answers their
  question better. Its `selftest` settles "does this adapter transmit" through the bus rather than
  through our own deaf receive path, which is why five earlier attempts failed structurally.
- **`mac/captures/` is gitignored**, so the `FRAMES` tables in `living_pathway.py` and
  `poc_inject.py` are the only git-tracked copies of two captured frame sets. Both are transcribed
  into the closing comment. The Living Room Pathway keypad press (`0x70` ch4 and `0x71` ch3, both
  to `0xC3`) is **not** in
  [cresnet-frame-decode.md](./docs/crestron/cresnet-frame-decode.md), which records only the touch
  panel action for that load. Transcribe them before deleting anything, if this is ever revisited.

## Next-session checkpoint, 2026-09-23

### The AADS is at 192.168.4.65 now, not .61

An unreserved DHCP lease moved it overnight on 2026-09-23 and took every AADS-backed lighting load
and all six audio zones down for ~85 minutes; the three MC2E Kitchen loads kept working throughout.
pde has since reserved `.65` to its MAC, so the address is fixed. Fixed in CresnetMon `49bc181`
(`macos-port-python`, **not pushed**), deployed and verified live. Post-mortem in
[crestron-aads-dhcp-outage.md](./docs/crestron/crestron-aads-dhcp-outage.md).

Three things from it worth not re-deriving:

- **"All AADS loads dead, MC2E fine" is a statement about the link, not the slot.** Lighting and A/V
  share the AADS connection and the MC2E is a separate connection to a separate processor, so that
  split rules out the panel slot before anything is opened. The slot was the first suspect and was
  never involved; the bridge is still `0x12`.
- **The `mac/` alarm-keypad guard is keyed on the host** (`if host != AADS_HOST: return`), so the
  stale address silently disarmed it for `poc_joinpress.py` and `poc_joinscan.py`. The integration's
  own guard keys on the *link name* and was unaffected. Identity by logical role survives a network
  change; identity by address does not. Both now proven by test in either direction.
- **`.59`, the MC2E, is still unreserved** and named by literal address in the same `DEFAULTS` table.
  It is exactly as exposed and simply has not renewed yet.

The bridge retried a dead address every 33 seconds for 85 minutes and surfaced nothing a person would
see. A repair issue or a link-health binary sensor is the obvious follow-up and has no issue yet.

## Next-session checkpoint, 2026-09-22

### Homie fork: performance work shipped, and what was left on the table

A deep code-quality audit of the Homie fork ran on 2026-09-22 against the low-power wall tablet.
**Five fixes are live**, committed and pushed on the fork's `main` (`ea7ac99`, `05703aa`, `b969b8b`,
`786c668`, `ee75b7a`, each independently revertable); `HOMIE_ASSET_VERSION` is now `20260922.3`
and the `homie-dash` iframe `?v=` matches. Full write-up, including what is still deliberately not
shipped, is in
[homie-dashboard-performance-audit.md](./docs/homie-dashboard/homie-dashboard-performance-audit.md).

The one number to carry forward: **`refreshAllUI()` used to fire on every `state_changed` event, and
96.9% of those events came from entities the dashboard never displays** (Lennox integration
internals, Zigbee plug voltage sensors). A relevance filter plus rAF coalescing cut full re-renders
by a measured 98.3% against the live stream. `stateCache` still updates on every event, so nothing
goes stale; only the render is skipped.

**The relevance set is a union of a static `CONFIG` sweep and the entities read during the last
render pass, and both halves are load-bearing.** Drop either and renders start going missing. The
read set is captured by subclassing the cache `Map`, not by instrumenting `haGetCached()`, because
16 call sites read `stateCache.get()` directly and a filter that missed them would freeze parts of
the UI with no error.

The dashboard now takes **`subscribe_entities`, deliberately unfiltered** (86.3% fewer bytes to
parse; its first message is a full snapshot, so there is no `get_states` call any more). Filtering to
the 101 entities `CONFIG` names would reach 99.3%, and was **rejected**: any entity the UI resolves at
runtime rather than by literal id would then be missing from the cache entirely, and that reads as a
silently wrong dashboard rather than an error. The remaining 13% is not worth it.

Three things about that switch are worth not re-deriving:

- **`StateCache.peek()` exists for a reason.** The delta-merge path must read previous state without
  recording a UI read. Route it through `get()` and every changed entity gets filed as "something the
  UI reads", the admissible set grows to cover everything, and the relevance filter quietly stops
  filtering.
- **There must be no `_wsReady` guard at the top of the `case "event"` block.** The seed snapshot
  arrives as an event and is what *sets* `_wsReady`, so that guard blocks the message it waits for and
  the dashboard never loads. A test pins this.
- **`last_changed` must stay an ISO string.** The wire sends float unix seconds and `_camMotionPoll()`
  feeds the value straight to `new Date()`.

**Every overlay hides with `opacity: 0`, not `display: none`, and CSS animations keep running on an
opacity:0 element.** That is the class of bug behind the animation fixes, and the reason fourteen
overlays now carry `content-visibility: hidden` when closed (~1,100 elements out of every layout
pass). `#overview2`/`#overview3` are excluded on purpose: not `.open`-gated, and pre-built so the
first swipe is instant. Assume any new infinite animation has this problem until gated.

`config.js` and `homie-custom.js` were reviewed and **needed no changes**. `homie-custom.js` is the
healthiest code here: a UMD module of 32 pure functions, zero DOM access, dependency-injected. Do not
"improve" it. The one finding in that area was the loader, which used `document.write` and so hid both
fetches from the browser's preload scanner; it is now static tags, which must stay where they are
because `config.js` references `ICONS` from the inline block just above.

The suite was **already red before this work** (it asserted a literal asset version, so it failed on
every deploy by construction) and is now 152/152 green. Fifteen tests were added; eleven of them
execute real extracted blocks rather than asserting on source text. Note these run in their own `vm`
realm, so `instanceof` and `deepStrictEqual` fail on prototype identity alone - compare fields.

Still pending, and the first thing to do in the morning: **nobody has looked at the tablet.**
Playwright is not installed on this machine. Everything is verified by test, checksum, parse, and
live WebSocket measurement against the served bytes (764 entities expanded with zero mismatches
against `/api/states`), but **not one pixel has been looked at**. The two second-pass changes in
particular - `content-visibility` on overlays, and the whole state-transport swap - are exactly the
kind that pass every offline check and still look wrong. pde accepted that risk explicitly.

Also noticed: `/config/www/community/homie-dashboard/` holds **100+ `.bak` files**, ~90 MB, going
back to 2026-08-08. The deploy procedure creates one each time and nothing prunes them.

**Home Assistant drives all thirty lighting loads and all six audio zones.** One custom
integration, registering as a physically unplugged TSW-752 touch panel, does both over CIP from a
single panel slot that it time-slices between the two subsystems. Read
[docs/crestron/crestron-ha-bridge.md](./docs/crestron/crestron-ha-bridge.md) before touching
anything lighting-related, along with
[ADR 0066](./docs/adr/0066-crestron-bridge-needs-two-cip-connections.md) and
[ADR 0067](./docs/adr/0067-discrete-on-off-synthesised-in-the-bridge.md), and
[crestron-subsystem-time-slicing.md](./docs/crestron/crestron-subsystem-time-slicing.md) before
touching anything that shares the slot.

The integration lives in the **CresnetMon** repo at `custom_components/crestron_cip/`, not here,
because this repo takes no deployable code. It is deployed to `/config/custom_components/` by SFTP.

### Four rules not to get wrong

**The DSC alarm keypad shares AADS joins `d130` through `d148` plus `d93`**, with Fire, Medical and
Panic on `d146`, `d147` and `d148`. The bridge never writes any of them, enforced in **two** places:
`const._validate()` rejects an unsafe load table at import, and `CipClient._press()` refuses with
the bytes in hand. Only the second covers every write, because entry presses and A/V presses never
come from the load table at all. Receiving those joins is expected and fine; only writing is
refused. Do not remove either check.

There used to be a third, `CrestronBridge._guard()`, and this checkpoint used to say there were
three. It applied `_validate()`'s own predicate to `_validate()`'s own data one call later, so any
table that would have tripped it failed at import and the module never loaded: it was called on
every write and could never fire. Deleted 2026-09-22 after mutation testing proved it dead, because
a check that reads like defence in depth and is not is worse than no check at all. See
[issue #26](https://github.com/pdehlke/homeassistant/issues/26). The `mac/` proof-of-concept scripts
now share one guard on `cip_xpanel.py` for the same reason: four hand-copied versions is how two of
them ended up with none.

**A panel slot holds exactly one subsystem at a time**, entered by pressing `d75` for AV, `d80` for
Climate, `d91` for Lights or `d93` for Alarm. The AADS reuses join numbers across subsystems, so
`d101` is Dining Room Table inside Lights and the AppleTV menu inside AV. The integration now
tracks which subsystem the slot is in as ordinary state and enters the right one before every
write, holding the slot lock across the switch. Nothing outside that lock may emit a join. The
latch lives in the running AADS program and a processor restart clears it, which is what took every
AADS-backed load offline for four hours on 2026-09-15
([crestron-lights-subsystem-gating.md](./docs/crestron/crestron-lights-subsystem-gating.md)). An
unconfirmed press now forgets the subsystem so the retry re-enters.

**The bridge's slot is `0x12`, the Kitchen panel, and moving it is not free.** Entering the Lights
subsystem makes the AADS switch on a light in that panel's own room, a courtesy behaviour pde had
lived with for years on the Guest Suite panel without it being written down anywhere. On `0x13`,
the Office panel's old slot, the bridge was silently switching North Sink on at every reconnect,
restart and return from A/V. `0x12` turns nothing on. Any future slot change has to be tested for
this before it ships.

**Entry dumps are partial and nondeterministic, so the bridge merges rather than rebuilds.** One
logged entry omitted seven joins that were high. Rebuilding state from a single dump published a
lit load as dark, which is how this was found. Bring-up also re-polls the AADS with a second
`UPDATE_REQUEST`; the MC2E does not answer one, so that path is gated on the link having
subsystems. Do not simplify the merge back into a rebuild.

### Scenes

Four script-backed buttons on the Homie Scenes chip: `script.scene_dinner`, `script.scene_visitors`,
`script.all_rooms_airplay` and `script.all_av_off`. None is a native HA `scene.*` snapshot, because
a snapshot cannot express the TV-off conditional, the music service-call chain, or a six-zone walk.
Design and verification in [homie-scenes-chip.md](./docs/homie-dashboard/homie-scenes-chip.md) for
the first two and
[crestron-av-zone-control-path.md](./docs/crestron/crestron-av-zone-control-path.md) for the other
two.

The two A/V buttons carry `entities: []` in the fork's `config.js` deliberately. Homie reads an
empty affected list as off, so each tap always runs its script and neither bubble ever glows. That
is honest while Home Assistant has no entity representing an audio zone.

### A/V is built and live

Six services in `crestron_cip`: `av_status`, `av_select_source`, `av_set_volume`, `av_power_off`,
`av_power_off_all`, `av_mute`. Every one takes the same slot lock the lighting commands use and
returns the zone's state afterwards. Verified live on 2026-09-22 against the AADS's own front panel
display. [Issue #20](https://github.com/pdehlke/homeassistant/issues/20) is closed; read the
document rather than the issue thread, because the body and first comment both carry claims the
build corrected.

What constrains any further A/V work:

- The zone cursor is **per slot**, so Home Assistant has its own and will not move the physical
  panels. But there is one volume join per slot, so only one zone is readable at a time. This is
  why the integration exposes services rather than six `media_player` entities that would report
  cached values for five of them.
- Volume is hold-to-ramp only, with no working direct analog write, and it resets to zero on a
  processor reboot. The speakers are inaudible below roughly 80% of full scale. Services take a
  percentage of full scale, because that is the unit the AADS works in internally.
- Selecting a source powers the zone on and overwrites the volume with a per-source preset, so
  volume must always be set after the source. The services enforce the order; callers do not.
- Powering a zone off clears its remembered source rather than muting it, and there is no join path
  back to off-but-remembering.

**Source identity beyond AirPlay and iPod is blocked on pde, not on an agent**: the AADS and
Integra wiring has been customised and the Integra's input labels do not match what they select.
Until that is untangled the source list cannot be trusted further.

### Deploying the Homie fork

Three rules, all of which were broken on 2026-09-22 and cost a round trip. They are documented in
the middle of
[homie-dashboard-install-plan.md](./docs/homie-dashboard/homie-dashboard-install-plan.md), which is
long enough that reading the top few checkpoints does not surface them.

- **Never overwrite `config.js` whole.** Its `HA_TOKEN` line is live-spliced on the Home Assistant
  host; the repo carries a short placeholder. Read the live token line back out of the file on the
  host and splice it there, so the secret never leaves the host.
- **Upload under a temp name and rename**, rather than writing over a file a client may be fetching.
- **Bump the `homie-dash` iframe's own `?v=`** with a Lovelace save, not only `HOMIE_ASSET_VERSION`
  inside the HTML. Miss it and the tablet serves cached HTML pointing at the old asset URLs, so
  nothing you deployed appears.

The SSH add-on `a0d7b954_ssh` is manual-boot. Start it before an SFTP deploy and stop it after.

### Live release and commit state

This goes stale fast, so confirm with `git` and the live instance rather than trusting the line. No
SHA is given for this repo, because the commit carrying this checkpoint is by definition the one
you are reading; use `git log -1`. Verified 2026-09-24: CresnetMon clean and pushed at `53257bf`
on `macos-port-python`. The fork was last verified 2026-09-22, clean at `8663e1c` with
`HOMIE_ASSET_VERSION` `20260922.1` matching both the live file and the dashboard iframe's `?v=`.

**The default branch, the live instance and the deployed files all agree at `53257bf`.**
`/config/custom_components/crestron_cip/` was verified byte-identical to it on all seven `.py`
files on 2026-09-24, `cip.py` at `dae59e7c`. Exactly two files have moved since `eb7a545`:
`const.py` for the AADS address (`49bc181`) and `cip.py` for the reconnect backoff (`53257bf`).
Loading either needed a full Home Assistant restart, because `manifest.json` sets
`config_flow: false` and there is no config entry to reload. Backups of each pre-deploy file are on
the host beside it as `<name>.py.bak-<timestamp>`.

Before those, seven commits arrived as `review/quality-fixes-20260922`, a code-quality review of
the whole integration, fast-forwarded onto `macos-port-python` and then deleted; the repo's history
stays linear, so they run contiguously from `93f9baa` to `eb7a545`. A tarball of the pre-review
files is on the host at
`/config/crestron_cip-before-review-fixes.tar.gz`, and the pre-deploy state was byte-identical to
`93f9baa` on all eight files, so a rollback target is exact if one is ever wanted.

What that review changed, in one line each: serialised the one entry-collection buffer inside
`CipClient` (a bring-up racing a command retry after a mid-command reconnect could take the lighting
link offline for five seconds); merged a timed-out re-poll instead of discarding up to five seconds
of live feedback; captured the writer before a press so a cancelled press still releases the join;
awaited the idle watch on shutdown; stopped caching an unconfirmed A/V cursor, which could ramp the
wrong room for eleven seconds. Then four behaviour-preserving refactors: an `_slot()` context
manager for the six A/V operations, one registration table for all ten services, a `Link` object
replacing four per-link dicts, and the `_guard()` deletion above.

Verified live on 2026-09-22 against real hardware, not just tests: discrete on and off on
`office_pool_bath` with a second `turn_on` correctly pressing nothing, `av_status` on Kitchen and
Studio with the cursor confirmed by `s11`, the idle return from A/V to Lights, and a lighting write
issued straight out of an A/V excursion re-entering Lights on demand in about one second. No
crestron error or warning in the log afterwards.

Note for the next SFTP deploy: the SSH example in the Home Assistant skill's
`references/api-access.md` uses `root@hass.ehlke.net`, which gets `Connection refused` on port 2222.
Only `192.168.4.141` works. The prose above that example already says so; the code block is stale.

### Open threads

`ready-for-agent`: [#24](https://github.com/pdehlke/homeassistant/issues/24) (Alarmo PRD),
[#29](https://github.com/pdehlke/homeassistant/issues/29) (four `mac/` scripts default to `0x03`,
the bridge's live MC2E slot), [#11](https://github.com/pdehlke/homeassistant/issues/11) and
[#10](https://github.com/pdehlke/homeassistant/issues/10) (Homie cosmetics),
[#1](https://github.com/pdehlke/homeassistant/issues/1) (Cresnet Path B spike, superseded in
practice by CIP working but deliberately left open: pde confirmed on 2026-09-24 that Path B is
parked rather than dead, which is what closed #28).

`ready-for-human`: [#23](https://github.com/pdehlke/homeassistant/issues/23) (the real Home
Perimeter join is outside both CIP connections),
[#21](https://github.com/pdehlke/homeassistant/issues/21),
[#14](https://github.com/pdehlke/homeassistant/issues/14),
[#13](https://github.com/pdehlke/homeassistant/issues/13),
[#12](https://github.com/pdehlke/homeassistant/issues/12).

`needs-info`: [#22](https://github.com/pdehlke/homeassistant/issues/22) (retire the MC2E XPanel
connection where the join map allows).

`needs-triage`: [#9](https://github.com/pdehlke/homeassistant/issues/9) (Energy panel scope) and
[#8](https://github.com/pdehlke/homeassistant/issues/8) (A/V speaker selection dropdown broken).
#8 predates all of the A/V work above and should be re-read against it rather than started from
scratch.

Closed on 2026-09-24, both written up in the checkpoint above:
[#27](https://github.com/pdehlke/homeassistant/issues/27) (the four `crestron_cip` coverage gaps,
plus the backoff defect gap 3 turned up) and
[#28](https://github.com/pdehlke/homeassistant/issues/28) (`wontfix`, Path B parked).

Closed on 2026-09-22 and worth knowing about rather than re-deriving:
[#20](https://github.com/pdehlke/homeassistant/issues/20) (A/V mapped and built),
[#25](https://github.com/pdehlke/homeassistant/issues/25) (re-enter Lights when a press goes
unconfirmed) and [#26](https://github.com/pdehlke/homeassistant/issues/26) (the alarm check that
could never fire).

**A `Fixes #NN` trailer in a CresnetMon commit will not close an issue here.** GitHub's closing
keywords only act within one repository, and this project deliberately keeps every issue in
`pdehlke/homeassistant` while most of the code lives in `pdehlke/CresnetMon` or the Homie fork. #26
was written with such a trailer, merged to the default branch, and stayed open until it was closed
by hand. Close cross-repo issues with `gh issue close` and say in the comment which commit did the
work, because nothing else links them.

### One loose end with no issue yet

[crestron-strategy.md](./docs/crestron/crestron-strategy.md) still says the AADS is being replaced
outright, and its "Rejected: keeping the AADS as a dumb amp only" section reasons from the premise
that there is no front door into the AADS's own matrix and amp functions. The A/V work disproved
that premise, exactly as the lighting work disproved it for lighting: every zone's source, volume,
mute and power is drivable today over CIP with no new hardware. That document has not been
rewritten and no issue tracks it.

### Credentials

Homie's three credentials are environment variables (`$HA_EDIT_KEY`, `$HOMIE_PASSWORD`,
`$HOMIE_TOKEN`), not files under `/Users/pde/tmp`; that move happened on 2026-08-20 and any
document still naming those paths is stale. See the Home Assistant skill's
`references/api-access.md` for the verified patterns for each.
