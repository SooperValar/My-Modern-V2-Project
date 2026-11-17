#!/usr/bin/env python3
"""The Barrow Hills' monsters, items and quests (Nov 17). Run after build_barrow.py, game stopped:

    place_barrow.py <.dat folder>          (tools/world/arealib.py)  -> made.json

Monsters (group 35: undead regenerate like Lab 11's, SLOW_UNDEAD_GROUP in data.h): Barrow Skeletons (the Skeleton 422,
its own look; Sergeant Major and Second Lieutenant), Barrow Wights (the Lord 336, First Lieutenant, the pale look 52000:
recolor_creature.py ramp `wightpale`), two to three in each medium tomb, the Barrow Wight Scribe in the Scribe's Barrow
(a bit stronger; carries the Rune-Carved Tablet), Barrow King Ulfgar in the King's Barrow (Captain; the Lord's own dark
look; carries Ulfgar's Torc) with two wight guards. Quests on Fenwatch's Aldous (the Torc) and Petra (the Tablet), found
by name. Item pictures 44533-44535 (tools/sprites/quest_items/barrow_hills.py, README.txt)."""
import sys, os, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
HERE = os.path.dirname(os.path.abspath(__file__))
A = Area(sys.argv[1], seed=1121)
GROUP, WIGHT_LOOK = 35, 52000
SK_RESIST, SK_IDENT = 23, 22
# ---------------------------------------------------------------- items
TABLET = A.quest_item('Rune-Carved Tablet', 'A slab of grey stone cut with rows of old runes, taken from the Scribe\'s Barrow. Petra of Fenwatch wants it.', 44533)
TORC = A.quest_item("Ulfgar's Torc", 'A heavy neck-ring of twisted gold with a garnet in each end, taken from the Barrow King. Aldous of Fenwatch wants it.', 44534)
AMULET = A.worn(191, "Ulfgar's Torc", 'The Barrow King\'s torc, cleansed by the reeve of Fenwatch. Whoever wears it fears little.', 44534, rank=10, value=8000,
                attrib={0: 3}, skill={SK_RESIST: 5})
RING = A.worn(338, "Scholar's Ring", 'A silver ring with a violet stone, given by Petra the scholar. Old writing comes easier to whoever wears it.', 44535, rank=10, value=6000,
              attrib={2: 3}, skill={SK_IDENT: 6}, clear=(1 << 9) | (1 << 10), driver=0, data=[0] * 10)
# ---------------------------------------------------------------- where
BARROWS = [(337, 806, 10, 12, 'king'), (352, 782, 6, 7, 'scribe'), (384, 782, 4, 5, ''), (392, 822, 4, 5, ''), (374, 836, 5, 4, ''), (350, 834, 4, 5, ''),
           (336, 778, 4, 4, ''), (380, 812, 4, 4, ''), (334, 836, 6, 6, 'medium'), (368, 779, 6, 6, 'medium')]      # as in build_barrow.py
ell = lambda x, y, cx, cy, rx, ry: ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0
def in_barrow(x, y, pad=1.5): return any(ell(x, y, cx, cy, rx + pad, ry + pad) for cx, cy, rx, ry, k in BARROWS)
def inside(b): cx, cy, rx, ry, k = b; return lambda x, y: ell(x, y, cx, cy, rx - 1.2, ry - 1.2)
def box(b): cx, cy, rx, ry, k = b; return (cx - rx, cy - ry, cx + rx, cy + ry)
OUT = lambda x, y: not in_barrow(x, y) and not (x >= 388 and 795 <= y <= 807) and abs(x - 366) + abs(y - 805) > 7   # not on the road's first stretch, not in the stone ring
HILLS = (325, 772, 399, 848)
# ---------------------------------------------------------------- monsters
SKEL_TXT = ['Rest... there is no rest...', 'The barrows are closed to you, %s!']
D_SKEL = 'The bones of a warrior buried with the old kings of the hills, risen with a rusted blade still in its hand.'
WIGHT_TXT = ['Another for the barrows.', 'Your warmth... give it to me, %s...']
D_WIGHT = 'A pale, cold thing that was once a man, wrapped in grave-clothes. The air turns to frost around it.'
PCT = {}
def mon(key, src, name, rank, x, y, text, desc, sprite, d=None):
    """the first of a kind finds its strength for the rank (arealib's search), the rest reuse it"""
    t = A.monster(src, name, rank, x, y, d=d, text=text, desc=desc, sprite=sprite, group=GROUP, pct=PCT.get(key))
    PCT[key] = A.last_pct; return t
skel = lambda x, y, rank: mon(rank, 422, 'Barrow Skeleton', rank, x, y, SKEL_TXT, D_SKEL, None)
wight = lambda x, y, d=None: mon('wight', 336, 'Barrow Wight', 'First Lieutenant', x, y, WIGHT_TXT, D_WIGHT, WIGHT_LOOK, d)
skels, wights = [], []
for b in (b for b in BARROWS if b[4] == 'medium'):                               # the medium tombs: two wights and a skeleton each
    s = A.spots(3, box(b), ok=inside(b), apart=2)
    wights += [wight(*s[0]), wight(*s[1])]; skels.append(skel(*s[2], 'Second Lieutenant'))
for x, y in A.spots(11, HILLS, ok=OUT, apart=6): wights.append(wight(x, y))
for i, (x, y) in enumerate(A.spots(13, HILLS, ok=OUT, apart=5)): skels.append(skel(x, y, 'Sergeant Major' if i % 2 else 'Second Lieutenant'))
KING = BARROWS[0]
for x, y in A.spots(2, box(KING), ok=lambda x, y: inside(KING)(x, y) and abs(x - 335) + abs(y - 806) >= 4, apart=4): wights.append(wight(x, y))
SCRIBE = A.monster(336, 'Barrow Wight Scribe', 'First Lieutenant', 350, 782, d=4, items=[TABLET], sprite=WIGHT_LOOK, group=GROUP, nudge=40,
                   text=['Your name is written now.', 'You will not read the stones, %s. No living eye reads them.'],
                   desc='A wight in the rags of a scholar\'s robe, its fingers worn to the bone from carving. It clutches a slab of runes to its chest.')
ULFGAR = A.monster(336, 'Barrow King Ulfgar', 'Captain', 335, 806, d=4, items=[TORC], group=GROUP,
                   text=['Kneel to your king.', 'Who wakes the King of the Hills? Your bones will guard my door, %s!'],
                   desc='The old king of the hills, risen in his black grave-mail. A torc of twisted gold still circles his neck.')
for n, t in (('skeleton', skels[0]), ('skeleton', skels[-1]), ('wight', wights[0]), ('scribe', SCRIBE), ('ulfgar', ULFGAR)): print('  %-9s %d %s' % (n, t, A.rank_of(t)))
# ---------------------------------------------------------------- quests (Fenwatch, by name)
ALDOUS, PETRA = A.by_name('Aldous'), A.by_name('Petra')
A.quest(ALDOUS, TORC, 51000, give=AMULET, lim=1, rmin=10,
        greet="Well met, %s. Since the old king rose in the Barrow Hills, north of the gate, the dead walk right up to our palisade. Bring me Ulfgar's torc from the King's Barrow and I'll see it cleansed - and yours to wear.")
A.quest(PETRA, TABLET, 37000, give=RING, lim=1, rmin=10,
        greet="Ah, %s - do you read runes? Neither do the living, any more. There is a tablet in the Scribe's Barrow in the hills north of town, guarded by the thing that carved it. Bring it to me and you shall have my ring.")
M = {'items': {'tablet': TABLET, 'torc': TORC, 'torc_amulet': AMULET, 'scholars_ring': RING}, 'skeletons': skels, 'wights': wights,
     'scribe': SCRIBE, 'ulfgar': ULFGAR, 'quests': {'aldous': ALDOUS, 'petra': PETRA}, 'pct': PCT}
A.save(M, HERE); print(M['items'], M['quests'], len(skels), 'skeletons', len(wights), 'wights')
