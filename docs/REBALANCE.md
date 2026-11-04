# Rebalance: two-handed weapons, rings, Harakim (TODO 11) - design

Status: **proposal, waiting for Cody's choices** (the questions at the end). Nothing built yet except where it says so.

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
