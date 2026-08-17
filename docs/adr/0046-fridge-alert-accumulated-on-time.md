# Fridge failure alert: accumulated on-time, not a continuous-off state trigger

The original automation triggered on `binary_sensor.fridge_power` reading `off` continuously for
three hours, which measured almost useless in practice: Sense's fridge-power sensor drops out
`unavailable` roughly every two hours, and a `for:` duration on a state trigger restarts its clock
on any transition, including through `unavailable`. With only 3 of 11 observed gaps between
dropouts exceeding three hours, a genuine failure would most likely be interrupted before the timer
matured — an estimated 3 times out of 4. Replaced with a `history_stats` helper accumulating hours
`on` over a rolling three-hour window, which a one-minute dropout doesn't reset, thresholded at 0.05
hours (roughly 30x below a healthy fridge's measured 1.63h per window). See
[docs/device-alerts/fridge-failure-alert.md](../device-alerts/fridge-failure-alert.md).
