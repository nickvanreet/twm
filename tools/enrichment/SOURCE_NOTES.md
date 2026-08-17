# Source and verification notes

- The SV6 numbering and 226-card checklist were cross-checked against the official Pokémon TCG database and Bulbapedia’s Twilight Masquerade set page.
- Base card metadata should remain sourced from the Pokémon TCG API in the app. That includes artist, exact rarity, attacks, abilities, HP, Pokédex numbers, flavor text and image URLs.
- The enrichment text in this pack is original paraphrased copy intended as short, child-friendly story material.
- Core Kitakami material (Ogerpon forms, Bloodmoon Ursaluna, Poltchageist/Sinistcha, the Loyal Three, Carmine, Kieran, Perrin and Festival Grounds) received extra story-specific treatment.
- `alternate_of` links the collector print to its regular SV6 card where the relationship is clear. Gold reprints that do not have a regular SV6 counterpart are left null.

## Secret artwork pass (v1.1)

Cards `sv6-168` through `sv6-226` now include original, child-friendly visual observations. Illustration Rare and Special Illustration Rare notes emphasize scene/storytelling. Ultra Rare and Hyper Rare notes deliberately describe the premium treatment rather than inventing a narrative background. Each art object includes the corresponding high-resolution Pokémon TCG image URL as `image_reference`.
