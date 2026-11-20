# Handoff: how this project fits together

Read this first in a new chat. It says where everything is, how each part is changed and put
live, Cody's standing rules, and what is still open. The full list of what was changed is in
`CHANGES.md`; the open items and design ideas in `docs/TODO.md` (by category) and `docs/HOSTING.md`.

**Starting a new chat:** Cody can paste:
> Read `docs/HANDOFF.md` in my project (Client\Claude outputs\My-Modern-V2-Project) first, then `docs/TODO.md`. Then: <the task>.

---

## The project

Mercenaries of Astonia v2 (2000-2001), restored and modernized by Cody ("MyV2"):
a modern Windows client, a 64-bit Linux server, new content (Labs 10 and 11, tiered armor,
two-handed axes, quests, chests...), and the MyV2 Editor (a map / NPC / quest / player editor
in the browser that can edit the running game live).

## Where things are (Cody's PC, Windows)

| What | Where |
|---|---|
| Live game server (runs here) | Ubuntu in WSL, home folder `/home/cody` (`~`): `./server`, sources, `.dat/` (world data) |
| Windows copy of the server source (Claude edits this) | `C:\Users\Cody\Desktop\MyV2\Server` (= `$HOME/mnt/MyV2/Server` in Claude's device shell when Cody adds the whole `MyV2` folder, which is the easy way: one "Add folder" covers Server, Client and the project; `$HOME/mnt/Server` if he adds it alone) |
| Client (what Cody plays) | `C:\Users\Cody\Desktop\MyV2\Client` (`merc.exe`, `Launcher.exe`, `GFX\`, `sfx\`, `gx00.*`, `pnglib.*`) |
| Git project (GitHub, public) | `C:\Users\Cody\Desktop\MyV2\Client\Claude outputs\My-Modern-V2-Project` = github.com/SooperValar/My-Modern-V2-Project |
| Player download | `Client\For Players\Mercenaries-of-Asgard-v2.zip` (rebuilt by `publish_client.py`); public link: the GitHub release, see HOSTING.md |

Project layout: `server/` (server source, the same files as the Windows Server folder),
`client/` (client source; `client/launcher/` the launcher; `client/package/README.txt` the player
readme), `tools/mapedit/` (the editor), `tools/release/` (publishing client updates),
`tools/sprites/` (sprite scripts and art), `tools/world/` (one-off world data tools),
`docs/` (TODO, HOSTING, ITEM_TIERS, this file).

Note: the real client source is the project's `client/` folder (the old copies in `Client` were moved out Nov 7).

## Cody's standing rules

- Always end with clear **"▶ Do this now"** steps.
- **Delete old files on your own** (Cody, Nov 17): superseded previews, scratch files, stale git locks. At the start of a
  session ask once for delete permission on the `MyV2` folder (`device_request_delete_permission`), then `rm` instead of
  moving files aside (git's `.lock` / `tmp_obj_*` leftovers included). Don't ask Cody to delete things.
- **Keep the hand-off documents current as we go** (this file, `docs/TODO.md`, `CHANGES.md`): Cody starts a new chat
  only about once a week, so every session should leave them complete enough for a cold start.
- `CHANGES.md` describes the game as it is now, in the section where a thing belongs (player features, Editor,
  Server console, Data changes, Tools), not as a diary: when something changes, update the old lines too. Use today's
  names everywhere (Greataxe, Intuition, Ice Gargoyle Cape); an original game item that was renamed gets "(Previously: Ice Cloak)".
- Keep `CHANGES.md` up to date with every change; commit every change (in the project folder);
  remind Cody to `git push` (Claude doesn't push).
- **Server source is changed in BOTH places and kept identical**: the Windows Server folder and
  the project's `server/`. Never copy a whole file over the other blindly; edit, then copy the
  edited file across and check they match (md5).
- **Restarts and code updates are pre-approved (Cody, Nov 14):** the server has no regular players and is almost
  always empty, so stop / restart / update-code / update-world whenever the work needs it, without asking first.
  Still check `who` first and use `"warn":30` if anyone is online. (Was: ask before every stop and wait for "go".)
- New sprites get **new numbers**; never replace the game's own sprites (fixing one of Claude's
  own in place is OK).
- Directions follow the minimap: north = smaller x, west = smaller y. On screen: larger x is
  down-right (south), larger y is up-right (east).
- Keep the world minimap and zone maps current when the map changes.
- Don't paste artifact URLs.
- Editing the live game's data directly from a browser tab (POST `/api/edit` via a browser tool)
  was refused by the safety system: don't; ask Cody to do such edits in the editor himself.
  This is only about the browser route: Claude DOES change live world data (templates, NPCs, npctalk.dat, zones...)
  through the control files and world tools (stop-send / tools / update-world), (stops are pre-approved, see above).

## Running and updating the server

- Cody starts Ubuntu, then the editor: `python3 /mnt/c/Users/Cody/Desktop/MyV2/Server/mapedit.py`.
  It opens at **http://localhost:8090** (8080 is reserved by Windows since WSL mirrored
  networking; the editor picks the first free port of 8080, 8090-8099 by itself).
- The editor's **Server** page starts / stops / restarts the game (`./server loop` restarts after
  a crash; output to `server.log`).
- **Claude controls it through files**: write `{"id":"<unique>","action":"<action>"}` into
  `Server\control\requests\<id>.json`; the answer appears in `Server\control\responses\`.
  Actions: `status`, `console` (+`"cmd"`), `log`, `start`, `stop`, `restart`,
  `update-code` (+`"warn":30`), `update-world`, `send`, `stop-send`, `get`, `get-world`,
  `reload-editor`. `control\status.json` is kept current.
- **Server code update**: edit the source in both places, then
  `{"action":"update-code","warn":30}`: warns players, stops, `claude-sync.sh get` (copies the
  changed Windows source into Ubuntu with a backup in `~/claude-backups/`, then `make`), starts.
- Console commands (control port 127.0.0.1:5556, or the editor's console): `who`, `status`,
  `announce`, `tell`, `kick`, `raise`, `lower`, `gold`, `quest`, `talkreload`, `talktest`,
  `talkkill`, `talkuse`, `talknear`, `talkmoney`, `zonereload`, `zone <x> <y>`, `chesttest <player> <x> <y> [real]`, `kqkill <player> <NPC template>`, `kills <player>`, `kqtime <player> <minutes>`, `edpatch`, `wear <player> <template>|off`, `fighttest <player> <NPC template> <rounds> [back|kill]` (test server only), `merchreload`, `shop <player> <merchant template> [buy|sell|page|leave]`, `recipereload`, `recipetest <player> <used slot> <held slot>`.
- **Test server** (for trying server changes without touching the live game): in Claude's device
  shell, `~/ctest` holds a copy of the server source and data. Copy the changed files there,
  `make server` (a full build may need two runs within the 3-minute limit). **Always check port
  5556 is free first** (`ss -ltn | grep 5556`) so the live server is never hit. Start it with
  `(./server > out.txt 2>&1 &)`, talk to it on 5556, kill it at the end (`pkill -f "^./server"`).
  Background processes die when the shell call ends.

## Changing the world data (item / NPC templates, merchant stock)

The live world is in Ubuntu (`~/.dat`); `Server\.dat` on Windows is only a copy (may be old). For a template change:
1. `{"action":"stop-send"}` (the game stops; pre-approved) - the current world is copied to `Server\.dat`.
2. In Claude's device shell: build `tools/world/build_lab.c` (`gcc -I server`) and run it on `$HOME/mnt/Server/.dat`
   with the spec (`tools/world/*.txt`).
3. `{"action":"get"}` if the code changed too (rebuild, no start), then `{"action":"update-world"}` (takes the world from
   Windows, starts the game), then `{"action":"reload-editor"}`.
New sprites: write them to `Client\GFX` (new numbers), then `tools/release/publish_client.py`; Cody pushes `client-dist`.

More world tools (Nov 10, all in `tools/world/`, build with `gcc -I server`, run on `$HOME/mnt/Server/.dat` with the game
stopped via `stop-send`, then `update-world` and `reload-editor`):
- `town_apply.c`: copy changed tiles and their items from one place to another (spec: `offset`, `tile`, `tiledata`,
  `itemdata`); `town_rearrange/` has the Nov 10 specs.
- `mapflags.c`: set / clear map flag bits on a list of tiles. **`struct map` is 28 bytes** (sprite, fsprite, ch, to_ch,
  it, dlight, light, flags u64): never write map.dat with a hand-made record layout (a 24-byte numpy dtype once
  scrambled it; caught and restored with `send`).
- `npcdata.c`: `chd <temp> <i> <value>` / `cht <temp> <i> <text>` set data / text of a template AND its living NPCs.
- `npc_lights.c`: lists every NPC's light duties (data 32-35) and whether a light is still on each spot.
- After changing indoors flags or lights, run `./server light` on a copy of the .dat (test server folder `~/ctest`)
  and copy map.dat back.
- NPC data that holds map spots: 10-18 patrol, 20-23 doors it closes, 29 resting spot, 32-35 lights it keeps burning,
  41 street light kind it switches. The editor's NPC page "Patrol & chores" tab sets them.
- Placing a template with the editor's NPC brush makes a NEW template per placed NPC (the copies get the next free
  numbers, e.g. Garrett 2008 -> placed as 2012): anything keyed by template number (merchants.dat) must use the
  placed one.
- Zones: `.dat/zones.dat` can be written while the game is stopped (send, edit, get-world, reload-editor); the editor
  holds them in memory, so reload it, and ask Cody first whether he has unsaved editor changes.

## The MyV2 Editor

- Runs as one file, `mapedit.py` (in the Server folder; a copy in `tools/mapedit/`).
- **Its source is two files** in `tools/mapedit/src/`: `mapedit_template.py` (the program, with the
  marker `@@PAGE@@`) and `mapedit.html` (the web page). Edit those, run
  `python3 tools/mapedit/src/pack.py`, copy the resulting `tools/mapedit/mapedit.py` to the Server
  folder, send `{"action":"reload-editor"}`, and Cody presses F5.
- Test it before deploying: run it on a copy of the data (`--dat <folder> --port <n>`) and use
  Playwright (installed in Claude's cloud workspace) for the page.
- Live editing: while the game runs, edits go into it as patch files (`edpatch`, checked against
  what the server has, all or nothing). With the server stopped, "Save to the game" writes the files.
- **Quests page** reward rules live in `npctalk.dat` too: `qreward` / `qstage` (gold, times, rewards per turn-in),
  `qrank` (lowest / highest rank); per-player counts in `.dat/questcount.dat`. Console `questgive <player> <template>`
  tests a hand-in. **Area clears** (Quests page, `#areas`): `clear` / `clearlabel` / `clearnpc` lines in `npctalk.dat`,
  progress in `.dat/clears.dat`, console `cleartest`. **Rugs** (Floors tab): `.dat/mapedit-rugs.json`; the Red and Blue rug are built in.
- **Kill quests** (Quests page, second box; Nov 11): `kq*` lines in `npctalk.dat` (listed at the top of `npctalk.c`),
  progress in `.dat/killquests.dat`, players `#kills`, say QUEST / YES to the giver; console `kqkill`, `kills`, `kqtime`.
- **Quests page** (rail: Quests): every item quest (`#quest`: wants / teaches / gives / exp / hint / order) and chain quest
  (`#journal`: names, journal steps, which NPCs use them) on one page. The `#quest` order is kept in `npctalk.dat` as
  `order <template> <place>` (-1 = not listed).
- **Zones** (zone names) are kept in `.dat/zones.dat` (`x1 y1 x2 y2 flag name`, one box a line; boxes with the same
  name are one zone), drawn in the editor's Zones tab; the game reloads them live (`zonereload`). Without the file the
  server uses the built-in table in `area.c`. `tools/world/worldzones.py` draws `docs/world_zones.png/.md` from it.
- Area brushes are kept in `.dat/mapedit-areas.json`; NPC dialogue, quests and chests in
  `.dat/npctalk.dat` (`quest.dat`, `chestlog.dat` beside it).

## The client and the launcher

- Source: `client/` (Visual Studio C, GDI). **Claude builds `merc.exe` itself with the BuildKit**:
  `Client\BuildKit\myv2-buildkit.tar.gz` (Microsoft's Windows SDK / MSVC files + `build_client.sh`; read
  `Client\BuildKit\README.txt` first). **Private: never add it to git, never publish it, never copy it into the
  project folder** (Microsoft's files may not be redistributed). Build in the cloud workspace (the PC's Linux shell has
  no compiler, and the cloud can't download the SDK): stage the tarball and every file of the project's `client\`,
  `tar xzf`, `apt-get install -y clang lld llvm` if missing, **`ln -sfn <unpacked>/myv2-buildkit/sdk /home/claude/sdk`**
  (the kit's lowercase header names are links into /home/claude/sdk; without it: "windows.h not found"),
  `bash myv2-buildkit/build_client.sh <source folder>`,
  then SendUserFile the merc.exe and commit it by fileUuid to `Client\merc_new.exe`; Cody swaps it in with the
  game closed. On Windows, `client\build.bat` (Visual Studio "Desktop development with C++") does the same.
- The client reads `client.ini`: `[server] host=` / `port=` (built-in default
  `myv2astonia.duckdns.org`, 5555; `-h` / `-p` on the command line win: `play.bat` uses
  `-h 127.0.0.1`), `[display]`, `[window_v2]`, `[update] base=` / `off=1` (launcher).
- **Launcher.exe** (`client/launcher/`, build with `build_launcher.bat` on Windows): reads
  `manifest.txt` from the `client-dist` branch on GitHub, downloads what changed (SHA-256),
  updates itself, starts `merc.exe`. Never touches `merc.dat`, `client.ini`, `*.moa`.
- **Publishing a client update** (new `merc.exe`, sprites, sounds, the readme):
  `python3 tools/release/publish_client.py <Client folder> <project folder> "<version>"`, then
  Cody runs `git push origin client-dist`. Players get it at their next launcher start (GitHub's
  cache: a few minutes). `gx00.dat/.idx` are "base" files that only come with the zip.
- The server refuses clients older than `MINVERSION` (`server/gendefs.h`); raise it with the
  client's `VERSION` only when a change must be in place before playing.
- New sprites are just PNGs in the client's `GFX\` folder (`NNNNN.png`); publish them.

## Hosting (done, see docs/HOSTING.md)

- AT&T gateway (192.168.1.254): the PC is fixed at 192.168.1.197; TCP 5555 forwarded
  ("Astonia"). Never forward 5556 (console) or 8080/8090 (editor); they only listen on 127.0.0.1.
- WSL mirrored networking (`%USERPROFILE%\.wslconfig`), Windows Firewall rules "Astonia server
  5555" and the Hyper-V rule "AstoniaWSL".
- Server name **myv2astonia.duckdns.org**, kept current by the Windows scheduled task
  "DuckDNS myv2astonia" (`%USERPROFILE%\duckdns\`; the token stays there, never in the project).
- Tested from outside (laptop on a phone hotspot) and the launcher's update path (version 1 -> 2).

## Sprite numbers (Nov 12)
Taken since (Nov 15-19): 37400-37527 chasm ground (Spires); 62000 / 62500 / 63000 / 63500 Spires gargoyles (next 64000); item pictures 44551-44555 (next 44556); bell 38463-38464, bell frame 38465-38466 (next object 38467); 43000-44001 wolves (3D, own shadow); 44500-44541 heads and quest items (next 44542); 38300-38307 lizard eggs (world objects); 48000-48025 wall
decorations; 50000+ recoloured monsters (Drowned Sailor 50000, Bog-man 50500, Sea Golem 51000, Barrow Wight 52000, Broodmother 53000, Lizard Hatchling 54000; next 55000). Check
`Client\GFX` before taking a number.

Client 2.15.06 shows sprites 0-65,535 (before: up to 34,767). Free for new sprites: 34,192 and up. Not free: the gaps
after each character's 448 frames (appearance tiers, `install_variant.py`, `LOOKTIER_STEP`). Plan for new world sprites
(TODO "World sprites"): ground 35000+ (marsh grounds 35700-35995), water 35500+, walls / brick / stone 36000+, floors 37000+, trees / plants /
cactus 38000+, cobwebbed versions 39000+; more blocks above 40000 when needed. Every ground / floor kind in 4+ variants.
New sprites above 34,767 need client 2.15.06 or later: raise `MINVERSION` when the first ones go into the world.

## Known quirks

- `server/lab9.c` and `lab9.h` differ from the Windows Server copies only in line endings (CRLF there, LF in git since
  the original import); an md5 check flags them, `diff --strip-trailing-cr` shows they match. Not a real difference.

- **Deleting files in Cody's folders** needs his approval (a permission prompt), and the approval
  has dropped by itself during a session. Git then can't remove its own lock files: after a commit,
  move any `.git/*.lock` and `.git/objects/maintenance.lock` aside (e.g. to `.git/stale-...`) so
  the next git command works; Cody can delete the `stale-*` files later.
- When committing a file to Cody's PC, use the `fileUuid` from sending it first; committing by a
  staged path once sent an old copy.
- `merc.exe` can't be replaced while the game is open.
- **Sounds** (`Client\sfx\N.wav`): the client reads them raw after a 44-byte header, 8-bit stereo 22050 Hz. A wav sent to Cody's PC
  through the chat (SendUserFile + commit) arrives with extra chunks added (a `LIST` before the data, a `C2PA` block after it),
  which the game would play as noise: rewrite it on the PC with Python's `wave` module (read the frames, write a plain file) and
  check its size is 44 + the data.

## Open items (details in docs/TODO.md and docs/HOSTING.md)

**Nov 13, evening:** new doors live (templates 1440-1456, Seyan'Du Door other facing 1456); the server with unsigned
item sprites is live too. World sprites so far (all in `Client\GFX`, NOT published yet): grounds + desert 35000-35549,
walls 36000-36077, doors 36500-36581, floors 37000-37067, cacti 38000-38006, trees 38100-38167, cobwebs 39000-39421 (all published; door templates 1460-1484 live, tools/world/cobweb_doors.txt) and snow ground 35400-35499 + 35600-35649 (published Nov 14), arches 36400-36409 (v2 + smooth; saved copies in tools/sprites/art/arches_v2, arches_light; published Nov 14) (CHANGES.md "New ground (world sprites)").
PUBLISHED Nov 14 (latest): client-dist 4544755 (2.15.06 + arches, trees, snow, cobwebs I + II; Cody pushes `client-dist`). Before: 03db219 (arches). Before: Nov 13 late: client-dist 185dc94 (client 2.15.06 + 511 world sprites; Cody pushes `client-dist`);
`MINVERSION` and `CLIENT_LATEST` 0x020F06 in both server folders (live after the next update-code).

**Nov 13:** new ground with soft edges (path, dusty path, clear water; sprites 35000+ in `Client\GFX`, editor Floors tab,
auto edges; CHANGES.md "New ground"). Cody plays with client 2.15.06 via `play.bat` (Launcher.exe would put the published
2.15.05 back). Publishing waits until the world sprites are further along.

**Nov 12, late:** client 2.15.06 (sprite numbers up to 65,535) built: `Client\merc_new.exe`, NOT published (Cody publishes
everything together with the new world sprites, before players get the game). Server side (unsigned item sprites) in
both server folders, live since Nov 13 (with the doors). World sprites:
first mock-up only (TODO "World sprites").

**Nov 12: waypoints are done and live** (tested by Cody; client 2.15.05 published and pushed, client-dist 0633098;
travel sound and `CLIENT_LATEST` 0x020F05 live since the evening update). Cody has five waypoints. The travel sound is the whoosh Cody picked (republished Nov 12, late); glow and the old Clan Pentagram stay as they are. Pieces: server `waypoint.c`, client travel window +
night glow (`WP_GLOW` in `hud.h`), editor Waypoints tab (the game lays the circles itself from `.dat/waypoints.dat`;
pictures by pasted screenshot), sprites 18300-18341 + 18401.. (pictures), `sfx\19.wav` (synthesized in Python, Claude
can't hear it). Console: `wpreload`, `wplist`, `wpfound`, `wpuse`. Details: TODO.md "Waypoints", CHANGES.md "Waypoints".
A test server can be built in Claude's device shell (`~/ctest`, gcc is there); it is gone with each new session.
Claude's own request for the Server / Client folders was refused automatically: Cody adds the `MyV2` folder with
"Add folder". `Client\merc_2.15.04.exe` is the client before waypoints.

**Nov 11:** kill quests built (Quests page box, server `npctalk.c` "kill quests", `#kills`); see CHANGES.md "Kill quests".
Cody makes the first ones and tries them.

**Restarts (Nov 15, after two slips):** a restart is pre-approved only while nobody is online: gate it in the same command, `grep -q '"online": 0' status.json && echo '{...stop-send...}' > requests/x.json`, and if someone is on (often Cody testing), ask first.

**Settled by Cody (Nov 16), don't raise again:** the exp / reward balance suggestions (Old Greyfang, Thieves Basement, Lizard Temple, Dungeon of Doors) are done; Azrael stays unticked in the Haunted Castle area clear on purpose (not a normal monster, not reached the normal way).

**Nov 16, later:** editor Items page (every item template; edits reach carried copies), drinks' Stats tab, Value price table, and **recipes** (server/recipe.c, `.dat/recipes.dat`, Items page -> Recipes; live). Test server for this session was `~/sb` (Iluvatar got test items there only).

**One chat from Nov 17 on** (Cody): the world-building (Fable) chat and the editor / sprites chat are merged into this
project's next session. What the second chat did Nov 15-17 (all live, CHANGES.md has the details):
- **Editor**: the **Items** page (every item template: search, kind filter, sort, Copy..., + New item; template edits reach
  copies on the map, with NPCs and with players), **Items -> Recipes** (`server/recipe.c`, `.dat/recipes.dat`: A used +
  B held -> result; keep A/B, either way, min rank, needs a skill/attribute; the game's 69 built-in combinations - flasks
  and flowers, Lizard's Teeth, rings and gems, the Amulet of the Sun - are recipes now), drinks' own Stats tab (Right
  away / While it lasts / Lasts), the Value price table, and the **Facing** row (S/W/N/E) for placed shrines and wall
  decorations. Console: `recipereload`, `recipetest`, `usetest`. Drinks check their Needed column.
- **Discord** (editor's DiscordLink): bots post only in #announcements (system webhook: shouts, login/out, [Server],
  up/down), #info (board webhook: who's online, rankings) and #game-chat (chat webhook + bot, plain text); everything
  else as code blocks. #updates is Cody's own; #commits is GitHub's own webhook. Community / Feedback: no bots.
- **Rat-Catcher's cellar**: Mirela (2141, house 525,468; hole 528,465 lands at 888,25 in Underground I), Young Ratlings
  2138-2139, Ratling Broodmother 2140 (not aggressive until a ratling is hit), Broodmother's Tail 2022 -> Rat-Catcher's
  Ring 2023. Tools: `tools/world/rat_cellar/`.
- **Sprites**: quest item pictures 44510-44523 (`tools/sprites/item_icon.py` + `objmodel.py`: glTF or OBJ, RPG Pack
  models in `MyV2\3d Models\`), wall decorations 48000-48025 for all four walls (backs for N/E: items are drawn even
  with hide walls) and turned shrines (temple statue drawn by Cody; `tools/sprites/wall_decor*.py`), templates 2033-2050.
- Open from that chat (Cody decides): the Seyan'Du shrine's turned tops are generated (Cody may redraw them like the
  temple's); signs could get a readable west version (mirroring flips their text); the window walls face one way only;
  TODO: Alchemy skill, change many items at once, a bigger world only if the towns don't fit.

**Nov 17, 21:53: the Golem Foundry is LIVE** (CHANGES.md "Golem Foundry"; client-dist 7404065, Cody pushes). Next in band D:
the Ashen Fields (Varo), then the Gargoyle Spires (Rhea; the Spires add Gargoyle Horns to Brann's bounty), the Monastery last.
Open: molten iron / crucibles / furnaces give no light (only the fire bowls do) - offered Cody hidden light sources.

**Exploration poles:** the Gargoyle Spires' is placed (Cody, Nov 19 19:14). **Still to place (Cody): the Monastery's**
(Lieutenant Colonel, by the pole table; QUEST_BUILD 9c) - remind him.

**Nov 19, 18:05: the Monastery of the Still Hand is LIVE - band D is complete** (CHANGES.md; client-dist 8fa9b5b, Cody pushes).
Next band E (Last Bastion and its areas, QUEST_BUILD) - and the TODO's new first item (recall to each town's temple).
Lessons: (1) `device_commit_files` does not reliably replace a file that already exists on Cody's PC - check its md5
there before running; edit existing files in place with the device shell. (2) Cody wants no whole-figure recolours of
humans: `unarmed_robes.py` (weapon out, clothes only) and `statues.py` are the tools.

**Nov 19, 07:20: the Gargoyle Spires are LIVE** (CHANGES.md "Gargoyle Spires"; client-dist 9c67f2c, Cody pushes). Band D: only
the Monastery is left (new monk sprites). Lessons: (1) the live server was one build behind (Nov 18's `if done` in npctalk.c
was never compiled live): after starting, `talkreload` should say just "NPC dialogue loaded: N entries" - "(some lines were
not understood)" means the live program and the source disagree; `update-code` fixed it. (2) publish_client.py copies and
hashes all ~14,000 client files and no longer finishes within the device shell's 3 minutes; `tools/release/publish_client_inc.py`
adds only new / resized files to client-dist (same manifest), but does not rebuild the player zip - run the full
publish_client.py from Ubuntu (no time limit) before handing out the zip. (3) Claude's first stop-send this session was
refused by the safety system; it went through after Cody said "go live". (4) A zone with flag 1 gets "the" in front:
"Shrike's Eyrie" is flag 0; "Ashra's Hollow" still reads "in the Ashra's Hollow" (fix: flag 0).

**Nov 18, 22:45 (for the next chat):** the old chat's device shell broke (Claude deleted its own `~/tmp` while freeing a
full scratch disk: never delete `~/tmp`; free space with `~/fw`, `~/scratch`, `~/ctest/.dat/mapedit-backups` instead).
Still to do once a shell works: commit `tools/world/worldmap.py` (the minimap fix, CHANGES.md "Minimap redraw without
Pillow") and the CHANGES / HANDOFF notes, unless Cody already did. Next area: the Gargoyle Spires (Rhea).

**Nov 18, 22:07: the Ashen Fields are LIVE** (CHANGES.md "Ashen Fields"): an ash-canyon maze SW of Stonehold, Ashra and
the Flame Lord, Varo's two quests; client-dist e9281d8 (Cody pushes). Next: the Gargoyle Spires (Rhea) when Cody says go,
the Monastery last. Cody places the Ashen Fields' exploration pole himself (Colonel area: 50,000 by the pole table).

**Nov 18: Golem Foundry LIVE; quest text pass done.** Foundry (CHANGES.md "Golem Foundry"); exploration-pole table final
(QUEST_BUILD 9c, 34 vanilla poles raised); every quest greeting says what and where (159-char limit, arealib asserts);
"what next" lines via the new `if done` condition; the Sea Hag (template 2318, sprites 58000+, 427,927 facing west) now
holds Maud's herb pouch (live; client-dist 2882854, Cody pushes).
Lessons: the editor lists GFX sprites only when it starts, so after new sprites send `reload-editor`. A monster that is dead
in Server\.dat (waiting on a respawn) has no character for the editor to show; a gated stop-send brings the live one back. Next: the Ashen Fields when Cody says go.

**Nov 17, 19:55: Stonehold is LIVE** - snowy grass (sprites 36100-36287, client-dist b73a33d, Cody pushes), the townspeople,
Selwyn's rotating shop, ten gate guards, waypoint 7; the editor knows snowy grass. Snowy pines live too (20:11). Selwyn: priced by level + tier more than metal
(merch.c rot_value, sell 200), Steel / Emerald / Crystal / Titanium only (live 20:35). Selwyn's prices final for now (Cody, 20:41: Rare x4, Epic x9 in rot_value). Next: the Golem Foundry - plan in QUEST_BUILD 9b, waiting for Cody's answers.

**Later Nov 17:** bounty items stack and are handed in a whole stack (live; CHANGES.md "Bounty items stack"). Cody's 11 new hatchery eggs checked (all work); three Hatchery archmages -> knights (live). Stonehold's
people + the rotating trader are built and tested on the test server but **not live**: `tools/world/stonehold/place_stonehold.py`
(made.json = the template numbers from the test run, 2274-2289, waypoint 7) and `merch.c` "rotate" (in both server folders and in the
live build since the stacking update, unused until the merchants.dat line goes in). Waiting for Cody's OK on the preview `fenwatch_preview\stonehold_people.png` and on a price
markup for Selwyn. Going live: stop-send, run place_stonehold.py on Server\.dat, `get` (rebuild), update-world.

**Where we left off (Nov 17, evening): Stonehold's ground is live** (the pass from the Hatcheries and the cliff town,
CHANGES.md "Stonehold"). Also today: bounty gold lowered to 1/200 of the exp (Cody); the Soulstone Mine idea (TODO). Next:
Stonehold's people, the ten gate guards, the rotating Rare / Epic trader (new merch.c code) and waypoint 7 - plan in
QUEST_BUILD.md section 9; show Cody before it goes live.

**Where we left off (Nov 17, afternoon): the Lizard Hatcheries are complete and live - band C is done.** Marsh + two
caves, usable lizard eggs (server item driver 77: a Lizard Egg for Corwin's pseudo-bounty, or 1 in 5 a Lizard Hatchling
attacks), lizards, the Broodmother and the Hatchery Archmage, quests on Aldous / Rook / Corwin (CHANGES.md "Lizard
Hatcheries"; client-dist c71f5d4 published locally, Cody pushes). Karate was taken out again (Cody: no use yet). Next:
**Stonehold** (band D hub) and its areas, following the quest plan (QUEST_BUILD.md section 9). Cody hasn't played the
Drowned Village, the Barrow Hills or the Hatcheries yet.

**Where we left off (Nov 17, noon): the Barrow Hills are complete and live** (terrain with two medium tombs, Barrow
Skeletons, pale Barrow Wights 52000+, the Scribe, King Ulfgar, Aldous's and Petra's quests; items 2051-2054, pictures
44533-44535; client-dist 0161385 published locally, Cody pushes). Server: undead in monster groups 34 / 35 heal like
Lab 11's (`SLOW_UNDEAD_GROUP`), and Fable's Good Moon / Frozen Heart code is **now live** (tested first); its Karate part was taken out again (Cody: no use yet).
Next: the **Lizard Hatcheries** (`docs/QUEST_BUILD.md` section 8). Cody hasn't played the Barrow Hills or the Drowned
Village yet.

**Where we left off (Nov 17, morning): the quest plan (new areas) continues in `docs/QUEST_BUILD.md`** - read it before any world-building work: state, Cody's rules, the approved space plan and route, numbers in use, tools (`tools/world/arealib.py`, `deploy.sh`, `render_region.py`), the unfinished code, and the next two areas step by step. Fable's session ran out mid-way (its Good Moon / Frozen Heart code went live Nov 17, after testing; Karate taken out). Live (Nov 17): wall decorations for all four walls + turned shrines (CHANGES.md), templates 2033-2050, editor Facing row; client-dist published locally (Cody pushes).

**Where we left off (Nov 16, 22:35): the Drowned Village is complete and live** (monsters, items 2024-2032, quests on Joss / Ilse / Corwin, Swimming in the server code; client-dist published locally, Cody pushes). Next: the Barrow Hills (plan in TODO.md; and TODO "Space and routes": where every planned area goes, `docs/world_space_plan.png`; the route to Stonehold is proposed through the Lizard Hatcheries, south, not the Barrow Hills; Cody's OK pending), then the Lizard Hatcheries with the Elixir of the Good Moon. Recoloured monsters now go to 50000 and up (Drowned Sailor 50000, Bog-man 50500, Sea Golem 51000; next free 52000). Cody edits Fenwatch live in the editor: before any stop, the gate on `"online": 0` as always; after `reload-editor` he may have to press the editor's round "Load the world again from disk" button (the editor does not restart while it has unsaved changes, and F5 alone then shows the old world). Sprite range 48000-49999 is another session's.

**Before that (Nov 16, late night): Fenwatch has its people** (15 NPCs, three merchants, waypoint 6; the border to the Wolfwood is blended; client-dist 18969bd, Cody pushes). Next: the Drowned Village (plan in TODO.md), with Swimming and the Draught of Clear Water. Two lessons: an NPC can't be put on a tavern tile (`god_drop_char` refuses MF_TAVERN; the log says "Could not drop char N": check the `log` action after every start), and placed NPCs are templates the server spawns at start, so a preview render of the .dat doesn't show them.

**Before that (Nov 16, night): Fenwatch's terrain is live** (CHANGES.md "Fenwatch"; plan and what comes next in TODO.md "The quest plan"). Town x 424-476 / y 770-834, marsh x 406-494 / y 732-852, the Fen Road from the Wolfwood road's end (449,728). Built with `tools/world/fenwatch/build_fenwatch.py` (marsh sprites: `tools/sprites/world_marsh.py`, grounds 35700-35995, reeds 38200-38207; published as client-dist 4aaea69, Cody pushes). Next: the town's NPCs, merchants and waypoint, then the Drowned Village. This session's way of working: previews are rendered with `tools/world/render_region.py` on a copy of `Server\.dat` in the device shell (`~/fw`), copied to `Client\Claude outputs\fenwatch_preview\` (a new file name each time), staged and sent to Cody; the test server is built in `~/ctest` (copy `*.c *.h *.S Makefile`, `mkdir .obj`, `make -j4 server` two or three runs) and `./server light > file` relights a copy of the .dat after a build (redirect its output: it is huge), then map.dat is copied back before `update-world`.

**Where we left off (Nov 16):** quest items have their own pictures (44510-44521, live, client-dist 39aab4b published locally; Cody pushes `client-dist`). Item pipeline: `tools/sprites/item_icon.py <model.gltf|.obj> <out.png>` (32x32 at the game camera; `--glass/--liquid` for bottles, `--recol Mat=rrggbb`, `--roll`). Models: `MyV2\3d Models\` Fantasy Props (glTF), RPG Pack 1/2 (OBJ/FBX, flat colours: the better match for the game's item look).

**Where we left off (Nov 15, wolf):** the first **3D-rendered monster** is live and published (client 2.15.07, pushed): the Grey Wolf, sprites 43000-43447, one test wolf (template 2057) at 532,624. Pipeline: Quaternius "Ultimate Animated Animal Pack" (CC0 glTF, `MyV2\3d Models\`; also fox, husky, deer, stag, bull, horse...) -> `tools/sprites/make_creature.py <model> <base> <out>` (uses glrender.py; no Blender) -> PNGs into `Client\GFX` -> publish. Sprites 43000-49999 are kept for these: they carry their own shadow (32%) and the client skips its flipped shadow there. A new creature copied from a "simple" monster needs CF_SIMPLE cleared. Delivery lesson: device_commit_files to a path already written earlier can leave the OLD file; give each delivery a new file name and check md5 on the device. The first Wolfwood was taken out again (Cody didn't like it): Cody builds the area himself, then Claude spreads the NPCs (Grey / Dire Wolves, Greyfang, Edda; see TODO).

**Where we left off (Nov 15, later):** Cody has set up the Bandit Hollow and Old Quarry quests the way he likes them. Bandit Hollow's three are now **item quests** (town-quest kind, #quest 20-22, the Quests page's Item quests; `qcount` lets one give several of its item) and the Old Quarry is **one chain quest** (quest 4, Brann's Conversations); `tools/world/quest_fix/to_item_quests.py` did the switch, but Cody has since edited them in the editor: the live `.dat` is the truth, not the scripts. Editor work this day: one cell per picture in the palettes, save buttons in the top bar, Show & flags as a round view button, keys always shown, the right panel for what is selected. Next: the next area of the quest plan (TODO.md "The quest plan": Wolfwood) when Cody says.

**Where we left off (Nov 15):** the **Old Quarry** is built and live too (CHANGES.md "Old Quarry"; `tools/world/old_quarry/`), with the first recoloured monsters (`tools/sprites/recolor_creature.py`). Before that (Nov 14, late): the **quest plan** is done ("Quest Map and Plan" doc + "Quest Planner" sheet on claude.ai; TODO.md "The quest plan") and its first area, **Bandit Hollow**, is built and live (CHANGES.md "Bandit Hollow"; `tools/world/bandit_hollow/`: build_hollow.py drives the MyV2 Editor's World class headless on a stopped .dat - floors, objects, doors, items, new item/NPC templates, NPC spawns - and talk.py writes the npctalk.dat lines; `~/bh/render.py` in Claude's device shell draws an iso preview of a map region from the real sprites). Next: Wolfwood / Old Quarry when Cody says.

**Where we left off (Nov 10, late):** the **town rearrangement is done** (CHANGES.md "Aston rearranged" and the lines after it; leftovers in TODO.md "Town rearrangement"; pictures in `MyV2\Town pictures (Nov 10)\`). The game is running. Next in `docs/TODO.md` "Up next": **soulstone levels too low (major)**, then Discord, speed, town NPC doors, logout at shutdown, resizable window. TODO.md is one design + to-do document by category (merged Nov 10 with Cody's `MyV2\Design Document.txt`; old numbers kept as "(was #n)"); if Cody adds ideas to `Design Document.txt`, fold them in. Still waiting on Cody: the Windows restart test of start-with-Windows (Discord #server-status shows if the server came back by itself). Discord server set up Nov 7 (layout in HOSTING.md); the editor posts server up / down through `Server\discord-webhook.txt` (secret, never in git). Git note: in a new session ask for delete permission on the project folder (device_request_delete_permission), else git leaves `.lock` files and Cody's push fails; clear stale `.git/*.lock`, `gc.pid` after commits.

**Tested by Cody in game (Nov 4-5), all good:** potion stacks, the Fire/Ice set bonuses, Burning Hits (+ `#burning`), Frost Armor, the
sets in the god shop, the Ice Gargoyle Cape and the Cloak of Ice names, thorns on every landed blow, the 2.15.02 client
(Ctrl+click, scroll charges, Greataxe name, Ice set pictures), Weapon Specialization in `#twohand` / `#greataxe`, set
pieces sold to merchants being destroyed, the three old Fire chests' new loot, the HP/End/Mana 50 requirement, the quests
page / `#quest` and the area clears. **Client 2.15.02 published Nov 5** (client-dist 08bdabd) and `CLIENT_LATEST` raised to
0x020F02. `#axe2h` renamed `#greataxe` (Nov 5).

**Tidy-up (Nov 7):** outdated files in `Client` and `Server` moved to `_old (safe to delete)` in each (old merc_*.exe, old zips, stale client source copies, lpng/zlib/original_borland; Server: *.pre* / *.orig copies, one-off add_* scripts, the .dat_before_* world snapshots). Cody deletes them. Cody's own `Client\client.ini` has `[server] host=127.0.0.1` so Launcher.exe works on the hosting PC (the router can't loop back to the public address); never publish client.ini.

**Name (Nov 7):** the game is called **Mercenaries of Asgard v2** (client 2.15.04 window title / save dialog / file properties, launcher title, README, login welcome line). The world stays Astonia (Aston, rank names). The address stays myv2astonia.duckdns.org; internal names (MyV2, MyV2 Editor, folders) stay. Client 2.15.04 + the new Launcher.exe PUBLISHED Nov 7 (client-dist 5060ae6), `CLIENT_LATEST` 0x020F04; new player zip `Client\For Players\Mercenaries-of-Asgard-v2.zip` (publish_client.py rebuilds it every publish) (folder "Mercenaries of Asgard v2", 22 MB; the old MyV2-Astonia.zip can go).

**Hosting (Nov 6):** backups every 6 hours live (`D:\MyV2 Backups`); start with Windows set up (task "MyV2 Server"), Cody tests it with a restart later: after it, check the game and editor came up (status.json). Section 4 done except: the restart test of start-with-Windows, step 3 (test server, skipped for now) and step 7 (a place for players, e.g. Discord).

**Client 2.15.03 published Nov 6** (client-dist 0212ff4: `#gca` with the Alt-selected enemy, names drawn over the map, the table / bar scroll sprites); `CLIENT_LATEST` 0x020F03.

**Readable tables (Nov 5, live):** templates 1409-1416 (tables / bar with a scroll, sprites 18290-18297 in `Client\GFX`, not yet in a published client). Cody places them and writes each Description.

**Zones (Nov 5):** Cody's earlier zone edits were lost: the live server never had a `.dat/zones.dat` (no backups either), so they were never saved (Zones tab edits lived only in the page until **Save zones**). Now the editor keeps a browser draft and offers to restore it, and warns before leaving with unsaved changes. Done Nov 5: Cody redrew and saved them (`.dat/zones.dat` now exists) and updated the area clears with **Re-check zones**.

**Where we left off (Nov 4):** live: the rebalance, area clears, stacking (TODO 14), the Cloak of Ice (template 1407). Fire set = melee / Ice set = casters (`tools/world/fire_ice_sets.txt` + `refresh_items`): with 4- and 6-piece set bonuses, now non-unique rare late-game drops (god shop has them, merchants destroy sold pieces), HP/End/Mana need 50, Fire 1-3 / Ice 1-2 damage to attackers; old Ice Cloak renamed Ice Gargoyle Cape: all LIVE since Nov 4 (TODO 19; Cody checks tooltips / #specialarmor in game). The Ice Gargoyle Cape 909 (was "Ice Cloak"; egg trade, temporary, unique) keeps its stats: don't change them. Client: `Client\merc.exe` is 2.15.02, published (earlier builds kept as `merc_2.15.01.exe` and `merc_old.exe`). After publishing a client, raise `CLIENT_LATEST` in `server/gendefs.h` to its version (players on older clients are then told on login to use Launcher.exe), and `MINVERSION` only if old clients can no longer play. Waiting for Cody at home: the summoner's
staff and waypoints (TODO 13, pictures in `docs/ref`). Cody is going through the quests and area clears. The DuckDNS
PowerShell window: switched to a hidden launcher; check with Cody that it stopped.

- **#quest** (IN PROGRESS, not final; live since the zones update; built and committed): the look is approved (column table, 15 a page); still open: the order
  and rewards; maybe a separate difficulty number per quest
  giver. `#journal` maybe only for temporary / seasonal quests.
- **Hosting section 4**: done (Nov 6-7) except the test server (skipped for now) and the restart test; see HOSTING.md.
- **Lab shrine keys**: done (Nov 6, scrolls from the Seyan'Du Lord, TODO 8).
- Ice set sprites: done; item tiers part 5 (Legendaries); prestige rewards.
- Name chosen: Mercenaries of Asgard v2 (Nov 7).
- Chests: only the game's two facings (south 220/221, west 222/223); north/east sprites were tried
  three ways and dropped.
