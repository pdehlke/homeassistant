# Replacing the Pergola Roof placeholder with a live solar/grid gauge

Established 2026-08-05 on Home Assistant 2026.7.4.

## The problem

The Vision Sample dashboard's Pergola Roof card is a `tile` bound to `cover.pergola_roof`, one
of the demo placeholders built in [vision-sample-demo-entities.md](vision-sample-demo-entities.md)
to fill a gap left by the visionos sample theme. It works, but it is fake: a Template Helper
cover backed by an `input_number`, with no real pergola behind it. Once the rest of the dashboard
had genuine entities in every other slot, this was the one card left showing something invented
for the demo rather than anything about the house. Asked to inventory real, non-demo,
non-`light.*` entities and suggest something to put there instead.

## Inventory and options considered

Excluding `light.*` and the demo placeholders (`vision-sample-demo-entities.md`'s seven), the
instance has real, previously unused-on-any-dashboard candidates including the Sense energy
monitor's per-circuit sensors, a Roborock Q5 Max+ vacuum with a live map image entity
(`image.q5_max_map_0`, distinct from the `vacuum.q5_max` entity already on this dashboard), and
an Electricity Maps grid-cleanliness sensor.

| Option | Verdict |
| :--- | :--- |
| Solar/grid-export gauge, sourced from Sense | Chosen |
| Roborock live map (`image.q5_max_map_0`) | Considered, not used |
| Grid cleanliness (Electricity Maps) | Considered, not used |

The Roborock map and grid-cleanliness sensor are both real and both confirmed unused on every
other dashboard on the instance, so either would have been a defensible, fresh choice. The solar
gauge won on relevance to the dashboard's existing content: the Home view already surfaces
climate and EV charging, and live production/export numbers fit that "what is the house doing
right now" theme more directly than a floor map or a carbon-intensity number would.

## `sense_287516`: an unnamed node that is actually the mains meter

The Sense integration's per-device sensors are named after Sense's own detection IDs unless pde
renamed them in the Sense app, and `sense_287516` never was. Its entity suffixes
(`_production`, `_to_grid`, `_from_grid`, `_net_production`, `_l1_voltage`, `_l2_voltage`) are
not shapes Sense uses for an appliance detection; they are the shape used for the whole-home
mains/solar measurement. Read as high-confidence inference from the entity's own shape, not
confirmed against the Sense app or an electrician's panel diagram.

## What was built

A `vertical-stack` of two native `gauge` cards, replacing the single `tile` card in place, sized
`grid_options: {columns: 6, rows: 4}` to match the EV Charger card's stack elsewhere on the same
view:

```json
{
  "type": "vertical-stack",
  "grid_options": { "columns": 6, "rows": 4 },
  "cards": [
    {
      "type": "gauge",
      "entity": "sensor.sense_287516_production",
      "name": "Solar Production",
      "unit": "W",
      "min": 0,
      "max": 6000,
      "needle": true
    },
    {
      "type": "gauge",
      "entity": "sensor.sense_287516_daily_to_grid",
      "name": "Exported Today",
      "unit": "kWh",
      "min": 0,
      "max": 30,
      "needle": true
    }
  ]
}
```

`min`/`max` on both gauges are round numbers with headroom over observed values (production has
been seen as high as ~4.5 kW, daily export past 22 kWh), not a measured system capacity; nothing
on the instance currently reports the solar array's rated size. Revisit if a day's real numbers
ever pin the needle against either ceiling.

The second gauge reads `sensor.sense_287516_daily_to_grid`, the day's gross energy sent to the
grid, not a net figure. Sense also exposes `sensor.sense_287516_daily_net_production`
(production minus whole-home consumption for the day), which was **not** used here: on the day
this was built it read negative (net importer over the full day) while `daily_to_grid` was a
healthy positive number, because the house pulls from the grid overnight and exports during
sunny hours, and the two sensors net those periods differently. A true "net flow to the grid"
figure would be `daily_to_grid` minus `daily_from_grid`, which does not exist as its own sensor
and would need a new template sensor to build. Out of scope for a dashboard-only change; the
label reads "Exported Today" rather than "Net Export" so the card does not claim more precision
than the underlying sensor has.

No custom radial-gauge card is installed on this instance (checked `lovelace/resources`); the
native `gauge` card already renders as a radial arc with an optional needle, so nothing new
needed installing.

## Left open

`cover.pergola_roof` and its backing `input_number.pergola_roof_position` helper still exist;
only the dashboard card was swapped, not the entity or its helper. Nothing else on the instance
references either. Left in place rather than deleted, same call as leaving
`water_heater.demo_water_heater` unbuilt in vision-sample-demo-entities.md: a decision for pde,
not something to make unilaterally while touching an unrelated card.

## Verified live

Read back `lovelace/config` for `vision-sample` and confirmed the saved card matches the JSON
above exactly. Screenshotted the live dashboard: both gauges render as radial arcs with a
needle, live wattage and kWh values, and correctly sized labels after shortening the second
gauge's name once "Exported to Grid Today" was confirmed truncating in the rendered card.
