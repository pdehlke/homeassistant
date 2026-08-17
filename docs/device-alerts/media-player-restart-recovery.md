# Media player restart recovery

Automation and helper script that, after Home Assistant restarts, reload any `media_player` left
`unavailable` and notify in-app if that doesn't fix it, so a stuck integration after a crash
doesn't require someone to notice and manually reload it.

| Object | Entity |
|---|---|
| Automation | `automation.recover_stuck_media_players_after_restart` (id `1786812930774`) |
| Helper script | `script.reload_media_player_config_entry` |

Both live and enabled. Created 2026-08-15, verified working the same day against Home Assistant
2026.8.1.

## Why it exists

On 2026-08-15 the Home Assistant host restarted uncleanly around 08:46 local (recorder logged an
unfinished session and an unclean database shutdown, both signatures of a hard restart rather than
a graceful one). Home Assistant's Music Assistant client failed to reconnect to the Music
Assistant App's websocket for several minutes afterward, and several `media_player` entities went
`unavailable`. Most recovered on their own within about a minute. Three did not, and were still
`unavailable` when checked roughly 45 minutes later: the bedroom Sonos/Cast entity, its
Music-Assistant-side counterpart, and an Apple TV. Getting them back required a manual config-entry
reload. Full incident, including how this connects to the Homie Dashboard Music/A/V chip symptom
it was originally mistaken for, is in the 2026-08-15 checkpoint in
[homie-dashboard-install-plan.md](../homie-dashboard/homie-dashboard-install-plan.md).

pde didn't want to have to notice and manually reload things after every restart. This automates
the one recovery step that actually helped (a config-entry reload) and tells him, in-app only, when
that wasn't enough.

## How it works

Broad by design: it watches every non-TV `media_player` entity, not a hand-maintained list of the
ones known to be fragile today. Television entities are excluded because their unavailable state
is expected when they are powered off or disconnected. The exclusion currently covers
`media_player.carol`, `media_player.carol_2`, `media_player.gymnasium`, and
`media_player.lg_webos_tv_um7300pua`. On 2026-08-15, the original broad query found several TVs
alongside the audio players that needed recovery; those TVs are now exempt.

```yaml
alias: Recover stuck media players after restart
triggers:
  - trigger: homeassistant
    event: start
    note: 5 min grace period below lets normal reconnects (e.g. crestron, ~1 min) finish on their
      own before we touch anything.
conditions: []
actions:
  - delay:
      minutes: 5
  - variables:
      stuck_entities: >
        {{ states.media_player | selectattr('state', 'eq', 'unavailable')
           | map(attribute='entity_id')
           | reject('in', ['media_player.carol', 'media_player.carol_2',
                          'media_player.gymnasium', 'media_player.lg_webos_tv_um7300pua'])
           | list }}
  - if:
      - condition: template
        value_template: "{{ stuck_entities | length > 0 }}"
    then:
      - repeat:
          for_each: "{{ stuck_entities }}"
          sequence:
            - action: script.turn_on
              target:
                entity_id: script.reload_media_player_config_entry
              data:
                variables:
                  target_entity: "{{ repeat.item }}"
      - delay:
          seconds: 60
      - variables:
          still_stuck: "{{ stuck_entities | select('is_state', 'unavailable') | list }}"
      - if:
          - condition: template
            value_template: "{{ still_stuck | length > 0 }}"
        then:
          - action: persistent_notification.create
            data:
              title: Media players still unavailable after restart
              message: >-
                Reloaded after HA restart but still unavailable: {{ still_stuck | join(', ') }}.
                Likely needs a physical/network check rather than another reload.
              notification_id: media_player_restart_recovery
mode: single
```

The 5 minute delay is a grace period: `crestron` recovered from this exact outage on its own in
about a minute once Music Assistant's connection came back, and the automation shouldn't fight
that. One reload attempt only, not a retry loop: the three entities that stayed down did so even
after a manual reload *and* a full Music Assistant App restart, which points to the physical
devices being unreachable rather than a software hiccup that more attempts would fix. Retrying
blindly can't repair hardware.

### The isolation problem, and why it's not `continue_on_error`

The reload step doesn't call `homeassistant.reload_config_entry` directly. It calls a small helper
script instead:

```yaml
alias: Reload media_player config entry
fields:
  target_entity:
    required: true
    selector:
      entity:
        domain: media_player
sequence:
  - action: homeassistant.reload_config_entry
    target:
      entity_id: "{{ target_entity }}"
mode: parallel
max: 10
```

fired via `action: script.turn_on` with `data.variables.target_entity`, not by calling
`homeassistant.reload_config_entry` inline inside the `repeat`.

The first version did call it inline, guarded with `continue_on_error: true`. That looked right
and validated cleanly, but broke on the very first live test: the bedroom Cast entity's config
entry rejects reload outright ("cannot be unloaded because it is in the non recoverable state"),
and that error aborted the *entire automation run* mid-loop, silently skipping every later entity
and the notify step that was supposed to be the safety net. `continue_on_error` did not help,
confirmed against Home Assistant's own docs
([home-assistant.io/docs/scripts/#error-handling](https://www.home-assistant.io/docs/scripts/#error-handling)):
it explicitly does not suppress "misconfiguration or errors that Home Assistant does not handle,"
and a config entry refusing to unload falls in that class, not the ordinary
recoverable-service-call-failure class the flag is meant for. Reproduced twice before accepting
that placement wasn't the problem.

`action: script.turn_on` is genuinely fire-and-forget: the caller gets an immediate acknowledgment
and never awaits or observes the started script run, so nothing that script does, including an
"unhandled" error, can propagate back and abort the caller. Confirmed by firing the helper script
directly at the known-bad Cast entity and watching the error land only in
`homeassistant.components.script.reload_media_player_config_entry`'s own log, never in the caller's
trace. (Calling the script's own dynamically-generated service, `action:
script.reload_media_player_config_entry`, would *not* give this isolation — that form blocks and
re-propagates the child's error the same as calling the action directly. Only the generic
`script.turn_on` detaches.)

Cost of this approach: a failed reload attempt leaves no error in the automation's own trace, only
inferable from the target entity still being unavailable at the 60 second recheck. Acceptable here
because the automation's actual correctness condition, whether the entity recovered, doesn't depend
on knowing *why* a reload attempt failed.

## Remaining gaps

Nothing clears `media_player_restart_recovery` when a flagged entity later comes back on its own;
`notification_id` means a later run overwrites it rather than stacking, but a stale "still down"
notice for something no longer down is possible if a device recovers between runs.

No mobile push, deliberately (pde's call): `persistent_notification.create` only, nothing routed to
`notify.notify` or a phone.

TV entities are intentionally outside this automation's scope. If another television is added,
add its entity ID to the exclusion list before treating it as a recovery candidate.

## Gotchas hit while building this

**Persistent notifications are not entities.** `GET /api/states` filtered on
`persistent_notification.` returns nothing whether or not notifications exist — confirmed here the
same way the [fridge failure alert](fridge-failure-alert.md) already documents it. Query them over
WebSocket instead:

```bash
python3 scripts/haws.py '{"type":"persistent_notification/get"}'
```

**Supervisor reports a stopped add-on as `state: error`, not `state: stopped`.** The SFTP add-on
used for Homie Dashboard deploys is `boot: manual` and sits stopped between uses by design; its
`error` state on its own isn't evidence anything is actually broken, only that it isn't running.

## Reproducing

```bash
U=http://hass.ehlke.net:8123
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$U/api/config/automation/config/1786812930774"
curl -s -H "Authorization: Bearer $HA_TOKEN" \
  "$U/api/config/script/config/reload_media_player_config_entry"
```

Trigger a manual test run (takes just over 6 minutes end to end, the delays are real):

```bash
python3 scripts/haws.py '{"type":"call_service","domain":"automation","service":"trigger","target":{"entity_id":"automation.recover_stuck_media_players_after_restart"},"service_data":{"skip_condition":true}}'
```
