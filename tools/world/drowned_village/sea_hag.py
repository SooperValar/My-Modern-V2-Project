#!/usr/bin/env python3
"""Wenna, Maud's Apprentice (wenna.py) becomes the Sea Hag (Cody, Nov 18): look B, the Mage (6096) recoloured grey-blue
(sprites 58000+, recolor_creature.py seahag2), on the drowned village's shore at 427,927 facing west. She holds Maud's Herb
Pouch (Ilse's second quest). Game stopped:   sea_hag.py <.dat folder>"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
HERE = os.path.dirname(os.path.abspath(__file__))
A = Area(sys.argv[1]); M = json.load(open(os.path.join(HERE, 'made.json'))); T = M['wenna']
f = A.tc(T)
A.W.apply([{'op': 'ctempset', 't': T, 'respawn': True, 'fields': {'name': 'the Sea Hag', 'reference': 'the Sea Hag', 'sprite': 58000,
            'description': "A hag of the drowned shore, grey as the deep and hung with weed. She stole the Bog Witch's herb pouch, and keeps it close."},
            'text': ['Back to the deep with you.', 'The sea takes all, %s - and so do I!']}], 'the Sea Hag')
for msg in A.W.apply([{'op': 'npcmove', 'x': f['x'], 'y': f['y'], 'tx': 427, 'ty': 927}], 'move')[1]: print('  !', msg)
for msg in A.W.apply([{'op': 'npcdir', 'x': 427, 'y': 927, 'dir': 3}], 'face west')[1]: print('  !', msg)
g = A.tc(T); print(T, g['name'], g['x'], g['y'], g['dir'], g['sprite'])
M['sea_hag'] = T; A.save(M, HERE)
