# Genre browse misclassification

Diagnosed and fixed live 2026-08-18, against Music Assistant server 2.9.13. Symptom: browsing
"Genres" in the Music Assistant web UI put Front 242, Fields Of The Nephilim, Patti Smith, The
English Beat, Bauhaus, Peter Murphy, Stan Ridgway, Talking Heads, The Psychedelic Furs, Tones On
Tail, The Jam, and both Elvis Costello library entries under **Classical** and **Experimental**,
alongside the one artist who actually belongs there, Philip Glass.

## Root cause

Not a content-based classifier. Each track's own genre tag was correct the whole time (verified
per-track via `music/get_library_item`): the affected artists' files all carry the plain,
unqualified ID3 genre string `Alternative`, which is 198 of this library's 432 tracks (46%),
almost certainly because they were tagged years ago against the old ID3v1/Winamp extended genre
list rather than a modern granular scheme.

Music Assistant's Genres browse page doesn't group by the raw tag directly. It rolls every raw
genre string up to one of a small set of canonical genres via a bundled alias table, queryable
per genre as `genre_aliases` on the `music/get_library_item` (`media_type: genre`) response. On
this instance, the `classical` canonical genre's alias list (181 entries) and the `experimental`
canonical genre's alias list (23 entries) both incorrectly included the bare string
`Alternative`, sitting next to genuinely classical/experimental terms like "Chamber Music" and
"Musique Concrète". Meanwhile `rock`'s alias list (140+ entries) and `punk`'s both correctly
carry qualified forms — "Alternative Rock", "Alternative Dance", "Alternative Punk", "Indie &
Alternative" — but never the bare word, which is exactly the string this library's files use. So
every artist tagged with the plain word got vacuumed into Classical and Experimental instead.

This is a known bug class upstream, not something specific to this library or its tagging.
[music-assistant/support#5840](https://github.com/music-assistant/support/issues/5840) documents
the identical defect for `metal`, whose alias list wrongly contained bare "Rock": 84% of that
reporter's "Metal" genre page turned out to be non-metal Rock content, for the same reason.

## Ruled out before finding the real cause

- **Homie Dashboard's own code.** Grepped the whole fork for `genre`; zero hits. Not implicated.
- **Per-track/per-album genre data being wrong.** It isn't. `music/get_library_item` on every
  affected track returns the correct, specific tag (`Alternative`, `Punk`, `Classical`, `Jazz`,
  `New Age`, `Electronica`, `Indie Rock`, `Rock` — an 8-value distribution across the library,
  internally consistent per artist).
- **MA server-side browse tree having a genre node.** It doesn't; `music/browse` against
  `library://genres`, `library://genre`, etc. all fall back to the root folder. Genre browsing is
  a frontend-only feature layered on the alias table described above.
- **Sonos or another consumer misreading a raw ID3v1 genre byte.** Moot: MA stores genre as
  already-decoded plain-text strings per track, not raw byte codes, so there's no byte-table
  mismatch to have.

## The fix: Promote Alias

Music Assistant ships a real per-genre alias manager, documented at
[music-assistant.io/genres](https://www.music-assistant.io/genres/), with four actions: Add
Alias, Link Alias, Promote Alias, Remove Alias. **Promote Alias converts a shared/incorrect alias
into its own standalone canonical genre**, and removes it from every genre that previously
claimed it as an alias. On this instance the UI surfaces it as a collapsed "Mapped Aliases (N)"
panel on a genre's detail page; it doesn't render by default the way the primary Play/Favorite/
Library/Delete action bar does, which is why it wasn't found on the first pass through the UI.

Promoting `Alternative` out of `classical` and `experimental` and into its own genre fixed this
completely. Verified live, before and after:

| Genre page | Before | After |
|---|---|---|
| Classical | 13 artists (12 wrongly "Alternative"-tagged + Philip Glass) | Philip Glass only |
| Experimental | Same 13 artists | Empty; alias manager now shows 21 mapped aliases, `Alternative` no longer among them |
| Alternative (new, `library://genre/66`) | Didn't exist | The 13 previously-misplaced artists |

Server-side: `classical`'s `genre_aliases` count dropped from 181 to 180, `experimental`'s from
23 to 22, both losing exactly the bare string `Alternative`, and a new canonical genre entity
(`library://genre/66`, name `Alternative`) appeared.

Cross-genre promotion edge cases (an alias shared by two genres, or albums/artists not following
their tracks after a promotion) were themselves a bug until
[music-assistant/server#3923](https://github.com/music-assistant/server/pull/3923), "Fix genre
movements when genres are promoted or deleted," merged 2026-05-22. Server 2.9.13 postdates that
fix, and the before/after table above shows both classical and experimental correctly stripped in
one promotion, so this instance has it.

## What wasn't verified

A relayed claim (from another LLM the user consulted, not verified independently) also warned
against running Music Assistant's "Scan Now" before promoting ("will reproduce the bad mapping")
and against "Full Restore" ("reinstalls the defective defaults"). Both are plausible — a rescan
or restore could plausibly re-seed the bundled alias table — but neither was tested here. Treat
as unconfirmed if it comes up again; don't repeat it as established fact without checking.

## Workaround, superseded

Before the real fix was applied, a static Music Assistant playlist named "Alternative (genuine)"
(`library://playlist/9`) was built directly via the API — `music/playlists/create_playlist` then
`music/playlists/add_playlist_tracks` — containing the 198 tracks whose raw tag is `Alternative`,
since `music/tracks/library_items` has no genre filter to query against directly. It's redundant
now that the native Alternative genre page does the same job and stays live as the library
changes, but it's harmless to leave in place or delete.
