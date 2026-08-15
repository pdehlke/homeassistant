# Climate target display: active hvac_action bound, nearest-bound fallback when idle

Both real thermostats run in `heat_cool` mode reporting a high/low band rather than one setpoint.
The displayed target picks whichever bound `hvac_action` is actively working toward (`cooling` →
high, `heating` → low); when idle — the normal resting state for a comfortable house, not a rare
edge case — it falls back to whichever bound `current_temperature` is nearer to, not the literal
band midpoint. The midpoint fallback was the original design, deliberate and covered by its own
test; it just didn't hold up once idle turned out to be the common case, producing a target (70°)
that matched no real setpoint on either thermostat. See
`docs/homie-dashboard/homie-thermostat-control-fix.md` and
`docs/homie-dashboard/climate-idle-target-fallback.md`.

## Considered Options (idle fallback)

- Always show the cooling bound — rejected, silently wrong once a zone idles on the heating side.
- Show the band as a range instead of one number — rejected as a bigger layout change than the bug
  warranted.
- Remember the last active bound — rejected, needs persisted per-entity state for no better an
  answer than the stateless nearest-bound heuristic already gives.
