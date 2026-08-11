# Cloud remote UI setup wedges permanently on any transient DNS hiccup

## Symptom

Home Assistant Cloud (Nabu Casa) was being set up for remote access, using a custom domain pointed
at Nabu Casa via two CNAME records. The Nabu Casa console confirmed both validated correctly.
Locally, the instance never got past this: `binary_sensor.remote_ui` stayed
`unavailable`, and `home-assistant.log` showed `hass_nabucasa` failing with `DNSError: Timeout
while contacting DNS servers` while trying to reach `api.nabucasa.com`. After the first failure,
nothing retried. Six hours later it was still stuck in the same state.

The instance-level root cause (a mistyped DNS fallback server, see below) is fixed. This document
is about what turned out to be the more important finding: `hass_nabucasa`'s remote-UI/ACME
certificate flow has effectively no tolerance for a single transient DNS failure, anywhere in a
multi-call sequence, and no automatic retry once it gives up. That is a source-level fragility, not
a configuration problem, and it will resurface on any Home Assistant instance that hits a DNS blip
at the wrong moment, regardless of how clean the DNS setup is.

## Timeline and evidence

| When (local, UTC-7) | Event |
|---|---|
| Original `nabu.log` | Two independent failures, `16:59:49` and `19:59:48`, both inside `hass_nabucasa.remote`'s certificate handler, both `Timeout while contacting DNS servers` on `api.nabucasa.com`. |
| (diagnosis) | `wlan0`'s static DNS nameservers were `9.9.9.9` and `149.112.112.212`. The second address is a typo of Quad9's real secondary, `149.112.112.112`, transposed. Confirmed dead by direct `dig`: no response at all, not even an ICMP unreachable. Supervisor's own resolution center had already flagged it (`dns_server_failed`, `dns_server_ipv6_error`), and `hassio_dns` (the Supervisor DNS plugin, CoreDNS-based) had inherited the same broken address as one of its two upstream fallbacks. |
| (fix) | `ha network update wlan0 --ipv4-method auto --ipv4-nameserver 9.9.9.9 --ipv4-nameserver 149.112.112.112`, then `ha dns restart`. Verified with a 40-way concurrent burst of lookups through `hassio_dns`: 0 failures, versus a consistent ~6s stall per query beforehand whenever the dead address was drawn. Supervisor's `dns_server_failed`/`dns_server_ipv6_error` issues cleared. |
| `18:00:23`, `19:00:24` | `sense.coordinator` independently hit the identical failure signature (`Timeout while contacting DNS servers`, `api.sense.com`) near the top of the hour, both before and unaffected by the nameserver fix above. Never identified the process driving this; `hassio_dns`'s own access log around `03:00:13` showed an ~85-query PTR sweep of the full `192.168.4.0/22` subnet, sourced from `127.0.0.1` and `172.30.32.1` (the docker bridge gateway, i.e. from a process on the HA host itself), but no `device_tracker`/nmap-style entities exist on this instance to explain who runs it. |
| `02:03:13` (first Core restart, after the nameserver fix) | `_certificate_handler` still failed with the same DNS timeout, at `cleanup_dns_challenge_record` specifically, ~90 seconds after boot. |
| `02:16:09` (second Core restart) | Same failure, same call site. |
| `02:24:56`–`02:25:03` (third Core restart) | A **completely independent** reproduction, run concurrently from a different container (the SSH & Web Terminal add-on, not Home Assistant Core) using `aiodns` directly against `hassio_dns` (`172.30.32.3`): 4 consecutive query failures out of 285 total, each timing out in ~1.0-1.5s. `hassio_dns`'s own access log has **zero** entries for this window: the queries never reached CoreDNS's logging middleware at all. `sense.coordinator` hit the same DNS timeout again 7 seconds later, at `02:25:10`, from inside Core. |
| ~`02:26:xx` | Third restart's certificate flow landed outside the bad window and completed: `remote_certificate_status: ready`, `remote_connected: true`, real certificate issued covering the custom domain, expiring `2026-11-08`. |

The 60x sequential A, 60x sequential AAAA, and 60x concurrent A+AAAA queries run in isolation (no
contention) all succeeded cleanly and fast, which ruled out an IPv6/AAAA-specific c-ares hang as
the mechanism. The failures only appeared during bursts of concurrent DNS activity: Home Assistant
Core's own mass integration startup (dozens of integrations, several cloud-backed, all resolving
and connecting within the first couple of minutes after boot) and, separately, the unidentified
hourly subnet-wide PTR sweep. Both point at the same underlying weak spot from different angles.

## Root cause, two layers

**Layer 1 (fixed): a dead DNS fallback server.** A single mistyped IP in `wlan0`'s static
nameserver config meant `hassio_dns`'s upstream forward list had one live server and one that
silently dropped every UDP query. Any client query that happened to draw the dead server first
paid a multi-second stall before failing over. This was the dominant cause of the *original*,
more frequent failures (including the ones affecting OpenWeatherMap, which is what prompted this
investigation in the first place). Fixed and verified; not the subject of the rest of this
document.

**Layer 2 (not fixed, source-level): the ACME/remote-UI flow assumes DNS never has a bad moment.**
Even with both upstream resolvers healthy, a Raspberry Pi 4 running HAOS produces short windows
(observed: single-digit seconds) where DNS UDP queries to the internal `hassio_dns` container are
dropped somewhere below CoreDNS, most plausibly conntrack/iptables contention from a burst of
concurrent outbound connections. This is a real, if narrow and hard-to-eliminate, reliability
characteristic of the platform under load, not a misconfiguration. `hass_nabucasa`'s certificate
handler has no defense against landing in one of these windows, and the consequence is total and
silent: the entire multi-call certificate issuance sequence dies on the first hiccup, on whichever
call happens to be in flight, and nothing retries until the next full Home Assistant Core restart.

## Fragile assumptions found in the source (for a future fix or upstream report)

All file/line references are from the `hass_nabucasa` package as vendored inside Home Assistant
Core `2026.8.1` (path `/usr/local/lib/python3.14/site-packages/hass_nabucasa/`, Python 3.14). The
exact `hass_nabucasa` pip version was not captured directly; look it up from `home-assistant/core`'s
requirements pinned at the `2026.8.1` tag before filing anything upstream, in case line numbers
have shifted.

1. **`remote.py:595`, `_certificate_handler`** (the task logged as "Remote UI loop"): calls
   `load_backend()` and, on any exception, logs `Unexpected error in Remote UI loop` and stops.
   Observed behavior across five separate failures in this session: it does not reschedule itself,
   does not back off and retry, and does not distinguish a transient network error from a
   permanent one. The only way to get another attempt is an external trigger; in practice, only a
   full Home Assistant Core restart or a `cloud` config-entry reload was observed to produce one.
   This is the central fragile assumption: **the whole ACME flow assumes every network call it
   makes will succeed, for its entire duration, on the first try.**

2. **`acme.py:555`, `issue_certificate`**: the specific call that failed every time in this
   session, `cleanup_dns_challenge_record`, runs unconditionally after the challenge validates,
   with no retry and no `try`/`except` around just this step. Given the DNS-01 flow already
   proved it can reach `api.nabucasa.com` earlier in the same sequence (to create the challenge),
   a failure here means the certificate may already be validated and nearly issued, only to be
   thrown away because the last housekeeping call hit a one-off network blip. A narrowly-scoped
   retry (a few attempts with short backoff) around this one call, or treating its failure as
   non-fatal to the overall issuance, would have prevented every failure observed here.

3. **`remote.py:485` (`connect`) and `remote.py:554` (`disconnect`)**: both raise
   `RemoteNotConnected("Can't handle request-connection without backend")` when
   `self._backend` is `None`, i.e. whenever no certificate has ever been successfully issued yet.
   This fires from `homeassistant/components/cloud/__init__.py`'s `on_prefs_updated` handler
   (triggered by the `cloud.remote_connect` / `cloud.remote_disconnect` services, and by toggling
   the Remote UI switch in the frontend, which calls the same code path) and surfaces as an
   unhandled traceback in the Core log, not a clean, actionable error. More importantly: **calling
   the documented public recovery service does not actually retry certificate issuance.** A user
   who hits this stuck state and reaches for the obvious self-service fix (toggle remote access
   off and on) gets a repeat of the same exception, not a new attempt. This is what produced the
   "failed once and gave up" symptom reported at the start of this investigation, and it is
   actively misleading: the tools that look like recovery mechanisms are not.

4. **No visible circuit-breaker or jitter.** Across the observed failures, `_certificate_handler`
   appears to run once at `cloud` component setup and effectively never again on its own. There is
   no evidence of a periodic retry with backoff of the kind that would let an instance self-heal
   from a bad five-second window without operator intervention. Whether a longer-period
   retry exists and simply did not fire within the ~7-hour observation window was not conclusively
   ruled out; if a next investigation confirms one does not exist, that is the single highest-value
   fix to propose upstream.

## Fixes applied here

- Corrected the `wlan0` static nameserver typo (Layer 1). Durable; will not recur on its own.
- Forced past Layer 2 empirically: restarted Home Assistant Core three times until the
  certificate handler's one-shot attempt happened to land outside a bad DNS window. This is a
  workaround, not a fix. It worked because the bad windows observed were on the order of single
  digit seconds within a multi-minute restart cycle, so the odds favored eventual success, not
  because anything was done to close the underlying gap.

## Open items

- **File an issue against `NabuCasa/hass-nabucasa`** describing point 1-3 above: the certificate
  handler should retry transient network failures with backoff instead of dying silently, and the
  `remote_connect`/`remote_disconnect` services should either trigger a fresh certificate attempt
  when none is in flight, or fail with a clear, documented error instead of a raw
  `RemoteNotConnected` traceback. Not yet filed; this document is the prep work for doing so with
  a concrete, reproduced timeline instead of a one-off report.

  Update, 2026-08-10: a fix for points 1 and 2 (the narrow `except` clauses around the DNS
  challenge create/cleanup calls, and `_certificate_handler` re-raising instead of retrying) was
  written and committed on branch `fix/remote-ui-dns-fragility` in the `pdehlke/hass-nabucasa`
  fork. Not pushed or opened as a PR upstream yet.
- **Identify what runs the hourly full-subnet PTR sweep.** Still unknown. It is not HA's
  `device_tracker` platform (no nmap/ping-based tracker entities exist on this instance) and it
  sources from the HA host itself (`127.0.0.1` and the docker bridge gateway), not from another
  device on the LAN. Worth finding, since it is an independent contributor to the same class of
  DNS contention documented here, separate from Core's own startup burst.
- **Confirm or rule out a genuine retry-with-backoff inside `_certificate_handler`.** This
  document assumes there isn't one, based on ~7 hours of silence after the first failure, but that
  is circumstantial. Reading the actual source (not just its tracebacks) before filing upstream
  would firm this up.
- **`ha core logs` returned stale output** during a long-running boot session; `-f`/follow only
  reliably streamed current content right after a fresh Core restart. Not chased down. Possibly a
  Supervisor log-streaming quirk worth its own investigation, unrelated to the DNS issue.
- **Minor `ha network update` CLI gotcha**: calling it with `--ipv4-nameserver` but without an
  explicit `--ipv4-method` did not simply update the nameserver list. It appended to the existing
  list and then failed validation ("method 'manual' requires at least an address or a route"),
  leaving a transiently worse three-entry nameserver list (old broken entry still present, two
  good ones appended) until retried with `--ipv4-method auto` supplied explicitly. Always pass
  `--ipv4-method` explicitly when touching nameservers on this Supervisor version.

## Verification

- DNS fix: direct `dig` against both the old (dead) and corrected fallback addresses, a 40-way
  concurrent burst through `hassio_dns` with zero failures, and Supervisor's resolution-center
  issues clearing.
- Remote UI: `cloud/status` over the websocket API showing `remote_connected: true`,
  `remote_certificate_status: ready`, and a real certificate covering the custom domain with a
  normal Let's Encrypt expiry, plus `binary_sensor.remote_ui` reading `on`.
- Layer-2 mechanism: an independent `aiodns` reproduction from a second container, run
  concurrently with a live Core restart, that failed in the same way at the same time as Core's
  own `sense.coordinator`, with `hassio_dns`'s access log showing no record of the failed queries
  ever arriving.
