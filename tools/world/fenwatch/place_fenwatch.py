#!/usr/bin/env python3
"""Fenwatch's people (Nov 16): the quest givers (greetings only for now; their quests come with their areas), the
innkeeper, two merchants, eight gate guards, and the waypoint on the market square.

    place_fenwatch.py <.dat folder>     (game stopped; uses the MyV2 Editor's World class)

Writes made.json (template numbers). Looks are the game's own (sprite + kindred taken from an Aston NPC)."""
import sys, os, json, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); DAT = sys.argv[1]
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/MyV2/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
def made(o):
    W.apply([o], o.get('op')); assert W.made, o; return W.made[1]
def tc(t): return me.tpl_read(W.tchar, t * me.CHAR_SIZE, me.CT_FIELDS)
def look(t): f = tc(t); return {'sprite': f['sprite'], 'kindred': f['kindred']}
JAMIL, INGA, SERENA, SIRJAN, STEVEN, HOLLIS, BRUNHILD, MERCHANT, CITYGUARD = 25, 50, 109, 28, 91, 2006, 65, 835, 2006
def place(t, x, y, d):
    n, msgs = W.apply([{'op': 'npcplace', 't': t, 'x': x, 'y': y, 'dir': d}], 'place')
    for m in msgs: print('  !', m)
def giver(name, like, x, y, d, greet, desc, shout='Guards! Guards!'):
    """a friendly quest giver without a quest yet (data 49 wanted item, 51 exp, 66 reward: set when its quest is made)"""
    t = made({'op': 'ctempnew', 'from': JAMIL, 'name': name})
    dd = list(tc(t)['data'])
    for i in list(range(10, 24)) + list(range(32, 36)) + [29, 41]: dd[i] = 0
    dd[49], dd[50], dd[51], dd[66], dd[37], dd[72] = 0, 0, 0, 0, 1, 0
    f = {'data': dd, 'item': [0] * 40, 'alignment': 10000, 'description': desc}; f.update(look(like))
    W.apply([{'op': 'ctempset', 't': t, 'fields': f, 'text': ['Hah!', shout, greet], 'respawn': False}], name)
    place(t, x, y, d); return t
def merchant(name, like, x, y, d, stock, greet, desc):
    t = made({'op': 'ctempnew', 'from': MERCHANT, 'name': name})
    dd = list(tc(t)['data'])
    for i in list(range(0, 24)) + list(range(32, 36)) + [29, 41]: dd[i] = 0
    for i, s in enumerate(stock[:10]): dd[i] = s
    f = {'data': dd, 'item': list(stock[:40]) + [0] * (40 - len(stock[:40])), 'description': desc}; f.update(look(like))
    W.apply([{'op': 'ctempset', 't': t, 'fields': f, 'text': ['Hah!', 'Thief! Guards!', greet], 'respawn': False}], name)
    place(t, x, y, d); return t
def guard(x, y, d):
    t = made({'op': 'ctempnew', 'from': CITYGUARD, 'name': 'Fenwatch Guard'})
    dd = list(tc(t)['data'])
    for i in list(range(10, 24)) + list(range(32, 36)) + [29, 41]: dd[i] = 0
    W.apply([{'op': 'ctempset', 't': t, 'fields': {'data': dd, 'description': 'A guard of Fenwatch in a mud-spattered cloak, watching the marsh.'},
              'text': ['The marsh takes another.', 'To arms! Hold the gate!', 'Keep to the roads out there, %s. The fen swallows the careless.'], 'respawn': False}], 'guard')
    place(t, x, y, d); return t

# NPCs can't stand on tavern tiles (god_drop_char refuses MF_TAVERN): the innkeeper's and Petra's corners of the inn are not tavern
if '--no-flags' not in sys.argv:
    W.apply([{'op': 'flag', 'x': x, 'y': y, 'bit': 7, 'mode': 0} for x0, y0, x1, y1 in ((430, 781, 431, 786), (438, 775, 440, 777))
             for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)], 'inn corners')
if '--flags-only' in sys.argv:
    print(W.save()); sys.exit()
M = {}
M['joss'] = giver('Joss', JAMIL, 457, 809, 2, "Mind the nets, %s. I'm Joss. I fished the eastern shore until the sea took the village there - and the drowned do not rest. Come back when you are ready to go east.",
                  'A weathered fisherman with rope-scarred hands, mending a net.')
M['ilse'] = giver('Ilse', INGA, 433, 811, 2, 'The Light keep you, %s. I am Ilse, priestess of Fenwatch. Something foul stirs in the bog to the east; I may need a strong arm soon.',
                  'The priestess of Fenwatch, in a plain grey robe, a silver sun at her throat.')
M['aldous'] = giver('Aldous', HOLLIS, 433, 827, 2, 'Welcome to Fenwatch, %s. I am Aldous, the reeve. The barrows to the north and the lizards to the south give us no peace. I will have work for you.',
                    'The reeve of Fenwatch: a broad, tired man who keeps the town and its palisade standing.')
M['petra'] = giver('Petra', SERENA, 438, 776, 3, 'Oh! A visitor, %s. I am Petra, a scholar of the old kings. The barrows north of here are full of their writing - if only someone dared go in.',
                   'A travelling scholar at a table covered in notes and rubbings of old runes.')
M['rook'] = giver('Rook', SIRJAN, 469, 779, 3, "Don't touch anything, %s. I am Rook. The lizards' archmages brew things I would give a great deal to study. Another day, perhaps.",
                  'The alchemist of Fenwatch, thin and stained to the elbows, smelling of sulphur and marsh herbs.')
M['bounty'] = giver('Bounty Master Corwin', STEVEN, 436, 793, 2, 'Fenwatch pays for what crawls out of the marsh, %s. The bounty lists are not posted yet - come back soon.',
                    'The keeper of the Fenwatch Bounty Office, a one-eyed old soldier with a ledger and a strongbox.')
M['innkeeper'] = merchant('Marta', BRUNHILD, 431, 782, 2, [1141, 1142, 1143], "Welcome to the Heron, %s. Sit, drink, and dry your boots.",
                          'Marta keeps the Heron, the inn of Fenwatch, and stands for no trouble in it.')
M['store'] = merchant('Odger', MERCHANT, 460, 779, 4, [91, 93, 100, 101, 102, 127, 131], 'Torches, flasks, potions - all a traveller needs in the fen, %s.',
                      'Odger, the storekeeper of Fenwatch.')
SMITH = [28, 32, 36, 29, 33, 37, 30, 34, 38, 1365, 1366, 1367, 69, 70, 71, 72, 73, 74]
M['smith'] = merchant('Brigit', STEVEN, 460, 791, 4, SMITH, 'Good steel does not rust if you oil it, %s. Even here.',
                      'Brigit, the smith of Fenwatch, soot to the eyebrows.')
M['guards'] = [guard(x, y, d) for x, y, d in ((447, 771, 4), (451, 771, 4), (447, 833, 3), (451, 833, 3), (425, 799, 1), (425, 803, 1), (475, 799, 2), (475, 803, 2))]
print(W.save())
# merchants.dat (the editor's Merchants tab; the server reads it at start / "merchreload")
p = os.path.join(DAT, 'merchants.dat'); s = open(p, encoding='latin-1').read().rstrip('\n') + '\n# Fenwatch (Nov 16)\n'
for k, kinds, stock in (('innkeeper', 8, [1141, 1142, 1143]), ('store', 8, [91, 93, 100, 101, 102, 127, 131]), ('smith', 3, SMITH)):
    s += 'merchant %d sell 0 buy 0 gold 0 kinds %d\nstock %d %s\n' % (M[k], kinds, M[k], ' '.join(map(str, stock)))
open(p, 'w', encoding='latin-1').write(s)
# the waypoint on the market square (the game lays its nine ground pieces itself)
p = os.path.join(DAT, 'waypoints.dat'); L = open(p, encoding='latin-1').read().rstrip('\n').split('\n')
nxt = next(int(l.split()[1]) for l in L if l.startswith('next '))
L = ['next %d' % (nxt + 1) if l.startswith('next ') else l for l in L] + ['wp %d 449 801 0 0 Fenwatch|Marsh town east of the Wolfwood' % nxt]
open(p, 'w', encoding='latin-1').write('\n'.join(L) + '\n'); M['waypoint'] = nxt
json.dump(M, open(os.path.join(HERE, 'made.json'), 'w'), indent=1); print(M)
