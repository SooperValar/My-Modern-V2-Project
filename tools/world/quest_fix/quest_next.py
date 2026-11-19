#!/usr/bin/env python3
""""What next" greetings (Cody, Nov 18: players need to know what to find next). An NPC with two item quests greets a
player by what he has done: one done -> "now bring me the other, from there"; both done -> thanks. npctalk.dat "when near"
lines with the new condition "if done <quest template> <op> <n>" (npctalk.c C_DONE). Game stopped:
    quest_next.py <.dat folder>"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
A = Area(sys.argv[1]); W = A.W
d = lambda t, op, v: {'type': 'done', 't': t, 'op': op, 'v': v}
def near(conds, text): return {'when': 'near', 'words': '', 'item': 0, 'conds': conds, 'answers': [text], 'acts': []}
PAIRS = {   # npc: (first quest, second quest, after first, after second, both)
 2142: (2142, 2203, "Thank you for the compass, %s. One more thing: the Sea Golem in the drowned village's flooded chapel has my silver net. Bring it back!",
        "My net - thank you, %s! Captain Morrow's compass is still out there, on his sunk ship in the drowned village.",
        "The sea is quieter thanks to you, %s. Mind the nets on your way out."),
 2143: (2143, 2204, "The hex-doll burned well, %s. Now Maud's herb pouch: a sea hag stole it, and lurks on the drowned village's shore.",
        "Thank you for the herbs, %s. Maud's hex-doll still curses us - she has it on her island in the drowned village.",
        "The Light keep you, %s. Fenwatch sleeps easier now that Maud is gone."),
 2144: (2144, 2271, "Ulfgar's torc - well done, %s. Now the Broodmother: bring me her crown from the hatcheries south of town.",
        "The Broodmother's crown - well done, %s. Now old Ulfgar: bring me his torc from the Barrow Hills north of town.",
        "Fenwatch owes you a great deal, %s. Beyond the hatcheries a pass climbs to Stonehold - they could use you there."),
 2277: (2277, 2317, "That Heart still burns, %s. Now the big one: the Brass Colossus in the Foundry's casting pit. Bring me its core.",
        "The Colossus Core - you mad fool, %s. Its Forgemaster still has the Foundry Heart, in his forge. Bring it to me.",
        "The Foundry is quiet at last, %s. Stonehold is in your debt."),
}
# Varo (the Ashen Fields, Nov 18): his templates from the area's made.json
import json
_AF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ashen_fields', 'made.json')
if os.path.exists(_AF):
    _q = json.load(open(_AF))['quests']
    PAIRS[_q['varo_ember']] = (_q['varo_ember'], _q['varo_veil'],
        "The Ember burns in my temple now, %s. Last, Ashra the Cinder Witch: her hollow lies at the end of the canyon's long north-west ravine.",
        "Ashra's veil - well done, %s. Now the Flame Lord: his cavern lies at the canyon's far south end, past the Smoking Steps.",
        "The ash lies still at last, %s. Go with my blessing.")
# Rhea (the Gargoyle Spires, Nov 19): her templates from the area's made.json
_GS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'gargoyle_spires', 'made.json')
if os.path.exists(_GS):
    _q = json.load(open(_GS))['quests']
    PAIRS[_q['rhea_clapper']] = (_q['rhea_clapper'], _q['rhea_eye'],
        "The bell stays silent now, %s. Last, Shrike their matriarch: her eyrie is at the Spires' far south end. Bring me her eye.",
        "Shrike is dead - well done, %s! The Bellkeeper still has the bell's clapper, in the ruined tower at the Spires' north end.",
        "The Spires are quiet at last, %s. The road to the Last Bastion lies open - go well.")
# Brother Anselm (the Monastery, Nov 19)
_MO = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'monastery', 'made.json')
if os.path.exists(_MO):
    _q = json.load(open(_MO))['quests']
    PAIRS[_q['anselm_beads']] = (_q['anselm_beads'], _q['anselm_sash'],
        "The Abbot rests at last, %s. Now Master Kesh: his Hall of the Silent Hand is at the north end. Bring me his sash.",
        "Kesh's sash - the Hand is broken, %s. The Fallen Abbot still holds his prayer beads, in the Sanctum at the south end.",
        "The monastery is still again, %s - the right kind of still. The Light keep you.")
qs, npcs = W.talk_load()
for npc, (a, b, ta, tb, both) in PAIRS.items():
    keep = [e for e in npcs.get(npc, []) if not (e.get('when') == 'near' and any(c.get('type') == 'done' for c in e.get('conds', [])))]
    npcs[npc] = [near([d(a, '>=', 1), d(b, '>=', 1)], both), near([d(a, '>=', 1), d(b, '=', 0)], ta), near([d(b, '>=', 1), d(a, '=', 0)], tb)] + keep
    for s in (ta, tb, both): assert len(s) <= 150, (npc, len(s), s)
# Huntmaster Edda: after Greyfang's fang (once), she still buys heads
npcs[2098] = [near([d(2100, '>=', 1)], "Greyfang is gone - well done, %s. I still pay for every wolf and dire wolf head from the Wolfwood.")] + \
             [e for e in npcs.get(2098, []) if not (e.get('when') == 'near' and any(c.get('type') == 'done' for c in e.get('conds', [])))]
W.talk_save(qs, npcs); print('what-next lines for', sorted(list(PAIRS) + [2098]))
