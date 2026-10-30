# Changes

Everything changed from the original Mercenaries of Astonia v2 source. The original client was built with Borland C++ 5 against DirectX 3-era DirectDraw; the server was written for 32-bit Linux.

Each section lists its changes roughly in the order they were made, oldest first.

**Contents**
- [Client](#client): [Modernization](#modernization-changes) · [HUD changes](#hud-changes) · [Game view](#changes-to-the-game-view) · [New HUD features](#new-features-in-the-hud)
- [Gameplay](#gameplay): [God / imp / builder tools](#god--imp--builder-commands-and-in-game-tools) · [Commands for all players](#general-commands-for-all-players) · [New zones and areas](#new-zones-and-areas) · [New for players](#new-features-from-a-players-point-of-view) · [Balance and fixes](#balance-changes-and-fixes)
- [Editor](#editor): [Overview](#overview) · [Server manager](#server-manager) · [Builder](#builder) · [Player editor](#player-editor) · [NPC editor](#npc-editor) · [Quest editor](#quest-editor) · [Conversation editor](#conversation-editor) · [Chest editor](#chest-editor) · [History and logs](#history-and-logs)
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
- The client already loads `gfx/NNNNN.png` before its packed files, so new sprites are just PNGs in the client's `gfx` folder.

**Two clients at once (testing)**
- `-m` lets a second client run at the same time (normally only one may run). `-o <file>` gives a client its own options / login file instead of `merc.dat`, so two clients don't share or overwrite each other's character.
- `play2.bat` starts the second client: `merc.exe -h 127.0.0.1 -p 5555 -m -o merc2.dat`. Start the first one as usual (`play.bat`), then `play2.bat`, and log in a different character there. The server allows several connections from one computer already.

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
- Client fix: the skill list showed Two-Handed Axe a second time as a blank row (the old placeholder for skill 36 was still in the client's table).

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
  - **Unique items are not sold**: everything with the unique flag (Skua's, Gorn's, Kwai's and the Purple One's weapons, the Fire and Ice sets, the Caps of the Math Genius, the Helm of Shadows) and the Grolm Crown (unique in practice, though it has no unique flag).
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

- **Item tables**: `#armor`, `#weapon`, `#sword`, `#dagger`, `#twohand`, `#axe`, `#axe2h`, `#specialw`, `#belt`, `#specialarmor`, `#moddedarmor` and `#rings`. They print tables of requirements and bonuses, read live from the item templates so they stay accurate if an item is changed. `#specialarmor` lists the unique armor (Fire and Ice sets, Ice Cloak, Titanium Armor of Ankh, Winged Boots, Helm of Shadows, Grolm Crown, Cap of the Math Genius); `#moddedarmor` lists the magic suffixes (of the Lion, Snake, Owl, Weasel, Bear, Magic, Life, Defence) that chest helmets and armor can carry, with their normal and Godly values. `#axe2h` lists the two-handed axes (in `#weapon` too) and `#twohand` / `#axe2h` describe their specials.
- **`#quest`**: every skill teacher, read live from the NPC templates: which skill (adjusted for your class, so Templars see Immunity and Surround Hit), who teaches it and where, and the teacher's own hint about the item. Skills you already know are marked; teachers of skills your class can't learn are counted, not listed.
- **`#exp`**: experience this session and in total, each with exp per hour, unspent points, and how much is left to the next rank.
- **`#played`**: time played this session and in total, and the character's creation date.
- **`#repair` / `#repairinv`**: use the Repair skill on every damaged worn item or backpack item. The first use warns that a failed repair can damage or destroy an item; repeating the command within 30 seconds goes ahead. The Repair skill code was split into `repair_citem()` so the single-item skill and these commands share it.
- **`/lowhp <hp>`**, **`/hudfont classic|smooth`**: client-side settings, see [Game view](#changes-to-the-game-view) and [HUD changes](#hud-changes).
- **`#silver <amount>`**: like `#gold`, but in silver coins (100 = 1 gold), so small amounts can be held on the mouse and handed to an NPC (e.g. 50 silver to the beggar).
- **`#journal`**: lists your quests with the journal text for the step you are at (see [Quests](#quests-and-chain-quests)).

## New zones and areas

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
- Four buildings west of New Street now have names: **Garna's Shop** (torches, lock picks, flasks), **Manfred's House**, **Leopold's House** and the **Barracks** (Peacekeepers and a Cityguard).
- **Ice Pentagram Quest** was one rectangle that also took in part of the water next to it; it is now two rectangles around the ice only, and the water is named **Underwater Pentagram Quest**.
- The second "Thieves House I" rectangle (20,20 - 49,69) is the thieves' underground area, now named **Thieves Basement**.
- Note: the small "Aston" box at 1,1 - 20,20 is deliberate. Gods are parked at 10,10 while they take over an NPC (`#usurp`), and naming it "Aston" keeps `/who` from showing that.

## New features from a player's point of view

### Labyrinth
- Entering a labyrinth part through the gate saves your temple; inside, death and recall go to the start of that part as before. Leaving by the exit portal or solving the part gives the old temple back (Purple One's temple, staff temple, ...) instead of always Aston.
- Lab items (keys, the Hourglass of Time, ...) now also vanish when a player ends up outside the labyrinth by recall, being saved by the gods or the god `#recall`, not only at the exit portal. Death is unchanged: items drop into the grave and stay in the lab.
- Shrines of Kwai: 22 now (20 + Lab 10 + Lab 11), so a Seyan'Du sword goes up to 15 + 22×4 = 103 WV.
- New labyrinth parts: [Lab 10](#new-zones-and-areas) and [Lab 11](#new-zones-and-areas).

### Prestige and prestige looks
- **Prestige** counts how often a character has prestiged: an arch class going back to the start of its class line (Arch-Templar to Templar, Seyan'Du stays Seyan'Du). What triggers it and what it gives are still to be decided.
- **Prestige looks**: prestige 1+ Arch-Templars (blue cape), Arch-Harakim (red cape) and Seyan'Du (amber) get a recoloured look. Base classes keep their normal look. Any class change sets the look of the new class, so a prestiged Templar who arches again gets the cape automatically.

### Two-handed axes
- New skill **Two-Handed Axe**. Every class that has Two-Handed has it too, with the same maximum and cost, and knows it from the start (at 4, like Two-Handed). Existing characters get it automatically; it keeps following Two-Handed when a character arches.
- Five new weapons, bronze to titanium, with their own double-bit axe sprites. A weapon flagged both axe and two-handed uses the Two-Handed Axe skill.
- **Same stats as two-handed swords, a different special**: two-handed axes have the same weapon value, Agility/Strength requirements and attack speed as two-handed swords. (At first they had 25% more WV, attacked 3 speed steps slower and needed more Strength.) Each has its own special instead, a percentage, so it works the same from Bronze to Titanium:
  - **Two-handed axe - Critical hits:** 1 in 8 of your hits does double damage.
  - **Two-handed sword - Deflect:** while you wield one, 1 in 8 melee hits against you is deflected (no damage); both sides get a message.
  - Only players get the specials (monsters that wield these weapons fight as before). The item tooltip and `#twohand` / `#axe2h` describe them. Tunable: `WP2H_SPECIAL` (data.h).
- Sold next to the two-handed swords: every merchant that sells a two-handed sword tier now also sells the axe of that tier (Karl in Aston, Gertrud, the outpost and lab merchants).

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

### Pentagrams
- **Solve count follows the players doing pentagrams.** It was players online + three random 0-19 (about 28 + everyone online, 54 after a server start), whatever they were doing. Now: for each player who activated a pentagram in the last 10 minutes and is still online (at least 1), 5 + a random 2 or 3 (rolled per round): 7-8 alone, 14-16 for two, 21-24 for three, 35-40 for five. Worked out at every activation, so it follows people joining and leaving; a solve starts a new round with nobody counted. Tunable: `PENTA_PER_PLAYER`, `PENTA_RECENT` in `use_driver.c`.
- **No graves for empty pentagram enemies.** A pentagram enemy whose only belonging is its own weapon leaves no grave; it just vanishes after the death mist, like an NPC with nothing on it. Ones with something else (the Grolm Fighters/Warriors/Knights/Mages carry armor and gold, or a tier drop) still leave one.

### Merchants
- **Merchants are easy to see**: merchants (all 63 of them) had Stealth around 160, so players had to walk right up to them before they showed. Their Stealth is now ignored: they show from as far as any character with no Stealth (light and line of sight still count).
- **Merchant stock**: a merchant keeps in stock his sale list (at most 10 items) plus everything in his template's backpack, up to 40. For every original merchant the two were the same items, so nothing changes for them; it lets a lab merchant carry whole armor tiers.
- **Merchants restock when their shop is opened**, not only after a trade, so stock added to a merchant shows up right away.

### New characters
- All six starting templates (Mercenary, Templar, Harakim, male and female) now start wearing a full set of cloth armor (helmet, armor, sleeves, leggings, boots, cloak; they had only the armor) and with 5 gold (was 2).

### Quests and chain quests
NPCs can now hold real conversations and run quests made in the editor (see [Quest editor](#quest-editor) and [Conversation editor](#conversation-editor)):
- **Talk to NPCs**: an NPC can answer what you say, react to items or money you hand it, greet you differently depending on your quest progress, rank, skills or money, and give rewards: items, experience, money, luck, a skill, a teleport, or a spell cast on you.
- **Quest chains**: each character has 255 quest steps. One quest's end can start the next (bring a potion → then kill Argha the thief → then bring the Spider Queen's head ...).
- **Kill quests**: "kill Argha" or "kill 5 spiders in the Kwai hall" count only while that quest is active, and count for your group members who can see you too. "Spider: 3/5" progress messages.
- **Quest rules on items**: a portal can lead somewhere else depending on your quest step, a door can open only after a quest, a lever can hand out a quest item once per character.
- **`#journal`**: your quests with the text for the step you are at.
- Example (a beggar near the temple): different greetings by rank and Bartering; 150 silver from a low rank gets Bless, Protect and Enhance; a small amount, or money from a high rank, gets a thank-you; "tip" takes 50 silver and gives the tip.

### Chests
- **Editor chests** (MyV2 chests) give a reward drawn by chance each time they are opened. Rewards can mix items, gold, newly made **tier armor** (chosen tiers, level range and metals), **items given only once on the whole server**, and "nothing".
- **Once per player**: a chest can give each player something only once.
- **First-time reward**: the first time each player opens such a chest, they get its special item instead of a draw. New players can each take theirs one after another, even while the chest is open and empty for everyone else. A first opening of a closed chest opens it, so it stays empty for its refill time like a normal opening; after that the player gets the normal draws like everyone else.
- A full backpack keeps the chest closed so you can come back.
- **Chests face north, east, south or west**: new sprites for chests seen from behind (north and east): the back with two hinge straps instead of the lock, and when open the lid has fallen forward toward the viewer, showing the open box.

## Balance changes and fixes

- Hitpoints, endurance and mana can go above 999 (cap 9999).
- Armor and weapon value cap raised from 250 to 9999. Skills and spells keep their original limits.
- Templar and Arch-Templar templates start with **Meditate fixed at 1** (maximum 1, so it can't be raised). Its real value still grows with Intuition and Willpower, which gives Templars a little mana regeneration. One-off patch: `tools/world/templar_meditate.c`.
- Female Templars raised Heal at cost class 7 while male Templars paid 3 (a template data error). Every Templar and Arch-Templar now gets the cheap rate, applied automatically to existing characters.
- A huge sapphire on a silver ring now gives the correct "too powerful" message (a 499 → 489 typo).
- Spell slots are bounds-checked against `MAXITEM`.
- `#recall` (gods) also gives the old temple back to a player taken out of a lab.

---

# Editor

## Overview

The **MyV2 Editor** is a map, NPC, quest and player editor in the browser (`tools/mapedit/mapedit.py`, also in the Windows Server folder). Python standard library only.
- Run it in the Ubuntu server folder: `python3 mapedit.py` (or the full path to it), then open http://localhost:8080.
- Named "MyV2 Editor", with the game's own icon (the client's `res_icon_1.ico`) in the corner and as the browser tab icon.
- **Layout** (after Cody's mock-up): a top bar with search (Ctrl+K: places, NPCs, players, items, or "x y") and the server status ("Server up · n online" / "Server stopped · editing on"); a left rail (Map, Players, NPCs, History, Server, Help); the piece library with tabs and the chosen piece below it; the map with a toolbar, area name labels and a minimap (M = big world map); the right panel with the selected tile, layers to show, flag overlays, the keys, and Save to the game / Discard / Undo last save.
- **Live editing while the server runs**: floors, objects, items, flags, portals, NPCs (place, move, turn, remove) and NPC and item templates all go straight into the running game, and players see them right away. The banner turns green ("Live editing"). There is nothing to save, and Ctrl+Z / Ctrl+Y undo and redo. How it works is under [Server · Data changes](#data-changes). Needs the new server (once: "Update code & restart"); with an older server running, the editor stays view-only and says so.
- With the server stopped, changes are saved to the game files with **Save to the game**.

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
- **Floors** (by how often they are used), **Walls** (drawn into the tile, they block), **Objects** (furniture, decoration, doors, chests…), **Items** (things players can pick up), **NPCs** (see [NPC editor](#npc-editor)), **Flags** (paint a flag on tiles).
- Right-click an item, object or wall in the library to edit its template.

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
- **Edit its template…** and **Quest rules…** (what happens when a player uses it, see [Conversation editor](#conversation-editor)).
- **Chests**: a summary and **Edit chest…** (see [Chest editor](#chest-editor)).
- **NPCs**: turn, move or remove, **Edit NPC…** (see [NPC editor](#npc-editor)).

**Item templates** (right-click a piece in the library, "Edit template…" on the brush card, or "Edit its template…" on an item on a tile): name, reference, description, both looks, value, minimum rank, driver, flags in groups, where it is worn, all modifiers (when worn / when active / needed), armor, weapon, light, damage to attackers, ages, damage, duration, and the driver values. By default the copies lying on the map get the change, but only where they still had the template's old value, so a portal's destination or a sign's own text stays. "Save as a new item…" makes a copy.

**Look of the editor**
- Its own toolbar design (it followed the inspiration mock-up too closely at first): a hotbar of square wood-and-gold slots across the top of the map (Cody preferred it to a column down the side), the key letter in the corner and a gold mark under the active tool; the brush size and undo/redo on the same bar.
- **Icons** chosen by Cody: select (an arrow over a tile), a paint brush, a dashed rectangle with corner handles, fill (four squares with arrows going out), an eraser, an eye dropper with a drop, and move (a hand with four arrows). View switches (larger round 42 px buttons): grid (a 3×3 grid), see through walls (a brick wall, solid at the bottom left and see-through at the top right), light from lamps (a candle in refresh arrows), reload the world (a globe in refresh arrows).
- The live/view-only banner is a strip along the top of the map.
- **Left rail**: the sections are slots with icons (Map: a parchment map; Players: a knight's helmet; NPCs: a hooded figure; History: an hourglass; Server: a castle tower; Help: a book), and a gold mark beside the open one.
- **Category tabs**: a grid of plaques with icons (Builder: a hammer; Floors: a tile; Walls: bricks; Objects: a chest; Items: a sword; NPCs: a hooded figure; Flags: a pennant). The other pages show a single title plaque.

## Player editor

The **Players** page (rail) lists every player character, online ones first, with rank, class and last seen. Clicking one opens it in tabs:
- **Overview:** description; total experience (sets the rank, and changes the unspent experience by the same amount) and unspent experience; money carried; bank (pays the depot rent); luck; the recall point (pick on map); where they stand, or where they come back at the next login; their quest steps.
- **Stats & skills:** attributes, hit points, endurance, mana and the skills their class can learn, each with value and maximum.
- **Worn & backpack:** the 12 worn slots, the item on the mouse and the 40 backpack slots. Each item can be removed (Ctrl+Z undoes it) or its template opened; an empty slot gets **+ Give an item…** (worn slots only offer items that fit there).
- **Depot:** the 62 depot slots, the same way, and the rent paid so far.
- **History:** created, last login, last logout, time played, last address, and the lines about the character in `server.log` (logins, logouts, kills, deaths, other), which can be filtered and clicked to show the place on the map.
- **Account:** download the character's **.moa** file (the client's key file: number, both keys, name, starting race, default display options) for a player who lost theirs; remove a forgotten password; rights and flags (staff, imp, god, creator, no shout, no tell, muted, golden/black list, hidden in #who).
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
- **Equipment & stock:** the 12 worn slots, and the 40 backpack slots, which are a merchant's stock. Each slot has an item picker with search and a link to edit that item.
- **Behaviour:** taking part in fights, attack distance, keyword action, groups (attack all but / help / shout for help / come to help codes), random walk, greeting players, light, picking up trash, self-destruct.
- **Patrol route:** up to 9 stops picked on the map, and the wait at each stop.
- **Talk & quest:** its fixed lines (greeting, keyword and reply, warning, attacking, killed an enemy, dying words, shouting for help, coming to help; %s = the player's name), the dying-words chance, knowledge area and level (the game's built-in answers), and the "bring me an item" quest (wanted item -> teaches a skill + experience, and/or gives an item back).
- **Conversations:** its own lines and quests, see [Conversation editor](#conversation-editor).
- **Advanced:** all 100 driver values, labelled after the original admin interface (`acct.c`).
- **Apply** writes the template, and by default respawns the NPCs of that template with the changes (as the game's own reset does). **Save as a new NPC…** makes a copy with a new name (numbers from 2000 up); it is not placed until you click a tile with the NPC brush, and that first placement uses it directly. Copying an NPC template copies its conversations; a removed editor-made NPC loses them.
- Fix: "Save as a new NPC" kept the original's respawning, though the copy has no spawn spot until it is placed. The game then kept trying to spawn it at 0,0 ("Could not drop char 2000" every 5 minutes in the log), and because of that spawn timer, the first placement made yet another copy instead of using it. A new NPC now respawns only once it is placed, and the first placement uses it (a stale spawn timer of it is removed).

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
- **Facing**: north, east, south or west (where the lock points; north = smaller x, up-left on the map), four pictures marked N E S W in the tile panel and the chest window; clicking one turns that chest.
- **+ Chest** (top of the Builder and Objects tabs): one plain chest for the whole map. The first click makes an item template **Chest** (a copy of Treasure Chest as an editor chest); after that it is a normal brush. Every chest placed with it is its own chest: the rewards belong to its spot, and the chest window opens as soon as one is placed (a single click).

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

**Server console** (`console.c`)
- Commands typed into the terminal the server runs in (read without blocking once per pass of the main loop): `help`, `who` (players online with rank, place, god/imp), `raise <player> <exp>`, `lower <player> <exp>`, `gold <player> <gold> [silver]`, `announce <text>` (to everyone, as "[Server] ..."), `tell <player> <text>`, `kick <player>`, `shutdown` (clean stop, like Ctrl+C). Player names can be shortened like in game; raise/lower/gold also work on players who are offline. Everything is logged with "CONSOLE:".
- Only when the server runs in a terminal (started with an argument, so it doesn't detach); started plain (`./server`) it detaches, and the console switches itself off.
- **Control port**: the server also takes its console commands on 127.0.0.1:5556 (this computer only), one line in, the answer back ending with a "." line. Machine-readable commands for it: `status` (online, ticker, uptime, pid) and `whotab` (one tab-separated line per player online).
- **Live editing**: `edpatch <file>` applies a patch from the editor (see [Data changes](#data-changes)).
- **Quest and chest testing**: `quest <player> [<n> <value>]` shows or sets a player's steps; `talktest <NPC template> <player> <text>` tries a conversation without logging in; `talkreload` reads `npctalk.dat` again; `talkkill <player> <template>`, `talkuse <player> <x> <y>`, `talknear <npc> <player>`, `talkmoney <npc> <player> <silver>`; `chesttest <player> <x> <y>` opens a chest as that player; `chesttest <player> <x> <y> real` with its real open/closed state.

## Data changes

Unchanged except for the version number and the larger view: `merc.dat`, `.moa` character saves, and the 16-byte client messages and compressed tick stream are all as in the original.

**Characters and items**
- New character data slots: `CHD_PRESTIGE` (32) and `CHD_LABTEMPLE` (33), used only by NPCs for lights before. New item flags `IF_NEEDIDENT` (bit 40) and `IF_NEARGLOW` (bit 41); new map flags `MF_NOLIGHT` (bit 10) and `MF_LIT` (bit 12, done in `check_dlight`/`check_dlightm`, so seeing characters and items there and the light the client draws both follow it).
- **Prestige** is `ch.data[CHD_PRESTIGE]`. **Prestige looks**: each character type uses 448 sprite numbers and the 576 after them are unused, so a recoloured copy fits right behind the original: sprite = template sprite + 448 (`god_minor_racechange` sets the look on any class change).
- **Labyrinth temple**: entering a part saves the player's temple in `CHD_LABTEMPLE` (slot 33). A player is in a lab when they have a saved lab temple or their recall point lies in a "Labyrinth" zone (`temple_in_lab`), so custom recall points don't keep lab items or strip them early. Lab items are removed outside the lab by `lab_left_check`. `SEYAN_SHRINES` = 22.
- **Tiered items** (`tier.c`): a tiered item is a plain piece of armor with rolled bonuses, kept in the item's spare `future3[]` fields (`IT_TIER`, `IT_TCAT`, `IT_TLEVEL`, ...; zero in every old item). Thorns and Light use the items' existing gethit damage and light; Thorns is no longer stored on the item (gethit damage adds up): the wearer gets it from the best Thorns piece only (`tier_thorns`, added in `really_update_char`). Regeneration effects: `tier_regen`, called from `do_regenerate`; Warding in `spell_curse` / `spell_stun`. Upgrade and reroll: `tier_upgrade`, `tier_reroll`. Glow: `tier_item_glow`, `tier_tile_glow`; graves: `body_has_items`. Old chest armor numbers: `tier_chest_item`. Soulstone drops: `soul_kill_drop` (tunable `SOULDROP_BASE`, `SOULDROP_PER_RANK`). Spell scroll marks: `item_marks`.
- **Item drivers**: 71 Portal of Time (Lab 10), 72 Lab 11 lecterns, shelves, gates and pages (`use_lab11`), 73 Soul Crucibles (templates 1369-1371, sprites 18220-18228), 74 upgrade stone (template 1372, sprite 18229), 75 MyV2 chest (`talk_chest_open`).
- **Two-handed axe**: skill 36 (`SK_AXE2H`; Agility/Strength/Strength like Two-Handed), added to existing characters in `really_update_char`; a weapon flagged both axe and two-handed uses it (`get_fight_skill`). Templates 1364-1368 (`tools/world/axe2h.txt`, rebalance `tools/world/axe2h_rebalance.spec`; axes already in the game are updated by `tools/world/wfix.c`, which keeps any bonus a piece had on top), sprites 18145-18165. While attacking with one, a character first acted `AXE2H_SLOW` (3) speed steps slower (`ch_act_speed` in `svr_act.c`); the rebalance gave them the swords' speed.

  | Axe (first version) | WV | Needs AGL / STR / Two-Handed Axe | Value | (2H sword WV, AGL / STR) |
  |---|---|---|---|---|
  | Bronze | 15 | 8 / 15 / 1 | 100 | 12, 10 / 12 |
  | Steel | 30 | 16 / 30 / 15 | 500 | 24, 20 / 24 |
  | Golden | 45 | 26 / 48 / 30 | 2500 | 36, 30 / 40 |
  | Crystal | 60 | 36 / 68 / 45 | 12500 | 48, 40 / 60 |
  | Titanium | 90 | 45 / 82 / 60 | 62500 | 72, 50 / 75 |

- **Pentagram enemies** (`is_penta_enemy`: templates 364-385, 538-542, 1094-1097) without belongings leave no grave (`svr_effect.c`). The log line of a pentagram activation shows "(act of needed, n doing pentagrams)".
- **Merchants**: `update_shop` stocks the sale list (`data[0..9]`) plus the template's backpack; restock on `do_look_char`; `do_char_can_see` ignores a merchant's Stealth (`CF_MERCHANT`).
- **Gods' shops**: merchants are character templates `1180-1188`, and 1189 the Scribe (`tools/world/godshop_merchants.txt`).
- **Lab 11 data**: `LAB11_UNDEAD_REGEN`, `LAB11_KEEPER`, `LAB11_ARENA_DEATHS` in `data.h`; `lab_glow_near`.
- **New characters**: starting templates 2, 3, 4, 76, 77, 78 (`tools/world/newplayer_start.spec`); Templar templates 3, 77, 544, 549 (Meditate). The player start templates (2, 3, 4, 13, 76-79, 543-552) and the Blank Template (1) are hidden from the editor's NPC lists.
- **Bank**: a player's bank balance, which pays the depot rent, is `data[13]` (editable in the Player editor).

**MyV2 quests, conversations and chests** (`npctalk.c`, data in `.dat/npctalk.dat`)
- `npctalk.dat` is a text file of blocks: `npc <template>`, `at <x> <y>` (quest rules on an item) and `chest <x> <y>`, with `when say|give|kill|near|money|use` lines (`when near`, `when money <silver>`, `when use` for an item), `if` conditions (`if quest <n> <op> <v>`, `if has <t>`, `if !has <t>`, `if rank <op> <v>`, `if area <text>`, `if skill <nr> <op> <v>`, `if gold <op> <silver>`), actions (`answer`, `tell`, `announce`, `set quest <n> <v>`, `add quest <n> <v>`, `give item|exp|gold|luck <n>`, `teach skill <nr> <v>`, `take item <t>`, `take gold <silver>`, `teleport x y`, `cast bless|protect|enhance|mshield|light|heal <power>`, `keep`, `pass`) and `end`; plus `quest <n> <name>` and `step <n> <value> <text>`.
- Hooks: say in `npc_hear` (`talk.c`), give and money in `npc_give()`, greeting in `driver.c` (`talk_has_near`, `talk_near_due`), kill in `do_char_killed` next to the soulstone drop, use in `use_driver()` before the item's own driver.
- `.dat/quest.dat`: 255 quest steps per character, kept with the character's creation date (a new character in an old slot starts clean). The first version (31 steps, no header) is converted when the server first opens it, keeping the steps.
- **MyV2 chests** (driver 75): `chest <x> <y> ... end` with `refill <seconds>`, `once player`, `first <t>` (first-time reward), and `reward item|unique|gold|nothing ...` / `reward tier <tiers> <metals> <piece> <level from> <level to> <weight>` lines (tier armor made by `tier_chest_reward` in `tier.c`; the older `tier metal piece weight` form still works). Rewards that can't be given any more (a once-only reward already given, an item marked Unique that exists somewhere) are left out of the draw; if nothing is left, it's empty. `.dat/chestlog.dat` keeps who opened which once-per-player chest (`P`), who got which first-time reward (`F x y cn stamp time name`) and which once-only rewards went to whom (`U`); `server.log` names every once-only reward.
- **How the game's own loot items work** (for reference): a chest, flower, mushroom or bookshelf is a map item whose driver gives something when it is used. Driver 1: one fixed item (data 0). Driver 42: one item at random, equal chance, from up to 10 (data 0-9). Driver 59: gold (data 0). Driver 30: needs an item in the hand, which it takes. Driver 53: an item engraved with the player's name. Driver 54: an item, and it alerts the monsters nearby. Once opened it stays open for its duration (Treasure Chests: 1 hour), then anyone can open it again. Items marked Unique (`IF_UNIQUE`: Helm of Shadows, god weapons, the Fire and Ice sets) can't be created while a copy exists anywhere (`god_create_item`).
- **Chest sprites**: south and west are the game's own (220/221, 222/223); north and east are new, 18130/18131 and 18132/18133, PNGs in `Client/GFX` (see [Tools](#tools)). The editor's `itemedit` takes a `sprite` to turn a chest.

**Live editing from the editor**
- The editor reads the game's current files (the server keeps them in shared memory), makes the change on that copy, and sends the difference to the server as a patch file with the console command `edpatch <file>` (control port, `console.c`). Every changed byte range carries the bytes it expects to find. If anything there changed in the meantime (an NPC walked onto the tile, an item was picked up), the server applies nothing and says so; the editor then tells you to try again. Undo works the same way, so it never overwrites something the game changed.
- The server handles the parts that need the game: it takes item lights out and puts them back around changed tiles (including walls and indoors changes, like build mode), resets the players' view caches when sight changes, and does the NPC actions itself (moving through `god_drop_char`, removing with its items, `reset_char` for a changed template). Placed NPCs spawn through the normal respawn timer (`effect.dat`) within a second. An online character's values are worked out again and their client refreshed after a live change (`do_update_char`).

**World patch tools**
- One-off world patches live in `tools/world/`: `lab10_open.c`, `place_items.c` with `lab10_extras.txt` and `lab10_pole_move.txt`, `templar_meditate.c`, `movetowers.py`, `fix_item_status.c`, `tools/world/tier_part2.txt`.
- `tools/world/build_lab.c`: builds an area from a spec file (map tiles, item and character templates, placed items); it also works out each changed template's experience value the way `reset_char` does (a rebuild had left the copied value of the base monster), but only for `copy` and `scale` (before, any `ch` line did, e.g. moving an NPC). `clear` empties an area of items, `movenpc` moves living NPCs to their template's new spot and `killnpc` removes them (Lab 11's monsters are made fresh on each rebuild), so an area can be rebuilt; afterwards `server pop` creates the new NPCs and `server light` the lighting. `place_items.c` and `build_lab.c` give placed items their template number (Lab 10's shrine of Kwai had been placed with 0; fixed in the data). Spec commands added over time: setting an item's driver, `ch <temp> worn <slot> <item temp>`, `ch <temp> gold <silver>`, `it <t> wv`, `atreq`, `skreq`, `dir <temp> <dx>` (resting direction of a template and its living NPCs).
- `tools/world/merchant_stock.c`: sets a merchant template's stock (`merchant_stock <.dat dir> <template> <item templates...>`).

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
- **Spell scroll marks**: `SV_ITEMMARKS` (78: a letter and a number per slot, for the backpack and worn slots or the open shop / grave), sent like `SV_TIERS`.

## Tools

**Server and data**
- **`makegod.c`**: a small offline tool that lists the player characters in `char.dat` and sets or removes god/imp/staff flags. The original game had no god password; gods were set directly in the data files.
- **`tools/claude-sync.sh`** syncs the server between Ubuntu (WSL) and the Windows copy: `send` (Ubuntu → Windows, keeps any newer Windows files), `get` (changed source files and the Makefile Windows → Ubuntu, with a backup, then `make server`), and `get-world` (world `.dat` files, server stopped).
- `tools/world/`: scripts that read the world data directly: a full minimap render, a scan of every portal/teleport/ladder with a landing check, and a zone map. Reports are in `docs/`.
- `tools/design/item_tier_samples.py` prints sample tier rolls (the same rules, for looking at numbers).
- Build: `tier.c`, `godshop.c`, `console.c` and `npctalk.c` are new files, so the Makefile changed.

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
- Hourglass sprites 18121-18128 (`tools/sprites/draw_hourglass.py`); unlit brazier 18129 (`tools/sprites/draw_brazier_unlit.py`).
- **Trees in Hide mode**: stumps 18190-18202 (`tools/sprites/art/stumps/`).
- **Torn page sprites** 18170-18183 (`tools/sprites/art/pages/`), torn from one generated page into four pieces.
- **Two-handed axe sprites** (`tools/sprites/art/axe2h/`): a double-bit axe in bronze (18145), steel (18150), gold (18155), crystal (18160) and titanium (18165), each but titanium followed by four damage states like the two-handed swords (rust, patina, tarnish, clouding, chipped edges). Made from a generated steel axe by `axe2h_build.py`.
- **Emerald special armor** 18210 helmet, 18211 armor (`tools/sprites/art/emerald_special/emerald_special.py`).
- **Soul Crucibles** 18220-18228 (three ranks: pale blue, violet, gold glow; each empty / one stone / full) and the **upgrade stone** 18229, made from one generated picture by `tools/sprites/art/crucible/crucible_build.py`.
- **Gods' shop page arrows** 18230/18231; **Lit** flag icon 18232 and dot 18233 (`tools/sprites/art/lit/`).
- **Chests facing north and east**, 18130/18131 (north, closed/open) and 18132/18133 (east), drawn by `tools/sprites/render_chest.py` from a small 3D model of the game's chest (same size, palette, 2-pixel iron bands, light from the upper left). Seen from behind, each is its own picture: the back with two hinge straps instead of the lock, and when open the lid has fallen forward toward the viewer, showing the open box. (The first versions, from `draw_chest_back.py`, were the south and west chests with the lock painted out, and the open ones looked like copies, so they were redrawn.) Copies in `tools/sprites/art/chest/`.

**Testing notes**
- Two clients at once (`play2.bat`, see [Client](#modernization-changes)).
- Live editing, tested with the real server: a floor, a light-giving object placed (the light around it rose) and erased (the light went back exactly), an NPC placed, moved, turned, its greeting changed and respawned, undo, and a deliberately wrong patch rejected while the server kept running.
- NPC placement, tested on a copy with the real server: a placed Geoffrey spawned with all his items, facing as set; a moved and turned one kept its spot; a removed one did not come back. Template editor: a changed greeting and patrol reached the respawned NPC, and the Janitor walked a new route set in the editor.
- Conversations: a quest intro over two lines that sets step 1, a follow-up line for step 1 and above, non-matching speech ignored, steps shown and reset from the console. Kills counted only once the quest was at the step, 1/3 and 2/3 across two Skeleton templates, the third finishing the step, a template-number match, a wrong area blocking its line, and no counting after the step was done.
- Chests: tier lines with a level range and fitting metals (levels 3-6 in Bronze/Steel/Golden, Golden only at 5-6), with chosen metals at level 16-18, and in the older form (a list of six metals once failed to read, being longer than its buffer; fixed); a Bronze armor of Magic tier made new; gold; once per player refusing the second try; an "once on the server" reward given once and then left out of the draw (the next players got a new Bronze Mage Helm of Heal and another item from the list); first-time rewards for three players in a row, the chest's timer started by the first opening of a closed chest.
