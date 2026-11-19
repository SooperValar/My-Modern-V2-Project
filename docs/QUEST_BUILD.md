# Quest plan: how to build the next areas (hand-off, Nov 17)

For a fresh chat continuing Cody's quest plan (new areas, monsters, NPCs, quests, rewards, hub towns). Read
`docs/HANDOFF.md` first (tools, rules, server control), then this. `docs/TODO.md` "The quest plan" has the checklist;
`CHANGES.md` describes what is built ("Fenwatch", "Drowned Village", "Bandit Hollow", "Old Quarry"...).
The plan itself: Cody's claude.ai artifacts "Quest Map and Plan" (doc) and "Quest Planner" (sheet: Planned Quests
with exp per quest, Reward Guide, New Areas). Their Status column is not kept up to date: TODO.md is.

---

## 1. Where things stand (Nov 17, afternoon)

| Band | Ranks | Hub | Areas | State |
|---|---|---|---|---|
| A | Private - Corporal | Aston | Rat-Catcher's Cellars; Old Graveyard | cellars live; graveyard not built |
| B | Sergeant - First Sergeant | Aston | Bandit Hollow, Wolfwood, Old Quarry | all live |
| C | Sergeant Major - Captain | **Fenwatch** (live) | Drowned Village, Barrow Hills, Lizard Hatcheries: **all live (Nov 17)** | band C done |
| D | Major - Brigadier General | **Stonehold (next)** | Golem Foundry, Monastery, Ashen Fields, Gargoyle Spires | space reserved |
| E | Major General - Field Marshal | Last Bastion | Frostfang Peaks, Barbarian Highlands, Citadel of Kael, Abyssal Rift | space reserved |
| F | Knight - Warlord | Last Bastion | Shattered Throne, Heart of the Rift (4-step chain) | space reserved |

**Waiting on Cody** (ask, don't guess):
- the redrawn Fisher-King's Belt picture (44531) OK? Redraw the two bounty head pictures (44524, 44525)?
- (Settled Nov 17: one chat from now on. The 48000-48025 wall decorations are finished and published; publishing
  takes everything in `Client\GFX` freely.)
- Drowned Village not yet tried in play by Cody (fights, Swimming under water, the six hand-ins).
- He is rearranging Fenwatch's NPCs in the editor: always find NPCs **by name** (`Area.by_name`), never by old position.

## 2. Cody's rules for this work (all settled; don't re-ask)

- Plan first, show it, wait for OK. **Before saving any new terrain, show a rendered preview** (section 5). He may say
  "I'll build this one": then he draws the area and zones and you place NPCs, items, quests.
- One area at a time: build, test, make live, show the result, then the next.
- **Gold**: only bounties pay gold - **1/200 of their exp** (Cody, Nov 17: 2,500 exp -> 12.5G, about what the monster itself
  carries; was 1/20, far too much against shop prices) - or a quest whose only reward is gold. Item or
  skill quests give no gold. Bounties: 10 heads = one standard quest.
- Exp per quest: the Quest Planner's Planned Quests column H. Reward items take the quest's rank as their rank requirement.
- New items get pictures in the game's style; quest items **value 0** (can't be sold) and **no labyrinth flag**
  (`IF_LABYDESTROY`, 1<<30: items copied from lab items vanish outside a lab). `Area.item` / `quest_item` do both.
- New sprites always get new numbers. 48000-48025 are the wall decorations (done); the next free there is 48026.
  Registry of what is where: HANDOFF.md "Sprite numbers".
- Stops / restarts only with nobody online, gated in the same command (`grep -q '"online": 0' status.json && ...`).
  `tools/world/deploy.sh` does this.
- **Leave a route to the next hub** in every hub area (a through road ending in an open gap, no tree wall across it),
  and keep to the space plan (section 3).
- **No leading "the"** in zone names or monster names (Cody, Nov 18: the zone toggle adds it; "the" in the middle is
  fine). Ask first if a name seems to need it.
- **Clear the old map flags** in every new area's box (Nov 18: the empty space still had the original map's death traps,
  "no fight", arena, bank... tiles): flag bits 5-14 off, then set only what the area needs.
- Swimming: full reduction of the under-water loss at Swimming 125 (live).
- Server code: edit in BOTH `Server\` (Windows) and the project's `server/`, keep them identical (cmp), test on the
  test server first. Commit every change (Cody pushes). After each commit move `.git/HEAD.lock`, `.git/index.lock`,
  `.git/objects/maintenance.lock` aside (`mv` to `.git/staleNNN-...`; no delete permission).
- End every reply with "▶ Do this now" steps.

## 3. The space plan (approved by Cody Nov 16)

Picture: `docs/world_space_plan.png` (column = map y = east, row = map x = south, like the minimap). All boxes were
empty in the live map. **Route: Aston -> east -> Fenwatch -> south through the Lizard Hatcheries -> Stonehold -> south
past Elysium -> Last Bastion.** The Barrow Hills are a dead end off Fenwatch's north gate.

| Area | Box x0,y0 - x1,y1 | Entered from |
|---|---|---|
| Barrow Hills (C, 1st Lieutenant) | 320,770 - 405,850 | Fenwatch north gate (424, 800-802) |
| Lizard Hatcheries (C, Captain) | 505,765 - 595,860 | Fenwatch south gate (476, 800-802); **through road south, y 800-815, open at x 595** |
| pass | 596,800 - 649,815 | |
| Stonehold (D hub) | 650,775 - 715,845 | |
| Golem Foundry / Monastery / Ashen Fields / Gargoyle Spires | 650,670-740,765 / 650,855-740,950 / 725,690-815,785 / 745,845-830,940 | Stonehold |
| pass (east of Elysium 776-822, 795-825, which stays walled off) | 716,828 - 834,842 | |
| Last Bastion (E-F hub) | 835,800 - 895,865 | |
| Frostfang / Barbarian Highlands / Citadel of Kael / Abyssal Rift | 835,690-925,790 / 835,880-925,975 / 900,795-1010,870 / 930,880-1020,975 | Last Bastion |
| Shattered Throne / Heart of the Rift (F) | 835,590-925,685 / 930,590-1020,685 | Last Bastion (Throne sealed until the Rift is done) |
| free for later | 645,455-1020,585; 645,105-795,445; x 130-315, y 755-900 | |

## 4. Numbers in use (check again before making new ones)

- Item templates up to **2082** (2064-2068 Golem Foundry; 2069-2077 Ashen Fields; 2078-2082 Gargoyle Spires) (2024-2032 Drowned Village; 2033-2050 wall decorations; 2051-2054 Barrow Hills;
  2055-2063 Lizard Hatcheries). NPC templates up to **2405** (2361-2405 Gargoyle Spires; 2319-2360 Ashen Fields; 2206-2239 Barrow Hills; 2240-2276 Lizard Hatcheries incl. Cody's 3 knight copies; 2277-2292 Stonehold; 2293-2317 Golem Foundry; 2318 the Sea Hag). `itempnew` / `ctempnew` take the next free number by themselves.
- Monster groups (NPC data 42/44): 30 bandits, 31 quarry golems, 32 deep grolms, 33 wolves, 34 Drowned Village, 35 Barrow Hills, 36 Lizard Hatcheries.
  37 Golem Foundry, 38 Ashen Fields, 39 Gargoyle Spires. **Next: 40.** Undead in a group listed in `SLOW_UNDEAD_GROUP` (`data.h`: 34, 35) regenerate like Lab 11's (~4 hp/s, not ~12):
  add each new undead area's group there (Cody, Nov 17).
- Sprites: monster recolours 41000+ (Quarry Golem), 42100+ (Deep Grolm), 50000+ Drowned Sailor, 50500+ Bog-man,
  51000-51981 Sea Golem, 52000+ Barrow Wight, 53000+ the Broodmother, 54000+ Lizard Hatchling, 55000 Iron Golem, 56000 Forgemaster, 57000 Brass Colossus (96x96), 58000 Sea Hag, 59000 Ash Gargoyle, 60000 the Flame Lord (1.4x: 64x96 frames), 61000 Ashra, 62000 / 62500 Gargoyle Knight / Mage, 63000 Bellkeeper, 63500 Shrike (1.3x): **next free block 64000** (a recolour fills base+0..1023, so step by 1000 to be safe; 500 worked
  for the Undead and Grolm). 3D creatures 43000-44447 (wolves). Item pictures 44500-44555: **next 44556**. Chasm ground 37400-37527. Bell and bell frame 38463-38466. World objects: lizard eggs 38300-38307. Ground: snowy grass 36100-36287, molten iron 36300-36349, ash set 37100-37337 (Ashen Fields; next free 37338; 36350-36399 free, 36400-36409 are the arches). Foundry / workshop objects 38400-38447, Ashen Fields objects 38448-38462, Spires bell 38463-38466 (next 38467).
  Server item drivers: 77 = lizard egg in a nest (`use_lizard_egg`); next free 78.
  World: marsh grounds and edges 35650-35995, reeds 38200-38207. Waypoints: 1-6 used (`next 7` in waypoints.dat).
- Fenwatch NPCs (`tools/world/fenwatch/made.json`): Joss 2142, Ilse 2143, Aldous 2144, Petra 2145, Rook 2146, Bounty
  Master Corwin 2147, Marta (inn) 2148, Odger (store) 2149, Brigit (smith) 2150, guards 2151-2158.
  Joss / Ilse / Corwin already hold quests (Drowned Village); a giver with a quest gets more via `Area.extra_quest`.
  **Aldous, Petra and Rook have greetings only**: their first quest goes on them with `Area.quest`.
- Rank indexes (`me.RANKS`): 8 Sergeant Major, 9 Second Lieutenant, 10 First Lieutenant, 11 Captain, 12 Major,
  13 Lieutenant Colonel, 14 Colonel, 15 Brigadier General, 16 Major General ... 19 Field Marshal, 20 Knight ... 23 Warlord.
- Attribute indexes for rewards: 0 Bravery, 1 Willpower, 2 Intuition, 3 Agility, 4 Strength (the plan's "Intelligence"
  = Intuition). Skills: 9 Perception, 10 Swimming, 1 Karate, 18 Enhance Weapon, 22 Identify, 23 Resistance, 24 Blast,
  28 Regenerate, 30 Meditate, 32 Immunity, 33 Surround Hit, 35 Warcry.

## 5. Tools (all in the project)

**Device shell setup** (each new session; Cody must have added the `MyV2` folder: paths are `$HOME/mnt/MyV2/...`):
- Test server: `mkdir -p ~/ctest/.obj; cp $HOME/mnt/MyV2/Server/{*.c,*.h,*.S,Makefile} ~/ctest/; cd ~/ctest; make -j4 server`
  (run make 2-3 times within the 3-minute limit until `server` exists). Check port 5556 is free before starting a
  test server (`ss -ltn | grep 5556`); start `(./server > out.txt 2>&1 &)`, talk to 127.0.0.1:5556, `pkill -f "^./server"`.
  `./server light > light.txt 2>&1` recomputes lights on `~/ctest/.dat` (redirect: its output is huge).
- A scratch copy of the live world: `mkdir -p ~/fw/x/.dat; for f in $HOME/mnt/MyV2/Server/.dat/*; do [ -f "$f" ] && cp "$f" ~/fw/x/.dat/; done`
  (`Server\.dat` is the world as of the last stop-send).

**`tools/world/arealib.py`** (written by Fable Nov 16; its docstring lists everything): `Area(dat, seed)` wraps the
MyV2 Editor's World class. Map edits (`op`, `run`, `clear`, `house`, `fence`, `place`, `marsh_edges`, `zone`),
templates (`item`, `quest_item`, `worn`, `monster` (scales a copy until it has the rank you name), `person` (a friendly
quest giver)), placing (`spots`, `free`), quests (`quest`, `extra_quest`, `carry`, `by_name`), `save(made, here)`.
**Tried Nov 17 (Barrow Hills)**: `monster` (rank search; `nudge` stays inside the rank; `A.last_pct` holds the
strength it found), `quest`, `worn`, `quest_item`, `spots`, `by_name` all worked as written. `extra_quest` and `person` are still untried. Its code is lifted from the Fenwatch / Drowned Village scripts, which worked, but `monster`'s rank
search, `quest` / `extra_quest` and `worn` have not been run as written. Test each on a scratch copy first and fix
what breaks. The working originals to compare with: `tools/world/drowned_village/place_village.py`,
`tools/world/fenwatch/place_fenwatch.py`.

**`tools/world/render_region.py`** `<Client folder> <.dat> x0 y0 x1 y1 out.png [scale]`: the preview from the real
sprites (fixed Nov 17: magenta keyed out; finds spritesheets.py itself). Use scale 0.4-0.8 for a whole area. NPCs show
only after the server has spawned them (a stop-send copy). To show Cody a picture: copy it to
`Client\Claude outputs\fenwatch_preview\<new name>.png` (always a new file name), `device_stage_files`, `SendUserFile`.

**`tools/world/deploy.sh [--code] script.py ...`** (written by Fable, **never run yet**): stop-send if nobody is
online, run the scripts on `Server\.dat`, relight via `~/ctest`, `get` the code if `--code`, update-world,
reload-editor, then print spawn failures ("Could not drop char N" = an NPC on a blocked or tavern tile). Until it has
been tried once, do the steps by hand as HANDOFF describes and compare. After reload-editor Cody may need the editor's
round "Load the world again from disk" button (the editor won't restart while it has unsaved changes).

**Sprites**: `tools/sprites/recolor_creature.py <Client> <src base> <new base> <ramp>` (ramps in the file: sandstone,
slate, drowned, bog, seagolem; add one per new monster). Source bases: Undead / Lord 19408, Skeleton 10192, Lizard
13264, Grolm 12240, Golem 17360, Gargoyle 18384, Ice Gargoyle 21456, Mage 4048, Ghost 9168. Item pictures:
`tools/sprites/item_icon.py <model.obj|.gltf> <out.png> [--size --yaw --bright --recol Mat=rrggbb --glass --liquid]`
with `MyV2\3d Models\RPG Pack 2\OBJ` (rings Ring1-7, Necklace1-3, Crown, Crown2, Potion*, Scroll, Skull, Bone...) and
`Fantasy Props`; examples in `tools/sprites/quest_items/README.txt` and `drowned_village.py`. A belt: draw it (see
the Fisher-King's Belt in `drowned_village.py`; recolouring the game's thin belt strip looked bad).
Marsh / ground sprites: `tools/sprites/world_marsh.py`, `world_ground.py`.

**Testing quests** (test server console): `questgive <player> <npc template>` hands the NPC its wanted item and prints
exp / gold; `zone <x> <y>`; `wplist`; `merchreload`; `usetest <player> <slot>` drinks a potion; `fighttest`.
Test character on the test server: Iluvatar.

## 6. Fable's potion code: LIVE since Nov 17 (tested on the test server)

Tested Nov 17 (test potions drunk with `usetest`: spell items with temp 65001 / 65002 on the character, no crash) and live
with the Barrow Hills update. The +15% and the Frozen Heart healing are easiest to see in play. What it is:
- **Elixir of the Good Moon** (Rook's reward, Lizard Hatcheries): `has_good_moon(cn)` in `skill_driver.c` is true at
  full moon, or while the character has a spell item with `temp == SPT_GOODMOON` (65001, `data.h`), or wears an item
  with `data[9] == SPT_GOODMOON`. Then spells are +15% and a Bad Moon doesn't weaken them. `spell_race_mod()` now takes
  the caster as a third argument (all 12 calls in skill_driver.c changed).
  **To make the potion**: copy the Stoneskin Potion (2015, a timed potion: driver 0, `duration` 10800 = 10 minutes at
  18 ticks a second), set `duration` 10800, `armor [0, 0]`, `data[1] = 65001` (the spell item's temp; `spell_from_item`
  in skill_driver.c copies it), `data[0]` = the buff icon sprite (0 = the default 93).
- **Ring of the Good Moon** (band F end reward, later): any worn item with `data[9] = 65001` (copy a ring with
  `driver=0`, data cleared, as Mirela's ring in `rat_cellar/mirela.py`). Nothing else reads `data[9]` of a worn
  item (checked: build.c / use_driver.c use it for other items, svr_do.c only for hidden items). The plan says "one per
  player": not enforced yet.
- **Potion of the Frozen Heart** (band E): a timed potion with `data[1] = 65002` (`SPT_FROZENHEART`); while it lasts
  the character regains `FROZEN_REGEN` = 200/1000 hitpoint a tick (3.6 a second) in `svr_do.c`'s regeneration loop.
- **Karate**: taken out again Nov 17 (Cody: no use for it yet). Brother Anselm's Karate quest (band D) waits until Karate
  has a use: then put `|| nr==SK_KARATE` back next to SK_SWIM in `driver.c` `npc_give` (see the comment there).
- **Test plan**: on a scratch copy make the elixir and the frozen-heart potion (arealib `item`), give them to Iluvatar
  (editor World op `padditem`), start the test server, `usetest Iluvatar <slot>`, and check: no crash; the character's
  spells list holds an item with temp 65001 / 65002 (stop the server, read char.dat / item.dat); hitpoints rise while
  Frozen Heart lasts. The +15% itself is easiest to see in play (Cody: cast Bless with and without the elixir).
  Then `update-code` (with `"warn":30`) and note it in CHANGES.md.
- Not needed: Clear Water / Second Wind (full restores: potion `mana`/`end` [0] = 999), Stoneskin / Fireward /
  Draught of the Void (timed potions with `armor[1]` / `skill[n][1]` / `attrib[i][1]`, no code).

## 7. The Barrow Hills: DONE, live Nov 17

CHANGES.md "Barrow Hills". Scripts: `tools/world/barrow_hills/build_barrow.py` (terrain; Cody asked for two medium tombs
with room for a few monsters), `place_barrow.py` (monsters, items, quests; `made.json`). Previews in
`Client\Claude outputs\fenwatch_preview\barrow_*_v5.png`, `barrow_wight_v2.png`. How it went live (deploy.sh still
untried): stop-send, the script on `Server\.dat`, (terrain: `./server light` in `~/ctest`, map.dat back), `get` when the
code changed, update-world, reload-editor, `log` for "Could not drop". **For Cody to try in game**: the fights (wights
now heal ~4 hp/s), the two hand-ins, the item pictures.
Device-shell lesson: the VM disk is small (~10 GB, ~0.7 GB free): every World.save writes a ~140 MB backup in
`.dat/mapedit-backups`; delete scratch copies and their backups as you go.

## 8. The Lizard Hatcheries: DONE, live Nov 17

CHANGES.md "Lizard Hatcheries". Scripts `tools/world/lizard_hatcheries/build_hatcheries.py` (terrain, caves, cave lights,
the egg nests and the Lizard Egg / Hatchling templates -> `made_terrain.json`) and `place_hatcheries.py` (monsters, items,
quests -> `made.json`). Cody's choices on the way: Fenwatch's marsh carried on; lakes kept back from the road; the big cave
set further back (area widened to y 757); the Grotto entered from the north; bosses swapped (Broodmother: big cave,
Archmage: Grotto); eggs: one big egg a tile, fuller nests, a ragged hatched egg; **option 4**: using an egg gives a Lizard Egg
(pseudo-bounty at Corwin: 2,600 exp + 13G; later Alchemy) or 1 in 5 hatches a Lizard Hatchling that attacks; regrow 5 min.
Tested on the test server (spawns, all hand-ins, 20 egg uses: 13 eggs, 5 hatchlings). **For Cody to try in game**.
Later Nov 17: Cody placed 11 more eggs in the editor (32 now; all checked: nest templates, driver 77, room beside each for a
hatchling, each used on the test server); three Hatchery archmages became knights (`fewer_mages.py`; Hatchery: 11 knights,
2 archmages). Eggs placed from templates 2056-2058 work by themselves; painted egg sprites don't. Cody then added 3 more
knights in the editor and called the area **final** (Nov 17, 19:41): 26 Lizard Knights, 5 Lizard Archmages, the Broodmother,
the Hatchery Archmage, 32 eggs; checked: every monster and egg reachable from the road, the copies are group 36 and carry
Lizard Heads, none on no-monster tiles.
Lessons: the egg's two looks are the item's sprite pair (whole / hatched, `active` = regrowing); `usexy <player> <x> <y>`
tests a map item; the device VM disk is small: delete scratch copies and `.dat/mapedit-backups` there as you go.

## 9. Stonehold (band D hub) - planned with Cody Nov 17, **town LIVE Nov 17** (ground, snowy grass, townspeople, trader, guards, waypoint 7)

Quest rows: the Quest Planner's Planned Quests 21-29 (exp there; the Watch bounty's gold is now 1/200 of its exp: 13,000 exp
-> 65G, not the sheet's 650G). Cody's answers (Nov 17):
- **Brother Anselm's first quest** (Abbot's Prayer Beads) gives a **Monk's Wrap** belt (+Agility, +endurance) instead of Karate.
- **A trader with a rotating random stock** of Rare and Epic gear: a couple of pieces of various kinds, changing now and then.
  Needs server code in `merch.c` (e.g. a `rotate` line in merchants.dat: how many, how often, tiers, metals, levels); build it
  on the chests' tier rewards (`npctalk.c` "reward tier", `tier.c`).
- **The look**: a town in a hollow ringed by granite cliffs (the game's pale rock blocks 1204 / 1206), houses backed into the
  rock, a fort wall and gatehouse across the north entrance; the game's own sprites only.
**Terrain** `tools/world/stonehold/build_stonehold.py` (v2 preview `fenwatch_preview\stonehold_v2.png`, `stonehold_town_v2.png`):
the pass x 596-649 (canyon, road y ~806-808 from the Hatcheries' exit), the town x 650-715 / y 775-845: square (682,810, free
for waypoint 7), Watch Barracks, the Granite Hearth (inn), Hagar's Forge, Varo's Temple (669-678 / 831-840, off the east road), Trader's House, two houses, a mine adit;
gates with road stubs ending open: west (681,766) -> Golem Foundry, east (681,854) -> Monastery, south-west (724,784) -> Ashen
Fields, south-east (724,835) -> the pass to the Last Bastion / Gargoyle Spires. No monsters in the pass or town.
**Townspeople live Nov 17** (CHANGES.md "Stonehold"; templates 2277-2292, `made.json`; Selwyn 2282 = merchants.dat `rotate`).
Snowy grass over town and pass (sprites 36100-36287). Snowy pines live (20:11). Selwyn: priced by level + tier (rot_value, sell 200), Steel / Emerald / Crystal / Titanium only (20:35; Cody is tempted to drop
Crystal too: remove bit 16 from the metals field, 58 -> 42). **Next**:  the Foundry, Ashen Fields, Spires; the Monastery last (new monk
sprites, 3D pipeline).

## 9b. The Golem Foundry (Major) - **LIVE Nov 17, 21:53** (CHANGES.md "Golem Foundry")

Quest Planner rows 21-22 + 27 (bounty). Area x 650-740 / y 670-765 (empty void now), west of Stonehold; the road leaves
Stonehold's west gate (681,766) and runs west (-y) into it. Monster group 37 (not undead). Draft:
- Look: an old mountain foundry - a slag-strewn yard with snow (Stonehold's snowy grass), then a great dark stone hall,
  glowing furnaces / fire, the Forgemaster's forge, and a casting pit at the back for the Brass Colossus.
- Monsters: **Iron Golems** (the Golem recoloured dark iron, Major), **the Iron Golem Forgemaster** (boss: Foundry Heart),
  **the Brass Colossus** (bigger boss, brass recolour: Colossus Core). Every golem carries a **Golem Core** (Brann's bounty:
  13,000 exp + 65G each, stacks).
- Quests (Hagar): Foundry Heart -> **Forgefire Ring** (Epic: +Strength, +Enhance) 71,000 exp; Colossus Core -> **Belt of the
  Colossus** (Epic: +hitpoints, +armor) 100,000 exp. Brann: Golem Cores (Gargoyle Horns come with the Spires).
- **Cody's answers (Nov 17, 21:05):** a snowy yard + one big hall; the Brass Colossus in its own casting pit at the back;
  foundry pieces (Cody: anvils, molten iron, nothing modern) drawn in `tools/sprites/world_foundry.py` (DRAFT, not in GFX
  yet): anvil on a log 38400, anvil on a granite block 38402, crucible of molten iron 38404, quench bucket 38406,
  grindstone 38408, iron ingots 38410, casting mould 38412 (no ground glow: Cody), stone furnace 38414, golem wrecks
  38416 / 38418 (each N+1 its hide-walls copy); molten iron ground 36300-36303 (edges into the hall floor to make). 3D props
  from Cody's `3d Models\Fantasy Props` (Anvil, Anvil_Log, Cauldron, Bucket_Metal, Whetstone) and RPG Pack 2 (Gold_Ingots).

## 9d. The Gargoyle Spires (Brigadier General) - **LIVE Nov 19, 07:20** (CHANGES.md "Gargoyle Spires")

**How it went live** (Claude's first stop-send was refused by the safety system; it went through after Cody's "go live"): gated stop-send ->
on `Server\.dat` in this order: `gargoyle_spires/build_spires.py`, `place_spires.py`, `quest_fix/quest_next.py`,
`quest_fix/quest_order.py` -> relight (copy the .dat to `~/ctest/.dat`, `./server light > light.txt`, map.dat back) ->
update-world -> reload-editor -> `log` for "Could not drop" -> `tools/release/publish_client.py` (chasm 37400-37527,
gargoyles 62000-63999, items 44551-44555, bell 38463-38464 and its broken frame 38465-38466; Cody pushes client-dist) -> CHANGES.md "Gargoyle Spires".
Tested on the test server (Nov 19): no spawn failures; zones; questgive Rhea 2279 (+160,000), her second quest (+230,000),
Brann's horns (+16,000 +80G, repeatable) and his cores (unchanged). Template numbers from the test run: items 2078-2082
(horn, clapper, eye, girdle, amulet), NPCs 2361-2405 (29 Knights, 12 Mages, Bellkeeper 2395, Shrike 2399, Rhea's second
quest 2404, Brann's horns 2405); the live run takes the next free numbers again (made.json). Previews `spires_v5_bell.png`,
`spires_v5_eyrie.png`, `spires_gargoyles_v2.png`, `spires_items_v1.png` (fenwatch_preview).


Quest Planner rows 28-29 + 27 (Gargoyle Horns for Brann). Area x 745-830 / y 845-940 (empty void now, checked with a
render); Elysium (776-822 / 795-825) stays walled off. The pass to the Last Bastion (716-834 / 828-842) is not built yet:
the plan builds it now, from Stonehold's south-east gate (724,835) south to an open gap at x 834, with the Spires' gate
off its east side (about 765,843). Monster group 39 (not undead). Draft shown to Cody:
- Look: a wind-scoured summit above Stonehold - snow and granite (Stonehold's / the Ashen Fields' cliffs), five ruined
  stone spires (gargoyle roosts) on rock islands, joined by narrow ridges / causeways with false turns. Zones: Gargoyle
  Spires, Broken Causeway, Bell Spire, Shrike's Eyrie.
- Route: gate -> the Lower Ledges -> Broken Causeway -> **Bell Spire** (centre-east, the Gargoyle Bellkeeper, a cracked
  bronze bell) -> the only bridge on to **Shrike's Eyrie** (far south-east corner, the highest spire). Bellkeeper before Shrike.
- Monsters: the game's Gargoyle Knights and Gargoyle Mages, Brigadier General; every Spires gargoyle carries a Gargoyle
  Horn. **Gargoyle Bellkeeper** (Brigadier General; verdigris-bronze recolour, 62000) with the Spire Bell Clapper;
  **Shrike, the Gargoyle Matriarch** (Major General; the Gargoyle 1.3x, storm-grey with red eyes, 63000) with Shrike's Eye.
- Quests (Commander Rhea, 2279, greeting only so far), rank Brigadier General (15)+, no gold: Spire Bell Clapper ->
  **Warden's Girdle** (Epic belt: +Bravery, +hitpoints) 160,000 exp; Shrike's Eye -> **Shrike's Eye** amulet (Epic:
  +Agility, +Perception) 230,000 exp. Brann: Gargoyle Horns 13,000 exp + 65G each (like the cores); his greeting updated.
- New pictures: item pictures 44551-44555 (horn, clapper, eye, girdle, amulet); objects (cracked bell, gargoyle perch
  statues, wind-carved pinnacles) 38463+. Pole: Brigadier General 60,000 (Cody places it).
- **Cody's answers (Nov 19, 06:44):** chasms ("like you're walking over a chasm"); build the whole pass now; recolours: Claude's
  recommendation (Knights frost-dusted granite, Mages dark slate with a pale blue glow, Bellkeeper verdigris bronze, Shrike
  storm-grey 1.3x red eyes; blocks 62000 / 62500 / 63000 / 63500, a gargoyle recolour fills base+0..447) - shown, his OK pending.
- **Chasm ground** `tools/sprites/world_chasm.py` -> 37400-37527 (in `Client\GFX`, not published): 37400 + 4*mask + variant,
  mask = solid ground at x-1 (1), y+1 (2), x-1,y+1 (4), x-2,y+1 (8), x-1,y+2 (16): each pixel looks "up the screen" for
  the nearest land and draws its cliff wall (snow lip, granite, dark with depth) or the misty drop. Chasm tiles get flag bit 0.
- **Cody (Nov 19, 06:56): more spread out, more to the north, the two goals far apart** -> v4: box widened north to x 742
  (the Monastery box ends at 740), a thinner rim, 18 islands: the **Bell Spire at the north end** (755,927), reached by the north
  branch (ledges - n1 - n2 - n3 - n4 - bell), **Shrike's Eyrie at the south end** (815,929) by the south branch (ledges - s1 - s3 -
  s4 - s5 - s6 - s7 - eyrie, the only way in); a middle loop (s3 - m1 - n3) and dead ends (s2, m3, n hook); three broken
  bridges (m2 - bell, s6 - m2, n hook - m2) as false turns. Checked: every walkable tile reachable from the gate with straight
  steps (the script opens closed pockets itself); about 110 steps to the Bell Spire, 170 to the Eyrie.
- **Terrain** `tools/world/gargoyle_spires/build_spires.py` (preview v4 `fenwatch_preview\spires_v4.png`, `_bell`, `_eyrie`; earlier v2,
  run on a scratch copy only, NOT live): Bastion Road (726-834, 828-844, no-monster flag, road ends open at x 834, gate
  to the Spires at 764-767 / 843-848); nine rock islands (ledges, north spire, junction, south pocket, west spire, bell,
  ...: replaced by the v4 layout above), snow ridges and flagstone bridges, ~25 lone pillars in the gorge, a granite rim round the box. Zones:
  Bastion Road, Gargoyle Spires, Broken Causeway, Bell Spire, Shrike's Eyrie. Still to draw: the cracked bell, perch statues.

## 9c. Exploration points ("poles"): the standard values (Cody, Nov 18 - FINAL; Cody places them himself)

One pole per large area off a town. Value by the area's **average monster rank** (the editor's area-clear average),
fitted to the game's own poles (the Labyrinth gorges sit on it: Grolm 5k Sergeant, Undead 20k Sergeant Major, Light&Dark
25k Second Lieutenant, Seasons 45k Lieutenant Colonel, Sunken Dark 50k Colonel, Tower XX 90k General). A pole pays
value x 0.5-1.5 (+ up to 10%), never more than 10% of the player's total exp (use_driver.c explorer_point).

| Rank | Value | Rank | Value | Rank | Value |
|---|---|---|---|---|---|
| Private | 250 | Sergeant Major | 20,000 | Major General | 70,000 |
| Private First Class | 500 | Second Lieutenant | 25,000 | Lieutenant General | 80,000 |
| Lance Corporal | 1,000 | First Lieutenant | 30,000 | General | 90,000 |
| Corporal | 2,500 | Captain | 35,000 | Field Marshal | 100,000 |
| Sergeant | 5,000 | Major | 40,000 | Knight | 125,000 |
| Staff Sergeant | 8,000 | Lieutenant Colonel | 45,000 | Baron | 150,000 |
| Master Sergeant | 12,000 | Colonel | 50,000 | Earl | 175,000 |
| First Sergeant | 15,000 | Brigadier General | 60,000 | Warlord | 200,000 |

**Nov 18 (Cody): poles below the table were raised to it, none lowered** - 34 poles, each by the average rank of the
monsters within 12 tiles (or its zone's): Bandit Cave 2.5k -> 5k, Dire Wolves Den 7k -> 12k, Deep Quarry 6k -> 15k,
Strange Forest 500 -> 12k (x3), Tower VIII 10k -> 40k, Lizard Temple 25k -> 40k, Gargoyle's Nest (7) 8-50k -> 45-100k,
Labyrinth Grolm (2) / Lizard (3) / Light&Dark (1) / Forest (3) / Water (2) gorges, Underground I (3) and II (4), Thieves
Basement. Left alone: the Pentagram Quest's poles (they climb with the pentagram levels, 1k-40k), the Riddle Gorge, the
Ice / Underwater pentagrams, and any above the table (e.g. the Haunted Castle 8k at Corporal).

## 10. After band D

Stonehold (a mountain mining town: Hagar, Anselm, Varo, Rhea, the Stonehold Watch bounty), then its four areas, then
the pass and the Last Bastion. Each as above: plan from the Quest Planner rows -> Cody's OK -> preview -> build ->
test -> live. New monster looks needed from band D on: monk sprites (Monastery), frost giant, rift-spawn, guardian
and two bosses (bands E-F): recolours where they will do, else the 3D pipeline (`tools/sprites/make_creature.py`,
models in `MyV2\3d Models`; HANDOFF "wolf"). Code still to write later: Fireward / Draught of the Void need none
(timed potions); "one Ring of the Good Moon per player" if wanted.
