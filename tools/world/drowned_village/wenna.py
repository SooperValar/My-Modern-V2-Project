#!/usr/bin/env python3
"""Maud's herb pouch moves to her apprentice (Cody, Nov 18: no single monster may hold the answer to two quests). Maud the
Bog Witch keeps only her hex-doll (Ilse's first quest); Wenna, Maud's Apprentice, a weaker bog witch (Sergeant Major), lives
in a house at the village's east end (477-485 / 888-896) with Maud's Herb Pouch (Ilse's second quest). Game stopped:
    wenna.py <.dat folder>"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
HERE = os.path.dirname(os.path.abspath(__file__))
A = Area(sys.argv[1]); M = json.load(open(os.path.join(HERE, 'made.json')))
MAUD, POUCH = M['maud'], M['items']['pouch']
it = [i for i in A.tc(MAUD)['item'] if i != POUCH]; it += [0] * (40 - len(it))
A.W.apply([{'op': 'ctempset', 't': MAUD, 'fields': {'item': it}, 'respawn': True}], 'Maud keeps only the doll')
x, y = min(((x, y) for x in range(478, 485) for y in range(889, 896) if A.free(x, y) and A.tile(x, y)[7] & 4), key=lambda p: abs(p[0] - 481) + abs(p[1] - 892))   # the house's middle
WENNA = A.monster(1012, "Wenna, Maud's Apprentice", 'Sergeant Major', x, y, d=2, items=[POUCH], group=34, nudge=30,
                  text=['The mistress will be pleased.', "You'll not have the mistress's herbs, %s!"],
                  desc="Maud's apprentice, younger and quicker, her apron pockets full of marsh herbs. She keeps the witch's herb pouch.")
print('Wenna', WENNA, x, y, A.rank_of(WENNA))
M['wenna'] = WENNA; A.save(M, HERE)
