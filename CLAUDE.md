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

## Next-session checkpoint, 2026-09-03

**Home Assistant drives all thirty of the house's lighting loads now.** This is the biggest thing
in the project and it is newer than most of the documents around it. A custom integration that
registers as a physically unplugged TSW-752 touch panel controls every one of them end to end over
CIP. Read [docs/crestron/crestron-ha-bridge.md](./docs/crestron/crestron-ha-bridge.md) before
touching anything lighting-related, along with
[ADR 0066](./docs/adr/0066-crestron-bridge-needs-two-cip-connections.md) and
[ADR 0067](./docs/adr/0067-discrete-on-off-synthesised-in-the-bridge.md).

The integration lives in the **CresnetMon** repo at `custom_components/crestron_cip/`, not here,
because this repo takes no deployable code. It is deployed to `/config/custom_components/` by SFTP.

The one rule not to get wrong: the DSC alarm keypad shares AADS joins `d130` through `d148` plus
`d93`, with Fire, Medical and Panic on `d146`, `d147` and `d148`. The bridge never writes any of
them, enforced both at table-import time and immediately before bytes reach the wire. Receiving
those joins is expected and fine; only writing is refused. Do not remove either check.

Before this, every `light.*` entity was a placeholder backed by an `input_boolean`. Those and every
HA scene were deleted. Scenes are a later phase: the scene count is zero and the Homie Scenes chip
still points at the deleted ones ([issue #16](https://github.com/pdehlke/homeassistant/issues/16)).

The last four loads, the Kitchen ones, were identified and wired 2026-09-03
([issue #18](https://github.com/pdehlke/homeassistant/issues/18), now closed). Three are ordinary
toggles; Island's MC2E channel turned out to be a dimmer with a separate on join and off join
rather than one toggle, which is why `Load` in `const.py` now carries `press_on`/`press_off`
fields rather than assuming every load presses one join both ways. Every other MC2E channel the
Kitchen slot reaches is a dimmer too, so expect Phase 2 (a dedicated brightness pass, not started)
to lean on that same shape. Full record in
[crestron-xpanel-control-path.md](./docs/crestron/crestron-xpanel-control-path.md#kitchen-identification-resolved-2026-09-03).

Live release and commit state go stale fast, so confirm with `git` and the live instance rather
than trusting this line: at the time of writing, Homie is at `20260903.1`, this repo is at
`c46f3e9`, the fork is at `0ea40f7`, and CresnetMon is at `39f3f40` on `macos-port-python`. All
three were clean and in sync.

With the lighting buildout's headline work done, the open threads are smaller and independent
rather than one obvious next step. [Issue #17](https://github.com/pdehlke/homeassistant/issues/17)
(`sensor.homie_lights_status` hardcoded against entities that no longer match reality) is now
directly testable against real loads for the first time. [Issue #16](https://github.com/pdehlke/homeassistant/issues/16)
(Scenes chip pointing at deleted scenes) and [issue #1](https://github.com/pdehlke/homeassistant/issues/1)
(the Cresnet Path B spike, superseded by CIP working but never formally closed) are both still open
and `ready-for-agent`.

Two older Homie items still deferred, both predating the lighting work and neither re-verified
since 2026-08-07:

- The close-time filter-reset test on the floors card's expand button is not mutation-sensitive (a
  later unfiltered `openThermostat()` independently clears the filter). The implementation is
  correct; the test does not independently prove it. No issue filed, so this note is the only
  record of it.
- `.ov3-col3`'s `justify-content: space-between` leaves an ugly gap between the security and floors
  cards when no purifier entity is configured. Cosmetic rather than an overflow. Tracked as
  [issue #10](https://github.com/pdehlke/homeassistant/issues/10).

Homie's three credentials are environment variables (`$HA_EDIT_KEY`, `$HOMIE_PASSWORD`,
`$HOMIE_TOKEN`), not files under `/Users/pde/tmp`; that move happened on 2026-08-20 and any
document still naming those paths is stale. See the Home Assistant skill's
`references/api-access.md` for the verified patterns for each.
