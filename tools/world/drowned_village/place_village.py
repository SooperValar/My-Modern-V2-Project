#!/usr/bin/env python3
"""The Drowned Village's monsters, items and quests (Nov 16).

    place_village.py <.dat folder> [--seed N]     (game stopped; uses the MyV2 Editor's World class)

Monsters (group 34): Drowned Sailors (Sergeant Major; the Undead 328, look 50000), Bog-men (Second Lieutenant; 328
scaled up, look 50500), Sea Golems in the flooded chapel (Second Lieutenant; Golem 460 scaled down, look 51000),
Captain Morrow on his wreck, Maud the Bog Witch in her hut. Quests on Fenwatch's Joss, Ilse and Bounty Master Corwin
(found by name: Cody may have moved them). Writes made.json."""
import sys, os, random, json, math, struct, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); DAT = sys.argv[1]
random.seed(int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1119)
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/MyV2/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
def made(o):
    W.apply([o], o.get('op')); assert W.made, o; return W.made[1]
def tc(t): return me.tpl_read(W.tchar, t * me.CHAR_SIZE, me.CT_FIELDS)
def rank_of(t): return me.RANKS[me.points2rank(struct.unpack_from('<i', W.tchar, t * me.CHAR_SIZE + 709)[0])]
LABY = 1 << 30; SK_SWIM, SK_MEDIT = 10, 30; GROUP = 34
# ---------------------------------------------------------------- items
def item(src, name, desc, clear=0, **f):
    t = made({'op': 'itempnew', 'from': src, 'name': name})
    f['description'] = desc; f['flags'] = W.itemp(t)['flags'] & ~(LABY | clear)
    W.apply([{'op': 'itempset', 't': t, 'fields': f}], 'item'); return t
FANG, SILVER_RING, BELT_SRC, MANA_POTION = 2018, 338, 2004, 102          # quest item (can't be sold: value 0), ring, belt, potion to copy
SHEAD = item(FANG, 'Drowned Sailor Head', 'The bloated grey-green head of a drowned sailor. The Fenwatch Bounty Office pays for these.', sprite=[44524, 0], value=0)
BHEAD = item(FANG, 'Bog-man Head', 'The head of a bog-man, brown as peat. The Fenwatch Bounty Office pays for these.', sprite=[44525, 0], value=0)
COMPASS = item(FANG, "Captain Morrow's Compass", 'A brass ship\'s compass, green with salt. "Morrow" is scratched into the lid. Joss of Fenwatch wants it.', sprite=[44526, 0], value=0)
DOLL = item(FANG, "Maud's Hex-Doll", 'A doll of straw and bog-reed, stuck with fish bones. It belonged to Maud the Bog Witch. Ilse of Fenwatch wants it destroyed.', sprite=[44527, 0], value=0)
NET = item(FANG, 'Silver Net', "A fishing net of fine silver thread, from the drowned village's chapel. Joss of Fenwatch wants it.", sprite=[44528, 0], value=0)
POUCH = item(FANG, "Maud's Herb Pouch", "A pouch of the Bog Witch's marsh herbs. Ilse of Fenwatch can make something better of them.", sprite=[44529, 0], value=0)
sk = [0] * 150; sk[SK_MEDIT * 3] = 4
RING = item(SILVER_RING, 'Ring of Tides', 'A ring of pale blue metal. Mana rises in its wearer like the tide.', clear=(1 << 9) | (1 << 10),
            sprite=[44530, 0], driver=0, data=[0] * 10, attrib=[0] * 15, hp=[0, 0, 0], end=[0, 0, 0], mana=[15, 0, 0], skill=sk, min_rank=8, value=5000)
sk = [0] * 150; sk[SK_SWIM * 3] = 8
FBELT = item(BELT_SRC, "Fisher-King's Belt", 'A belt of sealskin with a buckle shaped like a leaping fish.',
             sprite=[44531, 0], attrib=[0] * 15, hp=[25, 0, 0], end=[0, 0, 0], mana=[0, 0, 0], skill=sk, min_rank=9, value=8000)
CLEAR = item(MANA_POTION, 'Draught of Clear Water', 'Water so clear it seems to glow. It gives a caster back all of their mana.',
             hp=[0, 0, 0], end=[0, 0, 0], mana=[999, 0, 0], sprite=[44532, 0], value=800)
# ---------------------------------------------------------------- monsters
def scaled(src, pct):
    f = tc(src); a = list(f['attrib']); hp = list(f['hp']); en = list(f['end']); mn = list(f['mana']); s = list(f['skill'])
    for i in range(5): a[i * 6] = max(1, round(a[i * 6] * pct / 100))
    hp[0] = round(hp[0] * pct / 100); en[0] = round(en[0] * pct / 100); mn[0] = round(mn[0] * pct / 100)
    for i in range(50): s[i * 6] = min(255, round(s[i * 6] * pct / 100))
    return {'attrib': a, 'hp': hp, 'end': en, 'mana': mn, 'skill': s}
def npc(src, name, pct, x, y, d=None, items=(), text=None, desc=None, sprite=None):
    t = made({'op': 'ctempnew', 'from': src, 'name': name})
    f = scaled(src, pct) if pct != 100 else {}
    dd = list(tc(t)['data'])
    for i in list(range(10, 24)) + list(range(32, 36)) + [29, 41]: dd[i] = 0
    dd[42] = dd[44] = GROUP
    f['data'] = dd; f['item'] = list(items) + [0] * (40 - len(items))
    if desc is not None: f['description'] = desc
    if sprite: f['sprite'] = sprite
    W.apply([{'op': 'ctempset', 't': t, 'fields': f, 'text': text or [], 'respawn': False}], 'npc')
    n, msgs = W.apply([{'op': 'npcplace', 't': t, 'x': x, 'y': y, 'dir': d or random.choice([1, 2, 3, 4])}], 'place')
    for m in msgs: print('  !', m)
    return t
used = set()
def free(x, y):
    t = W.tile(x, y)
    return not t[1] and not t[2] and not t[4] and not (t[7] & 1) and not (t[7] & (1 << 7)) and (x, y) not in used
def spots(n, ok, box, apart):
    out = []; tries = 0
    while len(out) < n and tries < 20000:
        tries += 1
        x, y = random.randint(box[0], box[2]), random.randint(box[1], box[3])
        if free(x, y) and ok(x, y) and all(abs(x - a) + abs(y - b) >= apart for a, b in out): out.append((x, y)); used.add((x, y))
    assert len(out) == n, (n, len(out)); return out
dry = lambda x, y: not (W.tile(x, y)[7] & (1 << 3)) and W.tile(x, y)[0] not in (16933, 16957, 16958, 16959)
ell = lambda x, y, cx, cy, rx, ry: ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0
SAILOR_TXT = ['The sea keeps what it takes.', 'Come down... come down with us, %s...']
D_SAILOR = 'A sailor of the drowned village, grey-green and dripping, still in the rags of his oilskins.'
sailors = [npc(328, 'Drowned Sailor', random.choice([95, 100, 100, 105]), x, y, items=[SHEAD], text=SAILOR_TXT, desc=D_SAILOR, sprite=50000)
           for x, y in spots(18, lambda x, y: dry(x, y) and not ell(x, y, 434, 905, 19, 21) and not (452 <= x <= 470 and 882 <= y <= 914), (422, 858, 498, 900), 6)]
sailors += [npc(328, 'Drowned Sailor', 105, x, y, items=[SHEAD], text=SAILOR_TXT, desc=D_SAILOR, sprite=50000)
            for x, y in spots(4, lambda x, y: dry(x, y) and not ell(x, y, 490, 917, 3.2, 7.5), (478, 904, 498, 921), 4)]
BOG_TXT = ['Back to the peat with you.', 'The bog wants %s...']
bogmen = [npc(328, 'Bog-man', random.choice([106, 110, 114]), x, y, items=[BHEAD], text=BOG_TXT, sprite=50500,
              desc='A thing of peat and old bones that has pulled itself out of the bog. It moves slowly, and hits like a falling tree.')
          for x, y in spots(14, lambda x, y: dry(x, y) and ell(x, y, 434, 905, 20, 22) and not ell(x, y, 433, 906, 7.5, 8.5), (416, 884, 456, 926), 4)]
GOLEM_TXT = ['The tide returns.', 'None pass the water, %s.']
D_GOLEM = 'A golem of sea-stone and shell, set to guard the chapel long before the water came. It does not need to breathe.'
wet = lambda x, y: bool(W.tile(x, y)[7] & (1 << 3))
golems = [npc(460, 'Sea Golem', 72, x, y, items=[], text=GOLEM_TXT, desc=D_GOLEM, sprite=51000) for x, y in spots(5, lambda x, y: wet(x, y) and not (458 <= x <= 464 and 904 <= y <= 909), (455, 897, 467, 911), 4)]
SENTINEL = npc(460, 'Sea Golem Sentinel', 72 + 6, 461, 906, d=4, items=[NET], text=['The net stays.', 'You will not take it, %s.'], sprite=51000,
               desc='The largest of the chapel\'s golems stands before the altar. A net of silver thread is wound around its arm.')
MORROW = npc(336, 'Captain Morrow', 90, 490, 917, d=4, items=[COMPASS], text=['Back to your post, sailor.', 'All hands! Repel boarders! Drown that one - %s!'], sprite=50000,
             desc='The drowned captain of the wreck on the shore, a rusted cutlass in his hand and a brass compass on a chain at his belt.')
MAUD = npc(1012, 'Maud the Bog Witch', 125, 433, 906, d=3, items=[DOLL, POUCH], text=['Into the pot with you, dearie.', 'A visitor! The bog is hungry, %s, and so am I!'],
           desc='An old woman in a cloak of wet reeds, her hair full of fish bones. A straw doll hangs from her belt.')
for n, t in (('sailor', sailors[0]), ('bog-man', bogmen[0]), ('sea golem', golems[0]), ('sentinel', SENTINEL), ('morrow', MORROW), ('maud', MAUD)): print('  %-10s %d %s' % (n, t, rank_of(t)))
# ---------------------------------------------------------------- quests (Fenwatch's givers, by name)
def by_name(name):
    c = [t for t in range(1, len(W.tchar) // me.CHAR_SIZE) if W.tchar[t * me.CHAR_SIZE] and tc(t)['name'] == name and tc(t)['x']]
    assert c, 'no placed NPC called ' + name; return c[-1]
JOSS, ILSE, CORWIN = by_name('Joss'), by_name('Ilse'), by_name('Bounty Master Corwin')
def quest(t, want, skill, exp, give, greet):
    dd = list(tc(t)['data']); dd[49], dd[50], dd[51], dd[66], dd[37], dd[72] = want, skill, exp, give, 1, 0
    W.apply([{'op': 'ctempset', 't': t, 'fields': {'data': dd}, 'text': [None, None, greet], 'respawn': True}], 'quest')
def extra(of, want, exp, give):
    t = made({'op': 'ctempnew', 'from': of, 'name': tc(of)['name']})
    dd = list(tc(of)['data']); dd[49], dd[50], dd[51], dd[66] = want, 0, exp, give
    W.apply([{'op': 'ctempset', 't': t, 'fields': {'data': dd}, 'text': [None, None, ''], 'respawn': False}], 'extra quest'); return t
quest(JOSS, COMPASS, SK_SWIM, 16000, 0, "Mind the nets, %s. Captain Morrow went down with his ship off the drowned village, east of here - and still walks its deck. Bring me his compass and I will teach you to swim. And there is a silver net in the flooded chapel I would give a great deal for.")
quest(ILSE, DOLL, 0, 16000, RING, "The Light keep you, %s. Maud the Bog Witch curses this town from her island in the drowned village. Bring me her hex-doll, that I may burn it. And bring her herb pouch: I can make clean draughts of what she uses for poison.")
quest(CORWIN, SHEAD, 0, 2500, 0, "Fenwatch pays for what crawls out of the marsh, %s: every drowned sailor's head and every bog-man's head, as many as you bring.")
JOSS_NET, ILSE_POUCH, CORWIN_BOG = extra(JOSS, NET, 25000, FBELT), extra(ILSE, POUCH, 0, CLEAR), extra(CORWIN, BHEAD, 2500, 0)
qs, npcs = W.talk_load()
for a, of in ((JOSS_NET, JOSS), (ILSE_POUCH, ILSE), (CORWIN_BOG, CORWIN)): qs['alias'][a] = of
top = max([v for v in qs['order'].values() if v > 0] or [0])
for k, t in enumerate((JOSS, ILSE, ILSE_POUCH, JOSS_NET, CORWIN, CORWIN_BOG)): qs['order'][t] = top + 1 + k
R = lambda lim, gold, rmin, n=1: {'lim': lim, 'first': 0, 'gold': gold, 'st': [], 'rmin': rmin, 'rmax': -1, 'n': n}
qs['qrew'][JOSS] = R(1, 0, 8); qs['qrew'][ILSE] = R(1, 0, 8); qs['qrew'][ILSE_POUCH] = R(1, 0, 8, 3); qs['qrew'][JOSS_NET] = R(1, 0, 9)
qs['qrew'][CORWIN] = R(0, 1250, 9); qs['qrew'][CORWIN_BOG] = R(0, 1250, 9)      # 12.5G: 1/200 of the exp (Cody, Nov 17; was 125G)
print(W.talk_save(qs, npcs)); print(W.save())
M = {'items': {'sailor_head': SHEAD, 'bogman_head': BHEAD, 'compass': COMPASS, 'doll': DOLL, 'net': NET, 'pouch': POUCH, 'ring': RING, 'belt': FBELT, 'clear_water': CLEAR},
     'sailors': sailors, 'bogmen': bogmen, 'golems': golems, 'sentinel': SENTINEL, 'morrow': MORROW, 'maud': MAUD,
     'quests': {'joss': JOSS, 'joss_net': JOSS_NET, 'ilse': ILSE, 'ilse_pouch': ILSE_POUCH, 'corwin': CORWIN, 'corwin_bog': CORWIN_BOG}}
json.dump(M, open(os.path.join(HERE, 'made.json'), 'w'), indent=1); print(M['items'], M['quests'])
