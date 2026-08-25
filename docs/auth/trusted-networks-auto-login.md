# Auto-login for the Office wall display: the trusted networks auth provider

The Office wall display is a Raspberry Pi at `192.168.4.136` running a browser against this
instance's own frontend. As of 2026-08-25 it logs itself in as the `office` user with no login
screen and no user picker, using Home Assistant's
[trusted networks auth provider](https://www.home-assistant.io/docs/authentication/providers/#trusted-networks).
Built and verified live on Home Assistant 2026.8.3.

## What was added

`auth_providers` has no UI. The block goes in `/config/configuration.yaml` on the Home Assistant
VM, inserted directly after `default_config:`:

```yaml
homeassistant:
  auth_providers:
    - type: trusted_networks
      trusted_networks:
        - 192.168.4.136/32
      trusted_users:
        192.168.4.136: <office user id>   # from config/auth/list over the WebSocket API
      allow_bypass_login: true
    - type: homeassistant
```

The real user id is in the live file and deliberately not reproduced here, per this repo's rule
about anything identifying pde's accounts. Read it back with
`python3 .claude/skills/home-assistant/scripts/haws.py '{"type":"config/auth/list"}'`, which
returns `id`, `username`, `group_ids`, and `local_only` for every account.

Each key earns its place:

- `trusted_networks` is a `/32`, one address, not the LAN. It is the list of addresses allowed to
  use this provider at all.
- `trusted_users` maps that address to exactly one account. Without it the provider offers a user
  picker rather than a specific identity.
- `allow_bypass_login: true` is what removes the login screen entirely. It only skips the screen
  when the first matching provider resolves to exactly one user, which is why the mapping above
  has to be a single id rather than a list or a `group:` entry.
- `- type: homeassistant` has to be repeated explicitly. Declaring `auth_providers` at all
  replaces the default set, so leaving it out would have removed password login for every account
  on the instance, pde's included.
- Order is load-bearing. Providers are evaluated top to bottom, so `trusted_networks` has to come
  first for the bypass to fire before the password provider is reached.

## The reverse proxy is what makes this fragile

Home Assistant sits behind the Caddy LXC at `192.168.4.143`
([caddy-reverse-proxy.md](../networking/caddy-reverse-proxy.md)), and the direct `:8123` port no
longer answers at all, so every request the display makes arrives through the proxy. Two settings
in Settings > System > Network, HTTP server section, decide whether this provider can work
([http integration docs](https://www.home-assistant.io/integrations/http/), moved from YAML to the
UI in 2026.8):

- Trust X-Forwarded-For is on. Without it, HA sees the proxy's address as the client for every
  request and the Pi is indistinguishable from every other browser in the house.
- Trusted proxies is `192.168.4.143/32`, the proxy alone.

That second value is the one that quietly decides the outcome. Home Assistant refuses to
authenticate any client whose own address falls inside a trusted proxy range, with "Your computer
is not allowed", so a convenience-shaped `192.168.4.0/24` there would have made trusted-networks
auth impossible for every device on the LAN, including this one. It was already correctly narrow
before this work started; nothing about it needed changing.

## Verified live, 2026-08-25

- `POST /api/config/core/check_config` returned `{"result":"valid","errors":null,"warnings":null}`
  before the restart.
- Home Assistant was restarted, since auth providers are read only at startup and have no reload.
  It came back with `/api/` returning 200.
- The provider is loaded and refuses non-matching addresses: `POST /auth/login_flow` with handler
  `trusted_networks` from an admin workstation on the same LAN returns
  `{"type":"abort","reason":"not_allowed"}`. A provider that is not configured at all returns a
  bare 500 instead, confirmed by asking the same endpoint for the `command_line` handler, which
  this instance does not have. The abort is therefore the positive signal here.
- Password login survived the `auth_providers` declaration: the same call with handler
  `homeassistant` returns a `form` step at `step_id: init`.
- pde confirmed the Pi itself lands on the dashboard, which is the only test that proves the
  mapping end to end.

That last point cannot be checked from anywhere but the display. Sending a spoofed
`X-Forwarded-For: 192.168.4.136` from another machine does not simulate it: Caddy appends the real
client address to the header, and Home Assistant takes the rightmost address that is not a trusted
proxy, so the spoofed value is ignored. That is the security property working as intended, and
the reason the end-to-end check has to happen at the panel itself.

## Options rejected

| Option | Why not |
| --- | --- |
| Provision a long-lived token onto the display, the Homie Dashboard pattern ([ADR-0027](../adr/0027-homie-token-plaintext-dedicated-user.md)) | Homie needs a token because it is a standalone app authenticating over the WebSocket API. The Office display is an ordinary browser pointed at HA's own frontend, so a token would have to be injected into browser storage and re-injected on every rotation or reimage. |
| Log in by hand once and rely on the stored refresh token | Works until the browser profile is cleared, the kiosk is reimaged, or the token is revoked, and then a wall panel silently shows a login screen with no keyboard in front of it. Also needs the password typed at the panel. |
| `trusted_networks` with no `trusted_users` | Gives a user picker rather than an identity. `allow_bypass_login` does nothing unless exactly one user resolves for the address. |
| Widen `trusted_networks` to `192.168.4.0/24` | Every device on the LAN would authenticate as Office, including phones and laptops that already have their own accounts. |

## The trade-off being accepted

The IP address is the credential. Anything answering at `192.168.4.136` gets the Office identity
with no secret at all, and LAN addresses are spoofable by anything already on the network. Two
things keep the blast radius small: `office` is in `system-users`, not `system-admin`, and it is
`local_only: true`, so the identity is useless from outside the LAN even if Nabu Casa remote access
is in play. This is the normal trade for a wall panel with no keyboard, and it is the reason the
grant is a `/32` rather than a subnet.

## Operational notes

- `/config/configuration.yaml` is mode 0600, owned by root, on the HA VM. Reach it over SSH at
  `root@192.168.4.141:2222` with `$HA_EDIT_KEY`; the SSH & Web Terminal add-on is manual-boot, so
  start it first and stop it afterwards
  ([api-access.md](../../.claude/skills/home-assistant/references/api-access.md)).
- The pre-change file is backed up on the VM at `/config/configuration.yaml.bak-20260825-auth`
  (1398 bytes). Safe to delete once the arrangement has survived a while.
- Changing any of this needs a full Home Assistant restart, not a YAML reload.

## Still open

- `192.168.4.136` needs to be a DHCP reservation or a static address. Whether it currently is was
  not confirmed as part of this work. If the lease moves, the display silently drops to a login
  screen and some other device inherits the Office identity.
- The Pi's browser start URL is pde's to set and was not touched here.
