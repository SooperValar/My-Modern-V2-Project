# MyV2: design ideas and to-do

The one list of everything still to do or decide for Mercenaries of Asgard v2: fixes, systems, classes, items,
world, quests, the editor, the client and Discord. Merged Nov 10 from the old TODO list and Cody's
`Design Document.txt` (MyV2 folder). New ideas go straight in here, under their section.

- **Priority:** ★ **Next** (in the queue below) · ● **Soon** (decided, not started) · ○ **Idea** (not decided yet)
- **(was #n)** = the item's number in the old numbered list; `CHANGES.md`, `HANDOFF.md` and old commits use those numbers.
- Finished work moves to **Done** at the bottom (one line each; the details are in `CHANGES.md`).

---

## Up next (in order)

- ● **HIGH - 32-bit sprite numbers (Cody, Nov 19: "high on the to-do list... but we have to wait for the right time").**
  Sprite numbers are 16-bit everywhere, so 65,535 is the ceiling; about 13,000 are free and safe, the biggest free block
  is 768 (`docs/SPRITE_MAP.md`, `tools/world/sprite_scan.py`). The move touches: `map.dat` (sprite / fsprite per tile:
  the 28-byte tile grows), items and templates (`sprite[2]`), characters and templates (`sprite`, `sprite_override`),
  effects, the server's map/char/item messages to the client (`unsigned short` in svr_tick.c's smap / cmap and the
  packets), the client (`map[].ba_sprite` etc., `MAXSPRITE`, its sprite cache and loaders), the editor (`MAP_FMT`, every
  struct offset, the patch format) and every tool that reads the .dat files (arealib, mapedit, render_region, scans).
  Needs a one-time convert of all .dat files and a client everyone must update at once. **The right time:** a planned
  downtime with no players, before the sprite room actually runs out (rerun the scan now and then). Until then: keep
  new sets small (2 variants, 3x3 water) and record every range in SPRITE_MAP.md.

- ● **Godot client for MyV2** (Cody, Nov 21): built from github.com/jamesblack/thelastgate-godot (James OK'd it). `docs/GODOT_CLIENT.md`. Groups A and B done (Nov 25). **Nov 25: MyV2 switches to the Godot client only** (merc.exe dropped): work through the gap list in "The switch", then the server refuses old clients (done), then the 60-slot backpack (live Nov 26, 13:36). Later: the Editor and tools/world read slots 40-59 (item2). Step 6 (installer + updater) done: client 3.0.0 released Nov 26; Discord #welcome points to its Setup.exe. Buffer GC on hold (Cody, Nov 26: likely part of a new class later). Later: delete the test releases (Cody has no gh: delete them on the GitHub releases page, then `git push origin --delete updater-test-v0.9.0 updater-test-v0.9.1`).

**For Nov 18 (Cody, Nov 17 night):**
- ★ **Clean up the Golem Foundry's object distribution**: the pieces in the yard and the Hall (anvils, benches, crates,
  furnaces, wrecks, slag) placed by `build_foundry.py`; Cody rearranges in the editor (Objects -> Workshop, the
  Slag heaps / Golem wrecks / Crates scatter brushes, the Foundry Yard / Foundry Floor area brushes).
- ★ **Add some poles** (Cody's words; ask which kind / where if it isn't clear).
- ✓ (client 2.15.08 built Nov 20: walls, arches, trees) **Client: hide mode (F6) for the new trees** - `hide_sprite()` (client/engine.c) draws sprite+1, which for the new
  trees (38100-38163, four variants each) is the next variant or a missing number (Cody saw "Sprite 38144 is missing" by
  the willows, Nov 17). Stopgap: 38112 / 38124 / 38134 / 38144 / 38158 are copies of the stumps (client-dist). Fix in the
  next client build: the new trees -> a stump, 38164 + (sprite & 3).
  **Also the new walls (Nov 20, Cody: "Sprite 36038 is missing" by the Broodmother in hide mode):** sprite+1 of a new
  wall is the next variant (no hiding) or, after the last one, a missing number. Low blocks now exist at first+8 (plain)
  and first+9 (grain) of each material (36008/9 ... 36078/9; `world_walls.py --low`), so nothing is missing any more;
  the next client build: 36000-36079 with (sprite % 10) < 8 -> sprite - sprite % 10 + 8 + ((sprite % 10) >= 4).

0. ★ **Login check bug (found Nov 19) - FIXED, LIVE 21:17** (Cody's saved key for Iluvatar matched on both halves first; if a login ever fails with "wrong password" after this, the old line is in git history): `svr_tick.c` plr_login compares `ch[cn].pass2!=ch[cn].pass2` (itself), so the
   second half of the password is never checked against what the player sent (`player[nr].pass2`). Original game code.
   Fix only with Cody's OK: test a login with the test client first.
0. ★ **Recall to each town's temple / chapel** (Cody, Nov 19) - **LIVE Nov 19, 19:42** (CHANGES.md "Town shrines set your recall"): `use_driver.c` town_shrine[] - Skua 492,512 -> 512,512 (not purple players), the Purple One 560,549 -> 560,544 (only purple players; PURPLE_RECALL_X/Y in gendefs.h, was 558,542 everywhere - Cody), Fenwatch 434,817 -> 434,812 facing east, Stonehold 664,836 -> 669,836; `svr_god.c` god_transfer_char turns you that way on arrival. Original note: a player can change where Recall takes him to the
   temple or chapel of the town he is in, by using that town's shrine with nothing in his hand (Aston, Fenwatch, Stonehold,
   the Last Bastion later). Needs server code: the shrine's use driver sets the character's recall point (the temple's
   spot) and says so; Recall reads it instead of Aston. To work out: which object is each town's shrine, where the recall
   spot is, whether to charge for it, and what new characters start with (Aston).
0. ★ **Quest plan, area by area**: bands A-B done, Fenwatch + Drowned Village (Nov 16) + Barrow Hills + Lizard Hatcheries (Nov 17) live: band C done; Stonehold + its people, the Golem Foundry (Nov 17), the Ashen Fields (Nov 18) and the Gargoyle Spires with Bastion Road and the Monastery (Nov 19) live - band D done; next band E (the Last Bastion): **follow `docs/QUEST_BUILD.md`** - [Quests](#6-quests)
1. ★ **Soulstone levels too low** (MAJOR): LIVE Nov 26, 23:18 (Cody checks in game) - [Fixes](#1-fixes-and-balance)
2. ★ **Discord**: built Nov 14 (CHANGES.md "Discord"); waiting on Cody's webhooks / bot (HOSTING.md "Discord links")
3. ★ **Walking speed, speed modes and attack speed**: built Nov 27 (Speed / move / attack / cast, faster move rows, +2 move, item bonuses), not live; next: which items and abilities get bonuses, tweak numbers - [Systems](#2-gameplay-systems)
4. ★ **Town NPCs' door loop** - [Fixes](#1-fixes-and-balance)
5. ★ **Logout at shutdown** - [Fixes](#1-fixes-and-balance)
6. ★ **Resizable game window** - [Client](#8-client-sprites-and-art)

**Waiting on Cody:**
- Town leftovers: Re-check zones for the area clears, if not done yet ([World](#5-world-and-areas)). (Zones for the new buildings and Steven's house: done, Cody Nov 11.)
- The Windows restart test of start-with-Windows (Discord #server-status shows if the server came back by itself).
- Quest rewards on the editor's Quests page, if he wants changes ([Quests](#6-quests)). (Order: Cody is happy with it, Nov 11.)
- Checking the merchants in game: pages, selling + buying back, prices ([Items](#4-items-weapons-and-shops)).
- Setting up the area clears (quest areas first) and the class rewards, when he wants.

---

## 1. Fixes and balance

### ★ Soulstone levels too low (MAJOR) (was #28) - LIVE Nov 26, 23:18
Cody: "I'm getting level 6 armors dropping but only level 2 soul stones." Cause: stones held 10-15% of the enemy's exp and
took their level from that, 2-8 levels below the armor (enemy rank -1..+1). Built (Nov 26, both server folders, tested
on a test build): stone level = enemy rank -1..0 (Strong 0..+1), 1-20, exp inside that level (`tier_enemy_soulstone`);
drop chance never rarer than armor's 1 in 100 (`SOULDROP_MAX`, from rank 14). CHANGES.md "Soulstones from any enemy".
Left: Cody checks drops in game.

### ★ Town NPCs and their doors: no more open / close loop (was #27)
Town NPCs walk to "their" doors and close them (`driver.c` ~1592, `npc_driver_low`: up to four door spots in
`data[20..23]`, the NPC uses the door when its item is `active`, i.e. open, and nobody stands next to it; the editor's
NPC page sets these spots). Cody sees NPCs reopen a door that is already closed and then go to close it again, forever.
To check: doors whose open / closed state is the other way round (active = closed sprite), locked doors the NPC can't
really use, two NPCs sharing a door, or using an already closed door opening it.
Fix options (Cody would take either): only close when the door is really open (and remember a failed try for a while),
never use a door to open it, or an editor / server switch to turn door closing off (for one NPC, or all town NPCs).

### ★ Logout at shutdown (players online during a stop / restart) (was #17)
The logout loop at shutdown in `server.c` is bypassed (a WSL / live-server workaround, see CHANGES.md "Server
modernization"); check what happens to players online when the server stops or restarts (saved position, items, their
character staying "online"), and bring back a safe logout if needed.

### ○ Grave sprites are finicky depending on the direction (new, Nov 10)
Look at how graves pick their sprite and facing. (Chests have only the game's two facings, south 220/221 and west
222/223; north / east were tried three ways and dropped. Graves may have the same limit.)

### ○ Undead regeneration and underwater damage balance
After more testing. Nov 17: the quest areas' undead (groups in `SLOW_UNDEAD_GROUP`, data.h) heal ~4 hp/s like Lab 11's;
the game's other undead keep ~12 hp/s. The Graveyard undead (below) should go in that list too.

---

## 2. Gameplay systems

### ★ Walking speed, the three speed modes and attack speed (was #26)
**Nov 27: built, not live** (CHANGES.md "Speed, move speed, attack speed and cast speed"): Speed (mode + race +
bonuses) and three speeds from it - attack (Agi + Str), cast (Agi + Int), move (Agi + max(Str, Will), +2); the speed
table has 10 faster rows that only moves use; items / spells carry Speed / move / attack / cast bonuses (editor Items
page -> Stats -> Speed); protocol 3.1.0 with Godot client 3.1. **Next (Cody decides):** items and abilities with
bonuses (e.g. winged boots: move speed), tweak the numbers after playing (Cody: "we can always revisit later"), maybe
open the faster rows to attacks / casts. The notes below are how the old single speed worked.

Cody wants changes here; look at it together first. How it works now: one speed value is used for every action,
walking AND attacking (`ch[].speed`, set in `really_update_char`, `svr_do.c` ~4007):
n = (Agility + Strength) / 50 + speed_mod (items / spells) + 12 slow / 14 normal / 16 fast, speed = 20 - n
(0 fastest .. 19 slowest), so the speed buttons and Agi + Str change walking and attacking alike. Each animation step
waits on `speedtab[speed][ctick]` (`svr_act.c` ~1079, `speedo` / `ch_act_speed`; the greataxe once added `AXE2H_SLOW`).
The modes also cost endurance (fast drains it, `svr_do.c` ~4120-4137) and change Stealth (slow / normal sneak better,
`svr_do.c` ~3710). To decide: separate walk and attack speed, how much stats should matter, what the modes cost / give.

### ● Waypoints (was #13): live, Cody checks the sound and the glow
Live Nov 12 and tested by Cody (finding, the travel window, travel, his own pictures by paste). Client 2.15.05 published
Nov 12 (client-dist 0633098: travel window, night glow of found circles, circle sprites, `sfx\19.wav`, the pictures of
waypoints 1-5). CHANGES.md "Waypoints", "Waypoints tab".
**Left:**
- ~~push, then the update with the travel sound and `CLIENT_LATEST` 0x020F05~~ (done Nov 12, all live).
- Travel sound: Cody's own pick since Nov 12 (see CHANGES); night glow and the Clan Pentagram: fine as they are (Cody).
- New waypoint pictures need a client publish each time (until then: the stock picture).
- The old Clan Pentagram in the Mine, 1st Level (469,523) stays as it is (Cody, Nov 12).

### ● Weapon, ring and Harakim rebalance: what is left (was #11)
Live Nov 4 (see `docs/REBALANCE.md` and CHANGES "Rebalance"): Two-Handed now Agility-based, sword deflect / axe crit.
Still open:
- **Summoner's staff** (Harakim: dagger / spell book for casters, staff for summoners; spells Willpower-focused,
  summoning Intelligence-focused). Pictures in `docs/ref`.
- **Rings**: Agility rings on par with the Strength emerald rings; look over the whole ring list.
- ~~Ghost Companion follows its Harakim~~: already done (`companion_follow` in `god_transfer_char`: portals, teleports,
  recall, scrolls, waypoints). Only check lab exits if Cody sees it stay behind somewhere.

### ○ Peacekeeper as an editable flag (new, Nov 10)
Cody: how do town NPCs summon a Peacekeeper; make it a flag so it can be set on town NPCs.
Now (`driver.c` ~244, `npc_gotattack`): it is not a flag. Any NPC whose **alignment is exactly 10000** shouts "Skua!
Protect the innocent! Send me a Peacekeeper!" when a player attacks it and summons a "Shadow of Peace" (template 80)
for 2 minutes, once a minute at most. To do: a real flag (or an NPC editor checkbox that sets it), so it no longer
depends on the alignment value.

### ○ More than one Ghost Companion per player (Cody, Nov 6)
`#gca` / the spell bar already send all of a player's companions. To decide: how many, how they're summoned (the spell
with a selected enemy summons while below the limit, sends them at the limit?), mana, and `ch[].data[CHD_COMPANION]`
(holds one) + `die_companion`.

### ○ Black Stronghold points system: expand it (was #18)
How it works now (`talk.c`, `driver.c`): a character's points = kills in the Stronghold area below their rank / 25 +
at their rank + above their rank x 2 (`data[26..28]`) + 25 per Black Candle given to the Cityguard (`data[43]`, the
candle hack in `npc_give`) - points already spent (`data[41]`). Spent with the Cityguard (template 518) by saying
POINTS, BUY GOLD (1G a point, at most 100 at once), BUY HEALING (6), BUY MANA (9), BUY EXP (`stronghold_exp_per_pt`:
points_tot / 45,123, 1-125 exp a point). Ideas: more things to buy (items, tier armor, keys, a Stronghold title),
points as a reward type on the Quests page, a `#stronghold` command showing your points, the candle's 25 points
editable. Related fix: the three Black Stronghold Coin pieces (Star 761, Circle 762, Empty 763) all have the same
description ("showing a star"); fix in the item editor.

### ○ Prestige
What triggers it and what it gives (the Final Test's Shrine of Change will be used). Unused recolors of the
exploration point post could go with it (green 1012, blue 1019/1020, purple 1144; gold 1090 is the exploration point),
e.g. points or markers only prestiged characters can use.

---

## 3. Classes

### ○ Brawler (new class, Nov 10)
- **Fists** as the weapon: Claude could make them from the FoH sprite (to check which sprite that is).
- **Focus:** Hand to Hand, Braveness and Strength. Now Hand to Hand uses Braveness / Agility / Strength (`skill.c`);
  a Brawler version would be Braveness / Strength / Strength or similar.
- To decide: starting stats and skills, which race / templates, what the class gets that others don't (specials like
  the greataxe crit or the sword deflect), class rewards on the Quests page.

---

## 4. Items, weapons and shops

### ○ Ice, Burning and Lava Greataxes (new, Nov 10)
Special greataxes to go with the Fire / Ice themes.

### ○ Special weapons for every weapon type (new, Nov 10)
More special weapons so Sword, Two-Handed, Dagger and Greataxe have similar levels. First step: **a table of every
weapon** (type, level / requirements, damage, specials) generated from the world data, to see the gaps.

### ○ Item tiers part 5: Legendaries
Hand-designed named pieces; the current special armors move here. See `docs/ITEM_TIERS.md`.

### ● Merchants tab + shop rework: Cody checks in game (was #23)
LIVE Nov 4 (server `merch.c`, editor Merchants tab), see CHANGES.md "Merchants". Cody to check: pages, selling + buying
back, the prices. (Ties in with the Market below.)

---

## 5. World and areas

### ● Town rearrangement and a Market (Nov 10; MOSTLY DONE)
**Done Nov 10** (details in CHANGES.md "Aston rearranged" and the lines after it; pictures in
`MyV2\Town pictures (Nov 10)\`): Aston copied from Cody's copy (Market, graveyard, new houses, east side 2 tiles east,
holes / ladders / chest kept working); every NPC placed by Cody; Market merchants one tier each (new Garrett, Lionel,
Martin, Tabor = templates 2012-2015, Karl Bronze only, stock in `merchants.dat`); zones redone (Market one zone, gone
shops removed, Inga / Jefferson / Jamil); tile flags cleaned (grass / street, "no fighting" off the Market and Joe's
house, Cody's picks of stray "no monsters" removed); the Guard of the old Cloth shop stands in the Market, the Janitor
is back on his loop; NPC light duties fixed (each tends the lights of its own room).
**Left:**
- ~~Zones for the new buildings; Steven's house moved~~ (DONE, Cody Nov 11). Claude: redraw `docs/world_zones.png`.
- The Grave Keeper / graveyard quest NPC (see [Quests](#6-quests)).
- Area clears: "Re-check zones" on the Quests page (the Cursed Tomb and Gorn Clan Hall moved 2 east).
- Old shop greetings still name their old shops (e.g. Hagen "Welcome to the Golden Armor Shop!"): rewrite for the
  Market if Cody wants.
- Door spots of the NPCs that moved were cleared: set them again where they have a house (editor: NPC page, "Patrol &
  chores"). Old wrong door spots (part of the door loop item): the Barkeeper (508,488) and Thief 970 (455,546).
- The Market guard (Guard, template 7) has no patrol: give him stops if he should walk the Market.
- The Market square is still mostly "indoors" (left as is; Cody decides).
- Clear Cody's copy at x 443-627, y 737-929 when he's happy (it has a working spider spawner).
- Redraw `docs/world_zones.png` after Cody adds zones (`tools/world/worldzones.py`).

### ○ Sunken Gorge -> "The Sunken Archives"? (new, Nov 10)
More bookshelves; the enemies switch to blue lizards (Cody's recolors in
`C:\Users\Cody\Desktop\MyV2\V2SpriteChanger\Lizard\Aqua\Male`, would need new sprite numbers).

### ○ A bigger game world (new, Nov 10)
The map is fixed at 1024 x 1024 tiles (`MAPX` / `MAPY` in `gendefs.h`), shared by the server, the map files in `.dat`,
the editor and probably the client. To find out first: how much free space is left (`docs/world_minimap.png`), and what
growing the map would touch. A big change; maybe new areas fit in the free space first.

### ○ The Soulstone Mine: Mine, 4th Level (Cody, Nov 17)
A fourth mine level reached from **Stonehold's old mine adit** (the dead-end tunnel in the town's south cliff, 707-715 /
806-812, built Nov 17 and kept for this). Called the **Soulstone Mine**: mining it (like the mine levels' rock piles, use
driver 22 `use_pile`, which gives silver, gems and the odd creature) can also turn up **soulstones**, as well as gems.
**Harder than Mine, 3rd Level** (Gargoyle Knights Lieutenant Colonel / Gargoyle Mages Colonel): e.g. Brigadier General and
up. To decide: monsters (theme, ranks), size and where on the map (Mines 2 and 3 are at x 700-839, y 20-89), how the adit
leads down (ladder / hole like the other mine levels), the soulstone chance and levels (ties in with "Soulstone levels too
low" above: stones here could be the fix for higher ranks), and whether it counts as a Stonehold area (bounty, quest).

### ○ Underground III (was #16)
A third level below Underground I (840,0-1024,157) and Underground II (822,176-1020,333; reached by the hole at
925,101 -> 925,301). Theme: Deeplings or Firelings (to choose). To decide: theme, level range (above Underground II's
monsters), size and where on the map it fits, the way down from Underground II, new monsters (templates; sprites
recoloured or new numbers), loot / a boss, and zone + minimap + zone maps.

### ○ Swimming skill
A river south of Aston and a flooded mine quest like Lab 11 (without the darkness).

### ○ Lab 11's third merchant

---

## 6. Quests

### ◐ The quest plan: new areas and quests (Nov 14)
The plan is in the "Quest Map and Plan" doc and the "Quest Planner" sheet (Cody's claude.ai artifacts): 41 town-style
quests in 18 new areas and 3 hub towns (Fenwatch for band C, Stonehold for D, the Last Bastion for E-F), bounty halls,
item rewards (rings, amulets, belts, new potions) and two skill quests (Swimming; Karate on hold, Cody Nov 17: no use for it yet). Left out of questing by Cody:
the towers, the three Pentagram Quests, Black Stronghold, Underground I and II, Elysium, Staffer Corner; each lab counts
as one special quest. Build one area at a time from the bottom, with `tools/world/bandit_hollow/` as the pattern.
- [x] **Bandit Hollow** (east road, Sergeant to Master Sergeant; CHANGES.md "Bandit Hollow").
- [x] **Wolfwood** (Nov 15): Cody built the area, Claude placed Grey Wolves, Dire Wolves (instead of bears, Cody's call), Old Greyfang and Huntmaster Edda with her bounties (sprites and items are ready, CHANGES.md "The Wolfwood: taken out again"). Keep grey and dire wolves apart (a border the monsters can't cross). Was: the game has no four-legged animals but spiders; recolour existing monsters instead, or try one 3D-rendered wolf first (Cody's call). New monster looks otherwise come from `tools/sprites/recolor_creature.py` (sprite 14, base 16336, is NOT a creature: it is a sheet of world objects).
- [x] **Old Quarry** (Nov 15; CHANGES.md "Old Quarry").
- [ ] Rat-Catcher's Cellars and the Old Graveyard (band A extras; the graveyard ties in with the Graveyard quest below).
- [~] **Fenwatch** (band C hub; plan approved by Cody Nov 16, in this order):
  - [x] the town, the Fen Road and the marsh (Nov 16; CHANGES.md "Fenwatch"). Terrain only so far.
  - [x] its people, merchants and waypoint (Nov 16; `place_fenwatch.py`, template numbers in `made.json`): the six quest givers have greetings only, their quests (data 49 / 51 / 66 and the qrew / order lines, as in `rat_cellar/mirela.py`) come with their areas. Cody may add a waypoint picture (Waypoints tab) and change the merchants' stock.
  - [x] the marsh / Wolfwood border blended (`blend_wolfwood.py`). Left as it is: the Wolfwood's dark dirt road turns into the brown path at the border.
  - [x] **Drowned Village** (Nov 16; CHANGES.md "Drowned Village"): terrain, monsters, items, quests and Swimming are live. For Cody to try in game: the under-water loss with and without Swimming, how hard the fights are, the item pictures (the heads and the net are the weakest), Ilse's two hand-ins.
  - [x] **Barrow Hills** (Nov 17; CHANGES.md "Barrow Hills"): terrain with two medium tombs, Barrow Skeletons, pale Barrow Wights, the Scribe, King Ulfgar; Aldous (Torc -> amulet) and Petra (Tablet -> Scholar's Ring). Undead in groups 34/35 heal ~4 hp/s (Cody: the full rate made them too hard). For Cody to try in game.
  - [x] **Lizard Hatcheries** (Nov 17; CHANGES.md "Lizard Hatcheries"): marsh and two caves, usable lizard eggs (Lizard Egg pseudo-bounty, 1 in 5 hatches), Lizard Knights / Archmages, the Broodmother (Nest), the Hatchery Archmage (Grotto); Aldous (Crown -> Scaled Belt), Rook (Phial -> 2 Elixirs of the Good Moon), Corwin (Lizard Head, Lizard Egg). The road to Stonehold runs through. For Cody to try in game.
  - Recolours from sprite 52000 up (50000-51999 used; 48000-49999 is another session's), item pictures from 44533. No gold on item quests (Ulfgar's "and gold" dropped).
- [ ] Then Stonehold, the Last Bastion. **Space and routes (Nov 16; Cody: keep room for every planned area and a route from hub to hub; **approved by Cody Nov 16**; picture `docs/world_space_plan.png`, all boxes checked empty in the live map, x = south, y = east):**
  - Band C: Barrow Hills 320,770 - 405,850 (north gate); Lizard Hatcheries 505,765 - 595,860 (south gate).
  - **Route to Stonehold: south**, out of the Lizard Hatcheries' south side (a through road down its middle, y 800-815, ending in an open gap), a pass 596,800 - 649,815, to Stonehold 650,775 - 715,845. (The north strip above the Barrow Hills is not all free: the Sunken Dark lab is at about x 180-290, y 900-1000.)
  - Band D around Stonehold: Golem Foundry 650,670 - 740,765; Monastery 650,855 - 740,950; Ashen Fields 725,690 - 815,785; Gargoyle Spires 745,845 - 830,940. Elysium (776-822, 795-825) stays where it is, walled off.
  - Pass to the Last Bastion: 716,828 - 834,842 (just east of Elysium). Last Bastion 835,800 - 895,865; band E: Frostfang Peaks 835,690 - 925,790; Barbarian Highlands 835,880 - 925,975; Citadel of Kael 900,795 - 1010,870; Abyssal Rift 930,880 - 1020,975; band F: Shattered Throne 835,590 - 925,685; Heart of the Rift 930,590 - 1020,685.
  - Left free for later: 645,455 - 1020,585; 645,105 - 795,445; the north strip x 130-315, y 755-900. Every hub area is built with its road to the next hub in place, ending in an open gap.
- The new walls 36000-36077 have no cut-down hidden form either (their +1 is the next variant, so hide walls shows a whole wall). The window walls do it right (N+1 = a low slab); the plain ones would need renumbering or a client rule.
- New object sprite sets have no real cut-down "hidden" form: with hide walls on, a new tree shows the next variant
  (the original trees show stumps). Make proper hidden forms some time; run `tools/world/check_hide_sprites.py` after each build.
- Timed potions need no code: armor[1] / attrib[i][1] / skill[n][1] with a duration, like the Agility Potion (Stoneskin, Fireward, Draught of the Void). Still code: Clear Water / Second Wind-style full restores are fine already (end / mana [0]); Elixir of the Good Moon (spell power) and Frozen Heart (regeneration) need some.
- Rewards follow Cody's Quest Planner sheet. Gold (Nov 15, Cody): only bounties pay gold (1/200 of their exp since Nov 17; was 1/20), or a quest whose only reward is gold; quests with an item or skill give none. Bounties: 10 heads = one standard quest (0.5% of the rank's climb a head).

### ● `#quest` list: order and rewards (was #9)
The look is approved and live (column table, 15 a page); the editor's Quests page sets the order, rewards, exp and
hints of every quest. **Order settled** (Cody, Nov 11: happy with the current order). Rewards: Cody changes them there
if he wants (or asks Claude to suggest a plan). Maybe a separate "difficulty" number per quest giver so the
order doesn't have to follow the experience. Keep `#journal` only for temporary / seasonal quests?
Reference for the look: `docs/ref/quest_list_example.png`.

### ○ Graveyard quest (new, Nov 10)
Several undead have come up in the cemetery (the existing graveyard area north of town). The undead should be easier
than Lab 5, maybe with a stunted regeneration. A quest NPC needs skin samples or something to curb the problem. The NPC
could live in Steven's house, with Steven moving across from the Templar Outlaws.

### ● Area clears and class rewards: Cody sets them up
Both built and live (Quests page); Cody adds the areas (quest areas first) and the class rewards when he wants.

---

## 7. MyV2 Editor

### ● Kill quests on the Quests page (Nov 11; built, Cody tries them)
Made and changed on the Quests page, with Cody's criteria (Nov 11): zone, name rules (contains / is / starts with /
templates / any enemy, with exceptions), monster ranks, player ranks, classes, time to finish, wait before again, rewards
that change per turn-in, every giver text; requirements (quest step, skill, item, money, area) that hide the quest until
they fit, and quest steps set on hand-in (so town quest NPCs can give kill quests as part of chain quests). `#kills` in game, say QUEST / YES to the giver (CHANGES.md "Kill quests").
Next: Cody makes the first ones and tries them in game. Ideas if wanted later: rewards by class, kill quests in `#quest` too.

### ○ Area brushes: erase (new, Nov 10)
An area erase, used like the drag-and-drop painting.

### ○ Area brushes: frequency sliders (new, Nov 10)
The floor editor has sliders for how often each tile is used; the area brushes should have the same, inside the editor,
instead of a separate editor.

### ● Flags and zones for the new Aston (Nov 10)
- ~~Editor: clear a type of flag, drag a rectangle to add / remove a flag~~ (DONE Nov 10: Flags tab Add / Remove,
  Brush / Rectangle, Clear in the view / in a zone).
- ~~Zones~~ (DONE Nov 10, see CHANGES "Aston's zones after the move"). Left for Cody: zones for the Grave Keeper's
  house (not decided yet), Joe's gang's new house, Steven's new house and any other new building; then "Re-check
  zones" for the area clears (the Cursed Tomb and Gorn Clan Hall moved), and Claude redraws `docs/world_zones.png`.
- ~~Tile flags~~: grass / street cleared, Market and Joe's house without "no fighting" (DONE Nov 10); Cody fine-tunes
  the rest in the Flags tab. The Market is still mostly "indoors" (not asked to change).
- ~~Guard and Janitor~~ (DONE Nov 10): Guard 7 is the Market guard, the Janitor is back on his loop.
- ~~NPC candle / torch lighting~~ (DONE Nov 10): light duties fixed for the moved NPCs; editor tab "Patrol & chores".

### ○ Editor minimap redraws by itself (new, Nov 10)
The editor's minimap should refresh every so often (it goes stale while the world changes).

---

## 8. Client, sprites and art

### ★ Resizable game window (was #20)
The window already mostly resizes, but the blue background doesn't resize with it, and the spell effects (the spell
icons / effect display) stay where they were instead of following the new size. Make the background fill / scale with
the window and anchor the spell effects. Client change: rebuild with the BuildKit, publish after Cody tests.

### ● World sprites: more ground, water, walls, floors and trees (Cody, Nov 12)
Cody's priority over new characters. Wanted: new ground tiles (dirt paths, desert / sand areas), better-looking water,
more building types, more kinds of stone and brick, more floor types, new trees and plants. Way: build them from the
game's own tiles (same size, angle, light and palette) by recoloring, re-texturing and combining, with the edge /
corner pieces a path or a sand area needs to blend into grass; new sprite numbers; added to the editor's palette (and
area brushes, e.g. a "Desert" or "Dirt path" brush), then published in a client update. Start with a small test set
Cody looks at in game before making the rest.
- **Cody's rules (Nov 12):** every ground / floor kind comes in **4+ variants** so area brushes can randomize them (like
  the 4 grass tiles 551-554), and keep that for everything new. Also wanted: **cactus** sprites (desert), and **cobwebbed
  versions** of existing sprites (walls, corners, furniture...) for abandoned areas.
- **What we know (Nov 12):** floor tiles are 32x32 PNGs, the diamond 32 x 15 at the bottom (rows 17-31). Existing sets:
  grass 551-554, gray dirt 950-958, dark cobble 542-550, light stone / sand-ish 142-145 and 170-175, wood 133-141,
  dark grass 1003-1007, water 16933 / 16957-16959, light blue 16670-16673. Free sprite numbers: the client's limit is
  MAXSPRITE was 2000+32*1024 = 34768; **raised to 65536 in client 2.15.06 (Nov 12, not published yet)**, item sprites
  unsigned on the server. New world sprites from 35000 (numbering plan in HANDOFF.md "Sprite numbers"); keep out of the
  appearance-tier gaps after each character.
- **Edges:** a floor has one sprite per tile, so a soft grass-to-path edge needs whole blended tiles (made by a script:
  a noisy dithered mask along the sides / corners that border the other ground; seamless with the plain tiles). The
  full set per ground pair is up to 47 tiles; the editor would pick the right one by the neighbours (an "auto-edge"
  brush), so Cody only paints "path".
- **Done Nov 13 (in the editor, not published yet):** path, dusty path and clear water, 4 variants each + soft edges the
  editor places by itself (CHANGES.md "New ground"). Cody liked: the grass's own grain recoloured; not: shiny pebbles,
  flat smear, dark clumps. **Desert done Nov 13** (four sands, 7 cacti with black spines, four Desert area brushes).
  **Walls done Nov 13** (8 materials, clean + grain; Cody: no strong grain). **Floors done Nov 13** (7, clean + grain;
  red carpet dropped). Next: doors (below), trees, cobwebs, maybe more
  walls (log cabin, plaster, dungeon brick, carved sandstone); edges between two new grounds (path to sand) if wanted; maybe
  dead / dry cacti, agave, desert shrubs, bones and rocks.
- First mock-up (Nov 12, not in the game): `MyV2\Client\Claude outputs\world_sprites\_test_scene.png` (dirt path,
  desert sand, lighter water on grass, soft edges); scripts in Claude's shell only so far.

### ● Doors for the new walls (Cody, Nov 13) - LIVE Nov 13
Sprites 36500-36581 in `Client\GFX`; templates 1440-1456 in the live world (`tools/world/new_doors.txt`). Players see
them once the new client and sprites are published. Maybe later: grain versions, more styles.
Door sprites that match the new wall materials (sandstone, temple, brick, stone, slate, timber, fieldstone), closed and
open, both facings. Doors are items (templates with the door driver, an open / closed sprite pair), so new doors need new
item templates (world data: stop-send, a world tool, update-world), unlike walls and floors, which are only sprites.

### ○ New character sprites from existing ones (Cody, Nov 12; tabled for now)
Same animations as an existing character (all 448 frames per character), changed look: recolor by area, swapped / added
parts (helmet, cape, another head), effects (ghostly, glowing, rotting, size). Pipeline: `tools/sprites/export_sprites.py`,
Cody's V2 Sprite Recolor Tool, `install_variant.py`; a new block of 448 sprite numbers per character. No new poses.

### ○ Black stone archway: any width, and lighter stone (new, Nov 10)
Lengthen the black stone arch, or add a raised top stone piece so an arch can be any width. Also an arch in a lighter
stone: temple white, or a Greek beige / tan. New sprite numbers.

### ○ New sprite sheets from Blender (new, Nov 10)
Find out what Claude needs from Cody to make new sprite sheets from Blender models (`MyV2\3d Models`): camera angle,
lighting, the 8 directions and frames per animation, sizes, the palette / recolor rules.

---

## 9. Discord and community

### ★ Discord bots and a game chat bridge (was #25)
- **Info for Discord:** who is online, rankings (e.g. top characters by experience / rank, maybe per class), maybe a
  live status message kept up to date (online / player count) instead of new posts. The editor already has the data
  (console `who`, `status`, char.dat) and posts through the webhook (`discord()` in mapedit.py); a webhook can edit its
  own messages, so a status / rankings message can be updated in place without a bot.
- **Game -> Discord:** in-game shouts (`#shout`) posted to a dedicated channel (e.g. #game-chat), probably also
  `#announce`. Server side: log or forward shouts to the editor (console / control port); the editor posts them with a
  second webhook ("Name: text").
- **Discord -> game:** messages written in that channel shown in game (like a shout, e.g. "[Discord] Name: text").
  Needs a real Discord bot (a bot token, the Message Content intent, reading the channel) running next to the editor,
  then a console command that shouts the text in game. To decide: who may write (everyone, or only linked players),
  filtering (badwords.txt), length limits, mutes.

---

## Done

Details in `CHANGES.md`.

- Nov 20-21: chasm/water/ledge/steps pieces and editor tools; band C smoothing and multiple area clears per zone; first kills for every enemy type; trash window + `#trash`; quest rewards at Rare strength (half-Ankh regen on three amulets); Lab 9 questions re-checked; god command `#spellup`.
- Lab 11 arena deaths and the two warning signs (was #1).
- God item shop `#godshop`, merchants in Elysium, Elysium layout (was #2).
- Item tiers parts 1-4: Common to Legendary colours, random drops, soulstone upgrade / reroll (was #3).
- Pentagram enemies leave no grave unless they carry more than their weapon (was #4).
- Pentagram solve balance: 5 + 2-3 per player who activated one in the last 10 minutes (was #5).
- Equipment compare in the tooltip, Shift shows the worn piece (was #6).
- Ice set sprites 18100-18104 (was #7).
- Lab shrine keys: scrolls from the Lord of Seyan'du, 100 gold x lab level (was #8, Nov 6).
- Odd-shaped zones: `.dat/zones.dat`, the editor's Zones tab, `zonereload` (was #10).
- Two-handed sword / greataxe rebalance (was #11, part; the staff, rings and GC following are still open above).
- Area completion bonuses: area clears on the Quests page, `#areas` (was #12, Nov 4).
- Stacking consumables: potions to 20, Ctrl+click, scroll charges (was #14, Nov 4; client 2.15.02).
- Send the Ghost Companion at a chosen enemy: `#gca` / spell bar (was #15; client 2.15.03).
- Fire / Ice set stats and 4 / 6-piece bonuses (was #19, Nov 4).
- Fire / Ice sets as rare drops, destroyed when sold to merchants (was #21, Nov 4).
- Thorns on every landed blow; Cody tested, kept as is (was #22, Nov 4).
- Class rewards on the Quests page and in conversations (was #24, Nov 5).
- Editor view-switch icons redone in the gold-on-wood style.
- Nov 5: Ingrid / Gordon class rewards; Warrior templates start Immunity / Surround Hit at 4; Identify / Light / Recall
  fixed at 250; `{skill}` greetings; several item quests per NPC (`qalias`); Greenling Eye Collection -> Robin
  (quest template 2004); Players page reset / delete (backup) / restore.

- [ ] **Items page: change many at once** (Cody, Nov 16: later). Tick rows (or all shown) and set / add to a field for all of them (+2 damage, min rank 7, price x1.5).
- [ ] **Alchemy skill** (Cody, Nov 16: later). Lizard Eggs (the Hatcheries' nests) are meant to become an Alchemy ingredient (Cody, Nov 17). A new skill (server skill table, client skill names, trainers); recipes and potions can then need it (Needs / Needed already work with any skill).
- [ ] **A bigger world (only if needed)** (Cody, Nov 16): build the hub towns in the free space first (64% of the 1024x1024 map is empty: lower right x 640-1024 / y 450-1024, bottom middle x 128-640 / y 750-1024, right of centre x 640-800 / y 100-450; picture: Client\Claude outputs\world_free_space.png). Enlarging the map means MAPX/MAPY (about 420 uses in the server), NPC spots packed as x+y*1024 (data 10-35), map.dat, the editor and the client: a Fable job, test server first, full backup.
