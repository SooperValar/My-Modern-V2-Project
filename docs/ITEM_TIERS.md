# Item tiers (design, not built yet)

A slight overhaul, starting with **helmets and body armor**. It expands and replaces the
special armors that are in the game now.

## Tiers

| Tier | Name color | What it is |
|---|---|---|
| Common | White | Plain armor, as now (shops, drops) |
| Magic | Blue | One bonus. The current modded armor ("of the Lion", "of the Snake", ...) becomes this tier |
| Rare | Yellow | 2-3 random bonuses (attributes, hitpoints, mana, skills), a generated name |
| Epic | Purple | 3-4 stronger bonuses and one special effect (resistance, regeneration, light, ...) |
| Legendary | Orange | Hand-designed named pieces; the current special armors (Fire and Ice sets, Titanium Armor of Ankh, Helm of Shadows, Grolm Crown, ...) move here and get rebalanced. Drop only |

- **Bonus strength is not tied to the metal.** Harakim and Arch-Harakim wear steel for their whole career, so a Rare steel helm has to be able to be as good as a Rare crystal one. Proposal: every tiered item has an **item level** (from where it dropped, or from the soulstones used on it) that sets how strong its bonuses roll; the metal only sets the armor value and the requirements.
- Tier and bonuses live on the item itself (like today's modded and soulstone items), so no new templates are needed for Magic to Epic.

## How it shows

- The item's **name in the tooltip has the tier color** (must have). The tooltip already sends a color per line; the client gets five new colors.
- **A faint glow around the edge of the item's sprite, in the tier color.**
- Idea for later: a **grave that holds items glows faintly grey or white**, so players can see something is in it, without telling what.

## How players get them

- **Random drops** (main source). Better tiers deeper in the world.
- **Strong monsters** (the ones that drop soulstones) roll better tiers (wanted, details open).
- **Soulstones**:
  - **Reroll: 1 soulstone.** The item's bonuses roll again.
  - **Upgrade: 2 soulstones.** The item goes up one tier (Magic -> Rare -> Epic) and gains a bonus. Legendary can't be reached this way. How exactly is open (see below).
  - Decided against: needing a soulstone to identify or awaken Epic and Legendary items.

## Open questions

- Drop rates: to be decided.
- What the soulstone's rank does. Proposal: it sets the item level of the new roll (so a high-rank stone can make a steel helm strong), capped so a tier can't be pushed past what it's meant to be.
- How the upgrade works with 2 stones: put both in at once (e.g. combine the two first into one "double" stone, or hold one and use it on an item that already has one stone set in it), and whether both stones need a minimum rank for the target tier.
- The bonus pool per tier and its numbers; the Epic special effects.
- The glow: whether Common has none and Magic already glows; where it shows (inventory, shop and grave windows, on the ground).
- No old items or players to convert: there are none in the game yet.
- Later: weapons, the other armor pieces, rings.
