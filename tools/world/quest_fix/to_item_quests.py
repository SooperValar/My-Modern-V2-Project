#!/usr/bin/env python3
"""Nov 15: Bandit Hollow's three quests become item quests (the town quests' kind: the #quest list, the Quests page's
item quests), and the Old Quarry's two become one chain quest (quest 4, three journal steps: the seal, then the axe).
    python3 to_item_quests.py <.dat folder>"""
import sys, os, json, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
DAT = sys.argv[1]
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
BH = json.load(open(os.path.join(HERE, '..', 'bandit_hollow', 'made.json')))
OQ = json.load(open(os.path.join(HERE, '..', 'old_quarry', 'made.json')))

# ---- Bandit Hollow: wants, gives, exp, gold (silver), how many, lowest rank, greeting
HOLLOW = [
    (BH['hollis'], BH['head'], BH['belt'], 1600, 8000, 1, 4,
     "Hail, %s. Bandits hold the hollow down the east road. Bring me the head of Red Harlan, their chief, and the city will pay."),
    (BH['tobias'], BH['ledger'], BH['signet'], 1900, 9500, 1, 5,
     "Oh, %s, thank Skua! Bandits took my wagon on the east road, and my ledger with it. Their Quartermaster has it - bring it back!"),
    (BH['wynn'], BH['moonwort'], BH['second'], 1900, 9500, 3, 5,
     "Welcome, %s. The bandits' Poisoner stole my moonwort to poison their blades. Bring it back and I'll brew you something."),
]
for t, want, give, exp, gold, n, rank, greet in HOLLOW:
    d = list(W.ctemp(t)['data'])
    d[49], d[50], d[51], d[66], d[37] = want, 0, exp, give, 1
    W.apply([{'op': 'ctempset', 't': t, 'fields': {'data': d}, 'text': [None, None, greet], 'respawn': True}], 'item quest')

qs, npcs = W.talk_load()
for t, want, give, exp, gold, n, rank, greet in HOLLOW:
    npcs.pop(t, None)
    qs['qrew'][t] = {'lim': 1, 'first': 0, 'gold': gold, 'st': [], 'rmin': rank, 'rmax': -1, 'n': n}
top = max([v for v in qs['order'].values() if v > 0] or [0])
for k, (t, *_r) in enumerate(HOLLOW):
    qs['order'][t] = top + 1 + k
for q in (1, 2, 3, 5):
    qs['names'].pop(q, None); qs['steps'].pop(q, None)

# ---- Old Quarry: one chain quest, the seal then the axe
qs['names'][4] = 'The Old Quarry'
qs['steps'][4] = [
    [1, "Take the Foreman's Seal from the Golem Overseer in the middle of the Old Quarry and bring it to Brann at the quarry's mouth."],
    [2, "Brann has his seal. Now kill the Deep Grolm Chieftain in the caves at the far end of the quarry and bring Brann his stone axe (First Sergeant)."],
    [3, "Done: Brann paid you for the Chieftain's axe. The Old Quarry is quiet."],
]
BR = """npc %(brann)d Brann (the Old Quarry)
when give %(seal)d
if quest 4 < 2
answer My seal! With this the quarry's mine again. Here, %%s - a quarryman's amulet, and your wages. There's one more job, when you're up to it.
give item %(amulet)d
give exp 6000
give gold 30000
set quest 4 2
keep
end
when give %(seal)d
answer I've got my seal already, %%s.
end
when give %(axe)d
if quest 4 < 2
answer First my seal, %%s. Bring it back from the Golem Overseer, then we'll talk about the caves.
end
when give %(axe)d
if quest 4 = 2
if rank >= 7
answer The Chieftain's axe! Then the deep caves are quiet for a while. Take these, %%s - stoneskin draughts, they'll keep you whole down there.
give item %(stoneskin)d
give item %(stoneskin)d
give exp 10000
give gold 50000
set quest 4 3
keep
end
when give %(axe)d
if quest 4 = 2
answer You took that from the Chieftain? Come back when you're a First Sergeant, %%s, and I'll pay you for it.
end
when give %(axe)d
answer You've already brought me one of those, %%s.
end
when near
if quest 4 = 0
if rank < 6
answer Stay out of the pit, %%s. The golems would grind you to gravel - come back when you're a Master Sergeant.
end
when near
if quest 4 = 0
answer Work for you, %%s, if you've the nerve. The Golem Overseer in the middle of the pit wears my foreman's seal - bring it back and the quarry's mine again.
set quest 4 1
end
when near
if quest 4 = 1
answer The Overseer still has my seal, %%s. It stands in the middle of the pit.
end
when near
if quest 4 = 2
if rank >= 7
answer One more job, %%s. Grolms came up through the caves at the far end of the pit. Kill their Chieftain and bring me his stone axe.
end
when near
if quest 4 = 2
answer Thanks to you the quarry's working again, %%s. Grolms are stirring in the deep caves - come back when you're a First Sergeant.
end
when say quest|task|job|work|seal|golem*|overseer
if quest 4 < 2
answer The Golem Overseer in the middle of the pit has my foreman's seal, %%s. Bring it back.
set quest 4 1
end
when say quest|task|job|work|grolm*|chieftain|cave*|axe
if quest 4 = 2
answer The Deep Grolm Chieftain leads the grolms in the caves at the far end of the pit. Bring me his stone axe, %%s (First Sergeant).
end
""" % OQ
open(os.path.join(HERE, 'brann_talk.txt'), 'w').write(BR)
_q, bn = me.talk_parse(BR)
npcs[OQ['brann']] = bn[OQ['brann']]
print(W.talk_save(qs, npcs))
print(W.save())
