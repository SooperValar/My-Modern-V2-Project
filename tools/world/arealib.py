#!/usr/bin/env python3
"""Shared helpers for the quest plan's area build scripts (Nov 16; first used by barrow_hills/ and lizard_hatcheries/).
Wraps the MyV2 Editor's World class (edit operations on a stopped .dat) with what every area needs:

    from arealib import Area                 # sys.path: tools/world
    A = Area(sys.argv[1], seed=1120)         # the .dat folder
    A.op(op='floor', x=.., y=.., s=.., set=False); A.run('label')        # map edits (floor / object / erase / flag / place)
    t = A.item(src, name, desc, sprite=[n, 0], ...)                        # a new item template (labyrinth flag cleared)
    t = A.quest_item(name, desc, sprite)                                    # a quest item: can't be sold, no labyrinth flag
    t = A.monster(src, name, 'First Lieutenant', x, y, sprite=.., group=.., items=[..], text=[kill, shout])   # scaled to a rank
    A.quest(npc, want, exp, give=item, skill=0, greet=..., lim=1, gold=0, rmin=rank index, n=1)             # an item quest
    A.extra_quest(npc, want, exp, give, ...)                                 # a second item quest of the same NPC
    A.zone(x0, y0, x1, y1, 'Name'); A.save(made_dict, here)

Map: x grows down-right (south), y up-right (east). Flags (op 'flag', bit): 0 blocks walking, 2 indoors, 3 under water,
5 no monsters, 7 tavern (an NPC can't stand on a tavern tile). Ranks: index into me.RANKS (8 Sergeant Major ... 11 Captain,
12 Major, 15 Brigadier General, 19 Field Marshal, 23 Warlord)."""
import sys, os, random, json, math, struct, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
LABY = 1 << 30
QUEST_SRC = 2018            # Greyfang's Fang: a plain quest item (take, no value)
GRASS = [551, 552, 553, 554]; PATH = [35000, 35001, 35002, 35003]; DUSTY = [35100, 35101, 35102, 35103]
MARSH = [35700, 35701, 35702, 35703]; MUD = [35750, 35751, 35752, 35753]; MURK = [35800, 35801, 35802, 35803]
SAND = [35200, 35201, 35202, 35203]; DEEP = [16933, 16957, 16958, 16959]; FOREST = 1118; DIRT = 989; CAVE = 1014; VOID = 1008
OAK = [37000, 37001, 37002, 37003]; DARKWOOD = [37010, 37011, 37012, 37013]; FLAGSTONE = [37020, 37021, 37022, 37023]; SETTS = [37060, 37061, 37062, 37063]
W_SANDSTONE, W_TEMPLE, W_BRICK, W_MOSSY, W_CRACKED, W_SLATE, W_TIMBER, W_FIELDSTONE = ([b, b + 1, b + 2, b + 3] for b in (36000, 36010, 36020, 36030, 36040, 36050, 36060, 36070))
WILLOW = [38140, 38141, 38142, 38143]; DEAD = [38160, 38161, 38162, 38163]; PINE = [38150, 38151, 38152, 38153]; STUMPS = [38164, 38165, 38166, 38167]
OLDTREES = [1238, 1240, 1112, 1114, 880, 882]; REEDS = [38200, 38202, 38204, 38206]
ROCKS = [16352, 16360, 16368, 16376]; LOOSE_ROCKS = [1274, 1276, 1278]
DOOR_I, DOOR_II = 1440, 1441          # oak doors: I in a wall along y (x fixed: a north / south wall), II in a wall along x
TORCH, FIREBOWL, CAMPFIRE, BARREL, BONES, TOMBSTONE = 764, 741, 1148, 2007, 2021, 170
FENCE = {'rail': 40100, 'wattle': 40120, 'iron': 40140, 'lowstone': 40160, 'palisade': 40180, 'hedge': 40200, 'brown': 40220}   # +0 along y, +2 along x, +4/+6/+8/+10 corners left/right/top/bottom

class Area:
    def __init__(self, dat, seed=1):
        random.seed(seed)
        ed = os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/MyV2/Server/mapedit.py'))
        spec = importlib.util.spec_from_file_location('mapedit', ed); self.me = me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
        self.dat = dat; self.W = me.World(dat, os.path.dirname(os.path.abspath(dat)), os.path.join(dat, 'mapedit-areas.json'))
        self.ops = []; self.used = set()
        self.marsh = json.load(open(os.path.join(HERE, '..', 'sprites', 'world_marsh.json')))
    # ---- map
    def op(self, **k): self.ops.append(k)
    def run(self, label=''):
        n, msgs = self.W.apply(self.ops, label)
        for m in msgs: print('  !', label, m)
        self.ops = []; return n
    def tile(self, x, y): return self.W.tile(x, y)          # [floor, object, ch, to_ch, item, dlight, light, flags]
    def floor(self, x, y): return self.W.tile(x, y)[0]
    def clear(self, x, y, floor=None):
        """erase what stands on a tile, take off blocks-walking / under-water / no-monster, and maybe set its floor"""
        self.op(op='erase', x=x, y=y)
        for b in (0, 3, 5): self.op(op='flag', x=x, y=y, bit=b, mode=0)
        if floor is not None: self.op(op='floor', x=x, y=y, s=random.choice(floor) if isinstance(floor, (list, tuple)) else floor, set=False)
    def house(self, box, wall, floor, door_side=None, door=None, keep=1.0, indoors=True):
        """walls around box (x0,y0,x1,y1) and a floor inside; keep<1 leaves gaps (a ruin); door_side n/s (wall along y) or w/e"""
        x0, y0, x1, y1 = box
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                self.op(op='erase', x=x, y=y); self.op(op='floor', x=x, y=y, s=random.choice(floor), set=False)
                if indoors: self.op(op='flag', x=x, y=y, bit=2, mode=1)
                if (x in (x0, x1) or y in (y0, y1)) and random.random() < keep: self.op(op='object', x=x, y=y, s=random.choice(wall), block=3)
        self.run('walls')
        if door:
            self.op(op='erase', x=door[0], y=door[1]); self.op(op='place', x=door[0], y=door[1], t=DOOR_I if door_side in ('n', 's') else DOOR_II, fresh=1); self.run('door')
    def fence(self, box, kind, gaps=(), block=1):
        x0, y0, x1, y1 = box; b = FENCE[kind] if isinstance(kind, str) else kind; gaps = set(gaps)
        for x in range(x0 + 1, x1):
            for y in (y0, y1):
                if (x, y) not in gaps: self.op(op='object', x=x, y=y, s=b + 2, block=block)
        for y in range(y0 + 1, y1):
            for x in (x0, x1):
                if (x, y) not in gaps: self.op(op='object', x=x, y=y, s=b, block=block)
        for (x, y), s in {(x0, y0): b + 4, (x1, y1): b + 6, (x0, y1): b + 8, (x1, y0): b + 10}.items(): self.op(op='object', x=x, y=y, s=s, block=block)
        self.run('fence')
    def place(self, *items):
        for t, x, y in items: self.op(op='place', x=x, y=y, t=t, fresh=1)
        self.run('place')
    def marsh_edges(self, box):
        """soft edges on marsh grass inside box: murky water / path / marsh mud / forest floor creeping in (as the editor does)"""
        kind = {FOREST: 'forest floor', DIRT: 'path'}
        for s in MUD: kind[s] = 'marsh mud'
        for s in MURK: kind[s] = 'murky water'
        for s in PATH: kind[s] = 'path'
        medge = {s for e in self.marsh['marsh_base'].values() for s in e.values()}
        sides = [(1, 0), (0, 1), (-1, 0), (0, -1)]; corn = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
        def mask(x, y, k):
            m = 0
            for i, (dx, dy) in enumerate(sides):
                if kind.get(self.floor(x + dx, y + dy)) == k: m |= 1 << i
            for i, (dx, dy) in enumerate(corn):
                if kind.get(self.floor(x + dx, y + dy)) == k and not m & (1 << i) and not m & (1 << ((i + 1) % 4)): m |= 16 << i
            return m
        for x in range(box[0], box[2] + 1):
            for y in range(box[1], box[3] + 1):
                f = self.floor(x, y)
                if f in MARSH or f in medge:
                    new = None
                    for k in ('murky water', 'path', 'marsh mud', 'forest floor'):
                        m = mask(x, y, k)
                        if m: new = self.marsh['marsh_base'][k][str(m)]; break
                    if new is None and f in medge: new = random.choice(MARSH)
                    if new is not None and new != f: self.op(op='floor', x=x, y=y, s=new, set=False)
        self.run('marsh edges')
    def ground_edges(self, box, kinds=None):
        """soft edges on plain grass inside box where it meets clear water / golden sand / dusty path / path (tools/sprites/
        world_ground.json, the editor's auto edges); the first kind in the list that touches a tile wins"""
        tab = json.load(open(os.path.join(HERE, '..', 'sprites', 'world_ground.json')))['sets']
        kinds = kinds or ['clear water', 'golden sand', 'pale sand', 'dusty path', 'path']
        kind = {}
        for k in kinds:
            for s in tab[k]['plain']: kind[s] = k
        sides = [(1, 0), (0, 1), (-1, 0), (0, -1)]; corn = [(1, 1), (-1, 1), (-1, -1), (1, -1)]
        def mask(x, y, k):
            m = 0
            for i, (dx, dy) in enumerate(sides):
                if kind.get(self.floor(x + dx, y + dy)) == k: m |= 1 << i
            for i, (dx, dy) in enumerate(corn):
                if kind.get(self.floor(x + dx, y + dy)) == k and not m & (1 << i) and not m & (1 << ((i + 1) % 4)): m |= 16 << i
            return m
        n = 0
        for x in range(box[0], box[2] + 1):
            for y in range(box[1], box[3] + 1):
                if self.floor(x, y) not in GRASS: continue
                for k in kinds:
                    m = mask(x, y, k)
                    if m and str(m) in tab[k]['edges']: self.op(op='floor', x=x, y=y, s=tab[k]['edges'][str(m)], set=False); n += 1; break
        self.run('ground edges'); return n
    def zone(self, x0, y0, x1, y1, name, flag=1):
        p = os.path.join(self.dat, 'zones.dat'); s = open(p, encoding='latin-1').read()
        line = '%d %d %d %d %d %s' % (x0, y0, x1, y1, flag, name)
        if line not in s: open(p, 'w', encoding='latin-1').write(s.rstrip('\n') + '\n' + line + '\n')
    # ---- templates
    def made(self, o):
        self.W.apply([o], o.get('op')); assert self.W.made, o; return self.W.made[1]
    def tc(self, t): return self.me.tpl_read(self.W.tchar, t * self.me.CHAR_SIZE, self.me.CT_FIELDS)
    def ti(self, t): return self.me.tpl_read(self.W.titem, t * self.me.ITEM_SIZE, self.me.IT_FIELDS)
    def rank_index(self, t): return self.me.points2rank(struct.unpack_from('<i', self.W.tchar, t * self.me.CHAR_SIZE + 709)[0])
    def rank_of(self, t): return self.me.RANKS[self.rank_index(t)]
    def item(self, src, name, desc, clear=0, **f):
        """a new item template copied from src. Fields: sprite=[n, 0], value, min_rank (rank index), attrib (15: 5 x [worn, 0, needed]),
        hp / end / mana [worn or drunk, while a potion lasts, needed], skill (150: 50 x 3), armor / weapon [worn, while it lasts],
        duration (ticks, 18 a second: 10 minutes = 10800), data (10), driver"""
        t = self.made({'op': 'itempnew', 'from': src, 'name': name})
        f['description'] = desc; f['flags'] = self.W.itemp(t)['flags'] & ~(LABY | clear)
        self.W.apply([{'op': 'itempset', 't': t, 'fields': f}], 'item'); return t
    def quest_item(self, name, desc, sprite): return self.item(QUEST_SRC, name, desc, sprite=[sprite, 0], value=0)
    def worn(self, src, name, desc, sprite, rank, value, attrib=None, skill=None, hp=0, end=0, mana=0, armor=0, clear=0, **f):
        """a reward to wear, copied from src (338 Silver Ring: pass clear=(1<<9)|(1<<10), driver=0, data=[0]*10; 2004 belt; 191 amulet).
        attrib: {index: bonus} (0 Bravery, 1 Willpower, 2 Intuition, 3 Agility, 4 Strength); skill: {SK number: bonus}"""
        a = [0] * 15; s = [0] * 150
        for k, v in (attrib or {}).items(): a[k * 3] = v
        for k, v in (skill or {}).items(): s[k * 3] = v
        return self.item(src, name, desc, clear=clear, sprite=[sprite, 0], attrib=a, skill=s, hp=[hp, 0, 0], end=[end, 0, 0], mana=[mana, 0, 0],
                         armor=[armor, 0], min_rank=rank, value=value, **f)
    def scaled(self, src, pct):
        f = self.tc(src); a = list(f['attrib']); hp = list(f['hp']); en = list(f['end']); mn = list(f['mana']); s = list(f['skill'])
        for i in range(5): a[i * 6] = max(1, round(a[i * 6] * pct / 100))
        hp[0] = round(hp[0] * pct / 100); en[0] = round(en[0] * pct / 100); mn[0] = round(mn[0] * pct / 100)
        for i in range(50): s[i * 6] = min(255, round(s[i * 6] * pct / 100))
        return {'attrib': a, 'hp': hp, 'end': en, 'mana': mn, 'skill': s}
    def monster(self, src, name, rank, x, y, d=None, items=(), text=None, desc=None, sprite=None, group=None, pct=None, nudge=0, place=True):
        """a new NPC template copied from src and placed. rank: a rank name ('Captain') - its strength (attributes, hp, end, mana,
        skills) is scaled until the template's rank is that one (the middle of the range that fits, plus nudge %, kept inside that range); or give pct yourself.
        place=False: only the template (e.g. a monster that something else brings out: pop_create_char)"""
        t = self.made({'op': 'ctempnew', 'from': src, 'name': name})
        dd = list(self.tc(t)['data'])
        for i in list(range(10, 24)) + list(range(32, 36)) + [29, 41]: dd[i] = 0
        if group: dd[42] = dd[44] = group
        f = {'data': dd, 'item': list(items) + [0] * (40 - len(items))}
        if desc is not None: f['description'] = desc
        if sprite: f['sprite'] = sprite
        def setp(p):
            g = dict(f); g.update(self.scaled(src, p)); self.W.apply([{'op': 'ctempset', 't': t, 'fields': g, 'text': text or [], 'respawn': False}], 'npc')
        if pct is None:
            want = self.me.RANKS.index(rank); fit = []
            for p in range(40, 400, 2):
                setp(p); r = self.rank_index(t)
                if r == want: fit.append(p)
                elif r > want: break
            assert fit, 'no strength of template %d gives rank %s' % (src, rank)
            pct = max(fit[0], min(fit[-1], fit[len(fit) // 2] + nudge))      # nudge within the rank: it stays the rank asked for
        self.last_pct = pct; setp(pct)
        if not place: return t
        n, msgs = self.W.apply([{'op': 'npcplace', 't': t, 'x': x, 'y': y, 'dir': d or random.choice([1, 2, 3, 4])}], 'place')
        for m in msgs: print('  !', name, m)
        self.used.add((x, y)); return t
    def person(self, name, like, x, y, d, greet, desc, shout='Guards! Guards!'):
        """a friendly quest giver (a copy of Jamil, 25) with the look (sprite + kindred) of template `like`"""
        assert len(greet) <= 150, 'greeting too long (%d letters; the game keeps 159): %s' % (len(greet), greet)
        t = self.made({'op': 'ctempnew', 'from': 25, 'name': name}); dd = list(self.tc(t)['data'])
        for i in list(range(10, 24)) + list(range(32, 36)) + [29, 41]: dd[i] = 0
        dd[49], dd[50], dd[51], dd[66], dd[37], dd[72] = 0, 0, 0, 0, 1, 0
        lk = self.tc(like); f = {'data': dd, 'item': [0] * 40, 'alignment': 10000, 'description': desc, 'sprite': lk['sprite'], 'kindred': lk['kindred']}
        self.W.apply([{'op': 'ctempset', 't': t, 'fields': f, 'text': ['Hah!', shout, greet], 'respawn': False}], name)
        n, msgs = self.W.apply([{'op': 'npcplace', 't': t, 'x': x, 'y': y, 'dir': d}], 'place')
        for m in msgs: print('  !', name, m)
        return t
    # ---- spots
    def free(self, x, y):
        t = self.W.tile(x, y)
        return not t[1] and not t[2] and not t[4] and not (t[7] & 1) and not (t[7] & (1 << 7)) and (x, y) not in self.used
    def spots(self, n, box, ok=lambda x, y: True, apart=4):
        out = []; tries = 0
        while len(out) < n and tries < 40000:
            tries += 1; x, y = random.randint(box[0], box[2]), random.randint(box[1], box[3])
            if self.free(x, y) and ok(x, y) and all(abs(x - a) + abs(y - b) >= apart for a, b in out): out.append((x, y)); self.used.add((x, y))
        assert len(out) == n, 'only %d of %d spots in %s' % (len(out), n, box); return out
    # ---- quests (item quests: the Quests page's kind; npctalk.dat qreward / qrank / qcount / qalias / order)
    def by_name(self, name):
        c = [t for t in range(1, len(self.W.tchar) // self.me.CHAR_SIZE) if self.W.tchar[t * self.me.CHAR_SIZE] and self.tc(t)['name'] == name and self.tc(t)['x']]
        assert c, 'no placed NPC called ' + name; return c[-1]
    def _rew(self, t, lim, gold, rmin, n, alias=None):
        qs, npcs = self.W.talk_load()
        if alias: qs['alias'][t] = alias
        qs['order'][t] = max([v for v in qs['order'].values() if v > 0] or [0]) + 1
        qs['qrew'][t] = {'lim': lim, 'first': 0, 'gold': gold, 'st': [], 'rmin': rmin, 'rmax': -1, 'n': n}
        self.W.talk_save(qs, npcs)
    def quest(self, npc, want, exp, give=0, skill=0, greet=None, lim=1, gold=0, rmin=-1, n=1):
        """npc wants item `want`: gives exp, item `give` (n of it), teaches `skill`; lim = how often (0 = any number); gold in
        silver (100 = 1G; only bounties pay gold); rmin = lowest rank index"""
        assert not greet or len(greet) <= 150, 'greeting too long (%d letters; the game keeps 159, and %%s grows): %s' % (len(greet), greet)
        dd = list(self.tc(npc)['data']); dd[49], dd[50], dd[51], dd[66], dd[37], dd[72] = want, skill, exp, give, 1, 0
        self.W.apply([{'op': 'ctempset', 't': npc, 'fields': {'data': dd}, 'text': [None, None, greet] if greet else [], 'respawn': True}], 'quest')
        self._rew(npc, lim, gold, rmin, n)
    def extra_quest(self, npc, want, exp, give=0, lim=1, gold=0, rmin=-1, n=1):
        """one more item quest of the same NPC (an unplaced copy of it holds the quest; qalias)"""
        t = self.made({'op': 'ctempnew', 'from': npc, 'name': self.tc(npc)['name']})
        dd = list(self.tc(npc)['data']); dd[49], dd[50], dd[51], dd[66] = want, 0, exp, give
        self.W.apply([{'op': 'ctempset', 't': t, 'fields': {'data': dd}, 'text': [None, None, ''], 'respawn': False}], 'extra quest')
        self._rew(t, lim, gold, rmin, n, alias=npc); return t
    def carry(self, npc, item):
        """an existing NPC template (and its living copy) also carries this item"""
        it = list(self.tc(npc)['item']); it[it.index(0)] = item
        self.W.apply([{'op': 'ctempset', 't': npc, 'fields': {'item': it}, 'respawn': True}], 'carry')
    def save(self, made=None, here=None):
        r = self.W.save(); print(r)
        if made is not None: json.dump(made, open(os.path.join(here, 'made.json'), 'w'), indent=1)
        return r
