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

Read
/Users/pde/src/github.com/pdehlke/homeassistant/docs/homie-dashboard/homie-dashboard-install-plan.md
completely, then read the project's Home Assistant skill at
/Users/pde/src/github.com/
[pdehlke/homeassistant/.claude/skills/home-assistant/SKILL.md](.claude/skills/home-assistant/SKILL.md). Resume Homie work
from / Users/pde/src/github.com/pdehlke/homie-dashboard on main. Do not change
anything until you have checked both repositories' status and confirmed the
documented live release and commit state.

## Next-session checkpoint — 2026-08-07

Release `20260807.16` is live and Playwright-verified. It is NOT yet committed
to the homie-dashboard fork: the working tree has the Overview C overflow fix
(CSS + version bump + tests + docs) uncommitted, last pushed commit is still
`71b07e5`. Commit (or discard) that working tree before starting anything else
there.

Overview C's 21px overflow on the Fire HD 10 (1280x800, Fully Kiosk) turned out
to be a Home Assistant chrome problem, not a Homie layout problem:
`homie-dash`'s Lovelace iframe strategy was losing 56px to HA's own top app bar.
Fixed with a `kiosk_mode` block on `homie-dash` scoped to the `Homie Dashboard`
user (`hide_header` + `hide_sidebar`), same pattern as `Tablet` elsewhere. Full
writeup with measurements in [docs/homie-dashboard/homie-dashboard-install-plan.md](./docs/homie-dashboard/homie-dashboard-install-plan.md)'s new
"Overview C vertical overflow" section.

Two things intentionally deferred, unrelated to the above:

- The close-time filter-reset test on the floors card's expand button is not
  mutation-sensitive (a later unfiltered `openThermostat()` independently clears
  the filter). Implementation is correct; the test doesn't independently prove
  it. Still open.
- `.ov3-col3`'s `justify-content: space-between` leaves an ugly gap between the
  security and floors cards when no purifier entity is configured. Cosmetic, not
  overflow. Tracked as [issue #11](https://github.com/pdehlke/homeassistant/issues/11).

No secrets were copied into either repository. The Homie user's password file
was not touched; the fix used the Homie Dashboard's own long-lived token
(already documented in `/Users/pde/tmp/homie-dashboard-token`) to verify the fix
as that account via Playwright, admin token used to verify it does _not_ affect
Pete's sessions.
