#!/usr/bin/env python3
"""A new monster look from an existing animated one (Nov 14): every frame of a character sprite set (base+0..1023)
recoloured, keeping its shading - each pixel's brightness picks a colour on a ramp, so all 8 directions and every
walk / attack / death frame stay as the original drew them. The new set gets its own base (an NPC's sprite).

    recolor_creature.py <client folder> <source base> <new base> <ramp name> [--out <folder>] [--scale 1.4]

--scale (Nov 17, the Brass Colossus): every frame drawn bigger. The client draws a sprite in 32-px blocks, centred and
standing on its bottom edge (dd.c copysprite), so a frame grows to the next multiple of 32 and the feet stay on the
same line as the original's (the bottom margin is kept, not scaled).

Ramps (dark, mid, light): sandstone, slate, ... (RAMPS below). Made so far (CHANGES.md "Old Quarry"):
    41000 Quarry Golem   (the Golem, 17360, in sandstone)
    42100 Deep Grolm     (the Grolm, 12240, in cave slate)
    50000 Drowned Sailor (the Undead, 19408, drowned); 50500 Bog-man (the Grolm, 12240, bog); 51000 Sea Golem (the Golem, 17360, seagolem)
    52000 Barrow Wight   (the Undead Lord, 19408, wight)
    53000 the Broodmother (the Lizard, 13264, brood); 54000 Lizard Hatchling (the Lizard, 13264, hatchling)
    55000 Iron Golem (the Golem, 17360, iron); 56000 the Forgemaster (17360, forgemaster); 57000 the Brass Colossus (17360, brass, --scale 1.4: 96x96 frames)
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
RAMPS = {
    'sandstone': ((40, 30, 18), (128, 102, 68), (204, 180, 134)),
    'slate': ((18, 22, 30), (70, 82, 98), (150, 164, 182)),
    'drowned': ((10, 28, 30), (54, 112, 104), (160, 214, 196)),      # Drowned Sailor: the Undead, sea-green
    'bog': ((26, 20, 10), (92, 74, 40), (164, 150, 96)),              # Bog-man: the Grolm, mud brown
    'seagolem': ((8, 24, 40), (40, 104, 128), (150, 210, 220)),       # Sea Golem (Fenwatch): the Golem, blue-green
    'wight': ((30, 34, 40), (120, 130, 140), (214, 220, 226)),       # Barrow Wight (Barrow Hills): the Lord, grave-pale
    'wightpale': ((52, 60, 70), (168, 180, 192), (236, 242, 246)),  # Barrow Wight, the paler choice
    'brood': ((22, 4, 6), (110, 22, 20), (200, 84, 60)),             # the Broodmother (Lizard Hatcheries): the Lizard, dark red
    'hatchling': ((40, 46, 14), (150, 164, 70), (226, 232, 160)),     # Lizard Hatchling: the Lizard, pale yellow-green
    'iron': ((14, 16, 20), (72, 76, 86), (170, 176, 188)),            # Iron Golem (Golem Foundry): the Golem, dark forged iron
    'forgemaster': ((24, 10, 6), (96, 60, 46), (255, 168, 72)),      # the Iron Golem Forgemaster: iron glowing hot at the edges
    'brass': ((44, 26, 6), (164, 116, 40), (252, 222, 128)),         # the Brass Colossus: polished brass
    'seahag': ((6, 26, 30), (46, 112, 104), (186, 226, 204)),        # the Sea Hag (Drowned Village): the Mage (6096), sea-green and pale
    'seahag2': ((14, 22, 34), (70, 96, 112), (196, 210, 200)),       # the Sea Hag, the greyer, drowned choice
}


def ramp(r, t):
    d, m, l = r
    if t < 0.5: k = t / 0.5; return tuple(int(d[i] + (m[i] - d[i]) * k) for i in range(3))
    k = (t - 0.5) / 0.5; return tuple(int(m[i] + (l[i] - m[i]) * k) for i in range(3))


SCALE = 1.0

def enlarge(im, s):
    from PIL import Image
    w, h = im.size; bb = im.getbbox()
    if not bb: return Image.new('RGBA', (w, h), (0, 0, 0, 0))
    m = h - bb[3]                                          # the margin under the feet
    W, H = -(-int(w * s) // 32) * 32, -(-int(h * s) // 32) * 32
    big = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    a = big.split()[3].point(lambda v: 255 if v >= 110 else 0); big.putalpha(a)
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ox = round(W / 2 - w * s / 2); oy = round((H - m) - s * (h - m))
    out.alpha_composite(big, (ox, oy)); return out

def main():
    global SCALE
    if '--scale' in sys.argv: SCALE = float(sys.argv[sys.argv.index('--scale') + 1])
    client, src, dst, name = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(client, 'GFX')
    sys.argv = [sys.argv[0], client, '/tmp']
    exec(open(os.path.join(HERE, '..', 'world', 'spritesheets.py')).read().split('ids=sorted')[0], globals())
    R = RAMPS[name]; os.makedirs(out, exist_ok=True)
    frames = {k: load(src + k) for k in range(1024)}
    frames = {k: im.convert('RGBA') for k, im in frames.items() if im}
    lums = []
    for im in list(frames.values())[:60]:
        lums += [max(p[:3]) for p in (im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()) if p[3] and not (p[0] > 240 and p[1] < 16 and p[2] > 240)]
    lums.sort(); lo, hi = lums[len(lums) // 50], lums[-len(lums) // 50]
    n = 0
    for k, im in frames.items():
        px = im.load()
        for y in range(im.height):
            for x in range(im.width):
                c = px[x, y]
                if not c[3]: continue
                if c[0] > 240 and c[1] < 16 and c[2] > 240: px[x, y] = (0, 0, 0, 0); continue
                t = (max(c[:3]) - lo) / max(1, hi - lo)
                px[x, y] = ramp(R, max(0, min(1, t))) + (255,)
        if SCALE != 1.0: im = enlarge(im, SCALE)
        p = os.path.join(out, '%05d.png' % (dst + k))
        im.save(p); n += 1
    print('%d frames: %d -> %d (%s)' % (n, src, dst, name))


if __name__ == '__main__':
    main()
