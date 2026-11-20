#!/usr/bin/env python3
"""Band C, one area per rank (Nov 19; Cody: "make sure the progression is smooth through that portion of the ranks").
Area averages were Drowned Village 8.5, Barrow Hills 9.4, Lizard Hatcheries 11.0: nothing at Sergeant Major / First
Lieutenant. Now: Drowned Village -> Sergeant Major, Flooded Chapel Second Lieutenant, Barrow Hills -> First Lieutenant,
Lizard Hatcheries Captain - each with an area clear (the Quests page's suggested exp).

    retune_band_c.py <.dat folder> [--dry]

- the 5 Second Lieutenant Drowned Sailors (2161, 2177-2180) take the strength of a Sergeant Major one (2160);
- the 6 Sergeant Major Barrow Skeletons (2224, 2226 ... 2234) take the strength of a Second Lieutenant one (2208);
  (attributes, hit points, endurance, mana, skills; the NPCs respawn with it)
- area clears 14-17 (Barrow Hills' clear 13 keeps its NPCs; its exp follows its new rank)."""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from arealib import Area
dat = sys.argv[1]; dry = '--dry' in sys.argv
A = Area(dat, seed=1119); me = A.me; W = A.W
pts = lambda t: struct.unpack_from('<i', W.tchar, t * me.CHAR_SIZE + 709)[0]

def take(targets, model):
    f = A.scaled(model, 100)
    for t in targets:
        b = (A.rank_of(t), pts(t))
        W.apply([{'op': 'ctempset', 't': t, 'fields': f, 'text': [], 'respawn': True}], 'retune')
        print('  %d %-16s %-18s %9d  ->  %-18s %9d' % (t, A.tc(t)['name'], b[0], b[1], A.rank_of(t), pts(t)))

def avg(zone, skip=()):
    L = [n for n in W.zone_npcs(zone) if n['kind'] == 'enemy' and n['t'] not in skip]
    return L, sum(me.points2rank(n['pts']) for n in L) / len(L)

chapel = {n['t'] for n in W.zone_npcs('Flooded Chapel') if n['kind'] == 'enemy'}
print('before: Drowned Village %.2f, Barrow Hills %.2f' % (avg('Drowned Village', chapel)[1], avg('Barrow Hills')[1]))
take([2161, 2177, 2178, 2179, 2180], 2160)
take([2224, 2226, 2228, 2230, 2232, 2234], 2208)

def sug(rank, n):
    climb = me.RANK_PTS[rank] - (me.RANK_PTS[rank - 1] if rank else 0)
    pct = 0.03 if n <= 10 else 0.05 if n <= 25 else 0.07
    raw = climb * pct; mag = 10 ** max(0, len(str(int(raw))) - 2)
    return max(10, round(raw / mag) * mag)

qs, npcs = W.talk_load(); cl = qs['clears']
want = [('Drowned Village', 'Drowned', chapel), ('Flooded Chapel', 'Sea Golems', ()), ('Barrow Hills', None, ()), ('Lizard Hatcheries', 'Lizards', ())]
nid = max(cl) + 1
for zone, label, skip in want:
    L, a = avg(zone, skip); r = round(a)
    old = [c for c in cl.values() if c['zone'].lower() == zone.lower()]
    if old:
        c = old[0]; L2 = [n for n in L if n['t'] in c['npcs']]; r = round(sum(me.points2rank(n['pts']) for n in L2) / len(L2))
        c['exp'] = sug(r, len(c['npcs'])); print('  clear %d %s: %s, %d monsters, exp -> %d' % (c['id'], zone, me.RANKS[r], len(c['npcs']), c['exp']))
    else:
        c = {'id': nid, 'exp': sug(r, len(L)), 'seyan': 1, 'zone': zone, 'label': label, 'npcs': sorted({n['t'] for n in L})}
        cl[nid] = c; nid += 1
        print('  clear %d %s: %s (%.2f), %d monsters, exp %d' % (c['id'], zone, me.RANKS[r], a, len(c['npcs']), c['exp']))
if not dry:
    W.clears_save(list(cl.values())); W.save()
    print('saved')
