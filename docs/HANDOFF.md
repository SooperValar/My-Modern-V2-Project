# Handoff: how this project fits together

Read this first in a new chat. It says where everything is, how each part is changed and put
live, Cody's standing rules, and what is still open. The full list of what was changed is in
`CHANGES.md`; the open items in `docs/TODO.md` and `docs/HOSTING.md`.

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
| Windows copy of the server source (Claude edits this) | `C:\Users\Cody\Desktop\MyV2\Server` (= `$HOME/mnt/Server` in Claude's device shell) |
| Client (what Cody plays) | `C:\Users\Cody\Desktop\MyV2\Client` (`merc.exe`, `Launcher.exe`, `GFX\`, `sfx\`, `gx00.*`, `pnglib.*`) |
| Git project (GitHub, public) | `C:\Users\Cody\Desktop\MyV2\Client\Claude outputs\My-Modern-V2-Project` = github.com/SooperValar/My-Modern-V2-Project |
| Player download | `Client\MyV2-Astonia.zip` |

Project layout: `server/` (server source, the same files as the Windows Server folder),
`client/` (client source; `client/launcher/` the launcher; `client/package/README.txt` the player
readme), `tools/mapedit/` (the editor), `tools/release/` (publishing client updates),
`tools/sprites/` (sprite scripts and art), `tools/world/` (one-off world data tools),
`docs/` (TODO, HOSTING, ITEM_TIERS, this file).

Note: the `.c` files directly in the `Client` folder are old (October 19); the real client source
is the project's `client/` folder.

## Cody's standing rules

- Always end with clear **"▶ Do this now"** steps.
- **Keep the hand-off documents current as we go** (this file, `docs/TODO.md`, `CHANGES.md`): Cody starts a new chat
  only about once a week, so every session should leave them complete enough for a cold start.
- Keep `CHANGES.md` up to date with every change; commit every change (in the project folder);
  remind Cody to `git push` (Claude doesn't push).
- **Server source is changed in BOTH places and kept identical**: the Windows Server folder and
  the project's `server/`. Never copy a whole file over the other blindly; edit, then copy the
  edited file across and check they match (md5).
- **Ask before anything that stops or restarts the live game.** Reading status and logs, and
  preparing updates, is fine. Cody says **"go"** to approve an update-code restart.
- New sprites get **new numbers**; never replace the game's own sprites (fixing one of Claude's
  own in place is OK).
- Directions follow the minimap: north = smaller x, west = smaller y. On screen: larger x is
  down-right (south), larger y is up-right (east).
- Keep the world minimap and zone maps current when the map changes.
- Don't paste artifact URLs.
- Editing the live game's data directly from a browser tab (POST `/api/edit` via a browser tool)
  was refused by the safety system: don't; ask Cody to do such edits in the editor himself.

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
- **Server code update**: edit the source in both places, then (after Cody's "go")
  `{"action":"update-code","warn":30}`: warns players, stops, `claude-sync.sh get` (copies the
  changed Windows source into Ubuntu with a backup in `~/claude-backups/`, then `make`), starts.
- Console commands (control port 127.0.0.1:5556, or the editor's console): `who`, `status`,
  `announce`, `tell`, `kick`, `raise`, `lower`, `gold`, `quest`, `talkreload`, `talktest`,
  `talkkill`, `talkuse`, `talknear`, `talkmoney`, `zonereload`, `zone <x> <y>`, `chesttest <player> <x> <y> [real]`, `edpatch`.
- **Test server** (for trying server changes without touching the live game): in Claude's device
  shell, `~/ctest` holds a copy of the server source and data. Copy the changed files there,
  `make server` (a full build may need two runs within the 3-minute limit). **Always check port
  5556 is free first** (`ss -ltn | grep 5556`) so the live server is never hit. Start it with
  `(./server > out.txt 2>&1 &)`, talk to it on 5556, kill it at the end (`pkill -f "^./server"`).
  Background processes die when the shell call ends.

## Changing the world data (item / NPC templates, merchant stock)

The live world is in Ubuntu (`~/.dat`); `Server\.dat` on Windows is only a copy (may be old). For a template change:
1. `{"action":"stop-send"}` (Cody's "go": the game stops) - the current world is copied to `Server\.dat`.
2. In Claude's device shell: build `tools/world/build_lab.c` (`gcc -I server`) and run it on `$HOME/mnt/Server/.dat`
   with the spec (`tools/world/*.txt`).
3. `{"action":"get"}` if the code changed too (rebuild, no start), then `{"action":"update-world"}` (takes the world from
   Windows, starts the game), then `{"action":"reload-editor"}`.
New sprites: write them to `Client\GFX` (new numbers), then `tools/release/publish_client.py`; Cody pushes `client-dist`.

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
  `tar xzf`, `apt-get install -y clang lld llvm` if missing, `bash myv2-buildkit/build_client.sh <source folder>`,
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

## Known quirks

- **Deleting files in Cody's folders** needs his approval (a permission prompt), and the approval
  has dropped by itself during a session. Git then can't remove its own lock files: after a commit,
  move any `.git/*.lock` and `.git/objects/maintenance.lock` aside (e.g. to `.git/stale-...`) so
  the next git command works; Cody can delete the `stale-*` files later.
- When committing a file to Cody's PC, use the `fileUuid` from sending it first; committing by a
  staged path once sent an old copy.
- `merc.exe` can't be replaced while the game is open.

## Open items (details in docs/TODO.md and docs/HOSTING.md)

**Where we left off (Nov 4):** the rebalance (TODO 11) is LIVE (server code + world update done Nov 4: items
1378-1406, books at Damor, Greataxe names). Client: the new merc.exe (Greataxe in the skills list, 2.15.01) was swapped
in on Cody's PC (old one: `Client\merc_old.exe`) but NOT published yet: Cody tries it at home, then publish with
`publish_client.py`. The Ice set pictures (18100-18104) are in `Client\GFX` and go out with that same
publish. client-dist already has update 3 (sprites 18240-18287); Cody pushes it. Next: the summoner's staff
(design in `docs/REBALANCE.md`). Cody is also going through the quests on the Quests page. The DuckDNS PowerShell
window: switched to a hidden launcher; check with Cody that it stopped.

- **#quest** (IN PROGRESS, not final; live since the zones update; built and committed): the look is approved (column table, 15 a page); still open: the order
  and rewards; maybe a separate difficulty number per quest
  giver. `#journal` maybe only for temporary / seasonal quests.
- **Hosting section 4**: daily backups of the world data with a copy off the PC (next);
  the server and editor starting with Windows (a scheduled task; note the "only after login"
  caveat); a test copy of the server; accounts (who has god / imp, remove test characters);
  safety (runs as an ordinary user; a look at the network input code); a Discord (Cody creates it;
  Claude can do webhook posts: server up / restarting / announcements, a status message, later a
  chat bridge bot).
- **Lab shrine keys** for missed lab shrines: 100 gold per shrine times the lab level.
- **Ice set sprites** 18100-18104 are missing; item tiers part 5 (Legendaries); prestige rewards.
- Server name ideas were offered (e.g. "Astonia Rekindled", "Sunken Dark"); Cody hasn't chosen.
- Chests: only the game's two facings (south 220/221, west 222/223); north/east sprites were tried
  three ways and dropped.
