#!/usr/bin/env python3
"""Every quest giver's greeting says what he wants and where to find it (Cody, Nov 18). Game stopped:
    quest_intros.py <.dat folder>
Sources checked in the world: Joe's House, the Cursed Tomb's skeletons (bone swords), the pentagrams' grolms and gargoyles
(Potion of Life), the stone in Serena's house (Sword of Stealth), the Ratling Fighters of Underground I, the Skeleton
Lord's crypt, the Gargoyle's Nest chest (ice egg), the Riddle Gorge's bookshelves, the Lizard Gorge's jungle tree
(coconut); red flowers and silver small-ruby rings are common monster drops (populate.c), a small ruby set in a silver
ring makes one too (use_driver.c)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
A = Area(sys.argv[1])
G = {
 72: "Greetings, %s. Bring me a black candle from the Black Stronghold, north-west of town, and I'll make it worth your while.",
 518: "Welcome to the Cityguard barracks, %s. We need HELP against the Black Stronghold, north-west of town. Bring us a black candle from it!",
 567: "Woe, %s... Bring me a bone sword - the skeletons in the Cursed Tomb carry them - and I shall reward you.",
 111: "Hi, %s. Bring me a Potion of Life - the grolms and gargoyles of the pentagrams carry them - and I'll teach you {skill}.",
 109: "Pull the sword out of that stone, here in my house, and give it to me, %s - I'll teach you Resistance.",
 64: "Joe stole my bronze armor, %s! He lives just east of here. Bring it back and I'll teach you Repair.",
 342: "Hello, %s. Bring me a silver ring with a small ruby - monsters carry them, or set a ruby in a silver ring - and I'll teach you Sense Magic.",
 343: "Greetings, %s. Bring me a Ratling Fighter's Eye - the fighters in the Underground have them - and I'll teach you Rest.",
 180: "Welcome to the Temple of the Purple One, %s! Bring me a red flower - many creatures carry one - and you may join our order.",
 246: "May you pass the last gate, %s. I collect Ratling eyes from the Underground, and Greenling eyes too. Bring me a full collection!",
 161: "Hello, %s! I'd trade my key to the third door of Gorge III for a juicy coconut - the jungle tree here in the gorge has them.",
 615: "May you pass the last gate, %s. A gargoyle's ice egg lies in a chest in the Gargoyle's Nest. Bring it and I'll trade you a cape for it.",
 899: "Mayest thou pass the last gate, %s. Find the Book of Wisdom, Volume 1, on this gorge's shelves, and I will tell you a riddle.",
 905: "Mayest thou pass the last gate, %s. Find the Book of Wisdom, Volume 2, on this gorge's shelves, and I will tell you a riddle.",
 911: "Mayest thou pass the last gate, %s. Find the Book of Wisdom, Volume 3, on this gorge's shelves, and I will tell you a riddle.",
 912: "Mayest thou pass the last gate, %s. Find the Book of Wisdom, Volume 4, on this gorge's shelves, and I will tell you a riddle.",
 913: "Mayest thou pass the last gate, %s. Find the Book of Wisdom, Volume 5, on this gorge's shelves, and I will tell you a riddle.",
 90: "Hello, %s. I'll teach you {skill} if you bring me the potion the Skeleton Lord guards in his crypt here in Aston.",
 1097: "Greetings %s. Bring me the Soul of the Ghost King - he haunts the Ghost Underground, below the Gorn Clan Hall - and I'll reward you greatly!",
 1145: "Greetings %s. The Spider Queen wants me dead. Bring me her head - she nests in the Spider Underground, below the Kwai Clan Hall.",
 2098: "Welcome, %s. I pay for every wolf head from the Wolfwood, more for dire wolves. Bring me Old Greyfang's fang and you'll have something special.",
 2056: "Careful, %s - our golems turned on us. Get my Foreman's Seal back from the Prime Golem in the middle of the quarry, and I'll pay you well.",
}
for t, g in G.items():
    assert len(g.replace('%s', 'x' * 12)) < 159, (t, len(g))
    A.W.apply([{'op': 'ctempset', 't': t, 'fields': {}, 'respawn': True, 'text': [None, None, g]}], 'greeting %d' % t)
A.save(); print(len(G), 'greetings')
