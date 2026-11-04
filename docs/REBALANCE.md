# Rebalance: two-handed weapons, rings, Harakim (TODO 11) - design

Status: **built** (Nov 4): attributes, curve, spells, rings and stones, spell books, Ghost Companion following. Waiting to go live (server code + world update). **Staff: still to design.** Changes listed in `CHANGES.md` (Rebalance).

## Decisions so far

- **Attributes: yes.** Two-handed sword Agility, Agility, Strength; two-handed axe Strength, Strength, Agility.
- **Deflect / crit curve: min 8 %, max 25 %, K = 40**: chance = 8 % + 17 % x A / (A + 40) (A = Agility for the
  sword's deflect, Strength for the axe's crit): 10 -> 11.4 %, 25 -> 14.5 %, 50 -> 17.4 %, 75 -> 19.1 %, 100 -> 20.1 %,
  150 -> 21.4 % (today a flat 12.5 %).
- **Rings: Topaz (Agility), Amethyst (Intelligence) and Diamond (Braveness)**, each Small / Medium / Big / Huge at
  +3 / +6 / +9 / +12 like the Emerald.
- **Spells Willpower, Willpower, Intelligence; Ghost Companion Intelligence, Intelligence, Willpower - for every class.**
- **Spell books: tiers like armor / weapons, colour-coded covers, named Initiate, Apprentice, Adept, Mage, Archmage.**
  Flat bonuses (like a soulstoned item's power, but the same stats every time, not random): Willpower and spells,
  scaling from low to high. Proposal below, waiting for Cody's OK.
- **Staff: later** (after the books).

## Spell books (proposal)

A spell book is held in the left hand (the shield slot) with a dagger. No armor. The cover colour shows the tier; the
name stays white (these are plain items, not Magic / Rare / Epic).

| Book | Cover | Rank needed | Willpower | Blast, Heal, Bless, Magic Shield (each) | Mana | Points* |
|---|---|---|---|---|---|---|
| Initiate's Spell Book | Red | 2 Lance Corporal | +1 | +2 | +10 | 10 |
| Apprentice's Spell Book | Yellow | 6 Master Sergeant | +2 | +3 | +20 | 16 |
| Adept's Spell Book | Green | 10 First Lieutenant | +3 | +5 | +30 | 26 |
| Mage's Spell Book | Blue | 14 Colonel | +4 | +6 | +40 | 32 |
| Archmage's Spell Book | Purple | 18 General | +5 | +8 | +50 | 42 |

*Points as in `docs/ITEM_TIERS.md` (+1 skill = 1 point, +1 attribute = 2): a book is about as strong as a Rare tier
armor piece of its level (Rare budget = 2 x max(level, 8): 16, 16, 20, 28, 36), a bit more at the top because it takes
the place of a shield.

Decided: six spells (+ Protection and Enhance Weapon), the numbers above; **all five sold by Damor**. Later: a second
merchant who sells only spell books and staffs. Not dropped (yet).

**Two-Handed Axe skill renamed Greataxe** (Cody, Nov 4).

## Ghost Companion buff (decided and built, Nov 4)

- **Staff**: a Harakim holding a staff summons with +15 % power, an Arch-Harakim +20 % (instead of a class bonus on
  every summon; every staff's tooltip lists it). Other classes: no staff bonus.
- **Intelligence**: +1 % power per 10 points of the caster's Intelligence (every class).
- **Willpower**: +2 hitpoints per point of the caster's Willpower for the ghost (every class).

Before:

Cody wants the Ghost Companion a bit stronger depending on whether a Harakim summons it, whether it is summoned with a
staff, and the caster's stats. Now (`skill_ghost`, `skill_driver.c`): power = Ghost Companion skill x 4 / 11, times the
class factor of `spell_race_mod` (the same for every spell: Harakim 1.00, Arch-Harakim 1.05, Sorcerer 1.10, Warrior 1.10,
Mercenary 1.05, Seyan 0.95, Arch-Templar 0.95, Templar 0.90; new moon -0.15, full moon +0.15); its attributes, skills,
hitpoints (power x 5) and endurance come from that power, its weapon / armor from its Agility and Strength.


## Curve options (deflect for the sword from Agility, crit for the axe from Strength)

chance = min + (max - min) x A / (A + K), A = the attribute. Grows fast early, then flattens towards max and never
reaches it. Example with min 8 %, max 20 %:

| Attribute | K = 30 | K = 50 | K = 80 |
|---|---|---|---|
| 10 | 11.0 % | 10.0 % | 9.3 % |
| 25 | 13.5 % | 12.0 % | 10.9 % |
| 50 | 15.5 % | 14.0 % | 12.6 % |
| 75 | 16.6 % | 15.2 % | 13.8 % |
| 100 | 17.2 % | 16.0 % | 14.7 % |
| 150 | 18.0 % | 17.0 % | 15.8 % |

(Today: a flat 12.5 % everywhere.)


## How it works now (from the code)

**Skill value** (`really_update_char`, `svr_do.c`): a skill's value = its trained level + item bonuses + (the sum of
its three attributes) / 5. The three attributes per skill are in `skilltab[]` (`skill.c`).

| Skill | Attributes now |
|---|---|
| Two-Handed (sword) | Agility, Strength, Strength |
| Two-Handed Axe | Agility, Strength, Strength |
| Dagger | Braveness, Agility, Intelligence |
| Staff (marked unused) | Agility, Strength, Strength |
| Every spell, Ghost Companion included | Braveness, Intelligence, Willpower |
| Meditate | Intelligence, Willpower, Willpower |
| Concentrate | Willpower x 3 |

**Hitting** (`do_attack`): the attacker's weapon skill against the defender's weapon skill gives the chance to hit and a
damage bonus. Damage: weapon value + 1-6, + a random part of Strength / 2 (every weapon).

**The two-handed specials** (players only, `WP2H_SPECIAL` = 8):
- Two-handed sword: **deflects 1 in 8** melee hits against you.
- Two-handed axe: **1 in 8 of your hits is a critical** (double damage).

Both are flat: the same at every Agility / Strength.

**Rings** (only gold rings have stats; silver rings with gems are trade / quest items):

| Gem | Small | Medium | Big | Huge |
|---|---|---|---|---|
| Ruby | Willpower +3 | +6 | +9 | +12 |
| Emerald | Strength +3 | +6 | +9 | +12 |
| Sapphire | all five +1 | +2 | +4 | +6 |

There is **no Agility ring** (nor Intelligence or Braveness), so an Agility build has nothing like the Emerald rings.

**Harakim weapons**: there are no staffs players can use (the only two "staff" items are the Grolm Trident and Grolm
Crown) and no spell books. Daggers use Braveness, Agility and Intelligence.

**Ghost Companion and teleports**: a teleport (portal, recall, scroll, lab exit) moves only the player. The companion
stays behind, can't see its master, and after a while it destroys itself and costs the player 1 luck
(`driver.c`: "Self-destructed because of neglect").

## Proposal

### 1. Two-handed sword around Agility, two-handed axe around Strength

| Skill | Now | Proposed |
|---|---|---|
| Two-Handed (sword) | Agi, Str, Str | **Agi, Agi, Str** |
| Two-Handed Axe | Agi, Str, Str | **Str, Str, Agi** (the same three: no change for axe users) |

The specials grow with the attribute instead of a flat 1 in 8 (12.5 %):
- **Sword: deflect chance = 5 % + 1 % for every 10 Agility, at most 25 %.** Agility 75 -> 12.5 % (today's value), 150 -> 20 %.
- **Axe: critical chance = 5 % + 1 % for every 10 Strength, at most 25 %.** Same curve.

Tooltips and `#weapons` show the player's own current chance ("Deflect: 14 % of melee hits against you").

Effect on existing characters: two-handed sword users with much more Strength than Agility lose a few skill points
(each point of Strength moved to Agility in the formula is worth 1/5 of a skill point).

### 2. Agility rings on par with the Emerald (Strength) rings

New **Topaz** rings: Golden Small / Medium / Big / Huge Topaz Ring, **Agility +3 / +6 / +9 / +12**, same prices and
the same shops and drops as the Emerald rings. New sprites (recoloured emerald rings, new numbers).
Optional, same pattern: Amethyst (Intelligence) and Diamond (Braveness).

### 3. Harakim: casting focused on Willpower, summoning on Intelligence

| Skill | Now | Proposed |
|---|---|---|
| Spells (Bless, Heal, Blast, Curse, Stun, ...) | Brv, Int, Wil | **Wil, Wil, Int** |
| Ghost Companion | Brv, Int, Wil | **Int, Int, Wil** |

Weapons:
- **Dagger + spell book** (casters): the spell book goes in the left hand (the shield slot), no armor, + spell skills
  and + mana (e.g. "Bronze Spell Book: Blast +2, Bless +2, mana +10", tiers like the other gear).
- **Staff** (summoners): a two-handed staff, + Ghost Companion and + Intelligence. It fights with the Dagger skill, so
  no class needs a new skill.

Effect on existing characters: Harakim who raised Braveness lose spell power; Willpower / Intelligence builds gain.
Templars / Seyan who cast are affected too.

### 4. Ghost Companion follows its Harakim through teleports (ready to build)

When a player is moved by a portal, recall, teleport scroll or a god, their companion is moved with them, to a free
tile next to them. Not into places companions can't go (arena of rank, labyrinth start): there it is left behind as now.

## Questions for Cody

1. Two-handed sword: Agility, Agility, Strength? And the deflect / crit curve (5 % + 1 % per 10, at most 25 %)?
2. Rings: only Topaz (Agility), or also Amethyst (Intelligence) and Diamond (Braveness)?
3. Spells Willpower, Willpower, Intelligence and Ghost Companion Intelligence, Intelligence, Willpower - also for
   Templars and Seyan, or Harakim only (that would need class-dependent formulas)?
4. Spell book in the shield slot and a staff that uses the Dagger skill - OK? Who sells them, and tiers?
