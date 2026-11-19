#!/usr/bin/env python3
"""Stone statues from the game's own character sprites (Nov 19; Cody: "modify a few of the ... Mercenary sprites with a
blocky base to be a statue", every direction, and if they come out nice, all the classes for use elsewhere).
A character's standing frame for each of the 8 directions (base + 8*k: up, down, left, right, left-up, left-down,
right-up, right-down) turned to stone - its shading kept as the stone's light and dark, a little grain - standing on a
square stone plinth drawn in the game's view. World objects, 64x96 (the client draws them in 32-px blocks, centred, on
the bottom edge); each one's next number is its hide-walls form (the plinth and the feet only).

    statues.py <client folder> <source base> <first sprite> [--stone granite|marble|sandstone] [--nosword]
               [--out <folder>] [--sheet <png>]

  --nosword: the weapon taken out first (unarmed_robes.strip; the Mercenary) - a monk.
Sprites: first + 2*k (k = direction 0..7) and first + 2*k + 1 (hide-walls form): 16 numbers.
Made: 38479-38494 monk statues (the Mercenary 5072, no sword, granite) for the Monastery."""
import os, sys, random
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
STONES = {'granite': ((40, 40, 44), (138, 138, 142), (226, 226, 230)), 'marble': ((90, 88, 86), (196, 194, 190), (250, 250, 248)),
          'sandstone': ((70, 52, 32), (170, 140, 100), (236, 214, 170))}
DIRS = ['up', 'down', 'left', 'right', 'left-up', 'left-down', 'right-up', 'right-down']


def stone(im, stops, seed):
    r = random.Random(seed); im = im.convert('RGBA'); px = im.load(); (d, m, l) = stops
    for y in range(im.height):
        for x in range(im.width):
            p = px[x, y]
            if not p[3]: continue
            t = (0.3 * p[0] + 0.59 * p[1] + 0.11 * p[2]) / 255.0
            t = min(1.0, max(0.0, 0.18 + t * 1.25 + r.uniform(-0.05, 0.05)))           # lifted: stone is lighter than cloth and skin
            c = tuple(d[i] + (m[i] - d[i]) * t * 2 if t < 0.5 else m[i] + (l[i] - m[i]) * (t - 0.5) * 2 for i in range(3))
            px[x, y] = tuple(int(v) for v in c) + (255,)
    return im


def plinth(stops, h=9, w=13):
    """a square stone block in the game's view: top diamond 2w x w, sides h high; returns (image, top y in it)"""
    (d, m, l) = stops; W = 2 * w + 2; H = w + h + 2; im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(im)
    cx = W // 2; top = [(cx, 0), (W - 1, w // 2), (cx, w), (0, w // 2)]
    g.polygon([(0, w // 2), (cx, w), (cx, w + h), (0, w // 2 + h)], fill=tuple(int(v * 0.85) for v in m))                 # left face
    g.polygon([(cx, w), (W - 1, w // 2), (W - 1, w // 2 + h), (cx, w + h)], fill=tuple(int(v * 0.62) for v in m))        # right face
    g.polygon(top, fill=tuple(int((m[i] + l[i]) / 2) for i in range(3)))
    g.line([(0, w // 2), (cx, w), (W - 1, w // 2)], fill=tuple(int(v * 1.0) for v in l))                                     # lit edge
    g.line([(0, w // 2), (0, w // 2 + h), (cx, w + h), (W - 1, w // 2 + h), (W - 1, w // 2)], fill=d)
    g.line([(cx, w), (cx, w + h)], fill=tuple(int(v * 0.5) for v in m))
    g.line([(0, w // 2), (cx, 0), (W - 1, w // 2)], fill=tuple(int(v * 0.7) for v in m))
    return im, w // 2


FIG_SCALE = 1.15          # Cody (Nov 19): "looks like it's floating... is it just smaller than the square?" - a little bigger,
                          # feet set into the top (not on its back edge), a contact shadow under them, a smaller plinth

def statue(fig, stops, hide=False):
    pl, ty = plinth(stops, h=8, w=11); out = Image.new('RGBA', (64, 96), (0, 0, 0, 0))
    px0, py0 = 32 - pl.width // 2, 96 - pl.height - 4                     # the plinth on the tile's diamond
    fig = fig.crop(fig.getbbox())
    fig = fig.resize((max(1, round(fig.width * FIG_SCALE)), max(1, round(fig.height * FIG_SCALE))), Image.NEAREST)
    if hide: fig = fig.crop((0, max(0, fig.height - 7), fig.width, fig.height))
    out.alpha_composite(pl, (px0, py0))
    foot = py0 + ty + 4                                                     # just in front of the top's middle
    sh = Image.new('RGBA', (64, 96), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse([32 - 7, foot - 2, 32 + 7, foot + 2], fill=(20, 20, 24, 110))
    out.alpha_composite(sh)                                                 # the contact shadow
    fx, fy = 32 - fig.width // 2, foot + 1 - fig.height
    out.alpha_composite(fig, (fx, max(0, fy)))
    return out


def main():
    a = sys.argv[1:]; client, base, first = a[0], int(a[1]), int(a[2])
    look = a[a.index('--stone') + 1] if '--stone' in a else 'granite'; stops = STONES[look]
    sys.argv = [sys.argv[0], client, '/tmp']
    exec(open(os.path.join(HERE, '..', 'world', 'spritesheets.py')).read().split('ids=sorted')[0], globals())
    gdir = os.path.join(client, 'GFX') if os.path.isdir(os.path.join(client, 'GFX')) else os.path.join(client, 'gfx')
    out = a[a.index('--out') + 1] if '--out' in a else gdir
    os.makedirs(out, exist_ok=True); made = []
    if '--nosword' in a: from unarmed_robes import strip
    for k in range(8):
        fig = load(base + 8 * k).convert('RGBA')                          # noqa: F821 (spritesheets.py)
        if '--nosword' in a: fig = strip(fig)
        fig = stone(fig, stops, base + k)
        s, h = statue(fig, stops), statue(fig, stops, hide=True)
        s.save(os.path.join(out, '%d.png' % (first + 2 * k))); h.save(os.path.join(out, '%d.png' % (first + 2 * k + 1))); made.append(s)
    if '--sheet' in a:
        sh = Image.new('RGBA', (8 * 64, 100), (90, 110, 90, 255))
        for k, s in enumerate(made): sh.alpha_composite(s, (k * 64, 2))
        sh.resize((sh.width * 3, sh.height * 3), Image.NEAREST).save(a[a.index('--sheet') + 1])
    print('statues %d-%d from %d (%s%s)' % (first, first + 15, base, look, ', no weapon' if '--nosword' in a else ''))


if __name__ == '__main__':
    main()
