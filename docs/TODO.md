# MyV2: design ideas and to-do

The one list of everything still to do or decide for Mercenaries of Asgard v2: fixes, systems, classes, items,
world, quests, the editor, the client and Discord. Merged Nov 10 from the old TODO list and Cody's
`Design Document.txt` (MyV2 folder). New ideas go straight in here, under their section.

- **Priority:** ★ **Next** (in the queue below) · ● **Soon** (decided, not started) · ○ **Idea** (not decided yet)
- **(was #n)** = the item's number in the old numbered list; `CHANGES.md`, `HANDOFF.md` and old commits use those numbers.
- Finished work moves to **Done** at the bottom (one line each; the details are in `CHANGES.md`).

---

## Up next (in order)

0. ★ **Waypoints: push client-dist, then the last server update (sound, CLIENT_LATEST)** - [Systems](#2-gameplay-systems)
1. ★ **Soulstone levels too low** (MAJOR) - [Fixes](#1-fixes-and-balance)
2. ★ **Discord: online / rankings info and the game chat bridge** - [Discord](#9-discord-and-community)
3. ★ **Walking speed, speed modes and attack speed** (look at it together first) - [Systems](#2-gameplay-systems)
4. ★ **Town NPCs' door loop** - [Fixes](#1-fixes-and-balance)
5. ★ **Logout at shutdown** - [Fixes](#1-fixes-and-balance)
6. ★ **Resizable game window** - [Client](#8-client-sprites-and-art)

**Waiting on Cody:**
- Town leftovers: Re-check zones for the area clears, if not done yet ([World](#5-world-and-areas)). (Zones for the new buildings and Steven's house: done, Cody Nov 11.)
- The Windows restart test of start-with-Windows (Discord #server-status shows if the server came back by itself).
- Quest rewards on the editor's Quests page, if he wants changes ([Quests](#6-quests)). (Order: Cody is happy with it, Nov 11.)
- Checking the merchants in game: pages, selling + buying back, prices ([Items](#4-items-weapons-and-shops)).
- Setting up the area clears (quest areas first) and the class rewards, when he wants.
- Waypoints: `git push origin client-dist`, then "go" for the update; listen to the travel sound ([Systems](#2-gameplay-systems)).

---

## 1. Fixes and balance

### ★ Soulstone levels too low (MAJOR) (was #28)
Cody: "I'm getting level 6 armors dropping but only level 2 soul stones."
Now (`tier.c` ~419, `soul_kill_drop`): a stone drops in 1 of (20 + 6 x the player's rank) kills; it holds 10-15% of the
enemy's experience value and its level comes from that exp, so ordinary monsters give low-level stones while armor
levels follow a different scale. Strong monsters carry their own stone (same 10-15% rule, `tier_make_soulstone`).
To do: compare the stone level formula with the armor item-level formula (`docs/ITEM_TIERS.md`), make stones match the
level of armor that drops in the same area (e.g. stone level = the enemy's armor drop level, or a higher exp share),
maybe raise the drop rate for high ranks.

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
After more testing.

---

## 2. Gameplay systems

### ★ Walking speed, the three speed modes and attack speed (was #26)
Cody wants changes here; look at it together first. How it works now: one speed value is used for every action,
walking AND attacking (`ch[].speed`, set in `really_update_char`, `svr_do.c` ~4007):
n = (Agility + Strength) / 50 + speed_mod (items / spells) + 12 slow / 14 normal / 16 fast, speed = 20 - n
(0 fastest .. 19 slowest), so the speed buttons and Agi + Str change walking and attacking alike. Each animation step
waits on `speedtab[speed][ctick]` (`svr_act.c` ~1079, `speedo` / `ch_act_speed`; the greataxe once added `AXE2H_SLOW`).
The modes also cost endurance (fast drains it, `svr_do.c` ~4120-4137) and change Stealth (slow / normal sneak better,
`svr_do.c` ~3710). To decide: separate walk and attack speed, how much stats should matter, what the modes cost / give.

### ★ Waypoints (was #13): live; one server update left
Live Nov 12 and tested by Cody (finding, the travel window, travel, his own pictures by paste). Client 2.15.05 published
Nov 12 (client-dist 0633098: travel window, night glow of found circles, circle sprites, `sfx\19.wav`, the pictures of
waypoints 1-5). CHANGES.md "Waypoints", "Waypoints tab".
**Left:**
- Cody pushes `client-dist`, THEN says "go" for an update-code: it brings the travel sound (`waypoint.c`) and
  `CLIENT_LATEST` 0x020F05 (both already in the source, both copies). Not before the push, or players are told to
  update to a client that isn't out yet.
- Cody listens to the travel sound (Claude made `19.wav` without being able to hear it) and looks at the night glow
  and the stronger grey circle.
- New waypoint pictures need a client publish each time (until then: the stock picture).
- The old **Clan Pentagram** (item 7495 at 469,523, template 587; also template 570; sprite 761, the green 760 and red
  762 are unused) still runs the Lab 13 portal check when stepped on (its driver number 38 was reused): remove it or
  make that spot a waypoint. Cody decides.

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
