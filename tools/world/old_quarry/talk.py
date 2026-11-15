#!/usr/bin/env python3
"""SUPERSEDED Nov 15 by tools/world/quest_fix/to_item_quests.py (item quests / one chain quest). npctalk.dat lines for the Old Quarry, from made.json.   talk.py > old_quarry_talk.txt"""
import json, os
M = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'made.json')))
print("""# ---- Old Quarry (Nov 14; tools/world/old_quarry) ----
quest 4 The Foreman's Seal
step 4 1 Take the Foreman's Seal from the Golem Overseer in the middle of the Old Quarry and bring it to Brann at the quarry's mouth.
step 4 2 Done: Brann has his seal back.
quest 5 The Deep Grolm Chieftain
step 5 1 Kill the Deep Grolm Chieftain in the caves at the far end of the Old Quarry and bring Brann his stone axe.
step 5 2 Done: Brann paid you for the Chieftain's axe.

npc %(brann)d Brann (the Old Quarry)
when give %(seal)d
if quest 4 < 2
answer My seal! With this the quarry's mine again. Here, %%s - a quarryman's amulet, and your wages.
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
if quest 5 < 2
answer The Chieftain's axe! Then the deep caves are quiet for a while. Take these, %%s - stoneskin draughts, they'll keep you whole down there.
give item %(stoneskin)d
give item %(stoneskin)d
give exp 10000
give gold 50000
set quest 5 2
keep
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
if quest 5 = 0
if rank >= 7
answer One more job, %%s. Grolms came up through the caves at the far end of the pit. Kill their Chieftain and bring me his stone axe.
set quest 5 1
end
when near
if quest 5 = 1
answer The Deep Grolm Chieftain is at the back of the caves, %%s. Bring me his axe.
end
when say quest|task|job|work|seal|golem*|overseer
if quest 4 < 2
answer The Golem Overseer in the middle of the pit has my foreman's seal, %%s. Bring it back.
set quest 4 1
end
when say quest|task|job|work|grolm*|chieftain|cave*|axe
if quest 5 < 2
if rank >= 7
answer The Deep Grolm Chieftain leads the grolms in the caves at the far end of the pit. Bring me his stone axe, %%s.
set quest 5 1
end
""" % M)
