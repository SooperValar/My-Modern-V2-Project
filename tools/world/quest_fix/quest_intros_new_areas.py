#!/usr/bin/env python3
"""Fenwatch's and Stonehold's quest greetings, short enough to fit (Nov 18): an NPC's text line holds 159 letters, and
eight greetings were longer and cut off in the game ("...and I will tea"). Each extra quest (qalias) gets its own line
too: #quest <n> and the Quests page show it. Game stopped:   quest_intros_new_areas.py <.dat folder>"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
A = Area(sys.argv[1])
G = {
 2142: "Mind the nets, %s. Captain Morrow walks his sunk ship in the drowned village, east of here. Bring me his compass and I'll teach you to swim.",
 2203: "The Sea Golem in the drowned village's flooded chapel has my silver net, %s. Bring it back and you'll have a fine belt.",
 2143: "The Light keep you, %s. Maud the Bog Witch curses us from her island in the drowned village. Bring me her hex-doll to burn - and her herb pouch.",
 2204: "Maud keeps an herb pouch on her island in the drowned village, %s. Bring it and I'll brew you three Draughts of Clear Water.",
 2144: "Well met, %s. Bring me Ulfgar's torc from the Barrow Hills north of town, or the Broodmother's crown from the hatcheries to the south.",
 2271: "The Broodmother rules the lizard hatcheries south of town, %s. Bring me her crown and you'll have a belt fit for it.",
 2145: "Ah, %s - do you read runes? A rune-carved tablet lies in the Scribe's Barrow, in the hills north of town. Bring it to me.",
 2146: "Hm? Ah, %s. An archmage brews in a grotto in the lizard caves south of town. Bring me its phial for two Elixirs of the Good Moon.",
 2147: "Fenwatch pays for heads, %s: drowned sailors and bog-men from the drowned village, lizards from the hatcheries - and their eggs.",
 2205: "Bog-men lurk in the drowned village east of town, %s. Fenwatch pays for every head you bring.",
 2272: "Lizards breed in the hatcheries south of town, %s. Fenwatch pays for every lizard head you bring.",
 2273: "Take eggs from the nests in the lizard hatcheries south of town, %s - before they hatch. Fenwatch pays for each one.",
 2277: "Mind the sparks, %s. The old Foundry west of the gate has turned on us. Bring me its Forgemaster's Foundry Heart, or the Brass Colossus's core.",
 2317: "The Brass Colossus stands in the Foundry's casting pit, west of town, %s. Bring me its core and I'll make you a belt.",
 2280: "The Watch pays for Golem Cores from the Foundry west of town, %s - 65 gold apiece, as many as you bring. Gargoyle horns later.",
 2099: "Dire wolves roam the deep Wolfwood, %s. I pay well for every dire wolf head.",
 2100: "Old Greyfang leads the wolves of the Wolfwood, %s. Bring me his fang and I'll make you an amulet.",
}
for t, g in G.items():
    assert len(g) <= 145, (t, len(g))
    A.W.apply([{'op': 'ctempset', 't': t, 'fields': {}, 'respawn': True, 'text': [None, None, g]}], 'greeting %d' % t)
A.save(); print(len(G), 'greetings')
