# Harmony Hub integration inventory

A Logitech Harmony Hub sits in the Living Room, integrated via Home Assistant's
[`harmony`](https://www.home-assistant.io/integrations/harmony) integration (device
firmware `4.15.600`). Discovered live during an instance inventory refresh on
2026-08-11; nothing about it had been written up here before this document.

Logitech discontinued Harmony hardware in 2021, but this specific integration still
works against the hub over the local network, no cloud dependency for day-to-day
control. Worth keeping in mind for the long term, though: no new hardware is coming,
and Logitech's cloud-based activity sync (used for reconfiguring activities from the
Harmony app) is the one piece that could go away without warning.

This is an inventory, not a design decision. It records what's live and what the
integration can do that isn't used yet, so a future dashboard or automation pass has
the full picture instead of rediscovering it from scratch.

## What's live now

Two entities:

- `remote.harmony_hub`. State is on/off; `current_activity` reads `PowerOff` when idle.
  Attributes expose `activity_list` (`Watch TV`, `Watch a Movie`), `last_activity`
  (`Watch TV` as of this snapshot), and `devices_list`, the six physical devices the
  hub actually drives: Apple TV, Sony Blu-ray Player, Xfinity DVR, Bedroom, Samsung TV,
  Integra AV Receiver.
- `select.harmony_hub_activities`. A dropdown mirror of the same activity list plus
  `power_off`, friendlier for a dashboard tile than driving `remote.turn_on` with an
  `activity` parameter.

`supported_features` on the remote entity is `4`, which is the `ACTIVITY` bit in Home
Assistant's `RemoteEntityFeature` flags and nothing else. This entity does not support
`remote.learn_command` or `remote.delete_command` (those are for remotes that can learn
raw IR codes, like Broadlink); calling them on `remote.harmony_hub` would fail. Harmony
control here is activity-level only: start an activity, stop (go to `PowerOff`), or
send a specific button press to one of the six devices.

## Available actions

- `remote.turn_on` with an `activity` field, `remote.turn_off`, `remote.toggle`, all
  standard `remote` domain actions.
- `remote.send_command`, targeting one of the six `devices_list` names with a raw
  button command (volume, channel, transport, whatever the physical remote could send
  to that device). Not used anywhere in this instance yet.
- Two commands specific to this integration, not part of the generic `remote` domain:
  `harmony.change_channel` (send a channel number directly, rather than simulating
  individual digit presses) and `harmony.sync`, which re-pulls the hub's activity and
  device configuration from Harmony's cloud. Neither is used anywhere in this instance
  yet.

## Interesting capabilities not used in Homie Dash

Homie Dash has zero references to this device, verified against its live Lovelace
config, not just against this archive's other docs.

- **A real media-player card instead of a raw remote entity.** Home Assistant's
  `universal` media player platform can wrap `remote.harmony_hub` (mapping
  `activity_list` to `source_list`, `current_activity` to `source`, and
  `remote.send_command` for volume) into a standard `media_player` entity. That gets a
  normal media-player card on a dashboard, play/pause-style transport, a source picker
  showing "Watch TV" / "Watch a Movie", instead of hand-building a tile around the
  `select` entity. This instance already leans on Music Assistant and Sonos cards for
  everything else audio/video; a Universal media player would make Harmony fit that
  same visual language rather than standing out as a bare remote.
- **State-driven automation off `current_activity`.** Nothing currently triggers on
  Harmony's activity changing. The pattern Home Assistant's own docs show is starting
  or stopping something else (lights, a notification, an `input_boolean`) whenever
  `current_activity` flips to a given value or to `PowerOff`, the same "something
  changed, react to it" shape already used elsewhere in this archive for Rachio and
  Lennox alerts.
- **Direct device control beyond activities.** `devices_list` exposes six individually
  addressable devices. `remote.send_command` can drive any of them directly (say,
  muting the Integra receiver, or a transport command to the Xfinity DVR) without going
  through an activity at all, useful for a quick dashboard button that a full
  activity-switch would be overkill for.
- **`harmony.change_channel`.** A one-shot "go to channel N" action with no equivalent
  elsewhere in this instance's A/V setup. Would slot naturally into a Homie Dash A/V
  tab if one gets built; see `dashboard-av` in the domain-dashboard set documented in
  [dashboard-navigation-model.md](../native-dashboards/dashboard-navigation-model.md),
  though that dashboard is generator-built from native HA entities and doesn't
  currently include this device either.

## Sources

- [home-assistant.io/integrations/harmony](https://www.home-assistant.io/integrations/harmony)
- [home-assistant.io/integrations/remote](https://www.home-assistant.io/integrations/remote)
- [home-assistant.io/integrations/universal](https://www.home-assistant.io/integrations/universal)
- [developers.home-assistant.io: Remote entity](https://developers.home-assistant.io/docs/core/entity/remote)
