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

## Step 3: our art and sounds (Claude)
Use its SpriteCompiler to build `data/archives` from our `gx00`, `pnglib` and `GFX\` (or point the overrides at
`GFX\`), and our `sfx\`. Check a few areas (Aston, Fenwatch, Stonehold, the Spires) against merc.exe screenshots.

## Step 4: hide the TLG-only parts (Claude)
Skill trees, contracts, tokens, smith, depot, meta stats, MOTD, TLG planner formulas: off, so the client plays our game cleanly.

## Step 5: our features, one at a time, a preview for Cody after each (Claude)
Tier glow / marks, tooltips, buff timers, waypoint window, trash window, hide mode, `#gca`, stacks, compare.

## Step 6: getting it to players (later; only with Cody's "go live")
Its own Velopack auto-updater (GitHub releases on the fork) or our `client-dist` launcher. Decide when it plays well.
