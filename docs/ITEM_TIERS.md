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

## Answers so far (numbers are the questions as first asked)

Stones
1. A reroll stone must be exactly the item's level. **Decided.**
2. Container: two stones of the same level make an upgrade stone of that level; or, if the two differ, the result has the lower level, with a warning before combining. **Decided (either; leaning to allow different levels with the warning).**
3. A reroll keeps the tier and the number of bonuses; Magic items can be rerolled, Legendary can't. **Decided.**
4. Rare -> Epic also adds the Epic special effect. **Decided.**
5. Item levels 1-20. **Decided.**

Bonuses
6. Separate bonus pools for helmets and body armor are wanted, but they should not lean toward classes (helmet = caster, body = fighter). **Come back to.**
7. Bonus strength per level and tier. **Come back to, needs its own focused session.**
8. Epic special effects: ideas listed below. **To pick from.**
9. Names: Magic gets a suffix, Rare a prefix and a suffix, and the name must come from the bonuses the item really has (without limiting which bonuses can roll). Idea: after rolling, the strongest bonus names the suffix ("of the Bear" = Strength) and the second one the prefix; a third bonus is unnamed. **Decided in principle.**

Drops
10. Start by looking at how often Strong monsters appear. **Next.** (Found: only pentagram-quest enemies can become Strong, 1 in 25.)
11. Any monster can drop tiered armor, item level from the monster's rank, Strong monsters roll a better tier. **Decided.** (Found: every Strong monster carries a soulstone.)
12. Shops sell only Common. **Decided.** Maybe later Damor's shop sells some random Magic gear.
13. Legendary items: **longer conversation later.** Idea: each one changes an aspect of a skill.

Requirements and wear
14. Both the rank requirement and the metal's normal requirements apply. **Decided.**
15. Wear: leaning toward **no wear** (nothing to repair). Today's modded armor already takes no damage from fighting (max_damage 0); it still has the normal age limit.

How it shows
16. No glow on Common; Magic and up glow, everywhere items show. **Decided.**
17. The tooltip shows tier, item level and required rank. **Decided.**

Container
18. From chests and/or bought from Damor; price open. Multi-use containers held back for now.

## Bonus framework (built on the soulstone system)

The soulstone's way of rolling is kept and changed: the item level is a budget of points that is spent on bonuses (attributes and skills).

- **No extra requirements.** Bonuses never raise an item's requirements. An item only needs its metal's normal requirements and the rank of its item level.
- **Every item with bonuses gets a category** when it is made. The category decides which bonuses can roll; the tier decides how many. Odds when an item is made: **Fighter 30%, Mercenary 30%, Mage 30%, Utility 10%.** A reroll keeps the category.

| Category | Main attribute | Small extra | Skills that can roll |
|---|---|---|---|
| Fighter | Strength or Agility | Braveness | Hand to Hand, Dagger, Sword, Two-Handed, Two-Handed Axe, Surround Hit, Warcry, Resistance, Immunity, Regenerate, Rest |
| Mage | Intuition or Willpower | Braveness | Bless, Enhance Weapon, Protection, Magic Shield, Heal, Blast, Curse, Stun, Ghost Companion, Dispel Magic, Dagger, Resistance, Concentrate, Meditate |
| Mercenary | Any of the four, or a spread over all four | Braveness | Any from the Fighter and Mage lists, and Stealth |
| Utility | none (skills only) | none | Perception, Lock-Picking, Bartering, Repair, Light, Identify, Sense Magic, Swimming |

- **Braveness as the main attribute**: in Fighter, Mage and Mercenary there is a small chance (**10%**) that Braveness becomes the main attribute and the category's usual main attribute the secondary one (e.g. a Fighter item with Braveness first, Strength second). Named by the main one: "Brave Steel Fighter Armor of ...".
- Left out for now, because they have no real use in the game yet: Karate, Staff, Axe, and Recall.

### Hitpoints, endurance and mana (flat, outside the budget)

Every item with bonuses also gets hitpoints, endurance and mana by its category, tier and item level. They don't use budget points. **Even steps: Magic 1x, Rare 2x, Epic 3x, Legendary 5x, on a halved base** (a helmet and body armor stack, so each piece gives half). The value per level can be a fraction; the item gets level x value, rounded down.

| Per item level (hp/end/mana) | Magic | Rare | Epic | Legendary |
|---|---|---|---|---|
| Fighter | 1.5/1/0.5 | 3/2/1 | 4.5/3/1.5 | 7.5/5/2.5 |
| Mage | 0.5/1/1.5 | 1/2/3 | 1.5/3/4.5 | 2.5/5/7.5 |
| Mercenary | 1/1/1 | 2/2/2 | 3/3/3 | 5/5/5 |
| Utility (half of Mercenary) | 0.5/0.5/0.5 | 1/1/1 | 1.5/1.5/1.5 | 2.5/2.5/2.5 |

Example: a level 20 Legendary Fighter piece gives +150 hitpoints, +100 endurance, +50 mana; a helmet and body armor together +300/+200/+100. To check against real characters' hitpoints and mana per rank when we do the numbers (question 7).

### Utility items

No attributes, only skills: their whole budget goes into the utility skills, so those roll higher. They still get the small hitpoints/endurance/mana above.

### Names

**The attribute gives the prefix, the skill gives the suffix**, with the metal and the category in between:

- Rare and up: **"Strong Steel Fighter Armor of Resistance"** (Strength, Fighter, Resistance). The strongest attribute bonus and the strongest skill bonus name the item; further bonuses are unnamed.
- Magic (one bonus): only the prefix or only the suffix, e.g. "Strong Steel Fighter Armor" or "Steel Mage Helmet of Bless".
- Utility (no attributes): the suffix only, e.g. **"Steel Utility Armor of Mending"** (Repair).

Word list (liked; prefix words decided):

| Attribute | Prefix |
|---|---|
| Strength | Strong |
| Agility | Nimble |
| Intuition | Wise |
| Willpower | Willful |
| Braveness | Brave |
| A spread over all four (Mercenary) | Balanced |

The Balanced category is called **Mercenary** (alternative: Adventurer), e.g. **"Strong Steel Mercenary Armor of Stealth"**; with the spread over all four attributes: "Balanced Steel Mercenary Armor of Stealth".

**The metal always stays in the name.** Order: prefix, metal, category, piece, suffix.

**Name length (decided: option 1).** An item's stored name holds at most 39 characters (`char name[40]`), and full names can be longer ("Balanced Crystal Mercenary Helmet of Ghost Companion" is 52). So:
- The server **builds the full name from the item's tier data wherever players see it** (tooltip, look text, shop and grave windows, messages). No change to the data files.
- The **stored name is a short form** for the background (logs, god tools): short words such as "Resist" for Resistance, "Companion" for Ghost Companion, "Merc" for Mercenary, "Helm" for Helmet, e.g. "Strong Steel Merc Armor of Resist".

Skill suffixes: mostly the skill's own name ("of Resistance", "of Bless", "of Stealth"), with a nicer word where the name reads badly (Repair -> "of Mending", Lock-Picking -> "of Picking", Two-Handed Axe -> "of Cleaving", Surround Hit -> "of Sweeping", ...). To go through together.

## Decisions, round 3

- **Bonuses per tier (draft, see `docs/ITEM_SAMPLES.md`)**: Magic 1 bonus (the main attribute or one skill); Rare main attribute + 1-2 skills; Epic main attribute + a secondary + **3 skills**; Utility skills only (1 / 2-3 / 4). The main attribute takes about half the budget; **every other bonus gets at least 20% of the rest**, so no bonus is a throwaway +1 (except at the lowest levels, where the budget is tiny). **Budget = item level x tier (Magic 1, Rare 2, Epic 3)**, matching the even steps. 1 point = +1/2 attribute or +1 skill (the soulstone's values), to be judged from the samples.
- **A soulstone on a Common item** makes it Magic with a random category. Tiered armor also drops from monsters (below); soulstones are not the only way in.
- **No wear**: tiered items never wear out (can change later).
- **Tooltip**: full name in the tier color; tier, category, item level, required rank; the bonuses; armor value and requirements.
- **Strong monsters stay in the pentagrams only**, to keep people going there.
- **Drops (starting numbers)**: 1 in 100 kills drops tiered armor, 1 in 5 for Strong monsters; tier odds 70% Magic, 22% Rare, 7% Epic, 1% Legendary. Item level = the monster's rank +-1.
- **Metal follows the item level**: bronze and steel low, gold and crystal in the middle, titanium late; **steel can drop at any level**.
- Chests that give "of the Lion" style armor today give Magic items instead.
- **Glow**: subtle at every tier, never obnoxious (several pieces on the ground). **Grave glow** is built at the same time.
- Separate pools for helmets and body armor: **not needed**, the categories cover it.
- Rank to reroll or upgrade: **not needed for now**, maybe after release.
- **Soul Crucible**: the container's name. Sprite: a block with a glowing hole at the top and a soulstone symbol on the side, 2-3 sprites for its state (empty, one stone, full). Available at all ranks. **Three ranks**: Lesser Soul Crucible (stones up to level 7, cheap), Soul Crucible (up to 14), Greater Soul Crucible (up to 20, expensive). Same base sprite, **a different glow color per rank**, each with empty / half / full states.
- Come back to: Epic effects, Legendaries, the skill suffix words, the bonus values (after the samples).

## Decisions, round 4 (small ones)

1. **A skill rolls at most once per item**, to keep items varied.
2. **Attributes**: the category's two main attributes are equally likely (Strength or Agility, Intuition or Willpower). An Epic's secondary: **70% the other main attribute, 30% Braveness**. (Braveness-main items keep the usual main attribute as the secondary.)
3. **A reroll does not change the Epic special effect.** It gets its own way to be rerolled. Suggestion: an upgrade stone used on an Epic (which can't be upgraded further) rerolls its effect.
4. **An upgrade keeps** the main attribute and the skills, re-splits the bigger budget over them and adds one new skill.
5. **Selling price**: the metal's normal price x the tier step (x1, x2, x3, x5).
6. **Legendaries are unique, hand-designed items.** A soulstone does nothing to them ("This item is too powerful to change."). They exist **only for the main cap metals: steel, emerald and titanium**, and **all of them are late game** (high item levels; e.g. a steel Legendary for Harakim, not an early-game steel item). So the 1% Legendary drop chance only applies to late-game monsters; earlier, that roll falls to Epic.
7. **Weapons: soulstones are blocked on weapons for now.** Weapons get the tier system later; whether with the same bonuses or their own set is open.
8. **The glow is a look only**, no light.
9. **Tiered items can be dropped, given and traded** like any other item.
10. **Messages**: reroll "The soulstone sinks into the armor. Its powers shift."; upgrade "The armor's glow intensifies for a moment. Afterward, you feel it has become more powerful."
11. **Soul Crucible prices (first idea)**: Lesser 25-75 gold, Soul Crucible 150-300 gold, Greater 500-600 gold but probably higher. For scale: a titanium two-handed sword sells for 500 gold (50,000 silver). Suggestion for the Greater: about 1,500 gold.

## Decisions, round 5 (the bonus numbers)

- **Overall strength stays as drafted**: an Epic around rank 18 is about as strong as today's best unique armor (Cap of the Math Genius: +12 Willpower, +12 Intuition, +25 Identify, +25 Sense Magic). Legendaries get hand-set numbers, not the 5x formula.
- **Point values stay the soulstone's**: 1 point = +1 skill or +1/2 attribute. Can be reworked later.
- **Minimum budget 8**: budget = max(item level, 8) x tier step. A Magic item gives at least +4 (today's normal modded armor) from rank 1; Magic items grow from level 9 and reach the old Godly +8 around level 16.

  | Main attribute on a Magic item | Rank 3 | Rank 8 | Rank 13 | Rank 18 |
  |---|---|---|---|---|
  | Old modded (7 in 8) | +4 | +4 | +4 | +4 |
  | Old Godly (1 in 8, any rank, even bronze) | +8 | +8 | +8 | +8 |
  | New Magic | +4 | +4 | +7 | +9 |

- **In the pocket: "Blessed" double roll.** About 1 in 20 items would roll with double budget and a special prefix: a rare jackpot find, especially early. Concern: at end game everyone could end up with Blessed gear. If it is added, **a reroll removes the Blessed status**, so it stays a lucky find, not something to farm.

## Decisions, round 6 (late game)

- **Late game starts at rank 16, Major General** (Lieutenant General, 17, was the other candidate). From there gear lasts a long time, so players have time to farm the perfect pieces.
- **Legendaries have item levels 16-20** (need rank 16+). Only monsters of rank 16 and up can roll Legendary; below that the 1% Legendary roll becomes Epic. A Legendary drops at the monster's rank, capped at 20.

## Epic special effects (round 7)

Every Epic gets one. Left out: **Night sight** (it is the reward of the four-potion quest and would undo Lab 11's darkness) and **Water breathing** (would undo Lab 11's water and the planned flooded mine). Thrift was dropped (too close to Concentrate).

| Effect | What it does | Built on |
|---|---|---|
| **Regeneration** | Hitpoints also regenerate while moving and fighting (today only while standing still), plus faster regeneration | `do_regenerate` |
| **Clarity** | The same for mana | `do_regenerate` (today mana only regenerates with Meditate) |
| **Stamina** | The same for endurance | `do_regenerate` |
| **Thorns** | Melee attackers take damage back | items' existing "gethit damage" |
| **Light** | The wearer gives off light | items' light |
| **Warding** | Curses and stuns on the wearer wear off sooner | spell timers (new) |
| **Lasting** | Spells the wearer casts last longer | spell durations (new) |
| **(name open)** | More experience from kills only, at most +5% | experience code (new) |

- Category: no hard limits, so everyone has options; suggestion: weighted odds, e.g. Thorns twice as likely on Fighter items, Clarity and Lasting twice as likely on Mage items.
- Open: the strength numbers per item level; for the regeneration three, how much regenerates while active (suggestion: 20% of the standing rate at low levels up to 50% at level 20) and whether Clarity gives mana regeneration without Meditate; the name for the experience effect (ideas: Insight, Seasoned, Veteran, Tutelage, Fortune).

## How soulstones work now (for reference)

- A "Strong" monster (randomly boosted when it spawns) carries a soulstone holding 10-15% of that monster's experience. The stone's **level is the character rank that this much experience would give** (same scale as ranks; "That's as high as they go" above 20). So it comes from the monster, not from the player who finds it.
- Stone on stone: the first stone gains a random part (0-100%) of the second one's experience, the second is used up.
- Stone on equipment: random bonuses with a total strength of the stone's level, and the item then needs that rank to wear (`soultrans_equipment`).
- Suggestion: keep this rank scale for the tiers too. Item level, soulstone level and the rank needed to wear the item are then the same number, which is easy to understand ("a level 12 helm needs rank 12 and a level 12 stone").
