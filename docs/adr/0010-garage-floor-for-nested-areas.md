# Model the Garage as a Floor holding two Areas

Home Assistant's area registry has no parent-area field, so "the Garage Mechanical Closet is part
of the Garage" can't be expressed by nesting one area inside another. A Floor named Garage holding
both the Garage and Garage Mechanical Closet areas was chosen over two flat sibling areas (nothing
enforces or displays the relationship) or a shared label (cross-cutting, but produces no visual
hierarchy on a dashboard), since Floor-to-Area is the only containment the data model actually
offers. See [docs/areas-and-entities/area-floor-layout.md](../areas-and-entities/area-floor-layout.md).
