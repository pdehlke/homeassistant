# Music stations addressed uniformly via library://radio/&lt;n&gt;

Two of the six stations (1st Wave, BB King's Bluesville) resolve to both a Music Assistant
`library://radio/<n>` favorite-list URI and a native `siriusxm://` URI. All six are addressed via
`library://` for consistency — one addressing scheme for every entry, matched against the same
field `musicStationIsOn()` reads — accepting the documented risk that a library favorite's id
isn't content-stable (unfavoriting either station in Music Assistant would need a re-resolve via
`music_assistant.search`), rather than having two of six entries address their station differently
from the other four. See `docs/homie-dashboard/homie-music-chip.md`.
