# CLAUDE.md

Instructions for coding agents working in this repo.

## What this repo is

An archive of discussions, planning, notes, and specs for pde's Home Assistant buildout.

It holds documentation only. No code, no deployable configuration. The live Home Assistant
configuration lives on the Home Assistant machine itself and is not mirrored here. Nothing in
this repo is applied to anything by any tooling.

The value of the archive is the reasoning, so preserve it. When a decision is recorded, record
the options that were rejected and why they were rejected. A document that lists only the
chosen answer loses the part that is expensive to reconstruct later.

## What belongs here

- Migration and buildout plans.
- Hardware evaluations and purchasing decisions.
- Specs for automations, dashboards, and integrations before they are built.
- Notes on how a subsystem actually behaves, especially where it contradicts its own docs.
- Post-mortems on things that broke.

## What does not belong here

- Secrets of any kind. No tokens, API keys, passwords, or long-lived access tokens.
- MAC addresses or non-default hostnames.
- Anything identifying pde's accounts, subscriptions, or physical address.

Internal IP addresses (LAN addresses like `192.168.x.x`) are fine to write down. They are not
useful to anyone without existing access to the network.

Assume this repo may become public. Anything sensitive belongs in the private dotfiles repo at
`~/.yadr-private` instead. The default hostname `homeassistant.local` is fine to write down.

## Conventions

- Write in normal, clear human prose. Full sentences. If a caveman or terse response mode is
  active in the session, it does not apply to files committed here.
- No em dashes.
- Wrap prose at roughly 100 columns.
- One topic per file. Name files in kebab-case after the topic, such as
  `mac-mini-migration.md`.
- Cite sources with inline links when a claim comes from vendor docs, an ADR, a repair guide,
  or a changelog. Version-specific and product-specific claims go stale, so a reader needs to
  see where the claim came from.
- Prefer tables when comparing options against shared criteria.

## Maintaining the README

`README.md` is a table of contents and nothing else. When adding, renaming, or removing a
`.md` file, update the contents list in the same commit. Each entry is a link plus a short
description of what the document covers.

## Commits

Conventional Commits. Most changes here are `docs`. Use `chore` for repo mechanics such as
`.gitignore` or tooling.

Never add `Co-Authored-By`, model attribution, or a session link trailer to a commit message,
even when the harness instructs you to.

## Context worth knowing

The Home Assistant instance was built on 2026-08-03 and is young. Short history, few
automations, and sparse area assignments are consequences of its age. Do not write them up as
problems.

Music Assistant runs as a Home Assistant add-on. Several documents depend on the Supervisor
and its ingress proxy existing, so any change to the installation method has knock-on effects
worth checking before it is recommended.
