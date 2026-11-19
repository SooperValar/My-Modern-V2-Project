# Changes

Everything changed from the original Mercenaries of Astonia v2 source. The original client was built with Borland C++ 5 against DirectX 3-era DirectDraw; the server was written for 32-bit Linux.

Each section lists its changes roughly in the order they were made, oldest first.

**Contents**
- [Client](#client): [Modernization](#modernization-changes) · [HUD changes](#hud-changes) · [Game view](#changes-to-the-game-view) · [New HUD features](#new-features-in-the-hud)
- [Gameplay](#gameplay): [God / imp / builder tools](#god--imp--builder-commands-and-in-game-tools) · [Commands for all players](#general-commands-for-all-players) · [New zones and areas](#new-zones-and-areas) · [New for players](#new-features-from-a-players-point-of-view) · [Balance and fixes](#balance-changes-and-fixes)
- [Editor](#editor): [Overview](#overview) · [Server manager](#server-manager) · [Builder](#builder) · [Player editor](#player-editor) · [NPC editor](#npc-editor) · [Quest editor](#quest-editor) · [Conversation editor](#conversation-editor) · [Chest editor](#chest-editor) · [Merchants tab](#merchants-tab) · [Quests page](#quests-page) · [History and logs](#history-and-logs)
- [Server](#server): [Modernization](#server-modernization) · [Data changes](#data-changes) · [Server-side view changes](#server-side-view-changes) · [Tools](#tools)

---

# Client

## Modernization changes

Getting the original client to run on modern Windows. The original `merc.exe` would connect and log in, then close instantly or sit on a black screen. Compatibility modes didn't help, because the causes were bugs in the code, not Windows settings.

**Crash / black-screen root causes**

| Problem | Effect | Fix |
|---|---|---|
| `dd.c` sized its sprite cache from `GlobalMemoryStatus()` but allocated from a fixed 20 MB `HeapCreate()` heap. On machines with more than 2 GB of RAM the value overflows. | Heap exhausted → `HEAP_GENERATE_EXCEPTIONS` → instant close; or a negative limit → `free_2nd_cache()` loops forever → black screen | Plain `malloc`, fixed 256 MB cap |
| `sound.c` closed the same file handle twice | Harmless with the Borland CRT; the Microsoft CRT kills the process without a message | Handles start at -1 and are closed once (`sclose()`); a CRT invalid-parameter handler logs instead of terminating |
| Sprites partly off-screen wrote past the frame buffer (`display_alpha`, `display_png`, text output) | Random memory corruption | Bounds checks on all drawing |
| Unknown server data → silent `exit(1)` | Client vanishes with no clue why | Logs the command byte and a hex dump to `client.log`, skips the rest of the tick |

**DirectDraw → software rendering + GDI**
- The game always drew 16-bit RGB565 pixels itself; DirectDraw was only used for the exclusive 800×600×16 mode and surface memory. Surfaces are now plain memory buffers (same pixel code), and the finished frame is converted to 32-bit and scaled into a normal window with GDI (`StretchDIBits`).
- **First start opens wide**: as large as fits, up to 16:9 (it was 4:3, which cramped the HUD panels on a laptop; the world stays 4:3 in the middle and the panels use the room at the sides). After that the window keeps the size and place it was left at.
- Resizable window, remembered position, **Alt+Enter** borderless fullscreen (no display mode switch), DPI aware, 1 ms timer resolution.
- Mouse coordinates are mapped back from window space to game space.

**Replaced Borland-only code and libraries**
- `zlib.LIB` (Borland OMF) → `inflate.c`, a small streaming zlib-compatible inflater. The server sends one continuous deflate stream with a sync flush per tick, so the 32 KB window is kept between calls.
- `libpng.lib` → `pngdec.c` (8-bit RGB/RGBA, gray/palette expanded, interlace supported). Reads straight out of `pnglib.dat`.
- `alloc.h`, `dir.h`, `random/randomize`, `getdisk/setdisk`, `findfirst`, `filelength`, `_export`, CTL3D, `WM_CTLCOLOR` → Win32/MSVC equivalents.
- `MERC.RC` (Borland format with hex-embedded resources) → `client.rc`, with the icon and cursors as separate `.ico`/`.cur` files.
- Login dialog: `EndDialog` was called from the network thread; it now posts a message to the dialog's own thread.
- Load/Save character dialogs use the standard `OPENFILENAME` struct.
- `build.bat`: finds Visual Studio with `vswhere`, builds a static-CRT 32-bit exe with no DLL dependencies.

**Diagnostics and options**
- `crash.c`: unhandled-exception filter (code + faulting offset in `merc.exe`), invalid-parameter, abort and pure-call handlers. Everything goes to `client.log`.
- New `-h <host>` option (the server address used to be compiled in), plus `-p`, `-d`, `-f`, `-w`.
- **Server name and port in `client.ini`**: `[server] host=` and `port=`; the built-in default is now `myv2astonia.duckdns.org` port 5555 (was the original game's `mercaston.dnsalias.net`), so a handed-out client needs no `.bat` file. `-h` / `-p` on the command line still win (`play.bat` uses `-h 127.0.0.1` to play on this PC).
- The client already loads `gfx/NNNNN.png` before its packed files, so new sprites are just PNGs in the client's `gfx` folder.

**Two clients at once (testing)**
- `-m` lets a second client run at the same time (normally only one may run). `-o <file>` gives a client its own options / login file instead of `merc.dat`, so two clients don't share or overwrite each other's character.
- `play2.bat` starts the second client: `merc.exe -h 127.0.0.1 -p 5555 -m -o merc2.dat`. Start the first one as usual (`play.bat`), then `play2.bat`, and log in a different character there. The server allows several connections from one computer already.

**Launcher and updates** (`client/launcher/`, `tools/release/publish_client.py`)
- **Launcher.exe**, what players start: it reads `manifest.txt` from the project's `client-dist` branch on GitHub (over HTTPS), compares each listed file's SHA-256 with the player's copy, downloads what is missing or different, checks it and puts it in place, then starts `merc.exe`. If the site can't be reached it just starts the game. It updates itself too (renames itself to `Launcher.old.exe`, which it deletes on the next start). It never touches the player's own files (`merc.dat`, `client.ini`, `*.moa`, logs) and refuses paths outside the game folder. If the game is open, it asks to close it first. Log: `launcher.log`. `client.ini [update] base=` points it elsewhere (testing), `off=1` turns updates off. WinHTTP is loaded at run time and SHA-256 is built in, so it needs nothing beyond Windows.
- **Publishing an update**: `python3 tools/release/publish_client.py <Client folder> <project> "<version>"` copies the player files (`merc.exe`, `Launcher.exe`, `pnglib.*`, `README.txt`, `GFX/`, `sfx/`) to the `client-dist` branch with a fresh `manifest.txt`, using a temporary index, so the working copy isn't touched; then `git push origin client-dist`. `gx00.dat/.idx` (96 MB, never change) are listed as "base" (must exist) and come only with the zip.
- **Out-of-date clients**: a player whose client is older than the newest published one (`CLIENT_LATEST` in `gendefs.h`) is told in red on every login: "Your game is out of date (version 2.15.01, the newest is 2.15.02). Please close it and start the game with Launcher.exe: it updates the game for you." A client too old to play at all (below `MINVERSION`) is refused at login; from client 2.15.02 on its login window then says "Game too old: start it with Launcher.exe to update." (older clients say their own "Client version too old. Update needed."). When a new client is published, raise `CLIENT_LATEST` to its version.
- **Player zip**: the "MyV2 Astonia" folder with the launcher, the game, its graphics and sounds, and `README.txt` (`client/package/`): start with Launcher.exe, the Windows warning, making a character, saving it as a .moa, updates, problems.

**More sprite numbers (client 2.15.06, Nov 12; published Nov 13 with the world sprites, `MINVERSION` 2.15.06):** the client could only show sprites up to 34,767
(`MAXSPRITE` = 2000+32*1024 in `client/inter.h`); now every 16-bit number, 0-65,535 (`MAXSPRITE` 65536), the most the
server can send. Map, item and inventory sprites are read as unsigned (`common.h` `ba_sprite` / `it_sprite`, `socket.c`
inventory / worn / spells / hand), and every sprite drawing / loading function in `dd.c` refuses a number outside the
table instead of reading past it. Older `pnglib.idx` files (34,768 entries) still load. Server side: see
[Server modernization](#server-modernization). Numbering plan for new world sprites: HANDOFF.md.

## HUD changes

**800×600 HUD (first pass)**
- **Mouse wheel** scrolls the chat, the skill list and the backpack while the mouse is over them (handles fine-grained touchpad wheels).
- **Blue base values**: every attribute and skill shows its base value in blue next to the modified value.
- **Server Load** is shown under the Experience line instead of as a stray "1%" at the edge of the world view.

**HUD v2 (1.5× scale)**

A new HUD drawn on its own canvas (window size ÷ 1.5) and composited over the world with an area-filtered 1.5× scale, so text stays crisp. Magenta `0xF81F` is the transparent key, and mouse clicks go to the HUD where it's opaque and to the world everywhere else. All layout numbers live in `hud.h`, which both the drawing (`engine.c`) and the mouse handling (`inter.c`) use, so they always agree. The original 800×600 HUD code still runs in the background (it owns the game state the panels read); only its presentation is replaced.

- **Stats panel** (top left): attributes, HP/endurance/mana, a 10-row skill list with a scroll column, an Update row, and a current/max block. The columns are name | **blue base** | total | + | − | cost.
- **Backpack**: 4×5 grid of 35-unit slots with a scrollbar (40 slots total), plus the gold buttons.
- **Equipment and character/look panels**: taken from the original HUD art via a legacy-rectangle remap, so they look and click exactly as before.
- **Chat** (top right): 64 columns × 25 lines, wheel scrolling.
- **Weapon/Armor/Experience/Server Load panel** under the chat.
- **Skill and mode buttons** (bottom right): two separate boxes, larger buttons, abbreviated labels.
- **Minimap** (bottom left): 196 units, 2× zoom, kept clear of the world view.
- **Compass**: centered under the world view.
- **Shop window**: centered.
- The carried-item cursor follows the mouse on the new canvas.

**Colours and themes**
- **Colour theme** (`hud_theme` in `client.ini`, default 1): the HUD picture is recoloured when it loads: dark red marble becomes deep neutral grey and the gold borders and labels become tan at the same brightness. The coin icons and the blue background are kept. `hud_theme=0` brings back the original red/gold.
- **Clean theme** (`hud_theme=2`, the default): panels are no longer drawn from the old texture. Panel fills and border lines go into a list of simple shapes that the presenter draws at full window resolution in 24-bit colour, giving flat deep-grey panels and crisp 1-pixel tan lines; only the content (text, items, labels, icons) still comes from the 1.5x-scaled canvas. For the panels copied from the old HUD picture, the picture is classified once into panel area, border lines and labels/icons, so those panels get the same clean look.

**Later polish**
- **Stats panel**: a header row (Base / Total / + / − / Cost), the raise button is green **+** and the lower button red **−**, costs and the Update number use commas, the scroll buttons are boxed with triangle arrows, there is a small gap between the stats and the skills, and the Update button is wider (fits 999,999,999) with the label and number in their own cells.
- **Experience** total is shown with commas.
- **Backpack**: big pieces (walls, trees and other build-mode objects) are shrunk to fit their slot instead of spilling over neighbours. The old 800×600 backpack is no longer drawn under the new HUD, which had leaked big pieces into the gold buttons.
- **Fixed skills** (known, but with a maximum of 1, like a Templar's Meditate) sit at the bottom of the skill list in red, with no raise button or cost.
- **Smooth HUD font**: HUD text is no longer drawn with the 6x9 bitmap font scaled up 1.5x. It is collected while the HUD is drawn and drawn by the presenter with a real font (Consolas by default, `hud_fontface=` in `client.ini`) at full window resolution, ClearType-smoothed, in the bitmap font's own colours, one character per 6-unit cell so every layout and column stays where it was. `/hudfont classic` brings back the original pixel font, `/hudfont smooth` the new one (saved as `hud_font=` in `client.ini`). Tooltips blank out the text of panels under them.
- **Clean line work**: lines are placed where their band really lands at 1.5x (rounded, not truncated, so rows are evenly spaced) and end exactly on the middle of the lines they meet. The coin, equipment and character panels use only their own hand-placed lines (none detected in the old picture, none of a neighbour's), share border lines with the backpack, and copy old-art pixels only from inside their frame, so no bits of the old borders show. The Update button sits under Base and Mod with the points under the rest; only the button itself applies the raises.
- **Logging out**: the window stays open with an **Exit** button and an 8-second countdown, then closes by itself; Exit closes it sooner. The connection is closed quietly after the server's logout message.
- Client fix: the skill list showed the Greataxe skill a second time as a blank row (the old placeholder for skill 36 was still in the client's table).

## Changes to the game view

- The world renders onto a 1280×960 surface with 44×44 tiles (`common.h`, `inter.h`), with the text and alpha-effect math adjusted for the new `TILEX`.
- The outer ring of tiles the server never sends is skipped, and the view edge is masked, so there is no black border and no edge jitter while walking.
- World zoom (default 115%, `zoom=` in `client.ini`) crops into the world surface before scaling, slightly lowered so the HUD has room.
- Auto-walk markers sit just outside the visible edge midpoints and are clickable.
- **Low hitpoints glow**: `/lowhp <hp>` turns on a soft red glow that pulses on the ground under your character while your hitpoints are below that number, a little stronger the lower you go. `/lowhp` alone explains it and shows the current setting; `/lowhp 0` turns it off (the default). The client handles the command itself and remembers it in `client.ini` (`[display] lowhp_hp`).
- **Trees in Hide mode** (F6): trees now drop to a short stump like walls drop to a low block, so you can see past forests (stumps 18190-18202, `tools/sprites/art/stumps/`; client `hide_sprite`). Before, a tree's "low" sprite was the same tree.
- **Tiered items and graves glow** on the ground and in item windows (see [Tiered armor](#tiered-armor)): the client draws a one-pixel outline in the tier colour (`dd_glow_screen`, `dd_glow_world` in `dd.c`).
- **Lit tiles** in build mode show a small warm white dot (sprite 18233, `engine.c`).

## New features in the HUD

- **Item tooltips**: rest the mouse on an item in the backpack, the equipment or an open shop or grave for a moment and a small window shows it: name, weapon/armor value, bonuses (green), what it does when activated, requirements (red when your base values don't meet them, including rank and Seyan'Du/Purple-only items), condition, and value. In a shop it shows the price you'd pay with your Bartering; with a shop open, backpack items show what that merchant would pay, or that he doesn't buy that kind of item; elsewhere the base value. Plus the first lines of the description (up to 6). Answers are reused for 5 seconds. Lines of other panels are cut out under the tooltip in the clean theme. Everything is shown openly, because the same numbers are in `#armor`, `#belt`, `#rings` and so on; a new item flag `IF_NEEDIDENT` (bit 40, unused for now) hides an item's powers until it is identified, for unique late-game equipment.
- **Buff timers**: a small panel between the character panel and the chat lists every spell on you with the time left (m:ss, or h:mm:ss). Harmful spells (curse, stun, warcry) are red, and a buff's time turns red in its last 30 seconds. The client counts down between updates. The panel is hidden when the window is too narrow for it.
- **Hotkeys**: Ctrl+1 to Ctrl+9, Ctrl+0, Ctrl+- and Ctrl+= fire skill buttons 1-12 (left to right, top to bottom), next to the original Shift/Ctrl+F1-F12.
- **Tier colours in tooltips**: the name in the tier colour, then "Rare Fighter, item level 12"; the Epic effect under the bonuses in purple with a short explanation. Five tooltip colours (Common white, Magic blue, Rare yellow, Epic purple, Legendary orange); plain armor shows its name in white. "Damage to attackers" on any item reads "1-N" (the damage is random up to N).
- **Spell scroll marks**: spell scrolls (driver 48) show two small marks on their picture in the backpack, worn slots and shop / grave windows: the god's initial top left (**A** Ankh, **I** Ishtar, **S** Skua; the plain "Spell of" scrolls none) and the **charges left** top right. Worked out from the scroll's power (75 / 150 / 300) and charges, so custom scrolls follow too. The marks are drawn bold with a black outline (letter gold, charges white) so they read over any scroll picture (outlined text is font code +100 in `dd_puttext`; the presenter, `draw_texts` in `main.c`, draws the black ring and then the colour).
- **Equipment compare**: hovering an item you could wear (backpack, shop, grave) adds **"Compared to your <worn piece>:"** to its tooltip, listing only what would change: WV, AV, attributes, hitpoints/endurance/mana and skills, gains in green and losses in red, plus an Epic effect gained (+) or lost (-). "No difference." when nothing changes; "Nothing worn there:" for an empty slot.
  - Rings: two sections, one for each worn ring.
  - Two-handed weapons: against the weapon and the shield together. A shield while wielding a two-hander: "Can't be used with your ...".
  - Not for unidentified items or what you already wear.
  - **Hold Shift** while hovering: the worn piece(s) it would replace are shown beside the tooltip ("Equipped:"), as their own full tooltips. (Fix: they blinked every few seconds while the tooltip refreshed; the client now keeps the last complete answer's worn slots until the new one is complete.) Tooltips can hold 64 lines (was 40).
- **Build mode tooltips**: in build mode the backpack holds build pieces (template numbers, floor sprites, zone flags), not items, so the tooltip showed whatever real item happened to have that number. Now it describes the piece: a template's name, number, sprite, whether it blocks walking/sight, light, driver and description; a floor tile's sprite; a zone flag's name and what it does (`tip_build` in `svr_tick.c`).

---

# Gameplay

## God / imp / builder commands and in-game tools

- **Safety fixes** (hosting review): at most 5 connections at once from one internet address (`MAX_PER_ADDR`); the account name / description texts a client sends always end inside their buffer; the build-mode tile info only for spots on the map.
- **Abandoned new characters are cleaned up**: once a day at 4 o'clock, characters with under 1 hour of play that haven't logged in for 30 days are deleted, each saved first to the deleted-characters backups (restore from the editor's Players page). Staff, imp and god characters are never touched. Console: `charcleanup list` (who would go), `charcleanup` (now). `god_cleanup_new` in `svr_god.c`.
**Build mode**
- **`#build`** starts build mode and explains it in chat: what each page holds, the commands, and how to place (Shift+click) and pick up (right-click) pieces.
- The build pieces are in **numbered pages of 40** instead of one page per sprite number: **page 0** is the flags (zones like indoors, sight block, no-magic and so on), **pages 1 to N** are the floor types, and the **rest are objects** (walls, trees, furniture...). Every placeable item template is collected automatically, with repeats (same name and look) removed.
- Commands: `#build <page>`, `#build next`, `#build prev`, `#build end` (or `stop`). The current page is remembered (`CHD_BUILDPAGE`), and each page change prints "Build page X of N" and what it holds.
- Toggling the **indoors** or **sight block** flag on a tile now recalculates daylight around it (`build.c`), so newly built indoor areas aren't left in shadow. (`#light` fixes areas built before this.)
- `#build` help now says how to remove: left-click a map tile in build mode removes its object/item (the floor stays), right-click places.
- **`#undo`** (builders): undoes the last build action (one click, one removal or one whole area), repeatable; about 20,000 tile changes are remembered. Items removed by the action are re-created from their template.
- **Lit tiles** (zone flag `MF_LIT`, bit 12): the tile is always fully lit, day and night, whatever the lights around it, for a lit spot in a dark area. Only that tile; it doesn't spread. Build page 0 has it as **Lit** (icon sprite 18232, sprites in `tools/sprites/art/lit/`); `#tile` lists it as "lit"; the build tooltip explains it.
- **`#clear`** (build mode, area delete): left-click two corners on the map and every object (walls, tables, columns, ...) and item in that rectangle is removed; floors stay (lay another floor over a rug to remove it). Up to 100x100 tiles; one `#undo` brings it all back; `#clear` again before the second corner cancels; leaving build mode cancels too. Logged (`build_clear_*` in `build.c`).

**Inspecting**
- **`#tile [x y]`** (gods): floor and object sprite, item, flags, light and character on a tile. Typed without coordinates, the client fills in the tile under the mouse.
- Looking at a door as a god or while building shows its lock: locked or not, which key (template, whether it's used up) and the Lock Picking needed (picking works at skill + lock pick bonus ≥ value + 0..19, so it's certain at value + 19).

**Player management**
- **`#shrines <player>`** (imp and above, listed in the imp `#help`): marks all shrines of Kwai as visited and sets the player's Seyan'Du sword to its maximum weapon value. If they don't have the sword yet, they get a new one.
- **`#prestige <player> [n]`** (gods): shows or sets the prestige level and updates the look.
- **`#recall`** (gods) also gives back the temple a player had before entering the labyrinth, and takes away lab items. It now takes you to your own recall point instead of always Aston.
- **Recall points for gods and imps**: they recall (Recall spell, death, `#recall`) to **Elysium, 800,804** by default: at login and when the god/imp flag is given, a god or imp whose recall point is one of the standard temples (Aston, Purple temple, Staffers Corner) gets Elysium instead. A point of their own is kept.
- **`#setrecall <player> <x> <y>`** (gods): sets where a player recalls to and comes back after dying. `here` = where you stand, `default` = Elysium for gods/imps, otherwise their religion's temple (Aston / Purple temple / Staffers Corner); with no position it shows the current one. Refuses blocked tiles; tells the player; logged.
- **`#temple`** (gods/imps) now goes to the Temple of Skua (512,512) instead of 800,800 in Elysium, which `#recall` covers.

**Items for testing and events**
- **`#tier <1-3> <level> [f|m|c|u] [h|a]`** (gods) makes a tiered armor piece; **`#soullevel <level>`** a soulstone of that level; **`#upstone <level>`** an upgrade stone.
- **`#write ["title"] <text>`** (gods, imps): the original `#write <text>` made an untitled "Parchment" and silently did nothing when the text was too long or the backpack full. Now the optional title in quotes is the note's name (default "Note"), the text (up to 199 characters) is what players read when they look at it; too-long text is cut with a message, a full backpack says so. Still the empty parchment (template 132), never decays, logged with its text (`god_note` in `svr_god.c`). (Fix: the first try added it as `#note`, in the wrong letter's block of the command switch, and `#setrecall` too, so neither worked; `#setrecall` is now under "s".)
- **The gods' shops** (`godshop.c`): every item template a player can carry, free, for gods and their helpers.
  - **Categories**, worked out from each item's own data (new items sort themselves); nine at first (weapons 103, amulets 26, rings 40, keys 74, potions 82, quest 50, misc 35 items), ten once scrolls got their own: **weapons**, **belts**, **armors** (helmets, body armor, cloaks, sleeves, leggings, boots; torches and candles, the only left-hand items, count as weapons), **amulets**, **rings** (rings and gems), **keys**, **potions** (potions, flowers and drinks, with the Alchemist; the ales held in the hand used to show up as weapons), **scrolls** (their own merchant, the **Scribe**, template 1189; the spell scrolls are here), **quest** (items some NPC asks for, and labyrinth items), **misc** (the rest, including soulstones, Soul Crucibles and upgrade stones). Map objects (doors, chests, walls...) are not sold.
  - **Unique items are not sold**: everything with the unique flag (Skua's, Gorn's, Kwai's and the Purple One's weapons, the Caps of the Math Genius, the Helm of Shadows, the Ice Gargoyle Cape) and the Grolm Crown (unique in practice, though it has no unique flag). The Fire and Ice sets were unique too until they became rare drops; the god shop sells them now.
  - **Pages**: 38 items per page; the last two slots are "Previous page" / "Next page" arrows (templates 1374/1375, sprites 18230/18231).
  - **Quest items come out inert**: the copy has no template number, so no NPC accepts it as the real thing (its description says so). For the gods' live quests (LQ).
  - **Merchants in Elysium** (character templates 1180-1189, immortal): Armsmaster, Beltmaker, Armorer, Amulet Keeper, Ringmaker, Keymaster, Alchemist, Questkeeper, Curator, Scribe. They serve gods and imps standing next to them; anyone else is turned away ("I only serve the gods and their helpers"). They first stood in a row in Elysium (795-803, 805) and now stand in the god shop hall. They don't buy anything.
  - **`#godshop <category>`** (gods only) opens a category's shop from anywhere; `#godshop` alone lists the categories with their counts.
  - **Logged**: every item taken goes into the character's log and the server log (`GODSHOP: <name> took <item> (t=<template>, <category>)`, with `[imp]` for imps), so imps' use can be checked later.
  - A shop page is filled for each viewer when they look (so tooltips work); taking an item uses the viewer's own page, so two gods browsing at once don't get each other's items.
  - Fixes: a merchant kept the page he had shown before a server restart (it is saved with him), so changes to the shops didn't show until someone turned a page; the kept page now only counts within one server run. `#godshop` opened only once (the client keeps a closed shop shut for a few seconds so late updates don't reopen it; typing `#godshop` now lifts that), and tooltips didn't show in a shop opened from afar (allowed for gods). The client asks to look again every second while a shop is open; a gods' merchant now keeps the viewer's page instead of making all its items again each time.

**`#help`**
- Lists the new commands. Imps: `#recall`, `#temple`, `#shrines`. Gods: `#godshop`, `#soullevel`, `#tier`, `#upstone` (with `#create`, `#setrecall`). Creators: `#clear` (with `#build`, `#undo`, `#tile`, `#light`). `#write` was already in the imp list.
- Also: `#give` (imps), `#lower` and `#skill` (gods) were missing, and `#ggold`'s line was wrong (it is `#ggold <player> <gold> [silver]`).

## General commands for all players

All also work with `/`, and they are listed in `#help`.

- **Item tables**: `#armor`, `#weapon`, `#sword`, `#dagger`, `#twohand`, `#axe`, `#greataxe`, `#specialw`, `#belt`, `#specialarmor`, `#moddedarmor` and `#rings`. They print tables of requirements and bonuses, read live from the item templates so they stay accurate if an item is changed. `#specialarmor` lists the special armor (Fire set, Ice set, Ice Gargoyle Cape, Titanium Armor of Ankh, Winged Boots, Helm of Shadows, Grolm Crown, Cap of the Math Genius) and explains the Fire and Ice set bonuses; `#moddedarmor` lists the magic suffixes (of the Lion, Snake, Owl, Weasel, Bear, Magic, Life, Defence) that chest helmets and armor can carry, with their normal and Godly values. `#greataxe` lists the greataxes (in `#weapon` too) and `#twohand` / `#greataxe` describe the two-handed sword's and the greataxe's specials with your own chance.
- **`#quest`**: the quests of Aston and beyond as a table, easiest first, 15 a page (`#quest p2`, `p3`…): columns `#  Giver  Where  Reward  Exp`, lined up (the chat is 64 fixed-width letters a line; long names are cut to fit; Aston's streets without "Aston, "). Skill teachers come first, ordered by the experience they give (68 to 1,388, which follows how hard their item is to get), then the NPCs who trade an item for an item, ordered by the value of what they give. The place is the street the giver's house opens onto, "Aston, New Street" (`get_area_street` in `area.c`: the building they stand in, the street in front of its doors, else the closest street; outside town the area's name). Only what is left for you: skills you already know and skills your class can't learn are left out (`#quest all` shows every one, marked "learned" / "not your class"). Labyrinth and tower trades are not listed (they are puzzle steps). **`#quest <number>`**: that quest in detail, "Quest 3 of 24: Gunther" then lined-up Where / Wants / Reward lines, their own words (green), whether your class can learn it, and "Give Gunther the Silver Ring to finish it." `#quest all p2` and `#quest all <n>` work on the full list. (It used to print every teacher with its hint at once, too much for new players.)
- **`#exp`**: experience this session and in total, each with exp per hour, unspent points, and how much is left to the next rank.
- **`#played`**: time played this session and in total, and the character's creation date.
- **`#repair` / `#repairinv`**: use the Repair skill on every damaged worn item or backpack item. The first use warns that a failed repair can damage or destroy an item; repeating the command within 30 seconds goes ahead. The Repair skill code was split into `repair_citem()` so the single-item skill and these commands share it.
- **`/lowhp <hp>`**, **`/hudfont classic|smooth`**: client-side settings, see [Game view](#changes-to-the-game-view) and [HUD changes](#hud-changes).
- **`#silver <amount>`**: like `#gold`, but in silver coins (100 = 1 gold), so small amounts can be held on the mouse and handed to an NPC (e.g. 50 silver to the beggar).
- **`#journal`**: lists your quests with the journal text for the step you are at (see [Quests](#quests-and-chain-quests)).
- **`#kills`**: every kill quest ("Kill 5 Spiders"), who gives it and where, the reward, and how far you are ("3/5", "done: return to Gunther", "say QUEST to Gunther", "finished"); see the [Quests page](#quests-page).
- **`#burning`**: shows or hides the "Burning Hits damage inflicted" line (Fire set, 6 pieces); see [Fire and Ice sets](#fire-and-ice-sets).

## New zones and areas

- **Tables and bars with a scroll, readable like signs**: item templates 1409-1416 (Table, Marble Table, Round Table and Bar "with a Scroll"; `tools/world/table_scrolls.txt`), sprites 18290-18297 (the open scroll shrunk onto each table piece and the bar). Look at one to read it; each placed one has its own text, written in the editor's Description of the item.

**Tower floors packed together**
- Tower floors II-XX packed into one compact block (x 822-945, y 337-435), in floor order, five per row. Each floor moved as a unit with its items, NPCs and NPC templates (respawn, rest and patrol positions). Ladder offsets were recomputed and the tower zones in `area.c` moved with the floors. Tower I stays in the Strange Forest. One-off script: `tools/world/movetowers.py`.

**Arena of rank**
- Reopened and fixed (`use_driver.c`). Losing a fight there counts as an **arena death**: you keep your items, and you're locked out for 5 minutes with "You should try again after becoming stronger." (`CHD_ARENALOCK`).
- Rewards that can't be handed out are cleaned up properly instead of being left behind.

**Lab 10, the Seasons Gorge**

The world data held a nearly finished tenth labyrinth part (the "Mages of Time": Spring, Summer, Fall and Winter areas with the mages Flora, Aestas, Casas and Friga, Grolm trap rooms holding the door keys, an inn with merchants) that nothing led into, whose end room was sealed and whose hourglass sprites were missing. It now sits between Lab 9 (Riddles) and Lab 11:
- Lab 9's end portal and the labyrinth gate (after part 9) lead to Lab 10's inn (`use_labyrinth`).
- **All four mages matter**: Top (Flora), Middle (Friga), Bottom (Aestas) and the new **Sands of Time** (Casas, who carried a spare bottom before). Top, Middle and Bottom combine in any order into the new **Empty Hourglass**; with the sands it becomes the **Hourglass of Time**.
- The new **Portal of Time** (item driver 71) at the far end of Winter: the Hourglass of Time opens it for two minutes for everyone, so a group goes through together without waiting for the mages to respawn. It leads into the sealed end room, whose portal marks part 10 solved.
- Hourglass sprites 18121-18128 drawn for it (`tools/sprites/draw_hourglass.py`), as PNGs in the client's `gfx` folder.
- **Shrine of Change** in a small room in the garden past the merchants, built like the merchant rooms, with a path from Spring's main path to its door: the same shrine as at the Final Test entry, with the same notes, so every class can arch at Lab 10 (Mercenaries: a greater healing potion for Warrior, a greater mana potion for Sorcerer; Templars and Harakim: a potion of life). The Final Test one stays (`tools/world/lab10_shrine_of_change.txt`).
- Its labkeeper (the fight after the end portal) was missing too: part 10 now sends a Mage of Time (Friga, without her hourglass piece).
- Three exploration points (45,000 exp, bits 15-17 of the third exploration word) and its shrine of Kwai (bit 20, the template was there but never placed). The shrine stands in the shrine room south of Fall that was built for it, with its Seyan'Du door (`tools/world/lab10_shrine_room.txt`).
- **Merchants**: weapons Steel to Crystal (as before), armor Steel, Golden and Emerald (was Golden only).
- One-off data patches: `tools/world/lab10_open.c`, and `tools/world/place_items.c` with `lab10_extras.txt` (a small tool that makes item templates and places items from a list).

**Lab 11, the Sunken Dark**

A new labyrinth part after Lab 10 (map 180,900 - 299,999). The labyrinth gate after part 10 now leads here (`use_labyrinth`), and after part 11 to the Final Test. Its layout is an Excel sheet (see [Tools](#tools)).
- **Entry hall** (laid out by Cody in the layout sheet): the entry/exit portal on the west wall, a bar in the north-west with the barkeeper behind a north-south counter and the tavern floor (log out there) through a door at its back, an armor shop in the north-east and a weapon shop in the south-east, the offering shrine in the south-west, and the way into the Atrium in the middle of the east wall. A weapon merchant (Steel, Golden, Crystal and Titanium daggers, swords and two-handers) and an armor merchant (Steel, Golden, Emerald and Crystal). Lit, no monsters.
- **Four flooded, dark sections**: the Atrium, the Library, the Crypt and the Cistern. Each hides a *Drowned Tome* in one of its bookshelves (the others hold only rotten pages). Laying the tome on the section's lectern (in hand or from the backpack) drains the water and opens the gate to the next section. **After 10 minutes the water comes back**: a warning a minute before, then the gate shuts (it waits while someone stands in it) and the lectern is empty again, so the next player or group does the puzzle too. New item driver 72 (`use_lab11`, refill through `IF_EXPIREPROC`): lecterns, empty shelves and gates.
- **The Cistern's tome was torn apart**: its shelf, right by the lectern, only holds scraps and a hint. The four torn pages lie in sunken chests around the Cistern (plus some chests with only silt); using one page while holding another puts them together, and all four make the tome (driver 72 kinds 4-6). Torn page sprites 18170-18183 (`tools/sprites/art/pages/`): every set of pieces has a sprite, so when pages are joined the item shows them fitted together (`LAB11_PAGE_SPR`; `tools/world/lab11_page_sprites.txt` sets the four page templates).
- Swimming is underwater (hitpoints drain); dry islands break the swims up, the longest required one is about 20 tiles.
- **No light of your own** in the four flooded sections: new map flag `MF_NOLIGHT` (bit 10) puts out a character's own light (Light spell, torches, lit items) while standing there (`really_update_char`, `plr_map_set`); it comes back on leaving. Stepping in says "You feel your light being suppressed.", stepping out "Your light returns." The entry hall, the vault and the shrine room are exempt. `#tile` shows it as "no light".
- **Faint glow up close**: the sunken chests, the searchable and tome shelves, the exploration points and the cold braziers carry the new item flag `IF_NEARGLOW` (bit 41). They give a faint light (20) only while a player on no-light ground is within 3 tiles (braziers 5; an item's `data[8]` sets its own distance) (`lab_glow_near`, checked on every step and once a second while standing; it goes out a few seconds after they leave). In the dark they have to be found by exploring, not spotted from afar.
- **Braziers** start cold: using one lights it for five minutes. New unlit brazier sprite 18129 (`tools/sprites/draw_brazier_unlit.py`). Fix: removing the flames had left a bite out of the back of the bowl (the floor showed through); the script now draws the back rim across again and fills the bowl's inside, and 18129 was redrawn (a copy is in `tools/sprites/art/brazier/`). Its fire animation (item status 16) only runs while lit; at first the cold brazier also tried to animate, so the client asked for the missing sprites 18130-18133 (`tools/world/fix_item_status.c`). Lit bowls mark the landings, the entry and the vault.
- **Monsters** a step above Lab 10, on the islands only (the water is no-monster ground): Drowned Sailors, Gargoyle Archivists, Crypt Lords, Drowned Knights, Sea Golems and Marsh Shamans (templates 1210-1232, all see in the dark). Undead regenerate 650/1000 hitpoints a tick (about 12 a second), which makes them much tougher than their rank; Lab 11's undead (templates 1200-1259) regenerate 220 instead (`LAB11_UNDEAD_REGEN`).
- **Vault** (a small lit room off the Cistern) with the end portal: part 11 is solved after beating its labkeeper, the **Drowned Lord** (template 1200, `LAB11_KEEPER`), for 210,000 exp.
- Three exploration points (50,000 exp, bits 18-20 of the third exploration word) - one in an Atrium alcove, one in a Library corner, one deep in the Cistern - and the shrine of Kwai (bit 21) in the standard shrine room - red brick walls, two black candles, a Seyan'Du door - set into the Library's north wall.
- `area.c`: the area is named "Labyrinth, Sunken Dark", with its parts: Entry Hall, Atrium, Library, Crypt, Cistern and Vault.
- **Arena deaths while unfinished**: every player death anywhere in Lab 11 (180,900 - 299,999) is an arena death: items and gold are kept and no hitpoints or mana are lost; the message says the lab is still being built (`LAB11_ARENA_DEATHS` in `data.h`, set it to 0 when the lab is done). Two signs ("Sign (Unfinished)", template 1373) stand beside the doorway from the Entry Hall into the Atrium, the first underwater part, at 201,947 and 201,953 (`tools/world/lab11_tbd_signs.txt`).
- Fixes: the lecterns, empty shelves and gates were built with the driver of the item they were copied from (a table, the Lab 9 book shelf, a door), so lecterns did nothing, gates acted as doors and an empty shelf handed out a broken item ("n/a"); `build_lab` can now set an item's driver, and all three use driver 72. The tome's shelf is the only one with the "book on the shelf" look; empty shelves look like ordinary full ones. Every lectern stands right next to the gate it opens (the Crypt's had been back at its entrance, far from its gate at the end of the south tunnel). The Library's shelves stand in straight rows of three with lanes between them, and its islands sit between the rows instead of right behind the shelves. Each Atrium alcove has a row of three bookcases against its back wall, one of them searchable; only one alcove's holds the tome. The solid rock between the rooms is marked indoors as well; at first it was not, so daylight lit it and far-away walls showed up in the dark.

**Elysium (the gods' home)**
- **Rebuilt from a layout sheet** (see [Tools](#tools)):
  - North-east: the god shop hall, the 10 merchants along its walls facing into the room, the trash can, shields and fire bowls.
  - North-west: the monster gallery, moved as one block from the south-east (all 45 NPCs keep their place and facing); its door opens into the shop hall.
  - Main hall: shrine on the north wall between two shields; two portals - west to the Staffers Corner (template 1376), east to the Temple of Skua (512,512, template 1377).
  - East: the old north hall moved here, with its table in the middle and three shields.
  - South: four god vaults off a corridor, each with its own door; their floors never let items decay (no-expire).
  - Zone "Elysium" widened to x 776-821, y 793-824 (`area.c`); minimap and zone map redrawn.
- Elysium's west portal (template 1376) now lands at 802,162 inside the Staffers Corner; it went to 838,160, outside the building (`tools/world/elysium/staffportal.spec`). The Staffers Corner Scroll (template 1114) lands there too (`tools/world/staffscroll.spec`).

**Zone names (`area.c`)**
- **Lab 10** is "Labyrinth, Seasons Gorge", with its parts: Spring (with the Inn), Summer, Fall, Winter and the Hourglass Chamber.
- **Spider Underground** (through the hole in the Abandoned Kwai Clan Hall, Spider Queen) and **Ghost Underground** (through the hole in the Abandoned Gorn Clan Hall, Ghost King) had no name.
- **Aston streets**: Temple Street runs the whole way from the town gate to the Gorn Clan Hall (Rose Street starts south of it), Merchant's Way goes on north of Temple Street up to the mines, and the street around the arena is **Arena Street**, with new street signs where it meets Merchant's Way (plus Merchant's Way signs north of Temple Street; `tools/world/aston_signs.txt`).
- The second **Bank**, across from the Temple of Skua, had no name.
- The shop labelled "Cloth Armor Shop" is Geoffrey's **Crystal Armor Shop** (its sign says so); Ruth's real **Cloth Armor Shop**, across from the Temple of Skua, had no name. On South End, **Gunther's House** and **Robin's House** now have names. So do **Syleia's House**, just south of the Dungeon of Doors, and **Gina's Shop**, right outside the mines.
- **Steven's House** reached into the arena; it now covers the house only.
- **Aston rearranged** (Nov 10): Cody built the new town as a copy in the editor (at x 443-627, y 737-929; the copy is still there) and it was copied over Aston tile by tile (6,816 tiles and their items; `tools/world/town_apply.c` with `tools/world/town_rearrange/town_tiles.spec`): a **Market** square in the middle of town (where the Crystal / Cloth Armor Shops, Sirjan's and Joe's House were), a graveyard with a shrine and the Grave Keeper's house north of town, new houses, and the east side (Jamil's House, the Temple of the Purple One, the Cursed Tomb, the Abandoned Gorn Clan Hall) 2 tiles further east. The holes to Underground I and to the Ghost King, and the ladders back up, still lead to the same places; the Outlaw Hideout's Room 2 ladder now comes up at 488,566 (its old spot is a wall of the Grave Keeper's house). The Cursed Tomb chest moved with its contents. NPCs: the merchants who lost their shops (Geoffrey, Ruth, Sandra, Karl, Gertrud, Brunhild, Antonia, Henry, Hagen) and Sirjan, Jefferson, a Guard and a Janitor wait in the Temple of Skua for their new places; Joe's gang (Joe, James, John, Joshua) waits in the closed new house at 593-598,520-524; Inga lives in Sandra's old Leather Armor Shop; Jamil, the Priest and the Cursed Tomb / Gorn Clan Hall monsters moved 2 east with their buildings (`town_npcs.spec`). Door spots of the NPCs that moved were cleared (Inga uses Sandra's old door, Jamil his moved door; `tools/world/npcdata.c`, `town_npcdata.spec`).
- **Spiders by the town copy removed** (Nov 14): the 7 Spider's Webs at x 491-512, y 740-760 (just north of the editor's town copy at 443-627, 737-929) were already gone, but their 20 spiders (templates 390-392) were still there; removed with `tools/world/remove_npcs.c` (`remove_npcs <.dat> 485 730 520 765 390 391 392`; the web list is `tools/world/spiders_520_777.txt`). The other 70 webs and their spiders are unchanged.
- **Aston's zones after the move** (Nov 10): the **Market** is one zone (541,500 - 569,524, "in the Market"); the Temple of the Purple One, the Cursed Tomb, the Abandoned Gorn Clan Hall and Rose Street moved 2 east with their buildings; Castle Way reaches 2 tiles further east (to 552); **Inga's House** is now the old Leather Armor Shop (between the Temple of Skua and the Thieves Houses), **Jefferson's House** is Inga's old house, **Jamil's House** fits his rebuilt house. The zones of the buildings that are gone were removed (Joe's House, Sirjan's House, the Crystal / Cloth / Bronze / Steel / Golden / Leather Armor Shops, the Weapon Shop, Brunhild's Shop, Jefferson's old house); Cody adds the zones of the new buildings himself.
- **Aston's tile flags after the move** (Nov 10): the copy had brought "indoors", "no fighting" and "no monsters" onto grass and street tiles; they were cleared there (1,261 tiles, by the rule of the original town: those floors never have them; `tools/world/mapflags.c`, `town_rearrange/flagfix_applied.txt`), and "no fighting" was taken off the Market and around it and Joe's gang's house. "No monsters" in the original town is a 1-tile line on the grass around building lots (plus the Purple Temple and the Temple of Skua's aisle); after the cleanup Cody had the stray pieces around the Market, Jamil's House and the new buildings removed (88 tiles, `town_rearrange/nomonst_remove.txt`). The **Guard** who guarded Ruth's old Cloth Armor Shop now guards the **Market**, walking its four corners; the **Janitor** is back on his street loop (Temple Street, Rose Street, Castle Way, Merchant's Way) from 534,547.
- **NPC light duties after the move** (Nov 10): many town NPCs keep up to 4 torches or candles burning by their spot (data 32-35, `driver.c` "activate light"). After the move their spots pointed at removed torches or into other people's houses (Sandra would walk from the Market to Inga's house). Each moved NPC now tends the lights of the room it lives in (Inga, Sirjan, Jamil, Jefferson, Joe's gang, the Priest's fire bowls, the Bartender, a Thief); the Market merchants and the Market guard have none (the Market's fire bowls don't go out), nor do the two south-gate Cityguards (they kept the Temple of Skua's candles), the Begger (Gina's torches) and Thief 970 (`town_rearrange/lights_fix.spec`, check with `tools/world/npc_lights.c`).
- Four buildings west of New Street now have names: **Garna's Shop** (torches, lock picks, flasks), **Manfred's House**, **Leopold's House** and the **Barracks** (Peacekeepers and a Cityguard).
- **Ice Pentagram Quest** was one rectangle that also took in part of the water next to it; it is now two rectangles around the ice only, and the water is named **Underwater Pentagram Quest**.
- The second "Thieves House I" rectangle (20,20 - 49,69) is the thieves' underground area, now named **Thieves Basement**.
- Note: the small "Aston" box at 1,1 - 20,20 is deliberate. Gods are parked at 10,10 while they take over an NPC (`#usurp`), and naming it "Aston" keeps `/who` from showing that.
- **Zones of any shape**: a zone is a name made of one or more boxes. Every box with the same name is part of one zone (e.g. a 3x3 square plus one tile off its corner is one zone, not two), and the game names it once ("in the Aston Hall", never "Aston Hall, Aston Hall"). The zones are now kept in `.dat/zones.dat` (one box a line: `x1 y1 x2 y2 flag name`), drawn in the editor's **Zones** tab; a running game reads them again at once (`zonereload`), no restart. Until the first save there the server uses its built-in table in `area.c` as before. Boxes running past the map edge (Underground I ended at 1024) are cut to the map.
- Zone wording fixed: a zone with "at" after another one said "in Aston, in at Skeleton Lord"; now "in Aston, at Skeleton Lord" (and "on Temple Street").

## New features from a player's point of view

- **The game is called Mercenaries of Asgard v2** (Previously: Asguard in the client's title, MyV2 Astonia in the launcher and README): the window title ("Mercenaries of Asgard v2 (2.15.04)"), the .moa save dialog, the file properties, the launcher, the README and the login welcome line. The world is still Astonia.
- **Missed a lab shrine? Buy a scroll to it**: the Seyan'Du Lord (template 2005, west of the Final Entry; first called Lord of Seyan'du, renamed because the game shows at most 15 letters of a name) sells a Scroll to Lab N's Shrine for each of the 11 lab shrines of Kwai (Grolm, Lizard, Spellcaster, Knight, Undead, Light&Dark, Water, Forest, Riddle, Seasons Gorge, Sunken Dark), 100G x the lab number, no bartering. He only sells one to a Seyan'Du who hasn't found that shrine yet. The scroll takes you into a room north of Lab 7 (x 8-11, y 527-591; Lab 1 nearest the Lord, the top room is spare), facing a copy of the shrine standing against the wall; leave with Recall. A teleport scroll can set the way you face on arrival (data[4], a DX_ direction; `teleport2` / the recall arrival in `svr_do.c`). Merchants now sell display copies exactly as their template is (data and value refreshed at sale). Item templates 1417-1427 (scroll data: x, y, 0, the shrine bit), `tools/world/shrine_scrolls.txt`, `merch.c` (`SHRINE_SCROLL`), his stock in `.dat/merchants.dat`.
- **Send your Ghost Companion at one enemy**: Alt+click the enemy (it turns green), then type `#gca` (or `#gcattack`), or click **Ghost Companion on your spell bar** while your companion is out: your companion attacks exactly that enemy, not another one with the same name (`gc_send` in `talk.c`; it sends every companion you have, ready for more than one per player). Without a selection `#gca` uses the enemy you're fighting. Same rules as telling it by name: you must see the enemy, it must be within 40 tiles of the companion, and you must be allowed to attack it. Casting Ghost Companion this way costs no mana. Client 2.15.03 sends the selected enemy with `#gca` (published Nov 6; `CLIENT_LATEST` is 2.15.03, so older clients are told to use Launcher.exe) (and draws the names over characters after the map, so a wall drawn later no longer hides part of a name: `nameq` in `engine.c`); older clients only have the spell-bar way and "the enemy you're fighting".
### Labyrinth
- Entering a labyrinth part through the gate saves your temple; inside, death and recall go to the start of that part as before. Leaving by the exit portal or solving the part gives the old temple back (Purple One's temple, staff temple, ...) instead of always Aston.
- Lab items (keys, the Hourglass of Time, ...) now also vanish when a player ends up outside the labyrinth by recall, being saved by the gods or the god `#recall`, not only at the exit portal. Death is unchanged: items drop into the grave and stay in the lab.
- Shrines of Kwai: 22 now (20 + Lab 10 + Lab 11), so a Seyan'Du sword goes up to 15 + 22×4 = 103 WV.
- New labyrinth parts: [Lab 10](#new-zones-and-areas) and [Lab 11](#new-zones-and-areas).

### Prestige and prestige looks
- **Prestige** counts how often a character has prestiged: an arch class going back to the start of its class line (Arch-Templar to Templar, Seyan'Du stays Seyan'Du). What triggers it and what it gives are still to be decided.
- **Prestige looks**: prestige 1+ Arch-Templars (blue cape), Arch-Harakim (red cape) and Seyan'Du (amber) get a recoloured look. Base classes keep their normal look. Any class change sets the look of the new class, so a prestiged Templar who arches again gets the cape automatically.

### Greataxes
- New skill **Greataxe** (skill 36; first called Two-Handed Axe). Every class that has Two-Handed has it too, with the same maximum and cost, and knows it from the start (at 4, like Two-Handed). Existing characters get it automatically; it keeps following Two-Handed when a character arches. It uses Strength, Strength, Agility.
- Five new weapons, Bronze Greataxe to Titanium Greataxe, with their own double-bit axe sprites. A weapon flagged both axe and two-handed uses the Greataxe skill.
- **Same stats as two-handed swords, a different special**: greataxes have the same weapon value, Agility/Strength requirements and attack speed as two-handed swords. (At first they had 25% more WV, attacked 3 speed steps slower and needed more Strength.) Each has its own special instead, a percentage, so it works the same from Bronze to Titanium:
  - **Greataxe - Critical hits:** some of your hits do double damage.
  - **Two-handed sword - Deflect:** while you wield one, some melee hits against you are deflected (no damage); both sides get a message.
  - The chance grows with Strength (greataxe) or Agility (sword): see [Rebalance](#rebalance-two-handed-weapons-rings-spells-harakim). At first it was a flat 1 in 8.
  - Only players get the specials (monsters that wield these weapons fight as before). The item tooltip and `#twohand` / `#greataxe` describe them.
- Sold next to the two-handed swords: every merchant that sells a two-handed sword tier now also sells the greataxe of that tier (Karl in Aston, Gertrud, the outpost and lab merchants).

### Tiered armor
The design is in `docs/ITEM_TIERS.md`.
- **Part 1 - Magic (blue), Rare (yellow) and Epic (purple) helmets and body armor**, with rolled bonuses:
  - **Item level 1-20** = the rank needed to wear it. Budget = max(level, 8) x tier step (Magic 1, Rare 2, Epic 3); a point is +1 skill or +1/2 attribute.
  - **Category** Fighter / Mercenary / Mage / Utility (30/30/30/10) decides the bonuses: the main attribute (Strength or Agility, Intuition or Willpower, any of four or a spread, none for Utility; 10% Braveness first) and skills from the category's list. Magic: one bonus; Rare: main attribute + 1-2 skills; Epic: main + secondary + 3 skills; Utility: skills only (1 / 2-3 / 4). Every bonus but the main one gets at least 20% of the rest; a skill rolls at most once.
  - **Hitpoints, endurance and mana** per item level by category (Fighter 1.5/1/0.5, Mercenary 1/1/1, Mage 0.5/1/1.5, Utility 0.5/0.5/0.5) x tier step.
  - **Epic special effect** (weighted by category): Regeneration, Clarity, Stamina, Thorns, Light, Warding, Lasting, Enlightened.
  - The metal follows the item level (bronze 1-6, steel any level, gold 5-14, emerald 9-17, crystal 11-20, titanium 16-20). No wear. Price = the plain piece's price x tier step.
  - **Names**: the full name is built when shown ("Strong Steel Fighter Armor of Resistance": attribute prefix, metal, category, piece, the strongest skill as suffix); the stored name is a short form ("Strong Steel Fighter Armor of Resist") because names hold 39 characters.
  - **Look**: tiered pieces use the old modded armor's "special" sprites (the piece with a red gem): bronze 840/845, steel 830/835, gold 870/875, crystal 850/855, titanium 860/865. Emerald never had one (the old modded emerald helmet showed the armor's picture by mistake), so it gets new ones: 18210 helmet, 18211 armor.
  - **Drops**: a monster killed by a player (or his companion) drops a tiered piece 1 time in 100, a Strong monster 1 in 5 (and rolls its tier twice, keeping the better). Item level = the monster's rank +-1. Tier odds 70% Magic, 22% Rare, 8% Epic (the 1% Legendary goes to Epic until Legendaries exist).
  - **Treasure chests** that gave "of the Lion" style armor give a Magic piece of that metal instead (item level from the metal: bronze 3, steel 6, gold 9, emerald 12, crystal 15, titanium 18, +-1).
- **Part 2 - soulstones, Soul Crucibles, upgrade stones**:
  - **Soulstone on a plain helmet or body armor** (bronze to titanium, emerald too): it becomes a Magic piece, item level = the stone's level (at most 20). "The soulstone sinks into the armor. Magical powers awaken in it."
  - **Soulstone on a Magic, Rare or Epic piece**: rerolls its bonuses (same tier, category, level and Epic effect). The stone must be exactly the item's level. "The soulstone sinks into the armor. Its powers shift."
  - **Soulstones are not used on weapons** for now ("Soulstones can't be used on weapons yet."). Other old soulstone uses (flowers, potions, torches, the other armor pieces) work as before. Legendaries: "This item is too powerful to change."
  - **Soul Crucibles**: Lesser (stones up to level 7), Soul Crucible (up to 14), Greater (any level). Hold a soulstone and use the crucible: the first stone goes in (an empty hand takes it back out), the second makes an upgrade stone. Stones of different levels: a warning first ("The upgrade stone would only be level N. Use the crucible again to combine them anyway."), and the lower level counts. Then use the crucible with an empty hand to take the upgrade stone out; the crucible crumbles. Three ranks: pale blue, violet, gold glow.
  - **Upgrade stone** (the soulstone star in gold): used with a Magic or Rare piece one level below it (a level 13 stone for a level 12 item) raises it one tier, keeping its bonuses and adding a skill (Epic also gets its special effect). "The armor's glow intensifies for a moment. Afterward, you feel it has become more powerful." On an Epic it rerolls the special effect instead. The item's level and rank requirement don't change.
  - **Damor** (Aston, Damor's Magic Shop) sells the three crucibles: 50, 225 and 1,500 gold (placeholders).
- **Part 3 - the Epic effects work**. The strength grows with the item level (1 to 20). Wearing two pieces with the same effect doesn't add up: the best one counts.
  - **Regeneration / Clarity / Stamina**: hitpoints / mana / endurance keep regenerating while moving and fighting, at 10% (item level 1) to 30% (level 20) of the standing-still rate; standing still they regenerate 1-5% faster. Clarity works for every class (all have Meditate; Templars' is fixed at 1, so they get the base rate).
  - **Warding**: a Curse or Stun on the wearer lasts 5-25% shorter.
  - **Lasting**: Bless, Enhance Weapon and Protection cast by the wearer last 20-50% longer (10 minutes become 12-15), Light the same (30 minutes become 36-45). Not Magic Shield, Curse or Stun.
  - **Enlightened**: experience from kills +1-5% (only kill experience, not quests or pentagrams).
  - **Thorns**: the wearer does 1-(level/2) damage to melee attackers, from the best Thorns piece only. **Light** stays on the item; light doesn't add up anyway (the brightest counts).
- **Part 4 - the glow**:
  - **Tiered items glow**: a thin outline, one pixel around the sprite, in a strong tier colour (Magic blue, Rare gold, Epic purple, Legendary orange): on the ground, in the backpack, in the worn slots, and in shop and grave windows. Subtle by design; on the ground it is as dark as the tile, so it doesn't light up dark places.
  - **Graves glow** faint grey-white while they still hold something (items or gold): the grave stone of a player's body, and the body of a monster. Empty ones don't, so you can tell at a glance whether there is anything left - but not what.
- **Soulstones from any enemy**: any enemy a player (or their companion) kills can now drop a soulstone; before, only "Strong" pentagram enemies carried one. The chance follows the player's rank, so new players find them often: 1 in (20 + 6 x rank) kills - 1 in 20 at rank 0, 1 in 50 at rank 5, 1 in 80 at rank 10, 1 in 110 at rank 15, 1 in 158 at rank 23. The stone is made like a Strong enemy's (10-15% of the enemy's experience value, its level from that); Strong enemies keep their own stone and don't roll again. Logged. A grave holding a soulstone glows.
- **Grave glow only for something worth a look**: every NPC grave glowed, because every NPC dies holding the weapon and armor it fought with. Now an NPC's body or grave glows only when it holds something special: a Magic/Rare/Epic/Legendary piece, a unique item, or a magic item in its backpack (potions, scrolls, rings...). Its own fighting gear and gold don't count. A player's body/grave still glows while it holds anything, so players can find their belongings.

### Stacks of potions, combined spell scrolls (TODO 14)
- **Potions stack**, up to 20 of the same kind in one backpack slot (anything used up when used that has no special driver: healing, mana and other potions, Ratling Eye Essence...). The count shows on the item, the tooltip says "A stack of 7 (Ctrl+click: take one)".
- Getting one (buying, a reward, a quest) puts it on a matching stack; putting a stack from the hand on a matching one merges them (what doesn't fit stays in the hand). **Ctrl+click** a stack takes one into the hand, or adds one to the matching stack in the hand (client 2.15.02). Shift+click still moves the whole stack. Using one takes one off the stack. **Selling sells the whole stack** (price x count).
- **Spell scrolls combine their charges**: a scroll put on another of the same spell and power becomes one scroll with both charges (up to 254).
- Kept on the item (`IT_STACK`, a spare field; `stack_*` in `tier.c`). Console: `give <player> <item template> [count]`, `items <player>` (backpack with counts), `useslot <player> <slot>`.
- **Client 2.15.02**: Ctrl+click on the backpack; the Greataxe skill name (built with the BuildKit). Old clients still play (no Ctrl+click), so MINVERSION stays 2.15.01. Published Nov 5.

### Fire and Ice sets
**Fire set for melee, Ice set for casters** (both six pieces: helmet, armor, cloak, leggings, sleeves or gloves, boots)

| | Fire set (623-628) | Ice set (1272-1276, 1407) |
|---|---|---|
| Armor per piece | 9 (as Titanium) | 5 (Steel + 1) |
| Bonuses per piece | Braveness +1, Agility +2, Strength +2 | Braveness +1, Willpower +2, Intuition +2 |
| Needs | Braveness, Willpower, Intuition 30; Agility, Strength 70; Hitpoints, Endurance, Mana 50 | Braveness, Agility, Strength 30; Willpower, Intuition 70; Hitpoints, Endurance, Mana 50 |
| Stealth | -7 per piece | -7 per piece |
| Damage to attackers | 1-3 per piece | 1-2 per piece |
| Light | 220 | 100 |

(Previously: Fire set armor 7, Ice set armor 6, no bonuses, every attribute 30 and Hitpoints / Endurance / Mana 150 (Fire) or 200 (Ice) needed, Stealth -15 (Fire) / -10 (Ice), Damage to attackers Fire 1-2 / Ice 1-3, both unique, value 150,000.)

**Set bonuses**, at 4 and at 6 pieces worn:
- Fire, 4: **Weapon Specialization**, +4 % to the wielded weapon's special (two-handed sword deflect, greataxe critical hits; specials added later for other weapons get it too).
- Fire, 6: **Burning Hits**, each melee hit that does damage burns for an extra 10 % at once (no lasting burn). When a monster you killed took Burning Hits damage from you, your log says "Burning Hits damage inflicted: N."; `#burning` turns that line off and on (saved with the character).
- Ice, 4: **All Spells +5** (every spell skill).
- Ice, 6: **Frost Armor**, 20 % of the melee hits that land on you chill the attacker ("Chilled": Agility and Strength -10 for 5 seconds) and hurt it with a little cold (5 % of the hit).
- Item tooltips show "Fire set: 4 of 6 worn" and both bonuses ("4: Weapon Specialization +4%", "6: Burning Hits (10% Damage)", "4: All Spells +5", "6: Frost Armor (20% Chill)"), green when they apply; `#specialarmor` explains them.

**Rare late-game drops** (no longer unique): monsters worth over 1.5 million exp carry a random Fire or Ice piece in 1 of 1000 spawns. Value 10,000. Gods and imps get them from the god shop; no other shop sells them, and a piece sold to a merchant is destroyed (after the seller's chance to buy it back), so it never shows up in a shop. The three treasure chests that gave Fire pieces (Labyrinth Undead Gorge 27,467, Lizard Temple 499,229, Pentagram Quest 330,304) give a random Magic Emerald or Crystal helmet or body armor instead.

**Ice set pictures and the Cloak of Ice**: the Helmet, Armor, Leggings, Boots and Gloves of Ice showed "Sprite ... is missing": they now have pictures, the Fire set recoloured to ice blue with frost-white flecks (sprites 18100-18104). The new **Cloak of Ice** (template 1407, sprite 18105) makes the Ice set six pieces like the Fire set. Players get the pictures with the next client update.

**Ice Gargoyle Cape** (Previously: Ice Cloak): Syleia's reward for the ice gargoyle egg (template 909), unique and temporary (it melts), is not part of the Ice set and keeps its own stats (armor 15, Magic Shield, Resistance and Immunity +10). Only its name changed (and its description: "A cape made of ice..."); Syleia answers about it when asked about the "cape" too.

### Rebalance: two-handed weapons, rings, spells, Harakim
The design is in `docs/REBALANCE.md`.
- **Two-handed sword around Agility, greataxe around Strength.** The Two-Handed skill now uses Agility, Agility, Strength (was Agility, Strength, Strength); Greataxe Strength, Strength, Agility.
- **Deflect and critical hits grow with the attribute**: the two-handed sword's deflect (from Agility) and the greataxe's critical hit (from Strength) are 8 % + 17 % x A / (A + 40): 11 % at 10, 14.5 % at 25, 17 % at 50, 20 % at 100, 21 % at 150, never quite 25 % (was a flat 1 in 8). The Fire set's Weapon Specialization adds 4 %. The item tooltip and `#twohand` / `#greataxe` show your own chance.
- **Spells around Willpower, Ghost Companion around Intuition**: every spell now uses Willpower, Willpower, Intuition and Ghost Companion Intuition, Intuition, Willpower (all were Braveness, Intuition, Willpower), for every class.
- **Three new stones and golden rings**: **Topaz** (Agility), **Amethyst** (Intuition) and **Diamond** (Braveness), small / medium / big / huge, as the emeralds: the golden rings give +3 / +6 / +9 / +12 (the huge one +24 while active), same values and ranks. A stone on a plain golden ring makes the ring; they need a golden ring (not silver). Found like the others: in the mines (per level the share of stones is spread over six kinds: small stones as many as before, medium and big a little more, gargoyles 15 -> 9 of 30 at the deepest level) and as rare bonus items on monsters. `#rings` lists all six.
- **Spell books** (left hand, with a dagger; no armor): Initiate's (red, rank 2), Apprentice's (yellow, rank 6), Adept's (green, rank 10), Mage's (blue, rank 14), Archmage's (purple, rank 18): Willpower +1 / +2 / +3 / +4 / +5, Blast, Heal, Bless, Magic Shield, Protection and Enhance Weapon +2 / +3 / +5 / +6 / +8 each, mana +10 / +20 / +30 / +40 / +50. All five sold by Damor (a merchant for spell books and staffs may come later).
- **Ghost Companion buffs**: a Harakim holding a **staff** summons a stronger ghost, +15 % power (Arch-Harakim +20 %; every staff's tooltip says so); the caster's **Intuition** adds 1 % power per 10 points; the caster's **Willpower** adds 2 hitpoints per point to the ghost.
- **Ghost Companion follows its master** through portals, teleports, recall, scrolls and god moves, to a free tile next to them, unless it was more than 20 steps away, the player died, or the place is an arena. Before, it stayed behind and destroyed itself after a while, costing the player luck.

### Pentagrams
- **Solve count follows the players doing pentagrams.** It was players online + three random 0-19 (about 28 + everyone online, 54 after a server start), whatever they were doing. Now: for each player who activated a pentagram in the last 10 minutes and is still online (at least 1), 5 + a random 2 or 3 (rolled per round): 7-8 alone, 14-16 for two, 21-24 for three, 35-40 for five. Worked out at every activation, so it follows people joining and leaving; a solve starts a new round with nobody counted. Tunable: `PENTA_PER_PLAYER`, `PENTA_RECENT` in `use_driver.c`.
- **No graves for empty pentagram enemies.** A pentagram enemy whose only belonging is its own weapon leaves no grave; it just vanishes after the death mist, like an NPC with nothing on it. Ones with something else (the Grolm Fighters/Warriors/Knights/Mages carry armor and gold, or a tier drop) still leave one.

### Waypoints
(Live Nov 12; client 2.15.05 published Nov 12, `CLIENT_LATEST` 0x020F05.)
- **A waypoint** is a 3 × 3 rune circle on the ground. Click it to find it ("You found the waypoint Aston, Crossroads."); from then on its circle glows blue for you (other players see it carved and grey until they find it themselves).
- **Travel window**: clicking a waypoint opens a list of every waypoint: a small picture of the place, "Town, Place" and a short line; the ones you have not found show as "Unknown Location" / "???". Click a found one to travel there. Travel is free, and only works while you stand at a waypoint you have found. The mouse wheel or the arrows scroll the list; the X, Esc or walking away closes it. The place you are at is green.
- A found circle glows a little at night (the client never draws its lit pieces darker than light level 6, `WP_GLOW`); travelling plays a sound (`sfx\\19.wav`: the whoosh Cody picked, "scifi anime whoosh 27" by floraphonic from Pixabay, cut to 1.1 s and converted to the game's 8-bit 22 kHz format; the game had no teleport sound) for the traveller and those nearby at both ends.
- The Ghost Companion comes along (as with every teleport). Labyrinth items vanish, as with a teleport.
- Older clients (before 2.15.05) can find waypoints but are told to start the game with Launcher.exe to travel.

### Merchants
- **Merchants are easy to see**: merchants (all 63 of them) had Stealth around 160, so players had to walk right up to them before they showed. Their Stealth is now ignored: they show from as far as any character with no Stealth (light and line of sight still count).
- **Stock**: by default a merchant keeps in stock his sale list (at most 10 items) plus everything in his template's backpack, and restocks whenever his shop is opened. A merchant can also be given his own list (up to 240 items), his own prices and what he buys in the editor's [Merchants tab](#merchants-tab).
- **Pages**: with more than 40 things, the shop shows 38 a page and the Previous / Next page arrows (like the god shop); each player turns his own pages.
- **Seller's remorse**: what a player sells shows after the stock, and the seller can buy it back for what he got until he looks at someone else (or 10 minutes pass). Then the merchant keeps it at his normal price, or throws it away if he would not sell it (Fire / Ice pieces, damaged items, items marked to be destroyed in shops). Up to 62 such items a merchant.
- **The Market's merchants, one tier each** (Nov 10): armor - Ruth (Cloth), Sandra (Leather), Antonia (Bronze), Henry (Steel), Hagen (Golden), Brunhild (Emerald), Geoffrey (Crystal), **Tabor** (Titanium, new); weapons (dagger, sword, two-handed sword, greataxe of one metal) - Karl (Bronze; he used to sell Bronze, Steel and Golden), **Garrett** (Steel, new), **Lionel** (Golden, new), Gertrud (Crystal), **Martin** (Titanium, new). Titanium armor and weapons were sold nowhere before. Character templates 2012 Garrett (Harakim look), 2013 Lionel (Mercenary look), 2014 Martin and 2015 Tabor (Templar look), placed by Cody in the editor; their stock lists and Karl's are in `merchants.dat` (`tools/world/town_rearrange/market_merchants.spec`, `merchants_add.txt`).

### New characters
- All six starting templates (Mercenary, Templar, Harakim, male and female) now start wearing a full set of cloth armor (helmet, armor, sleeves, leggings, boots, cloak; they had only the armor) and with 5 gold (was 2).

### Quests and chain quests
NPCs can now hold real conversations and run quests made in the editor (see [Quest editor](#quest-editor) and [Conversation editor](#conversation-editor)):
- **Talk to NPCs**: an NPC can answer what you say, react to items or money you hand it, greet you differently depending on your quest progress, rank, skills or money, and give rewards: items, experience, money, luck, a skill, a teleport, or a spell cast on you.
- **Quest chains**: each character has 255 quest steps. One quest's end can start the next (bring a potion → then kill Argha the thief → then bring the Spider Queen's head ...).
- **Kill quests**: "kill Argha" or "kill 5 spiders in the Kwai hall" count only while that quest is active, and count for your group members who can see you too. "Spider: 3/5" progress messages.
- **Quest rules on items**: a portal can lead somewhere else depending on your quest step, a door can open only after a quest, a lever can hand out a quest item once per character.
- **`#journal`**: your quests with the text for the step you are at.
- **Identify, Light and Recall are fixed at full strength**: a player who knows one (learned from a quest, or known from the start) has it at 250, the most any skill can be, and can't raise it; the skill list shows it in red at the bottom like a Templar's Meditate (`FIXED_SKILL_VALUE`, `really_update_char`; applied to existing characters at their next login). At 250 Light and Recall are at their strongest (Light already maxes out at about 63, Recall is fastest from about 204) and Identify works on everything but items of power over 375. Exp already spent raising them is not given back.
- **{skill} and {item} in an NPC's greeting** (its text line 2, the "Says" on the Quests page, also shown by `#quest <n>`): {skill} names the skill it teaches this player next (class rewards), {item} the item it wants. Ingrid's and Gordon's greetings were the codes "#stunspec" / "#cursespec", which only the game's hidden code turned into "I'll teach you Stun / Immunity"; they are now normal texts with {skill} ("Hello, %s. I'll teach you {skill}, if you bring me the potion from the Skeleton Lord."), set with `tools/world/npc_text.py`, and the hidden code is gone. Console: `greettext <player> <NPC template>`.
- **Warrior-Mercenaries** start Immunity and Surround Hit at 4 (the male template had 3, the female 4; `tools/world/warrior_start.py`). Characters who already arched keep their values.
- **Greenling eyes work like Ratling eyes**: the full Greenling Eye Collector becomes a **Greenling Eye Collection** (new item 1408, the full collector's picture) instead of the Greenling Eye Essence at once; Robin takes it for the essence (his second quest, template 2004; set its times and exp on the Quests page). Collectors already in the world were changed too (`tools/world/greenling_collection.txt`, `fix_collectors.py`).
- **Ingrid and Gordon** (Stun and Curse teachers): the original game's code taught Templars and Arch-Templars Immunity / Surround Hit instead, and Seyan'Du Stun / Curse first and Immunity / Surround Hit on a second turn-in. The same rules are now class rewards you can see and change on the Quests page (`tools/world/ingrid_gordon_classes.txt`); the hidden code is gone. A skill teacher now also refuses a skill the player's class can't learn ("I cannot teach Stun to one of your kind") and gives the item back.
- **Rewards by class**: an item quest or a conversation line can teach a different skill or give a different item depending on the player's class (any classes picked in the editor).
- Example (a beggar near the temple): different greetings by rank and Bartering; 150 silver from a low rank gets Bless, Protect and Enhance; a small amount, or money from a high rank, gets a thank-you; "tip" takes 50 silver and gives the tip.

### Chests
- **Editor chests** (MyV2 chests) give a reward drawn by chance each time they are opened. Rewards can mix items, gold, newly made **tier armor** (chosen tiers, level range and metals), **items given only once on the whole server**, and "nothing".
- **Once per player**: a chest can give each player something only once.
- **First-time reward**: the first time each player opens such a chest, they get its special item instead of a draw. New players can each take theirs one after another, even while the chest is open and empty for everyone else. A first opening of a closed chest opens it, so it stays empty for its refill time like a normal opening; after that the player gets the normal draws like everyone else.
- A full backpack keeps the chest closed so you can come back.
- **Chests can be turned** between the game's own two looks: lock facing south or west.

## Balance changes and fixes

- Hitpoints, endurance and mana can go above 999 (cap 9999).
- Armor and weapon value cap raised from 250 to 9999. Skills and spells keep their original limits.
- Templar and Arch-Templar templates start with **Meditate fixed at 1** (maximum 1, so it can't be raised). Its real value still grows with Intuition and Willpower, which gives Templars a little mana regeneration. One-off patch: `tools/world/templar_meditate.c`.
- Female Templars raised Heal at cost class 7 while male Templars paid 3 (a template data error). Every Templar and Arch-Templar now gets the cheap rate, applied automatically to existing characters.
- A huge sapphire on a silver ring now gives the correct "too powerful" message (a 499 → 489 typo).
- Spell slots are bounds-checked against `MAXITEM`.
- `#recall` (gods) also gives the old temple back to a player taken out of a lab.
- **Gold is looted automatically**: the gold a monster carried goes straight to the player who killed it (or whose Ghost Companion or other follower did), with "You take 1G 20S from the Thief.", instead of lying in its grave. Not for players killed, merchants or arena fights.
- **Damage to attackers** (items, and the Epic effect Thorns) now hurts the attacker on every melee blow that lands, also when your armor stops all of its damage (before: only blows that hurt you). It still adds up over the worn pieces (a full Fire set does 1-18).

---

# Editor

## Overview

The **MyV2 Editor** is a map, NPC, quest and player editor in the browser (`tools/mapedit/mapedit.py`, also in the Windows Server folder). Python standard library only.
- Run it in the Ubuntu server folder: `python3 mapedit.py` (or the full path to it), then open http://localhost:8080. If that port can't be used (with WSL's mirrored networking, Windows can reserve 8080), it takes the first free one from 8090 to 8099 and prints which; `--port <n>` picks one.
- Named "MyV2 Editor", with the game's own icon (the client's `res_icon_1.ico`) in the corner and as the browser tab icon.
- **Layout** (after Cody's mock-up): a top bar with search (Ctrl+K: places, NPCs, players, items, or "x y") and the server status ("Server up · n online" / "Server stopped · editing on"); a left rail (Map, Players, NPCs, History, Server, Help); the piece library with tabs and the chosen piece below it; the map with a toolbar, area name labels and a minimap (M = big world map); the right panel with the selected tile, layers to show, flag overlays, the keys, and Save to the game / Discard / Undo last save.
- **Live editing while the server runs**: floors, objects, items, flags, portals, NPCs (place, move, turn, remove) and NPC and item templates all go straight into the running game, and players see them right away. The banner turns green ("Live editing"). There is nothing to save, and Ctrl+Z / Ctrl+Y undo and redo. How it works is under [Server · Data changes](#data-changes). Needs the new server (once: "Update code & restart"); with an older server running, the editor stays view-only and says so.
- With the server stopped, changes are saved to the game files with **Save to the game**.

## New ground (world sprites)

New floor tiles made from the game's own tiles (`tools/sprites/world_ground.py`, Nov 13), each with **4 variants** (a floor
brush paints them at random) and **soft edges into grass**:
- **Path** (35000-35003): brown earth with the grass tiles' own grain, no shiny pebbles or clumps. **Dusty path**
  (35100-35103): the same, lighter. **Clear water** (35500-35503): the game's dark water made lighter and clearer, with
  light wave lines (the game's own water stays as the "deep" water).
- **Soft edges:** 46 edge tiles per ground (35004-35049, 35104-35149, 35504-35549): grass with the ground creeping in
  from the sides / corners that border it, dithered, seamless with the plain tiles. The editor places them by itself:
  after any floor change, every grass tile (551-554) or edge tile next to a changed tile gets the edge tile that fits its
  neighbours, or plain grass again when the ground was painted away (in one undo step with the painting). Between
  two grounds a grass tile shows the edge of clear water first, then path, then dusty path. The map shows the variants
  and edges at once while painting (the page picks the variant and draws the edges as the save will), not after the save.
- **Desert (Nov 13):** four sands, each with 4 variants and soft grass edges: **pale sand** (35200+), **golden sand**
  (35250+), **dune sand** with faint wind ripples (35300+), **red desert** (35350+). Between grounds the edge order is
  clear water, path, dusty path, then the sands.
- **Cacti** (`tools/sprites/world_plants.py`, 38000-38006, black spines): saguaro with two arms, left arm, right arm, no
  arms; barrel cactus with flowers and without; prickly pear with fruit. 32x64 like the game's trees; drawn into the tile
  and block walking. Editor: Map → Objects, "New plants" at the top.
- **Area brushes** (Areas tab, built in): **Desert** (golden sand), **Pale Desert**, **Desert Dunes** (fewer cacti) and
  **Red Desert**: the sand at random plus cacti scattered (kept apart), with the grass edges around the painted area.
- **New walls (Nov 13, `tools/sprites/world_walls.py`):** eight materials on the game's own wall block (the outline and
  grey cap of wall 1200: a lit left face, a shaded right face; courses line up from tile to tile), each in 4 variants and
  each **clean and with grain** (the grain like the game's painted walls): Sandstone (36000 / grain 36004), White Temple
  (36010 / 36014), Red Brick (36020 / 36024), Mossy Stone (36030 / 36034), Cracked Stone (36040 / 36044), Dark Slate
  (36050 / 36054), Timber-Framed (36060 / 36064, braces on half the variants), Fieldstone (36070 / 36074). Editor: Map →
  Walls, "New walls" at the top; each paints its 4 variants at random, drawn into the tile, blocking walking and
  sight like the game's walls (an object brush can now carry variants). The list is `tools/sprites/world_walls.json`
  (built into the editor as `WORLD_WALLS`).
- **New floors (Nov 13, `tools/sprites/world_floors.py`):** seven floors, 4 variants each, clean and with grain, the
  patterns along the map's axes so planks and joints continue from tile to tile: Oak Planks (37000 / grain 37004), Dark
  Wood Planks (37010 / 37014), Flagstone (37020 / 37024), Checkered Marble (37030 / 37034), Terracotta Tiles (37040 /
  37044), White Marble (37050 / 37054), Stone Setts (37060 / 37064). Editor: Map → Floors, "New floors" (each paints its
  4 variants at random, like the game's floor sets). The list is `tools/sprites/world_floors.json` (`WORLD_FLOORS`).
- **New doors (Nov 13, `tools/sprites/world_doors.py`):** eight styles on the game's own door shapes (the slab of Unlocked
  Door I / II, closed and swung open; the texture on the door's face, its edge plain): Oak (36500), Dark Wood (36510),
  Iron-Bound (36520), Iron (36530), Temple (36540), Sandstone (36550), Iron Gate (36560, see-through bars), Curtain
  (36570); each +0 closed I, +1 open I, +2 closed II, +3 open II. Templates 1440-1455 ("Oak Door I", "Oak Door II", ...:
  copies of Unlocked Door I 22 / II 84, so they open, close and lock the same way), from `tools/world/new_doors.txt`.
  The **Seyan'Du Door's other facing**: the game had it only as a Door II (915 / 916); the game's two facings are mirror
  images (1216 is 1212 mirrored), so 36580 / 36581 are 915 / 916 mirrored, template 1456 (a copy of the Seyan'Du Door
  559, same driver), for walls running the other way.
- Editor: Map → Floors, "New ground · soft edges into grass" at the top. The sprites are loose PNGs in `Client\GFX`
  (published with the next client update; they need client 2.15.06, numbers above 34,767).
- The edge table is `tools/sprites/world_ground.json` (also built into the editor as `WORLD_GROUND`): re-run
  `world_ground.py <Client folder>` after changing the look, then rebuild the table into `mapedit_template.py`.

## New fences (Nov 14)
- Six new fence types beside the game's red Wooden Fence, on its layout (the fence on the tile's middle line; two straight pieces and four corners, each followed by its hidden-walls copy): **Split-Rail Fence** (weathered posts, two rails), **Wattle Fence** (woven sticks between stakes), **Wrought Iron Fence** (black bars with spear tips), **Low Fieldstone Wall** (knee-high dry stone), **Log Palisade** (sharpened logs, man-high; blocks sight too) and **Hedge** (trimmed, waist-high). Sprites 40100-40211 (`tools/sprites/world_fences.py`): type t from 40100 + 20t; +0 along y, +2 along x, +4/+6/+8/+10 the corners (left: -y and -x, right: +y and +x, top: -x and +y, bottom: -y and +x), each N+1 its copy.
- **Brown Wooden Fence**: the game's red picket fence (1172-1183) recoloured to brown wood, same shapes and shading: 40220-40231 in the game's order (`tools/sprites/brown_fence.py`).
- Editor: Objects tab, section "New fences" (WORLD_FENCES).

## Window walls (Nov 14)
- Every new wall material (Sandstone, White Temple, Red Brick, Mossy Stone, Cracked Stone, Dark Slate, Timber-Framed, Fieldstone; clean and grain) has a **window** in the game's own style: the block with an open slit through it, like the Red / Grey Brick window (1218) - a top slab over a low block whose top is a plain sill (no bricks or stones on it, as in the game), and you see through the gap. One piece works in a wall running either way. Placed with "blocks walking" only (not sight), like the game's windows.
- Sprites 36600-36663 (`tools/sprites/world_windows.py`, made on the game's own 1218 / 1219 shapes): 36600 + 4k the window, +1 its **cut-down hidden-walls form** (a low slab, like 1219); +2/+3 the same pair again (numbers kept from a first draft).
- **Windows for the game's own walls too**: the game had them only for Grey Brick (1218), Red Stone (1232) and Marble (1168 / 1170). Now every other wall has one, cut the same way from the wall's own picture with a plain sill in its colour: Greek Wall I-III, the three Mine Walls, Stone Wall I-V and the pebbled Dark Stone Wall, Black Stone, Brown Stone, both Lava Walls, the Black Stronghold walls (plain, with holes, with embers), Dark Stone, Earth Wall I-II and the Green Glowing Stone Wall. Sprites 36700-36757 (`tools/sprites/game_wall_windows.py`): 36700 + 2i the window, +1 its hidden form (the wall's own cut-down picture). Not done: pillars, arches, the Black Stronghold buttresses and the magic gates (not plain walls), and the cobwebbed walls.
- Editor: Walls tab, section "Windows": the game's 4, then the game's other walls, then the new walls (49 in all).

## The Wolfwood: Cody's area, the wolves and Huntmaster Edda (Nov 15)
Cody made the area (zones "Eastern Forest", "Deep Forest", "Dire Wolves Den", "Wynn & Edda's Hut"); Claude placed the NPCs (`tools/world/wolfwood/place_wolfwood.py`, then `off_road.py`):
- **44 Grey Wolves** (Sergeant) spread through the Eastern Forest, none within 3 tiles of its road.
- **31 Dire Wolves** (Master Sergeant) in the Deep Forest and the Dire Wolves Den, thicker the closer to Old Greyfang (`add_wolves.py`: spots weighted by the distance to him, closer together near him): 7 within 10 tiles of him, 4 at 10-20, 11 at 20-35, 9 further out.
- **Old Greyfang** (First Sergeant) at 414,541 in the den.
- Every wolf is its own template (from the Spider, not "simple"), wolf group 33, and carries its head (Greyfang his fang).
- **Huntmaster Edda** (a Templar woman: kindred Templar + female, the female Templar look 8144) in Wynn & Edda's Hut at 514,654, with her item quests (`#quest`): Wolf Head 150 exp + 0.75G, Dire Wolf Head 400 exp + 2G (10 heads = one standard quest, 5% of the rank's climb; the Quest Planner's per-head share is 0.5% now) (both as often as you like, from Sergeant / Master Sergeant), Greyfang's Fang -> Greyfang Amulet and 14,000 exp (once, from First Sergeant; no gold).
- **Wynn** is a Harakim woman now (kindred Harakim + female, the female Harakim look 6096).
- NPC templates 2057-2100 and more (`made.json`).

## The Wolfwood: taken out again, Cody builds the area (Nov 15)
A first Wolfwood (forest, trail, Hunters' Lodge, 16 Grey Wolves, 9 Dire Wolves, Old Greyfang, Huntmaster Edda and her head bounties) was built and then taken out again at Cody's wish (`tools/world/wolfwood/clear_wolfwood.py`): the map is back as it was before, the NPCs, their templates, Edda's quests and the zones are gone. Cody makes the area himself; then Claude places the NPCs (the build script's NPC and quest part can be reused: `build_wolfwood.py`).
- Kept for then: the sprites (Grey Wolf 43000, **Dire Wolf 43500** (dark, bigger), **Old Greyfang 44000** (pale, biggest), item pictures **Wolf Head 44500**, **Dire Wolf Head 44501**; published) and the item templates 2016-2019 (Wolf Head, Dire Wolf Head, Greyfang's Fang, Greyfang Amulet +2 Bravery +2 Agility), Sign (Wolfwood) and Pile of Bones (bones picture 418).
- Tools: `make_creature.py --tint Main=rrggbb,...` (a coat colour), `tools/sprites/head_icon.py` (an item picture of a creature's head, cut from the model).
- The test Grey Wolf (2057) went with it.

## Test: the first 3D-rendered monster, a Grey Wolf (Nov 15)
- **Sprites 43000-43447**: a full animated character set (standing and walking in 8 directions, the 16 turns, 8 actions in 4 directions: bite, sniff the ground, flinch) rendered (with the ground squeezed towards the viewer, so the far paws stay on the game's flipped-sprite shadow, and the ground 3 pixels lower than first, row 59, where the shadow lies) from the Quaternius "Ultimate Animated Animal Pack" wolf (CC0, glTF in `MyV2\3d Models\`) at the game's camera (30 degrees down, 64x64, lit from the upper left, dark edge, fur grain that moves with the body). Published with client 2.15.07 (Nov 15).
- **Its own shadow**: the game's shadow is the sprite flipped upside down under the feet, which works for upright figures but put a long animal's body shadow below its paws (it looked like floating). The wolf frames carry their own soft shadow, the body pressed flat under it (half-transparent pixels), and **client 2.15.07** skips the flipped shadow for sprites 43000-49999 (`dd_shadow`, dd.c). Players need 2.15.07 (or they see both shadows); published, and CLIENT_LATEST 0x020F07 tells older clients to update (after the next update-code).
- **Tools**: `tools/sprites/glrender.py` (a small glTF renderer: skinned animation, no Blender needed) and `tools/sprites/make_creature.py <model> <base> <out>` (the frame layout: engine.c eng_char, svr_act.c act_turn_*). The same pack has a fox, husky, deer, stag, bull, horse and more, so other animals can be made the same way.
- **One test wolf** (template 2057, from the Spider 392, same strength; not "simple animation", so a usurped wolf can pick up, drop, give and use) in the field by the east road at 532,624 (`tools/world/wolf/test_wolf.py`).

## Fix: quest items that vanished (Nov 15)
- Red Harlan's Head, the Stolen Ledger, the Bundle of Moonwort, the Foreman's Seal, the Chieftain's Stone Axe, the Stoneskin Potion and Greyfang's Fang were made as copies of labyrinth items and kept their "labyrinth item" flag, so the server took them away from any player outside a labyrinth (they vanished on pick-up; only the console test worked). The flag is off on the templates and on every copy in the world; the build scripts clear it now. Found through the editor's new "(Quest)" mark (Stoneskin showed it).

## Editor: quest items marked "(Quest)" (Nov 15)
- Everywhere an item is picked (rewards, a merchant's stock, chest rewards, quests, an NPC's items) and in a merchant's stock list, a quest item shows **(Quest)** in orange: an item some NPC wants for a quest, or one a labyrinth needs.

## Area clears: average monster rank and a suggested reward (Nov 15)
- Each area on the Quests page shows **Average rank of monsters** (the ticked NPCs' ranks, averaged) and the list goes from the lowest to the highest.
- **Suggested reward**: a quest's share of that rank's climb, by how many monsters it takes: up to 10 = Small (3%), up to 25 = Standard (5%), more = Big (7%), rounded; **Use it** puts it in the exp box (then Save).

## Chain quests in #quest and in the Quests page's list (Nov 15)
- Each chain quest has a name of its own that says which chain it is: quest 4 is the **Quarry Chain Quest**. `#quest` shows that name in the list (the giver is in `#quest <n>`).
- The Quests page's list stays slim: the **Settings ▾** button (was "Times · rank", with a short summary under it: "once · Sgt+", "chain") opens a quest's settings under its row: times, ranks, rewards turn-in by turn-in, class rewards; for a chain quest: each part's journal line, reward and rank, which ranks #quest lists it for, and a button to the giver's Conversations. The chain row itself is just its name, "chain quest, 2 parts", and the total exp.
- **#quest** lists chain quests too (a quest number with a name, a giver and journal steps in npctalk.dat), **one part at a time**: the row is the part the player is at (its giver, where, the first reward of that part, its exp), marked **»** ("» a chain quest: one part at a time"). Once a part is done the next one shows; when the last journal step is reached it's done (blue with `#quest all`). **#quest <n>** on one: its name, "a chain quest, part 1 of 2", the giver and where, **Now:** the journal line of that part, its rewards (each item with how many, the exp), its rank, "Talk to Brann. #journal shows how far you are."
- How it reads the lines: the **giver** is the NPC whose line sets the quest to its lowest value; a **part** is a journal step but the last; its **rewards** are the "give item" / "give exp" of the lines that fit that step and move the quest on; its **rank**: those lines' "rank >=" (Brann's axe: First Sergeant).
- The editor's **Item quests** list shows chain quests among the others (same order, ▲▼, Listed): the giver, where, the name and each part's journal line, each part's rewards and exp; **Times · rank** says "chain quest · its lines" (opens the giver's Conversations, where its items and rewards are set) and has a rank range for who #quest lists it for. Kept in npctalk.dat as `corder <quest> <place>` (-1 = not listed) and `crank <quest> <lowest> <highest>` (npctalk.c, svr_do.c).

## Gold only for bounties (Nov 15, Cody's rule)
- Quests that give an item or a skill give no gold; only bounties (heads, as often as you like) pay gold, or a quest whose only reward is gold. Old Greyfang's fang lost its 700G; the Quest Planner's Gold column now fills in only for "Per head" rows.

## Quest givers made friendly (Nov 15)
- Tobias, Wynn, Brann and Huntmaster Edda were copies of Jamil (template 25, alignment -750, as in the original game). They are 10,000 now, the game's mark of a shopkeeper or quest giver: area spells leave them alone and killing one costs the killer luck. (Alignment doesn't decide who can be attacked; the editor's hint for it says what it does now.)

## Editor: an NPC's class and look together (Nov 15)
- In the NPC editor's General tab: **Class** (Mercenary, Templar, Harakim, Seyan'Du, Arch-Templar, Arch-Harakim, Warrior, Sorcerer, or no class for monsters and animals) and **man / woman** set its kind (kindred) like a player's; then **Base look**, the game's own look for that class; then **Cosmetic look**: tick "own look" and pick it with **Choose a look**: a list with a picture of every look an NPC has in the game (and the class looks), named by the NPCs that have it, with a search (wolf, guard, Inga...); only when it should look different (a recoloured monster, a wolf). Changing the class changes the look too, unless it has its own. The old number field "Class" is called **Monster class** now.

## Editor: erase a rectangle (Nov 15)
- A new tool next to the eraser, **Erase a rectangle** (key **R**): drag over an area and its walls, objects and items go (floors stay), like the rectangle tool paints. Shift+drag with the eraser does the same.
- The brush card at the bottom left hides on the Zones, Waypoints and Merchants tabs (it stayed stuck there).

## Item quests can give several of their item (Nov 15)
- On the Quests page, **Gives item** has a **count** in front of it (1-50, "3 × Potion of Second Wind"): the first reward hands over that many (Wynn gives 3 Potions of Second Wind). The NPC says "Here are 3 of my Potion of Second Wind in exchange."; `#quest` shows "3 Potion of Second Wind". Later steps give one. Kept in `npctalk.dat` as `qcount <template> <n>` (npctalk.c, svr_do.c).

## Editor: map view layout (Nov 15)
- **Save to the game, Discard and Undo last save** sit in the top bar, left of the server status (with the unsaved-changes count, and Relight the world when it is offered).
- **Show & flags**: a round button (an eye) with the view buttons at the top right of the map. Click it to open the Show and Show flags checkboxes in a panel under it, and again to close it (remembered in this browser).
- **The right panel** is for what you select: the **Selected** section shows the picked tile and everything on it that can be changed. **Keys** are always shown at its bottom.

## Editor: tabs as columns (Nov 15)
- In the Map's left panel the tabs (Builder, Floors, Areas, Walls, Objects, Items, NPCs, Merchants, Flags, Zones, Waypoints) are a column, and the open tab's categories a second column. Only the picked category shows; the editor remembers the pick per tab. While searching, every category shows and a click jumps to it. A tab with one category has no second column.
- **Builder**: Flags, Floors, Walls, Objects, Items - each with what you used lately of that kind (remembered in this browser, up to 120).
- **Floors**: **Areas** (rugs, and floor sets: your mixes and the game's own sets), **Floors** (inside: the new floors and the game's floors that lie mostly indoors), **Grounds** (outside: the new grounds and the game's floors that lie mostly outdoors), **Tiles** (the rest: used both inside and out, or not at all).
- **Walls**: **Walls** (building and cave walls, the new walls), **Webbed Walls**, **Windows**, **Trees** (the game's and the new ones), **Columns**, **Misc.** (arches, gates, rubble...).
- **Objects**: **Chests**, **Scatter Brushes**, **Torches** (candles, braziers, lamps, lights, fires), **Fences**, **Plants**, **Webs** (webs on their own and webbed objects), **Transport** (portals, holes, ladders), **Doors**, **Signs**, **Mines** (what players can mine; walls that can't be mined are in Walls), **Misc.**
- **Items**: **Weapons**, **Armor**, **Rings**, **Jewelry**, **Quest** (items an NPC asks for, labyrinth items), **Potions** (potions, flowers, drinks), **Scrolls**, **Keys**, **Misc.** Sorted from each template's own data, so new items find their place.
- **Labyrinth items placed elsewhere**: picking one asks whether to keep the flag that makes it vanish when its carrier leaves the labyrinth; by default the placed copy goes without it.
- **One cell per picture**: pieces that look the same in the same category are one cell (chests with different contents, portals with different destinations, ladders and locked doors with different settings); give the placed piece its contents, destination or key in the tile panel. "Show every version" still lists them all.
- **Scatter brush card**: a wider scroll bar, and **Add item** next to Save brush: while it is on, a click on any piece on the left adds it to the brush (or takes it out); "Done adding" ends it.

## Scatter brushes in the editor (Nov 15)
- **Scatter brushes** (Objects tab, at the top): paint trees, plants, flowers, rocks or items at random. The editor's own: Mixed trees, Autumn trees, Pines, Birches & blossom, Wildflowers, Undergrowth, Rocks.
- **Make your own**: Ctrl+click (or Shift+click) any pieces in the Objects, Walls or Items tabs - the game's trees, the new trees (each paints its 4 variants), flowers, plants, rocks, fences, items - and they become one brush. The card shows each piece with a slider for how often it is picked, **How full** (pieces per 100 free tiles) and **Keep apart** (pieces that block walking never stand next to each other, so there is always a way through). **Save brush** keeps it, by name, in the list (in this browser); right-click a saved one to delete it.
- Paints only on free ground and keeps the floor (the area brushes' own placing); Alt+paint removes pieces; works with the brush sizes, rectangle and fill.

## Old Quarry (Nov 15)
The second area of the quest plan: Master Sergeant to First Sergeant, south of the east road.
- **The trail**: from the east road at 533,652 south across the field to the quarry's mouth. **Brann**, the foreman, waits there by his shed (no monsters around it).
- **The pit** (zone "Old Quarry", 576,640 - 642,712): an oval quarry floor of dusty stone inside a rim of rock walls, with rock outcrops, stacks of cut stone and a fire in the middle. 10 **Quarry Golems** (Master Sergeant) and the **Golem Overseer** (First Sergeant; carries the Foreman's Seal).
- **The Deep Grolm Caves** (zone, 616,713 - 644,744): a dark cave at the pit's far end, reached by a passage, lit by four torches. 7 **Deep Grolms** (First Sergeant) and the **Deep Grolm Chieftain** (Sergeant Major; carries his stone axe).
- **New monster looks, recoloured from the game's own animated monsters** (every frame, all directions; `tools/sprites/recolor_creature.py`): the Quarry Golem is the Golem in sandstone (sprites 41000+), the Deep Grolm the Grolm in cave slate (42100+).
- **A chain quest, "The Old Quarry"** (journal quest 4, from Brann, once per character; numbers from the Quest Planner sheet), in two parts:
  - the **Foreman's Seal** from the Golem Overseer -> **Quarryman's Amulet** (+20 endurance, Master Sergeant), 6,000 exp, 300G. Brann turns away players below Master Sergeant.
  - then the **Chieftain's Stone Axe** (only after the seal; from First Sergeant: Brann asks for it once the seal is back, and a lower rank is told to come back; the axe brought before the seal is refused) -> 2 **Stoneskin Potions** (+8 armor for 10 minutes; a timed potion like the Agility Potion, no new code), 10,000 exp, 500G.
- Journal: 1 bring the seal, 2 bring the axe, 3 done.
- Built with `tools/world/old_quarry/build_quarry.py` and `talk.py` (items 2012-2015, NPCs 2037-2056 in `made.json`); since Nov 15 Brann's lines come from `tools/world/quest_fix/to_item_quests.py`.

## Bandit Hollow (Nov 14)
The first area of the quest plan (the "Quest Map and Plan" doc and "Quest Planner" sheet): ranks Sergeant to Master Sergeant.
- **The east road**: a dirt trail from Aston's east gate (533,601) across the field and on to **Bandit Hollow** (x 498-572, y 662-748), a clearing in a thick forest. Zones "Bandit Hollow" and "Wynn's Hut".
- **The bandit camp**: a red picket palisade (514,692 - 556,740, gate in its west side with two torches), three campfires with logs to sit on, barrels, the Quartermaster's storehouse, the Poisoner's hut, two sleeping shacks and **Red Harlan's lodge** (fieldstone, door on the west, four fire bowls).
- **Monsters** (Outlaw look, group 30): 17 Bandits (Sergeant and Staff Sergeant), the **Bandit Quartermaster** (carries the Stolen Ledger), the **Bandit Poisoner** (carries the Bundle of Moonwort), two **Harlan's Guards** and **Red Harlan** (Master Sergeant; carries his head).
- **Three item quests**, the town quests' kind (the Quests page's Item quests, `#quest` 21-23; each once per character; exp and gold as in the Quest Planner sheet: Hollis 1,600 exp and 80G, Tobias and Wynn 1,900 exp and 95G each). Each giver says what it wants in its greeting; handing over the item gives the reward:
  - **Sergeant Hollis** (Cityguard, just outside the east gate): Red Harlan's head -> **Harlan's Studded Belt** (+2 Strength, Sergeant).
  - **Tobias** (a robbed merchant by the gate): the Stolen Ledger -> **Merchant's Signet** (ring, +3 Bartering, Staff Sergeant).
  - **Wynn** (herbalist, her hut on the road, with a garden of flowers to pick; no monsters there): the Bundle of Moonwort -> 3 **Potions of Second Wind** (endurance back to full).
  - Ranks: Hollis from Sergeant, Tobias and Wynn from Staff Sergeant (a lower rank is told to come back later and gets the item back).
- **Barrel** (item template 2007): a plain wooden barrel to decorate with (blocks walking, can be looked at); the game's only other barrel, "barrel (portal)" (1100), is the Thieves House's secret way down. The editor's builder shows it as its own piece. The 7 barrels in the bandit camp are this item.
- **Wagons** (sprites 40000-40007, `tools/sprites/world_wagons.py`; item templates 2008-2011, `tools/world/wagons.py`): a farm wagon with sacks and a crate and a broken one (a wheel off, split side, planks in the grass), each east-west or north-south, drawn in the game's own wood palette and grain. A wagon is an item on its front tile; its second tile needs "blocks walking" (east-west: the tile at y+1; north-south: the tile at x-1). Tobias's broken wagon stands by the east road at 542,610, in a small clearing (8 field trees removed).
- **Hidden forms** (client sprites 16883, 38168, 39305, 39422): with "hide walls" on, the client draws objects as sprite+1; the barrel, the last stump and the web with a spider had no such sprite ("Sprite 16883 is missing"). Copies added and published; `tools/world/check_hide_sprites.py` lists any others.
- Built with `tools/world/bandit_hollow/build_hollow.py` (uses the MyV2 Editor's own World class on the .dat; `made.json` lists the template numbers: items 2001-2006, NPCs 2008-2036) and `talk.py` (the first npctalk.dat lines; since Nov 15 the quests are item quests: `tools/world/quest_fix/to_item_quests.py`). Tested on a copy with the real server (`talknear`, `talktest`, `questgive`, `zone`).

## #rank and #ranks (Nov 14)

**#rank**: your rank and experience, the next rank, the experience it starts at, how much more you need and how far
along you are. **#ranks**: all 24 ranks and the experience each starts at (yours highlighted). Both in `#help`
(`svr_do.c` do_rank / do_ranks; the thresholds are those of `helper.c` points2rank).

## Discord (Nov 14)

The game and Discord are linked through the editor (setup: `docs/HOSTING.md` "Discord links"): in-game shouts go to
**#game-chat** under the player's name, and what people write in #game-chat shows in game as **"[Discord] Name: text"**
(a bot; bad words refused); announcements, players entering / leaving and the guard's "Hear ye, hear ye!" (a new rank; since Nov 14 also arching: Arch-Templar, Arch-Harakim, Warrior, Sorcerer, Seyan'Du) go to **#system**;
**#status** has two messages kept up to date: who is online, and the **rankings** (top 10 by experience + the best 3 of
each class), then who is online with the game time and the moon (as `#time` in game, which now also shows the moon; when a Good Moon starts, everyone in game and #system gets "A Good Moon rises!"): a game day is 80 real minutes and a
28-day month has a **Bad Moon** (new moon) on day 1 (spells 15% weaker, regeneration halved) and a **Good Moon** (full moon) on day 15 (spells
15% stronger, regeneration doubled); the board says which is on, or how long (real time) until the next one. [Server] messages (restart warnings) go to **#server-status** with the up / down posts. GitHub pushes can go to **#github** (a GitHub webhook, no code). Server console: `feed`, `dshout`, `rankings`.

## Cobwebs (Nov 14)

Cobwebbed, lightly dusty copies of the game's things (the originals unchanged), sprites 39000+
(`tools/sprites/cobwebs.py`; copies in `tools/sprites/art/cobwebs_v1`):
- **Walls** 39000-39050: 17 walls (the game's common ones and the 8 new walls), 3 web placements each. The webs hang
  from the middle of a face's top edge or sit at its foot, never at the block's sides, so webbed walls join their
  neighbours cleanly. Editor, Walls tab: **Cobwebbed walls** (each paints one of its 3 at random).
- **Furniture** 39200-39224: chests, bookshelves, tables, candles (candles webbed at the foot). Editor, Objects tab:
  **Cobwebbed furniture**, decoration drawn into the tile (a chest there can't be opened).
- **Trees, stumps, fences, pillars** 39400-39421: the game's bare tree and the 4 dead trees (webs between the branches;
  the small ones three small webs spread out), stumps and the log, the 6 wooden fence pieces, marble / Greek / black
  pillars and the sandstone column (webbed like a wall), the pedestal, two small tables. Objects tab: **Cobwebbed
  trees, stumps, fences & pillars** (they block like the originals). Published Nov 14.
- **Loose cobwebs** 39300-39304: hanging webs (↘ and ↗), a web on the floor, torn scraps, a big web with a spider.
  Objects tab: **Cobwebs** (nothing blocks).
- **Doors** 39100-39149 (closed / open), templates 1460-1484 ("Cobwebbed Door I" ..., each a copy of its own door;
  `tools/world/cobweb_doors.txt`, live since Nov 14): in the builder's Objects list like any door, placed unlocked.

Published Nov 14.

## Snow ground (Nov 14)

Three snow grounds like the sands (the game's grass grain recoloured, 4 variants each, soft auto edges against grass):
**soft snow** 35400-35449, **bluish snow** 35450-35499, **bright snow** 35600-35649 (`tools/sprites/world_ground.py`).
In the editor's Floors tab under New ground. Published Nov 14.

## New trees (Nov 14)

40 trees in the game's style, 4 of each kind in mixed sizes (32x64, 32x96, 64x96), sprites 38100-38167
(`tools/sprites/world_trees.py`; copies in `tools/sprites/art/trees_v1`):
- **Autumn** orange 38100-38103, red 38104-38107, yellow 38108-38111; **Blossom** 38120-38123; **Birch** 38130-38133
  (white bark): the game's own four tree shapes (round, cone, tall, big) with the leaves recoloured.
- **Willow** 38140-38143 (the crown thins into hanging curtains), **Pine** 38150-38153, **Snowy pine** 38154-38157
  (top layer white all over, each layer below whitening from the bottom up, ragged lower edges; its layers stack bottom
  first), **Dead tree** 38160-38163, **Stumps and a log** 38164-38167.

Editor, Objects tab: **New trees**, one cell a kind that paints one of its 4 at random (they block like the game's
trees; dead trees and stumps block walking only). New area brushes: **Autumn Forest**, **Pine Forest**, **Snowy Forest**
(on the new soft snow). Sprites in `Client\GFX`, published Nov 14.

## Wider arches (Nov 14)

Stone arches as wide as you like. An arch is two halves, the second **4 tiles** from the first:
- **↘** (down-right): the game's 942 + 934, bridge 36401.
- **↗** (up-right): 36402 + 36403 (the same arch mirrored; the game's own ↗ arch 937 + 944 can't be widened cleanly,
  its end isn't level), bridge 36400.

Two looks, the same pieces and rule: the game's stone as it is (above), and **smooth** (specks out, grain a bit softer):
↘ 36404 + 36405, bridge 36406; ↗ 36407 + 36409, bridge 36408. Don't mix the looks in one arch. Published to players Nov 14.

To widen by N tiles: put N bridges on the tiles right after the first half and the second half N tiles further (4 + N).
The bridges are cut from the arch's own stone (`tools/sprites/arch_bridge.py`). The editor's Objects tab has an
**Arches** section with all six pieces (halves block walking, bridges don't). Sprites in `Client\GFX`.

## One of each look in the builder (Nov 13)

Many item templates look the same and differ only in their settings (each locked door its own key, each portal its own
destination, each exploration point its own number): the Walls and Objects tabs now show **one of each look** (same
pictures, driver, blocking and kind), named without "Locked" / "Unlocked" and trailing numbers (831 object templates show as 383).

Placing one has nothing to do with any copy placed before: it starts **fresh**, a new instance with its own settings in
the tile panel (only the Copy tool copies a placed piece with its settings):
- a door (driver 2 or 20) with no lock;
- a portal or ladder / hole with no destination (the editor asks right away: click the spot it should lead to);
- a **lever** (driver 19) that works nothing yet (the editor asks right away: click the door / gate it works; the tile
  panel shows "Lever · what it works" with Pick on map / Go there);
- an **item chest** (driver 42) that is empty (the tile panel lists what it gives, one at random each time: pick,
  add, remove items); editor chests (driver 75) open their chest editor as before;
- a **sign** named "Sign" with no text (the tile panel opens with its description ready to type);
- an exploration point with a new number of its own.
Esc leaves a pick for later. Pasting a lever together with what it works makes the copy work the pasted one.
**Exploration points: up to 1024** (was 128). Points 0-127 work as in the original (a bit in data 0-3, players
remember them in character data 46-49); points 128-1023 have data 0-3 = 0 and their number in data 5, and players
remember those in `.dat/explore.dat` (a row per character: its creation date, then 1024 bits; `use_driver.c`
`explorer_point`). The editor hands out numbers past 127 once the first 128 are used, and shows "Point number N of 1024".
Console test: `usexy <player> <x> <y>` (the player uses the item on that spot).

Pasting with the Copy tool makes new copies too (editing one changes only it). A paste with exploration points asks:
**a new point** (its own number: players get experience for it as well as for the original; the usual) or **the same
point** (one point in two places, e.g. behind two different choices: whoever found one gets nothing from the other). **Show every version** (a tick box above the list, remembered)
or searching a template number lists them all again. The Items tab is never grouped (keys open doors by their own template).

The placed piece gets its own settings in the tile panel (they are the item's own data, not the template's):
- **Doors** (driver 2): "Door · lock": no lock / locked with a key (pick the key item), locked when the game starts,
  lock-picking difficulty (0 = can't be picked), the key vanishes when used; a special game-code lock (data 0 ≥ 65500,
  e.g. the Black Stronghold coins) is shown and left alone.
- **Exploration points** (driver 57): placing one gives it a free point number of its own (a bit in data 0-3, 128 in
  all; players remember found points by it), so it counts as a new point; the panel shows the number.
- **Ladders and holes** (driver 16: they move the player by an offset from their own spot): the same "Leads to" /
  "Pick on map" / "Go there" as portals, for this one ladder only (the panel shows the spot it leads to and stores the
  offset). Before, the only way was its template, and saving a template changes every placed copy that still had the
  old value. Portals (driver 6) already had it.

## Server manager

The **Server** page (rail: Server):
- Running/stopped, players online, uptime.
- **Start** (keeps running when the editor is closed; output to `server.log`), **Restart**, **Stop** (players online are warned first: no wait / 30 s / 1-5 min, with reminders).
- **Update code & restart** (stop, `claude-sync.sh get` = take the changed source and rebuild, start) and **Update world & restart** (stop, `claude-sync.sh get-world`, start), with the steps shown as they run.
- **Sync-only buttons**: "Send to Windows" (`claude-sync.sh send`), "Get code" (`get`: take the changed source and rebuild, no restart; the new build is used at the next restart), "Get world" (`get-world`, only while stopped, with a backup).
- **Announce**; a **console** (any console command); the **players online** with Map / Tell / Gold / Exp / Kick; the **server log** (follow, filter).
- **Requests from Claude**: while the editor runs, JSON files dropped into the Windows `Server/control/requests/` are carried out (status, console, log, start, stop, restart, update-code, update-world, send, stop-send, get, get-world, reload-editor) and answered in `control/responses/`; `control/status.json` is kept up to date. They are listed on the Server page. `stop-send` warns, stops and sends (for world edits); `reload-editor` restarts the editor itself after an update (not while there are unsaved map changes). Claude asks in chat before anything that stops or restarts the game.
- When the server stops, the editor reloads the world it saved.
- Fixes: the map could stay black (if the map area had no size yet on the first frame, drawing threw an error that stopped the drawing loop for good; the loop now waits until the map has a size, and an error in one frame no longer stops it). After the editor restarted itself, a server it had started stayed listed as a finished ("zombie") process once it shut down, so the editor still thought it was running and "Update code & restart" gave up after 90 seconds; the editor now collects finished processes and ignores ones that have ended.

## Builder

The map page (rail: Map).

**Tabs of the piece library**
- **Builder**: recently used pieces, chests, floor mixes, floors and flags, walls and objects.
- **Areas**: area brushes (see below).
- **Floors** (by how often they are used), **Walls** (drawn into the tile, they block), **Objects** (furniture, decoration, doors, chests…), **Items** (things players can pick up), **NPCs** (see [NPC editor](#npc-editor)), **Merchants** (see [Merchants tab](#merchants-tab)), **Flags** (paint a flag on tiles: **Add / Remove** mode, **Brush / Rectangle** (drag a rectangle to set or clear a flag on all of it), and **Clear a flag** in the view or in a whole zone in one go, with a count of the tiles that have it in the view; undo works), **Zones** (see below).
- Right-click an item, object or wall in the library to edit its template.

**Rugs** (Floors tab, at the top)
- A rug brush: pick one and drag a rectangle (at least 2 × 2): the corners and sides go where they belong, the middle is filled at random from its middle pieces (weighted by how often they appear). Brush, rectangle and the other drawing tools all lay it as a rectangle; Alt or the eraser work as usual.
- Two come from the game's own map: the **Red rug** (border 523-530, middle 520/521/522) and the **Blue rug** (border 534-541, middle 531/532/533).
- **+ Learn a rug from the map**: drag over a whole rug, its border included (at least 3 × 3); its corners, its sides (the most common piece on each) and its middle become a new rug, named by you. Right-click your own rug to rename or delete it. Kept in `.dat/mapedit-rugs.json`.

**Discord posts** (the editor): when the game goes down (with the reason, e.g. "an update"), is offline, comes online again, or restarted by itself after a crash, a message goes to the Discord channel whose webhook address is in `Server\discord-webhook.txt` (kept out of the project). Control action `discord` posts any message.

**Automatic backups** (the editor, while it runs): every 6 hours (0, 6, 12, 18 o'clock) the game data (`.dat/*.dat`, about 7 MB zipped) goes to `~/myv2-backups` and the off-PC folder `D:\MyV2 Backups` (`--backup-dir`), kept as the last 8, 14 daily and 8 weekly; see docs/HOSTING.md for restoring.

**Copy tool** (C, in the toolbar): drag over an area to copy it, then click to paste it with its top corner on the clicked tile, as many times as you like (a dashed blue outline shows where it goes; Shift+drag copies another area, Esc forgets the copy). It copies the floors, walls / objects, the tile flags and the items (each paste makes new items; editor chests keep their rewards and each gets its own timer). NPCs are not copied. One paste is one undo step; works while the game runs.

**Zones tab** (draws the game's zones; see [Zone names](#new-zones-and-areas))
- Lists every zone in the order the game names them (search filters); click one to pick it and go there, or click the map to pick the smallest zone at that spot. The picked zone's boxes are shaded blue on the map, the others outlined in gold.
- The picked zone: its name (renaming it to another zone's name offers to join the two), what the game says ("in", "in the", "on" for streets, "at"), its boxes (go to, remove) and **Delete zone**. **+ Add box** and drag on the map (a click adds a single tile) adds boxes until "Done" or Esc; Alt+click removes the picked zone's box under the mouse. **+ New zone** starts one and goes straight to adding boxes.
- **Save zones** writes `.dat/zones.dat` (the old one goes to `mapedit-backups/`) and the running game reloads it; **Undo changes** forgets what wasn't saved. Works while the game runs.
- Unsaved zone changes are kept in the browser as you make them: if the page is refreshed or the editor restarts before **Save zones**, the Zones tab offers **Restore them** (or **Throw away**). Leaving or refreshing the page with unsaved zone or editor-panel changes asks first. Console `zonefiles` lists `.dat/zones.dat` and its backups; `zonerestore <file>` puts a backup back.
- Boxes of one name that said different things ("in" / "in the") take the word most of them use.

**No black flash while the game runs**: the editor re-reads the running game every few seconds (NPCs moving, live edits). It used to throw the whole map picture away and redraw it from nothing, so the map blinked black. Now it fetches what is on screen again and keeps showing the old picture until the new one is there; parts off screen are just dropped and fetched when you go there.

**Tools** (the hotbar across the top of the map, with the key letter on each slot)
- **Select** (V): click a tile to see and change it in the right panel.
- **Brush** (B, drag), **Rectangle** (U, or Shift+drag), **Fill** (F: a room up to its walls and the void, indoors or outdoors like the clicked tile, not past doors; with a floor: the patch of the same floor).
- **Erase** (E), **Pick** (I, eye dropper: takes the piece under the mouse as the brush), **Move** (H; right-drag, middle-drag or Space+drag also move the view).
- Alt paints the opposite (clears a flag; with a wall/object/item, erases). Brush size 1-9 (click for bigger, right-click for smaller); undo/redo; zoom slider at the bottom.
- Floors from build mode's random sets paint random variants.
- **Floor mixes** (so a big area of one floor doesn't look like a flat or tiled pattern): Ctrl+click (or Shift+click) floors to put several in one brush; each has a weight slider (how often it's painted, shown in %), and "+ look-alikes" adds floors whose colour is close. Brush, rectangle and fill paint a random pick per tile. "Save mix" keeps it under a name in the Floors and Builder tabs (stored in the browser; right-click a saved mix to delete it); the game's own random sets (e.g. 551 = the four Aston grasses) are listed there too.

**View switches** (round buttons top right) and layers
- Grid (G), see through walls (W), light from lamps (L), reload the world; hide/show the right panel with the tab on its edge (› hides it, ‹ brings it back).
- Layers to show: floors, walls/objects, items, characters, see-through walls, lamp light, grid, area names; any number of flag overlays in their own colours.
- **NPC and player names** on the map: Show → "NPC and player names" (or the N key; remembered in this browser). NPCs in cream, players in blue, NPCs waiting to spawn faded.

**The selected tile** (right panel)
- Change its floor, remove its object/item, tick its flags.
- **Items and portals**: name, description (what players read when they look), its data values, and for portals (driver 6) "Leads to x, y" with **Pick on map** (click the destination on the map or on the world map with M) and **Go there**. Placing a portal asks right away where it should lead. Lab portals (data 2 set) are flagged, with a button to make them normal portals.
- **Exploration points** ("poles", driver 57): their experience as a field you can change (then Save item), and what a player really gets: half to 1.5 times it, once per character, +10 luck, never more than 10% of the player's total experience (+ up to 10%), and from what total experience looking at it says "too early".
- **Edit its template…** and **Quest rules…** (what happens when a player uses it, see [Conversation editor](#conversation-editor)).
- **Chests**: a summary and **Edit chest…** (see [Chest editor](#chest-editor)).
- **NPCs**: turn, move or remove, **Edit NPC…** (see [NPC editor](#npc-editor)).

**Area brushes** (the **Areas** tab, next to Floors)
- Paint a whole landscape at once with brush, rectangle or fill: each tile gets the area's floor mix (tick **Also lay the floor**, or untick it to keep the floor), and free tiles now and then get one of its trees, plants, rocks or decorations, at the same density as the real area. Walls, items, NPCs and blocked tiles are left alone; with **keep pieces apart**, two pieces that block walking never stand side by side. Alt+paint removes pieces (the floor stays). Undo, saving and live editing work as for any edit. On the black void (new ground) it lays the floor too when "Also lay the floor" is ticked (fix: at first it skipped void tiles, so painting new ground did nothing); with it unticked, pieces only go on existing ground, and a stroke that changes nothing says so.
- Seven ready-made brushes, learned from the game's own areas: **City Park** (Memorial Park), **Forest** (Strange Forest), **Dense Forest** (the labyrinth's Forest Gorge), **Jungle** (north of Strange Forest), **Cave**, **Fire Cave** and **Ice Cave** (the pentagram caves; no pentagrams, enemies or walls).
- **+ Learn from the map**: drag over any part of the map and its floors and loose pieces become a new brush. Walls are recognised by shape (blocking pieces in lines, with blocking neighbours on two sides) and left out, as are things that belong to buildings (doors, chests, signs, lights, candles, shrines…) and anything players can pick up.
- **Edit…** (or right-click a brush): its name; an **overall amount** slider (0-300%, 100% = as in the real area); each floor with an on/off tick and a weight slider; each piece with an on/off tick and a slider for how many per 100 free tiles (off: never painted, kept in the list); **+ Add the floor brush** / **+ Add the current brush** (a tree, plant, rock or item you picked); the spacing rule. Your brushes are kept in `.dat/mapedit-areas.json`; saving one of the editor's own keeps your version under its name, and deleting your version brings the editor's own back.
- **Save as new area type…**: keeps the current settings under a new name as another area type; the one you started from stays as it was saved.
- **Reset to defaults**: for the editor's own area types, back to the editor's settings (your saved version is removed); for one you learned, learns it again from the part of the map it came from (click Save to keep it).
- The ready-made **City Park** no longer lays the cobblestone path floors (544-550) and **Dense Forest** no longer the white tile 1158: they were in the learned areas but are paths, not ground.
- Server side: a new edit op `area` (`area_learn`, `area_pick` in `mapedit.py`), built on the existing floor, object and place ops.

**Item templates** (right-click a piece in the library, "Edit template…" on the brush card, or "Edit its template…" on an item on a tile): name, reference, description, both looks, value, minimum rank, driver, flags in groups, where it is worn, all modifiers (when worn / when active / needed), armor, weapon, light, damage to attackers, ages, damage, duration, and the driver values. By default the copies lying on the map get the change, but only where they still had the template's old value, so a portal's destination or a sign's own text stays. "Save as a new item…" makes a copy.

**Look of the editor**
- Its own toolbar design (it followed the inspiration mock-up too closely at first): a hotbar of square wood-and-gold slots across the top of the map (Cody preferred it to a column down the side), the key letter in the corner and a gold mark under the active tool; the brush size and undo/redo on the same bar.
- **Icons** chosen by Cody: select (an arrow over a tile), a paint brush, a dashed rectangle with corner handles, fill (four squares with arrows going out), an eraser, an eye dropper with a drop, and move (a hand with four arrows). View switches (larger round 42 px buttons): grid (a 3×3 grid), see through walls (a brick wall, solid at the bottom left and see-through at the top right), light from lamps (a candle in refresh arrows), reload the world (a globe in refresh arrows).
- The live/view-only banner is a strip along the top of the map.
- **Left rail**: the sections are slots with icons (Map: a parchment map; Players: a knight's helmet; NPCs: a hooded figure; History: an hourglass; Server: a castle tower; Help: a book), and a gold mark beside the open one.
- **Category tabs**: a grid of plaques with icons (Builder: a hammer; Floors: a tile; Walls: bricks; Objects: a chest; Items: a sword; NPCs: a hooded figure; Merchants: a shopping bag; Flags: a pennant). The other pages show a single title plaque.

## Player editor

The **Players** page (rail) lists every player character, online ones first, with rank, class and last seen. Clicking one opens it in tabs:
- **Overview:** description; total experience (sets the rank, and changes the unspent experience by the same amount) and unspent experience; money carried; bank (pays the depot rent); luck; the recall point (pick on map); where they stand, or where they come back at the next login; their quest steps.
- **Stats & skills:** attributes, hit points, endurance, mana and the skills their class can learn, each with value and maximum.
- **Worn & backpack:** the 12 worn slots, the item on the mouse and the 40 backpack slots. Each item can be removed (Ctrl+Z undoes it) or its template opened; an empty slot gets **+ Give an item…** (worn slots only offer items that fit there).
- **Depot:** the 62 depot slots, the same way, and the rent paid so far.
- **History:** created, last login, last logout, time played, last address, and the lines about the character in `server.log` (logins, logouts, kills, deaths, other), which can be filtered and clicked to show the place on the map.
- **Account:** download the character's **.moa** file (the client's key file: number, both keys, name, starting race, default display options) for a player who lost theirs; remove a forgotten password; rights and flags (staff, imp, god, creator, no shout, no tell, muted, golden/black list, hidden in #who).
- **Start over or delete** (Account tab; the character must be offline, the game running; you type the name to confirm):
  - **Reset to a brand new character**: a new character of its class at the start with the start gear (an arch class goes back to its base class: Arch-Templar to Templar). Kept: name, password and .moa key, staff / imp / god rights. Gone: experience, stats, skills, everything carried, worn and in the depot, bank, gold, prestige; it gets a new creation date, so its quest steps, quest counts and area clears start over.
  - **Delete this character**: it and all its items are removed and the name is free again; a backup of the character with everything it had goes to `.dat/mapedit-backups/deleted/<name>-<date>.chr`.
  - **Deleted characters** (under the Players list): the backups, each with **Restore**. If its name was taken in the meantime, it comes back under a new random name (like a new character's), so you can download its .moa and send it to the player.
  - Done by the game (`god_reset_player`, `god_delete_player`, `god_restore_player` in `svr_god.c`; console `charreset <nr> <name>`, `chardelete <nr> <name>`, `chardeleted`, `charrestore <file>`).
- Changes go through the normal edit path: undo, history, saving when the server is stopped, and live into the running game when it runs (an online player's client is refreshed).

## NPC editor

**How the game keeps NPCs**: a template is the recipe (name, look, stats, gear, lines, behaviour) and also holds one spawn spot. The NPCs in the world are living copies, made from their template whenever they (re)spawn. So every placed NPC has a template of its own, and templates without a spot are recipes the game's code spawns from (pentagram and labyrinth monsters, summons) or ones not placed yet.

**The NPCs tab** (Map → NPCs)
- **In the world:** every NPC that is in the game, alive or respawning (faded), with its area, position and template. Click goes there and selects it; right-click edits it; **Copy** picks it as the NPC brush to place copies.
- **Blueprints:** templates without a spawn spot. First "Your new NPCs · not placed yet", then the game's own (spawned by its code).
- **Placing**: pick one, choose where it faces (N/E/S/W, the minimap's directions), click a free tile. The editor makes a copy of its template (new numbers from 2000 up), with that tile as its spawn and resting spot and respawning on, and adds a respawn timer. The server then creates it the normal way, with its items, about a second after. Until then it shows faded on a dashed ring.
- **+ New NPC…** (in Blueprints): a name, a kind (friendly, merchant or enemy) and a look picked from every NPC look in the game. It starts as a plain NPC of that kind, copied from the weakest ordinary one placed in the world (a townsperson / Ruth / a Thief), without that NPC's lines, patrol, doors, lights, quest or attack zone; friendly and enemy start with an empty backpack, a merchant keeps its stock to start from. It greets players (with an empty greeting until you write one) and doesn't respawn until placed. Its editor opens and the NPC brush is ready to place it.
- The player start templates (what new characters are made from) and the Blank Template are not listed as NPCs.

**On the map**
- Select an NPC (or a faded one waiting to spawn) to **turn** it, **move** it (pick the tile on the map) or **remove** it. Moving or turning one that its template spawns also moves or turns its spawn. Removing it stops its template from respawning (a copy the editor made is freed). NPCs made by spawners or quests are only moved or removed themselves. Alt+click with an NPC picked removes the NPC on that tile.
- The patrol route of a selected NPC is drawn on the map.

**Edit NPC…** (on a selected NPC, the NPC brush card "Edit template…", or right-click in the NPCs tab) opens every part of an NPC template, in tabs:
- **General:** name, reference, description, look (sprite base, with a preview), facing, alignment (below 0 = enemy), money, class, flags (respawns, merchant, immortal, sees in the dark, undead, never sleeps, invisible, simple animation, ignores spells, no HP regeneration).
- **Stats & skills:** the five attributes, HP, endurance, mana, all skills, the bonuses, and "Scale everything" by a percentage.
- **Rank:** an NPC's rank comes from its experience value, which the server works out from its stats at every respawn, so it can't be set directly. The Stats tab shows the rank and has "Scale to this rank": it finds the smallest scale of all stats that makes the NPC exactly the chosen rank (using the server's own cost formulas), or says so if the stats max out first. The rank also shows in the editor's header line.
  - **Limits**: next to the rank, "limits like Mercenary / Templar / Harakim / Seyan'Du / Warrior-Mercenary / Sorcerer-Mercenary / Arch-Templar / Arch-Harakim" (no value goes past that player class's maximum, the rest goes into the other stats; the maximums come from the classes' player templates) or "no limits (monsters)". Enemies start on no limits, other NPCs on Seyan'Du.
  - **The right weapon skill**: an NPC fights with the skill of the weapon in its right hand (Hand to Hand without one), so its best fighting skill is moved there first (e.g. Sword 40 -> Dagger when it wields a dagger) and scaling raises that one.
- **Equipment & stock:** the 12 worn slots, and the 40 backpack slots, which are a merchant's stock. Each slot has an item picker with search and a link to edit that item; Pick… on a worn slot lists only items that fit it (helmets for Head, weapons for the right hand, rings for the rings...), the backpack only things that can be picked up.
- **Behaviour:** taking part in fights, attack distance, keyword action, groups (attack all but / help / shout for help / come to help codes), random walk, greeting players, light, picking up trash, self-destruct.
- **Patrol & chores:** up to 9 patrol stops picked on the map and the wait at each stop; the **doors it closes** (up to 4, data 20-23), the **lights it keeps burning** (up to 4 torches / candles / fire bowls it walks to and relights when they go out, data 32-35) and the **street lights it switches** on at night and off by day (an item kind, within 8 tiles; data 41), each picked on the map with Go there / Remove.
- **Talk & quest:** its fixed lines (greeting, keyword and reply, warning, attacking, killed an enemy, dying words, shouting for help, coming to help; %s = the player's name), the dying-words chance, knowledge area and level (the game's built-in answers), and the "bring me an item" quest (wanted item -> teaches a skill + experience, and/or gives an item back).
- **Conversations:** its own lines and quests, see [Conversation editor](#conversation-editor).
- **Advanced:** all 100 driver values, labelled after the original admin interface (`acct.c`).
- **Apply** writes the template, and by default respawns the NPCs of that template with the changes (as the game's own reset does). **Save as a new NPC…** makes a copy with a new name (numbers from 2000 up); it is not placed until you click a tile with the NPC brush, and that first placement uses it directly. Copying an NPC template copies its conversations; a removed editor-made NPC loses them.
- Fix: "Save as a new NPC" kept the original's respawning, though the copy has no spawn spot until it is placed. The game then kept trying to spawn it at 0,0 ("Could not drop char 2000" every 5 minutes in the log), and because of that spawn timer, the first placement made yet another copy instead of using it. A new NPC now respawns only once it is placed, and the first placement uses it (a stale spawn timer of it is removed).
- Fix: changing an NPC's worn gear, backpack (merchant stock) or carried item and pressing Apply did nothing (the editor left those fields out, as it must for players); now they are saved and the NPC respawns with them.

**Go to** (top right of the NPC, player and quest-rules windows): closes the window and shows that NPC, player or tile on the map, selected. An NPC: where it is now (with several of that template, each Go to on it shows the next one); not in the world: its spawn spot.

## Quest editor

Under the NPC editor's **Conversations** tab.
- **Quest steps:** 255 numbered quests per character (was 31 at first), all starting at 0. Each quest has a name and **journal texts per step**, edited under the quest; players read them with `#journal` (the highest step text at or below where they are).
- **Kill counter** button: "kill N of X (in area A) while quest Q is at step S" makes the two lines that count the kills in a quest of their own ("Spider: 3/5") and moves quest Q on at the last one.
- Quest names and step texts are kept in `npctalk.dat`.

## Conversation editor

An NPC's own conversation lines (the NPC editor's **Conversations** tab), and **Quest rules…** for an item on a tile. For a player, the first line whose trigger and conditions fit is used, before the game's built-in answers and before its "wants item" quest.

**Triggers**
- **When the player says**: every word must be in it; `a|b` = either, `ring*` = ring, rings, ….
- **When the player gives** an item.
- **When the player gives money** (at least an amount). With a matching line the NPC keeps it; otherwise it gives it back as before ("I don't take money from you!").
- **When a player comes close** (greeting): replaces the NPC's fixed greeting when its conditions fit; otherwise the normal greeting. Applying such a line turns on "Greets players" for the NPC. Such NPCs greet each player at most once a minute, and the NPC at most every 2 seconds (fix: the game remembers just the last four players greeted, so a changed situation, e.g. having finished Jamil's quest, got no new greeting for a long time).
- **When the player kills**: the killed NPC by name (`Spider*`, `Ghost|Skeleton`; every Spider counts, whatever its template) or by template numbers (`#35,36`). Credit goes to the player who killed it, or whose companion did, and to the members of their group who can see them. Each one only gets it if the line's conditions fit them, so with a quest-step condition a kill only counts while that quest is active.
- **When a player uses** (quest rules on an item: a portal, door, lever, chest…): the first rule whose conditions fit replaces what the item normally does; with **then the item works as usual** its normal use still happens afterwards; if no rule fits, the item works as usual. The rules belong to the tile, so they stay when the item there is replaced.

**Conditions (optional)**
- A quest step (=, is not, below, above, at most, at least).
- The player carries or doesn't carry an item.
- Their rank (picked from the rank names).
- **Area**: part of an area name; for kills the victim's position, otherwise the player's.
- **A skill** (0 = doesn't know it; e.g. Bartering 12 shows who finished Jamil's quest).
- **Money** carried.
- **The player's class**: is / is not any mix of the eight classes (click them, picked ones are gold). **By class** (on a line) splits it into three lines (Templars, Mercenaries and Seyan'Du, Harakim; change the classes as you like), so each can teach its own skill or give its own item; this is how chain quests give class rewards.

**What happens**
- The NPC **answers** (several lines in turn, `%s` = the player's name, `{q2}` = the player's value of quest 2); **tell** (only the player sees it); **announce** (everyone online). For a kill, the message lines go to the player.
- **Set** or **add to** quest steps.
- **Give** an item, experience, money or luck; **teach** a skill; **teleport** to x y (pick on map).
- **Take** an item or money from the player; for a handed-over item, **keep** it (otherwise it hands it back).
- **Cast a spell** on the player (bless, protect, enhance, magic shield, light, heal, with a power; the game lowers the power to what the player can take). For a kill or an item rule, the player's own magic casts it.
- While the server runs, applying sends the changes to it right away, so new lines work at once.

## Chest editor

For every loot item (chests, flowers, bookshelves…).
- **Tile panel**: a short summary (what it gives, each chance, when it opens again) and a button, **Edit chest…** or **Convert to an editor chest…**.
- **The chest window** opens in the big window like the NPC and player editors. (Fix: it used to be in the side panel, which the editor's refresh every few seconds while the server runs wiped halfway; the tile panel also isn't redrawn now while you are typing in it.)
- **Old-style chests**: shows what they give, then **Convert…** fills in those rewards (the old tier armor numbers become Magic pieces of that metal). Drivers 30, 53 and 54 lose their special part, and it asks first.
- **Editor chests**: facing, the name players see, how long it stays empty, once per player, the **first-time reward** (a checkbox and an item picker), a chance bar, and one card per reward (Item / Gold / Tier armor / Once on the server / Nothing, chosen with buttons) with its weight and %, move up, copy and remove; tier armor has Tier, Level from-to, Metal and Piece as chips. **+ Item / + Gold / + Tier armor / + Once on the server / + Nothing** add one.
- **Facing**: the game's own chest has two looks, lock facing south (220/221) or west (222/223); the tile panel and the chest window show both, marked S and W, and clicking one turns that chest.
- **+ Chest** (top of the Builder and Objects tabs): one plain chest for the whole map. The first click makes an item template **Chest** (a copy of Treasure Chest as an editor chest); after that it is a normal brush. Every chest placed with it is its own chest: the rewards belong to its spot, and the chest window opens as soon as one is placed (a single click).
- **Copy this chest…** (in an editor chest's window): then each free spot you click on the map gets a new chest with the same rewards, first-time item, once-per-player setting, refill time, name and facing. Each copy is its own chest (its own timer and once-per-player list, since those go by the spot). Picking another brush stops copying; unsaved changes must be saved first.

## Merchants tab

Map → **Merchants** (next to NPCs): every merchant (not the gods' shops), searchable by name, place or an item he sells, with how many items he sells and where he stands. Click one to open his shop; right-click opens his NPC.
- **Stock**: the items he always has, in shop order: add by search, move up / down, remove, sort by name (up to 240; more than 40 makes pages in the game).
- **Sells at** and **Pays when buying**: a % of the normal price (normal = up to 4x the value when he sells, a quarter when he buys, both better with Bartering); empty = the normal price.
- **Buys from players**: Armor, Weapons, Magic, Other, in any mix.
- **Gold**: the most he pays for one item (0 = his own gold).
- **Go to**, **Apply** (writes `.dat/merchants.dat`, and the running game reads it at once), **Back to the game's own** (forgets his settings: his stock follows his NPC backpack and sale list again, normal prices). Merchants without own settings work as before.

## Waypoints tab

Map → **Waypoints**: the list of waypoints in the order of the travel window. **+ New waypoint** and a click on the map sets the middle of the circle; then its name ("Town, Place", up to 31 letters), the line under it (up to 34), and the look (**Rune circle**, or the **Pentagram** kept as a second look). **Move**, ▲ / ▼ (the order), **Delete**. **Save waypoints** writes `.dat/waypoints.dat`; a running game lays the circles at once (`wpreload`).
- **Nothing is placed by hand**: the game makes the nine circle pieces itself on whatever floor is there, and removes them when the waypoint is deleted or moved. Build the floor and pillars around it with the other tabs (the short round pillar of Cody's example is the game's sprite 107). The nine tiles must be free of other objects; a tile that holds one gets no piece (logged).
- **The travel window's picture** of a waypoint (64 × 32, `GFX\\184NN.png`, NN = the waypoint's number): **Use my own picture…** takes any image file, or a screenshot pasted with Ctrl+V while the waypoint is picked (cut to twice as wide as high around its middle, then shrunk); **Take it from the editor's map** cuts it from the map as the editor shows it (128 × 64 map pixels around the circle). Players get it with the next client update; until then they see a stock picture.
- A waypoint's number is never used again, so a new waypoint is never "found" by anybody. Deleting one takes it from everyone who found it.

## Quests page

Rail: **Quests**. Every quest on one page.

**Item quests** (the `#quest` list): one row for each NPC that wants an item: the NPC (click to open it in the NPC editor), where it is (click to see it on the map), what it **wants**, the skill it **teaches**, the item it **gives**, the **exp**, what it **says** (the hint `#quest <n>` shows), and **Listed**.
- The rows are in the order players see them in `#quest`: move one with ▲ ▼; untick **Listed** to leave it out of `#quest`. The numbers are what `#quest` shows ("–" for an NPC that teaches no skill and gives no item, like the Cityguard's black candle, which `#quest` leaves out).
- **+ New quest**: pick any NPC; it gets a row at the end to fill in. **Remove** makes an NPC an ordinary one again.
- **Save** writes the changed NPCs like the NPC editor does (live into the running game, the NPCs respawn with their new reward; with the server stopped, into the editor, then **Save to the game**) and the order into `npctalk.dat` (`order <template> <place>`, -1 = not listed; the game reads it at once). Changed rows are highlighted; **Undo changes** forgets them.
- Labyrinth and tower trades are puzzle steps that `#quest` never lists; they are under **Show** at the bottom.
- **Ranks** (under Times · rank, any quest, skill teachers too): the lowest and/or highest rank that may do it. A player of another rank is told "You are not ready for this yet, X. Come back when you are a Corporal." or "This task is not for one of your rank, X." and gets the item back; `#quest` leaves the quest out for them (`#quest all` shows it in blue) and its details show "Rank: Corporal to Captain". Kept in `npctalk.dat` as `qrank <template> <lowest> <highest>` (-1 = none).
- **Gold** as a reward (in G; 1.5 = 1G 50S), for skill teachers (given with the skill) and item trades.
- **Times** (item trades): how often one player can do it, **Once**, **a number of times** or **Forever**, and **rewards that change with each turn-in**: the row's reward for the first N times, then any number of steps (up to 7), each with its own item, exp and gold and how many turn-ins it lasts; the last step is given from then on. E.g. the Ratling Eye Collection: 10,000 exp the 1st time, 7,500 the 2nd, 5,000 the 3rd, then only the potion. After the last allowed time the NPC says it doesn't need any more and hands the item back. Kept in `npctalk.dat` as `qreward <template> <times> <first> <gold>` plus a `qstage <template> <times> <item> <exp> <gold>` line per step (gold in silver; the older one-line form still reads); how often each player did each one in `.dat/questcount.dat` (a row per character, reset when the character slot is reused). `#quest` shows each player the reward they get now, the later ones where they change ("Later: from the 2nd time: …; from the 3rd time: …"), how many times are left, and leaves out the ones they have finished.
- The same fields are still on the NPC editor's Talk & quest tab; both change the same thing.
- **More than one item quest per NPC**: **+ New quest** also offers NPCs that already give one ("· another quest"). The new quest is kept in a hidden, unplaced copy of the NPC (its own row: what it wants, teaches, gives, its hint, times, rewards by class, ranks, order); the NPC itself takes either item. Kept in `npctalk.dat` as `qalias <quest template> <NPC template>`; the copies are left out of the NPC lists. `#quest` shows each quest at its NPC's place.
- **Rewards by class** (under Times · rank, any item quest, skill teachers too): **+ Add a class reward**, then click the classes it is for (any mix of Templar, Arch-Templar, Mercenary, Warrior, Sorcerer, Seyan'Du, Harakim, Arch-Harakim; picked ones are gold), the skill it teaches them (the row's, another one, or none; **+ then…** adds up to three more: each turn-in teaches the first one they don't know yet, and the NPC says "Bring me the item again to learn …") and the item it gives them (the row's, another one, or nothing). Several rules are allowed; the first one with the player's class counts, other classes get the row's reward. The class's item replaces the row's item in the first reward and in later steps that give the row's item; exp, gold, times and ranks are the same for everyone. `#quest` shows each player the next skill and their own item. Kept in `npctalk.dat` as `qclass <template> <classes joined by |> <skills joined by ,> <item>` (-1 = the row's).

**Kill quests** (`#kills`; the Quests page's second box): "kill 5 Spiders" for an NPC, made and changed here instead of in the NPC's own conversation lines. Each quest is a card (**Edit** opens it; ▲ ▼ set the order a giver offers its quests in; **Open NPC**, **Delete**, **Save** into the game at once). Every setting left empty means no limit:
- **What to kill**: how many; **in the zone** (a zone from the Zones tab, optional); **monster rank** from / to (e.g. pentagram monsters of some ranks only); what the counter calls them (empty: the name, with an "s" for more than one); and the **rules**: any number of "name contains" (`spider` also counts Weak Spider and Strong Spider), "name is", "name starts with", template numbers, **Any enemy**, each either counting or **except** (never counts, e.g. except "Spider Queen"). With a zone picked, the NPCs living there are shown: click a name to count it. **As text** shows the rules as the game reads them.
- **Who can take it, and when**: the player's rank from / to (players outside it hear "You should get stronger first" / "You are a bit too strong for this task"), **only some classes**, **requirements** (any number, all must fit: a quest step such as "quest 7 is at least 2", a skill such as "Bartering is above 0", carrying or not carrying an item, money, being in an area; until they fit, the quest is hidden: the giver doesn't offer it and `#kills` doesn't list it, unless a "requirements not met" text is set, which the giver then says), the **time to finish** once taken (minutes, hours or days; when it runs out the task fails: "Your task for Gunther ran out of time.", the giver says so and it can be taken again), and the **wait before doing it again**.
- **Rewards**: how often per player (once, a number of times, forever); exp, gold, an item and a skill it teaches; **rewards change with each turn-in** works like item quests (the first reward for the first n times, then steps for so many times each, the last one every time after); **when it is handed in, also** set or add to up to four quest steps (to go on with a chain quest, or unlock the next kill quest).
- **What the giver says**: offering it, the player saying yes, not done yet, handing it in, rank too low, rank too high, wrong class, done all times, ran out of time, not again yet, backpack full, requirements not met (only the ones the settings can cause are listed; empty = the default shown in grey).
- In the game: a player says **QUEST** (or task, job, work, kill) to the giver, or the giver offers it when it greets them (only givers with "Greets players" on; at most every 10 minutes; the card warns when it's off); **YES** (ok, sure, accept) within 2 minutes takes it. A giver offers one kill quest at a time (the first the player can do now); when none can be taken it gives the reason (not again yet, rank, class, done). Kills count only while it is taken: the killer, a Ghost Companion's master, and group members who can see them, "Spiders: 3/5", at the last one "Done! Return to Gunther." Saying QUEST again or coming close hands it in (an item reward needs room in the backpack). A player can have tasks from several givers at once. `#kills` lists every kill quest with the player's state (say QUEST to …, 3/5 and the time left, done: return to …, out of time, again in 2 hours, from / up to a rank, not for your class, finished), the giver and place, the next reward and the rules (times, time to finish, wait, ranks, classes).
- Changing a quest's giver, what to kill, how many, the zone or the monster ranks starts the players' progress on it again (how often they did it stays).
- Kept in `npctalk.dat`: `kq <id> <giver> <count> <times, 0 = forever> <exp> <gold in silver> <item>`, then `kqkill` (rules joined by |: names with * as a wildcard, `#390,391`, `@enemy`, `!` = except), `kqzone`, `kqvrank`, `kqlabel`, `kqrank`, `kqclass`, `kqtime <minutes to finish> <minutes before again>`, `kqif <condition as an "if" line>`, `kqset <set|add> <quest> <value>`, `kqskill`, `kqfirst`, `kqstage <times> <item> <exp> <gold>`, `kqtext <which> <text>` (the full list is at the top of `npctalk.c`); up to 64. Progress in `.dat/killquests.dat` (a row per character). Console: `kqkill <player> <NPC template>` counts a kill for the player (and shows the victim's place and rank), `kills <player>` shows their `#kills`, `kqtime <player> <minutes>` moves their taken / handed-in times back (to test time limits and waits); `talktest <giver> <player> quest` / `yes` and `talknear` try the giver.
- (The older way still works: an NPC's own conversation lines with the **Kill counter** button and quest steps, for kills that are part of a chain quest.)

**Area clears** (`#areas`; the Quests page's third box): kill every chosen NPC of an area for an experience bonus.
- Search a zone and **+ Add area**: every NPC whose spawn spot is in that zone is listed with a tick box (the enemies ticked); set what the counter calls them ("Skeletons"), the experience, and **again as Seyan'Du**. **All enemies** / **None**, **Delete**, **Save** (into the game at once).
- In the game: each new kill of a ticked NPC tells the player "4 of 12 Skeletons in this area."; the last one "You cleared Skeleton Lord!" and the experience. `#areas` lists every area and how far you are.
- A kill counts for the killer (or a Ghost Companion's master) and the members of their group, each only while standing in that zone, so a player who joins late doesn't get the kills made before. Each NPC counts once (respawned ones don't count again). Once per character; with "again as Seyan'Du" once more after becoming a Seyan'Du. Changing an area's NPC list starts everyone's progress there again.
- Kept in `npctalk.dat` (`clear <id> <exp> <again as Seyan'Du> <zone>`, `clearlabel`, `clearnpc <id> <templates>`, up to 64 areas of up to 64 NPCs); progress in `.dat/clears.dat` (a row per character). Console: `cleartest <player> <NPC template>` counts a kill as that player.
- **Re-check zones** (after redrawing a zone or placing new enemies): each area then shows the enemies now in its zone that aren't ticked (**Tick them**) and ticked NPCs no longer in the zone (**Untick them**); then Save. The list is also read fresh each time the Quests page opens.

**Chain quests** (`#journal`): each quest number with its name and journal texts (from which step on), **+ Step**, **Delete**, **+ New chain quest** (the next free number), and **Used by**: every NPC (or item tile) whose conversation lines check or move the quest on, with a click to open its Conversations. Saving goes into the game at once.

**In the game**: `#quest` follows the order from the Quests page (quests placed there first, the rest after them as before: skill teachers by exp, then item trades). An item trade can now give experience as well (before, only a skill teacher gave the exp).

## History and logs

- **History** (rail): this session's edits (click to go there) and the backups.
- **Undo / redo** (Ctrl+Z / Ctrl+Y) for everything: map, items, NPCs, templates and players.
- **Saving** (server stopped) writes `map.dat` and `item.dat`, and `char.dat`, `tchar.dat`, `effect.dat` and `titem.dat` when they changed, after copying the old ones to `.dat/mapedit-backups/<date-time>/`; it refuses if the files changed on disk since loading. **Undo last save** puts back whichever files that save wrote. **Relight** runs `./server light`.
- The first live edit after the editor starts copies the world files to `.dat/mapedit-backups/<date-time>-live/`.
- While the game server runs without live editing: view only, and it reads the world files again every few seconds, so NPCs and players show where they are.
- The **server log** (Server page, follow and filter) and each player's **History** tab (Player editor).

---

# Server

## Server modernization

The server source assumed a 32-bit Linux, where `long` and `time_t` are 4 bytes. Built as 64-bit (WSL/Ubuntu), they are 8 bytes, which broke the network protocol and the binary `.dat` files.

| File | Problem | Fix |
|---|---|---|
| `svr_tick.c` | `fdiff`/`mcmp`/`mcpy` and the packet readers/writers used `unsigned long` as a 4-byte unit | `unsigned int`. Fixed the "Server data error" (-128 / -90) seen in the client. |
| `data.h` | `time_t` fields in `struct character` grew the record from 3605 to 3617 bytes | `int`. Character records load correctly again. |
| `data.h` | `long load` and natural 64-bit padding changed `struct global` | `int`, plus `#pragma pack(4)`. Fixed the bogus player cap / login queue. |

**WSL / live-server workarounds in `server.c`** (deliberate; the Windows Server folder and the project keep the same file)
- **Fixed CPU speed**: `cycles_per_sek` is set to 3000000000 instead of being measured with `rdtsc` over one second, which gave wrong values under WSL and threw off the game's timing.
- **No stop on an unclean shutdown**: with the "data files were not cleanly unmounted" flag set, the server logs it and starts anyway instead of quitting.
- **`./server skill`, `load` and `save` bypassed**: those old maintenance runs (skill table, loading / saving every character at once) do nothing now; they are not needed for the live server.
- **No logout loop at shutdown**: the server no longer logs out every active player (`plr_logout ... LO_SHUTDOWN`) when it stops; that cleanup left "ghost" characters behind. (To revisit: players online during a stop / restart, see `docs/TODO.md`.)

**Server console** (`console.c`)
- Commands typed into the terminal the server runs in (read without blocking once per pass of the main loop): `help`, `who` (players online with rank, place, god/imp), `raise <player> <exp>`, `lower <player> <exp>`, `gold <player> <gold> [silver]`, `announce <text>` (to everyone, as "[Server] ..."), `tell <player> <text>`, `kick <player>`, `shutdown` (clean stop, like Ctrl+C). Player names can be shortened like in game; raise/lower/gold also work on players who are offline. Everything is logged with "CONSOLE:".
- Only when the server runs in a terminal (started with an argument, so it doesn't detach); started plain (`./server`) it detaches, and the console switches itself off.
- **Control port**: the server also takes its console commands on 127.0.0.1:5556 (this computer only), one line in, the answer back ending with a "." line. Machine-readable commands for it: `status` (online, ticker, uptime, pid) and `whotab` (one tab-separated line per player online).
- **Live editing**: `edpatch <file>` applies a patch from the editor (see [Data changes](#data-changes)).
- **Quest and chest testing**: `quest <player> [<n> <value>]` shows or sets a player's steps; `talktest <NPC template> <player> <text>` tries a conversation without logging in; `talkreload` reads `npctalk.dat` again; `talkkill <player> <template>`, `talkuse <player> <x> <y>`, `talknear <npc> <player>`, `talkmoney <npc> <player> <silver>`; `chesttest <player> <x> <y>` opens a chest as that player; `chesttest <player> <x> <y> real` with its real open/closed state.
- **Area clears**: `cleartest <player> <NPC template>` counts a kill of that NPC for the player (who must stand in the zone).
- **Kill quests**: `kqkill <player> <NPC template>` counts a kill of that NPC for the player's taken kill quests; `kills <player>` shows the player's `#kills`; `kqtime <player> <minutes>` moves their kill quest times back (tests time limits and waits).
- **Quests**: `questgive <player> <NPC template>` hands that NPC the item it wants, as that player, and shows the exp and gold they got and how often they have done it.
- **Zones**: `zonereload` reads `.dat/zones.dat` again (or the built-in `area.c` table if there is none); `zone <x> <y>` shows the zone names at a spot and the place `#quest` would give.
- **Items**: `give <player> <item template> [count]` (into the backpack; stacks merge), `items <player>` (the backpack with stack counts), `useslot <player> <slot>` (uses that backpack item as the player).
- **Fights** (test server only, they really fight): `wear <player> <item template>|off` puts a new item straight into its worn slot and shows the main values (or takes everything off); `fighttest <player> <NPC template> <rounds> [back|kill]` gives the damage totals of the player hitting the NPC, of the NPC hitting the player (`back`, with the damage done back by thorns and frost and how often it was chilled), or fights until it dies (`kill`).
- **Waypoints**: `wpreload` reads `.dat/waypoints.dat` again and remakes the circles; `wplist`; `wpfound <player> [all|none|<nr>]` shows what a player has found, or sets all / none / switches one; `wpuse <player> <x> <y>` as if the player clicked the circle piece there.
- **Merchants**: `merchreload` reads `.dat/merchants.dat` again; `shop <player> <merchant template> [buy <slot>|sell <backpack slot>|page <38/39>|leave]` shows the shop as that player sees it, or buys, sells, turns a page or ends the remorse.

**Sprite numbers up to 65,535 (Nov 12):** item sprites (`sprite[2]`) and a character's `sprite_override` were signed
shorts in `data.h`, so a sprite above 32,767 turned negative; now unsigned (same size, the `.dat` files don't change).
`client.h` `cmap` sprites and the item sprite fields sent in `svr_tick.c` unsigned too. The editor reads and writes item
sprites as unsigned (0-65,535 in the item editor).

## Data changes

Unchanged except for the version number and the larger view: `merc.dat`, `.moa` character saves, and the 16-byte client messages and compressed tick stream are all as in the original.

**Characters and items**
- New character data slots: `CHD_PRESTIGE` (32) and `CHD_LABTEMPLE` (33), used only by NPCs for lights before. New item flags `IF_NEEDIDENT` (bit 40) and `IF_NEARGLOW` (bit 41); new map flags `MF_NOLIGHT` (bit 10) and `MF_LIT` (bit 12, done in `check_dlight`/`check_dlightm`, so seeing characters and items there and the light the client draws both follow it).
- **Prestige** is `ch.data[CHD_PRESTIGE]`. **Prestige looks**: each character type uses 448 sprite numbers and the 576 after them are unused, so a recoloured copy fits right behind the original: sprite = template sprite + 448 (`god_minor_racechange` sets the look on any class change).
- **Labyrinth temple**: entering a part saves the player's temple in `CHD_LABTEMPLE` (slot 33). A player is in a lab when they have a saved lab temple or their recall point lies in a "Labyrinth" zone (`temple_in_lab`), so custom recall points don't keep lab items or strip them early. Lab items are removed outside the lab by `lab_left_check`. `SEYAN_SHRINES` = 22.
- **Tiered items** (`tier.c`): a tiered item is a plain piece of armor with rolled bonuses, kept in the item's spare `future3[]` fields (`IT_TIER`, `IT_TCAT`, `IT_TLEVEL`, ...; zero in every old item). Thorns and Light use the items' existing gethit damage and light; Thorns is no longer stored on the item (gethit damage adds up): the wearer gets it from the best Thorns piece only (`tier_thorns`, added in `really_update_char`). Regeneration effects: `tier_regen`, called from `do_regenerate`; Warding in `spell_curse` / `spell_stun`. Upgrade and reroll: `tier_upgrade`, `tier_reroll`. Glow: `tier_item_glow`, `tier_tile_glow`; graves: `body_has_items`. Old chest armor numbers: `tier_chest_item`. Soulstone drops: `soul_kill_drop` (tunable `SOULDROP_BASE`, `SOULDROP_PER_RANK`). Spell scroll marks: `item_marks`.
- **Item drivers**: 71 Portal of Time (Lab 10), 72 Lab 11 lecterns, shelves, gates and pages (`use_lab11`), 73 Soul Crucibles (templates 1369-1371, sprites 18220-18228), 74 upgrade stone (template 1372, sprite 18229), 75 MyV2 chest (`talk_chest_open`).
- **Greataxe** (first called Two-Handed Axe): skill 36 (`SK_AXE2H`; Strength/Strength/Agility since the rebalance, Agility/Strength/Strength before), added to existing characters in `really_update_char`; a weapon flagged both axe and two-handed uses it (`get_fight_skill`). Templates 1364-1368 (`tools/world/axe2h.txt`, rebalance `tools/world/axe2h_rebalance.spec`, names `tools/world/greataxe.txt`; axes already in the game were updated by `tools/world/wfix.c`, which keeps any bonus a piece had on top, and renamed by `tools/world/rename_items.c`), sprites 18145-18165. While attacking with one, a character first acted `AXE2H_SLOW` (3) speed steps slower (`ch_act_speed` in `svr_act.c`); the rebalance gave them the swords' speed.
- **Two-handed specials**: `wp2h_chance` (`svr_do.c`), tunable `WP2H_MIN`, `WP2H_MAX`, `WP2H_K` (`data.h`; at first a flat `WP2H_SPECIAL` 1 in 8), plus `weapon_special_bonus` (the Fire set).

  | Greataxe (first version) | WV | Needs AGL / STR / Greataxe | Value | (2H sword WV, AGL / STR) |
  |---|---|---|---|---|
  | Bronze | 15 | 8 / 15 / 1 | 100 | 12, 10 / 12 |
  | Steel | 30 | 16 / 30 / 15 | 500 | 24, 20 / 24 |
  | Golden | 45 | 26 / 48 / 30 | 2500 | 36, 30 / 40 |
  | Crystal | 60 | 36 / 68 / 45 | 12500 | 48, 40 / 60 |
  | Titanium | 90 | 45 / 82 / 60 | 62500 | 72, 50 / 75 |

- **Pentagram enemies** (`is_penta_enemy`: templates 364-385, 538-542, 1094-1097) without belongings leave no grave (`svr_effect.c`). The log line of a pentagram activation shows "(act of needed, n doing pentagrams)".
- **Merchants** (`merch.c`): `.dat/merchants.dat` (`merchant <template> sell <%> buy <%> gold <silver> kinds <mask>` and `stock <template> <items...>`; kinds 1 armor, 2 weapons, 4 magic, 8 other); without an entry a merchant stocks his sale list (`data[0..9]`) plus his template's backpack and buys what `data[0]` is. The 40 shop slots are filled for each viewer before the shop is shown, a tooltip is asked or a trade is made (`merch_fill`; display copies of the stock have `future3[8]` = -1); what players sold him is kept in his `depot[]` (`future3[8]` = what the seller got, `t_bought` = the seller, `t_sold` = when the remorse ends; the item garbage collector now knows merchants' depots). `player[].merch_co` / `merch_page`: the merchant a player deals with and his page there (in `client.h`, so the whole server is rebuilt after a change). `do_char_can_see` ignores a merchant's Stealth (`CF_MERCHANT`). The old `update_shop` is no longer used.
- **Fire and Ice sets**: `set_pieces`, `set_of_temp`, `frost_armor` and the Burning Hits code in `svr_do.c` (`do_attack`); numbers `SET_*` in `data.h`; the Chilled spell is item template number `SPELL_CHILL` (199, not a skill); `CF_NOBURNMSG` (bit 47) for `#burning`; drops in `populate.c` (`SET_DROP_EXP`, `SET_DROP_CHANCE`); merchants destroy sold pieces. Data: `tools/world/fire_ice_sets.txt`, `fire_ice_hem.txt`, `fire_ice_drops.txt`, `ice_cloak.txt`, `ice_names.txt` (applied with `build_lab`, then `refresh_items`).
- **Damage to attackers**: `do_hurt` also does it when a landed melee blow does no damage.
- **Gods' shops**: merchants are character templates `1180-1188`, and 1189 the Scribe (`tools/world/godshop_merchants.txt`).
- **Lab 11 data**: `LAB11_UNDEAD_REGEN`, `LAB11_KEEPER`, `LAB11_ARENA_DEATHS` in `data.h`; `lab_glow_near`.
- **New characters**: starting templates 2, 3, 4, 76, 77, 78 (`tools/world/newplayer_start.spec`); Templar templates 3, 77, 544, 549 (Meditate). The player start templates (2, 3, 4, 13, 76-79, 543-552) and the Blank Template (1) are hidden from the editor's NPC lists.
- **Bank**: a player's bank balance, which pays the depot rent, is `data[13]` (editable in the Player editor).

**MyV2 quests, conversations and chests** (`npctalk.c`, data in `.dat/npctalk.dat`)
- `npctalk.dat` is a text file of blocks: `npc <template>`, `at <x> <y>` (quest rules on an item) and `chest <x> <y>`, with `when say|give|kill|near|money|use` lines (`when near`, `when money <silver>`, `when use` for an item), `if` conditions (`if quest <n> <op> <v>`, `if has <t>`, `if !has <t>`, `if rank <op> <v>`, `if area <text>`, `if skill <nr> <op> <v>`, `if gold <op> <silver>`), `if class <names>` / `if !class <names>` (names joined by |: templar, archtemplar, mercenary, warrior, sorcerer, seyan, harakim, archharakim, or the groups templars, mercenaries, harakims; the character's `kindred` bits), actions (`answer`, `tell`, `announce`, `set quest <n> <v>`, `add quest <n> <v>`, `give item|exp|gold|luck <n>`, `teach skill <nr> <v>`, `take item <t>`, `take gold <silver>`, `teleport x y`, `cast bless|protect|enhance|mshield|light|heal <power>`, `keep`, `pass`) and `end`; plus `quest <n> <name>` and `step <n> <value> <text>`.
- Hooks: say in `npc_hear` (`talk.c`), give and money in `npc_give()`, greeting in `driver.c` (`talk_has_near`, `talk_near_due`), kill in `do_char_killed` next to the soulstone drop, use in `use_driver()` before the item's own driver.
- `.dat/quest.dat`: 255 quest steps per character, kept with the character's creation date (a new character in an old slot starts clean). The first version (31 steps, no header) is converted when the server first opens it, keeping the steps.
- **MyV2 chests** (driver 75): `chest <x> <y> ... end` with `refill <seconds>`, `once player`, `first <t>` (first-time reward), and `reward item|unique|gold|nothing ...` / `reward tier <tiers> <metals> <piece> <level from> <level to> <weight>` lines (tier armor made by `tier_chest_reward` in `tier.c`; the older `tier metal piece weight` form still works). Rewards that can't be given any more (a once-only reward already given, an item marked Unique that exists somewhere) are left out of the draw; if nothing is left, it's empty. `.dat/chestlog.dat` keeps who opened which once-per-player chest (`P`), who got which first-time reward (`F x y cn stamp time name`) and which once-only rewards went to whom (`U`); `server.log` names every once-only reward.
- **How the game's own loot items work** (for reference): a chest, flower, mushroom or bookshelf is a map item whose driver gives something when it is used. Driver 1: one fixed item (data 0). Driver 42: one item at random, equal chance, from up to 10 (data 0-9). Driver 59: gold (data 0). Driver 30: needs an item in the hand, which it takes. Driver 53: an item engraved with the player's name. Driver 54: an item, and it alerts the monsters nearby. Once opened it stays open for its duration (Treasure Chests: 1 hour), then anyone can open it again. Items marked Unique (`IF_UNIQUE`: Helm of Shadows, god weapons, the Ice Gargoyle Cape) can't be created while a copy exists anywhere (`god_create_item`).
- **Chest sprites**: the game's own, 220/221 (lock facing south) and 222/223 (lock facing west). The editor's `itemedit` takes a `sprite` to turn a chest. (North- and east-facing chests, 18130-18133, were tried: first the south/west chests with the lock painted out, then renders of a 3D model, then image-generator art. None matched well enough, so they were removed again with their scripts; they are in the git history.)

**Live editing from the editor**
- The editor reads the game's current files (the server keeps them in shared memory), makes the change on that copy, and sends the difference to the server as a patch file with the console command `edpatch <file>` (control port, `console.c`). Every changed byte range carries the bytes it expects to find. If anything there changed in the meantime (an NPC walked onto the tile, an item was picked up), the server applies nothing and says so; the editor then tells you to try again. Undo works the same way, so it never overwrites something the game changed.
- The server handles the parts that need the game: it takes item lights out and puts them back around changed tiles (including walls and indoors changes, like build mode), resets the players' view caches when sight changes, and does the NPC actions itself (moving through `god_drop_char`, removing with its items, `reset_char` for a changed template). Placed NPCs spawn through the normal respawn timer (`effect.dat`) within a second. An online character's values are worked out again and their client refreshed after a live change (`do_update_char`).

**World patch tools**
- One-off world patches live in `tools/world/`: `lab10_open.c`, `place_items.c` with `lab10_extras.txt` and `lab10_pole_move.txt`, `templar_meditate.c`, `movetowers.py`, `fix_item_status.c`, `tools/world/tier_part2.txt`.
- `tools/world/build_lab.c`: builds an area from a spec file (map tiles, item and character templates, placed items); it also works out each changed template's experience value the way `reset_char` does (a rebuild had left the copied value of the base monster), but only for `copy` and `scale` (before, any `ch` line did, e.g. moving an NPC). `clear` empties an area of items, `movenpc` moves living NPCs to their template's new spot and `killnpc` removes them (Lab 11's monsters are made fresh on each rebuild), so an area can be rebuilt; afterwards `server pop` creates the new NPCs and `server light` the lighting. `place_items.c` and `build_lab.c` give placed items their template number (Lab 10's shrine of Kwai had been placed with 0; fixed in the data). Spec commands added over time: setting an item's driver, `ch <temp> worn <slot> <item temp>`, `ch <temp> gold <silver>`, `it <t> wv`, `atreq`, `skreq`, `dir <temp> <dx>` (resting direction of a template and its living NPCs).
- `tools/world/merchant_stock.c`: sets a merchant template's stock (`merchant_stock <.dat dir> <template> <item templates...>`).
- `build_lab` spec keywords added for the rebalance and the sets: `attr`, `skill`, `hp` / `end` / `mana`, `minrank`, `placement`, `armor`, `gethit`, `hpreq` / `endreq` / `manareq`, `ch <t> additems`, and `itemdata <x> <y> <values...>` (a placed item's data, e.g. a chest's contents).
- `tools/world/refresh_items.c`: gives items already in the world (lying around, carried, worn, in depots) the stats of their template (`refresh_items <.dat> <templates...> [names] [write]`; `names` also copies name, reference and description).
- `tools/world/rename_items.c`: renames items already in the world (e.g. the greataxes).
- `tools/world/remove_npcs.c`: removes NPCs of given templates inside a box (by position or resting spot), with everything they carry and their map links (`remove_npcs <.dat> <x1> <y1> <x2> <y2> <templates...>`). NPCs hatched by a spawner item (Spider's Web, driver 43: up to 3 spiders each, a new one a minute or two after one dies) come back unless the spawner goes too (`place_items` `remove x y`).

## Server-side view changes

**Bigger world view**
- Line-of-sight grid 40×40 → 64×64 (`VIS_W`/`VIS_C` in `gendefs.h`), with all hard-coded `40`/`20` offsets replaced.
- Player sight radius 16 → 22 (`VIS_PLR_RADIUS`).
- The sight cache remembers the radius it was computed with, so a larger request isn't served from a smaller cached map.
- `TILEX`/`TILEY` 34 → 44 (`client.h`).
- Symmetric view cut: `YSCUT = YECUT = 2`, so the player is in the exact center.
- `MINVERSION` → `0x020F01`, so old 800×600 clients get a clean refusal instead of garbage.

**New packets** (the client must be updated for each)
- **Item tooltips**: the client asks with `CL_CMD_ITEMINFO` (34), the server answers with 64-byte `SV_ITEMINFO` lines (75). Equipment compare: `tip_compare` in `svr_tick.c` writes the section and a hidden line (font 8, "W <slot> [<slot>]") naming the worn slots; the client (`engine.c` hud_tooltip, `socket.c`) reads it and asks for those worn tooltips while Shift is down.
- **Buff timers**: a 20-byte `SV_SPELLTIME` packet (74) with each spell update.
- **Glow**: `SV_TILEGLOW` (76: map tile, glow) and `SV_TIERS` (77: the tiers of the backpack and worn slots, or of the open shop / grave). The glow of a map tile is a new field in `struct cmap` on both sides; it scrolls with the map. In the clean HUD the panels behind items are drawn by the presenter (the framebuffer holds the transparent key colour there); the outline is blended with the panel colour, not the key, which had turned every colour pink.
- **Waypoints** (`waypoint.c`): item driver 76 = a circle piece (made by the server from `.dat/waypoints.dat`, template 0, walkable, usable); `svr_tick.c` shows a player the lit sprite (+10) of the waypoints he found. `SV_WAYPOINT` (79, 80 bytes: row, rows, flags 1 found + 2 here, picture sprite, number, name 32, line 40), one per row, opens the window with the last row; `CL_CMD_WAYPOINT` (35: number) travels. Only sent to clients from 2.15.05 on. Found waypoints per character: `.dat/wpfound.dat` (256 bits a row, like `clears.dat`).
- **Spell scroll marks**: `SV_ITEMMARKS` (78: a letter and a number per slot, for the backpack and worn slots or the open shop / grave), sent like `SV_TIERS`.

## Tools

**Server and data**
- **`makegod.c`**: a small offline tool that lists the player characters in `char.dat` and sets or removes god/imp/staff flags. The original game had no god password; gods were set directly in the data files.
- **`tools/claude-sync.sh`** syncs the server between Ubuntu (WSL) and the Windows copy: `send` (Ubuntu → Windows, keeps any newer Windows files), `get` (changed source files and the Makefile Windows → Ubuntu, with a backup, then `make server`), and `get-world` (world `.dat` files, server stopped).
- `tools/world/`: scripts that read the world data directly: a full minimap render, a scan of every portal/teleport/ladder with a landing check, and a zone map. Reports are in `docs/`.
- `tools/design/item_tier_samples.py` prints sample tier rolls (the same rules, for looking at numbers).
- Build: `tier.c`, `godshop.c`, `merch.c`, `console.c`, `npctalk.c` and `waypoint.c` are new files, so the Makefile changed.

**Lab 11 layout sheet**
- `tools/world/lab11/lab11_layout.xlsx`: one cell per tile with a short code (wall, water, shelf, lectern, gate, brazier, merchant, ...), coloured automatically, plus a Sections sheet with the rectangles that drain together, and codes for the shrine room (SW, SF, SC, SD). `lab11.py build` checks it (required swims, reachability) and turns it into the build spec; `lab11.py export` made the sheet from the first, generated layout (`draft_layout.py`).

**Elysium layout sheet**
- `tools/world/elysium/elysium_layout.xlsx`: the whole built Elysium (map x 771-829, y 788-826; rows = x, north at the top, like the minimap), one cell per tile with codes for walls, floor, fire bowls, doors, the shrine, the 10 god shop merchants (M1-M10) and the monster gallery NPCs. A hidden "Original" sheet keeps the export so only changed cells get rebuilt. `?note` cells are free-form requests.
- `elysium.py export|diff`, `area_dump.c` (dumps a map rectangle with items and characters), `elysium_preview.png`.
- `elysium_build.py` makes the build_lab spec from the cells that changed; `apply.sh` runs it on the server .dat and relights the area. Round 2 rewrite after the first rebuild left messy floors: new floor copies plain floor (never carpet pieces) from the same room, flags come from the same room (a room that is all new is listed to check), walls take the nearest wall style, and the sheet has codes for columns (`c`), gate/arch pieces (`g`), tables (`t`) and portals (`P`) so nothing is silently turned into plain wall. An unchanged sheet builds to nothing.
- `isorender.py` draws an area from the game's camera angle (`elysium_render.png`).

**Sprites** (new sprites are PNGs in the client's `gfx` folder)
- `tools/sprites/export_sprites.py`: exports a character's frames from `gx00`/`pnglib` to PNGs (colour key made transparent), e.g. to give the V2 Sprite Recolor Tool the base Templar, Harakim and Mercenary.
- `tools/sprites/install_variant.py`: copies a recoloured set into `gfx/` right after the original (sprite numbers + 448).
- New sprites from generated art (`tools/sprites/art/`, made with `tools/sprites/shrink_art.py`): **18140** an open parchment scroll and **18141** a weathered open book, ready for new items. The script cuts out the background, shrinks the object to sprite size and rounds the colours to the client's 16-bit palette.
- **Waypoint circles** (`tools/sprites/draw_waypoint.py`; originals in `tools/sprites/art/waypoint/`): nine see-through ground pieces each, so they lie on any floor: rune circle 18300-18308 (lit, blue: 18310-18318), pentagram 18320-18328 (lit 18330-18338). The PNGs hold colour multiplied by alpha, as the client reads them. Travel window pictures (`draw_waypoint_pics.py`): 18340 "not found yet", 18341 stock picture; 18401-18655 = the picture of waypoint 1-255 (made in the editor).
- Hourglass sprites 18121-18128 (`tools/sprites/draw_hourglass.py`); unlit brazier 18129 (`tools/sprites/draw_brazier_unlit.py`).
- **Trees in Hide mode**: stumps 18190-18202 (`tools/sprites/art/stumps/`).
- **Torn page sprites** 18170-18183 (`tools/sprites/art/pages/`), torn from one generated page into four pieces.
- **Greataxe sprites** (`tools/sprites/art/axe2h/`): a double-bit axe in bronze (18145), steel (18150), gold (18155), crystal (18160) and titanium (18165), each but titanium followed by four damage states like the two-handed swords (rust, patina, tarnish, clouding, chipped edges). Made from a generated steel axe by `axe2h_build.py`.
- **Emerald special armor** 18210 helmet, 18211 armor (`tools/sprites/art/emerald_special/emerald_special.py`).
- **Soul Crucibles** 18220-18228 (three ranks: pale blue, violet, gold glow; each empty / one stone / full) and the **upgrade stone** 18229, made from one generated picture by `tools/sprites/art/crucible/crucible_build.py`.
- **Gods' shop page arrows** 18230/18231; **Lit** flag icon 18232 and dot 18233 (`tools/sprites/art/lit/`).
- **Ring stones and spell books** 18240-18287 (`tools/sprites/rings_books.py`); **Ice set** 18100-18105, the Fire set recoloured (`tools/sprites/ice_set.py`).
- Chest sprites for north and east (18130-18133) were tried and removed again; see [Data changes](#data-changes).

**Testing notes**
- Two clients at once (`play2.bat`, see [Client](#modernization-changes)).
- Live editing, tested with the real server: a floor, a light-giving object placed (the light around it rose) and erased (the light went back exactly), an NPC placed, moved, turned, its greeting changed and respawned, undo, and a deliberately wrong patch rejected while the server kept running.
- NPC placement, tested on a copy with the real server: a placed Geoffrey spawned with all his items, facing as set; a moved and turned one kept its spot; a removed one did not come back. Template editor: a changed greeting and patrol reached the respawned NPC, and the Janitor walked a new route set in the editor.
- Conversations: a quest intro over two lines that sets step 1, a follow-up line for step 1 and above, non-matching speech ignored, steps shown and reset from the console. Kills counted only once the quest was at the step, 1/3 and 2/3 across two Skeleton templates, the third finishing the step, a template-number match, a wrong area blocking its line, and no counting after the step was done.
- Chests: tier lines with a level range and fitting metals (levels 3-6 in Bronze/Steel/Golden, Golden only at 5-6), with chosen metals at level 16-18, and in the older form (a list of six metals once failed to read, being longer than its buffer; fixed); a Bronze armor of Magic tier made new; gold; once per player refusing the second try; an "once on the server" reward given once and then left out of the draw (the next players got a new Bronze Mage Helm of Heal and another item from the list); first-time rewards for three players in a row, the chest's timer started by the first opening of a closed chest.
- Fire and Ice sets (`fighttest`): 4 Fire pieces raised the two-handed specials from 19.2 % to 23.3 %; the 6th Fire piece raised melee damage by about 11 % (the burn plus its Strength); 4 Ice pieces raised Blast by 5 (plus the armor's own Willpower and Intuition); with 6 Ice pieces a Gargoyle hitting 3000 times was chilled about 1 time in 5 landed blows, and the thorns did 9.1 (Fire) / 6.5 (Ice, with frost) damage back per attack.
- Merchants (`shop`): selling and buying back, the remorse ending on leaving (kept at the normal price; a Fire piece destroyed), 43 items on two pages, a 50 % price.

## Quest item pictures (Nov 16)

The quest items have their own pictures (sprites 44510-44521, `Client\GFX`, published: client-dist 39aab4b):
Stolen Ledger, Potion of Second Wind, Stoneskin Potion, Foreman's Seal, Chieftain's Stone Axe and Merchant's Signet are
rendered from Quaternius's RPG Pack 2 (CC0, OBJ, `MyV2\3d Models\RPG Pack 2`) with `tools/sprites/item_icon.py`
(+ `objmodel.py`: .obj files, bottle glass drawn behind the liquid, colour swaps per material); Bundle of Moonwort,
Harlan's Studded Belt, Quarryman's Amulet and Greyfang's Fang are the game's own pictures reworked; the Greyfang Amulet
is the Lizard's Teeth Necklace with grey wolf teeth and Greyfang's fang on a gold cap. Red Harlan's Head keeps its picture.
Item templates and every copy still showing the old picture changed by `tools/world/quest_fix/item_sprites.py` (live).
Details: `tools/sprites/quest_items/README.txt`.

## Editor: Items page (Nov 16)

A new **Items** page (left bar, under Map): every item template in one list with its picture, number, name, kind
(weapon and its skill, armor and where it is worn, ring, amulet, used up, quest...), min. rank, value, weapon and armor
value, and how many copies exist on the map, with NPCs and with players. Search, a kind filter (default: everything
players can pick up) and sortable columns (both remembered). Click a row to edit the template; **Copy...** makes a new
item from one, **+ New item** an empty one (`itempblank`). Applying a template change now also changes the copies NPCs
and players carry, wear or keep in a depot (before: only those on the map), wherever a copy still has the template's
old value (`itempset` with `copies: 'all'`; the box in the template's footer, ticked by default, shows the counts).

## Recipes: players make items (Nov 16)

New: **recipes** (`server/recipe.c`, `.dat/recipes.dat`). A player holds item B under the mouse cursor and uses item A
(or the other way round): both are used up (one of a stack) and he gets the result. Per recipe: keep A / keep B (a tool
that stays), "either way" (else only B held + A used), a minimum rank, and the message he reads. Recipes are checked
before the game's own combinations (`use_driver.c`: the flasks and flowers, driver 4; the Leather Necklace and Lizard's
Teeth, driver 14), so a recipe with the same two items replaces what the game did. Chains (a necklace taking teeth one
by one) are one recipe a step; an NPC can then ask for the finished item in a quest.
Editor: **Items page -> Recipes**: a table with item pickers (A + B -> result), Keep, Either way, Min. rank, Message;
Save writes recipes.dat and has the running game read it (`recipereload`). It refuses two recipes with the same two
items. "What the game itself already does" lists the built-in 30 with "Make a recipe of it".
Console: `recipereload`, `recipetest <player> <used slot> <held slot>` (tested on a test server: flask + red flower,
and the reverse order). Live since Nov 16 (update-code).

**Needs a skill (Nov 16, later):** a recipe can need a skill (or an attribute) at a value - the player's current value,
with gear and spells; a skill must also be learned ("You need Bartering 150 to make that."). recipes.dat lines are now
`recipe <A> <B> <result> <flags> <min rank> <need: skill 0-49 / attribute 100-104 / -1> <need value> <text>`.
Drinks (used up when used, not worn) now check their **Needed** column when drunk, against the current values
(before, only Min. rank was checked; no drink in the game had Needed values). Item Needed values are bytes: 127 at most.
Console `usetest <player> <slot>` (he uses that item). Tested on the test server; live since Nov 16.


**The game's own combinations as recipes (Nov 16):** the 30 (flasks and flowers, Leather Necklace + Lizard's Tooth) are in the live recipes.dat, exactly as the game did them (only that way round: flag 4, no message, no needs); copy in `tools/world/recipes/recipes_builtin_nov16.dat`. Mixes not listed still do what the code does (a Black Potion).

**Rings and the Amulet of the Sun as recipes too (Nov 16):** 39 more in the live recipes.dat (now 69): plain golden ring + ruby / emerald / sapphire / topaz / amethyst / diamond, plain silver ring + ruby / emerald / sapphire (ring used, gem held), and the six Amulet of the Sun part combinations (either way). Still in the code only: Piece of Gold / Silver used alone -> a plain ring, and the "too powerful for a silver ring" / "needs a golden ring" refusals.

## Discord: new channel layout, everything as code (Nov 16)

Cody's layout: Server (updates, commits, announcements, info, game-chat), Community (chat, screenshots, trade, guides),
Feedback (suggestions, balance, bugs). The bots post in three channels only; #updates is Cody's own (no bot), #commits
is GitHub's own Discord hook. Webhooks (in the Server folder, never in git):
- `discord-system-webhook.txt` -> #announcements: guard shouts, announcements, entering / leaving, [Server] messages,
  and now the server going up / down / crash notices too (unless a `discord-webhook.txt` exists).
- `discord-board-webhook.txt` -> #info (who's online, rankings: in place, as before).
- `discord-chat-webhook.txt` + `discord-bot.txt` (line 2: the channel id) -> #game-chat, plain text as before.
Every bot post is a code block (```, the up / down notices coloured with ```ansi) except #game-chat.

## Rat-Catcher's cellar: the ratlings (Nov 16)

The small room in Underground I (886-891, 24-30), where the hole in the quest giver's house (528,465 in Aston) lands (888,25): two **Young Ratlings** (templates 2138, 2139; Lance Corporal, Ratling stats at 65%, 3,000 points) and the **Ratling Broodmother** (2140; Corporal, 80%, 11,000 points). `tools/world/rat_cellar/place_ratlings.py` (made.json). Live.

**Mirela and her quest (Nov 16):** Mirela (template 2141, a woman), Aston's rat-catcher, in her house at 525,468 (the hole there lands in the ratling cellar). She wants the **Broodmother's Tail** (item 2022, sprite 44522; the Ratling Broodmother carries it) and gives the **Rat-Catcher's Ring** (2023, sprite 44523, +1 Agility worn): once, Lance Corporal and up, 200 exp (standard: 5% of the Lance Corporal climb), no gold. `tools/world/rat_cellar/mirela.py`. Live; sprites published (client-dist, Cody pushes).

**The cellar ratlings are calm (Nov 16):** the Young Ratlings and the Broodmother attack no one until a ratling is attacked (data 43-46 = 0; they keep group 12 and protect it, data 59). `tools/world/rat_cellar/calm.py`. Live.


## Fenwatch: the marsh town (Nov 16)

The hub town of band C (Sergeant Major to Captain), east of the Wolfwood. So far the place itself; its people, merchants, waypoint and quests come next.
- **The Fen Road**: from the east end of the Wolfwood's road (449,728) through the marsh to the town's west gate.
- **The marsh** (zone "Fenwatch Marsh", x 406-494, y 732-852): marsh grass with pools of murky water and patches of mud, reeds along the water, willows, dead trees and stumps, a thick rim of trees outside. Nothing lives there yet.
- **The town** (zone "Fenwatch", x 424-476, y 770-834): a log palisade with four gates (west: the Wolfwood; east, north and south: roads that end at the tree rim until the Drowned Village, the Barrow Hills and the Lizard Hatcheries are built), two torches at each. Two streets cross at a market square of stone setts (its centre, 449,801, is kept free for a waypoint). No monsters in town; the pools and the pond can't be walked on.
- **Buildings**: the inn (429,774 - 441,787; tavern, so players can log out), the Bounty Office (432,790 - 440,797), the chapel (fieldstone, 428,806 - 440,817, graves beside it), the reeve's hall (fieldstone, 428,821 - 439,831), a store (454,775 - 462,783), a smithy (454,787 - 462,795), the alchemist's hut (mossy stone, 466,774 - 473,781, a herb plot beside it), a spare house (466,788 - 473,796), the fisherman's shack (454,806 - 460,812) by a pond with a jetty.
- **New ground and plants** (`tools/sprites/world_marsh.py`; sprites published): **marsh grass** (35700-35703), **marsh mud** (35750-35753) and **murky water** (35800-35803), each with 4 variants and soft edges into grass (the 46 tiles after each); soft edges **on marsh grass** for murky water (35850-35895), marsh mud (35900-35945) and the path (35950-35995); **reeds** (38200, 38202, 38204, 38206: cattail clumps you can walk through; each N+1 its cut-down form for "hide walls").
- **Editor**: Floors tab, the three marsh grounds beside the other new grounds; painted on grass they get grass edges as before, and marsh grass gets its own soft edges where murky water, path or marsh mud touches it (after the save; the page's live preview shows only the grass edges). Objects tab, Plants: Reeds I-IV.
- Built with `tools/world/fenwatch/build_fenwatch.py` (the editor's World class; it places the marsh-based edges itself, with stone setts and the forest's dirt road counted as path), then `./server light` on a copy for the torches. Preview pictures: `Client\Claude outputs\fenwatch_preview\`.
- **The people of Fenwatch (Nov 16)** (`tools/world/fenwatch/place_fenwatch.py`, templates 2142-2158 in `made.json`): **Joss** the fisherman (his shack), **Ilse** the priestess (chapel), **Aldous** the reeve (his hall), **Petra** the scholar (in the inn), **Rook** the alchemist (his hut) and **Bounty Master Corwin** (Bounty Office): friendly, each with a greeting that points at the area its quest will be in; no quests yet. **Marta** keeps the inn, the Heron (Astonian Ale, Dragon's Breath, Mana Lite); **Odger** the store (torch, lock pick, flask, healing and mana potions, the greater ones too); **Brigit** the smithy (steel, golden and crystal weapons, greataxes, golden armor): `merchants.dat` has their stock. Eight **Fenwatch Guards**, two inside each gate. **Waypoint 6 "Fenwatch"** on the market square (no picture yet). The innkeeper's and Petra's corners of the inn are not tavern tiles (an NPC can't stand on one).
- **The border to the Wolfwood (Nov 16)** (`blend_wolfwood.py`): wavy instead of a straight line at y 731/732, the marsh's tree wall there thinned to a loose mix of forest trees, willows and dead trees, with edge tiles where the forest floor creeps into the marsh grass (sprites 35650-35695; the editor places them too). A no-monster strip (y 732-733) keeps the wolves in the wood and, later, the marsh's monsters in the marsh.

## Drowned Village (Nov 16)

East of Fenwatch (zone "Drowned Village", x 416-504, y 853-950), for Sergeant Major to Second Lieutenant; reached by the east gate's road.
- **The sunken village**: nine ruined houses (mossy stone and timber, half their walls gone, dark plank floors), a broken road, many murky pools, reeds, dead trees.
- **Maud's bog** (north-east): a wide bog with an island (433,906) reached by a mud causeway; a mossy hut (430,903 - 436,909), a campfire, piles of bones.
- **The Flooded Chapel** (zone, yard 454,896 - 468,912, nave 457,899 - 465,910, and the sunken lane at x 460-461, y 884-896): under water (the game's "under water" tiles: you can walk there, breath runs out), a low fieldstone wall around the yard, graves, an altar with candles.
- **The shore** (east): a sand beach, the sea (can't be walked on) and the wreck of Captain Morrow's ship (a plank deck with rails at 487-493, 910-924), barrels and a broken wagon.
- The Fenwatch marsh's east tree wall is thinned; a no-monster strip (y 849-850) keeps the village's monsters out of the town's marsh.
- Built with `tools/world/drowned_village/build_village.py`.
- **Monsters** (group 34; `tools/world/drowned_village/place_village.py`, numbers in `made.json`; looks recoloured from the game's own monsters with `recolor_creature.py`): 22 **Drowned Sailors** (Sergeant Major, a few Second Lieutenant; the Undead in sea-green, sprites 50000+) in the village and around the wreck; 14 **Bog-men** (Second Lieutenant; the Grolm in mud brown, 50500+) around Maud's bog; 5 **Sea Golems** and the **Sea Golem Sentinel** (Second / First Lieutenant; the Golem in blue-green, 51000+) under water in the Flooded Chapel; **Captain Morrow** (Second Lieutenant) on his wreck; **Maud the Bog Witch** (Second Lieutenant) in her hut. Sailors and Bog-men carry their heads.
- **Quests** (item quests, `#quest`; no gold except the bounty):
  - **Joss**: Captain Morrow's Compass -> **teaches Swimming**, 16,000 exp (from Sergeant Major). The Silver Net (the Sentinel carries it) -> **Fisher-King's Belt** (+8 Swimming, +25 hitpoints, Second Lieutenant), 25,000 exp (from Second Lieutenant).
  - **Ilse**: Maud's Hex-Doll -> **Ring of Tides** (+15 mana, +4 Meditate, Sergeant Major), 16,000 exp. Maud's Herb Pouch (Maud carries it too) -> 3 **Draughts of Clear Water** (mana back to full), no exp: two hand-ins, because an item quest gives one kind of item.
  - **Bounty Master Corwin**: Drowned Sailor Head and Bog-man Head, 2,500 exp + 12.5G each, as often as you like, from Second Lieutenant.
- **Swimming** (server `svr_do.c`, `driver.c`, `data.h` SWIM_FULL, `skill.c`): under water a player loses breath (about 4.5 hitpoints a second, no regeneration) as before; now each point of Swimming takes 1/125 of that away, **none left at Swimming 125**. This also holds in the game's other under-water places (the Underwater Pentagram area). No class had Swimming in its skill list, so the teaching NPC gives it to the player's class on the spot (up to 60 raised, difficulty 5, like Perception).
- **Item pictures** 44524-44532 (`tools/sprites/quest_items/drowned_village.py`): the two heads (cut from the monsters' own frames), compass, hex-doll, net, pouch, ring, belt (drawn: a coiled sealskin belt with a silver fish buckle; a first recolour of the game's thin belt strip looked bad), draught. Items 2024-2032; the quest items and heads have no value (can't be sold) and no labyrinth flag.

## Barrow Hills (Nov 17)

North of Fenwatch (zone "Barrow Hills", x 320-403, y 768-852), for First Lieutenant; a dead end reached by Fenwatch's
north gate road (the North Road, y ~800-802), which ends at a ring of standing stones (366,805) with trails on.
- **Tombs**: the **King's Barrow** (zone, 327,794 - 347,818; door 347,806; three fire bowls, bones) and the **Scribe's
  Barrow** (zone, 346,775 - 358,789; door 352,789; a candle, bones) in mossy stone; two medium tombs (334,836 and
  368,779, room for a few monsters each) in mossy stone; six small ones in fieldstone. Dirt floors, dark inside (indoors).
- Grass upland, dead and old trees, stumps, tombstones; a pine / old-tree rim. Fenwatch's marsh north tree wall is opened
  at the road and thinned; a no-monster strip (x 407-408) keeps the hills' monsters out of the marsh.
- Built with `tools/world/barrow_hills/build_barrow.py` (uses `tools/world/arealib.py`).
- **Monsters** (group 35; `tools/world/barrow_hills/place_barrow.py`, numbers in `made.json`): 15 **Barrow Skeletons**
  (the Skeleton's own look; Sergeant Major and Second Lieutenant), 17 **Barrow Wights** (First Lieutenant; the Undead Lord
  recoloured grave-pale, sprites 52000+), two wights and a skeleton in each medium tomb, two wight guards in the King's
  Barrow; the **Barrow Wight Scribe** in the Scribe's Barrow (a strong First Lieutenant; carries the **Rune-Carved
  Tablet**) and **Barrow King Ulfgar** in the King's Barrow (Captain, the Lord's own dark look; carries **Ulfgar's Torc**).
- **Undead regenerate less here** (and in the Drowned Village): undead in monster groups 34 and 35 heal like Lab 11's,
  about 4 hitpoints a second instead of about 12 (server `svr_do.c`, `SLOW_UNDEAD_GROUP` in `data.h`; Cody, Nov 17: the full
  rate made them too hard to kill at their rank). Holy water still works on them.
- **Quests** (item quests, `#quest`; once each, from First Lieutenant, no gold): **Aldous**: Ulfgar's Torc -> the
  **Ulfgar's Torc** amulet (+3 Bravery, +5 Resistance), 51,000 exp. **Petra**: the Rune-Carved Tablet -> **Scholar's Ring**
  (+3 Intuition, +6 Identify), 37,000 exp. Item templates 2051-2054; pictures 44533 (tablet), 44534 (torc, both items),
  44535 (ring) (`tools/sprites/quest_items/barrow_hills.py`, README.txt). Published: client-dist 0161385.

## Stonehold and the pass (Nov 17; live: ground, snowy grass, townspeople)

The band D hub (zone "Stonehold", x 650-715, y 775-845; Major to Brigadier General), reached from the Lizard Hatcheries' road:
- **Stonehold Pass** (zone, x 596-649): a narrow canyon of pale granite cliffs (the game's rock blocks 1204 / 1206) with snow
  along its edges, pines and dead trees; the road climbs from the Hatcheries' south edge to the town.
- **The town**: a hollow ringed by granite cliffs, its buildings cut into the rock: the **Watch Barracks**, the **Granite
  Hearth** (inn), **Hagar's Forge**, **Varo's Temple**, the **Trader's House** (zones), two houses, an old mine adit in the
  south cliff (dead end for now: the Soulstone Mine idea, TODO). A fieldstone fort wall with a two-tower gatehouse across the
  north entrance; cobbled streets to the square (682,810, kept for waypoint 7); snow patches, pines and boulders.
- **Five ways out**, each with a guard post (two guards, facing away from town; placed with the townspeople): the north gate
  (the pass), west (-> Golem Foundry), east (-> Monastery), south-west (-> Ashen Fields), south-east (-> the Last Bastion's
  pass and the Gargoyle Spires). The roads to areas not built yet end open at the town's edge. No monsters in town or pass.
- Built with `tools/world/stonehold/build_stonehold.py` (guard posts in `made_terrain.json`).
- **Snowy grass** (Cody: "a snowy grass look... towards the top of a mountain"; his own snow painting kept): new ground
  sprites 36100-36287 (`tools/sprites/world_snowgrass.py`): pale, cold alpine grass with snow lying in patches, soft edges
  into green grass, and soft edges on snowy grass for soft snow, the path and the dusty path. Every grass tile of the pass
  and the town became snowy grass (`snowy_stonehold.py`). The editor knows it (Grounds list; painting snow or a path on it
  gives the snowy edges by themselves, like marsh grass). Published in client-dist b73a33d. The 17 green pines of the pass
  and the town became **snowy pines** of the same shapes (Cody, Nov 17, 20:10; `snowy_pines.py`).
- **The townspeople** (`place_stonehold.py`, `made.json`; greetings only, their quests come with the areas): **Hagar** the
  smith (Forge), **Varo** the priest (Temple), **Commander Rhea** of the Stonehold Watch (Arch-Templar look) and **Watch
  Sergeant Brann** the bounty officer (Warrior look) in the Barracks; **Dora** keeps the Granite Hearth (drinks as at the
  Heron; the rest of the inn is a tavern: log out there); **Selwyn** in the Trader's House: a **rotating stock** - every hour
  4 new Rare or Epic helmets / body armor (22:8), level 12-16, only Steel, Emerald, Crystal or Titanium (the new metals field of
  `rotate`), **priced by level and tier more than by metal** (Cody: high-level steel must not be cheap; `rot_value` in
  merch.c: 2G x 1.25^level x tier (Rare 4, Epic 9: Cody doubled Rare and tripled Epic, 20:38) x metal, only a nudge (Steel 1, Emerald 1.1, Crystal 1.2, Titanium 1.3; Cody:
  steel must not be half the price of titanium), then his `sell 200` (2x) and the buyer's Barter: e.g. level 12 Steel Rare
  233G, level 16 Titanium Epic 1,661G at Barter 150, 4x that with no Barter). Only his own rotating pieces are priced so; other loot keeps its value. He buys nothing (new `rotate` line in
  merchants.dat, `merch.c`; a click while his wares change shows the new ones and buys nothing). Ten gate guards, a
  Warrior and an Arch-Templar at each way out, facing away from town. **Waypoint 7** on the square.

## Bounty gold lowered (Nov 17)

Bounties pay **1/200 of their exp in gold** (was 1/20: a head paid 10-20 times what the monster carries, and ten Lizard
Heads bought the dearest weapon in any shop). Now: Wolf Head 0.75G, Dire Wolf Head 2G (Huntmaster Edda); Drowned Sailor
and Bog-man Head 12.5G, Lizard Head 26G, Lizard Egg 13G (Bounty Master Corwin). The exp is unchanged. Cody may adjust later.

## Lizard Hatcheries (Nov 17)

South of Fenwatch (zone "Lizard Hatcheries", x 495-595, y 757-860), for Captain; reached by Fenwatch's south gate road,
which runs on through the area and leaves its far (south) edge open for the pass to Stonehold.
- **The marsh carried on** (Cody's choice): marsh grass, mud flats, murky lakes (can't be walked on), reeds, willows, dead
  trees, a few rock outcrops; lakes and mud kept back from the road. A no-monster strip (x 495-496) keeps the lizards out of
  Fenwatch's marsh.
- **Two caves** in the brown mine rock (dark inside, lit by the game's cave lights, Earth Light II): the **Hatchery** (zone),
  set well back west of the road: a great hall with a pool, the **Broodmother's Nest** (zone) and three egg chambers, a long
  tunnel out to a path from the road; and the **Archmage's Grotto** (zone), a smaller cave at the far end, entered from the
  north by its own path.
- **Lizard eggs** (new world sprites 38300-38307, `tools/sprites/world_eggs.py`): one big leathery egg a tile in a nest of
  twigs, reeds and straw (cream, pale, greenish); 24 of them (32 since Cody placed more in the editor, Nov 17 evening), 3-4 a chamber and 2-3 in each mud pit outside. **Using an egg**
  (server item driver 77, `use_lizard_egg` in `use_driver.c`): you lift a **Lizard Egg** out of the nest - or, 1 time in 5,
  it splits open and a **Lizard Hatchling** (Second Lieutenant, pale yellow-green look 54000) attacks you. Either way the
  nest shows a broken shell until the egg regrows (5 minutes). The nest eggs are item templates 2056-2058 (data: the egg
  item, the hatchling, the chance; duration = the regrow time).
- **Monsters** (group 36; `tools/world/lizard_hatcheries/place_hatcheries.py`, `made.json`): 23 **Lizard Knights** (Captain;
  12 out on the marsh, 11 in the Hatchery), 5 **Lizard Archmages** (Captain; 2 in the Hatchery, 3 in the Grotto; Cody, Nov 17
  evening: three of the Hatchery's five became knights, `fewer_mages.py`),
  **the Broodmother** (Major, dark red look 53000) in her Nest with the **Broodmother's Crown**, the **Hatchery Archmage** (a
  strong Captain) in the Grotto with the **Archmage's Phial**. Every lizard carries a **Lizard Head**.
- **Quests** (item quests, `#quest`): **Aldous**: the Broodmother's Crown -> **Scaled Belt** (+4 armor, +3 Strength, Captain),
  52,000 exp. **Rook**: the Archmage's Phial -> 2 **Elixirs of the Good Moon** (spells +15% for 10 minutes, no Bad Moon
  weakening), 52,000 exp. **Bounty Master Corwin**: Lizard Head 5,200 exp + 26G, **Lizard Egg** 2,600 exp + 13G, as often as
  you like, from Captain (the egg: a pseudo-bounty for now; later an Alchemy ingredient). Aldous's, Rook's and Corwin's
  greetings name what they want. Items 2055 (Lizard Egg), 2059-2063; pictures 44536-44541
  (`tools/sprites/quest_items/lizard_hatcheries.py`). Built with `build_hatcheries.py` (terrain, eggs) and
  `place_hatcheries.py`. Published: client-dist c71f5d4.

## New potion effects (server, Nov 17; written by Fable Nov 16)

Live since Nov 17 (tested on the test server: both potions drunk, their effect on the character, no crash):
- **Elixir of the Good Moon** (spell item `SPT_GOODMOON` 65001, `skill_driver.c` `has_good_moon`): while it lasts (or at full
  moon, or wearing an item with data[9] = 65001: the later Ring of the Good Moon) spells are 15% stronger and a Bad Moon
  doesn't weaken them. A potion: a timed potion with data[1] = 65001 (made with the Lizard Hatcheries).
- **Potion of the Frozen Heart** (`SPT_FROZENHEART` 65002, `svr_do.c`): while it lasts, 3.6 extra hitpoints a second.
- Karate for every class was part of it too, but is taken out again (Cody, Nov 17: no use for it yet); no NPC teaches it.
No such potions are in the world yet.

## Wall decorations for all four walls, turned shrines (Nov 16-17)

Items are drawn at full height even with hide walls (F6), so a decoration on the far side of a wall shows there: it now
has its back. Sprites 48000-48025 (`tools/sprites/wall_decor*.py`, `tools/sprites/art/shrines_cody/`; published):
- pictures (Misty Plains, Sunset) and the framed Mirror: W versions and wooden backs for N / E walls; the framed Mirror
  (1246) now hangs like the pictures (48000; its template and every copy; the two on a north wall at 614,530 / 622,530
  got the back);
- round mirrors and shields (the game had S and W): wooden / leather backs for N and E;
- bookshelves: the book-of-wisdom shelf for S, a plain back (no books) for N and E;
- temple shrine (792) and Seyan'Du shrine (914) turned W / N / E: the temple's statue and bowl drawn by Cody, the sides
  turning with it (the shadowy side only shows facing S and E; the shiny side everywhere else).
Skeletons in Chains already had all four (620 S, 622 W, 626 N, 624 E).
Item templates 2033-2050 ("..., wall W", "..., back, wall N" ...; `tools/world/wall_decor_items.py`, live). Editor: a
**Facing** row (S / W / N / E) in the side panel for a placed shrine, picture, mirror, shield, bookshelf or skeleton in
chains: one click turns that one (shrines keep their own settings this way).

## Bounty items stack (Nov 17, evening)

Cody: bounty hand-ins stack, and handing them in takes the whole stack.
- **Bounty items stack** like potions, up to 20 in one backpack slot: Wolf / Dire Wolf Heads, Drowned Sailor and Bog-man
  Heads, Lizard Heads, Lizard Eggs - and every bounty made later, by itself. A bounty item is what an item quest wants that
  can be done any number of times and pays gold (only bounties pay gold); the server works it out from the quests
  (`bounty_item` in `npctalk.c`, stack kind 3 in `tier.c`). Ctrl+click takes one off a stack, as with potions.
- **Handing in a stack** gives the reward once for each item in it (exp and gold added up); if a quest has a limit and
  wants fewer, the rest comes back.
- Console: `questgive <player> <NPC template> [count]` hands in a stack.
Tested on the test server (12 Lizard Heads: 62,400 exp + 312G; 5 Wolf Heads; 4 Bog-man Heads; quest items that aren't
bounties, like the Broodmother's Crown, still don't stack). Live Nov 17 (update-code; the new build also holds Stonehold's
rotating-trader code, unused until its merchants.dat line goes in).

## Editor: "Learn from the map" sees the trees (Nov 17, evening)

In groves (willows, dead trees, pines) the trees stood close enough to look like walls to the area learner, so it left
them out and learned only the floor. Trees, plants, stumps and rocks now never count as walls (`NOT_WALLS` in `mapedit.py`).
Checked on the Lizard Hatcheries (willows, dead trees and reeds are learned now) and the Wolfwood.

## Golem Foundry (Nov 17; band D, Major) - LIVE

West of Stonehold (zone "Golem Foundry", x 650-740, y 670-765), on Stonehold's west road. Cody's choices: a snowy yard
and one great hall, the Brass Colossus in its own casting pit; anvils, molten iron and workshop pieces, nothing modern.
- **The yard**: snowy grass and snow, slag heaps (the game's lava rocks), golem wrecks, ore, crates, snowy pines.
- **The Foundry Hall** (zone): a slate hall on flagstone; eight stone furnaces along the north wall feeding a channel of
  **molten iron** (new ground 36300-36349, blocks walking, soft edges into the flagstone) with a branch to the casting
  moulds; crucibles, ingots, anvils, grindstones, quench buckets, long workbenches, tool racks, crates; the golem works;
  **the Forgemaster's Forge** (zone) in the south-west corner. Lit by fire bowls.
- **The Casting Pit** (zone): a round pit behind the hall, a ring of molten iron, one stone bridge in.
- **New world pieces** (`tools/sprites/world_foundry.py`, from Cody's `3d Models\Fantasy Props` + RPG Pack 2): anvil on a
  log 38400, anvil on a block 38402, crucible 38404, quench bucket 38406, grindstone 38408, iron ingots 38410, casting
  mould 38412, stone furnace 38414, golem wrecks 38416 / 38418, tool rack 38424, crate stacks 38426 / 38428 / 38430,
  **workbench pieces like the game's tables** (fill the tile, join into a bench of any length): 38432 / 38442 legs (bench
  along map y), 38444 / 38446 legs (along map x), 38434 plain, 38436 hammer and tongs, 38438 blade and chain, 38440 drawer
  shelf (each N+1 its hide-walls copy; 38420 / 38422 unused). In the editor: **Objects -> Workshop** (for shops too).
- **Monsters** (group 37; the game's Golem recoloured, `recolor_creature.py`): 22 **Iron Golems** (Major, dark iron 55000),
  **the Iron Golem Forgemaster** (strong Major, glowing iron 56000; Foundry Heart), **the Brass Colossus** (Lieutenant
  Colonel, brass 57000, drawn 1.4x bigger: 96x96 frames, `--scale`; Colossus Core). Every golem carries a **Golem Core**.
- **Quests**: Hagar - Foundry Heart -> **Forgefire Ring** (+4 Strength, +8 Enhance, Major) 71,000 exp; Colossus Core ->
  **Belt of the Colossus** (+50 hitpoints, +6 armor, Major) 100,000 exp. Watch Sergeant Brann - **Golem Cores**, 13,000
  exp + 65G each, any number (stacks). Item pictures 44542-44546 (`quest_items/golem_foundry.py`).
- Scripts `tools/world/golem_foundry/build_foundry.py` + `place_foundry.py` (made.json). Tested on the test server (spawns,
  reachability, both Hagar quests once, a stack of 5 cores). Client files published: client-dist 7404065.

## Editor: scatter brushes and area brushes for the new areas (Nov 17, evening)

Scatter brushes (Objects tab): Reeds, Marsh trees (willows, dead trees), Snowy pines, Boulders, Slag heaps (the lava
stones), Golem wrecks, Crates, Lizard egg nests (the working nest items). Area brushes (floor mix + pieces): Marsh,
Lizard Marsh (with egg nests), Mountain Meadow (snowy grass, snow, snowy pines, boulders), Foundry Yard, Foundry Floor.

## Exploration points: a standard value by rank (Nov 18)

A table of pole values by the area's average monster rank (QUEST_BUILD.md 9c: 250 at Private ... 5,000 Sergeant ...
40,000 Major ... 200,000 Warlord), fitted to the game's own Labyrinth poles. One pole per large area off a town (Cody
places them). 34 existing poles that sat below the table were raised to it (none lowered): e.g. Strange Forest 500 ->
12,000, Gargoyle's Nest up to 100,000, Tower VIII 40,000, Bandit Cave 5,000, Dire Wolves Den 12,000, Deep Quarry 15,000.
The pentagram poles keep their own climbing values. A pole still pays its value x 0.5-1.5, never over 10% of the
player's exp.

## Quest givers say what they want and where (Nov 18)

Cody: every quest needs an intro that tells the player what to bring and where to find it. 22 greetings rewritten
(`tools/world/quest_fix/quest_intros.py`; sources checked in the world): Damor and the Cityguard (black candle, the Black
Stronghold north-west of town), the Gorn ghost (bone sword, Cursed Tomb skeletons), Gordon (Potion of Life, pentagram
grolms and gargoyles), Serena (the sword in the stone in her house), Jefferson (Joe, just east), Manfred (silver small-ruby
ring), Leopold (Ratling Fighters, Underground), the Purple One's priest (red flower), Robin (Ratling and Greenling eyes),
the Gorge III coconut merchant, Syleia (ice egg, Gargoyle's Nest chest), the five riddlers (Books of Wisdom on the
gorge's shelves), Ingrid (Skeleton Lord's crypt), the Spider Queen and the Ghost King (where each other lives), Huntmaster
Edda (the Wolfwood), Brann at the quarry (the Foreman's Seal, the Prime Golem). The new areas' givers already said so.
Still to check with Cody: the Gorge III merchants for the Lizard's Teeth Necklace and the Superior Agility potion, and the
five tower-floor NPCs.
