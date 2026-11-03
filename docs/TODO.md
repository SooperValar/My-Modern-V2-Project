# To do

In order:

1. ~~**Lab 11 arena deaths**~~ (done): every death in Lab 11 counts as an arena death (items kept) until the lab is finished. Two signs, one on each side of the entrance to the first underwater section, saying the lab is still being worked on and deaths there are arena deaths for now.
2. ~~**God item shop**~~ (done: `#godshop`, merchants in Elysium, and the Elysium layout): a shop only gods can use, with every item template in the game, free. It needs pages (a shop window holds 62 items), e.g. next/previous buttons or a category or search filter.

3. ~~**Item tiers**~~ (done: parts 1-4) for helmets and body armor (Common/Magic/Rare/Epic/Legendary, white/blue/yellow/purple/orange, random drops, soulstone upgrade and reroll): see `docs/ITEM_TIERS.md`. Part 5, Legendaries, is under "Later".

4. ~~**Pentagram enemies leave no grave**~~ (done) unless they carry something besides their weapon.
5. ~~**Pentagram solve balance**~~ (done: 5 + 2-3 per player who activated one in the last 10 minutes): look at how the solve count works (now: players online + three random 0-19, so about 28 + players online; 54 right after a server start; every active pentagram in the world counts) and make it work for a solo player as well as for groups. **Base it on the players actually doing pentagrams** (e.g. those in the pentagram area or who activated one recently), not everyone online; usually 1-5 people.

6. ~~**Equipment compare**~~ (done: differences in the tooltip, Shift shows the worn piece): when hovering an item, show how it compares to what is worn in that slot (e.g. a second tooltip with the worn piece, or +/- differences in green and red).

7. **Ice set sprites**: the Helmet, Armor, Leggings, Boots and Gloves of Ice (unique, templates 1272-1276) use sprites 18100-18104, which don't exist in the client ("Sprite ... is missing"). They need pictures (new ones or recoloured).

8. **Lab shrine keys for missed lab shrines**: a way for players to get a key for a labyrinth shrine they missed. Price: 100 gold per shrine times the lab level (e.g. a missed shrine in lab 5 costs 500 gold).

9. **#quest list: order and rewards**: the new `#quest` (built, committed, not live yet) lists the quest givers easiest first by their experience reward. Cody wants to go through the list and adjust the order and the rewards (skill / item / experience: the NPC editor's Talk & quest tab). Maybe a separate "difficulty" number per quest so the order doesn't have to follow the experience. Also: keep `#journal` only for temporary / seasonal quests?

10. **Odd-shaped zones**: a zone doesn't have to be one box. Several boxes with the same name act as ONE zone (e.g. a 3x3 square plus one tile off its bottom-right corner is one zone, not two). Now: `server/area.c` is a list of boxes (`x1,y1,x2,y2,name,flag`), and `get_area` / `get_area_m` add every box that contains the spot, so two touching or overlapping boxes with one name give "Elysium, Elysium", and `get_area_street` treats each box as its own building (size = that box only). To do: group boxes by name (list a name once; size and edges of a building from all its boxes), let the editor draw and show a zone as one shape made of boxes (add/remove a box or tiles, one name and flag for all), and keep the minimap / zone maps right.

11. **Weapon, ring and Harakim rebalance** (idea 2, to design first):
    - **Two-handed sword around Agility, two-handed axe around Strength.** Now both skills use Agility/Strength/Strength (`skill.c`), and both specials are a flat 1 in 8 (`WP2H_SPECIAL`, `data.h`): sword = deflect 1 in 8 melee hits against you, axe = critical hit (double damage) 1 in 8 of your hits (`do_attack`, `svr_do.c`). Idea: sword Agility-heavy with a deflect/parry chance that grows with Agility; axe Strength-heavy with a crit chance that grows with Strength. Update the tooltips (`svr_tick.c`) and `#weapons` (`svr_do.c`).
    - **Rings**: Agility rings on par with the Strength emerald rings; look over the whole ring list.
    - **Harakim**: dagger / spell book for casters, staff for summoners. Spells Willpower-focused, summoning (Ghost Companion) Intelligence-focused. Now every spell uses Braveness/Intelligence/Willpower (`skill.c`), and the Staff skill uses Agility/Strength/Strength.
    - **Ghost Companion follows its Harakim through portals and teleports** (also recall, lab exits, `#recall`?).

12. **Area completion bonuses** (idea 3, an early-game experience boost): kill all of an area's set creatures (e.g. the Haunted Castle 588,530-623,554, Skeleton Lord 590,467-610,488, and other buildings in and around Aston) and get an experience bonus. Not for spawner areas (the Abandoned Clan Halls). To decide: which areas and their bonus; the list of creatures per area (their placed NPCs, e.g. picked in the editor); once per character or again after a cooldown; does a group share it (kills by party members / companions count); how far the player must have taken part (e.g. at least one kill, or in the area); a message on completion and maybe a "#areas" list of done/not done. Uses the zone boxes (see 10, odd-shaped zones).

Later (ideas, not decided):

- Item tiers part 5: Legendaries (hand-designed named pieces; the current special armors move here), see `docs/ITEM_TIERS.md`.
- Prestige: what triggers it and what it gives (the Final Test's Shrine of Change will be used).
- Unused recolors of the exploration point post: green 1012, blue 1019/1020, purple 1144 (gold 1090 is the exploration point). Nothing uses them yet; maybe for prestige (e.g. points or markers only prestiged characters can use).
- Swimming skill: a river south of Aston and a flooded mine quest like Lab 11 (without the darkness).
- Lab 11's third merchant.
- Undead regeneration and underwater damage balance, after more testing.

## ~~MyV2 Editor: redo the view-switch icons (round buttons top right of the map)~~ (done)
Cody wants to revisit these five, like the tool symbols: grid, see through walls, light from lamps, reload the world, show/hide the right panel. Same gold-on-wood style.
