#!/usr/bin/env python3
"""New doors for MyV2, on the game's own door shapes (Unlocked Door I 1216 / 1217 and II 1212 / 1213: a slab across
the tile, closed, and swung open to the side; the shading of the originals is kept), re-textured per style.
Each style has 4 sprites from 36500 + 10*style: +0 closed I, +1 open I, +2 closed II, +3 open II
(I and II: the two facings, as the game's "Door I" / "Door II" templates).

    world_doors.py <client folder> [--out <folder>] [--sheet <png>] [--scene <png>]
"""
import json, math, os, random, sys
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import world_ground as WG
from world_walls import Noise, mix

FIRST = 36500
SHAPES = [1216, 1217, 1212, 1213]       # closed I, open I, closed II, open II


def lum(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def is_cap(c):
    return max(c) - min(c) < 14 and 50 < c[0] < 96


def analyse(im):
    """per pixel: (part, u, v, shade): part 'cap' / 'face' / 'edge'; u across the face, v down from its top edge;
    shade = the original's brightness relative to its big face (keeps the game's lighting)"""
    px = im.load()
    # the slab: a grey cap on top, its big lit face, and a thin side in shade. Which columns are side and which face
    # comes from the brightness under the cap (the side is clearly darker), not from the outline.
    cols = {}
    for x in range(32):
        body = [lum(px[x, y]) for y in range(64) if px[x, y][3] and not is_cap(px[x, y][:3])]
        if body:
            cols[x] = sum(body) / len(body)
    if not cols:
        return {}, 1
    lo, hi = min(cols.values()), max(cols.values())
    cut = (lo + hi) / 2 if hi > lo * 1.18 else -1
    bright = sorted(x for x, m in cols.items() if m > cut)
    dark = sorted(x for x in cols if x not in bright)
    # the wider part is the door's face (an open door shows its face in shade), the narrow one its edge
    face, side = (bright, dark) if len(bright) >= len(dark) else (dark, bright)
    gm = lambda g: sum(cols[x] for x in g) / len(g) if g else 0
    ref = max(gm(face), gm(side))
    face_shade = gm(face) / ref
    edge_shade = gm(side) / ref if side else 0.8
    out = {}
    for x in range(32):
        top = None          # the first row below the cap in this column: v counts from there
        for y in range(64):
            c = px[x, y]
            if not c[3]:
                continue
            if is_cap(c[:3]):
                out[x, y] = ('cap', 0, 0, 1)
                continue
            if top is None:
                top = y
            if x in face:
                out[x, y] = ('face', x - face[0], y - top, face_shade)
            else:
                out[x, y] = ('edge', 0, y - top, edge_shade)
    return out, len(face)


# ---------------------------------------------------------------- styles: (u, v, width, part, noise) -> rgb
def wood(u, v, w, n, base, bands=((9, 11), (40, 42)), iron=(52, 52, 56), studs=False, handle=True):
    seam = (int(u) % 4) == 3
    c = tuple(x * (0.88 + 0.22 * n.v(u * 0.9, v * 0.25)) for x in base)
    if seam:
        c = tuple(x * 0.62 for x in base)
    for a, b in bands:
        if a <= v <= b:
            c = iron
            if studs and int(u) % 3 == 1 and v == a:
                c = (120, 120, 126)
    if handle and abs(u - (w - 4)) < 1 and 24 <= v <= 26:
        c = (40, 40, 42)
    return c


def s_oak(u, v, w, part, n):
    return wood(u, v, w, n, (170, 118, 70))


def s_darkwood(u, v, w, part, n):
    return wood(u, v, w, n, (96, 62, 40), studs=True)


def s_dungeon(u, v, w, part, n):
    c = wood(u, v, w, n, (84, 60, 44), bands=((6, 9), (23, 26), (40, 43)), iron=(46, 46, 50), studs=True)
    if (u < 1.5 or u > w - 2) and part == 'face':
        c = (46, 46, 50)          # iron frame on both sides
    return c


def s_iron(u, v, w, part, n):
    base = (104, 106, 112)
    c = tuple(x * (0.9 + 0.16 * n.f(u * 0.4, v * 0.2)) for x in base)
    if v in (3, 26, 48) or u < 1 or u > w - 2:
        c = (70, 72, 78)
    if (v in (5, 24, 28, 46)) and int(u) % 4 == 2:
        c = (150, 152, 160)        # rivets
    return c


def s_temple(u, v, w, part, n):
    base = (230, 226, 212); gold = (204, 166, 70)
    c = tuple(x * (0.94 + 0.08 * n.f(u * 0.3, v * 0.3)) for x in base)
    if u < 1.5 or u > w - 2.5 or v < 2 or v in (24, 25) or v > 47:
        c = gold                   # gold frame and middle rail
    elif 6 <= v <= 20 and 4 <= u <= w - 5 and (u in (4, w - 5) or v in (6, 20)):
        c = mix(base, gold, 0.6)   # a panel outline
    return c


def s_sandstone(u, v, w, part, n):
    base = (196, 160, 112)
    c = tuple(x * (0.88 + 0.2 * n.f(u * 0.5, v * 0.3)) for x in base)
    if u < 1.5 or u > w - 2.5 or v < 2 or v > 47:
        c = tuple(x * 0.72 for x in base)
    if 10 <= v <= 38 and abs(u - w / 2) + abs((v - 24) / 2.2) < 4.5 and abs(u - w / 2) + abs((v - 24) / 2.2) > 3.2:
        c = tuple(x * 0.6 for x in base)       # a carved diamond
    return c


def s_gate(u, v, w, part, n):
    """iron bars: see-through between them"""
    if part == 'face' and int(u) % 3 != 1 and v not in (3, 4, 24, 25, 46, 47):
        return None
    return (64, 66, 72) if int(u) % 3 == 1 else (80, 82, 88)


def s_curtain(u, v, w, part, n):
    base = (150, 34, 44)
    fold = 0.78 + 0.3 * abs(math.sin(u * 1.1))
    c = tuple(x * fold * (0.95 + 0.08 * n.v(u, v * 0.3)) for x in base)
    if v < 3:
        c = (196, 156, 72)         # the rod / gold hem
    return c


STYLES = [('Oak Door', s_oak), ('Dark Wood Door', s_darkwood), ('Iron-Bound Door', s_dungeon), ('Iron Door', s_iron),
          ('Temple Door', s_temple), ('Sandstone Door', s_sandstone), ('Iron Gate', s_gate), ('Curtain', s_curtain)]


def make(shape, geo, w, func, n, capcol=(70, 66, 62)):
    im = Image.new('RGBA', (32, 64), (0, 0, 0, 0)); px = im.load()
    for (x, y), (part, u, v, sh) in geo.items():
        if part == 'cap':
            c = capcol
        else:
            c = func(u, v, w, part, n)
            if c is None:
                continue
            c = tuple(a * sh for a in c)
        px[x, y] = tuple(max(0, min(255, int(a))) for a in c[:3]) + (255,)
    return im


SEYAN = 36580     # the Seyan'Du Door's missing other facing: closed 36580, open 36581


def seyan_other(S):
    """the game made its two door facings as mirror images (Door I 1216 is Door II 1212 mirrored), and has the Seyan'Du
    Door (915 closed, 916 open) only as a Door II: mirrored, it fits walls running the other way"""
    from PIL import ImageOps
    return {SEYAN: ImageOps.mirror(S.get(915).convert('RGBA')), SEYAN + 1: ImageOps.mirror(S.get(916).convert('RGBA'))}


def build(client):
    S = WG.Sprites(client)
    shapes = [analyse(S.get(n).convert('RGBA')) for n in SHAPES]
    out, names = {}, []
    for k, (name, func) in enumerate(STYLES):
        first = FIRST + k * 10
        for j, (geo, w) in enumerate(shapes):
            out[first + j] = make(SHAPES[j], geo, w, func, Noise(first + 3))
        names.append([first, name, [first + j for j in range(4)]])
    out.update(seyan_other(S))
    return out, names


def scene(doors, names, client, path):
    """the new red brick walls with each door in them: Door I in walls along map y, Door II in walls along map x;
    closed in one wall, open in the next"""
    S = WG.Sprites(client); floor = [S.get(n) for n in WG.GRASS]
    wall = [S.get(36024 + k) for k in range(4)]
    N = 22; img = Image.new('RGBA', (32 * N + 64, 16 * N + 140), (0, 0, 0, 255)); r = random.Random(2)
    place = {}
    for wx, j in ((2, 0), (5, 1)):            # walls along y at x = 2 (closed I) and x = 5 (open I)
        for y in range(1, 18):
            place[wx, y] = ('w', 0)
        for i, (first, name, vs) in enumerate(names):
            place[wx, 1 + i * 2 + 1] = ('d', vs[j])
    for wy, j in ((5, 2), (2, 3)):            # walls along x at y = 5 (closed II) and y = 2 (open II), further down
        for x in range(9, 21):
            place[x, wy] = ('w', 0)
        for i, (first, name, vs) in enumerate(names[:6]):
            place[10 + i * 2, wy] = ('d', vs[j])
    order = sorted([(x, y) for x in range(N) for y in range(N)], key=lambda c: (c[0] - c[1], c[0] + c[1]))
    for x, y in order:
        sx = 16 * (x + y) + 16; sy = 8 * (x - y) + 8 * N + 90
        img.alpha_composite(r.choice(floor), (sx - 16, sy - 24))
    for x, y in order:
        k = place.get((x, y))
        if k:
            sx = 16 * (x + y) + 16; sy = 8 * (x - y) + 8 * N + 90
            img.alpha_composite(r.choice(wall) if k[0] == 'w' else doors[k[1]], (sx - 16, sy - 56))
    img.save(path)


if __name__ == '__main__':
    client = sys.argv[1]
    doors, names = build(client)
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else WG.gfx_dir(client)
    os.makedirs(out, exist_ok=True)
    for nr, im in doors.items():
        im.save(os.path.join(out, '%05d.png' % nr))
    with open(os.path.join(HERE, 'world_doors.json'), 'w') as f:
        json.dump(names, f)
    print('%d door sprites written: %s' % (len(doors), ', '.join('%s %d-%d' % (n, f, f + 3) for f, n, v in names)))
    if '--sheet' in sys.argv:
        sh = Image.new('RGBA', (4 * 104 + 190, len(names) * 200 + 30), (30, 30, 30, 255)); d = ImageDraw.Draw(sh)
        for j, lab in enumerate(('closed I', 'open I', 'closed II', 'open II')):
            d.text((190 + j * 104, 4), lab, fill=(200, 200, 200, 255))
        for i, (first, name, vs) in enumerate(names):
            d.text((8, 20 + i * 200 + 90), name, fill=(255, 220, 120, 255))
            for j in range(4):
                sh.alpha_composite(doors[first + j].resize((96, 192), Image.NEAREST), (190 + j * 104, 20 + i * 200 + 5))
        sh.save(sys.argv[sys.argv.index('--sheet') + 1])
    if '--scene' in sys.argv:
        scene(doors, names, client, sys.argv[sys.argv.index('--scene') + 1])
    if '--compare' in sys.argv:       # next to the game's own doors, each in a grey brick wall
        S = WG.Sprites(client)
        rows = [('Game: Unlocked Door', [S.get(n) for n in (1216, 1217, 1212, 1213)]),
                ("Game: Seyan'Du Door (I: new)", [doors[SEYAN], doors[SEYAN + 1], S.get(915), S.get(916)])]
        rows += [(nm, [doors[f + j] for j in range(4)]) for f, nm, v in names]
        wall = S.get(1214).convert('RGBA'); fl = S.get(551).convert('RGBA')

        def cell(door, facing):
            im = Image.new('RGBA', (112, 96), (30, 30, 30, 255)); d = (16, -8) if facing == 0 else (16, 8)
            base = (24, 64) if facing == 0 else (24, 48)
            pos = [(base[0] + i * d[0], base[1] + i * d[1]) for i in range(3)]
            for (x, y) in pos:
                im.alpha_composite(fl, (x - 16, y - 24))
            for i in sorted(range(3), key=lambda i: (pos[i][1], pos[i][0])):
                x, y = pos[i]; im.alpha_composite(door.convert('RGBA') if i == 1 else wall, (x - 16, y - 56))
            return im.resize((224, 192), Image.NEAREST)
        sh = Image.new('RGBA', (150 + 4 * 232, len(rows) * 202 + 30), (30, 30, 30, 255)); dr = ImageDraw.Draw(sh)
        for j, lab in enumerate(('closed I', 'open I', 'closed II', 'open II')):
            dr.text((150 + j * 232 + 60, 6), lab, fill=(200, 200, 200, 255))
        for i, (nm, ds) in enumerate(rows):
            y = 26 + i * 202; dr.text((6, y + 90), nm, fill=(140, 200, 255, 255) if nm.startswith('Game') else (255, 220, 120, 255))
            for j, dd in enumerate(ds):
                sh.alpha_composite(cell(dd, 0 if j < 2 else 1), (150 + j * 232, y))
        sh.save(sys.argv[sys.argv.index('--compare') + 1])
