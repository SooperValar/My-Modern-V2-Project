#!/usr/bin/env python3
"""Window versions of the new walls (Nov 14, Cody: "all the new walls should have a window variant, so houses can
have a window"), in the game's own window style: the wall block with an open slit through it (the game's 1218
Red / Grey Brick window: a top slab over a low block, you see through the gap; placed with "blocks walking" only,
not sight). The game's own shapes are used (1218 for the window, 1219 for its cut-down hidden-walls form), filled
with each material of world_walls.py, clean and grain. Numbered from 36600:

    36600 + 4*k   the window wall          36601 + 4*k   its hidden form (sprite+1)
    36602 + 4*k   the same again (kept so the numbers of the first draft stay filled), 36603 its hidden form
    k = 0..15: the materials of world_walls.json in order (Sandstone, Sandstone grain, White Temple, ...)

Writes the PNGs and world_windows.json (the editor's WORLD_WINDOWS: [sprite, name, blocks 1 = walking only]).

    world_windows.py <client folder> [--out <folder>] [--sheet <png>] [--scene <png>]
"""
import json, os, random, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import world_walls as WW, world_ground as WG

FIRST = 36600
U0, U1, V0, V1 = 4, 11, 11, 25            # the window on the face (u across 0..15, v down 0..44)


def geometry_cut(block):
    """the game's cut wall (1201): cap on top of a low slab; v counted from the slab's top edge"""
    px = block.load(); bb = block.getbbox(); top = bb[1]
    cap = px[16, top + 8][:3]; g = {}
    for y in range(64):
        for x in range(32):
            if px[x, y][3] == 0: continue
            if y <= top + 17 and all(abs(a - b) < 12 for a, b in zip(px[x, y][:3], cap)): g[x, y] = ('cap', 0, 0)
            elif x < 16: g[x, y] = ('L', x, y - top - 8 - x / 2.0 + 30)
            else: g[x, y] = ('R', x - 16, y - top - 16 + (x - 16) / 2.0 + 30)
    return g, cap


def geometry_any(block, capcol):
    """like world_walls.geometry, but the cap colour counts as cap anywhere (the window's slab and its sill)"""
    px = block.load(); g = {}
    for y in range(64):
        for x in range(32):
            if px[x, y][3] == 0: continue
            if all(abs(a - b) < 14 for a, b in zip(px[x, y][:3], capcol)): g[x, y] = ('cap', 0, 0)
            elif x < 16: g[x, y] = ('L', x, y - 12 - x / 2.0)
            else: g[x, y] = ('R', x - 16, y - 20 + (x - 16) / 2.0)
    return g


def build(client):
    S = WG.Sprites(client)
    geo0, capcol = WW.geometry(S.get(WW.SHAPE))
    wgeo = geometry_any(S.get(1218), capcol)
    cgeo, ccap = geometry_cut(S.get(1219))
    out, names, k = {}, [], 0
    for m, (name, func, captint) in enumerate(WW.MATERIALS):
        first = WW.FIRST + m * 10
        for grain, suffix in ((0, ''), (WW.GRAIN, ' (grain)')):
            n = FIRST + 4 * k
            win = WW.make_wall(wgeo, capcol, func, captint, WW.Noise(first * 7), WW.variant_rng(name, 0), grain=grain)
            cut = WW.make_wall(cgeo, ccap, func, captint, WW.Noise(first * 7), WW.variant_rng(name, 0), grain=grain)
            out[n], out[n + 1], out[n + 2], out[n + 3] = win, cut, win, cut
            names.append([n, '%s%s, window' % (name, suffix), 1])
            k += 1
    return out, names


def scene(out, names, client, path):
    """a little house of each of a few materials: windows in both visible walls"""
    S = WG.Sprites(client); grass = [S.get(n) for n in WG.GRASS]; floor = S.get(133)
    walls = json.load(open(os.path.join(HERE, 'world_walls.json')))
    N = 22; r = random.Random(3); Wm = {}
    picks = [0, 3, 6, 12, 14, 9]       # material kinds (index k) to show
    for i, k in enumerate(picks):
        bx = 2 + (i % 3) * 7; by = 2 + (i // 3) * 9
        wfirst = walls[k][0]
        for x in range(bx, bx + 5):
            for y in range(by, by + 6):
                edge = x in (bx, bx + 4) or y in (by, by + 5)
                if not edge: Wm[x, y] = ('f', 0); continue
                if x == bx + 4 and y in (by + 2, by + 3): Wm[x, y] = ('s', FIRST + 4 * k)    # east-west wall: right face
                elif y == by and x == bx + 2: Wm[x, y] = ('s', FIRST + 4 * k)                    # north-south wall: left face
                else: Wm[x, y] = ('s', wfirst + r.randrange(4))
    img = Image.new('RGBA', (32 * N + 64, 16 * N + 120), (0, 0, 0, 255))
    order = sorted([(x, y) for x in range(N) for y in range(N)], key=lambda c: (c[0] - c[1], c[0] + c[1]))
    for x, y in order:
        sx = 16 * (x + y) + 16; sy = 8 * (x - y) + 8 * N + 70
        img.alpha_composite(floor if Wm.get((x, y), ('g',))[0] == 'f' else r.choice(grass), (sx - 16, sy - 24))
    allspr = dict(out)
    for x, y in order:
        k = Wm.get((x, y))
        if k and k[0] == 's':
            sx = 16 * (x + y) + 16; sy = 8 * (x - y) + 8 * N + 70
            im = allspr.get(k[1]) or S.get(k[1])
            img.alpha_composite(im, (sx - 16, sy - 56))
    img = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
    img.convert('RGB').save(path)


if __name__ == '__main__':
    client = sys.argv[1]
    out, names = build(client)
    dst = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else WG.gfx_dir(client)
    os.makedirs(dst, exist_ok=True)
    for nr, im in out.items(): im.save(os.path.join(dst, '%05d.png' % nr))
    json.dump(names, open(os.path.join(HERE, 'world_windows.json'), 'w'))
    print('%d sprites %d-%d' % (len(out), min(out), max(out)))
    if '--sheet' in sys.argv:
        sh = Image.new('RGBA', (8 * 72, 4 * 140), (30, 30, 30, 255))
        for i, n in enumerate(sorted(out)[:32]):
            sh.alpha_composite(out[n].resize((64, 128), Image.NEAREST), ((i % 8) * 72 + 4, (i // 8) * 140 + 6))
        sh.save(sys.argv[sys.argv.index('--sheet') + 1])
    if '--scene' in sys.argv:
        scene(out, names, client, sys.argv[sys.argv.index('--scene') + 1])
