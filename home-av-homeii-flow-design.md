# HOME A/V tab with HOMEii Flow

## Goal

Make the empty A/V tab on the Home kiosk dashboard a usable Music Assistant interface without
changing any other Home tab or creating an area-and-leaf navigation hierarchy around it.

## Design

Change only the existing view whose path is `a-v` on the `vision-sample` dashboard. Convert that
view from an empty Sections view to a Panel view containing one `custom:homeii-music-flow` card.
Panel mode is required because HOMEii Flow declares a 12-column maximum that prevents it from
occupying the full width of a wider Sections layout.

Use the existing `input_text.homeii_flow_active_player` helper and give this instance a distinct
card ID. Leave HOMEii's language, theme, and phone layout selection on automatic settings. Do not
configure direct Music Assistant credentials: normal player selection, playback, search, library,
and queue operations work through Home Assistant, while the direct connection is only needed for
Sendspin browser playback and direct artwork access.

## Safety and verification

Read and back up the complete live dashboard before saving because Lovelace writes replace the
whole configuration. Refuse the change unless exactly one view has path `a-v`, preserve every
other view unchanged, then read the saved configuration back. Finally, render `/vision-sample/a-v`
at the tablet target of 1280 by 800 pixels and confirm the card loads full-width without an error
placeholder or horizontal overflow.
