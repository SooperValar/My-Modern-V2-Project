# My Modern V2 Project

**Mercenaries of Astonia v2**, the 1999–2004 Windows MMORPG, brought back to life on modern Windows 10/11 — with a reworked 1280×960 view, a redesigned HUD and a set of quality-of-life features.

> Based on the Mercenaries of Astonia engine by Daniel Brockhaus.
> See [`server/LICENSE`](server/LICENSE) — free to use and modify, credit required, no commercial use.

## What's in here

| Folder | What it is |
|---|---|
| `client/` | The Windows client (`merc.exe`), ported from Borland C++/DirectDraw to Visual Studio/GDI |
| `server/` | The Linux game server, fixed to build and run correctly as a 64-bit program (works fine under WSL) |
| [`CHANGES.md`](CHANGES.md) | The full breakdown of every change and why it was needed |
| `tools/world/` | Scripts that read the world data: minimap render, portal/teleport scan |
| [`docs/world_links.md`](docs/world_links.md) | Every portal, teleporter and ladder: where it is, where it goes, plus coordinates hard-coded in the server |
| [`docs/world_zones.md`](docs/world_zones.md) | Zone names (`/who`, "where am I") and the map rectangles they cover |

The commit history follows the work step by step: the untouched original source first, then each fix and feature as its own commit — so `git log` / the GitHub history doubles as a changelog.

## Highlights

**Client — runs on modern Windows**
- No more instant closes / black screen after login (memory-size overflow, CRT crashes, out-of-bounds writes fixed)
- DirectDraw exclusive 800×600×16 mode replaced by a normal resizable window (GDI), borderless fullscreen with **Alt+Enter**
- No external libraries: zlib and libpng replaced by small built-in decoders; static CRT, no DLL dependencies
- Crash handler + `client.log` instead of silent exits

**Client — bigger, nicer view**
- 1280×960 world surface with a 44×44 tile view (was 34×34), slightly zoomed in (`zoom=` in `client.ini`)
- Brand-new HUD drawn at 1.5× scale: wider stat columns, a bigger backpack (4×5), bigger chat, bigger skill/mode buttons, a minimap that doesn't overlap the world, compass centered under the view
- Blue **base values** next to every stat and skill
- **Server Load** shown under Experience
- **Mouse wheel** scrolls the chat, the skill list and the backpack
- Auto-walk markers at the edges of the view, smooth view edge while walking

**Server**
- 64-bit fixes: 8-byte `unsigned long` / `time_t` vs. the 4-byte on-disk and network formats (corrupted packets, broken character records, broken player cap)
- Larger line-of-sight grid and sight radius to fill the bigger client view, symmetric view
- `#shrines <player>` (imp and above): all 20 Kwai shrines + max Seyan'Du sword
- `makegod` tool to give a character god rights offline

## Building

### Client (Windows)
Requires Visual Studio (2019 or newer) with the **Desktop development with C++** workload.

```
cd client
build.bat
```

Produces `merc.exe` (32-bit, no runtime DLLs needed).

### Server (Linux / WSL)
```
cd server
make server
./server
```

God rights for your character (stop the server first):

```
gcc -o makegod makegod.c
./makegod            # list characters
./makegod <name>     # make <name> a god   (-r <name> removes it)
```

## Running

The game **data files are not in this repository** (they're large and part of the original release):

- Client: `gx00.dat`, `gx00.idx`, `pnglib.dat`, `pnglib.idx`, `gfx\`, `sfx\` — put `merc.exe` next to them.
- Server: the `.dat/` folder (`map.dat`, `char.dat`, `item.dat`, …) from the original server release.

Start the server, then the client:

```
merc.exe -h 127.0.0.1 -p 5555
```

(`client/play.bat` does exactly that.)

| Option | |
|---|---|
| `-h <host>` | server address |
| `-p <port>` | server port (default 5555) |
| `-d <folder>` | folder with the game data |
| `-f` / `-w` | start fullscreen / windowed |

`client.ini` (created next to `merc.exe`):

```ini
[display]
fullscreen=0   ; Alt+Enter toggles it in game
smooth=1       ; smooth scaling of the frame to the window
zoom=115       ; world zoom in percent (100 = no zoom)
```

The client speaks protocol version **2.15.1** (`0x020F01`); the server's `MINVERSION` matches, so old 800×600 clients are refused by the modified server.

## Credits

- Original game and engine: **Daniel Brockhaus** (Mercenaries of Astonia, Intent Software)
- Restoration, port and QoL work: Cody (SooperValar), with Claude
