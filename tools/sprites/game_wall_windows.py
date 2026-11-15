#!/usr/bin/env python3
"""Windows for the game's own walls (Nov 14, Cody: "ideally all walls can be windows"). The game has windows for
three walls only (Grey Brick 1214 -> 1218, Red Stone 1200 -> 1232, Marble 1156 -> 1168 / 1170); this makes the
rest, in the same style: the wall's own picture with the game's window slit cut through it (the mask of 1218
against the full block 1214, bottom-aligned, so taller walls keep their upper part) and the lower block's top
painted as a plain sill in the wall's own colour. Each window's hidden-walls form (N+1) is the wall's own cut-down
picture. Numbered from 36700: 36700 + 2*i the window, +1 its hidden form, i in the order of WALLS.
Writes game_wall_windows.json (more WORLD_WINDOWS entries for the editor).

    game_wall_windows.py <client folder> [--out <folder>] [--sheet <png>]
"""
import json, os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
FIRST = 36700
WALLS = [(100, 'Greek Wall'), (102, 'Greek Wall II'), (104, 'Greek Wall III'), (122, 'Mine Wall (gold)'), (124, 'Mine Wall (coal)'),
         (126, 'Mine Wall (lava)'), (150, 'Stone Wall'), (152, 'Stone Wall II'), (154, 'Stone Wall III'), (156, 'Stone Wall IV'),
         (158, 'Dark Stone Wall (pebbles)'), (160, 'Stone Wall V'), (400, 'Black Stone Wall'), (556, 'Brown Stone Wall'), (661, 'Lava Wall'),
         (930, 'Black Stronghold Wall'), (932, 'Black Stronghold Wall II'), (1210, 'Dark Stone Wall'), (1260, 'Earth Wall'), (1262, 'Earth Wall II'),
         (16535, 'Black Stronghold Wall (hole)'), (16537, 'Black Stronghold Wall (hole II)'), (16574, 'Black Stronghold Wall (ember)'),
         (16576, 'Black Stronghold Wall (ember II)'), (16578, 'Black Stronghold Wall (ember III)'), (16580, 'Black Stronghold Wall (ember IV)'),
         (16582, 'Black Stronghold Wall (ember V)'), (16688, 'Lava Wall II'), (16718, 'Green Glowing Stone Wall')]
SILL_TOP, SILL_H = 32, 16      # in the 64-high window 1218


def main():
    client = sys.argv[1]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(client, 'GFX')
    sheet = sys.argv[sys.argv.index('--sheet') + 1] if '--sheet' in sys.argv else None
    sys.argv = [sys.argv[0], client, '/tmp']
    exec(open(os.path.join(HERE, '..', 'world', 'spritesheets.py')).read().split('ids=sorted')[0], globals())
    full, win = load(1214).convert('RGBA'), load(1218).convert('RGBA')
    fp, wp = full.load(), win.load()
    made, names = {}, []
    for i, (s, name) in enumerate(WALLS):
        im = load(s).convert('RGBA'); W, H = im.size; off = H - 64; px = im.load()
        res = im.copy(); rp = res.load()
        # the sill colour: the wall's own face pixels just below the slit, a little lighter
        acc, k = [0, 0, 0], 0
        for y in range(off + 40, min(H, off + 60)):
            for x in range(W):
                if px[x, y][3]: acc = [a + b for a, b in zip(acc, px[x, y][:3])]; k += 1
        sill = tuple(min(255, int(a / max(1, k) * 1.12)) for a in acc)
        for y in range(off, H):
            for x in range(W):
                yy = y - off
                if not px[x, y][3]: continue
                if fp[x, yy][3] and not wp[x, yy][3]: rp[x, y] = (0, 0, 0, 0)            # the slit
                d = abs(x - 15.5) / 2.0
                if SILL_TOP + d - 0.5 <= yy <= SILL_TOP + SILL_H - d + 0.5 and wp[x, yy][3]:
                    n = ((x * 7 + y * 13) % 9 - 4) / 60.0
                    rp[x, y] = tuple(max(0, min(255, int(c * (1 + n)))) for c in sill) + (255,)
        n = FIRST + 2 * i
        made[n] = res; made[n + 1] = load(s + 1).convert('RGBA')
        names.append([n, name + ', window', 1])
    os.makedirs(out, exist_ok=True)
    for n, im in made.items(): im.save(os.path.join(out, '%05d.png' % n))
    json.dump(names, open(os.path.join(HERE, 'game_wall_windows.json'), 'w'))
    print('%d sprites %d-%d' % (len(made), min(made), max(made)))
    if sheet:
        S = Image.new('RGBA', (10 * 70, ((len(WALLS) + 9) // 10) * 104), (40, 60, 40, 255))
        for i, (s, name) in enumerate(WALLS):
            im = made[FIRST + 2 * i]; S.alpha_composite(im, ((i % 10) * 70 + 4, (i // 10) * 104 + 100 - im.height))
            orig = load(s).convert('RGBA'); S.alpha_composite(orig, ((i % 10) * 70 + 36, (i // 10) * 104 + 100 - orig.height))
        S = S.resize((S.width * 2, S.height * 2), Image.NEAREST)
        S.convert('RGB').save(sheet)


if __name__ == '__main__':
    main()
