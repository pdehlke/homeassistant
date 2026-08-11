# Overview C Solar: home green percentage

The full-screen Solar view's "Low Carbon" stat used to show the Tucson Electric Power grid's own
green share. It now shows the green share of the home's own consumption, which is a different and
more useful number once solar production is in the mix. See
[homie-dashboard-install-plan.md](homie-dashboard-install-plan.md) for the fork location and
deployment workflow this change went through.

## The problem

Before this change, `sfs-stat-low-carbon` read `100 - fossil_fuel_percentage` straight from the
Electricity Maps sensor (`sensor.electricity_maps_grid_fossil_fuel_percentage`). That is an honest
number, but it describes the grid, not the house. On a day with meaningful solar production, the
home draws a shrinking share of its power from that grid, so the grid's own mix increasingly
understates how green the home's actual consumption is. At the extreme, running entirely on solar
with zero grid import, the old number would still report whatever TEP's mix happened to be that
hour, even though none of that grid mix was powering the house at all.

## The formula

Agreed with pde over a grilling session before writing any code:

- **Exporting or neutral** (`gridKw <= 0.01`, the same neutral threshold `gridDirection` already
  used): the home's consumption is fully covered by solar, so the result is **100%** regardless of
  the grid's own mix that hour.
- **Importing** (`gridKw > 0.01`): the result blends two sources by their share of home
  consumption. Solar counts as 100% green. Imported grid power counts at the grid's own green
  fraction (`100 - fossil_fuel_percentage`).

  ```
  greenKw = solarKw + gridImportKw * (gridGreenPercent / 100)
  homeGreenPercent = clamp(greenKw / homeKw * 100, 0, 100)
  ```

  `homeKw` is read directly from the live-consumption sensor (`sensor.sense_287516_energy`), the
  same value already bound to the "Live Usage" stat, rather than derived as `solarKw + gridKw`.
  The two are usually close but not identical, since they come from independently metered
  sensors (Sense's whole-home node versus the separate grid-flow sensor); using the
  already-displayed consumption figure keeps this stat consistent with what "Live Usage" shows
  next to it, and matches "percentage of the home's energy consumption" literally.

- **Missing data**: if solar, grid, home consumption, or (while importing) the grid's green
  fraction is null or unavailable, or home consumption is zero, the result is `—`, matching every
  other stat on this card.
- **Clamped to [0, 100]**: solar and grid flow come from independent sensors that can drift out of
  step for a moment (solar reads high right as the grid sensor is still catching up to a state
  that would otherwise call it "importing"), so the blend is clamped rather than allowed to read
  above 100% or below 0%.

Implemented as a pure function, `homeGreenPercentage(solarKw, gridKw, homeKw, gridGreenPercent)`,
in `dist/homie-custom.js`, and wired into `solarFullscreenView`'s `lowCarbon` field, the same field
that already fed `sfs-stat-low-carbon`. The label text stays "Low Carbon": it already reads as a
property of current consumption rather than an explicit claim about the grid, so nothing about the
visible card needed to change, only the number behind it.

## Options considered and rejected

- **Derive home consumption as `solarKw + gridImportKw` instead of reading the live-consumption
  sensor.** Self-consistent with the other two sensors already in the formula, and immune to any
  metering mismatch between them. Rejected because "the home's energy consumption" is a value this
  card already shows independently (the "Live Usage" stat), and reusing that sensor keeps this new
  stat honestly describing the same consumption figure sitting right next to it, rather than a
  reconstructed one that could quietly diverge from what "Live Usage" says.
- **Rename the "Low Carbon" label** to something that flags the change, such as "Home Green %".
  Rejected: the existing label does not name the grid explicitly, so it does not overclaim, and
  leaving it unchanged avoids unrelated layout or test churn for a purely cosmetic call.
- **Fall back to the raw grid percentage when solar/grid data is missing but the grid mix isn't.**
  Rejected in favor of the same `—` convention every other stat on this card already uses for
  missing inputs. A silent fallback to a different, unlabeled quantity would be harder to notice
  than a dash.

## Verification

- `node --test test/screen-a.test.cjs`: added a dedicated test for `homeGreenPercentage` covering
  export, neutral, pure-grid-import, blended import, clamping, and each missing-data path; updated
  the existing full-screen view model test (the old expectation was the raw grid figure while
  exporting, now correctly 100%); added a new blended-import integration test. Full suite 56/56.
- Deployed live and confirmed `homie-custom.js` byte-for-byte identical between the fork's working
  tree, the live filesystem over SFTP, and an HTTP fetch with a cache-busting query string.
- Exercised the deployed `HOMIE_CUSTOM.solarFullscreenView` directly in a live browser session
  against the instance's actual readings at the time (559 W home, 313 W solar, 0.2 kW import,
  86.05% grid fossil fraction): **61.0%** home-green, versus the 13.95% the old raw-grid figure
  would have shown for the same moment. The live stat itself read `—` during this check because
  Electricity Maps' fossil-percentage sensor was genuinely `unavailable` at that moment, confirmed
  independently over REST; that is the missing-data path working as designed, not a regression.

## A deployment gap this change caught

`homie-custom.js` was deployed and hash-verified first, without bumping the cache-busting
`HOMIE_ASSET_VERSION` token in `homie-dashboard.html`. That token is what makes a browser refetch
`homie-custom.js` instead of running a cached copy; leaving it unchanged means any device that had
already loaded the dashboard, such as an always-on kiosk tablet, would keep running the old
comparison logic indefinitely despite the new file sitting correctly on disk. This is the same
trap `homie-thermostat-control-fix.md` documents under "Two mistakes caught by testing against the
real thing." Caught before calling this done, not after: bumped `HOMIE_ASSET_VERSION` from
`20260808.15` to `20260809.1` in `homie-dashboard.html`, and separately bumped the matching
`?v=` query string on the `homie-dash` Lovelace iframe strategy's URL (a second, outer
cache-busting layer for `homie-dashboard.html` itself), since that file's own bytes changed too.
Both were backed up before deploying and verified live: the served HTML declares the new version
string, and `homie-custom.js` fetched under the new query string hashes identically to the fork's
working tree.
