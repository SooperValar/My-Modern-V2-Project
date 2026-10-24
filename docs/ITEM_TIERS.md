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

- **Bonus strength is not tied to the metal.** Harakim and Arch-Harakim wear steel for their whole career, so a Rare steel helm has to be able to be as good as a Rare crystal one. Every tiered item has an **item level** (from where it dropped, or from the soulstones used on it) that sets how strong its bonuses roll; the metal only sets the armor value and its normal requirements.
- **Rank requirement** from the item level, so a strong steel item can't be handed to a low-ranked character (like soulstone items need the stone's rank now).
- Tiers overlap: a high-level Magic item may beat a low-level Epic one when the level gap is wide enough.
- Tier and bonuses live on the item itself (like today's modded and soulstone items), so no new templates are needed for Magic to Epic.

## How it shows

- The item's **name in the tooltip has the tier color** (must have). The tooltip already sends a color per line; the client gets five new colors.
- **A faint glow around the edge of the item's sprite, in the tier color.**
- Idea for later: a **grave that holds items glows faintly grey or white**, so players can see something is in it, without telling what.

## How players get them

- **Random drops** (main source). Better tiers deeper in the world.
- **Strong monsters** (the ones that drop soulstones) roll better tiers (wanted, details open).
- **Soulstones**:
  - The stone's level has to match the item's level, much like now.
  - **Reroll: a soulstone.** The item's bonuses roll again.
  - **Level rule: an upgrade needs a stone one level above the item** (a level 13 upgrade stone for a level 12 item, and so on). A reroll uses a stone of the item's own level. **The upgrade does not change the item's level or its rank requirement**: a level 12 item stays wearable at rank 12. The higher stone is just the price of the upgrade.
  - **Upgrade: an upgrade stone.** Two soulstones of a similar level go into a **container** (new item, gets its own generated sprite) and come out as one upgrade stone, the way flowers go into a flask to make a potion. Using it on an item raises it one tier (Magic -> Rare -> Epic) and adds a bonus. Legendary can't be reached this way.
  - Decided against: needing a soulstone to identify or awaken Epic and Legendary items.

## Open questions

- Drop rates: to be decided.
- How close "matching" and "similar level" are (same rank, within 1-2 ranks, ...), and whether a higher stone can raise an item's level when used on it.
- The container: its name and how players get it. Idea: as a gold sink, multi-use containers sold for more money. Sprite prompt to be written.
- Stone on stone stays: using a soulstone on another merges them into a higher-level stone, as now.
- Upgrade stones on each other: undecided. Suggestion: they don't combine (only plain soulstones merge), so there is one clear way to each kind of stone.

## How soulstones work now (for reference)

- A "Strong" monster (randomly boosted when it spawns) carries a soulstone holding 10-15% of that monster's experience. The stone's **level is the character rank that this much experience would give** (same scale as ranks; "That's as high as they go" above 20). So it comes from the monster, not from the player who finds it.
- Stone on stone: the first stone gains a random part (0-100%) of the second one's experience, the second is used up.
- Stone on equipment: random bonuses with a total strength of the stone's level, and the item then needs that rank to wear (`soultrans_equipment`).
- Suggestion: keep this rank scale for the tiers too. Item level, soulstone level and the rank needed to wear the item are then the same number, which is easy to understand ("a level 12 helm needs rank 12 and a level 12 stone").
- The bonus pool per tier and its numbers; the Epic special effects.
- The glow: whether Common has none and Magic already glows; where it shows (inventory, shop and grave windows, on the ground).
- No old items or players to convert: there are none in the game yet.
- Later: weapons, the other armor pieces, rings.
