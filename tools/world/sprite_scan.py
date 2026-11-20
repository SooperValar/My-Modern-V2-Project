#!/usr/bin/env python3
"""Sprite numbers: what is used, by what, and what is free (Nov 19; Cody: "we will keep adding sprites at a high rate -
is the game going to still be able to handle them all?"). Writes docs/SPRITE_MAP.md.

    sprite_scan.py <client folder> <server folder>

A sprite number is 16 bits everywhere (map, items, characters, the network): 1-65535. A number is TAKEN when the client
has a picture for it (gx00.dat, pnglib.dat or a loose GFX/<n>.png). Each taken number is then sorted by what refers to
it: the world (map floors and objects), items and item templates (both looks), characters and NPC templates (their
look's whole frames: base + 0..447, and for the original looks their prestige recolours too: base + 0..1023), a number written in the client's or the server's C code, our own new art
(loose GFX files) - or nothing found (original art nothing seems to use: candidates to reuse, after a closer look)."""
import glob, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'mapedit')); sys.argv_ = sys.argv; sys.argv = ['x']
import mapedit as me
client, server = sys.argv_[1], sys.argv_[2]; dat = os.path.join(server, '.dat')

# --- taken: the client has a picture
idx = open(os.path.join(client, 'gx00.idx'), 'rb').read(); orig = set()
for n in range(len(idx) // 12):
    xs, ys, off = struct.unpack_from('<3i', idx, n * 12)
    if 0 < xs <= 2048 and 0 < ys <= 2048: orig.add(n)
pi = open(os.path.join(client, 'pnglib.idx'), 'rb').read(); p = struct.unpack('<%di' % (len(pi) // 4), pi)
orig |= {i for i, v in enumerate(p) if v}
ours = {int(os.path.splitext(os.path.basename(f))[0]) for f in glob.glob(os.path.join(client, 'GFX', '*.png'))
        if os.path.splitext(os.path.basename(f))[0].isdigit()}
taken = (orig | ours) - {0}

# --- referenced
ref = {}
def mark(n, why):
    if 0 < n < 65536: ref.setdefault(n, set()).add(why)
m = open(os.path.join(dat, 'map.dat'), 'rb').read()
for i in range(0, len(m), 28):
    a, b = struct.unpack_from('<HH', m, i); mark(a, 'world'); mark(b, 'world')
for fn, size, maxn in (('item.dat', me.ITEM_SIZE, me.MAXITEM), ('titem.dat', me.ITEM_SIZE, me.MAXTITEM)):
    d = open(os.path.join(dat, fn), 'rb').read()
    for k in range(min(maxn, len(d) // size)):
        o = k * size
        if d[o + me.I_USED]:
            for s in struct.unpack_from('<2H', d, o + me.I_SPRITE): mark(s, 'items')
looks = set()
for fn, maxn in (('char.dat', me.MAXCHARS), ('tchar.dat', me.MAXTCHARS)):
    d = open(os.path.join(dat, fn), 'rb').read()
    for k in range(min(maxn, len(d) // me.CHAR_SIZE)):
        o = k * me.CHAR_SIZE
        if d[o + me.C_USED]:
            for off in (me.C_SPRITE,):
                s = struct.unpack_from('<H', d, o + off)[0]
                if s: looks.add(s)
sl = sorted(looks)
for i, s in enumerate(sl):          # a look's block (see below)
    # the client draws a look's frames at base + 0..447 (216 + 7*32 + a few: engine.c); the original looks (below 41000,
    # 1024 apart) also have prestige recolours at +448 and +896 (LOOKTIER_STEP, svr_god.c); our new looks (41000 on) do not
    size = 1024 if s < 41000 else 448
    for k in range(min(size, (sl[i + 1] - s) if i + 1 < len(sl) else size)): mark(s + k, 'characters')
lit = re.compile(r'(?<![\w.])(\d{2,5})(?![\w.])')
for folder, why in ((os.path.join(ROOT, 'client'), 'client code'), (server, 'server code')):
    for f in glob.glob(os.path.join(folder, '*.c')) + glob.glob(os.path.join(folder, '*.h')):
        for mm in lit.finditer(open(f, encoding='latin-1').read()):
            mark(int(mm.group(1)), why)
for n in range(1, 2000): mark(n, 'interface (0-1999)')        # the client's own pictures: never reuse these

def runs(nums):
    out = []; s = None
    for n in sorted(nums):
        if s is None: s = e = n
        elif n == e + 1: e = n
        else: out.append((s, e)); s = e = n
    if s is not None: out.append((s, e))
    return out

free_all = set(range(1, 65536)) - taken
# a number with no picture can still be in use: a character look whose frames are missing, a number in the code, a
# map tile or item pointing at nothing. Only numbers nothing refers to are FREE to use.
free = {n for n in free_all if n not in ref}
unref = {n for n in orig - ours if n not in ref}
# our art: which tool makes each run (a tool file that names a number in the run)
tools = {f: open(f, encoding='utf-8', errors='replace').read() for f in glob.glob(os.path.join(ROOT, 'tools', 'sprites', '**', '*.py'), recursive=True)}
nums_in = {f: {int(x) for x in re.findall(r'\b(\d{4,5})\b', t)} for f, t in tools.items()}
L = ['# Sprite numbers', '', '_Written by `tools/world/sprite_scan.py` (rerun it after adding sprites)._', '',
     'A sprite number is 16 bits everywhere (map, items, characters, the network): **1-65535 is the hard limit**.', '',
     '| | numbers |', '|---|---:|',
     '| taken (the client has a picture) | %d |' % len(taken), '| - original art (gx00 / pnglib) | %d |' % len(orig - ours),
     '| - our new art (loose GFX files) | %d |' % len(ours),
     '| no picture, but referred to: do not use (mostly the prestige-recolour room of the original looks, +448 / +896) | %d |' % len(free_all - free),
     '| **free** | **%d** |' % len(free),
     '| original art nothing seems to use (see below) | %d |' % len(unref), '']
fr = runs(free)
L += ['## Free blocks (100 or more in a row)', '', 'Biggest: %d. Sets like the sea (1,024) no longer fit in one block: split a big set over two blocks, or make it smaller.' % max(e - s + 1 for s, e in fr), '',
      '| from | to | size |', '|---:|---:|---:|']
L += ['| %d | %d | %d |' % (s, e, e - s + 1) for s, e in sorted(fr, key=lambda r: -(r[1] - r[0])) if e - s + 1 >= 100]
L += ['', 'Free in smaller gaps: %d (fine for single items, props and icons).' % sum(e - s + 1 for s, e in fr if e - s + 1 < 100), '']
L += ['## Our new art (loose GFX files)', '', '| from | to | count | made by |', '|---:|---:|---:|---|']
for s, e in runs(ours):
    who = sorted({os.path.relpath(f, os.path.join(ROOT, 'tools', 'sprites')) for f, ns in nums_in.items() if any(s <= n <= e for n in ns)})
    L.append('| %d | %d | %d | %s |' % (s, e, e - s + 1, ', '.join(who[:3]) + (' ...' if len(who) > 3 else '') if who else '?'))
L += ['', '## Original art nothing seems to use', '',
      'Taken by original pictures, but not on the map, not an item or template look, not inside any character\'s or NPC\'s',
      'animation block, and not written in the client\'s or server\'s code. **Candidates** to reuse - each needs a look',
      'first (some are picked by a formula, like spell effects or animation frames).', '',
      '| from | to | count |', '|---:|---:|---:|']
ur = runs(unref)
L += ['| %d | %d | %d |' % (s, e, e - s + 1) for s, e in ur if e - s + 1 >= 50]
L += ['', 'In smaller runs: %d.' % sum(e - s + 1 for s, e in ur if e - s + 1 < 50), '']
if not unref:
    L += ['**None found** (Nov 19): the original art is small (about %d numbers) and all of it belongs to a character or' % len(orig - ours),
          'NPC look (their animation blocks sit side by side, 256 apart), an item, the map or the interface. Reclaiming',
          'original art would mean retiring whole character looks - not worth it while there is free room.', '']
L += ['## Budget rules (Nov 19)', '',
      '- Put every new set in this file\'s free list (rerun the scan) and name its range in the tool\'s docstring.',
      '- Big auto-tiling sets are the expensive ones: prefer 2 variants to 4, a 3x3 water picture to 4x4.',
      '- A set bigger than the biggest free block: the editor\'s DROPS / LEDGES would need a set split over two blocks.',
      '- The way past 65,535 is 32-bit sprite numbers in map.dat, items, characters and the network - a big change, only if needed.', '']
open(os.path.join(ROOT, 'docs', 'SPRITE_MAP.md'), 'w').write('\n'.join(L) + '\n')
print('taken', len(taken), 'free', len(free), 'unreferenced original', len(unref), 'biggest free', max(e - s + 1 for s, e in fr),
      'unref runs>=50', sum(e - s + 1 for s, e in ur if e - s + 1 >= 50))
if '--why' in sys.argv_:
    from collections import Counter
    c = Counter()
    for n in orig - ours:
        w = ref.get(n, set())
        c['world' if 'world' in w else 'items' if 'items' in w else 'characters' if 'characters' in w else
          'interface' if any(x.startswith('interface') for x in w) else 'code' if w else 'none'] += 1
    print(c); print('looks', len(looks), sorted(looks)[:40])
if '--ours' in sys.argv_:
    un = sorted(n for n in ours if n not in ref)
    print('our art referenced', len(ours) - len(un), 'not (yet) used anywhere', len(un))
    for s, e in runs(un):
        if e - s + 1 >= 40: print('  ', s, e, e - s + 1)
