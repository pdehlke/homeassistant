# Solar green-% stats read home consumption from its own existing sensor, never reconstructed

Both the instantaneous "Low Carbon" stat and its daily "% Green Today"/"CO2 Intensity Today"
companions divide by home energy consumption read directly from the existing consumption
sensor(s) already bound to this card's own "Live Usage"/"Today's Usage" stats, rather than
reconstructed as `solar + gridImport` from the same inputs already in the formula.
Self-consistency with an already-displayed figure was chosen over immunity to a (so far
unobserved) metering mismatch between independently metered sensors, so this stat can never
quietly diverge from the number sitting right next to it. See
[docs/homie-dashboard/overview-c-solar-home-green-percentage.md](../homie-dashboard/overview-c-solar-home-green-percentage.md) and
[docs/homie-dashboard/overview-c-solar-today-totals.md](../homie-dashboard/overview-c-solar-today-totals.md).
