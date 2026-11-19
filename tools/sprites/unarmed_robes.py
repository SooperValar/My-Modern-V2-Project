#!/usr/bin/env python3
"""Bare-handed robed figures from a human character sprite set (Nov 19, the Monastery; Cody: no full-figure recolours,
"are you able to remove the sword from a merc sprite?"). For every frame of a set (base+0..1023):
  1. the weapon goes: its pixels are cool steel greys and the Mercenary is drawn in warm browns and skin, so every pixel
     with blue >= red - 6 (and not near-black) is taken out; holes it leaves inside the body are filled from the
     neighbours; the hand is left as a fist (attacks become punches);
  2. the clothes (everything but skin) are recoloured along a ramp, the skin kept;
  3. the edges cleaned (Cody: "the edges look really messy", "the lighter one looks outlined"): dark pixels inside the
     robe take its shadow, not black; the robe's outline next to skin becomes a skin shadow; on pale robes the outline is
     lighter (edge floor); the arms' and legs' own dark brown outline is lightened toward a mid skin tone; lone pixels
     sticking out are dropped.

    unarmed_robes.py <client folder> <source base> <new base> <look> [--out <folder>] [--preview <png>]

Looks (LOOKS below). Made (Monastery of the Still Hand): from the Mercenary (5072):
    64000 Fallen Monk (saffron), 64500 Fallen Mystic (grey), 65000 Master Kesh (kesh), 45000 the Fallen Abbot (abbot),
    45500 Brother Anselm (anselm)
(sprite numbers must stay below 65,536: 65500 + 447 would not, so the Abbot is at 45000)."""
import os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
# look: (ramp stops, edge floor, colour of the robe's outline next to skin)
LOOKS = {
    'saffron': ([(0, (40, 16, 4)), (0.5, (176, 84, 18)), (1, (250, 176, 60))], 0.1, (86, 56, 44)),
    'grey':    ([(0, (20, 20, 22)), (0.5, (96, 94, 90)), (1, (196, 192, 184))], 0.15, (96, 66, 54)),
    'kesh':    ([(0, (8, 8, 10)), (0.6, (34, 32, 38)), (0.85, (150, 24, 20)), (1, (220, 60, 40))], 0.0, (86, 56, 44)),
    'anselm':  ([(0, (34, 24, 14)), (0.5, (120, 92, 60)), (1, (210, 186, 146))], 0.12, (86, 56, 44)),     # Brother Anselm: plain undyed wool, not fallen
    'abbot':   ([(0, (70, 62, 48)), (0.5, (200, 192, 172)), (0.9, (244, 240, 228)), (1, (255, 210, 110))], 0.4, (176, 124, 104)),
}
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def ramp(stops, t):
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if t <= b:
            f = (t - a) / (b - a) if b > a else 0
            return tuple(int(ca[i] + (cb[i] - ca[i]) * f) for i in range(3))
    return stops[-1][1]


def steel(p):
    r, g, b, a = p
    return a and b >= r - 6 and max(r, g, b) >= 28


def skin(p):
    r, g, b, a = p
    return r > 50 and g >= 0.6 * r and b >= 0.45 * r


def strip(im):
    im = im.convert('RGBA'); px = im.load(); W, H = im.size
    kill = [(x, y) for y in range(H) for x in range(W) if steel(px[x, y])]
    for x, y in kill: px[x, y] = (0, 0, 0, 0)
    for _ in range(3):
        fill = []
        for x, y in kill:
            if px[x, y][3]: continue
            nb = [px[x + dx, y + dy] for dx, dy in N4 if 0 <= x + dx < W and 0 <= y + dy < H and px[x + dx, y + dy][3]]
            if len(nb) >= 3: fill.append((x, y, tuple(sum(c[i] for c in nb) // len(nb) for i in range(4))))
        for x, y, c in fill: px[x, y] = c
    for y in range(H):
        for x in range(W):
            if px[x, y][3] and sum(px[x, y][:3]) < 60:
                if sum(1 for dx, dy in N4 if 0 <= x + dx < W and 0 <= y + dy < H and px[x + dx, y + dy][3]) <= 1: px[x, y] = (0, 0, 0, 0)
    return im


def robe(im, look):
    stops, edge_floor, skin_edge = LOOKS[look]
    im = im.copy(); px = im.load(); W, H = im.size
    op = lambda x, y: 0 <= x < W and 0 <= y < H and px[x, y][3] > 0
    src = [[px[x, y] for x in range(W)] for y in range(H)]
    for y in range(H):
        for x in range(W):
            p = src[y][x]
            if not p[3] or skin(p): continue
            t = min(1, (0.3 * p[0] + 0.59 * p[1] + 0.11 * p[2]) / 150)
            inner = all(op(x + dx, y + dy) for dx, dy in N4)
            nskin = sum(1 for dx, dy in N4 if op(x + dx, y + dy) and skin(src[y + dy][x + dx]))
            if inner and t < 0.3: t = 0.3
            if not inner and t < 0.2 and nskin: px[x, y] = skin_edge + (p[3],); continue
            if not inner: t = max(t, edge_floor)
            px[x, y] = ramp(stops, t) + (p[3],)
    for y in range(H):                                       # the arms' and legs' own dark outline, lightened
        for x in range(W):
            p = src[y][x]
            if p[3] and skin(p) and sum(p[:3]) <= 330 and not all(op(x + dx, y + dy) for dx, dy in N4):
                px[x, y] = tuple(int(p[i] + ((196, 142, 120)[i] - p[i]) * 0.55) for i in range(3)) + (p[3],)
    for _ in range(2):
        for y in range(H):
            for x in range(W):
                if px[x, y][3] and sum(1 for dx, dy in N4 if op(x + dx, y + dy)) <= 1: px[x, y] = (0, 0, 0, 0)
    return im


def main():
    a = sys.argv[1:]; client, src_base, new_base, look = a[0], int(a[1]), int(a[2]), a[3]
    assert look in LOOKS, sorted(LOOKS); assert new_base + 1023 < 65536 or new_base + 447 < 65536
    sys.argv = [sys.argv[0], client, '/tmp']
    exec(open(os.path.join(HERE, '..', 'world', 'spritesheets.py')).read().split('ids=sorted')[0], globals())
    gdir = os.path.join(client, 'GFX') if os.path.isdir(os.path.join(client, 'GFX')) else os.path.join(client, 'gfx')
    out = a[a.index('--out') + 1] if '--out' in a else gdir
    os.makedirs(out, exist_ok=True); n = 0
    for k in range(1024):
        im = load(src_base + k)                                  # noqa: F821 (from spritesheets.py)
        if im is None: continue
        assert new_base + k < 65536, 'sprite numbers stop at 65535'
        robe(strip(im), look).save(os.path.join(out, '%d.png' % (new_base + k))); n += 1
    print('%d frames: %d -> %d (%s, no weapon)' % (n, src_base, new_base, look))
    if '--preview' in a:
        frames = [8, 0, 16, 24, 72, 200, 216, 248]
        sh = Image.new('RGBA', (len(frames) * 60, 90), (205, 212, 220, 255))
        for i, f in enumerate(frames):
            p = os.path.join(out, '%d.png' % (new_base + f))
            if os.path.exists(p):
                im = Image.open(p).convert('RGBA'); sh.alpha_composite(im, (i * 60 + 30 - im.width // 2, 88 - im.height))
        sh.resize((sh.width * 4, sh.height * 4), Image.NEAREST).save(a[a.index('--preview') + 1])


if __name__ == '__main__':
    main()
