# Rachio disabled-zone detection: baseline diff, not entity_registry_updated

Home Assistant's `entity_registry_updated` (`action: remove`) event would fire with less latency
than a poll when the Rachio integration actually drops a disabled zone's entity, but it also fires
for reasons that aren't a disabled zone: an integration reload, a reauth, a genuinely deleted (not
merely disabled) zone. Trusting it alone risked false positives without testing each of those
cases individually. Chosen instead: a baseline diff against a remembered set of entities that
should exist, generically identified by a `Zone number` attribute rather than a hardcoded name
list, so a re-enabled zone is picked up automatically. See
`docs/rachio/rachio-zone-disabled-alert.md`.

## Consequences

The registry event was revisited once a later fix (trigger-timing debounce, see the reload-race
ADR) solved the reliability problem it was originally being considered to solve, without needing a
different trigger source at all — lowering its priority further rather than raising it.
