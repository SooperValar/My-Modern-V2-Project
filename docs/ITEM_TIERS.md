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

- Bonuses scale with the armor's metal, so the metal tiers keep mattering.
- Tier and bonuses live on the item itself (like today's modded and soulstone items), so no new templates are needed for Magic to Epic.

## How it shows

- The item's **name in the tooltip has the tier color** (must have). The tooltip already sends a color per line; the client gets five new colors.
- **A glow** on items of the higher tiers (wanted, to some extent; how strong and from which tier is open).

## How players get them

- **Random drops** (main source). Better tiers deeper in the world.
- **Strong monsters** (the ones that drop soulstones) roll better tiers (wanted, details open).
- **Soulstones**:
  - **Upgrade**: using a soulstone on a Magic or Rare item raises it one tier (Magic -> Rare -> Epic) and adds a bonus. Higher tiers need a higher stone rank. Legendary can't be reached this way.
  - **Reroll**: using a soulstone on a Rare or Epic item rolls its bonuses again; the stone's rank sets how strong the new roll can be.
  - Decided against: needing a soulstone to identify or awaken Epic and Legendary items.

## Open questions

- Drop rates per tier, and what "deeper in the world" means (by area, by monster rank, ...).
- The bonus pool per tier and its numbers; the Epic special effects.
- How upgrade and reroll pick between them when a stone is used on an item (two kinds of stone, or upgrade first and reroll once at the top, ...).
- What happens to soulstone-enhanced items that already exist (count as Rare or Epic by their number of bonuses?).
- The glow: from which tier, and how it looks (in the world, on the character, in the inventory).
- Later: weapons, the other armor pieces, rings.
