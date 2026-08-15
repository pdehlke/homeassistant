# Daily solar stats skip a gap hour rather than blanking the whole badge

"% Green Today" and "CO2 Intensity Today" treat each recorder hourly bucket as valid only if every
input it needs is present, skip any hour missing a required input, and continue the running total
from the hours that did report — rather than showing `—` for the whole day if any single hour has
a gap, the strict convention every other stat on this card uses for missing live data. Accepted
trade-off: the grid's fossil%/CO2 sensors blip unavailable for a minute or two on most refresh
cycles, so a strict policy would blank the badge on most days even though HA's hourly long-term
statistics have so far always back-filled successfully around those blips. See
`docs/homie-dashboard/overview-c-solar-today-totals.md`.
