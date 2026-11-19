#!/usr/bin/env python3
"""The Ashen Fields' monsters, items and quests (Nov 18). Run after build_ashen.py, game stopped:

    place_ashen.py <.dat folder>          (tools/world/arealib.py)  -> made.json

Monsters (group 38), Colonels: Flames (the game's Flame, 516, as it is) and Ash Gargoyles (the Gargoyle, 324, charcoal:
sprites 59000) through the ravines, more of them deeper in; a few Flames guard each boss.
  Ashra the Cinder Witch (a Colonel caster from the Spellcaster Lord, 249; the Mage look in ash and ember, 61000) in
  Ashra's Hollow, at the end of the long north-west branch, with Ashra's Ash-Veil.
  the Flame Lord (Brigadier General; the Flame 1.4x, blue-hearted fire fireL2, 60000) in the Ember Cavern, reached only
  through the Smoking Steps, with the Ember of the First Flame.
Quests (Varo the priest, Stonehold), Colonel: Ember -> 3 Fireward Draughts (+15 Resistance for 10 minutes) 130,000 exp;
Ash-Veil -> Ring of Embers (+5 Intuition, +10 Blast) 130,000 exp. No gold (only bounties pay gold).
Item pictures 44547-44550 (tools/sprites/quest_items/ashen_fields.py)."""
import sys, os, random, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
HERE = os.path.dirname(os.path.abspath(__file__))
A = Area(sys.argv[1], seed=1181); random.seed(1181)
T = json.load(open(os.path.join(HERE, 'made_terrain.json')))
FLAME, GARG, CASTER, STONESKIN = 516, 324, 249, 2015
GROUP, SK_RES, SK_BLAST = 38, 23, 24
canyon = {(c[0], c[1]): (c[2], c[3]) for c in T['canyon']}; lava = {tuple(p) for p in T['lava']}; CH = T['chambers']
# ---------------------------------------------------------------- items
EMBER = A.quest_item('Ember of the First Flame', 'A coal that has burned since the mountain was young, hot even through gloves. The Flame Lord carried it. Varo of Stonehold wants it.', 44547)
VEIL = A.quest_item("Ashra's Ash-Veil", "A veil of grey gauze, singed at the hem, that smells of smoke. Ashra the Cinder Witch wore it. Varo of Stonehold wants it.", 44548)
sk = [0] * 150; sk[SK_RES * 3 + 1] = 15
DRAUGHT = A.item(STONESKIN, 'Fireward Draught', 'A fiery orange draught, blessed in Varo\'s temple. For ten minutes it wards you: your Resistance is higher.',
                 sprite=[44550, 0], armor=[0, 0], skill=sk, duration=10800, min_rank=14, value=2500)
RING = A.worn(338, 'Ring of Embers', "A soot-dark band set with a stone that glows like a coal, blessed by Varo with ash from Ashra's veil. Fire answers the one who wears it.",
              44549, rank=14, value=20000, attrib={2: 5}, skill={SK_BLAST: 10}, clear=(1 << 9) | (1 << 10), driver=0, data=[0] * 10)
# ---------------------------------------------------------------- where
def ok(x, y, parts=None, tmin=0.08):
    p = canyon.get((x, y))
    if not p or (x, y) in lava or p[1] < tmin: return False
    if parts and p[0] not in parts: return False
    return all((x + dx, y + dy) in canyon for dx in (-1, 0, 1) for dy in (-1, 0, 1))      # not hard against a cliff
BOX = (725, 690, 815, 787)
FT = ['Hssss.', 'Burn, %s!']
FD = 'A living flame, taller than a man, that drifts over the ash. It burns whatever it touches.'
GT = ['...', 'Ssstone and ash, %s!']
GD = 'A gargoyle of charcoal-grey stone, dusted with ash. It sits so still on the ravine ledges that it looks like part of the cliff.'
flames, gargs = [], []
# the ravines and chambers, more monsters deeper in (two passes: the outer half, then the inner)
for kind, n, tlo, thi in (('flame', 7, 0.1, 0.5), ('garg', 7, 0.1, 0.5), ('flame', 9, 0.5, 0.95), ('garg', 9, 0.5, 0.95)):
    for x, y in A.spots(n, BOX, ok=lambda x, y: ok(x, y) and tlo <= canyon[(x, y)][1] < thi and canyon[(x, y)][0] not in ('cavern', 'hollow'), apart=6):
        if kind == 'flame':
            flames.append(A.monster(FLAME, 'Flame', 'Colonel', x, y, text=FT, desc=FD, group=GROUP, pct=(A.flame_pct if flames else None)))
            A.flame_pct = A.last_pct
        else:
            gargs.append(A.monster(GARG, 'Ash Gargoyle', 'Colonel', x, y, text=GT, desc=GD, sprite=59000, group=GROUP, pct=(A.garg_pct if gargs else None)))
            A.garg_pct = A.last_pct
# Ashra and her guard
hc = tuple(CH['hollow'][0]); hollow = [p for p in canyon if canyon[p][0] == 'hollow']
ax, ay = min((p for p in hollow if ok(*p, parts=('hollow',), tmin=0) and A.free(*p)), key=lambda p: abs(p[0] - hc[0]) + abs(p[1] - hc[1]))
ASHRA = A.monster(CASTER, 'Ashra the Cinder Witch', 'Colonel', ax, ay, d=1, items=[VEIL], group=GROUP, sprite=61000, nudge=40,
                  text=['The ash remembers.', 'You will be ash too, %s - grey and still, like all the rest.'],
                  desc='A witch in sooty black, her skin lit from within like a banked fire. Ash drifts from her veil wherever she walks.')
for x, y in A.spots(3, (hc[0] - 7, hc[1] - 7, hc[0] + 7, hc[1] + 7), ok=lambda x, y: ok(x, y, parts=('hollow',), tmin=0) and abs(x - ax) + abs(y - ay) >= 3, apart=3):
    flames.append(A.monster(FLAME, 'Flame', 'Colonel', x, y, text=FT, desc=FD, group=GROUP, pct=A.flame_pct))
# the Flame Lord and his guard (on cinders, not the molten pools)
cc = tuple(CH['cavern'][0]); cav = [p for p in canyon if canyon[p][0] == 'cavern']
lx, ly = min((p for p in cav if ok(*p, parts=('cavern',), tmin=0) and A.free(*p) and not any((p[0] + dx, p[1] + dy) in lava for dx in (-1, 0, 1) for dy in (-1, 0, 1))),
             key=lambda p: abs(p[0] - cc[0]) + abs(p[1] - cc[1]))
LORD = A.monster(FLAME, 'the Flame Lord', 'Brigadier General', lx, ly, d=2, items=[EMBER], group=GROUP, sprite=60000, nudge=30,
                 text=['Kneel to the fire.', 'I WAS BURNING BEFORE YOUR KIND HAD NAMES, %s!'],
                 desc='A towering pillar of fire, white-gold at the edges, with a heart of blue flame that hurts to look at. Something glows brighter still inside it.')
for x, y in A.spots(4, (cc[0] - 10, cc[1] - 10, cc[0] + 10, cc[1] + 10), ok=lambda x, y: ok(x, y, parts=('cavern',), tmin=0) and abs(x - lx) + abs(y - ly) >= 4, apart=4):
    flames.append(A.monster(FLAME, 'Flame', 'Colonel', x, y, text=FT, desc=FD, group=GROUP, pct=A.flame_pct))
for n, t in (('flame', flames[0]), ('gargoyle', gargs[0]), ('ashra', ASHRA), ('flame lord', LORD)): print('  %-10s %d %s' % (n, t, A.rank_of(t)))
# ---------------------------------------------------------------- quests (Varo, Stonehold, by name)
VARO = A.by_name('Varo')
A.quest(VARO, EMBER, 130000, give=DRAUGHT, n=3, lim=1, rmin=14,
        greet="The ash canyon past the south-west gate burns again, %s. Its Flame Lord holds the Ember of the First Flame. Bring it to me.")
VARO_VEIL = A.extra_quest(VARO, VEIL, 130000, give=RING, lim=1, rmin=14)
M = {'items': {'ember': EMBER, 'veil': VEIL, 'draught': DRAUGHT, 'ring': RING}, 'flames': flames, 'gargoyles': gargs, 'ashra': ASHRA, 'flame_lord': LORD,
     'quests': {'varo_ember': VARO, 'varo_veil': VARO_VEIL}, 'vents': T['vent_templates'], 'rocks': T['rock_templates']}
A.save(M, HERE); print(M)
