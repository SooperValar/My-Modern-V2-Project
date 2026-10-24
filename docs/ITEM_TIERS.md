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

## Open questions (suggested answer in brackets)

Stones
1. Reroll: does the stone have to be exactly the item's level? [yes, exactly]
2. Container: how close must the two stones be, and what level is the upgrade stone? [same level; the upgrade stone has that level]
3. Reroll: keeps the tier and the number of bonuses, only rolls which bonuses and how strong? [yes] Can Magic items be rerolled? [yes] Legendary? [no]
4. Rare -> Epic: the upgrade adds a bonus; does it also add the Epic special effect? [yes]
5. Highest item level: stones stop a little above 20. [item levels 1-20]

Bonuses
6. The bonus pool: the same for helmets and body armor, or different? [different leanings: helmets mind (Intuition, Willpower, mana, spell skills), body armor body (Strength, Agility, hitpoints, armor)]
7. How strong a bonus is per item level and per tier (the formula). [I draft numbers to look at]
8. The Epic special effects. [short list to pick from: resistance, regeneration, mana regeneration, light, ...]
9. Rare names: generated names ("Stormcrest Helm") or the base name with a suffix ("Steel Helmet of the Wolf")? [suffix names, easier to read]

Drops
10. Drop rates. [to be decided]
11. Which monsters drop tiered armor and how the item level is set. [any monster can; item level from the monster's rank, Strong monsters roll a better tier]
12. Shops sell only Common. [yes]
13. The Legendary list and their new numbers. [go through the current special armors one by one]

Item level and requirements
14. The rank requirement is added to the metal's normal requirements (Strength, Agility). [yes, both apply]

Wear and repair
15. Can tiered items be repaired and do they wear out? Soulstone items today can't be repaired. [they wear and can be repaired like normal armor]

How it shows
16. The glow: none on Common; from Magic up? [yes] Where: backpack, worn slots, shop and grave windows, on the ground? [all of them]
17. Tooltip shows the tier, item level and required rank. [yes]

Container
18. Name, where to get it, how many uses, price. [a cheap single-use one in shops, pricier multi-use ones as a gold sink]

Later
- Weapons, the other armor pieces, rings.
- Upgrade stones on each other: suggestion, they don't combine.

Decided
- Stone on stone stays: using a soulstone on another merges them into a higher-level stone, as now.
- No old items or players to convert: there are none in the game yet.

## How soulstones work now (for reference)

- A "Strong" monster (randomly boosted when it spawns) carries a soulstone holding 10-15% of that monster's experience. The stone's **level is the character rank that this much experience would give** (same scale as ranks; "That's as high as they go" above 20). So it comes from the monster, not from the player who finds it.
- Stone on stone: the first stone gains a random part (0-100%) of the second one's experience, the second is used up.
- Stone on equipment: random bonuses with a total strength of the stone's level, and the item then needs that rank to wear (`soultrans_equipment`).
- Suggestion: keep this rank scale for the tiers too. Item level, soulstone level and the rank needed to wear the item are then the same number, which is easy to understand ("a level 12 helm needs rank 12 and a level 12 stone").
