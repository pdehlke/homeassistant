# Project TODO

A live, ordered backlog for ongoing Home Assistant and Homie Dashboard work. Unlike most files in
this archive, this one is meant to be mutated in place rather than treated as a historical record:
items get reordered, completed, or added as work happens. When an item is finished, it moves out
of this list; the reasoning behind how it was done belongs in a dedicated document of its own (and
this file links to it once one exists).

New items go at the bottom unless told otherwise. Ask before reordering or removing an item for
any reason other than completing it.

1. Fix Overview C calendar entries
2. Overview A irrigation indicator
3. Tesla inverter integration
4. More complete Energy panel
5. Investigate empty weather card
6. Fix Overview C floors card's uneven spacing (`.ov3-col3`'s `justify-content: space-between`
   stretches an oversized gap between the security and floors cards when no purifier entity is
   configured; cosmetic, found while fixing Overview C's vertical overflow, see
   `homie-dashboard-install-plan.md`)
