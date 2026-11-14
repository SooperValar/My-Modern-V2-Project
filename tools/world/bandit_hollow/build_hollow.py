#!/usr/bin/env python3
"""Bandit Hollow (Nov 14): the east road out of Aston and the bandit camp at its end.

    build_hollow.py <.dat folder> [--seed N]     (game stopped; uses the MyV2 Editor's World class)

Writes map, items, NPC and item templates through the editor's own edit operations, then saves (the editor
keeps a backup in .dat/mapedit-backups). Prints the template numbers it made and writes
bandit_hollow_talk.txt (the npctalk.dat lines, with the real template numbers) next to this script.
Map: x grows down-right (south on screen), y grows up-right (east)."""
import sys, os, random, json, importlib.util, struct
HERE = os.path.dirname(os.path.abspath(__file__))
DAT = sys.argv[1]
SEED = int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 1114
random.seed(SEED)
ED = os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py'))
spec = importlib.util.spec_from_file_location('mapedit', ED); me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
OPS = []
def op(**k): OPS.append(k)
def run(label):
    global OPS
    n, msgs = W.apply(OPS, label)
    for m in msgs: print('  !', m)
    OPS = []
    return n
def made(o):
    W.apply([o], o.get('op'))
    assert W.made, o
    return W.made[1]

# ---------------------------------------------------------------- area
X0, X1, Y0, Y1 = 498, 572, 662, 748            # the hollow (forest around a clearing)
GATE = (533, 601)                               # Aston's east gate
TREES = [1238, 1240, 1112, 1114, 880, 882]
FOREST = 1118; DIRT = 989
TIMBER = [36060, 36061, 36062, 36063]; STONE = [36070, 36071, 36072, 36073]
OAK = [37000, 37001, 37002, 37003]
blocked = set()          # tiles that must stay free of trees
def keep(x0, y0, x1, y1, pad=0):
    for x in range(x0 - pad, x1 + pad + 1):
        for y in range(y0 - pad, y1 + pad + 1): blocked.add((x, y))

# the trail: from the gate across the field and into the camp gate (a gentle wiggle, 3 wide)
trail = []
import math
for y in range(603, 700):
    cx = 533 + int(round(1.6 * math.sin((y - 603) / 9.0)))
    for x in range(cx - 1, cx + 2): trail.append((x, y))
for p in trail: blocked.add(p)
# buildings and the camp
HUT = (540, 674, 546, 681)            # Wynn's hut (x0,y0,x1,y1), door on its north wall
CAMP = (514, 692, 556, 740)           # palisade
STORE = (516, 700, 523, 710)          # the quartermaster's storehouse, door on its south wall
POISON = (548, 699, 554, 706)         # the poisoner's hut, door on its north wall
LODGE = (525, 726, 545, 738)          # Red Harlan's lodge (fieldstone), door on its west wall
keep(*HUT, pad=2); keep(*CAMP, pad=2); keep(540, 683, 547, 688)   # garden
keep(526, 604, 541, 610)              # Hollis and Tobias by the gate

# ground and trees in the hollow
for x in range(X0, X1 + 1):
    for y in range(Y0, Y1 + 1):
        d = min(x - X0, X1 - x, Y1 - y, 99)               # the west side opens into the field
        dw = y - Y0
        p = 0.95 if d <= 2 else 0.55 if d <= 5 else 0.10 if d <= 9 else 0.02
        if dw <= 3 and d > 2: p = min(p, 0.05)
        op(op='floor', x=x, y=y, s=DIRT if random.random() < 0.05 else FOREST, set=False)
        if (x, y) not in blocked and random.random() < p:
            op(op='object', x=x, y=y, s=random.choice(TREES), block=3)
        else:
            op(op='erase', x=x, y=y)
# the trail
for x, y in trail:
    op(op='floor', x=x, y=y, s=DIRT, set=False); op(op='erase', x=x, y=y)
run('Bandit Hollow: ground, trees, trail')

def walls(box, sprites, door_side, door_at):
    x0, y0, x1, y1 = box
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            edge = x in (x0, x1) or y in (y0, y1)
            if edge:
                op(op='floor', x=x, y=y, s=random.choice(OAK), set=False)
                op(op='object', x=x, y=y, s=random.choice(sprites), block=3)
                op(op='flag', x=x, y=y, bit=2, mode=1)
            else:
                op(op='erase', x=x, y=y); op(op='floor', x=x, y=y, s=random.choice(OAK), set=False)
                op(op='flag', x=x, y=y, bit=2, mode=1)      # indoors (MF_INDOORS = 1<<2)
    run('walls')
    dx, dy = door_at
    op(op='erase', x=dx, y=dy)
    # a wall along y (x fixed: north / south wall) takes door I, a wall along x takes door II
    op(op='place', x=dx, y=dy, t=1440 if door_side in ('n', 's') else 1441, fresh=1)
    run('door')

# camp ground: dirt-heavy inside the palisade
x0, y0, x1, y1 = CAMP
for x in range(x0, x1 + 1):
    for y in range(y0, y1 + 1):
        op(op='floor', x=x, y=y, s=DIRT if random.random() < 0.45 else FOREST, set=False); op(op='erase', x=x, y=y)
run('camp ground')
# the palisade: wooden fence (1172 along one axis, 1174 the other; corners 1176-1182), the gate in the west side
FENCE_X, FENCE_Y = 1172, 1174
gate = set((x, y0) for x in range(531, 536))
for x in range(x0, x1 + 1):
    for y in (y0, y1):
        if (x, y) not in gate: op(op='object', x=x, y=y, s=FENCE_Y, block=1)
for y in range(y0 + 1, y1):
    for x in (x0, x1): op(op='object', x=x, y=y, s=FENCE_X, block=1)
for (x, y), s in {(x0, y0): 1176, (x0, y1): 1178, (x1, y1): 1180, (x1, y0): 1182}.items():
    op(op='object', x=x, y=y, s=s, block=1)
run('palisade')
walls(HUT, TIMBER, 'n', (HUT[0], 677))
walls(STORE, TIMBER, 's', (STORE[2], 705))
walls(POISON, TIMBER, 'n', (POISON[0], 702))
walls(LODGE, STONE, 'w', (531, LODGE[1]))
SHACKS = [(515, 715, 520, 721), (549, 721, 554, 727)]
walls(SHACKS[0], TIMBER, 's', (SHACKS[0][2], 718))
walls(SHACKS[1], TIMBER, 'n', (SHACKS[1][0], 724))

# furniture, fires, lights
PLACE = [
    (1148, 529, 712), (1148, 543, 716), (1148, 536, 699),            # campfires
    (764, 530, 690), (764, 536, 690),                                 # torches at the camp gate
    (82, 518, 703), (83, 518, 707), (298, 551, 704),                  # tables
    (741, 527, 728), (741, 543, 728), (741, 527, 736), (741, 543, 736),  # fire bowls in the lodge
    (299, 539, 736), (82, 542, 680), (1132, 541, 675),
]
# loose pieces drawn into the tile: barrels by the storehouse, logs and stumps to sit on around the fires
PIECES = [(16882, 525, 701), (16882, 525, 702), (16882, 524, 708), (16882, 515, 711), (16882, 546, 708),
          (38164, 531, 711), (38166, 527, 713), (38165, 529, 714), (38164, 541, 715), (38167, 545, 717), (38166, 543, 718),
          (38165, 535, 698), (38164, 538, 700), (16882, 516, 719), (16882, 553, 726)]
for s_, x, y in PIECES: op(op='object', x=x, y=y, s=s_, block=1)
for t, x, y in PLACE: op(op='place', x=x, y=y, t=t, fresh=1)
for x in range(541, 547):            # Wynn's herb garden: flowers to pick
    for y in range(684, 688):
        if random.random() < 0.5: op(op='place', x=x, y=y, t=random.choice([16, 45, 137]), fresh=1)
run('furniture')

# safe spots: Wynn's hut and garden, and where Hollis and Tobias stand, take no monsters
for x in range(HUT[0], HUT[2] + 1):
    for y in range(HUT[1], 688):
        op(op='flag', x=x, y=y, bit=5, mode=1)
run('no monsters at the hut')

# ---------------------------------------------------------------- items
def item(src, name, desc, **f):
    t = made({'op': 'itempnew', 'from': src, 'name': name})
    f['description'] = desc
    W.apply([{'op': 'itempset', 't': t, 'fields': f}], 'item')
    return t
HEAD = item(1270, "Red Harlan's Head", "The head of Red Harlan, chief of the bandits of the Hollow.")
LEDGER = item(1270, 'Stolen Ledger', "Tobias the merchant's ledger, stained with ale.", sprite=[16912, 0])
MOONWORT = item(1270, 'Bundle of Moonwort', 'Pale moonwort, tied with string. It smells bitter.', sprite=[1460, 0])
BELT = item(777, "Harlan's Studded Belt", 'A heavy leather belt studded with iron. It belonged to Red Harlan.',
            attrib=[0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0], hp=[0, 0, 0], end=[0, 0, 0], min_rank=4, value=1500)
SIGNET = item(362, "Merchant's Signet", "A merchant's gold signet ring. Traders take one look at it and lower their prices.",
              skill=[0] * 36 + [0] * 0 + [0] * 114, min_rank=5, value=1500)
skill = list(me.tpl_read(W.titem, SIGNET * me.ITEM_SIZE, me.IT_FIELDS)['skill']); skill = [0] * 150; skill[12 * 3] = 3
W.apply([{'op': 'itempset', 't': SIGNET, 'fields': {'skill': skill}}], 'signet')
SECOND = item(101, 'Potion of Second Wind', 'A herbal draught that gives a tired fighter back all of their endurance.',
              hp=[0, 0, 0], end=[999, 0, 0], sprite=[1795, 0], value=600)
print('items: head %d ledger %d moonwort %d belt %d signet %d second wind %d' % (HEAD, LEDGER, MOONWORT, BELT, SIGNET, SECOND))

# ---------------------------------------------------------------- NPCs
GROUP = 30
def scaled(src, pct):
    f = me.tpl_read(W.tchar, src * me.CHAR_SIZE, me.CT_FIELDS)
    a = list(f['attrib'])
    for i in range(5): a[i * 6] = max(1, round(a[i * 6] * pct / 100))
    hp = list(f['hp']); en = list(f['end']); mn = list(f['mana'])
    hp[0] = round(hp[0] * pct / 100); en[0] = round(en[0] * pct / 100); mn[0] = round(mn[0] * pct / 100)
    sk = list(f['skill'])
    for i in range(50): sk[i * 6] = min(255, round(sk[i * 6] * pct / 100))
    return {'attrib': a, 'hp': hp, 'end': en, 'mana': mn, 'skill': sk}
def npc(src, name, pct, x, y, d=4, items=(), text=None, extra=None, desc=None):
    t = made({'op': 'ctempnew', 'from': src, 'name': name})
    f = scaled(src, pct) if pct != 100 else {}
    dd = list(me.tpl_read(W.tchar, t * me.CHAR_SIZE, me.CT_FIELDS)['data'])
    for i in list(range(20, 24)) + list(range(32, 36)) + [41]: dd[i] = 0
    if src in (344,): dd[42] = dd[44] = GROUP
    for k, v in (extra or {}).items(): dd[k] = v
    f['data'] = dd
    if items: f['item'] = list(items) + [0] * (40 - len(items))
    if desc is not None: f['description'] = desc
    W.apply([{'op': 'ctempset', 't': t, 'fields': f, 'text': text or [], 'respawn': False}], 'npc')
    n, msgs = W.apply([{'op': 'npcplace', 't': t, 'x': x, 'y': y, 'dir': d}], 'place')
    for m in msgs: print('  !', m)
    return t
BANDIT_TEXT = ['Another fool for the ditch.', 'Your purse, %s, or your life!']
spots = [(518, 696, 85), (522, 714, 85), (527, 709, 85), (533, 714, 100), (531, 703, 85), (539, 700, 85), (540, 712, 100),
         (546, 712, 85), (549, 720, 100), (538, 721, 85), (522, 722, 100), (517, 730, 85), (552, 732, 100), (528, 694, 85),
         (538, 694, 85), (518, 718, 85), (551, 724, 85)]
bandits = [npc(344, 'Bandit', pct, x, y, d=random.choice([1, 2, 3, 4]), text=BANDIT_TEXT) for x, y, pct in spots]
QM = npc(344, 'Bandit Quartermaster', 110, 519, 705, d=1, items=[LEDGER], text=['Ha! Into the books with you.', 'Thief! Those are MY goods, %s!'])
PO = npc(344, 'Bandit Poisoner', 105, 551, 702, d=2, items=[MOONWORT], text=['Sleep well, %s.', 'A taste of my brew, %s?'])
GUARDS = [npc(344, "Harlan's Guard", 115, x, y, d=3, text=['The chief will hear of this.', 'Nobody sees the chief, %s!']) for x, y in ((529, 732), (541, 732))]
HARLAN = npc(344, 'Red Harlan', 160, 535, 733, d=3, items=[HEAD], text=['Hah! Bury that one with the rest.', "You've come a long way to die, %s!"],
             desc='A broad man with a red beard and a notched sword. The chief of the bandits of the Hollow.')
# quest givers: friendly, with their item quest (data 49 = the item they want, so the console's questgive can test them)
HOLLIS = npc(2006, 'Sergeant Hollis', 100, 530, 606, d=4, extra={49: HEAD, 37: 1},
             text=['Another one for the graveyard.', 'You will regret that, %s!', 'Hail, %s. Bandits hold the hollow down the east road. Their chief is Red Harlan - bring me his head!'],
             desc='A sergeant of the Cityguard, keeping watch on the east road.')
TOBIAS = npc(25, 'Tobias', 100, 539, 607, d=3, extra={49: LEDGER, 37: 1, 50: 0, 51: 0, 72: 0},
             text=['Ha!', 'Help! Thieves!', 'Ah, %s! Bandits robbed my wagon on the east road - they took my ledger. Bring it back and I will make it worth your while!'],
             desc='A travelling merchant whose wagon was robbed on the east road.')
WYNN = npc(25, 'Wynn', 100, 543, 678, d=1, extra={49: MOONWORT, 37: 1, 50: 0, 51: 0, 72: 0},
           text=['Ha!', 'Leave me be!', 'Welcome to my hut, %s. The bandits poison their blades with my moonwort - their Poisoner took my whole harvest. Will you get it back?'],
           desc='An old herbalist who lives at the edge of Bandit Hollow.')
for t in (TOBIAS, WYNN):
    W.apply([{'op': 'ctempset', 't': t, 'fields': {'item': [0] * 40}, 'respawn': False}], 'empty backpack')
print('npcs: bandits %s quartermaster %d poisoner %d guards %s harlan %d hollis %d tobias %d wynn %d' % (bandits, QM, PO, GUARDS, HARLAN, HOLLIS, TOBIAS, WYNN))
for t in [QM, PO, HARLAN, bandits[0], bandits[3], GUARDS[0]]:
    print('  %d %s: %s' % (t, me.tpl_read(W.tchar, t * me.CHAR_SIZE, me.CT_FIELDS)['name'], me.RANKS[me.points2rank(struct.unpack_from('<i', W.tchar, t * me.CHAR_SIZE + 709)[0])]))
print(W.save())
json.dump({'head': HEAD, 'ledger': LEDGER, 'moonwort': MOONWORT, 'belt': BELT, 'signet': SIGNET, 'second': SECOND, 'bandits': bandits,
           'qm': QM, 'po': PO, 'guards': GUARDS, 'harlan': HARLAN, 'hollis': HOLLIS, 'tobias': TOBIAS, 'wynn': WYNN},
          open(os.path.join(HERE, 'made.json'), 'w'), indent=1)
