#!/usr/bin/env python3
"""Nov 16: Mirela, the rat-catcher of Aston, in her house (525,467; the hole there at 528,465 lands in the ratling
cellar), and her quest: the Broodmother's Tail (the Ratling Broodmother carries it) for the Rat-Catcher's Ring
(+1 Agility). Once; Lance Corporal and up; 200 exp (a standard quest: 5% of the Lance Corporal climb); no gold (Cody's
rule: an item reward pays no gold). Sprites 44522 (tail), 44523 (ring) in Client\\GFX.
    mirela.py <.dat folder>      (the game stopped: stop-send; then update-world, reload-editor)"""
import sys, os, json, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); DAT = sys.argv[1]
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
M = json.load(open(os.path.join(HERE, 'made.json')))
def made(o):
    W.apply([o], o.get('op')); assert W.made, o; return W.made[1]
LABY = 1 << 30
def item(src, name, desc, clear=0, **f):
    t = made({'op': 'itempnew', 'from': src, 'name': name})
    f['description'] = desc
    f['flags'] = W.itemp(t)['flags'] & ~(LABY | clear)
    W.apply([{'op': 'itempset', 't': t, 'fields': f}], 'item'); return t
TAIL = item(2018, "Broodmother's Tail", "The long bald tail of the Ratling Broodmother. Mirela the rat-catcher wants it.", sprite=[44522, 0])
r = W.itemp(338); at = list(r['attrib']); at[3 * 3] = 1          # Agility, when worn
RING = item(338, "Rat-Catcher's Ring", "A plain silver ring set with two little green stones. Mirela wore it for thirty years of rat-catching.",
            clear=(1 << 9) | (1 << 10), sprite=[44523, 0], driver=0, attrib=at, data=[0] * 10)
# the Broodmother carries the tail
bm = M['broodmother']; it = list(me.tpl_read(W.tchar, bm * me.CHAR_SIZE, me.CT_FIELDS)['item'])
it[it.index(0)] = TAIL
W.apply([{'op': 'ctempset', 't': bm, 'fields': {'item': it}, 'respawn': True}], 'Broodmother tail')
# Mirela: a woman (Inga's look and kind), like Huntmaster Edda
inga = me.tpl_read(W.tchar, 50 * me.CHAR_SIZE, me.CT_FIELDS)
MIR = made({'op': 'ctempnew', 'from': 25, 'name': 'Mirela'})
dd = list(me.tpl_read(W.tchar, MIR * me.CHAR_SIZE, me.CT_FIELDS)['data'])
for i in list(range(10, 24)) + list(range(32, 36)) + [29, 41]: dd[i] = 0
dd[49], dd[50], dd[51], dd[66], dd[37], dd[72] = TAIL, 0, 200, RING, 1, 0
W.apply([{'op': 'ctempset', 't': MIR, 'fields': {'data': dd, 'item': [0] * 40, 'sprite': inga['sprite'], 'kindred': inga['kindred'], 'alignment': 10000,
          'description': "Mirela, Aston's old rat-catcher: grey-haired, sharp-eyed, with a cudgel by the door and a hole in her floor."},
          'text': ['Hah!', 'Get out of my house, %s!',
                   "Welcome, %s. Ratlings nest under my house - down that hole. Bring me the Broodmother's tail and my old ring is yours."],
          'respawn': False}], 'Mirela')
print('Mirela', MIR, W.apply([{'op': 'npcplace', 't': MIR, 'x': 525, 'y': 468, 'dir': 2}], 'place Mirela')[1])
qs, npcs = W.talk_load()
top = max([v for v in qs['order'].values() if v > 0] or [0])
qs['order'][MIR] = top + 1
qs['qrew'][MIR] = {'lim': 1, 'first': 0, 'gold': 0, 'st': [], 'rmin': 2, 'rmax': -1, 'n': 1}
print(W.talk_save(qs, npcs))
print('tail', TAIL, 'ring', RING, W.save())
M.update({'tail': TAIL, 'ring': RING, 'mirela': MIR})
json.dump(M, open(os.path.join(HERE, 'made.json'), 'w'), indent=1)
