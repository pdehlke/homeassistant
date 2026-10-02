# Homie A/V chip

The A/V chip on Homie Dash controls the six Crestron audio zones. It carries the same controls as
Home Assistant's Speakers dashboard (`dashboard-speakers`), built on 2026-10-02.

## The request

Earlier the same day the chip had been emptied: its five Music Assistant categories moved to the
Music chip, and it was left in the row as a placeholder because pde had follow-up plans for it. See
[homie-music-chip.md](./homie-music-chip.md)'s 2026-10-02 section. The follow-up, in pde's words:
"take the functionality of the Speakers dashboard and add it as the content for the now empty A/V
chip on Homie Dash."

## What the Speakers dashboard has

Read from the live Lovelace config rather than from memory:

- A badge for `binary_sensor.crestron_link_aads`.
- Three buttons. All AirPlay runs `script.all_rooms_airplay`, All Off runs `script.all_av_off`, and
  Refresh presses `button.crestron_audio_refresh`.
- One markdown line built from the refresh button's `oldest_read` attribute, followed by a fixed
  reminder that a wall panel can change a room without Home Assistant noticing.
- Six `entities` cards, one per zone, each with four rows: the audio switch, the source select, the
  volume number and the mute switch.

The entity model behind those is in
[crestron-audio-entity-model.md](../crestron/crestron-audio-entity-model.md).

## What was built

The chip keeps `action: "av"` and gains an `av` block in the fork's `config.js` naming the link
sensor, the refresh button, the two scripts, and each zone's four entities. A tap opens its own
overlay, `#av-overlay`: the link state in the header, the three buttons, the freshness line, and six
cards in a 3x2 grid. Each card has a power button, a source picker, a volume slider and a mute
button.

Decisions worth keeping:

- **Source options and the volume range come from the entities at render time.** The select's
  `options` attribute and the number's `min`, `max` and `step` are read from state, so the panel
  cannot drift from the integration. Only entity ids and room labels are in config.
- **Room labels are the Crestron names**, for the reason the Speakers dashboard uses them: the wall
  panels are the competing interface for these rooms.
- **Nothing is optimistic.** A zone command takes seconds, because the bridge has to take the panel
  slot and walk its cursor to the room. Home Assistant's REST service call does not return until
  the command has finished, so the card is marked busy for the life of that call and then repaints
  from reported state. A card that flipped at tap time would be wrong for several seconds in the
  ordinary case and wrong for good when a command fails.
- **The two scripts are called as `script.<name>`, where the Speakers dashboard uses
  `script.turn_on`.** `turn_on` returns as soon as the script has started. Calling the script as a
  service returns when it has finished, which is what keeps the All AirPlay button busy for the ten
  seconds a six-room walk takes. A second tap while busy sends nothing.
- **The panel is repainted in place and never rebuilt.** A rebuild on every state change would
  close an open source picker and move a slider under a finger. A slider that is mid-drag is left
  alone until it is released.
- **An off or unread room keeps power and source live.** Its volume and mute entities report
  `unavailable` and those two controls are disabled, but either power or source is how the room
  gets switched on, so they stay usable.
- **The freshness wording and thresholds are copied from the dashboard's template**, in a pure
  function, `avFreshnessText()`, in `homie-custom.js`. The line is an age, so the panel also
  re-renders it every 30 seconds while open.
- **The chip glows while any room is on.** The Speakers dashboard has no equivalent; this follows
  what every other Homie chip does.

The relevance filter needed no change. Every entity id in the `av` block is found by the static
`CONFIG` sweep, so a change to any of them triggers a render.

## Rejected

| Option | Why not |
|---|---|
| An iframe of the Speakers dashboard inside the chip | Needs a Home Assistant session inside Homie's own iframe, renders in a different visual language, and the same nested-iframe idea was already rejected for other chips. |
| Reusing the Lights chip's accordion popup, one row per room | That popup assumes one entity per row with one toggle. A room here has four entities of three domains, so each row would have needed a custom card anyway, with five of six rooms hidden behind a tap. The dashboard's point is all six at once. |
| Keeping the media browser's frame, as the placeholder did | It is 420px wide and built around a list with a back button. Six cards need the width. |
| Source as a row of six buttons per room | Thirty-six buttons on one panel. A picker is one control per room and takes its options from the entity. |
| Showing "Muted" in place of the volume while muted | The volume entity reports 0 while muted. The panel shows what the entity says and lights the mute button. |
| Optimistic state on tap | See above. |

## Verified live, 2026-10-02

Driven with `playwright-cli` at 1280x800 against the deployed file, on the real zones:

- Refresh read all six rooms; the line went from "Not all rooms have been read yet." to "Read just
  now."
- Studio power on came up on AirPlay at 90%, and the chip lit. Power off cleared the card.
- Studio volume set to 80 from the slider; Home Assistant reported 80.1.
- Studio mute on and off.
- Studio source to Tuner 1; `processor_source_name` agreed and the volume held at 80.
- All Off returned every room to off. The freshness line went back to "Not all rooms have been read
  yet." until the next Refresh, which is the integration invalidating its cache after `d40`.

All AirPlay was not tapped live, because it powers all six rooms. It shares its code path with All
Off and a test covers it.

The fork's suite went from 166 to 173 passing. The busy guard, the mid-drag guard, the
unavailable-mute guard and the closed-panel guard were each checked by mutation.

## Known limits

- While a command runs, the volume can read 0% for a moment before it settles.
- A muted room reads 0% for as long as it is muted.
- The source picker is the browser's native dropdown. It was verified in Chromium; how FireOS
  renders it on the wall tablet had not been looked at when this was written.
- Nothing polls the zones, by the integration's design, so a change made at a wall panel does not
  appear until Refresh is tapped. The freshness line exists to say so.
