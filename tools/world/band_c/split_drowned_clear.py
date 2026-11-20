#!/usr/bin/env python3
"""The Drowned Village as two area clears (Nov 20; Cody: "add an area twice in case there's 2 sets of enemies"):
clear 18 becomes the Drowned Sailors (and the Sea Hag; Sergeant Major), a new clear the Bog-men (and Captain Morrow and
Maud the Bog Witch; Second Lieutenant). Exp: the Quests page's suggestion for each. The game says "Drowned Village
(Bog-men)" when a zone has more than one clear (npctalk.c clear_name).

    split_drowned_clear.py <.dat folder>"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from arealib import Area
A = Area(sys.argv[1], seed=1120); me = A.me; W = A.W
def sug(rank, n):
    climb = me.RANK_PTS[rank] - (me.RANK_PTS[rank - 1] if rank else 0)
    raw = climb * (0.03 if n <= 10 else 0.05 if n <= 25 else 0.07); mag = 10 ** max(0, len(str(int(raw))) - 2)
    return max(10, round(raw / mag) * mag)
chapel = {n['t'] for n in W.zone_npcs('Flooded Chapel')}
L = [n for n in W.zone_npcs('Drowned Village') if n['kind'] == 'enemy' and n['t'] not in chapel]
sets = {'Drowned Sailors': [n for n in L if n['name'] in ('Drowned Sailor', 'Sea Hag')],
        'Bog-men': [n for n in L if n['name'] in ('Bog-man', 'Captain Morrow', 'Maud the Bog Witch')]}
assert sum(len(v) for v in sets.values()) == len(L), [n['name'] for n in L]
qs, npcs = W.talk_load(); cl = qs['clears']
dv = [c for c in cl.values() if c['zone'] == 'Drowned Village']; assert len(dv) == 1, dv
nid = 1
while nid in cl: nid += 1
for (label, ns), c in zip(sets.items(), [dv[0], {'id': nid, 'seyan': 1, 'zone': 'Drowned Village'}]):
    r = round(sum(me.points2rank(n['pts']) for n in ns) / len(ns))
    c.update(label=label, npcs=sorted(n['t'] for n in ns), exp=sug(r, len(ns))); cl[c['id']] = c
    print('  clear %d Drowned Village (%s): %s, %d monsters, exp %d' % (c['id'], label, me.RANKS[r], len(ns), c['exp']))
W.clears_save(list(cl.values())); print('saved')
