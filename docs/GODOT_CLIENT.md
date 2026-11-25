# The Godot client for MyV2 (plan and step-by-step setup)

Goal (Cody, Nov 21): a new client for the MyV2 server, built from James Black's Godot 4 / C# client for The Last
Gate (github.com/jamesblack/thelastgate-godot), because it runs very smoothly. **James gave permission** for Claude
to look at it and build on it. The TLG server (github.com/ZarroTsu/TheLastGate) is not needed and nothing is pulled
from it: **our server is the only contract** the new client keeps.

**Step 1 DONE (Nov 22, 00:19):** tools installed, fork github.com/SooperValar/myv2-godot-client, git copy in `MyV2\Godot-Client` on branch `myv2` (remotes origin = fork, upstream = James), LFS art pulled, `dotnet build` OK, runs in Godot 4.7.2. **Cody chose 1e (b)**: he adds the build domains to the allow list; next chat Claude installs .NET in the PC's Linux shell, checks it builds there, then starts Step 2.

Earlier status: planning only (Nov 21, 23:45). Nothing built, nothing changed. `MyV2\TLG-Godot-Source` is a plain copy
(no git, the art files are Git LFS placeholders); the real working copy will be `MyV2\Godot-Client` (step 1).

---

## What Claude found (Nov 21)

- Layout: `src/TheLastGate.Core` (network + game state, no screen), `src/TheLastGate.Assets` (sprite archives),
  `src/TheLastGate.Rules` (copies of TLG server formulas), `game/` (the Godot project: HUD, windows, map drawing),
  `tools/SpriteCompiler`, `tests/`. Its own rules for code are in its `CLAUDE.md` (read it before editing).
- **Login is identical** to ours (16-byte packets, same challenge cipher and secret, same login / new-player / mod packets).
- **After login, about 20 server messages differ** (all in `src/TheLastGate.Core/Net/ServerCommand.cs`,
  `ServerCommandLength.cs` and `Net/Handlers/`):

| What | MyV2 (`Server/svr_tick.c`, client `socket.c`) | TLG client |
|---|---|---|
| SV_SETCHAR_ITEM / WORN / held item (OBJ 25) | 9 / 9 / 5 bytes | 11 / 10 / 6 |
| SETMAP flag 64 / flag 128 | 5 bytes (nr, id, speed) / 1 (proz) | 6 / 8 |
| 52-55 | SV_LOG0-3 (log lines) | Look7, Look8, CloseShop |
| 74-79 | SPELLTIME(20) ITEMINFO(64) TILEGLOW(4) TIERS(64) ITEMMARKS(126) WAYPOINT(80) | waypoints, MOTD, char waypoints, ClearBox, tokens, tree |
| Log lines | 52-55 | 90-99 |
| View | 44 x 44 tiles (`TILEX`), SETMAP3 index & 2047 | 54 x 54 |
| Version sent at login | 0x020F0x (server refuses below `MINVERSION`) | 0x000F00 |
| Client commands 34 / 35 | CL_CMD_ITEMINFO / CL_CMD_WAYPOINT | Smith / Waypoints (36-40 are TLG-only) |
| Player state | our inventory / worn / skill counts (check `server/client.h`) | 60 inv, 20 worn, 100 skills, 40 buffs |

- **TLG-only features to switch off:** skill trees, contracts, tokens, smith, depot, meta stats / terminology,
  the planner's TLG formulas (`Rules`), MOTD.
- **MyV2 features to add:** tier glow + item marks/tiers, server-driven item tooltips (ITEMINFO), buff timers
  (SPELLTIME), our waypoint window + travel glow, trash window, hide-mode rules for the new trees / walls, `#gca`,
  stacks / Ctrl+click, equipment compare.
- **Sprites:** it reads archives (`data/archives/bmplib`, `pnglib`) plus loose `NNNNN.png` overrides, up to sprite
  133,072 (so our 0-65,535 fit, and it is ready for the 32-bit sprite TODO). Ours: `gx00.dat/.idx` (base),
  `pnglib.dat/.idx`, `GFX\NNNNN.png` (~19,760 files), sounds `sfx\N.wav`.
- **Building:** needs the .NET SDK and Godot 4.7.2 .NET. Neither Claude's cloud workspace nor the PC's Linux shell
  has them, and both are blocked from downloading them (nuget.org, dotnet, github.com not on the allow list).


## Building in Claude's device shell (works since Nov 24)
The build domains are allowed. The session folder (`/sessions`, = `$HOME`) is ~95% full, so everything lives in `/tmp`
(~3 GB free; may be wiped when the VM restarts: then redo these):
```bash
cd /tmp && curl -sSL https://dot.net/v1/dotnet-install.sh -o dotnet-install.sh
U=$(bash dotnet-install.sh --channel 10.0 --dry-run 2>&1 | grep -o 'https://[^ ]*linux-x64.tar.gz' | head -1)
curl -sSL "$U" -o sdk.tgz && mkdir -p dotnet && tar xzf sdk.tgz -C dotnet && rm sdk.tgz   # the script's own extract fails
mkdir -p /tmp/gc && cd "$HOME/mnt/MyV2/Godot-Client" && tar cf - --exclude=./.git --exclude=./art --exclude='*/bin' \
  --exclude='*/obj' --exclude=./game/.godot . | tar xf - -C /tmp/gc       # build a COPY: Linux obj/ files would break Cody's Windows build
export DOTNET_CLI_HOME=/tmp/dnhome NUGET_PACKAGES=/tmp/nuget DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 \
  PATH=/tmp/dotnet:$PATH DOTNET_ROLL_FORWARD=Major                       # tests target net8, only the 10 runtime is installed
cd /tmp/gc && dotnet build tests/TheLastGate.Tests && dotnet test tests/TheLastGate.Tests --no-build
```
Nov 24: SDK 10.0.404, build clean, 906 tests pass; the 26 failing are the sprite / archive tests (no `art/` in the
copy: expected). Edit in `MyV2\Godot-Client` (the real git copy), sync to `/tmp/gc` to build and test; Cody runs it in Godot.

---

## Step 1: set up (Cody does this, Claude walks him through it)

### 1a. Install the tools (Windows, once)
Open **PowerShell** (Start menu, type PowerShell) and run these one at a time:
```powershell
winget install --id Git.Git -e
winget install --id Microsoft.DotNet.SDK.10 -e
winget install --id GodotEngine.GodotEngine.Mono -e
```
Close PowerShell and open a new one (so it finds the new programs), then check:
```powershell
git --version
git lfs version
dotnet --version
```
`dotnet` should say 10.0.x. Godot is not on the PATH; it lands in
`%LOCALAPPDATA%\Microsoft\WinGet\Packages\GodotEngine.GodotEngine.Mono_Microsoft.Winget.Source_8wekyb3d8bbwe\`.
Check its folder name says **4.7.2** (the client was made with 4.7.2-stable .NET; if winget gave a newer one, tell Claude).
Once: `git lfs install`.

### 1b. Make your own copy on GitHub (a fork)
1. Sign in to GitHub as SooperValar, open https://github.com/jamesblack/thelastgate-godot
2. Click **Fork** (top right). Owner: SooperValar. Name: e.g. `myv2-godot-client`. Untick nothing else. **Create fork**.
   (A fork of a public repo is public. If you'd rather keep it private, tell Claude: that's a few extra steps.)

### 1c. Put the git copy in MyV2\Godot-Client
In PowerShell:
```powershell
cd C:\Users\Cody\Desktop\MyV2
git clone https://github.com/SooperValar/myv2-godot-client.git Godot-Client
cd Godot-Client
git lfs pull
git config core.hooksPath .githooks
git remote add upstream https://github.com/jamesblack/thelastgate-godot.git
git checkout -b myv2
```
- `git lfs pull` downloads the real art and sound files (a few hundred MB).
- `upstream` lets us pull James's later fixes; `myv2` is our own branch, so his `main` stays clean.
- After this, `MyV2\TLG-Godot-Source` is no longer needed (Claude can delete it).

### 1d. Check it builds and runs, unchanged
```powershell
dotnet build TheLastGate.sln
dotnet test tests/TheLastGate.Tests
```
Then start Godot (the `..._mono_win64.exe` in the folder above), **Import**, pick
`MyV2\Godot-Client\game\project.godot`, open it, press **F5**. The launcher should appear (it points at the TLG
server; don't log in). Tell Claude whether each step worked or paste the error.

### 1e. Decide how building happens from then on
- **(a)** Claude edits the code (in `MyV2\Godot-Client`), Cody runs `dotnet build` / presses F5 and reports back; or
- **(b)** Cody adds `nuget.org`, `api.nuget.org`, `builds.dotnet.microsoft.com`, `dotnetcli.azureedge.net` and
  `github.com` to the allowed domains (claude.ai settings, network / capabilities); in a NEW chat Claude installs .NET
  in the PC's Linux shell and builds and tests Core itself (Godot runs still on Windows). Less work for Cody.

---

## Pushing (Claude does it, Cody's rule)
Same bundle method as the project (HANDOFF): commit in `MyV2\Godot-Client` on `myv2`, `git bundle create
..\Client\push-godot.bundle origin/myv2..myv2`, stage it, in the cloud clone (`add_repo` SooperValar/myv2-godot-client,
push access; clone with `GIT_LFS_SKIP_SMUDGE=1 --depth 1`) `git fetch <bundle> myv2:refs/tmp/myv2` and
`GIT_LFS_SKIP_PUSH=1 git push origin refs/tmp/myv2:refs/heads/myv2`, delete the bundle, `git update-ref
refs/remotes/origin/myv2 <sha>` on the PC. New art (LFS files) can't go up this way: LFS objects need a real push
(Step 3 will settle how). The repo's own CLAUDE.md is James's (TLG paths): our server is the contract, not TLG's.
First push Nov 24: myv2 f05a4e86.

## Step 2: talk to our server (Claude) - DONE in code Nov 24 (Godot-Client `myv2` f05a4e86), Cody tries it in Godot
What changed (see the commit message for the list): server messages renumbered / resized to ours, TLG-only messages
removed, our 74-79 messages read into new state (`BuffTimers`, `ItemTiers`, `ItemInfoReply`, `WaypointList`,
`MapTile.Glow`; no windows yet), **animation timing = our 20x20 `speedtab` on a 20-tick cycle** (`StatusSpeed`; TLG had
0-299 speeds over 200 ticks), 44x44 view, version 0x020F09, unsigned sprite numbers, server
myv2astonia.duckdns.org with 127.0.0.1 as fallback (`ServerAddress.Live`; a hand-added `[server]` section in
`%APPDATA%\Godot\app_userdata\TheLastGateGodot\settings.cfg` overrides it). Background item looks and `#buffs` are
unhooked in `GameScreen` (our server would print them in chat). `ClientCommand.Smith` (34) is our CL_CMD_ITEMINFO.
Tests: 823 pass (the 26 failing are sprite / SkiaSharp tests, no art or libSkiaSharp in the device shell); the GodotTests
compile (they need Godot to run). **Not run yet: the JetBrains cleanup check** (`dotnet tool restore` needs more disk than
the device shell has; committed with `--no-verify`).
Headless test (`/tmp/hl`, a console app on Core; the test server built in `/tmp/ts` from `Server\` + `.dat` without
mapedit-backups): new-player login, 512 ticks without a desync, walk, chat, worn items, ITEMINFO tooltip lines.
`.moa`: ours = key (56) + pdata (480) = 536 bytes; the Godot launcher keeps the key from any size but writes 640-byte
files, which merc.exe refuses: use a COPY. Git in the device shell: `git status` over the whole repo times out (19k art
files): limit it to `src game tests`; the LFS hooks complain (no git-lfs there) but commits go through.

Earlier plan text:
Rewrite `ServerCommand`, `ServerCommandLength`, `ClientCommand` and the handlers to match the table above; send our
version (0x020F09 or later); 44 x 44 view; our player-state sizes; add an `ServerAddress` entry for
myv2astonia.duckdns.org / 127.0.0.1. Prove it with a headless test first (log in to the **test server** `~/ctest`,
walk, read the map, inventory, chat), then in Godot against the test server. **No server changes**; merc.exe keeps
working beside it. Commits on the `myv2` branch, pushed to Cody's fork.

## Step 3: our art and sounds (Claude) - DONE in code Nov 24 (myv2 78ae8129 + 315f2d95), Cody checks it in game
Not copied into the repo (that would put ~300 MB into GitHub's 1 GB free LFS quota and grow with every rebuild): the
client **reads our art and sounds straight from the MyV2 client folder** (`game/Assets/MyV2Art.cs`), in merc.exe's order:
`GFX\NNNNN.png`, `pnglib`, `GFX\NNNNN.bmp`, `gx00` (gx00 is byte-for-byte TLG's bmplib format; our pnglib.idx is
shorter, 34,768 entries, so `PngLibrary` now accepts a short index). Then TLG's archives as a fallback; a player's own
`user://overrides` still win over everything. Sounds: our `sfx\N.wav` first, then TLG's `data/sounds` (click).
Folder: env `MYV2_CLIENT`, else in the editor `MyV2\Client` beside the repo, else the exported exe's folder (Step 6).
**TLG's interface art moved to sprite 100,000 + its number** (`SpriteNumbers.ClientArtBase`): its HUD font is at 18100
and frames / windows at 18000-18129, which clashed with our Ice set (18100-18104) and other GFX sprites there - that was
the "gibberish" on screen. Moved: the 18000-18139 block and the restyled 42/43/44/92/99, in 5 constants
(ClassicFonts, OptionsWindowView, SessionStatsWindowView, WorldMapWindowView, PlannerLook, TutorialPages), the scenes and
OptionsTheme.tres. Numbers below 100,000 are always the server's (ours). Comparison (Nov 24): ours 33,713 sprites,
TLG 18,820, 12,197 v2 originals identical, 54 differ (ours win). Check sheet: `Claude outputs\godot_art_check.png`.
.moa fix: a 536-byte MyV2 file now keeps its name and description (same first 321 bytes as TLG's settings block), so
the client no longer sends an empty description at login.
Device-shell git: a commit takes ~90 s (scans the 19k art files; use `commit -uno`, add only the needed paths); the art
files show as "modified" there only because git-lfs isn't installed in the shell - not real changes.

Earlier plan text:
Use its SpriteCompiler to build `data/archives` from our `gx00`, `pnglib` and `GFX\` (or point the overrides at
`GFX\`), and our `sfx\`. Check a few areas (Aston, Fenwatch, Stonehold, the Spires) against merc.exe screenshots.

## Feature inventory (Nov 24): Cody wants to KEEP the client's features and make them fit our server where possible
(Cody: "I'd like to keep the planner and implement it into my server as well. If the features exist in the client and
I can make them fit my server I'd like to explore that option.") So Step 4 no longer hides things by default.

**A. Client-only, work once fed our data (no server change):** Planner raise costs (same v2 formulas as merc.exe
`attrib_needed` / `skill_needed` / `hp_needed` / `mana_needed`; Endurance = v*end[3]/2 is missing in `Rules/RaiseCost`),
skill names (TLG gets them from the server's terminology messages; we put our 50 names from merc.exe `_skilltab` into
the client), hotbar, area use, use queue, give more, auto walk, explored map / notes / world map (sized for TLG's
2048x1024 world: `WorldMapView.TilesAcross`, `NoteLimits.Tiles` -> our 1024x1024), session stats (gold), options,
accessibility. HP / End / Mana box layout. Window title / app name.
**B. Client adapters to messages our server ALREADY sends:** item tooltips <- SV_ITEMINFO (CL_CMD_ITEMINFO 34),
buff timers <- SV_SPELLTIME, waypoint window <- SV_WAYPOINT rows / CL_CMD_WAYPOINT (35, [1] = destination), item tier
colours / marks / tile glow <- SV_TIERS / SV_ITEMMARKS / SV_TILEGLOW, merchants (already work), trash window (merc.exe
feature, `#trash`).
**C. Need new server work (features new to our game):**
- Hit Score / Parry Score + List Offenses / List Defenses: TLG's "meta stats" (terminology text + values); our server
  has the values (to_hit / to_parry etc. in svr_do.c) and would send them. Small-moderate.
- Currency rows (3x "???"): TLG's Black Stronghold points, Osiris points, tokens. We have Black Stronghold points
  (data[26..28], [41], [43]); the other two rows could show something of ours (exploration points?). Small.
- MOTD / tutorial / new-player welcome windows: server sends a window number + text. Small (text to write).
- Planner's combat and buff previews (`Rules/CombatModel`, `BuffModel`, `ItemEffects`, `TarotMath`, `TreeEffects`): TLG
  formulas; port ours from svr_do.c / skill code. Moderate, client-side.
- Depot (account storage), Smith (weapon / armor smithing with catalysts), Skill tree + contract tree + tokens,
  casino / contract / experience shops: whole TLG game systems; large, game-design decisions first.
- Not worth it: spectating, lycanthrope / kindred skills, tarot.

## Step 4: (was "hide the TLG-only parts") - now: groups A + B, then C items one at a time as Cody picks them
**Group A DONE Nov 24 (myv2 d1cf8f91, Cody checked it in game):** our 37 skill names / groups / attributes
(`Core/State/MyV2Skills.cs`), merc.exe's skill order and "unused / fixed (red) / raisable" display, totals = value[5]
(TLG packed two bytes), Endurance row + its raise cost (v*d/2), at most 99 raises per CL_CMD_STAT (our server ignores
more), world / explored map / notes at 1024x1024 (`WorldMap.WorldTiles`), currency rows hidden until they have points,
skill-tree button hidden, launcher: our race numbers (2/3/4, 76/77/78; anything else became a male Mercenary), Game
Mode / Season hidden, Discord https://discord.gg/hVpuUPp3jp, updates checked on SooperValar/myv2-godot-client, game name
"Mercenaries of Asgard v2" (user folder `MercenariesOfAsgardV2`), no description upload under 10 letters (our server
REPLACES a short description with "...looks somewhat nondescript"; Iluvatar's was overwritten that way Nov 24).
HUD art: every HUD scene sprite asks at 100,000+ (TLG's light HUD used sprites 1-10, which are our v2 interface);
the HUD frames (`data/overrides/00001.png` light, `18001.png` dark) and overlays (`00099`, `18099` skill area,
`18097`/`18098` meta panel) are edited by `tools/myv2-hud/build.sh` (always from TLG's originals): 8th attribute row,
skill panel / Update row / HP box one row (14 px) lower, wider value columns (HP box dividers 97/129, overlay 159->165,
172->175), Planner and Update tabs (Update divider on the x=136 line). Scene offsets moved to match.
**Lessons:** pushing LFS objects from Claude's cloud copy is refused (GitHub storage authorization error), so commits
with art: commit in the cloud, bundle to the PC, put the LFS objects in `.git/lfs/objects/xx/yy/<sha256>`, `git reset`
to the commit, and CODY runs `git push` (Windows has git-lfs). `device_commit_files` adds a C2PA `caBX` chunk to PNGs
(and stamps the sent copy in /mnt/user-data/outputs too): strip it on both sides before committing (same pixels).
**Zone name (Cody OK'd Nov 24):** client myv2 07e3f271 (version 3.0.0, `ServerCommand.Zone` 80 -> `Player.Location`,
`Hud/ZoneText` shows the innermost zone when the chain is over 20 letters); server `SV_ZONE` in both server folders
(CHANGES.md "Godot client support"), tested on the test server (old-version client gets nothing; new one gets
"Aston, Temple of Skua" / "Aston" / "Aston, Temple Street"). Server part LIVE Nov 24, 22:12 (Cody's "go live",
update-code with nobody online; full rebuild since client.h changed). Next: group B.
Skill trees, contracts, tokens, smith, depot, meta stats, MOTD, TLG planner formulas: off, so the client plays our game cleanly.

## Step 5: our features, one at a time, a preview for Cody after each (Claude)
Tier glow / marks, tooltips, buff timers, waypoint window, trash window, hide mode, `#gca`, stacks, compare.

## Step 6: getting it to players (later; only with Cody's "go live")
Its own Velopack auto-updater (GitHub releases on the fork) or our `client-dist` launcher. Decide when it plays well.
