#!/usr/bin/env python3
"""Stonehold's people (Nov 17): the quest givers (greetings only for now; their quests come with their areas), the
innkeeper, the rotating Rare / Epic trader, ten gate guards (a Warrior and an Arch-Templar at each of the five ways
out, facing away from the town), and waypoint 7 on the square. Run after build_stonehold.py, game stopped:

    place_stonehold.py <.dat folder>          (tools/world/arealib.py)  -> made.json

The trader's stock is the server's "rotate" line in merchants.dat (merch.c, Nov 17): every 60 minutes 4 new pieces,
Rare or Epic (22:8), level 12-16, Steel / Emerald / Crystal / Titanium, priced by level, tier and metal (merch.c rot_value) at 2x (Cody, Nov 17). Tiers exist only for helmets and body armor, so the variety is the metal
and the piece. He buys nothing (kinds 0). The Granite Hearth is a tavern (players can log out there) except the
innkeeper's corner: NPCs can't stand on tavern tiles."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
HERE = os.path.dirname(os.path.abspath(__file__)); DAT = sys.argv[1]
A = Area(DAT, seed=1130); W = A.W
T = json.load(open(os.path.join(HERE, 'made_terrain.json')))
JAMIL, INGA, SERENA, SIRJAN, STEVEN, HOLLIS, BRUNHILD, MERCHANT, CITYGUARD = 25, 50, 109, 28, 91, 2006, 65, 835, 2006
WAR_M, WAR_F, AT_M, AT_F = 247, 552, 544, 549          # looks: Warrior / Arch-Templar, male / female
def look(t): f = A.tc(t); return {'sprite': f['sprite'], 'kindred': f['kindred']}
def place(t, x, y, d, who):
    n, msgs = W.apply([{'op': 'npcplace', 't': t, 'x': x, 'y': y, 'dir': d}], 'place')
    for m in msgs: print('  !', who, m)
def merchant(name, like, x, y, d, stock, greet, desc):
    t = A.made({'op': 'ctempnew', 'from': MERCHANT, 'name': name}); dd = list(A.tc(t)['data'])
    for i in list(range(0, 24)) + list(range(32, 36)) + [29, 41]: dd[i] = 0
    for i, s in enumerate(stock[:10]): dd[i] = s
    f = {'data': dd, 'item': list(stock[:40]) + [0] * (40 - len(stock[:40])), 'description': desc}; f.update(look(like))
    W.apply([{'op': 'ctempset', 't': t, 'fields': f, 'text': ['Hah!', 'Thief! Guards!', greet], 'respawn': False}], name)
    place(t, x, y, d, name); return t
def guard(name, like, x, y, d, desc):
    t = A.made({'op': 'ctempnew', 'from': CITYGUARD, 'name': name}); dd = list(A.tc(t)['data'])
    for i in list(range(10, 24)) + list(range(32, 36)) + [29, 41]: dd[i] = 0
    f = {'data': dd, 'description': desc}; f.update(look(like))
    W.apply([{'op': 'ctempset', 't': t, 'fields': f, 'respawn': False,
              'text': ['The mountain keeps its own.', 'To arms! To the gate!', 'Stonehold stands, %s. Watch the road out there; things walk down from the heights.']}], 'guard')
    place(t, x, y, d, name); return t

# the Granite Hearth: a tavern, but not the innkeeper's corner
INN = (658, 817, 666, 829); CORNER = (658, 821, 660, 825)
A.ops = [{'op': 'flag', 'x': x, 'y': y, 'bit': 7, 'mode': 0 if CORNER[0] <= x <= CORNER[2] and CORNER[1] <= y <= CORNER[3] else 1}
         for x in range(INN[0], INN[2] + 1) for y in range(INN[1], INN[3] + 1)]
A.run('inn tavern')
M = {}
M['hagar'] = A.person('Hagar', SIRJAN, 674, 783, 2, "Mind the sparks, %s. I'm Hagar, smith of Stonehold. West of the gate the old Foundry still roars, and what it makes now isn't fit for honest hands. I'll have work for you.",
                      'The smith of Stonehold, broad as a door, with a leather apron burnt through in a dozen places.')
M['varo'] = A.person('Varo', JAMIL, 671, 835, 2, 'Peace on you, %s. I am Varo, keeper of this temple. The fields south of here burned long ago, and the ash does not lie still. Come back when you are ready.',
                     'A grey-bearded priest in a heavy wool robe, a granite pendant on a cord at his neck.')
M['rhea'] = A.person('Commander Rhea', AT_F, 659, 792, 2, 'You came through the pass on your own feet, %s? Then you may be useful. I am Rhea, commander of the Stonehold Watch. The heights are not quiet.',
                     'The commander of the Stonehold Watch, in plate scarred by many winters on the walls.')
M['bounty'] = A.person('Watch Sergeant Brann', WAR_M, 659, 796, 2, 'The Watch pays for what it does not have to fight itself, %s. The bounty lists go up soon - golems, gargoyles, whatever comes down the mountain.',
                       'The Watch sergeant who keeps the bounty ledger, a heavy man with a crossbow bolt scar through one ear.')
M['innkeeper'] = merchant('Dora', BRUNHILD, 659, 823, 2, [1141, 1142, 1143], 'Come in out of the wind, %s. The fire is warm and the ale is strong at the Granite Hearth.',
                          'Dora keeps the Granite Hearth, the inn cut into the mountain at Stonehold.')
M['trader'] = merchant('Selwyn', HOLLIS, 697, 783, 1, [], 'Fine armor from far places, %s. What I have changes with every caravan through the pass - look now, it may be gone in an hour.',
                       'Selwyn, a travelling trader in a fur-trimmed coat, who deals only in the finest armor.')
P = T['posts']; M['guards'] = []
for k, (way, pair) in enumerate(P.items()):
    (x1, y1, d1), (x2, y2, d2) = pair
    war, at = (WAR_M, AT_F) if k % 2 == 0 else (WAR_F, AT_M)
    M['guards'].append(guard('Stonehold Guard', war, x1, y1, d1, 'A warrior of the Stonehold Watch, axe in hand, eyes on the road away from the town.'))
    M['guards'].append(guard('Stonehold Templar', at, x2, y2, d2, 'An arch-templar of the Stonehold Watch, keeping watch on the road away from the town.'))
A.save()
# merchants.dat: the innkeeper; the trader buys nothing and has only his rotating stock
p = os.path.join(DAT, 'merchants.dat'); s = open(p, encoding='latin-1').read().rstrip('\n') + '\n# Stonehold (Nov 17)\n'
s += 'merchant %d sell 0 buy 0 gold 0 kinds 8\nstock %d 1141 1142 1143\n' % (M['innkeeper'], M['innkeeper'])
s += 'merchant %d sell 200 buy 0 gold 0 kinds 0\n# rotate <template> <count> <minutes> <tiers: 4 Rare + 8 Epic> <level from> <level to> <metals: 58 = Steel, Emerald, Crystal, Titanium>\nrotate %d 4 60 12 12 16 58\n' % (M['trader'], M['trader'])
open(p, 'w', encoding='latin-1').write(s)
# waypoint on the square
p = os.path.join(DAT, 'waypoints.dat'); L = open(p, encoding='latin-1').read().rstrip('\n').split('\n')
nxt = next(int(l.split()[1]) for l in L if l.startswith('next '))
L = ['next %d' % (nxt + 1) if l.startswith('next ') else l for l in L] + ['wp %d 682 810 0 0 Stonehold|Mountain town beyond the pass' % nxt]
open(p, 'w', encoding='latin-1').write('\n'.join(L) + '\n'); M['waypoint'] = nxt
json.dump(M, open(os.path.join(HERE, 'made.json'), 'w'), indent=1); print(M)
