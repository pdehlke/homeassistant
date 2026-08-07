# Music Assistant dashboard examples

HOMEii Flow is excluded because its look and feel was not a good fit.

## Candidates

1. [Music Assistant Player Card](https://github.com/droans/mass-player-card)

   A substantial Material-style interface with now-playing, queues, favorites,
   library browsing, player switching, grouping, and queue transfer. The
   [community thread](https://community.home-assistant.io/t/music-assistant-player-card-control-your-players-adjust-transfer-and-join-queues-and-browse-your-media/929266)
   has a large screenshot.

2. [Yet Another Media Player, YAMP](https://github.com/jianyu-li/yet-another-media-player)

   Artwork-driven theming, multi-player chips, grouping, Music Assistant search,
   queue management, lyrics, and dedicated full-page search and speaker-grouping
   modes.

3. [Mediocre Media Player Cards](https://github.com/antontanderup/mediocre-hass-media-player-cards)

   Despite the name, this is polished and wall-panel-oriented. It provides both
   regular cards and a full-screen panel card with artwork colors, search, media
   browsing, queues, grouping, and large touch controls. See the
   [community showcase](https://community.home-assistant.io/t/media-player-card-with-grouping-support-and-custom-buttons/868819).

4. [Maxi Media Player](https://github.com/punxaphil/maxi-media-player)

   Clean and configurable. Player, favorites, search, queue, volume, and
   grouping can be shown together or split into separate cards. That flexibility
   may suit Home's existing Sections layout particularly well.

5. [Music Assistant Cover Wall](https://github.com/eliseo-juan/mass-coverwall-card)

   A clean grid of playlist, album, or artist artwork with one-tap playback. It
   would need to be paired with a player card, but it could make an attractive
   content browser. See the
   [Reddit showcase](https://www.reddit.com/r/homeassistant/comments/1s9zomf/i_built_a_music_assistant_cover_wall_card_for/).

6. [Music Assistant Lovelace UI](https://github.com/rxritalin/Music-Assistant-Lovelace-UI)

   A handcrafted full-screen music dashboard rather than a packaged card.
   Visually ambitious, but designed around an unusual 1920 by 720 display and
   described by its author as rough. Best treated as layout inspiration. See the
   [original showcase](https://www.reddit.com/r/homeassistant/comments/1dz5vip/fullscreen_lovelace_music_card/).

7. [Homie Dashboard](https://github.com/Big-Edge2297/homie-dashboard)

   A complete touch-first wall-tablet dashboard with Music Assistant browsing.
   Its overall visual language differs from Home, but its horizontal tablet
   layout and media interactions are useful references.

Music Assistant also maintains an
[official community extensions gallery](https://www.music-assistant.io/community-extensions/)
with screenshots and links to Music Assistant dashboards and cards.

## Revised shortlist for Home

1. Maxi Media Player
2. YAMP
3. Mediocre Media Player
4. Music Assistant Player Card
5. YAMP or Maxi paired with Cover Wall

Important grouping caveat: Music Assistant can dynamically group compatible
players, and Mediocre exposes that control. Different player protocols may not
synchronize or may reject joining. A permanent Universal Group could send the
same audio to dissimilar players, but Music Assistant warns that those players
may not be synchronized. I recommend first exposing temporary grouping in
Mediocre and testing which combinations work before creating a permanent “Whole
House” group.
