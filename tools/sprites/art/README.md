# New sprites from generated art

Large images made with an AI image generator, shrunk to game sprites with `../shrink_art.py`.
The client loads `gfx/NNNNN.png` before its packed files, so a sprite is just a PNG in the
client's `gfx` folder. These are new numbers; no existing sprite is replaced.

| Sprite | File | Source | Notes |
|---|---|---|---|
| 18140 | `18140_scroll.png` | `scroll_source.png` | Open parchment scroll lying on the ground (isometric). The generated handwriting is too fine to survive at 32 px, so a few short ink lines were drawn back onto the page at final size. |
| 18141 | `18141_book.png` | `book_source.png` | Weathered open book, seen from the front (good as a backpack icon). |

Free numbers after these: 18142-18144, then 18166 and up (18130-18133 are left empty: the brazier's fire
animation would look for them if its cold sprite were ever given status 16 again).

Prompt tips that worked: ask for a "pre-rendered 3D isometric game asset, late-1990s CGI"
like Diablo / Ultima Online props, bold chunky details that stay readable at a very small
size, one light from the upper left, no shadow, the object filling the image, and a flat
plain background; put "pixel art, 8-bit, retro sprite, cartoon, outlines" in the negative prompt.

## Draft: two-handed axes (`axe2h_painted/`)

The generator returned a black silhouette of a double-bit axe (`axe_silhouette_source.png`).
`axe_paint.py` uses it as a stencil and paints the five metals of the two-handed swords onto
it (colours taken from sprites 1505, 1465, 1490, 1485 and 1655): bronze, steel, gold, crystal,
titanium. Kept as a fallback while a rendered version is tried; not in the client yet.
(`axe_paint.py` expects `mask.npy`, the silhouette's largest dark shape as a boolean array.)

## Two-handed axes (`axe2h/`)

A double-bit two-handed axe in the five metals of the two-handed swords, with damage states.
Source: the generated steel axe (`axe2h_source_generated.png`) with its back blade enlarged
(`axe2h_source_backblade.png`). `axe2h_build.py` recolours the metal of the head with each
sword's colours, keeps the wood haft and leather wrap, and gives the end cap the sword's
crossguard colour. Like the swords, each metal has its perfect sprite and four worse ones
right after it (the server adds 1 to an item's sprite with every damage state): the metal
rusts red (steel), grows green patina (bronze), tarnishes olive (gold) or clouds over and
darkens (crystal), loses its shine, gets chipped edges from the second state on, and the
haft gets grimy. Titanium items do not age, so titanium has only its perfect sprite.

| Metal | Perfect | Worn 1-4 |
|---|---|---|
| Bronze | 18145 | 18146-18149 |
| Steel | 18150 | 18151-18154 |
| Gold | 18155 | 18156-18159 |
| Crystal | 18160 | 18161-18164 |
| Titanium | 18165 | - |

The earlier drafts (`axe2h_painted/`, painted on a silhouette) are kept for reference.
