#!/usr/bin/env python3
"""MyV2 Editor - the Mercenaries of Astonia v2 map editor, in the browser.

Run it in the server's folder (where .dat/ and ./server are), then open
http://localhost:8080 in your browser:

    python3 mapedit.py
    python3 mapedit.py --client /mnt/c/Users/Cody/Desktop/MyV2/Client --port 8080

Editing works only while the game server is stopped; while it runs the map
can be looked at but not changed. Changes are kept in memory until Save, which
first copies map.dat and item.dat into .dat/mapedit-backups/<date-time>/.
Only the Python standard library is needed.

Files read: .dat/map.dat, item.dat, titem.dat, char.dat (written: map.dat,
item.dat), area.c (zone names), the client's GFX/, pnglib.dat/.idx and
gx00.dat/.idx (sprites), and optionally a minimap picture (world_minimap.png).
"""
import argparse, glob, io, json, mmap, os, re, shutil, struct, subprocess, sys, threading, time, zlib, random
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ---------------------------------------------------------------- data layout
# (offsets from the server's data.h; checked against the file sizes at start)
MAPX = MAPY = 1024
MAXITEM, MAXCHARS, MAXTITEM, MAXTCHARS, MAXEFFECT = 98304, 8192, 4548, 4548, 4096
FX_SIZE = 47                      # effect: used B, flags B, type B, duration I, data 10I
NPC_FIRST_NEW = 2000              # templates the editor makes (one per placed NPC) are numbered from here
PLAYER_START = {2, 3, 4, 13, 76, 77, 78, 79, 543, 544, 545, 546, 547, 548, 549, 550, 551, 552}   # new player characters are made from these
PENTA_TEMPLATES = set(range(364, 386)) | set(range(538, 543)) | set(range(1094, 1098))
MAP_SIZE, ITEM_SIZE, CHAR_SIZE = 28, 634, 3605
USE_EMPTY, USE_ACTIVE = 0, 1
TICKS_SPAWN = 18                  # a placed NPC appears about a second after the server starts
# map: sprite H, fsprite H, ch I, to_ch I, it I, dlight H, light h, flags Q
MAP_FMT = '<HHIIIHhQ'
# item
I_USED, I_NAME, I_DESC, I_FLAGS, I_TEMP, I_SPRITE, I_X, I_Y, I_CARRIED, I_DRIVER, I_DATA, I_ACTIVE, I_LIGHT = \
    0, 1, 81, 281, 295, 537, 529, 531, 533, 593, 594, 525, 509
I_PLACEMENT = 293
# character
C_USED, C_NAME, C_FLAGS, C_SPRITE, C_TEMP, C_X, C_Y, C_DIR = 0, 1, 301, 297, 319, 717, 719, 733
C_ALIGN, C_TOX, C_FRX, C_STATUS, C_ITEM, C_WORN, C_SPELL, C_CITEM, C_DATA = 309, 721, 725, 729, 738, 898, 978, 1058, 1605
CF_RESPAWN, CF_MERCHANT = 1 << 4, 1 << 10
DIRS = {1: 'south', 2: 'north', 3: 'west', 4: 'east'}     # DX_RIGHT +x, DX_LEFT -x, DX_UP -y, DX_DOWN +y (minimap: north = smaller x)

# template fields: name -> (offset, struct format); strings are 'Ns'
CT_FIELDS = {
    'name': (1, '40s'), 'reference': (41, '40s'), 'description': (81, '200s'), 'kindred': (281, '<i'),
    'sprite': (297, '<H'), 'sound': (299, '<H'), 'flags': (301, '<Q'), 'alignment': (309, '<h'),
    'attrib': (321, '30B'), 'hp': (351, '<6H'), 'end': (363, '<6H'), 'mana': (375, '<6H'), 'skill': (387, '300B'),
    'weapon_bonus': (687, 'B'), 'armor_bonus': (688, 'B'), 'points_tot': (709, '<i'), 'x': (717, '<h'), 'y': (719, '<h'),
    'dir': (733, 'B'), 'gold': (734, '<i'), 'item': (738, '<40I'), 'worn': (898, '<20I'), 'citem': (1058, '<I'),
    'speed_mod': (1132, 'b'), 'gethit_dam': (1136, 'b'), 'gethit_bonus': (1137, 'b'), 'light_bonus': (1138, 'B'),
    'class': (1549, '<i'), 'data': (1605, '<100i'),
}
CT_TEXT = 2005                    # text[10][160]
# extra fields of a player character
PL_FIELDS = dict(CT_FIELDS, **{
    'points': (705, '<i'), 'luck': (1533, '<i'), 'depot': (1281, '<62I'), 'depot_cost': (1529, '<i'),
    'creation_date': (1062, '<i'), 'login_date': (1066, '<i'), 'logout_date': (1601, '<i'), 'addr': (1070, '<I'),
    'current_online_time': (1074, '<I'), 'total_online_time': (1078, '<I'), 'temple_x': (311, '<H'), 'temple_y': (313, '<H'),
    'tavern_x': (315, '<H'), 'tavern_y': (317, '<H'), 'pass1': (289, '<I'), 'pass2': (293, '<I'), 'used': (0, 'B'),
    'a_hp': (689, '<i'), 'a_end': (693, '<i'), 'a_mana': (697, '<i'), 'armor': (713, '<h'), 'weapon': (715, '<h'), 'temp': (319, '<H'),
})
KIN = [(0, 'Mercenary'), (1, 'Seyan\'Du'), (2, 'Purple'), (4, 'Templar'), (5, 'Arch-Templar'), (6, 'Harakim'), (9, 'Arch-Harakim'),
       (10, 'Warrior'), (11, 'Sorcerer'), (7, 'male'), (8, 'female')]
RANKS = ['Private', 'Private First Class', 'Lance Corporal', 'Corporal', 'Sergeant', 'Staff Sergeant', 'Master Sergeant', 'First Sergeant',
         'Sergeant Major', 'Second Lieutenant', 'First Lieutenant', 'Captain', 'Major', 'Lieutenant Colonel', 'Colonel', 'Brigadier General',
         'Major General', 'Lieutenant General', 'General', 'Field Marshal', 'Knight of Astonia', 'Baron of Astonia', 'Earl of Astonia',
         'Warlord of Astonia']
RANK_PTS = [50, 850, 4900, 17700, 48950, 113750, 233800, 438600, 766650, 1266650, 1998700, 3035500, 4463550, 6384350, 8915600,
            12192400, 16368450, 21617250, 28133300, 36133300, 49014500, 63000600, 80977100]     # helper.c points2rank()


def points2rank(v):
    for i, p in enumerate(RANK_PTS):
        if v < p:
            return i
    return 23
IT_FIELDS = {
    'name': (1, '40s'), 'reference': (41, '40s'), 'description': (81, '200s'), 'flags': (281, '<Q'), 'value': (289, '<I'),
    'placement': (293, '<H'), 'max_age': (298, '<2I'), 'max_damage': (314, '<I'), 'attrib': (322, '15b'),
    'hp': (337, '<3h'), 'end': (343, '<3h'), 'mana': (349, '<3h'), 'skill': (355, '150b'), 'armor': (505, '2b'),
    'weapon': (507, '2b'), 'light': (509, '<2h'), 'duration': (513, '<I'), 'cost': (517, '<I'), 'power': (521, '<I'),
    'sprite_override': (535, '<H'), 'sprite': (537, '<2h'), 'status': (541, '2B'), 'gethit_dam': (543, '2b'),
    'min_rank': (545, 'b'), 'driver': (593, 'B'), 'data': (594, '<10i'),
}


def tpl_read(buf, base, fields):
    out = {}
    for k, (off, fmt) in fields.items():
        if fmt.endswith('s'):
            out[k] = cstr(buf[base + off:base + off + int(fmt[:-1])])
        else:
            v = struct.unpack_from(fmt, buf, base + off)
            out[k] = list(v) if len(v) > 1 else v[0]
    return out


def tpl_write(buf, base, fields, vals):
    for k, v in vals.items():
        if k not in fields:
            continue
        off, fmt = fields[k]
        if fmt.endswith('s'):
            n = int(fmt[:-1])
            b = str(v).encode('latin-1', 'replace')[:n - 1]
            buf[base + off:base + off + n] = b + b'\0' * (n - len(b))
            continue
        cnt = struct.calcsize(fmt) // struct.calcsize(fmt.lstrip('<0123456789'))
        code = fmt.lstrip('<0123456789')
        lim = {'B': (0, 255), 'b': (-128, 127), 'H': (0, 65535), 'h': (-32768, 32767), 'I': (0, 2 ** 32 - 1),
               'i': (-2 ** 31, 2 ** 31 - 1), 'Q': (0, 2 ** 64 - 1)}[code]
        vs = list(v) if isinstance(v, list) else [v]
        if len(vs) != cnt:
            continue
        vs = [max(lim[0], min(lim[1], int(x))) for x in vs]
        struct.pack_into(fmt, buf, base + off, *vs)


def template_points(t):
    """experience value of an NPC template, as reset_char() works it out"""
    a, hp, en, ma, sk = t['attrib'], t['hp'], t['end'], t['mana'], t['skill']
    pts = 0
    for z in range(5):
        for m in range(10, a[z * 6]): pts += m * m * m * 3 // 20
    for m in range(50, hp[0]): pts += m * 3
    for m in range(50, en[0]): pts += m * 2 // 2
    for m in range(50, ma[0]): pts += m * 3
    for z in range(50):
        if z in (9, 8, 7):        # perception, stealth, lock-picking don't count
            continue
        for m in range(1, sk[z * 6]):
            v = m * m * m * 2 // 40
            pts += v if v > m else m
    return pts


MF = ['move block', 'sight block', 'indoors', 'under water', 'no lag', 'no monsters', 'bank', 'tavern',
      'no magic', 'death trap', 'no light', 'arena', 'lit', 'no expire', 'no fight']
MF_MOVEBLOCK, MF_SIGHTBLOCK = 1, 2
CF_PLAYER, CF_BODY = 1 << 5, 1 << 17
IF_MOVEBLOCK, IF_SIGHTBLOCK, IF_TAKE, IF_LOOK, IF_LOOKSPECIAL, IF_USE, IF_USESPECIAL = 1, 2, 4, 16, 32, 512, 1024

# build mode's random floors: picking one of these paints a random one of its set (same as the game)
FLOOR_SETS = {1003: [1003, 1005, 1006, 1007], 542: list(range(542, 551)), 551: list(range(551, 555)),
              133: list(range(133, 142)), 142: [142, 143, 144, 145], 170: list(range(170, 176)),
              704: [704, 659, 660, 688], 950: list(range(950, 959)), 16670: list(range(16670, 16674)),
              16933: [16933, 16957, 16958, 16959]}


def cstr(b):
    return b.split(b'\0', 1)[0].decode('latin-1')


# ---------------------------------------------------------------- NPC dialogue (.dat/npctalk.dat, read by npctalk.c)
OPS = ('=', '!=', '<', '>', '<=', '>=')


def talk_parse(text):
    quests, npcs, cur, e = {}, {}, None, None
    steps, chests, chest = {}, {}, None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        w = line.split(None, 1)
        k, rest = w[0], (w[1] if len(w) > 1 else '')
        a = rest.split()
        try:
            if chest is not None:
                if k == 'end':
                    chest = None
                elif k == 'refill' and a:
                    chest['refill'] = int(a[0])
                elif k == 'once':
                    chest['once'] = 1
                elif k == 'reward' and a:
                    if a[0] in ('item', 'unique', 'gold'): chest['rewards'].append({'type': a[0], 'v': int(a[1]), 'w': int(a[2])})
                    elif a[0] == 'nothing': chest['rewards'].append({'type': 'nothing', 'w': int(a[1])})
                    elif a[0] == 'tier' and len(a) >= 7:
                        chest['rewards'].append({'type': 'tier', 'tiers': a[1].split(','), 'metals': 'fit' if a[2] in ('fit', 'any') else a[2].split(','),
                                                 'piece': a[3], 'lo': int(a[4]), 'hi': int(a[5]), 'w': int(a[6])})
                    elif a[0] == 'tier':        # the older form: tier metal piece weight (its level: the metal's own range)
                        chest['rewards'].append({'type': 'tier', 'tiers': [a[1]], 'metals': 'fit' if a[2] == 'any' else [a[2]],
                                                 'piece': a[3], 'lo': 0, 'hi': 0, 'w': int(a[4])})
                continue
            if k == 'chest' and len(a) >= 2:
                chest = {'refill': 0, 'once': 0, 'rewards': []}
                chests['%d,%d' % (int(a[0]), int(a[1]))] = chest
                cur, e = None, None
                continue
            if k == 'quest' and a:
                quests[int(a[0])] = rest.split(None, 1)[1] if len(a) > 1 else ''
            elif k == 'step' and len(a) >= 2:
                steps.setdefault(int(a[0]), []).append([int(a[1]), rest.split(None, 2)[2] if len(a) > 2 else ''])
            elif k == 'npc' and a:
                cur, e = int(a[0]), None
                npcs.setdefault(cur, [])
            elif k == 'at' and len(a) >= 2:
                cur, e = '@%d,%d' % (int(a[0]), int(a[1])), None
                npcs.setdefault(cur, [])
            elif k == 'when' and cur is not None and a:
                e = {'when': 'use' if isinstance(cur, str) else a[0] if a[0] in ('give', 'kill', 'near', 'money') else 'say', 'words': '', 'item': 0, 'conds': [], 'answers': [], 'acts': []}
                if a[0] in ('give', 'money'):
                    e['item'] = int(a[1])
                else:
                    e['words'] = rest.split(None, 1)[1] if len(a) > 1 else ''
                npcs[cur].append(e)
            elif e is None:
                continue
            elif k == 'end':
                e = None
            elif k == 'if':
                if a[0] == 'quest': e['conds'].append({'type': 'quest', 'n': int(a[1]), 'op': a[2], 'v': int(a[3])})
                elif a[0] == 'has': e['conds'].append({'type': 'has', 't': int(a[1])})
                elif a[0] == '!has': e['conds'].append({'type': 'hasnot', 't': int(a[1])})
                elif a[0] == 'rank': e['conds'].append({'type': 'rank', 'op': a[1], 'v': int(a[2])})
                elif a[0] == 'area': e['conds'].append({'type': 'area', 's': rest.split(None, 1)[1] if len(a) > 1 else ''})
                elif a[0] == 'skill': e['conds'].append({'type': 'skill', 'n': int(a[1]), 'op': a[2], 'v': int(a[3])})
                elif a[0] == 'gold': e['conds'].append({'type': 'gold', 'op': a[1], 'v': int(a[2])})
            elif k == 'answer':
                e['answers'].append(rest)
            elif k in ('set', 'add') and a[0] == 'quest':
                e['acts'].append({'type': k, 'n': int(a[1]), 'v': int(a[2])})
            elif k == 'give' and a[0] in ('item', 'exp', 'gold', 'luck'):
                e['acts'].append({'type': a[0], 'v': int(a[1])})
            elif k in ('tell', 'announce'):
                e['acts'].append({'type': k, 's': rest})
            elif k == 'teach' and a[0] == 'skill':
                e['acts'].append({'type': 'skill', 'v': int(a[1])})
            elif k == 'teleport':
                e['acts'].append({'type': 'teleport', 'x': int(a[0]), 'y': int(a[1])})
            elif k == 'take' and a[0] == 'item':
                e['acts'].append({'type': 'take', 'v': int(a[1])})
            elif k == 'take' and a[0] == 'gold':
                e['acts'].append({'type': 'takegold', 'v': int(a[1])})
            elif k == 'cast' and len(a) >= 2:
                e['acts'].append({'type': 'cast', 's': a[0], 'v': int(a[1])})
            elif k in ('keep', 'pass'):
                e['acts'].append({'type': k})
        except (IndexError, ValueError):
            continue
    return {'names': quests, 'steps': steps, 'chests': chests}, npcs


def talk_text(quests, npcs, names):
    out = ['# MyV2 custom NPC dialogue, kill tracking and quest steps - written by the MyV2 Editor (the server reads it: npctalk.c)', '']
    qn, qs = quests.get('names', {}), quests.get('steps', {})
    for n in sorted(set(qn) | set(qs)):
        out.append('quest %d %s' % (n, ' '.join(str(qn.get(n, '')).split())))
        for v, t in sorted(qs.get(n, []), key=lambda x: int(x[0])):
            if str(t).strip():
                out.append('step %d %d %s' % (n, int(v), ' '.join(str(t).split())))
    for key, c in sorted(quests.get('chests', {}).items()):
        if not c.get('rewards'):
            continue
        x, y = key.split(',')
        out += ['', 'chest %d %d %s' % (int(x), int(y), names.get('chest ' + key, ''))]
        if int(c.get('refill', 0) or 0) > 0: out.append('refill %d' % int(c['refill']))
        if c.get('once'): out.append('once player')
        for r in c['rewards']:
            w = max(1, int(r.get('w', 1)))
            if r['type'] in ('item', 'unique', 'gold'): out.append('reward %s %d %d' % (r['type'], int(r['v']), w))
            elif r['type'] == 'nothing': out.append('reward nothing %d' % w)
            elif r['type'] == 'tier':
                tiers = [t for t in (r.get('tiers') or ['magic']) if t in ('magic', 'rare', 'epic')] or ['magic']
                mets = r.get('metals') or 'fit'
                mets = 'fit' if mets == 'fit' else ','.join(m for m in mets if m in ('bronze', 'steel', 'golden', 'emerald', 'crystal', 'titanium')) or 'fit'
                lo, hi = int(r.get('lo') or 0), int(r.get('hi') or 0)
                out.append('reward tier %s %s %s %d %d %d' % (','.join(tiers), mets, r.get('piece', 'any') if r.get('piece') in ('helm', 'armor') else 'any', lo, max(lo, hi), w))
        out.append('end')
    for t in sorted(npcs, key=lambda k: (isinstance(k, str), str(k).zfill(12))):
        if not npcs[t]:
            continue
        if isinstance(t, str):
            x, y = t[1:].split(',')
            out += ['', 'at %d %d %s' % (int(x), int(y), names.get(t, ''))]
        else:
            out += ['', 'npc %d %s' % (t, names.get(t, ''))]
        for e in npcs[t]:
            clean = lambda x: ' '.join(str(x).split())
            if isinstance(t, str) or e.get('when') == 'use': out.append('when use')
            elif e.get('when') == 'give': out.append('when give %d' % int(e.get('item', 0)))
            elif e.get('when') == 'kill': out.append('when kill ' + clean(e.get('words', '')).lower())
            elif e.get('when') == 'near': out.append('when near')
            elif e.get('when') == 'money': out.append('when money %d' % max(1, int(e.get('item', 1) or 1)))
            else: out.append('when say ' + clean(e.get('words', '')).lower())
            for c in e.get('conds', []):
                ty = c.get('type')
                if ty == 'quest' and c.get('op') in OPS: out.append('if quest %d %s %d' % (int(c['n']), c['op'], int(c['v'])))
                elif ty == 'has': out.append('if has %d' % int(c['t']))
                elif ty == 'hasnot': out.append('if !has %d' % int(c['t']))
                elif ty == 'rank' and c.get('op') in OPS: out.append('if rank %s %d' % (c['op'], int(c['v'])))
                elif ty == 'area' and clean(c.get('s', '')): out.append('if area ' + clean(c['s']).lower())
                elif ty == 'skill' and c.get('op') in OPS: out.append('if skill %d %s %d' % (int(c['n']), c['op'], int(c['v'])))
                elif ty == 'gold' and c.get('op') in OPS: out.append('if gold %s %d' % (c['op'], int(c['v'])))
            for a in e.get('answers', []):
                if clean(a):
                    out.append('answer ' + clean(a)[:400])
            for a in e.get('acts', []):
                ty = a.get('type')
                if ty in ('set', 'add'): out.append('%s quest %d %d' % (ty, int(a['n']), int(a['v'])))
                elif ty in ('item', 'exp', 'gold', 'luck'): out.append('give %s %d' % (ty, int(a['v'])))
                elif ty in ('tell', 'announce') and clean(a.get('s', '')): out.append('%s %s' % (ty, clean(a['s'])[:400]))
                elif ty == 'skill': out.append('teach skill %d' % int(a['v']))
                elif ty == 'teleport': out.append('teleport %d %d' % (int(a['x']), int(a['y'])))
                elif ty == 'take': out.append('take item %d' % int(a['v']))
                elif ty == 'takegold' and int(a.get('v', 0)) > 0: out.append('take gold %d' % int(a['v']))
                elif ty == 'cast' and a.get('s') in ('bless', 'protect', 'enhance', 'mshield', 'light', 'heal'): out.append('cast %s %d' % (a['s'], max(1, int(a['v']))))
                elif ty in ('keep', 'pass'): out.append(ty)
            out.append('end')
    return '\n'.join(out) + '\n'


# ---------------------------------------------------------------- world
class World:
    FILES = ('map.dat', 'item.dat', 'char.dat', 'tchar.dat', 'effect.dat', 'titem.dat')
    KIND_FILE = {'m': 'map.dat', 'i': 'item.dat', 'c': 'char.dat', 't': 'tchar.dat', 'f': 'effect.dat', 'T': 'titem.dat'}

    def __init__(self, dat, server_dir, area_file):
        self.dat, self.server_dir, self.area_file = dat, server_dir, area_file
        self.lock = threading.RLock()
        self.load()

    def load(self):
        with self.lock:
            p = lambda n: os.path.join(self.dat, n)
            self.map = bytearray(open(p('map.dat'), 'rb').read())
            self.item = bytearray(open(p('item.dat'), 'rb').read())
            self.titem = bytearray(open(p('titem.dat'), 'rb').read())
            self.char = bytearray(open(p('char.dat'), 'rb').read())
            self.tchar = bytearray(open(p('tchar.dat'), 'rb').read()) if os.path.exists(p('tchar.dat')) else None
            self.fx = bytearray(open(p('effect.dat'), 'rb').read()) if os.path.exists(p('effect.dat')) else None
            if self.tchar is not None and len(self.tchar) < MAXTCHARS * CHAR_SIZE: self.tchar = None
            if self.fx is not None and len(self.fx) < MAXEFFECT * FX_SIZE: self.fx = None
            if len(self.map) < MAPX * MAPY * MAP_SIZE or len(self.item) < MAXITEM * ITEM_SIZE \
                    or len(self.titem) < MAXTITEM * ITEM_SIZE:
                sys.exit('The .dat files are smaller than this editor expects - wrong folder or another server version.')
            self.mtimes = {n: os.path.getmtime(p(n)) for n in self.FILES if os.path.exists(p(n))}
            self.touched = set()
            self.made = None
            self.talk_copies = []
            self.live, self.live_actions, self.live_backup = False, [], None
            self.undo, self.redo, self.dirty = [], [], 0
            self.free_hint = 1
            self.areas = self.read_areas()
            self.gen = getattr(self, 'gen', 0) + 1      # the browser fetches everything again when this changes
            self.loaded = time.time()
            if not hasattr(self, 'history'):
                self.history = []

    def refresh_live(self):
        """while the game runs, read its files again now and then so NPCs and changes show"""
        with self.lock:
            if self.dirty or time.time() - self.loaded < 8:
                return
            p = lambda n: os.path.join(self.dat, n)
            try:
                self.map = bytearray(open(p('map.dat'), 'rb').read())
                self.item = bytearray(open(p('item.dat'), 'rb').read())
                self.titem = bytearray(open(p('titem.dat'), 'rb').read())
                self.char = bytearray(open(p('char.dat'), 'rb').read())
                if self.tchar is not None: self.tchar = bytearray(open(p('tchar.dat'), 'rb').read())
                if self.fx is not None: self.fx = bytearray(open(p('effect.dat'), 'rb').read())
            except OSError:
                return
            self.mtimes = {n: os.path.getmtime(p(n)) for n in self.FILES if os.path.exists(p(n))}
            # changes made offline can't be undone any more; live edits can (they check what they find)
            self.undo = [e for e in self.undo if ('L', 0) in e]
            self.redo = [e for e in self.redo if ('L', 0) in e]
            self.gen += 1
            self.loaded = time.time()

    def reload_now(self):
        """read the running game's files right now (it keeps them in shared memory, so they are current)"""
        with self.lock:
            self.loaded = 0
            d = self.dirty; self.dirty = 0
            self.refresh_live()
            self.dirty = d

    def online(self):
        n = 0
        for c in range(1, MAXCHARS):
            o = c * CHAR_SIZE
            if self.char[o + C_USED] == USE_ACTIVE and struct.unpack_from('<Q', self.char, o + C_FLAGS)[0] & CF_PLAYER:
                n += 1
        return n

    def chars(self):
        """every NPC and player standing somewhere in the world"""
        out = []
        for c in range(1, MAXCHARS):
            o = c * CHAR_SIZE
            if not self.char[o + C_USED]:
                continue
            fl = struct.unpack_from('<Q', self.char, o + C_FLAGS)[0]
            if fl & CF_BODY:
                continue
            x, y = struct.unpack_from('<HH', self.char, o + C_X)
            if not x and not y:
                continue
            out.append([c, cstr(self.char[o + C_NAME:o + C_NAME + 40]), x, y,
                        struct.unpack_from('<H', self.char, o + C_TEMP)[0], 1 if fl & CF_PLAYER else 0,
                        self.char_sprite(c), 1 if self.char[o + C_USED] == USE_ACTIVE else 0])
        return out

    def search(self, q):
        q = q.strip().lower()
        out = []
        if not q:
            return out
        m = re.match(r'^(\d+)[ ,]+(\d+)$', q)
        if m:
            out.append({'type': 'place', 'name': 'Position %s, %s' % m.groups(), 'x': int(m.group(1)), 'y': int(m.group(2))})
        seen = set()
        for a, b, c, d, n in self.areas:
            if q in n.lower() and n not in seen:
                seen.add(n)
                out.append({'type': 'place', 'name': n, 'x': (a + c) // 2, 'y': (b + d) // 2})
        for c in self.chars():
            if q in c[1].lower():
                out.append({'type': 'player' if c[5] else 'npc', 'name': c[1], 'x': c[2], 'y': c[3], 'temp': c[4],
                            'sprite': c[6], 'online': c[7]})
                if len(out) > 60:
                    break
        for t in range(1, MAXTITEM):
            o = t * ITEM_SIZE
            if not self.titem[o + I_USED]:
                continue
            name = cstr(self.titem[o + I_NAME:o + I_NAME + 40])
            if q in name.lower() or q == str(t):
                out.append({'type': 'item', 'name': name, 't': t, 'sprite': self.ti_u16(t, I_SPRITE)})
                if len(out) > 100:
                    break
        return out[:100]

    def read_areas(self):
        try:
            src = open(self.area_file, encoding='latin-1').read()
        except OSError:
            return []
        out = []
        for a, b, c, d, n in re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*"([^"]+)"', src):
            out.append((int(a), int(b), int(c), int(d), n))
        return out

    def zone(self, x, y):
        return ', '.join(n for a, b, c, d, n in self.areas if a <= x <= c and b <= y <= d)

    # --- raw access
    def tile(self, x, y):
        return list(struct.unpack_from(MAP_FMT, self.map, (x + y * MAPX) * MAP_SIZE))

    def set_tile(self, x, y, t):
        struct.pack_into(MAP_FMT, self.map, (x + y * MAPX) * MAP_SIZE, *t)

    def it_u8(self, i, off): return self.item[i * ITEM_SIZE + off]
    def it_u16(self, i, off): return struct.unpack_from('<H', self.item, i * ITEM_SIZE + off)[0]
    def it_u64(self, i, off): return struct.unpack_from('<Q', self.item, i * ITEM_SIZE + off)[0]
    def ti_u16(self, t, off): return struct.unpack_from('<H', self.titem, t * ITEM_SIZE + off)[0]
    def ti_u64(self, t, off): return struct.unpack_from('<Q', self.titem, t * ITEM_SIZE + off)[0]

    def item_sprite(self, i):
        o = i * ITEM_SIZE
        s0, s1 = struct.unpack_from('<hh', self.item, o + I_SPRITE)
        active = struct.unpack_from('<i', self.item, o + I_ACTIVE)[0]
        return (s1 if active and s1 else s0) & 0xffff

    def char_sprite(self, c):
        o = c * CHAR_SIZE
        spr = struct.unpack_from('<H', self.char, o + C_SPRITE)[0]
        d = self.char[o + C_DIR]
        return spr + {3: 0, 4: 8, 2: 16, 1: 24, 5: 32, 6: 40, 7: 48, 8: 56}.get(d, 0) if spr else 0

    # --- reading for the browser
    def region(self, x0, y0, x1, y1):
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(MAPX - 1, x1), min(MAPY - 1, y1)
        g, f, fl, it, ch, li = [], [], [], [], [], []
        with self.lock:
            pl = self.pending()
            pend = {(x, y): self.tchar_sprite(tp) for x, y, tp, _ in pl if x0 <= x <= x1 and y0 <= y <= y1}
            pname = {(x, y): self.tname(tp) for x, y, tp, _ in pl if x0 <= x <= x1 and y0 <= y <= y1}
            pc, nm = [], {}      # nm: tile index -> [name, 1 player / 0 NPC / 2 waiting to spawn]
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    s, fs, c, _, i, dl, lt, flags = struct.unpack_from(MAP_FMT, self.map, (x + y * MAPX) * MAP_SIZE)
                    g.append(s); f.append(fs); fl.append(flags & 0xffffffff); li.append(max(0, lt))
                    it.append(self.item_sprite(i) if 0 < i < MAXITEM and self.it_u8(i, I_USED) else 0)
                    ch.append(self.char_sprite(c) if 0 < c < MAXCHARS and self.char[c * CHAR_SIZE + C_USED] else 0)
                    pc.append(pend.get((x, y), 0) if not ch[-1] else 0)
                    if ch[-1]:
                        o = c * CHAR_SIZE
                        nm[len(ch) - 1] = [cstr(self.char[o + C_NAME:o + C_NAME + 40]), 1 if struct.unpack_from('<Q', self.char, o + C_FLAGS)[0] & CF_PLAYER else 0]
                    elif pc[-1]:
                        nm[len(ch) - 1] = [pname[(x, y)], 2]
        return {'x0': x0, 'y0': y0, 'w': x1 - x0 + 1, 'h': y1 - y0 + 1, 'g': g, 'f': f, 'fl': fl, 'it': it, 'ch': ch, 'li': li, 'pc': pc, 'nm': nm}

    def tile_info(self, x, y):
        with self.lock:
            s, fs, c, _, i, dl, li, flags = self.tile(x, y)
            r = {'x': x, 'y': y, 'zone': self.zone(x, y), 'floor': s, 'object': fs, 'light': li, 'dlight': dl,
                 'flags': [MF[b] for b in range(len(MF)) if flags >> b & 1]}
            if 0 < i < MAXITEM and self.it_u8(i, I_USED):
                o = i * ITEM_SIZE
                r['item'] = {'index': i, 'name': cstr(self.item[o + I_NAME:o + I_NAME + 40]), 'temp': self.it_u16(i, I_TEMP),
                             'sprite': self.item_sprite(i), 'driver': self.item[o + I_DRIVER],
                             'data': list(struct.unpack_from('<10i', self.item, o + I_DATA)),
                             'duration': struct.unpack_from('<I', self.item, o + 513)[0],
                             'desc': cstr(self.item[o + I_DESC:o + I_DESC + 200])}
            if 0 < c < MAXCHARS and self.char[c * CHAR_SIZE + C_USED]:
                o = c * CHAR_SIZE
                tp = struct.unpack_from('<H', self.char, o + C_TEMP)[0]
                fl = struct.unpack_from('<Q', self.char, o + C_FLAGS)[0]
                r['char'] = {'index': c, 'name': cstr(self.char[o + C_NAME:o + C_NAME + 40]), 'temp': tp,
                             'dir': self.char[o + C_DIR], 'player': 1 if fl & CF_PLAYER else 0,
                             'merchant': 1 if fl & CF_MERCHANT else 0,
                             'alignment': struct.unpack_from('<h', self.char, o + C_ALIGN)[0]}
                r['char'].update(self.spawn_info(tp, c))
            else:
                for px, py, tp, n in self.pending():
                    if (px, py) == (x, y):
                        r['pending'] = {'temp': tp, 'name': self.tname(tp), 'sprite': self.tchar_sprite(tp), 'dir': self.tchar[tp * CHAR_SIZE + C_DIR]}
                        r['pending'].update(self.spawn_info(tp, 0))
                        break
            return r

    # --- NPCs: every template is one NPC with its own spawn spot (x, y; data[29] = its resting place)
    def t_u16(self, t, off): return struct.unpack_from('<H', self.tchar, t * CHAR_SIZE + off)[0]
    def t_u64(self, t, off): return struct.unpack_from('<Q', self.tchar, t * CHAR_SIZE + off)[0]
    def tname(self, t): return cstr(self.tchar[t * CHAR_SIZE + C_NAME:t * CHAR_SIZE + C_NAME + 40])

    def tchar_sprite(self, t, d=None):
        o = t * CHAR_SIZE
        spr = struct.unpack_from('<H', self.tchar, o + C_SPRITE)[0]
        d = self.tchar[o + C_DIR] if d is None else d
        return spr + {3: 0, 4: 8, 2: 16, 1: 24}.get(d, 8) if spr else 0

    def pending(self):
        """NPCs waiting to (re)spawn: respawn timers in effect.dat -> (x, y, template, effect)"""
        out = []
        if self.fx is None or self.tchar is None:
            return out
        for n in range(1, MAXEFFECT):
            o = n * FX_SIZE
            if self.fx[o] == USE_ACTIVE and self.fx[o + 2] == 2:
                x, y, tp = struct.unpack_from('<3I', self.fx, o + 7)
                if 0 < tp < MAXTCHARS and x < MAPX and y < MAPY:
                    out.append((x, y, tp, n))
        return out

    def living(self, tp):
        out = []
        for c in range(1, MAXCHARS):
            o = c * CHAR_SIZE
            if self.char[o + C_USED] == USE_ACTIVE and struct.unpack_from('<H', self.char, o + C_TEMP)[0] == tp \
                    and not struct.unpack_from('<Q', self.char, o + C_FLAGS)[0] & (CF_PLAYER | CF_BODY):
                out.append(c)
        return out

    def is_home(self, tp, c):
        """is this NPC the one its template spawns (not a copy a spawner or a quest made somewhere else)?"""
        if self.tchar is None or not self.tchar[tp * CHAR_SIZE + C_USED] or not self.t_u64(tp, C_FLAGS) & CF_RESPAWN:
            return False
        if not c:
            return True
        return struct.unpack_from('<i', self.char, c * CHAR_SIZE + C_DATA + 29 * 4)[0] == \
            struct.unpack_from('<i', self.tchar, tp * CHAR_SIZE + C_DATA + 29 * 4)[0]

    def spawn_info(self, tp, c):
        if self.tchar is None or not (0 < tp < MAXTCHARS):
            return {'home': None}
        hx, hy = struct.unpack_from('<hh', self.tchar, tp * CHAR_SIZE + C_X)
        src, n = (self.char, c) if c else (self.tchar, tp)
        stops = [v for v in struct.unpack_from('<9i', src, n * CHAR_SIZE + C_DATA + 40) if v]
        return {'patrol': [[v % MAPX, v // MAPX] for v in stops], 'home': [hx, hy] if self.is_home(tp, c) else None, 'respawns': 1 if self.t_u64(tp, C_FLAGS) & CF_RESPAWN else 0,
                'made': 1 if tp >= NPC_FIRST_NEW else 0, 'count': len(self.living(tp))}

    def npc_templates(self):
        if self.tchar is None:
            return []
        count = {}
        for c in range(1, MAXCHARS):
            o = c * CHAR_SIZE
            if self.char[o + C_USED] == USE_ACTIVE and not struct.unpack_from('<Q', self.char, o + C_FLAGS)[0] & (CF_PLAYER | CF_BODY):
                tp = struct.unpack_from('<H', self.char, o + C_TEMP)[0]
                count[tp] = count.get(tp, 0) + 1
        out = []
        for t in range(1, MAXTCHARS):
            o = t * CHAR_SIZE
            if not self.tchar[o + C_USED]:
                continue
            fl = self.t_u64(t, C_FLAGS)
            if fl & CF_PLAYER or t in PLAYER_START or t == 1:
                continue
            x, y = struct.unpack_from('<hh', self.tchar, o + C_X)
            al = struct.unpack_from('<h', self.tchar, o + C_ALIGN)[0]
            # [number, name, sprite, kind (merchant / enemy / friendly), how many in the world, spawn x, spawn y, made by the editor,
            #  placed (has a spawn spot and respawns), sprite base]
            out.append([t, self.tname(t), self.tchar_sprite(t, 4), 'merchant' if fl & CF_MERCHANT else 'enemy' if al < 0 else 'friendly',
                        count.get(t, 0), x, y, 1 if t >= NPC_FIRST_NEW else 0, 1 if fl & CF_RESPAWN and (x or y) else 0,
                        struct.unpack_from('<H', self.tchar, o + C_SPRITE)[0]])
        return out

    def npc_world(self):
        """every NPC that is in the game: alive, or waiting to (re)spawn"""
        out = []
        for c in range(1, MAXCHARS):
            o = c * CHAR_SIZE
            if self.char[o + C_USED] != USE_ACTIVE:
                continue
            fl = struct.unpack_from('<Q', self.char, o + C_FLAGS)[0]
            if fl & (CF_PLAYER | CF_BODY):
                continue
            x, y = struct.unpack_from('<hh', self.char, o + C_X)
            tp = struct.unpack_from('<H', self.char, o + C_TEMP)[0]
            al = struct.unpack_from('<h', self.char, o + C_ALIGN)[0]
            out.append([c, cstr(self.char[o + C_NAME:o + C_NAME + 40]), x, y, tp, self.char_sprite(c), 'alive',
                        'merchant' if fl & CF_MERCHANT else 'enemy' if al < 0 else 'friendly', self.zone(x, y)])
        if self.tchar is not None:
            for x, y, tp, n in self.pending():
                fl = self.t_u64(tp, C_FLAGS)
                al = struct.unpack_from('<h', self.tchar, tp * CHAR_SIZE + C_ALIGN)[0]
                out.append([0, self.tname(tp), x, y, tp, self.tchar_sprite(tp), 'waiting',
                            'merchant' if fl & CF_MERCHANT else 'enemy' if al < 0 else 'friendly', self.zone(x, y)])
        return out

    def plain_base(self, kind):
        """a plain NPC of this kind to start a new one from: placed in the world, no special code, no patrol, the weakest"""
        best = None
        for t in range(2, MAXTCHARS):
            o = t * CHAR_SIZE
            if not self.tchar[o + C_USED] or t in PLAYER_START or t in PENTA_TEMPLATES:
                continue
            fl = self.t_u64(t, C_FLAGS)
            al = struct.unpack_from('<h', self.tchar, o + C_ALIGN)[0]
            k = 'merchant' if fl & CF_MERCHANT else 'enemy' if al < 0 else 'friendly'
            d = struct.unpack_from('<100i', self.tchar, o + C_DATA)
            pts = struct.unpack_from('<i', self.tchar, o + 709)[0]
            x, y = struct.unpack_from('<hh', self.tchar, o + C_X)
            if k != kind or fl & (CF_PLAYER | 1 | (1 << 15) | (1 << 19)) or d[25] or d[26] or d[10] or pts <= 0 or not (x or y) or not fl & CF_RESPAWN:
                continue
            if kind == 'friendly' and (al <= 0 or d[24] or d[42]):      # a townsperson: good, stays out of fights, no group
                continue
            if best is None or pts < best[0]:
                best = (pts, t)
        return best[1] if best else 0

    def palette(self):
        with self.lock:
            floors, objs = {}, {}
            mv = memoryview(self.map)
            for k in range(MAPX * MAPY):
                s, fs = struct.unpack_from('<HH', mv, k * MAP_SIZE)
                floors[s] = floors.get(s, 0) + 1
                if fs:
                    objs[fs] = objs.get(fs, 0) + 1
            temps = []
            for t in range(1, MAXTITEM):
                o = t * ITEM_SIZE
                if not self.titem[o + I_USED]:
                    continue
                fl = self.ti_u64(t, I_FLAGS)
                # [number, name, sprite, can be picked up, driver, blocks (1 walking, 2 sight), becomes an item (else drawn into the tile)]
                temps.append([t, cstr(self.titem[o + I_NAME:o + I_NAME + 40]), self.ti_u16(t, I_SPRITE),
                              1 if fl & IF_TAKE else 0, self.titem[o + I_DRIVER],
                              (1 if fl & IF_MOVEBLOCK else 0) | (2 if fl & IF_SIGHTBLOCK else 0),
                              1 if fl & (IF_TAKE | IF_LOOK | IF_LOOKSPECIAL | IF_USE | IF_USESPECIAL) else 0,
                              struct.unpack_from('<H', self.titem, o + I_PLACEMENT)[0]])
        fl_sorted = sorted(floors.items(), key=lambda a: -a[1])
        ob_sorted = sorted(objs.items(), key=lambda a: -a[1])
        return {'floors': fl_sorted, 'objects': ob_sorted, 'templates': temps, 'flags': MF, 'sets': FLOOR_SETS,
                'npcs': self.npc_templates()}

    # --- editing: every change remembers the old bytes so a batch can be undone
    def _save_map(self, rec, x, y):
        k = ('m', x, y)
        if k not in rec:
            o = (x + y * MAPX) * MAP_SIZE
            rec[k] = bytes(self.map[o:o + MAP_SIZE])

    def _buf(self, kind):
        return {'i': (self.item, ITEM_SIZE), 'c': (self.char, CHAR_SIZE), 't': (self.tchar, CHAR_SIZE), 'f': (self.fx, FX_SIZE),
                'T': (self.titem, ITEM_SIZE)}[kind]

    def _keep(self, rec, kind, n):
        k = (kind, n)
        if k not in rec:
            b, sz = self._buf(kind)
            rec[k] = bytes(b[n * sz:(n + 1) * sz])

    def _save_item(self, rec, i):
        self._keep(rec, 'i', i)

    def _cur(self, key):
        if key[0] == 'm':
            o = (key[1] + key[2] * MAPX) * MAP_SIZE
            return bytes(self.map[o:o + MAP_SIZE])
        b, sz = self._buf(key[0])
        return bytes(b[key[1] * sz:(key[1] + 1) * sz])

    # --- NPC editing helpers
    def _c_set(self, buf, n, off, fmt, *v):
        struct.pack_into(fmt, buf, n * CHAR_SIZE + off, *v)

    def _char_at(self, x, y):
        c = self.tile(x, y)[2]
        if 0 < c < MAXCHARS and self.char[c * CHAR_SIZE + C_USED] == USE_ACTIVE:
            return c
        return 0

    def _pending_at(self, x, y):
        return [(tp, n) for px, py, tp, n in self.pending() if (px, py) == (x, y)]

    def _free_tchar(self):
        for t in range(NPC_FIRST_NEW, MAXTCHARS):
            if not self.tchar[t * CHAR_SIZE + C_USED]:
                return t
        return 0

    def _free_fx(self):
        for n in range(1, MAXEFFECT):
            if not self.fx[n * FX_SIZE]:
                return n
        return 0

    def _free_spot(self, x, y):
        t = self.tile(x, y)
        if t[7] & MF_MOVEBLOCK or t[0] == 1008:
            return 'blocked (a wall, an object or the void)'
        if self._char_at(x, y):
            return 'someone is standing there'
        if self._pending_at(x, y):
            return 'an NPC is waiting to spawn there'
        i = t[4]
        if 0 < i < MAXITEM and self.it_u8(i, I_USED) and self.it_u64(i, I_FLAGS) & IF_MOVEBLOCK:
            return 'an item there blocks walking'
        return ''

    def _spawn_timer(self, rec, tp, x, y):
        n = self._free_fx()
        if not n:
            return False
        self._keep(rec, 'f', n)
        o = n * FX_SIZE
        self.fx[o:o + FX_SIZE] = b'\0' * FX_SIZE
        self.fx[o] = USE_ACTIVE; self.fx[o + 2] = 2                    # a respawn timer, as when an NPC dies
        struct.pack_into('<I3I', self.fx, o + 3, TICKS_SPAWN, x, y, tp)
        return True

    def _set_home(self, rec, tp, x, y):
        self._keep(rec, 't', tp)
        self._c_set(self.tchar, tp, C_X, '<hhhh', x, y, x, y)
        self._c_set(self.tchar, tp, C_DATA + 29 * 4, '<i', x + y * MAPX)

    def _free_char(self, rec, c):
        """take a living NPC out of the world: off its tile, its items gone"""
        o = c * CHAR_SIZE
        x, y = struct.unpack_from('<hh', self.char, o + C_X)
        if 0 <= x < MAPX and 0 <= y < MAPY:
            t = self.tile(x, y)
            if t[2] == c:
                self._save_map(rec, x, y); t[2] = 0; self.set_tile(x, y, t)
        ids = list(struct.unpack_from('<40I', self.char, o + C_ITEM)) + list(struct.unpack_from('<20I', self.char, o + C_WORN)) + \
            list(struct.unpack_from('<20I', self.char, o + C_SPELL)) + [struct.unpack_from('<I', self.char, o + C_CITEM)[0]]
        for i in ids:
            if 0 < i < MAXITEM and not i & 0x80000000:
                self._save_item(rec, i); self.item[i * ITEM_SIZE + I_USED] = USE_EMPTY
        self._keep(rec, 'c', c)
        self.char[o + C_USED] = USE_EMPTY

    # --- NPC dialogue
    def talk_path(self):
        return os.path.join(self.dat, 'npctalk.dat')

    def talk_load(self):
        try:
            return talk_parse(open(self.talk_path(), encoding='latin-1').read())
        except OSError:
            return {'names': {}, 'steps': {}, 'chests': {}}, {}

    def talk_save(self, quests, npcs, ctl=None):
        p = self.talk_path()
        if os.path.exists(p):
            bk = os.path.join(self.dat, 'mapedit-backups')
            os.makedirs(bk, exist_ok=True)
            shutil.copy2(p, os.path.join(bk, 'npctalk-%s.dat' % time.strftime('%Y%m%d-%H%M%S')))
        names = {t: self.tname(t) for t in npcs if isinstance(t, int) and self.tchar is not None and 0 < t < MAXTCHARS}
        for key in quests.get('chests', {}):
            x, y = map(int, key.split(','))
            i = self.tile(x, y)[4] if 0 <= x < MAPX and 0 <= y < MAPY else 0
            names['chest ' + key] = cstr(self.item[i * ITEM_SIZE + I_NAME:i * ITEM_SIZE + I_NAME + 40]) if 0 < i < MAXITEM else ''
        for t in npcs:
            if isinstance(t, str):
                x, y = map(int, t[1:].split(','))
                i = self.tile(x, y)[4] if 0 <= x < MAPX and 0 <= y < MAPY else 0
                names[t] = cstr(self.item[i * ITEM_SIZE + I_NAME:i * ITEM_SIZE + I_NAME + 40]) if 0 < i < MAXITEM else ''
        with open(p + '.tmp', 'w', encoding='latin-1', errors='replace') as f:
            f.write(talk_text(quests, npcs, names))
        os.replace(p + '.tmp', p)
        if ctl and server_running():
            r = ctl.console('talkreload', 5)
            return 'Saved; the game uses it now.' if r and 'loaded' in r else 'Saved. (The game reads it at its next start: the running server is older.)'
        return 'Saved. The game uses it when the server starts.'

    def talk_copy(self, src, dst, ctl=None):
        """a copied NPC template gets the original's dialogue (and a freed number loses its own)"""
        q, npcs = self.talk_load()
        if src in npcs and npcs[src]:
            npcs[dst] = json.loads(json.dumps(npcs[src]))
        elif dst in npcs:
            del npcs[dst]
        else:
            return
        self.talk_save(q, npcs, ctl)

    # --- templates: reading and changing them
    def ctemp(self, t):
        if self.tchar is None or not (0 < t < MAXTCHARS) or not self.tchar[t * CHAR_SIZE + C_USED]:
            return None
        base = t * CHAR_SIZE
        r = tpl_read(self.tchar, base, CT_FIELDS)
        r['text'] = [cstr(self.tchar[base + CT_TEXT + i * 160:base + CT_TEXT + i * 160 + 160]) for i in range(10)]
        r['t'] = t
        r['count'] = len(self.living(t))
        r['pending'] = len([p for p in self.pending() if p[2] == t])
        r['made'] = 1 if t >= NPC_FIRST_NEW else 0
        r['names'] = {'worn': [self.iname(v) for v in r['worn']], 'item': [self.iname(v) for v in r['item']],
                      'citem': self.iname(r['citem']), 'want': self.iname(r['data'][49]), 'give': self.iname(r['data'][66])}
        return r

    # --- player characters
    def is_player(self, c):
        o = c * CHAR_SIZE
        return 0 < c < MAXCHARS and self.char[o + C_USED] != USE_EMPTY and \
            struct.unpack_from('<Q', self.char, o + C_FLAGS)[0] & CF_PLAYER and not struct.unpack_from('<Q', self.char, o + C_FLAGS)[0] & CF_BODY

    def kin_name(self, k):
        cls = [n for b, n in KIN if b not in (7, 8) and k >> b & 1]
        return (cls[0] if cls else '?') + (' (f)' if k >> 8 & 1 else ' (m)' if k >> 7 & 1 else '')

    def players(self):
        out = []
        for c in range(1, MAXCHARS):
            if not self.is_player(c):
                continue
            o = c * CHAR_SIZE
            pt = struct.unpack_from('<i', self.char, o + 709)[0]
            out.append({'c': c, 'name': cstr(self.char[o + 1:o + 41]), 'online': 1 if self.char[o] == USE_ACTIVE else 0,
                        'rank': RANKS[points2rank(pt)], 'points': pt, 'kin': self.kin_name(struct.unpack_from('<i', self.char, o + 281)[0]),
                        'login': max(struct.unpack_from('<i', self.char, o + 1066)[0], struct.unpack_from('<i', self.char, o + 1601)[0]),
                        'sprite': self.char_sprite(c), 'flags': struct.unpack_from('<Q', self.char, o + C_FLAGS)[0]})
        out.sort(key=lambda p: (-p['online'], -p['login']))
        return out

    def iteminfo(self, i):
        if not (0 < i < MAXITEM) or i & 0x80000000 or not self.item[i * ITEM_SIZE + I_USED]:
            return None
        o = i * ITEM_SIZE
        return {'i': i, 'name': cstr(self.item[o + 1:o + 41]), 'temp': self.it_u16(i, I_TEMP), 'sprite': self.item_sprite(i),
                'desc': cstr(self.item[o + I_DESC:o + I_DESC + 200]), 'value': struct.unpack_from('<I', self.item, o + 289)[0]}

    def pchar(self, c):
        if not self.is_player(c):
            return None
        o = c * CHAR_SIZE
        r = tpl_read(self.char, o, PL_FIELDS)
        r['text'] = []
        r['c'] = c
        r['online'] = 1 if self.char[o] == USE_ACTIVE else 0
        r['rank'] = RANKS[points2rank(r['points_tot'])]
        r['kin_name'] = self.kin_name(r['kindred'])
        r['bank'] = r['data'][13]
        r['items'] = {'item': [self.iteminfo(i) for i in r['item']], 'worn': [self.iteminfo(i) for i in r['worn'][:12]],
                      'depot': [self.iteminfo(i) for i in r['depot']], 'citem': self.iteminfo(r['citem'])}
        r['ip'] = '%d.%d.%d.%d' % (r['addr'] & 255, r['addr'] >> 8 & 255, r['addr'] >> 16 & 255, r['addr'] >> 24) if r['addr'] else ''
        r['quests'] = {}
        try:      # quest steps (npctalk.c's quest.dat)
            with open(os.path.join(self.dat, 'quest.dat'), 'rb') as f:
                h = f.read(16)
                if h[:8] == b'MYV2QST2':
                    nv, rs = struct.unpack_from('<ii', h, 8)
                    f.seek(16 + c * rs)
                    row = f.read(rs)
                    if len(row) == rs and struct.unpack_from('<i', row)[0] == r['creation_date']:
                        r['quests'] = {n + 1: v for n, v in enumerate(struct.unpack_from('<%dH' % nv, row, 4)) if v}
        except OSError:
            pass
        return r

    def moa(self, c):
        """the client's character file (struct key + struct pdata of the client)"""
        p = self.pchar(c)
        if not p:
            return None
        name = p['name'].encode('latin-1', 'replace')[:39]
        key = struct.pack('<III40si', c, p['pass1'], p['pass2'], name, p['temp'] if 0 < p['temp'] < 1000 else 2)
        pd = bytearray(480)
        pd[0:len(name)] = name
        ref = p['reference'].encode('latin-1', 'replace')[:79]; pd[80:80 + len(ref)] = ref
        de = p['description'].encode('latin-1', 'replace')[:159]; pd[160:160 + len(de)] = de
        struct.pack_into('<iii', pd, 324, 0, 1, 1)                   # hide, show names, show percentages
        for n in range(12):                                         # the skill buttons: empty
            pd[336 + n * 12:336 + n * 12 + 2] = b'-\0'
            struct.pack_into('<i', pd, 336 + n * 12 + 8, -1)
        return key + bytes(pd)

    def phistory(self, c, limit=400):
        """what server.log says about this character"""
        p = self.pchar(c)
        if not p:
            return []
        pat = re.compile(r'^(\d\d)\.(\d\d)\.(\d\d) (\d\d:\d\d:\d\d): (.+?) \((\d+) at (\d+),(\d+) from ([\d.]+), ID=-?\d+\): (.*)$')
        key = ' (%d at ' % c
        out = []
        for fn in ('server.log.1', 'server.log'):
            try:
                f = open(os.path.join(self.server_dir, fn), 'rb')
            except OSError:
                continue
            with f:
                for line in f:
                    if key.encode() not in line:
                        continue
                    m = pat.match(line.decode('latin-1').rstrip('\n'))
                    if not m or m.group(5).split(' [')[0] != p['name']:
                        continue
                    t = m.group(10)
                    kind = 'login' if t.startswith('Login successful') else 'logout' if t.startswith(('Connection closed', 'Idle timeout', 'Exit', 'Pressed F12', 'Punished for leaving')) \
                        else 'kill' if t.startswith('Killed ') else 'death' if t.startswith(('Died', 'new player body')) or 'killed by' in t.lower() else 'other'
                    out.append({'t': '20%s-%s-%s %s' % (m.group(3), m.group(2), m.group(1), m.group(4)), 'x': int(m.group(7)), 'y': int(m.group(8)),
                                'ip': m.group(9), 'kind': kind, 'text': t[:200]})
                    if len(out) > 20000:
                        del out[:10000]
        return out[-limit:]

    def iname(self, t):
        if 0 < t < MAXTITEM and self.titem[t * ITEM_SIZE + I_USED]:
            return cstr(self.titem[t * ITEM_SIZE + I_NAME:t * ITEM_SIZE + I_NAME + 40])
        return ''

    def itemp(self, t):
        if not (0 < t < MAXTITEM) or not self.titem[t * ITEM_SIZE + I_USED]:
            return None
        r = tpl_read(self.titem, t * ITEM_SIZE, IT_FIELDS)
        r['t'] = t
        r['onmap'] = sum(1 for i in range(1, MAXITEM) if self.item[i * ITEM_SIZE + I_USED] == USE_ACTIVE
                         and self.it_u16(i, I_TEMP) == t and not self.it_u16(i, I_CARRIED))
        r['made'] = 1 if t >= NPC_FIRST_NEW else 0
        return r

    def _respawn_template(self, rec, tp):
        """like the game's reset_char: the NPCs of this template go, and it spawns again (with the changes) at its spot"""
        if self.live:          # the game does it itself
            self.live_actions.append(((23, tp, 0, 0, 0), (23, tp, 0, 0, 0)))
            return
        for c in self.living(tp):
            self._free_char(rec, c)
        for x, y, ptp, n in self.pending():
            if ptp == tp:
                self._keep(rec, 'f', n); self.fx[n * FX_SIZE] = USE_EMPTY
        hx, hy = struct.unpack_from('<hh', self.tchar, tp * CHAR_SIZE + C_X)
        if self.t_u64(tp, C_FLAGS) & CF_RESPAWN and (hx or hy):
            self._spawn_timer(rec, tp, hx, hy)

    def player_op(self, rec, op):
        c = int(op['c'])
        if not self.is_player(c):
            return 'not a player character'
        o = c * CHAR_SIZE
        k = op['op']
        if k == 'pset':
            f = {k2: v for k2, v in (op.get('fields') or {}).items() if k2 in PL_FIELDS and k2 not in
                 ('item', 'worn', 'depot', 'citem', 'used', 'pass1', 'pass2', 'temp', 'x', 'y', 'a_hp', 'a_end', 'a_mana', 'armor', 'weapon',
                  'creation_date', 'login_date', 'logout_date', 'addr', 'current_online_time', 'total_online_time')}
            self._keep(rec, 'c', c)
            if 'bank' in op:
                d = list(struct.unpack_from('<100i', self.char, o + C_DATA)); d[13] = int(op['bank']); f['data'] = d
            if op.get('nopass'):            # forget the password (CF_PASSWD and the stored hash)
                self.char[o + 1139:o + 1155] = b'\0' * 16
                f['flags'] = int(f.get('flags', struct.unpack_from('<Q', self.char, o + C_FLAGS)[0])) & ~(1 << 42)
            tpl_write(self.char, o, PL_FIELDS, f)
            return ''
        where, slot = op.get('where'), int(op.get('slot', 0))
        off, cnt = {'item': (C_ITEM, 40), 'worn': (C_WORN, 12), 'depot': (1281, 62), 'citem': (C_CITEM, 1)}.get(where, (0, 0))
        if not cnt or not (0 <= slot < cnt):
            return 'bad slot'
        cur = struct.unpack_from('<I', self.char, o + off + 4 * slot)[0]
        if k == 'pdelitem':
            if not cur:
                return 'that slot is empty'
            self._keep(rec, 'c', c)
            if 0 < cur < MAXITEM and not cur & 0x80000000:
                self._save_item(rec, cur); self.item[cur * ITEM_SIZE + I_USED] = USE_EMPTY
            struct.pack_into('<I', self.char, o + off + 4 * slot, 0)
            return ''
        if k == 'padditem':
            tp = int(op['t'])
            if not self.itemp(tp):
                return 'item template %d does not exist' % tp
            if cur:
                return 'that slot is taken'
            i = self._free_item()
            if not i:
                return 'no free item slot'
            self._save_item(rec, i); self._keep(rec, 'c', c)
            io = i * ITEM_SIZE
            self.item[io:io + ITEM_SIZE] = self.titem[tp * ITEM_SIZE:(tp + 1) * ITEM_SIZE]
            self.item[io + I_USED] = USE_ACTIVE
            struct.pack_into('<H', self.item, io + I_TEMP, tp)
            struct.pack_into('<hhH', self.item, io + I_X, 0, 0, c)
            struct.pack_into('<i', self.item, io + I_ACTIVE, 0)
            struct.pack_into('<I', self.char, o + off + 4 * slot, i)
            return ''
        return 'unknown player edit'

    def temp_op(self, rec, op):
        k = op['op']
        if k == 'ctempset':
            if self.tchar is None:
                return 'tchar.dat is missing'
            t = int(op['t'])
            if not self.ctemp(t):
                return 'NPC template %d does not exist' % t
            base = t * CHAR_SIZE
            self._keep(rec, 't', t)
            before = bytes(self.tchar[base:base + CHAR_SIZE])
            f = dict(op.get('fields') or {})
            for k2 in ('x', 'y', 'points_tot'):
                f.pop(k2, None)
            tpl_write(self.tchar, base, CT_FIELDS, f)
            for i, txt in enumerate(op.get('text') or []):
                if i < 9 and txt is not None:      # text 9 is the NPC's own memory
                    b = str(txt).encode('latin-1', 'replace')[:159]
                    self.tchar[base + CT_TEXT + i * 160:base + CT_TEXT + i * 160 + 160] = b + b'\0' * (160 - len(b))
            if any(k2 in f for k2 in ('attrib', 'hp', 'end', 'mana', 'skill')):
                struct.pack_into('<i', self.tchar, base + 709, template_points(tpl_read(self.tchar, base, CT_FIELDS)))
            if 'dir' in f:
                struct.pack_into('<i', self.tchar, base + C_DATA + 30 * 4, int(f['dir']))
            if bytes(self.tchar[base:base + CHAR_SIZE]) != before and op.get('respawn', True):
                self._respawn_template(rec, t)
            return ''
        if k == 'ctempnew':
            src = int(op['from'])
            if not self.ctemp(src):
                return 'NPC template %d does not exist' % src
            t = self._free_tchar()
            if not t:
                return 'no free NPC template number left'
            self._keep(rec, 't', t)
            o = t * CHAR_SIZE
            self.tchar[o:o + CHAR_SIZE] = self.tchar[src * CHAR_SIZE:(src + 1) * CHAR_SIZE]
            self.talk_copies.append((src, t))
            self._c_set(self.tchar, t, C_TEMP, '<H', t)
            self._c_set(self.tchar, t, C_X, '<hhhh', 0, 0, 0, 0)          # not placed yet: the NPC brush places it
            self._c_set(self.tchar, t, C_DATA + 29 * 4, '<i', 0)
            # no respawning until it is placed (else the game keeps trying to spawn it at 0,0: "Could not drop char")
            self._c_set(self.tchar, t, C_FLAGS, '<Q', self.t_u64(t, C_FLAGS) & ~CF_RESPAWN)
            for i in range(10, 19):
                self._c_set(self.tchar, t, C_DATA + i * 4, '<i', 0)       # no patrol of the original
            if op.get('name'):
                tpl_write(self.tchar, o, CT_FIELDS, {'name': op['name'], 'reference': op['name']})
            self.made = ('npc', t)
            return ''
        if k == 'ctempblank':           # + New NPC: a plain one of a kind, with a name and a look
            kind = op.get('kind', 'friendly')
            src = self.plain_base(kind)
            if not src:
                return 'no plain %s NPC found to start from' % kind
            t = self._free_tchar()
            if not t:
                return 'no free NPC template number left'
            self._keep(rec, 't', t)
            o = t * CHAR_SIZE
            self.tchar[o:o + CHAR_SIZE] = self.tchar[src * CHAR_SIZE:(src + 1) * CHAR_SIZE]
            self._c_set(self.tchar, t, C_TEMP, '<H', t)
            self._c_set(self.tchar, t, C_X, '<hhhh', 0, 0, 0, 0)
            self._c_set(self.tchar, t, C_FLAGS, '<Q', self.t_u64(t, C_FLAGS) & ~CF_RESPAWN)    # placing it turns this on
            d = list(struct.unpack_from('<100i', self.tchar, o + C_DATA))
            for i in list(range(10, 24)) + [29, 31, 32, 33, 34, 35, 41, 47, 48, 49, 50, 51, 52, 53, 54, 55, 59, 60, 63, 64, 66, 69, 73, 79, 93, 95]:
                d[i] = 0                     # no patrol, doors, lights, quest, helpers or attack zone of the original
            d[37] = 1                        # greets players (its greeting line is empty until you write one)
            struct.pack_into('<100i', self.tchar, o + C_DATA, *d)
            self.tchar[o + CT_TEXT:o + CT_TEXT + 1600] = b'\0' * 1600
            name = str(op.get('name') or 'New NPC')
            f = {'name': name, 'reference': name, 'description': str(op.get('description') or '')}
            if op.get('sprite'):
                f['sprite'] = int(op['sprite'])
            if kind != 'merchant':
                f['item'] = [0] * 40         # an empty backpack (a merchant keeps its stock to start from)
            tpl_write(self.tchar, o, CT_FIELDS, f)
            self.made = ('npc', t)
            return ''
        if k == 'itempset':
            t = int(op['t'])
            if not self.itemp(t):
                return 'item template %d does not exist' % t
            base = t * ITEM_SIZE
            self._keep(rec, 'T', t)
            before = bytes(self.titem[base:base + ITEM_SIZE])
            tpl_write(self.titem, base, IT_FIELDS, op.get('fields') or {})
            after = bytes(self.titem[base:base + ITEM_SIZE])
            if op.get('update_map', True) and after != before:
                # the copies lying on the map get the new values - wherever a copy still had the template's old value
                # (so their own changes, like a portal's destination or a sign's text, stay)
                old, new = tpl_read(before, 0, IT_FIELDS), tpl_read(after, 0, IT_FIELDS)
                chg = {k2 for k2 in IT_FIELDS if old[k2] != new[k2]}
                for i in range(1, MAXITEM):
                    o = i * ITEM_SIZE
                    if self.item[o + I_USED] != USE_ACTIVE or self.it_u16(i, I_TEMP) != t or self.it_u16(i, I_CARRIED):
                        continue
                    cur = tpl_read(self.item, o, {k2: IT_FIELDS[k2] for k2 in chg})
                    upd = {}
                    for k2 in chg:
                        if isinstance(new[k2], list):
                            v = [nv if cv == ov else cv for cv, ov, nv in zip(cur[k2], old[k2], new[k2])]
                            if v != cur[k2]: upd[k2] = v
                        elif cur[k2] == old[k2]:
                            upd[k2] = new[k2]
                    if upd:
                        self._save_item(rec, i)
                        tpl_write(self.item, o, IT_FIELDS, upd)
                        x, y = self.it_u16(i, I_X), self.it_u16(i, I_Y)
                        if 0 <= x < MAPX and 0 <= y < MAPY:
                            self._save_map(rec, x, y)
            return ''
        if k == 'itempnew':
            src = int(op['from'])
            if not self.itemp(src):
                return 'item template %d does not exist' % src
            t = next((n for n in range(NPC_FIRST_NEW, MAXTITEM) if not self.titem[n * ITEM_SIZE + I_USED]), 0)
            if not t:
                return 'no free item template number left'
            self._keep(rec, 'T', t)
            o = t * ITEM_SIZE
            self.titem[o:o + ITEM_SIZE] = self.titem[src * ITEM_SIZE:(src + 1) * ITEM_SIZE]
            struct.pack_into('<H', self.titem, o + I_TEMP, t)
            if op.get('name'):
                tpl_write(self.titem, o, IT_FIELDS, {'name': op['name'], 'reference': op['name'].lower()})
            self.made = ('item', t)
            return ''
        return 'unknown template edit'

    def npc_op(self, rec, op, x, y):
        """place / move / turn / remove an NPC; returns an error text or ''"""
        if self.tchar is None or self.fx is None:
            return 'tchar.dat or effect.dat is missing: NPCs cannot be edited'
        k = op['op']
        if k == 'npcplace':
            src = int(op['t'])
            if not (0 < src < MAXTCHARS) or not self.tchar[src * CHAR_SIZE + C_USED]:
                return 'NPC template %d does not exist' % src
            why = self._free_spot(x, y)
            if why:
                return '%d,%d: %s' % (x, y, why)
            hx, hy = struct.unpack_from('<hh', self.tchar, src * CHAR_SIZE + C_X)
            if src >= NPC_FIRST_NEW and not hx and not hy and not self.living(src):
                tp = src               # a new NPC made in the editor and not placed yet: this is its spot
                for px, py, ptp, pn in self.pending():      # a stale spawn timer of it (at 0,0) goes
                    if ptp == src:
                        self._keep(rec, 'f', pn); self.fx[pn * FX_SIZE] = USE_EMPTY
            else:
                tp = self._free_tchar()
            if not tp:
                return 'no free NPC template number left'
            d = int(op.get('dir', 4))
            self._keep(rec, 't', tp)
            o = tp * CHAR_SIZE
            if tp != src:
                self.tchar[o:o + CHAR_SIZE] = self.tchar[src * CHAR_SIZE:(src + 1) * CHAR_SIZE]
                self.talk_copies.append((src, tp))
            self.tchar[o + C_USED] = USE_ACTIVE
            self._c_set(self.tchar, tp, C_TEMP, '<H', tp)
            self._c_set(self.tchar, tp, C_FLAGS, '<Q', self.t_u64(tp, C_FLAGS) | CF_RESPAWN)
            self.tchar[o + C_DIR] = d
            self._c_set(self.tchar, tp, C_DATA + 30 * 4, '<i', d)
            self._set_home(rec, tp, x, y)
            if not self._spawn_timer(rec, tp, x, y):
                return 'no free effect slot for the spawn'
            self._save_map(rec, x, y)
            return ''
        c = self._char_at(x, y)
        pend = self._pending_at(x, y)
        if c and struct.unpack_from('<Q', self.char, c * CHAR_SIZE + C_FLAGS)[0] & CF_PLAYER:
            return 'that is a player'
        if not c and not pend:
            return 'no NPC on %d,%d' % (x, y)
        tp = struct.unpack_from('<H', self.char, c * CHAR_SIZE + C_TEMP)[0] if c else pend[0][0]
        home = self.is_home(tp, c)
        self._save_map(rec, x, y)
        if k == 'npcdir':
            d = int(op['dir'])
            if d not in DIRS:
                return 'bad direction'
            if c and self.live:
                self.live_actions.append(((22, c, tp, d, 0), (22, c, tp, self.char[c * CHAR_SIZE + C_DIR], 0)))
            elif c:
                self._keep(rec, 'c', c)
                self.char[c * CHAR_SIZE + C_DIR] = d
                self._c_set(self.char, c, C_DATA + 30 * 4, '<i', d)
                self._c_set(self.char, c, C_STATUS, '<h', 0)
            if home:
                self._keep(rec, 't', tp)
                self.tchar[tp * CHAR_SIZE + C_DIR] = d
                self._c_set(self.tchar, tp, C_DATA + 30 * 4, '<i', d)
            return ''
        if k == 'npcmove':
            tx, ty = int(op['tx']), int(op['ty'])
            if not (0 <= tx < MAPX and 0 <= ty < MAPY):
                return 'outside the map'
            why = self._free_spot(tx, ty)
            if why:
                return '%d,%d: %s' % (tx, ty, why)
            self._save_map(rec, tx, ty)
            if c and self.live:
                self.live_actions.append(((21, c, tp, tx, ty), (21, c, tp, x, y)))
            elif c:
                t0 = self.tile(x, y); t0[2] = 0; self.set_tile(x, y, t0)
                t1 = self.tile(tx, ty); t1[2] = c; self.set_tile(tx, ty, t1)
                self._keep(rec, 'c', c)
                self._c_set(self.char, c, C_X, '<hhhhhh', tx, ty, tx, ty, tx, ty)
                self._c_set(self.char, c, C_DATA + 29 * 4, '<i', tx + ty * MAPX)
            if home:
                self._set_home(rec, tp, tx, ty)
                for _, n in self._pending_at(x, y) if not c else []:
                    self._keep(rec, 'f', n); struct.pack_into('<2I', self.fx, n * FX_SIZE + 7, tx, ty)
            return ''
        if k == 'npcremove':
            if c and self.live:
                self.live_actions.append(((20, c, tp, 0, 0), (23, tp, 0, 0, 0)))
            elif c:
                self._free_char(rec, c)
            for ptp, n in pend:
                self._keep(rec, 'f', n); self.fx[n * FX_SIZE] = USE_EMPTY
            if home:     # it should not come back: its template stops respawning (one the editor made is freed)
                self._keep(rec, 't', tp)
                if tp >= NPC_FIRST_NEW:
                    self.tchar[tp * CHAR_SIZE + C_USED] = USE_EMPTY
                    self.talk_copies.append((0, tp))     # its dialogue goes too
                else:
                    self._c_set(self.tchar, tp, C_FLAGS, '<Q', self.t_u64(tp, C_FLAGS) & ~CF_RESPAWN)
                for n in range(1, MAXEFFECT):     # and any other respawn timer it has
                    o = n * FX_SIZE
                    if self.fx[o] == USE_ACTIVE and self.fx[o + 2] == 2 and struct.unpack_from('<I', self.fx, o + 15)[0] == tp:
                        self._keep(rec, 'f', n); self.fx[o] = USE_EMPTY
            return ''
        return 'unknown NPC edit'

    def _free_item(self):
        for i in list(range(self.free_hint, MAXITEM)) + list(range(1, self.free_hint)):
            if not self.item[i * ITEM_SIZE + I_USED]:
                self.free_hint = i + 1
                return i
        return 0

    def _remove_item(self, rec, x, y):
        t = self.tile(x, y)
        i = t[4]
        if 0 < i < MAXITEM:
            self._save_item(rec, i)
            self.item[i * ITEM_SIZE + I_USED] = USE_EMPTY
        t[4] = 0
        self.set_tile(x, y, t)

    def apply(self, ops, label=''):
        """ops: list of dicts; returns (tiles changed, messages)"""
        rec, msgs, n = {}, [], 0
        with self.lock:
            self.made = None
            self.talk_copies = []
            for op in ops:
                if op['op'] in ('pset', 'padditem', 'pdelitem'):
                    err = self.player_op(rec, op)
                    if err:
                        msgs.append(err)
                    else:
                        n += 1
                    continue
                if op['op'] in ('ctempset', 'ctempnew', 'ctempblank', 'itempset', 'itempnew'):
                    err = self.temp_op(rec, op)
                    if err:
                        msgs.append(err)
                    else:
                        n += 1
                    continue
                x, y = int(op['x']), int(op['y'])
                if not (0 <= x < MAPX and 0 <= y < MAPY):
                    continue
                k = op['op']
                if k.startswith('npc'):
                    err = self.npc_op(rec, op, x, y)
                    if err:
                        msgs.append(err)
                    else:
                        n += 1
                    continue
                self._save_map(rec, x, y)
                t = self.tile(x, y)
                if k == 'floor':
                    s = int(op['s'])
                    t[0] = random.choice(FLOOR_SETS[s]) if s in FLOOR_SETS and op.get('set', True) else s
                    self.set_tile(x, y, t)
                elif k == 'object':           # a raw object sprite (eyedropper), with its blocking
                    t[1] = int(op['s'])
                    blk = int(op.get('block', 3))
                    t[7] = (t[7] & ~3) | (MF_MOVEBLOCK if blk & 1 else 0) | (MF_SIGHTBLOCK if blk & 2 else 0)
                    if not t[1]:
                        t[7] &= ~3
                    self.set_tile(x, y, t)
                elif k == 'place':            # a template, like build mode
                    tp = int(op['t'])
                    if not (0 < tp < MAXTITEM) or not self.titem[tp * ITEM_SIZE + I_USED]:
                        msgs.append('template %d does not exist' % tp); continue
                    fl = self.ti_u64(tp, I_FLAGS)
                    if fl & (IF_TAKE | IF_LOOK | IF_LOOKSPECIAL | IF_USE | IF_USESPECIAL):
                        if t[4] and 0 < t[4] < MAXITEM and self.it_u8(t[4], I_USED):
                            if not op.get('replace'):
                                msgs.append('%d,%d already has an item' % (x, y)); continue
                            self._remove_item(rec, x, y); t = self.tile(x, y)
                        if self.titem[tp * ITEM_SIZE + I_DRIVER] == 33:
                            msgs.append('pentagrams need build mode in game (they get numbered there)'); continue
                        i = self._free_item()
                        if not i:
                            msgs.append('no free item slot'); continue
                        self._save_item(rec, i)
                        o = i * ITEM_SIZE
                        self.item[o:o + ITEM_SIZE] = self.titem[tp * ITEM_SIZE:(tp + 1) * ITEM_SIZE]
                        self.item[o + I_USED] = USE_ACTIVE
                        struct.pack_into('<H', self.item, o + I_TEMP, tp)
                        struct.pack_into('<hhH', self.item, o + I_X, x, y, 0)
                        struct.pack_into('<i', self.item, o + I_ACTIVE, 0)
                        t[1] = 0          # an item replaces an object sprite (as in the game)
                        t[4] = i
                    else:                             # a plain piece: drawn into the tile
                        t[1] = self.ti_u16(tp, I_SPRITE)
                        t[7] = (t[7] & ~3) | (MF_MOVEBLOCK if fl & IF_MOVEBLOCK else 0) | (MF_SIGHTBLOCK if fl & IF_SIGHTBLOCK else 0)
                    self.set_tile(x, y, t)
                elif k == 'erase':            # like left-click in build mode: object and item go, floor stays
                    self._remove_item(rec, x, y)
                    t = self.tile(x, y)
                    t[1] = 0
                    t[7] &= ~3
                    self.set_tile(x, y, t)
                elif k == 'itemedit':        # change the item on the tile: name, description, data values
                    i = t[4]
                    if not (0 < i < MAXITEM) or not self.it_u8(i, I_USED):
                        msgs.append('no item on %d,%d' % (x, y)); continue
                    self._save_item(rec, i)
                    o = i * ITEM_SIZE
                    if 'name' in op:
                        b = str(op['name']).encode('latin-1', 'replace')[:39]
                        self.item[o + I_NAME:o + I_NAME + 40] = b + b'\0' * (40 - len(b))
                        r = b.lower()     # the reference ("a portal") follows the name
                        self.item[o + 41:o + 81] = r + b'\0' * (40 - len(r))
                    if 'desc' in op:
                        b = str(op['desc']).encode('latin-1', 'replace')[:199]
                        self.item[o + I_DESC:o + I_DESC + 200] = b + b'\0' * (200 - len(b))
                    for kk, v in (op.get('data') or {}).items():
                        if 0 <= int(kk) < 10:
                            struct.pack_into('<i', self.item, o + I_DATA + 4 * int(kk), int(v))
                    if 'driver' in op:
                        self.item[o + I_DRIVER] = int(op['driver']) & 255
                    if 'duration' in op:
                        struct.pack_into('<I', self.item, o + 513, max(0, int(op['duration'])))
                    self.set_tile(x, y, t)
                elif k == 'flag':
                    b = 1 << int(op['bit'])
                    m = int(op.get('mode', 2))
                    t[7] = (t[7] | b) if m == 1 else (t[7] & ~b) if m == 0 else (t[7] ^ b)
                    self.set_tile(x, y, t)
                n += 1
            # keep only real changes
            real = {}
            for key, old in rec.items():
                if self._cur(key) != old:
                    real[key] = old
            npc_moved = any(key[0] in 'ctf' for key in real)
            if npc_moved and not any(key[0] == 'm' for key in real) and 'x' in ops[0]:     # an NPC spawn: remember its tile for the history
                real[('m', int(ops[0]['x']), int(ops[0]['y']))] = self._cur(('m', int(ops[0]['x']), int(ops[0]['y'])))
            if real or self.live_actions:
                self.touched |= {self.KIND_FILE[key[0]] for key in real}
                self.undo.append(real)
                self.redo.clear()
                self.dirty += 1
                tiles = [k for k in real if k[0] == 'm']
                fx, fy = (tiles[0][1], tiles[0][2]) if tiles else (int(ops[0].get('x', 0)), int(ops[0].get('y', 0)))
                self.history.append({'t': time.strftime('%H:%M:%S'), 'what': label or 'edit', 'tiles': max(1, len(tiles)),
                                     'x': fx, 'y': fy})
            return max(len([k for k in real if k[0] == 'm']), n if real else 0), msgs

    # --- live editing: the changes go to the running game as a patch (see edpatch in console.c)
    KIND_NR = {'m': 0, 'i': 1, 'c': 2, 't': 3, 'T': 4, 'f': 5}

    def _write_patch(self, pairs, actions):
        """pairs: {key: (bytes the game should have now, bytes to write)}"""
        out, cnt = [], 0
        for key, (exp, new) in pairs.items():
            idx = key[1] + key[2] * MAPX if key[0] == 'm' else key[1]
            diff = [i for i in range(len(new)) if exp[i] != new[i]]
            runs = []
            for i in diff:              # runs of changed bytes; close ones go together
                if runs and i - runs[-1][1] <= 2:
                    runs[-1][1] = i + 1
                else:
                    runs.append([i, i + 1])
            for i, j in runs:
                out.append(struct.pack('<BIHH', self.KIND_NR[key[0]], idx, i, j - i) + exp[i:j] + new[i:j])
                cnt += 1
        body = b'MYV2PATCH1' + struct.pack('<I', cnt) + b''.join(out) + struct.pack('<I', len(actions)) + \
            b''.join(struct.pack('<B4i', *a) for a in actions)
        path = os.path.abspath(os.path.join(self.server_dir, '.edpatch.bin'))
        with open(path, 'wb') as f:
            f.write(body)
        return path, cnt

    def _send_patch(self, ctl, pairs, actions):
        path, cnt = self._write_patch(pairs, actions)
        if not cnt and not actions:
            return True, ''
        r = ctl.console('edpatch ' + path, timeout=60) if ctl else None
        if r is None:
            return False, 'The game server did not answer on its control port (it needs the newer server: Update code & restart).'
        if r.startswith('ok'):
            notes = [l[5:] for l in r.splitlines() if l.startswith('note ')]
            return True, '; '.join(notes)
        if 'Unknown command' in r:
            return False, 'The running server is older than live editing: use "Update code & restart" on the Server page once.'
        return False, 'Not done: the game changed something there since the editor looked (an NPC walked by, an item was picked up…). Try again.' \
            if 'conflict' in r else r.strip()

    def _live_backup(self):
        if self.live_backup:
            return
        bk = os.path.join(self.dat, 'mapedit-backups', time.strftime('%Y%m%d-%H%M%S') + '-live')
        os.makedirs(bk, exist_ok=True)
        for n in self.FILES:
            if os.path.exists(os.path.join(self.dat, n)):
                shutil.copy2(os.path.join(self.dat, n), os.path.join(bk, n))
        self.live_backup = bk

    def apply_live(self, ops, label, ctl):
        with self.lock:
            if self.dirty:
                return 0, ['There are unsaved changes from before the server started: save or discard them first.']
            self.reload_now()
            self._live_backup()
            n0, h0 = len(self.undo), len(self.history)
            self.live, self.live_actions = True, []
            try:
                changed, msgs = self.apply(ops, label + ' (live)')
            finally:
                self.live = False
            acts, self.live_actions = self.live_actions, []
            if len(self.undo) == n0:
                self.dirty = 0
                return changed, msgs
            rec = self.undo[-1]
            new = {k: self._cur(k) for k in rec}
            ok, note = self._send_patch(ctl, {k: (rec[k], new[k]) for k in rec}, [a for a, _ in acts])
            if not ok:
                self._swap(rec)
                self.undo.pop(); del self.history[h0:]
                self.dirty = 0; self.touched = set()
                return 0, msgs + [note]
            rec[('L', 0)] = (new, [a for a, _ in acts], [b for _, b in reversed(acts)])
            self.dirty = 0; self.touched = set()
            for a, b in self.talk_copies:
                self.talk_copy(a, b, ctl)
            self.reload_now()
            return changed, msgs + ([note] if note else [])

    def undo_live(self, which, ctl):
        with self.lock:
            src, dst = (self.undo, self.redo) if which == 'undo' else (self.redo, self.undo)
            if not src:
                return [], ''
            rec = src[-1]
            if ('L', 0) not in rec:
                src.pop()
                return [], 'That change was made while the server was stopped; it can\'t be undone while it runs.'
            new, acts, inv = rec[('L', 0)]
            old = {k: v for k, v in rec.items() if k != ('L', 0)}
            self.reload_now()
            ok, note = self._send_patch(ctl, {k: (new[k], old[k]) for k in old}, inv)
            if not ok:
                return [], note
            src.pop()
            back = dict(new); back[('L', 0)] = (old, inv, acts)
            dst.append(back)
            self.reload_now()
            pos = [[k[1], k[2]] for k in old if k[0] == 'm']
            self.history.append({'t': time.strftime('%H:%M:%S'), 'what': which + ' (live)', 'tiles': len(pos),
                                 'x': pos[0][0] if pos else 0, 'y': pos[0][1] if pos else 0})
            return pos, note

    def _swap(self, rec):
        back = {}
        for key, old in rec.items():
            if key[0] == 'L':
                continue
            back[key] = self._cur(key)
            if key[0] == 'm':
                o = (key[1] + key[2] * MAPX) * MAP_SIZE
                self.map[o:o + MAP_SIZE] = old
            else:
                b, sz = self._buf(key[0])
                b[key[1] * sz:(key[1] + 1) * sz] = old
            self.touched.add(self.KIND_FILE[key[0]])
        return back

    def undo_redo(self, which):
        with self.lock:
            src, dst = (self.undo, self.redo) if which == 'undo' else (self.redo, self.undo)
            if not src:
                return []
            rec = src.pop()
            dst.append(self._swap(rec))
            self.dirty += 1
            pos = [[k[1], k[2]] for k in rec if k[0] == 'm']
            for k in rec:          # items changed on their own (renamed, a portal's destination): where they lie
                if k[0] == 'i':
                    ix, iy = struct.unpack_from('<hh', self.item, k[1] * ITEM_SIZE + I_X)
                    if 0 <= ix < MAPX and 0 <= iy < MAPY and [ix, iy] not in pos:
                        pos.append([ix, iy])
                elif k[0] in 'ct':
                    b = self.char if k[0] == 'c' else self.tchar
                    ix, iy = struct.unpack_from('<hh', b, k[1] * CHAR_SIZE + C_X)
                    if 0 < ix < MAPX and 0 < iy < MAPY and [ix, iy] not in pos:
                        pos.append([ix, iy])
            if pos:
                self.history.append({'t': time.strftime('%H:%M:%S'), 'what': which, 'tiles': len(pos), 'x': pos[0][0], 'y': pos[0][1]})
            return pos

    def save(self):
        with self.lock:
            p = lambda n: os.path.join(self.dat, n)
            files = [n for n in self.FILES if n in self.touched or n in ('map.dat', 'item.dat')]
            for n in files:
                if n in self.mtimes and abs(os.path.getmtime(p(n)) - self.mtimes[n]) > 1:
                    return 'The world files changed on disk since they were loaded (the server ran?). Reload first - your unsaved changes would overwrite them.'
            bk = os.path.join(self.dat, 'mapedit-backups', time.strftime('%Y%m%d-%H%M%S'))
            os.makedirs(bk, exist_ok=True)
            for n in files:
                shutil.copy2(p(n), os.path.join(bk, n))
            bufs = {'map.dat': self.map, 'item.dat': self.item, 'char.dat': self.char, 'tchar.dat': self.tchar, 'effect.dat': self.fx,
                    'titem.dat': self.titem}
            for n in files:
                data = bufs[n]
                with open(p(n) + '.tmp', 'wb') as f:
                    f.write(data)
                os.replace(p(n) + '.tmp', p(n))
                self.mtimes[n] = os.path.getmtime(p(n))
            self.dirty = 0
            self.touched = set()
            self.history.append({'t': time.strftime('%H:%M:%S'), 'what': 'saved to the game', 'tiles': 0})
            return 'Saved. Backup of the old files: ' + bk

    def backups(self):
        d = os.path.join(self.dat, 'mapedit-backups')
        if not os.path.isdir(d):
            return []
        return sorted(n for n in os.listdir(d) if re.match(r'^\d{8}-\d{6}$', n))

    def restore_last(self):
        """put the files from before the last save back (that backup is then marked used)"""
        with self.lock:
            b = self.backups()
            if not b:
                return 'There is no saved backup to go back to.'
            src = os.path.join(self.dat, 'mapedit-backups', b[-1])
            for n in self.FILES:
                if os.path.exists(os.path.join(src, n)):
                    shutil.copy2(os.path.join(src, n), os.path.join(self.dat, n))
            os.rename(src, src + '-restored')
            self.load()
            self.history.append({'t': time.strftime('%H:%M:%S'), 'what': 'undid the save of ' + b[-1], 'tiles': 0})
            return 'Went back to the world as it was before the save of %s.' % b[-1]


def reap():
    """collect finished child processes (a server this editor started, also before it restarted itself)"""
    try:
        while os.waitpid(-1, os.WNOHANG)[0] > 0:
            pass
    except (ChildProcessError, OSError):
        pass


def server_running():
    reap()
    try:
        out = subprocess.run(['pgrep', '-x', 'server'], capture_output=True, text=True).stdout.split()
        for p in out:
            if int(p) == os.getpid():
                continue
            try:                       # a finished process nobody collected yet is not running
                if open('/proc/%s/stat' % p).read().rsplit(')', 1)[1].split()[0] == 'Z':
                    continue
            except (OSError, IndexError):
                pass
            return True
        return False
    except Exception:
        return False


# ---------------------------------------------------------------- the game server: control
CONSOLE_PORT = 5556


class ServerCtl:
    """Runs and talks to the game server.
    - console(): a command over the server's control port (127.0.0.1:5556, console.c)
    - jobs (one at a time, in a thread): start, stop, restart, update code (claude-sync.sh get:
      copies the source Claude changed and rebuilds), update world (claude-sync.sh get-world).
      Stopping warns players first if any are online.
    - requests from Claude: JSON files dropped into <control>/requests/ are carried out and
      answered in <control>/responses/<id>.json; <control>/status.json is kept up to date.
    """

    def __init__(self, server_dir, control_dir, world):
        self.dir, self.control, self.world = server_dir, control_dir, world
        self.job = None            # {'name', 'step', 'log': [...], 'done', 'ok', 'started'}
        self.lock = threading.Lock()
        self.requests = []         # what Claude asked for, newest last
        self.was_running = server_running()
        self.started_at = None
        if control_dir:
            for d in ('requests', 'responses'):
                try:
                    os.makedirs(os.path.join(control_dir, d), exist_ok=True)
                except OSError:
                    pass
        threading.Thread(target=self._watch, daemon=True).start()

    # --- the control port
    def console(self, cmd, timeout=5):
        import socket
        try:
            s = socket.create_connection(('127.0.0.1', CONSOLE_PORT), timeout=timeout)
        except OSError:
            return None
        try:
            s.sendall((cmd.replace('\n', ' ') + '\n').encode('latin-1', 'replace'))
            buf = b''
            end = time.time() + timeout
            while not (buf.endswith(b'\n.\n') or buf == b'.\n') and time.time() < end:
                d = s.recv(65536)
                if not d:
                    break
                buf += d
        except OSError:
            return None
        finally:
            s.close()
        t = buf.decode('latin-1')
        return t[:-2] if t.endswith('.\n') else t

    def port_ok(self):
        """is the running server's control port answering (live editing needs it)? checked at most every 10 s"""
        now = time.time()
        if now - getattr(self, '_port_t', 0) > 10:
            self._port_t, self._port = now, self.console('status', 2) is not None
        return self._port

    def status(self):
        running = server_running()
        st = {'running': running, 'online': 0, 'uptime': None, 'port': False, 'players': []}
        if running:
            r = self.console('status', 2)
            if r is not None:
                st['port'] = True
                for kv in r.split():
                    k, _, v = kv.partition('=')
                    if v.lstrip('-').isdigit():
                        st[k] = int(v)
                w = self.console('whotab', 2) or ''
                for line in w.splitlines():
                    f = line.split('\t')
                    if len(f) >= 7:
                        st['players'].append({'name': f[0], 'rank': f[1], 'x': int(f[2]), 'y': int(f[3]), 'where': f[4],
                                              'role': f[5], 'points': int(f[6])})
            else:
                st['online'] = self.world.online()
        with self.lock:
            st['job'] = dict(self.job) if self.job else None
            if st['job']:
                st['job']['log'] = list(self.job['log'][-60:])
            st['requests'] = self.requests[-30:]
        return st

    # --- jobs
    def _log(self, msg):
        with self.lock:
            if self.job:
                self.job['log'].append(time.strftime('%H:%M:%S ') + msg)
                self.job['step'] = msg

    def run_job(self, name, warn=30, reason='a restart', on_done=None):
        with self.lock:
            if self.job and not self.job['done']:
                return 'Busy: %s is still running.' % self.job['name']
            self.job = {'name': name, 'step': 'starting', 'log': [], 'done': False, 'ok': None, 'started': time.strftime('%H:%M:%S')}
        threading.Thread(target=self._job, args=(name, warn, reason, on_done), daemon=True).start()
        return None

    def _job(self, name, warn, reason, on_done):
        ok = False
        try:
            if name == 'start':
                ok = self._start()
            elif name == 'stop':
                ok = self._stop(warn, reason or 'maintenance')
            elif name == 'restart':
                ok = self._stop(warn, reason or 'a restart') and self._start()
            elif name == 'update-code':
                ok = self._stop(warn, reason or 'an update') and self._sync('get') and self._start()
            elif name == 'update-world':
                ok = self._stop(warn, reason or 'a world update') and self._sync('get-world') and self._start()
            elif name == 'rebuild':
                ok = self._run(['make', 'server'], 'make server')
            elif name == 'send':                 # Ubuntu -> Windows: the source, and the world files if the server is stopped
                ok = self._sync('send')
            elif name == 'stop-send':            # stop and send the saved world, then stay stopped (for world edits)
                ok = self._stop(warn, reason or 'maintenance') and self._sync('send')
            elif name == 'get':                  # Windows -> Ubuntu: the source Claude changed, rebuilt (no restart)
                ok = self._sync('get')
            elif name == 'get-world':            # Windows -> Ubuntu: the world files (only while stopped)
                if server_running():
                    self._log('stop the server first'); ok = False
                else:
                    ok = self._sync('get-world')
            else:
                self._log('unknown job ' + name)
        except Exception as e:
            self._log('failed: %s' % e)
        with self.lock:
            self.job['done'], self.job['ok'] = True, ok
        self._log('done' if ok else 'stopped with an error')
        if on_done:
            on_done(ok, list(self.job['log']))

    def _run(self, args, label):
        self._log('running ' + label)
        try:
            p = subprocess.run(args, cwd=self.dir, capture_output=True, text=True, timeout=900)
        except Exception as e:
            self._log('%s failed: %s' % (label, e)); return False
        for line in (p.stdout + p.stderr).splitlines()[-40:]:
            self._log('  ' + line)
        if p.returncode:
            self._log('%s ended with code %d' % (label, p.returncode)); return False
        return True

    def _sync(self, what):
        sc = os.path.join(self.dir, 'claude-sync.sh')
        if not os.path.exists(sc):
            self._log('no claude-sync.sh in ' + self.dir); return False
        return self._run(['bash', sc, what], 'claude-sync.sh ' + what)

    def _start(self):
        if server_running():
            self._log('the server is already running'); return True
        exe = os.path.join(self.dir, 'server')
        if not os.path.exists(exe):
            self._log('no ./server here - build it first'); return False
        self._log('starting ./server loop (its output goes to server.log)')
        log = open(os.path.join(self.dir, 'server.log'), 'a')
        subprocess.Popen([exe, 'loop'], cwd=self.dir, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         start_new_session=True)       # keeps running when the editor is closed
        for _ in range(60):
            time.sleep(1)
            if self.console('status', 1) is not None:
                self._log('the server is up'); self.started_at = time.time(); return True
            if not server_running() and _ > 5:
                self._log('the server stopped right away - see the log'); return False
        self._log('the server runs, but its control port does not answer (an old ./server? update the code)')
        return server_running()

    def _stop(self, warn, reason):
        if not server_running():
            self._log('the server is not running'); return True
        st = self.status()
        if warn and st.get('online'):
            self._log('warning %d player(s): going down in %d seconds' % (st['online'], warn))
            self.console('announce The server goes down for %s in %d seconds.' % (reason, warn))
            left = warn
            while left > 0:
                step = 10 if left > 10 else left
                time.sleep(step)
                left -= step
                if left in (30, 10):
                    self.console('announce The server goes down in %d seconds.' % left)
        self._log('shutting down (saves everything)')
        if self.console('shutdown', 3) is None:
            self._log('control port not answering: sending the stop signal instead')
            subprocess.run(['pkill', '-TERM', '-x', 'server'])
        for _ in range(90):
            time.sleep(1)
            if not server_running():
                self._log('the server has stopped'); return True
        self._log('the server did not stop within 90 seconds'); return False

    # --- Claude's requests, and keeping the world view right
    def _watch(self):
        while True:
            try:
                running = server_running()
                if self.was_running and not running and not self.world.dirty:
                    self.world.load()                  # it saved its files when it stopped
                self.was_running = running
                if self.control:
                    self._requests()
                    self._status_file()
            except Exception as e:
                print('control:', e)
            time.sleep(2)

    def _status_file(self):
        st = self.status()
        st['time'] = time.strftime('%Y-%m-%d %H:%M:%S')
        st['editor'] = 'MyV2 Editor'
        p = os.path.join(self.control, 'status.json')
        try:
            with open(p + '.tmp', 'w') as f:
                json.dump(st, f, indent=1)
            os.replace(p + '.tmp', p)
        except OSError:
            pass

    def _answer(self, rid, obj):
        p = os.path.join(self.control, 'responses', rid + '.json')
        try:
            with open(p + '.tmp', 'w') as f:
                json.dump(obj, f, indent=1)
            os.replace(p + '.tmp', p)
        except OSError:
            pass

    def _requests(self):
        d = os.path.join(self.control, 'requests')
        try:
            names = sorted(n for n in os.listdir(d) if n.endswith('.json'))
        except OSError:
            return
        for n in names:
            p = os.path.join(d, n)
            try:
                req = json.load(open(p))
                os.remove(p)
            except (OSError, ValueError):
                try:
                    os.remove(p)
                except OSError:
                    pass
                continue
            rid = re.sub(r'[^\w.-]', '_', str(req.get('id') or n[:-5]))
            act = req.get('action', '')
            entry = {'id': rid, 'time': time.strftime('%H:%M:%S'), 'action': act, 'cmd': req.get('cmd', ''), 'note': req.get('note', ''), 'result': 'working'}
            with self.lock:
                self.requests.append(entry)
            print('Claude asks: %s %s' % (act, req.get('cmd', '')))
            if act == 'status':
                entry['result'] = 'done'
                self._answer(rid, {'ok': True, 'status': self.status()})
            elif act == 'console':
                r = self.console(req.get('cmd', ''))
                entry['result'] = 'done' if r is not None else 'server not reachable'
                self._answer(rid, {'ok': r is not None, 'output': r})
            elif act == 'log':
                entry['result'] = 'done'
                self._answer(rid, {'ok': True, 'log': self.log_tail(int(req.get('lines', 200)))})
            elif act == 'reload-editor':         # start this editor again (after it was updated)
                entry['result'] = 'done'
                self._answer(rid, {'ok': True, 'note': 'the editor restarts now'})
                threading.Thread(target=self._reexec, daemon=True).start()
            elif act in ('start', 'stop', 'restart', 'update-code', 'update-world', 'rebuild', 'send', 'stop-send', 'get', 'get-world'):
                def done(ok, log, entry=entry, rid=rid):
                    entry['result'] = 'done' if ok else 'failed'
                    self._answer(rid, {'ok': ok, 'log': log})
                err = self.run_job(act, int(req.get('warn', 30)), req.get('reason', ''), done)
                if err:
                    entry['result'] = err
                    self._answer(rid, {'ok': False, 'error': err})
            else:
                entry['result'] = 'unknown action'
                self._answer(rid, {'ok': False, 'error': 'unknown action ' + act})

    def _reexec(self):
        time.sleep(1.5)
        if self.world.dirty:
            print('Not restarting the editor: there are unsaved map changes.')
            return
        print('Restarting the editor (requested by Claude) ...')
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def log_tail(self, n=200):
        p = os.path.join(self.dir, 'server.log')
        try:
            with open(p, 'rb') as f:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - 256 * 1024))
                lines = f.read().decode('latin-1').splitlines()
            return lines[-n:]
        except OSError:
            return []


# ---------------------------------------------------------------- sprites
class Sprites:
    def __init__(self, client):
        self.client = client
        self.gfx = {}
        for d in ('GFX', 'gfx'):
            for f in glob.glob(os.path.join(client, d, '*')):
                n, e = os.path.splitext(os.path.basename(f))
                if n.isdigit():
                    self.gfx.setdefault(int(n), {})[e.lower()] = f
        try:
            pi = open(os.path.join(client, 'pnglib.idx'), 'rb').read()
            self.pidx = struct.unpack('<%di' % (len(pi) // 4), pi)
            self.pdat = open(os.path.join(client, 'pnglib.dat'), 'rb').read()
        except OSError:
            self.pidx, self.pdat = (), b''
        try:
            self.gidx = open(os.path.join(client, 'gx00.idx'), 'rb').read()
            f = open(os.path.join(client, 'gx00.dat'), 'rb')
            self.gdat = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        except (OSError, ValueError):
            self.gidx, self.gdat = b'', None
        self.cache = {}
        self.lock = threading.Lock()

    @staticmethod
    def png(w, h, rgba):
        raw = b''.join(b'\0' + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))
        def chunk(t, d):
            c = t + d
            return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
        return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)) + \
            chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b'')

    def get(self, nr):
        """(content type, bytes) or None; the client looks in the same order"""
        with self.lock:
            if nr in self.cache:
                return self.cache[nr]
        r = None
        d = self.gfx.get(nr, {})
        if '.png' in d:
            r = ('image/png', open(d['.png'], 'rb').read())
        elif nr < len(self.pidx) and self.pidx[nr]:
            st = self.pidx[nr]
            end = min([v for v in self.pidx if v > st] or [len(self.pdat)])
            r = ('image/png', self.pdat[st:end])
        elif '.bmp' in d:
            r = ('image/bmp', open(d['.bmp'], 'rb').read())
        elif self.gdat is not None and nr * 12 + 12 <= len(self.gidx):
            xs, ys, off = struct.unpack_from('<3i', self.gidx, nr * 12)
            if 0 < xs <= 2048 and 0 < ys <= 2048:
                px = struct.unpack_from('<%dH' % (xs * ys), self.gdat, off)
                out = bytearray(xs * ys * 4)
                for k, v in enumerate(px):
                    if v != 0xF81F:
                        out[k * 4] = ((v >> 11) & 31) * 255 // 31
                        out[k * 4 + 1] = ((v >> 5) & 63) * 255 // 63
                        out[k * 4 + 2] = (v & 31) * 255 // 31
                        out[k * 4 + 3] = 255
                r = ('image/png', self.png(xs, ys, bytes(out)))
        with self.lock:
            self.cache[nr] = r
        return r


# ---------------------------------------------------------------- web server
def make_handler(world, sprites, page, minimap, ctl):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, code, ctype, body, cache=False):
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'max-age=86400' if cache else 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def js(self, obj):
            self.send(200, 'application/json', json.dumps(obj).encode())

        def do_GET(self):
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            if u.path == '/':
                return self.send(200, 'text/html; charset=utf-8', page)
            if u.path.startswith('/sprite/'):
                try:
                    r = sprites.get(int(u.path[8:]))
                except ValueError:
                    r = None
                return self.send(200, r[0], r[1], True) if r else self.send(404, 'text/plain', b'no sprite')
            if u.path in ('/icon.ico', '/favicon.ico'):   # the game's own icon, from the client folder
                for n in ('res_icon_1.ico', 'TLB.ICO', 'tlb.ico'):
                    f = os.path.join(sprites.client, n)
                    if os.path.exists(f):
                        return self.send(200, 'image/x-icon', open(f, 'rb').read(), True)
                return self.send(404, 'text/plain', b'none')
            if u.path == '/minimap.png':
                if minimap and os.path.exists(minimap):
                    return self.send(200, 'image/png', open(minimap, 'rb').read(), True)
                return self.send(404, 'text/plain', b'none')
            if u.path == '/api/info':
                running = server_running()
                if running:
                    world.refresh_live()
                return self.js({'running': running, 'live': bool(running and ctl and ctl.port_ok()), 'online': world.online(), 'gen': world.gen, 'dirty': world.dirty,
                                'undo': len(world.undo), 'redo': len(world.redo), 'areas': world.areas,
                                'minimap': bool(minimap and os.path.exists(minimap)), 'dat': os.path.abspath(world.dat),
                                'backups': len(world.backups())})
            if u.path == '/api/srv/status':
                return self.js(ctl.status())
            if u.path == '/api/srv/log':
                return self.js({'log': ctl.log_tail(int(q.get('n', 300)))})
            if u.path == '/api/search':
                return self.js(world.search(q.get('q', '')))
            if u.path == '/api/chars':
                return self.js(world.chars())
            if u.path == '/api/npcs':
                return self.js(world.npc_templates())
            if u.path == '/api/npcworld':
                return self.js(world.npc_world())
            if u.path == '/api/players':
                return self.js(world.players())
            if u.path == '/api/pchar':
                return self.js(world.pchar(int(q['c'])) or {'error': 'no such player'})
            if u.path == '/api/phist':
                return self.js(world.phistory(int(q['c'])))
            if u.path == '/api/moa':
                b = world.moa(int(q['c']))
                if not b:
                    return self.send(404, 'text/plain', b'no such player')
                nm = re.sub(r'[^A-Za-z0-9_-]', '', world.pchar(int(q['c']))['name']) or 'character'
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', 'attachment; filename="%s.moa"' % nm)
                self.send_header('Content-Length', str(len(b)))
                self.end_headers()
                self.wfile.write(b)
                return
            if u.path == '/api/chest':
                qs, npcs = world.talk_load()
                return self.js({'chest': qs['chests'].get('%d,%d' % (int(q['x']), int(q['y'])))})
            if u.path == '/api/talk':
                qs, npcs = world.talk_load()
                return self.js({'quests': {str(k): v for k, v in qs['names'].items()}, 'steps': {str(k): v for k, v in qs['steps'].items()},
                                'entries': npcs.get('@' + q['at'] if 'at' in q else int(q.get('t', 0)), []),
                                'givers': {str(t): len(v) for t, v in npcs.items() if v}})
            if u.path == '/api/ctemp':
                return self.js(world.ctemp(int(q['t'])) or {'error': 'no such NPC template'})
            if u.path == '/api/itemp':
                return self.js(world.itemp(int(q['t'])) or {'error': 'no such item template'})
            if u.path == '/api/history':
                return self.js({'history': world.history[-300:], 'backups': world.backups()})
            if u.path == '/api/region':
                return self.js(world.region(int(q['x0']), int(q['y0']), int(q['x1']), int(q['y1'])))
            if u.path == '/api/tile':
                return self.js(world.tile_info(int(q['x']), int(q['y'])))
            if u.path == '/api/palette':
                return self.js(world.palette())
            self.send(404, 'text/plain', b'not found')

        def do_POST(self):
            u = urlparse(self.path)
            n = int(self.headers.get('Content-Length') or 0)
            body = json.loads(self.rfile.read(n) or b'{}')
            if u.path == '/api/srv/cmd':
                r = ctl.console(str(body.get('cmd', '')))
                return self.js({'output': r} if r is not None else {'error': 'The server does not answer on its control port (is it running, with the new code?).'})
            if u.path == '/api/srv/action':
                err = ctl.run_job(str(body.get('action', '')), int(body.get('warn', 30)), str(body.get('reason', '')))
                return self.js({'error': err} if err else {'ok': True})
            if u.path in ('/api/edit', '/api/undo', '/api/redo') and server_running():
                if u.path == '/api/edit':      # live: the changes go straight into the running game
                    changed, msgs = world.apply_live(body.get('ops', []), body.get('label', ''), ctl)
                    return self.js({'changed': changed, 'msgs': msgs, 'dirty': world.dirty, 'undo': len(world.undo),
                                    'redo': len(world.redo), 'made': world.made, 'live': True})
                n0 = len(world.undo) + len(world.redo)
                tiles, note = world.undo_live(u.path[5:], ctl)
                ok = note == '' or bool(tiles)
                return self.js({'tiles': tiles, 'done': ok, 'error': None if ok else note, 'note': note if ok else '',
                                'dirty': world.dirty, 'undo': len(world.undo), 'redo': len(world.redo)})
            if u.path in ('/api/save', '/api/relight', '/api/restore') and server_running():
                return self.js({'error': 'The game server is running: live edits are already in the game, there is nothing to save.'})
            if u.path == '/api/chest':
                qs, npcs = world.talk_load()
                key = '%d,%d' % (int(body['x']), int(body['y']))
                if body.get('chest'):
                    qs['chests'][key] = body['chest']
                else:
                    qs['chests'].pop(key, None)
                return self.js({'msg': world.talk_save(qs, npcs, ctl)})
            if u.path == '/api/talk':
                qs, npcs = world.talk_load()
                if 'quests' in body:
                    qs['names'] = {int(k): str(v)[:60] for k, v in body['quests'].items() if 1 <= int(k) <= 255 and str(v).strip()}
                if 'steps' in body:
                    qs['steps'] = {int(k): [[int(a), str(b)[:300]] for a, b in v] for k, v in body['steps'].items() if 1 <= int(k) <= 255}
                if 'at' in body:
                    npcs['@%d,%d' % tuple(int(v) for v in body['at'])] = body.get('entries') or []
                elif 't' in body:
                    npcs[int(body['t'])] = body.get('entries') or []
                return self.js({'msg': world.talk_save(qs, npcs, ctl)})
            if u.path == '/api/edit':
                changed, msgs = world.apply(body.get('ops', []), body.get('label', ''))
                for a, b in world.talk_copies:
                    world.talk_copy(a, b, ctl)
                return self.js({'changed': changed, 'msgs': msgs, 'dirty': world.dirty, 'undo': len(world.undo), 'redo': len(world.redo),
                                'made': world.made})
            if u.path in ('/api/undo', '/api/redo'):
                n0 = len(world.undo if u.path == '/api/undo' else world.redo)
                tiles = world.undo_redo(u.path[5:])
                return self.js({'tiles': tiles, 'done': n0 > 0, 'dirty': world.dirty, 'undo': len(world.undo), 'redo': len(world.redo)})
            if u.path == '/api/save':
                return self.js({'msg': world.save(), 'dirty': world.dirty})
            if u.path == '/api/restore':
                if world.dirty:
                    return self.js({'error': 'There are unsaved changes: save or discard them first.'})
                return self.js({'msg': world.restore_last()})
            if u.path == '/api/reload':
                world.load()
                return self.js({'msg': 'Reloaded from disk.'})
            if u.path == '/api/relight':
                if world.dirty:
                    return self.js({'error': 'Save first.'})
                exe = os.path.join(world.server_dir, 'server')
                if not os.path.exists(exe):
                    return self.js({'error': 'No ./server here to recompute the lights.'})
                try:
                    subprocess.run([exe, 'light'], cwd=world.server_dir, capture_output=True, timeout=600)
                except subprocess.TimeoutExpired:
                    return self.js({'error': 'Relight took too long.'})
                world.load()
                return self.js({'msg': 'Lights recomputed (./server light) and the map reloaded.'})
            self.send(404, 'text/plain', b'not found')
    return H


def main():
    ap = argparse.ArgumentParser(description='MyV2 Editor: the Astonia v2 map editor (browser)')
    ap.add_argument('--dat', default='.dat', help='folder with map.dat etc. (default .dat)')
    ap.add_argument('--client', default='/mnt/c/Users/Cody/Desktop/MyV2/Client', help='the game client folder (sprites)')
    ap.add_argument('--area', default='area.c', help="the server's area.c (zone names)")
    ap.add_argument('--minimap', default=None, help='world minimap picture (default: the project docs one)')
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--control', default='/mnt/c/Users/Cody/Desktop/MyV2/Server/control',
                    help='folder where Claude leaves requests (status, console commands, restarts, updates); "" = off')
    a = ap.parse_args()
    if a.minimap is None:
        a.minimap = os.path.join(a.client, 'Claude outputs', 'My-Modern-V2-Project', 'docs', 'world_minimap.png')
    if not os.path.exists(os.path.join(a.dat, 'map.dat')):
        sys.exit('No %s/map.dat - run this in the server folder, or give --dat.' % a.dat)
    print('Loading the world from %s ...' % os.path.abspath(a.dat))
    world = World(a.dat, os.path.dirname(os.path.abspath(a.dat)), a.area)
    sprites = Sprites(a.client)
    if not sprites.gfx and not sprites.pidx and sprites.gdat is None:
        print('Warning: no sprites found in %s (give --client)' % a.client)
    page = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mapedit.html'), 'rb').read() \
        if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mapedit.html')) else PAGE.encode()
    ctl = ServerCtl(world.server_dir, a.control if a.control and os.path.isdir(os.path.dirname(a.control)) else None, world)
    httpd = ThreadingHTTPServer((a.host, a.port), make_handler(world, sprites, page, a.minimap, ctl))
    print('MyV2 Editor: open http://localhost:%d in your browser.%s Ctrl+C to quit.' %
          (a.port, ' (The game server is running: view only.)' if server_running() else ''))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        if world.dirty:
            print('\nQuit with unsaved changes - they were not written.')
        print('Bye.')


PAGE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MyV2 Editor</title>
<link rel="icon" href="/icon.ico">
<style>
:root {
  --bg: #121316; --rail: #17181c; --panel: #1b1c20; --panel2: #232429; --panel3: #2b2d33; --line: #2f3137; --text: #e7e4dc;
  --dim: #8f8c84; --dim2: #6c6a64; --gold: #d6a443; --gold2: #f0c463; --goldbg: #3a2f17; --ok: #6cc070; --okbg: #1d2e1f; --bad: #e0675a; --badbg: #3a1f1c;
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; background: var(--bg); color: var(--text); font: 13px/1.4 system-ui, "Segoe UI", sans-serif; overflow: hidden; }
button, input, select { font: inherit; color: var(--text); }
button { cursor: pointer; background: none; border: 0; }
input[type=text], input[type=number], select { background: var(--panel2); border: 1px solid var(--line); border-radius: 6px; padding: 5px 9px; outline: none; }
input[type=text]:focus, input[type=number]:focus { border-color: var(--gold); }
input[type=checkbox] { accent-color: var(--gold); width: 15px; height: 15px; margin: 0; }
kbd { background: var(--panel3); border: 1px solid var(--line); border-radius: 3px; padding: 0 4px; font: 11px ui-monospace, Consolas, monospace; color: var(--text); }
.mono { font-family: ui-monospace, Consolas, monospace; }
svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; display: block; }

/* layout */
#app { display: grid; grid-template-columns: 64px 280px 1fr 280px; grid-template-rows: 52px 1fr; height: 100%; }
#app.noright { grid-template-columns: 64px 280px 1fr 0; }
header { grid-column: 1 / -1; display: flex; align-items: center; gap: 14px; padding: 0 14px; border-bottom: 1px solid var(--line); background: var(--rail); }
.logo { display: flex; align-items: center; gap: 10px; font-weight: 600; font-size: 15px; min-width: 316px; }
.logo img { width: 32px; height: 32px; border-radius: 6px; image-rendering: pixelated; box-shadow: 0 0 0 1px #3b3d44; }
.logo .ed { color: var(--gold); }
#search { position: relative; flex: 1; max-width: 560px; margin: 0 auto; }
#search input { width: 100%; padding: 8px 12px 8px 34px; border-radius: 8px; background: var(--panel); }
#search > svg { position: absolute; left: 11px; top: 9px; width: 16px; height: 16px; color: var(--dim); }
#search .hint { position: absolute; right: 9px; top: 7px; }
#results { position: absolute; left: 0; right: 0; top: 40px; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; max-height: 420px; overflow-y: auto; display: none; z-index: 20; box-shadow: 0 12px 30px rgba(0,0,0,.5); }
#results .r { display: flex; gap: 10px; align-items: center; padding: 6px 10px; cursor: pointer; }
#results .r:hover, #results .r.act { background: var(--panel3); }
#results .r canvas { width: 30px; height: 30px; flex: none; }
#results .ty { font-size: 10px; text-transform: uppercase; letter-spacing: .06em; color: var(--dim2); width: 46px; flex: none; }
#results .sub { color: var(--dim); font-size: 11px; margin-left: auto; }
#pill { margin-left: auto; padding: 4px 12px; border-radius: 99px; font-size: 12px; white-space: nowrap; }
#pill.up { background: var(--okbg); color: var(--ok); border: 1px solid #2c4a2f; }
#pill.down { background: var(--goldbg); color: var(--gold2); border: 1px solid #574420; }

nav { background: linear-gradient(180deg, #1f1b15 0%, #15130f 100%); border-right: 1px solid #3a3022; display: flex; flex-direction: column; align-items: center; padding: 10px 0; gap: 8px; }
nav button { position: relative; width: 56px; color: #a8987a; display: flex; flex-direction: column; align-items: center; gap: 4px; font-size: 10.5px; letter-spacing: .02em; }
nav button .ico { width: 42px; height: 42px; border-radius: 3px; display: grid; place-items: center;
  background: radial-gradient(circle at 50% 35%, #3a3226 0%, #221d16 75%); border: 1px solid #4d4130;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,.55), inset 0 2px 3px rgba(255,230,170,.06); }
nav button svg { width: 22px; height: 22px; stroke-width: 1.6; }
nav button:hover { color: #eadcb9; }
nav button:hover .ico { border-color: #8a7140; color: #fff3d6; }
nav button.on { color: #f0c463; }
nav button.on .ico { color: #ffe39a; border-color: #d6a443; background: radial-gradient(circle at 50% 35%, #5a4520 0%, #2a2014 80%);
  box-shadow: 0 0 10px rgba(214,164,67,.35), inset 0 0 0 1px rgba(0,0,0,.4); }
nav button.on::after { content: ''; position: absolute; right: -4px; top: 13px; width: 3px; height: 18px; border-radius: 2px; background: #d6a443; }
nav .grow { flex: 1; }

#left { background: var(--panel); border-right: 1px solid var(--line); display: flex; flex-direction: column; min-height: 0; }
.tabs { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; padding: 10px 10px 10px; border-bottom: 1px solid #3a3022; }
.tabs button { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 6px 2px 4px; border-radius: 3px; color: #a8987a; font-size: 11px;
  background: linear-gradient(180deg, #29231a, #1c1913); border: 1px solid #40362a; }
.tabs button svg { width: 18px; height: 18px; stroke-width: 1.6; }
.tabs button:hover { color: #fff3d6; border-color: #8a7140; }
.tabs button.on { color: #ffe39a; border-color: #d6a443; background: linear-gradient(180deg, #4a3a1c, #2a2014); box-shadow: 0 0 8px rgba(214,164,67,.25); }
.seg { display: grid; grid-auto-flow: column; grid-auto-columns: 1fr; gap: 4px; margin: 2px 0 10px; }
.seg button { padding: 6px 4px; border-radius: 3px; color: #a8987a; background: linear-gradient(180deg, #29231a, #1c1913); border: 1px solid #40362a; font-size: 12px; }
.seg button:hover { color: #fff3d6; border-color: #8a7140; }
.seg button.on { color: #ffe39a; border-color: #d6a443; background: linear-gradient(180deg, #4a3a1c, #2a2014); }
.newnpc { background: var(--panel2); border: 1px solid #40362a; border-radius: 4px; padding: 10px; margin-bottom: 12px; display: flex; flex-direction: column; gap: 6px; }
.newnpc .lb { color: var(--dim); font-size: 12px; }
.newnpc .hint { color: var(--dim2); font-size: 11.5px; }
.newnpc input[type=text] { width: 100%; }
.newnpc .seg { margin: 0; }
.newnpc .looks { display: grid; grid-template-columns: repeat(5, 1fr); gap: 4px; max-height: 210px; overflow-y: auto; }
.newnpc .look { border: 1px solid #40362a; border-radius: 3px; display: grid; place-items: center; cursor: pointer; background: #1c1913; }
.newnpc .look:hover { border-color: #8a7140; }
.newnpc .look.on { border-color: #d6a443; box-shadow: 0 0 6px rgba(214,164,67,.35); }
#palwrap .row button.sm { color: var(--dim); border: 1px solid var(--line); border-radius: 5px; padding: 1px 7px; font-size: 11px; }
#palwrap .row button.sm:hover { color: var(--text); border-color: var(--gold); }
.tabs button.title { grid-column: 1 / -1; flex-direction: row; justify-content: center; gap: 8px; font-size: 12.5px; padding: 7px; }
#lsearch { margin: 10px; }
.sect { font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--dim2); padding: 6px 12px 6px; }
#palwrap { flex: 1; overflow-y: auto; padding: 0 8px 10px 10px; min-height: 0; }
.grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
.cell { aspect-ratio: 1 / 1.08; background: var(--panel2); border: 1px solid var(--line); border-radius: 7px; cursor: pointer; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; padding: 2px 2px 3px; font: 10px ui-monospace, Consolas, monospace; color: var(--dim); overflow: hidden; text-align: center; line-height: 1.1; }
.cell:hover { border-color: #4a4c53; }
.cell.sel { border-color: var(--gold); background: var(--goldbg); color: var(--gold2); box-shadow: 0 0 0 1px var(--gold) inset; }
.cell canvas { width: 100%; flex: 1; min-height: 0; object-fit: contain; }
.cell .sw { width: 20px; height: 20px; border-radius: 5px; margin: auto 0 6px; }
.cell .lab { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
.list .row { display: flex; gap: 10px; align-items: center; padding: 5px 6px; border-radius: 6px; cursor: pointer; border: 1px solid transparent; }
.list .row:hover { background: var(--panel2); }
.list .row.sel { border-color: var(--gold); background: var(--goldbg); }
.list .row canvas { width: 34px; height: 34px; flex: none; }
.list .row .n { color: var(--dim); font-size: 11px; }
.empty { color: var(--dim); padding: 10px 4px; }
#card { border-top: 1px solid var(--line); padding: 10px 12px; display: flex; gap: 12px; align-items: center; min-height: 62px; }
#card canvas { width: 40px; height: 40px; flex: none; background: var(--panel2); border-radius: 6px; }
#card .t { font-weight: 600; }
#card .s { color: var(--dim); font-size: 12px; }
#card.mix { flex-direction: column; align-items: stretch; gap: 8px; max-height: 46%; overflow-y: auto; }
#card .mixhd { display: flex; align-items: baseline; gap: 8px; }
#card .mixhd .t { flex: 1; }
.mixrow { display: flex; align-items: center; gap: 8px; }
.mixrow canvas { width: 30px !important; height: 30px !important; }
.mixrow .num { width: 40px; font: 11px ui-monospace, Consolas, monospace; color: var(--dim); }
.mixrow input[type=range] { flex: 1; accent-color: var(--gold); min-width: 0; }
.mixrow .pct { width: 34px; text-align: right; font-size: 11px; color: var(--dim); }
.mixrow .x, .mixbtns button { color: var(--dim); border: 1px solid var(--line); border-radius: 5px; padding: 1px 7px; font-size: 11px; }
.mixrow .x:hover { color: var(--bad); border-color: var(--bad); }
.mixbtns { display: flex; gap: 6px; flex-wrap: wrap; }
.mixbtns button:hover { color: var(--text); border-color: var(--gold); }
.cell .badge { position: absolute; top: 3px; right: 4px; font-size: 9px; color: var(--gold2); }
.cell { position: relative; }
.cell.inmix { border-color: #8a6a2a; }

#view { position: relative; min-width: 0; min-height: 0; overflow: hidden; background: #050506; }
#cv { width: 100%; height: 100%; display: block; }
/* map tools: a hotbar column on the left, view switches top right, zoom at the bottom */
#tools { position: absolute; left: 10px; top: 10px; display: flex; flex-direction: row; align-items: center; gap: 4px; padding: 5px 6px; z-index: 3;
  background: linear-gradient(180deg, #2a241b 0%, #1a1712 100%); border: 1px solid #4a3d26; border-radius: 4px;
  box-shadow: 0 6px 18px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,220,150,.08); }
#tools .sep { width: 1px; align-self: stretch; margin: 2px 4px; background: linear-gradient(180deg, transparent, #6b5630, transparent); }
.slot { position: relative; width: 40px; height: 40px; border-radius: 3px; color: #d8c9a6; display: grid; place-items: center;
  background: radial-gradient(circle at 50% 35%, #3a3226 0%, #221d16 75%); border: 1px solid #4d4130;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,.55), inset 0 2px 3px rgba(255,230,170,.06); }
.slot svg { width: 22px; height: 22px; stroke-width: 1.6; }
.slot i { position: absolute; right: 3px; bottom: 1px; font: 600 9px ui-monospace, Consolas, monospace; font-style: normal; color: #9c8a64; }
.slot:hover:not(:disabled) { color: #fff3d6; border-color: #8a7140; }
.slot.on { color: #ffe39a; border-color: #d6a443; background: radial-gradient(circle at 50% 35%, #5a4520 0%, #2a2014 80%);
  box-shadow: 0 0 10px rgba(214,164,67,.35), inset 0 0 0 1px rgba(0,0,0,.4); }
.slot.on::before { content: ''; position: absolute; bottom: -6px; left: 12px; height: 3px; width: 16px; border-radius: 2px; background: #d6a443; }
.slot:disabled { opacity: .35; cursor: default; }
.slot.sz { font: 700 13px ui-monospace, Consolas, monospace; color: #e8d8b0; }
.slot.sz small { position: absolute; left: 3px; top: 1px; font-size: 8px; color: #9c8a64; font-weight: 500; }
#view.hasban #tools { top: 44px; }
#view.hasban #viewbar { top: 43px; }
#viewbar { position: absolute; right: 26px; top: 9px; display: flex; gap: 6px; z-index: 3; }
#tright { position: absolute; right: 0; top: 50%; transform: translateY(-50%); z-index: 3; width: 18px; height: 70px; border-radius: 7px 0 0 7px;
  background: linear-gradient(90deg, #2a241b, #1f1b15); border: 1px solid #4a3d26; border-right: 0; color: #d6a443; font: 700 18px/1 system-ui; display: grid; place-items: center; padding: 0 0 2px; }
#tright:hover { color: #ffe39a; background: linear-gradient(90deg, #3a3022, #251f17); }
#viewbar .rnd { width: 42px; height: 42px; border-radius: 50%; display: grid; place-items: center; color: #cfc3a6;
  background: radial-gradient(circle at 50% 30%, #332c21, #1b1813); border: 1px solid #4d4130; box-shadow: 0 3px 10px rgba(0,0,0,.45); }
#viewbar .rnd svg { width: 24px; height: 24px; }
#viewbar .rnd:hover { color: #fff3d6; border-color: #8a7140; }
#viewbar .rnd.on { color: #ffe39a; border-color: #d6a443; box-shadow: 0 0 9px rgba(214,164,67,.4); }
#zoombar { position: absolute; left: 50%; transform: translateX(-50%); bottom: 10px; display: flex; align-items: center; gap: 8px; z-index: 3;
  background: rgba(26,23,18,.92); border: 1px solid #4a3d26; border-radius: 4px; padding: 4px 10px; }
#zoombar button { color: #cfc3a6; width: 22px; height: 22px; display: grid; place-items: center; }
#zoombar button svg { width: 16px; height: 16px; }
#zoombar button:hover { color: #fff3d6; }
#zoombar input[type=range] { width: 140px; accent-color: #d6a443; }
#zoombar .zv { width: 44px; text-align: right; color: #b8a982; font: 12px ui-monospace, Consolas, monospace; }
#size { display: none; }
#bar .rgt { margin-left: auto; }
#coords { position: absolute; left: 10px; bottom: 10px; background: rgba(23,24,28,.92); border: 1px solid var(--line); border-radius: 7px; padding: 4px 10px; color: var(--dim); font: 12px ui-monospace, Consolas, monospace; pointer-events: none; z-index: 3; }
#mini { position: absolute; right: 10px; bottom: 10px; width: 220px; height: 220px; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; background: #000; z-index: 3; box-shadow: 0 6px 20px rgba(0,0,0,.5); display: none; }
#mini .t { position: absolute; left: 8px; top: 5px; font-size: 10px; letter-spacing: .08em; color: rgba(255,255,255,.65); text-shadow: 0 1px 2px #000; pointer-events: none; }
#mini canvas { width: 100%; height: 100%; cursor: crosshair; image-rendering: pixelated; }
#world { position: absolute; inset: 0; background: rgba(5,5,6,.82); z-index: 10; display: none; place-items: center; }
#world canvas { width: min(92%, 88vh); aspect-ratio: 1; image-rendering: pixelated; border: 1px solid var(--line); border-radius: 8px; cursor: crosshair; }
#world .t { position: absolute; top: 14px; color: var(--dim); }
#banner.live { background: var(--okbg); color: #d6f5d8; border-color: #2f5a33; }
#banner { position: absolute; left: 0; right: 0; top: 0; background: var(--badbg); color: #ffd6cf; border-bottom: 1px solid #5a2c26; padding: 7px 14px 7px 70px; z-index: 4; display: none; font-size: 12px; }
#toast { position: absolute; left: 50%; transform: translateX(-50%); bottom: 16px; max-width: 70%; background: var(--panel); border: 1px solid var(--line); border-left: 3px solid var(--gold); padding: 8px 14px; border-radius: 7px; display: none; z-index: 12; white-space: pre-line; }

#srv { grid-column: 3 / 5; overflow-y: auto; padding: 20px 24px 40px; display: none; background: var(--bg); }
#app.srvmode #view, #app.srvmode #right { display: none; }
#app.srvmode #srv { display: block; }
#app.srvmode #left { display: none; }
#app.srvmode { grid-template-columns: 64px 0 1fr 0; }
.sgrid { display: grid; grid-template-columns: minmax(320px, 1fr) minmax(320px, 1fr); gap: 16px; max-width: 1400px; }
.box { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; min-width: 0; }
.box h3 { margin: 0 0 10px; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--dim2); font-weight: 600; display: flex; align-items: center; gap: 8px; }
.box.wide { grid-column: 1 / -1; }
.big { font-size: 22px; font-weight: 600; display: flex; align-items: center; gap: 10px; }
.dotst { width: 11px; height: 11px; border-radius: 50%; background: var(--dim2); }
.dotst.up { background: var(--ok); box-shadow: 0 0 8px var(--ok); }
.facts { display: flex; gap: 22px; margin: 10px 0 14px; color: var(--dim); flex-wrap: wrap; }
.facts b { color: var(--text); font-weight: 600; }
.acts { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.btn.sec { background: var(--panel3); border: 1px solid var(--line); }
.btn.sec:hover:not(:disabled) { border-color: var(--gold); }
.btn.danger:hover:not(:disabled) { border-color: var(--bad); color: #ffd6cf; }
.jobbox { margin-top: 12px; background: #0e0f11; border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; font: 12px/1.5 ui-monospace, Consolas, monospace; color: #c9c6be; max-height: 220px; overflow-y: auto; white-space: pre-wrap; display: none; }
table.pl { width: 100%; border-collapse: collapse; }
table.pl td, table.pl th { text-align: left; padding: 6px 6px; border-bottom: 1px solid var(--line); white-space: nowrap; }
table.pl th { color: var(--dim2); font-weight: 500; font-size: 12px; }
table.pl td.w { white-space: normal; color: var(--dim); }
table.pl button { color: var(--dim); border: 1px solid var(--line); border-radius: 5px; padding: 1px 7px; font-size: 11px; margin-right: 3px; }
table.pl button:hover { color: var(--text); border-color: var(--gold); }
.row2 { display: flex; gap: 8px; }
.row2 input { flex: 1; min-width: 0; }
#conout, #logbox { background: #0e0f11; border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; font: 12px/1.45 ui-monospace, Consolas, monospace; color: #c9c6be; white-space: pre-wrap; overflow-y: auto; }
#conout { height: 180px; margin-top: 8px; }
#logbox { height: 340px; }
.req { padding: 5px 0; border-bottom: 1px solid var(--line); color: var(--dim); font-size: 12px; }
.req b { color: var(--text); font-weight: 500; }
#right { background: var(--panel); border-left: 1px solid var(--line); display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
#rscroll { flex: 1; overflow-y: auto; padding: 4px 14px 10px; min-height: 0; }
#right .sect { padding: 14px 0 8px; }
#tile { color: var(--dim); }
#tile .hd { color: var(--text); font-weight: 600; }
#tile .kv { display: grid; grid-template-columns: 62px 1fr; gap: 6px 8px; align-items: center; margin-top: 8px; }
#tile .kv .k { color: var(--dim2); font-size: 12px; }
#tile .kv .v { display: flex; gap: 6px; align-items: center; min-width: 0; }
#tile .kv canvas { width: 28px; height: 28px; flex: none; background: var(--panel2); border-radius: 4px; }
#tile .kv input[type=number] { width: 72px; padding: 3px 6px; }
#tile .x { color: var(--dim); padding: 1px 6px; border: 1px solid var(--line); border-radius: 5px; font-size: 11px; }
#tile .x:hover { color: var(--bad); border-color: var(--bad); }
#tile .nm { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text); }
#tile .ied { margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--line); display: flex; flex-direction: column; gap: 6px; }
#tile .ied .lb { color: var(--dim2); font-size: 12px; }
#tile .ied input[type=text], #tile .ied textarea { width: 100%; background: var(--panel2); border: 1px solid var(--line); border-radius: 6px; padding: 4px 8px; color: var(--text); font: inherit; }
#tile .ied textarea { height: 54px; resize: vertical; }
#tile .ied .dest { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
#tile .ied .dest input { width: 64px; }
#tile .ied .dgrid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 4px; }
#tile .ied .dgrid input { width: 100%; padding: 3px 4px; font-size: 11px; }
#tile .ied .warn { color: var(--gold2); font-size: 12px; }
#tile .ied button.sm { color: var(--dim); border: 1px solid var(--line); border-radius: 5px; padding: 2px 8px; font-size: 12px; }
#tile .ied button.sm:hover { color: var(--text); border-color: var(--gold); }
#tile .ied button.sm.on { color: var(--gold2); border-color: var(--gold); background: var(--goldbg); }
.face { display: flex; gap: 4px; flex-wrap: wrap; align-items: center; }
.face button { color: var(--dim); border: 1px solid var(--line); border-radius: 5px; padding: 2px 8px; font-size: 12px; }
.face button:hover { color: var(--text); border-color: var(--gold); }
.face button.on { color: var(--gold2); border-color: var(--gold); background: var(--goldbg); }
#tile .ied .note { color: var(--dim); font-size: 12px; }
#tile .chestg { display: flex; flex-direction: column; gap: 6px; }
#tile .chestg .rw { display: flex; flex-direction: column; gap: 4px; padding: 6px; border: 1px solid #40362a; border-radius: 4px; background: #1c1913; }
#tile .chestg .ipick { display: flex; gap: 5px; align-items: center; flex-wrap: wrap; }
#tile .chestg input[type=number] { width: 64px; padding: 3px 6px; }
#tile .chestg select { padding: 3px 6px; max-width: 100%; }
#tile .chestg .hint { color: var(--dim2); font-size: 11px; }
#tile .chestg .chips { display: flex; flex-wrap: wrap; gap: 3px; }
#tile .chestg .chip { padding: 2px 7px; border-radius: 10px; font-size: 11px; color: #a8987a; border: 1px solid #40362a; background: #221d16; }
#tile .chestg .chip:hover { color: #fff3d6; border-color: #8a7140; }
#tile .chestg .chip.on { color: #ffe39a; border-color: #d6a443; background: #3a2f17; }
#tile .flg { display: grid; grid-template-columns: 1fr 1fr; gap: 3px 8px; margin-top: 8px; }
.chk { display: flex; align-items: center; gap: 8px; padding: 3px 0; cursor: pointer; user-select: none; }
.chk .dot { width: 9px; height: 9px; border-radius: 3px; flex: none; }
.chk span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.flags2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0 10px; }
.keys { color: var(--dim); font-size: 12px; line-height: 1.75; }
#foot { border-top: 1px solid var(--line); padding: 12px 14px; }
#dirty { color: var(--dim); margin-bottom: 8px; }
#dirty.on { color: var(--gold2); }
.btns { display: flex; gap: 8px; align-items: center; }
.btn { padding: 7px 14px; border-radius: 7px; }
.btn.pri { background: #9a7428; color: #fff7e6; font-weight: 600; }
.btn.pri:hover:not(:disabled) { background: #b38630; }
.btn.ghost { color: var(--dim); }
.btn.ghost:hover:not(:disabled) { color: var(--text); }
.btn:disabled { opacity: .4; cursor: default; }
#undosave { margin-top: 8px; color: var(--dim2); font-size: 12px; padding: 0; }
#undosave:hover:not(:disabled) { color: var(--text); }
#undosave:disabled { opacity: .5; cursor: default; }
/* template editor */
#tpl { position: fixed; inset: 0; background: rgba(5,5,6,.72); z-index: 30; display: none; place-items: center; }
#tpl.on { display: grid; }
#tpl.picking { background: transparent; pointer-events: none; }
#tpl.picking .mbox { display: none; }
#tpl .mbox { width: min(980px, 94vw); height: min(760px, 92vh); background: var(--panel); border: 1px solid var(--line); border-radius: 12px; display: grid; grid-template-rows: auto auto 1fr auto; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,.5); }
#tpl .mhd { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-bottom: 1px solid var(--line); }
#tpl .mhd .ttl { font-size: 15px; font-weight: 650; flex: 1; }
#tpl .mhd .ttl small { color: var(--dim); font-weight: 400; margin-left: 8px; }
#tpl .mtabs { display: flex; gap: 2px; padding: 0 12px; border-bottom: 1px solid var(--line); overflow-x: auto; }
#tpl .mtabs button { padding: 9px 12px; color: var(--dim); border-bottom: 2px solid transparent; white-space: nowrap; }
#tpl .mtabs button.on { color: var(--gold2); border-bottom-color: var(--gold); }
#tpl .mbody { overflow-y: auto; padding: 14px 18px 24px; }
#tpl .cbar { display: flex; height: 22px; border-radius: 6px; overflow: hidden; margin: 2px 0 12px; border: 1px solid var(--line); }
#tpl .cbar div { min-width: 18px; display: grid; place-items: center; font-size: 11px; color: #15120d; font-weight: 700; border-right: 1px solid rgba(0,0,0,.35); }
#tpl .rwl { display: flex; flex-direction: column; gap: 10px; }
#tpl .rwc { border: 1px solid #40362a; border-left: 4px solid; border-radius: 8px; background: #1c1913; padding: 10px 12px; display: flex; flex-direction: column; gap: 10px; }
#tpl .rwh { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
#tpl .rwh > b { color: var(--dim); min-width: 14px; }
#tpl .rwh .sp { flex: 1; }
#tpl .rwh .pct { color: var(--gold2); font-weight: 650; min-width: 38px; }
#tpl .rwh .ipick input { width: 64px; }
#tpl .seg2 { display: flex; border: 1px solid #40362a; border-radius: 7px; overflow: hidden; }
#tpl .seg2 button { padding: 4px 10px; color: #a8987a; background: #221d16; border-right: 1px solid #40362a; font-size: 12px; }
#tpl .seg2 button:last-child { border-right: 0; }
#tpl .seg2 button.on { color: #ffe39a; background: #3a2f17; }
#tpl .chips { display: flex; flex-wrap: wrap; gap: 4px; }
#tpl .chip { padding: 3px 10px; border-radius: 12px; font-size: 12px; color: #a8987a; border: 1px solid #40362a; background: #221d16; }
#tpl .chip:hover { color: #fff3d6; border-color: #8a7140; }
#tpl .chip.on { color: #ffe39a; border-color: #d6a443; background: #3a2f17; }
#tpl .rwadd { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 14px; }
#tpl .note2 { line-height: 1.6; }
#tpl .grid2 > label { display: flex; gap: 8px; align-items: center; }
#tpl .mft { display: flex; gap: 10px; align-items: center; padding: 10px 16px; border-top: 1px solid var(--line); flex-wrap: wrap; }
#tpl .mft .sp { flex: 1; }
#tpl .grid2 { display: grid; grid-template-columns: 170px 1fr; gap: 8px 14px; align-items: center; }
#tpl .grid2 > .lb { color: var(--dim); }
#tpl .hint { color: var(--dim2); font-size: 12px; }
#tpl h4 { margin: 18px 0 8px; color: var(--gold2); font-size: 13px; font-weight: 650; }
#tpl h4:first-child { margin-top: 0; }
#tpl input[type=text], #tpl textarea { width: 100%; }
#tpl textarea { background: var(--panel2); border: 1px solid var(--line); border-radius: 6px; padding: 5px 9px; color: var(--text); font: inherit; height: 60px; resize: vertical; outline: none; }
#tpl input[type=number] { width: 90px; }
#tpl .chks { display: flex; flex-wrap: wrap; gap: 6px 16px; }
#tpl .chks label { display: flex; gap: 6px; align-items: center; }
#tpl table.st { border-collapse: collapse; }
#tpl table.st td, #tpl table.st th { padding: 3px 10px 3px 0; text-align: left; }
#tpl table.st th { color: var(--dim2); font-weight: 500; font-size: 12px; }
#tpl table.st input { width: 72px; }
#tpl .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 0 28px; }
#tpl .ipick { display: flex; gap: 6px; align-items: center; min-width: 0; }
#tpl .ipick input { width: 76px; }
#tpl .ipick .nm { color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; min-width: 0; }
#tpl .ipick .nm.none { color: var(--dim2); }
#tpl button.sm { color: var(--dim); border: 1px solid var(--line); border-radius: 5px; padding: 2px 8px; font-size: 12px; white-space: nowrap; }
#tpl button.sm:hover { color: var(--text); border-color: var(--gold); }
#tpl .stop { display: grid; grid-template-columns: 28px 70px 70px auto; gap: 6px; align-items: center; margin-bottom: 6px; }
#tpl .dgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 6px 14px; }
#tpl .dgrid label { display: grid; grid-template-columns: 1fr 86px; gap: 6px; align-items: center; color: var(--dim); font-size: 12px; }
#tpl .dgrid label input { width: 86px; }
#tpl .note { background: var(--panel2); border: 1px solid var(--line); border-radius: 8px; padding: 9px 12px; color: var(--dim); margin: 10px 0; }
#ipop { position: fixed; z-index: 40; width: 340px; max-height: 380px; background: var(--panel); border: 1px solid var(--gold); border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,.5); display: none; flex-direction: column; }
#ipop input { margin: 8px; }
#ipop .lst { overflow-y: auto; padding: 0 4px 6px; }
#ipop .r { display: flex; gap: 8px; align-items: center; padding: 3px 6px; border-radius: 5px; cursor: pointer; }
#ipop .r:hover { background: var(--panel3); }
#ipop .r .n { color: var(--dim2); font-size: 11px; margin-left: auto; }
</style>
</head>
<body>
<div id="app">
<header>
  <div class="logo"><img src="/icon.ico" alt=""><div>MyV2 <span class="ed">Editor</span></div></div>
  <div id="search">
    <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
    <input id="q" type="text" placeholder="Search items, NPCs, players, places… or type x y" autocomplete="off">
    <span class="hint"><kbd>Ctrl K</kbd></span>
    <div id="results"></div>
  </div>
  <div id="pill" class="down">…</div>
</header>

<nav>
  <button data-m="map" class="on" title="Build the map"><span class="ico"><svg viewBox="0 0 24 24"><path d="M4 5c3-1.5 5 1.5 8 0s5-1.5 8 0v14c-3-1.5-5 1.5-8 0s-5-1.5-8 0z"/><path d="M7 9.5l2 1.5 3-2 2 2.5" stroke-dasharray="1.6 1.6"/><path d="M15.5 13.5l3 3M18.5 13.5l-3 3"/></svg></span>Map</button>
  <button data-m="players" title="Player characters: stats, backpack, depot, history, character file"><span class="ico"><svg viewBox="0 0 24 24"><path d="M5 13c0-5 3-9 7-9s7 4 7 9v5l-2 2H7l-2-2z"/><path d="M5 12.5h14M12 12.5V20M8.5 15.5h1.5M14 15.5h1.5"/></svg></span>Players</button>
  <button data-m="npcs" title="Every NPC and player in the world"><span class="ico"><svg viewBox="0 0 24 24"><path d="M12 3c-4 0-6.5 3.5-6.5 8.5V21h13v-9.5C18.5 6.5 16 3 12 3z"/><path d="M8.5 13c.5-3 1.8-4.5 3.5-4.5s3 1.5 3.5 4.5c-1 1.5-2.2 2-3.5 2s-2.5-.5-3.5-2z"/></svg></span>NPCs</button>
  <button data-m="history" title="What you changed, and the saves"><span class="ico"><svg viewBox="0 0 24 24"><path d="M6 3h12M6 21h12"/><path d="M7 3c0 5 5 6 5 9s-5 4-5 9M17 3c0 5-5 6-5 9s5 4 5 9"/><path d="M9.5 18.5h5" opacity=".6"/></svg></span>History</button>
  <button data-m="server" title="Run and control the game server"><span class="ico"><svg viewBox="0 0 24 24"><path d="M5 21V8h2V5h2v3h2V5h2v3h2V5h2v3h2v13z"/><path d="M10 21v-4a2 2 0 0 1 4 0v4M8 12h2M14 12h2"/></svg></span>Server</button>
  <div class="grow"></div>
  <button data-m="help" title="How it works"><span class="ico"><svg viewBox="0 0 24 24"><path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17a3 3 0 0 1 3-3h11"/><path d="M10.5 7.5a2 2 0 1 1 2.6 1.9c-.6.2-1.1.6-1.1 1.2"/></svg></span>Help</button>
</nav>

<aside id="left">
  <div class="tabs" id="tabs"></div>
  <input id="lsearch" type="text" placeholder="Search name or number" autocomplete="off">
  <div id="palwrap"></div>
  <div id="card"></div>
</aside>

<main id="view">
  <canvas id="cv"></canvas>
  <div id="tools">
    <div id="toolgrp" style="display:flex;flex-direction:row;gap:4px"></div>
    <div class="sep"></div>
    <button class="slot sz" id="szbtn" title="Brush size: click for bigger, right-click for smaller ([ and ])"><small>size</small><span>1</span></button>
    <select id="size"><option value="1">1×1</option><option value="2">2×2</option><option value="3">3×3</option><option value="5">5×5</option><option value="7">7×7</option><option value="9">9×9</option></select>
    <div class="sep"></div>
    <button class="slot" id="undo" title="Undo (Ctrl+Z)"><svg viewBox="0 0 24 24"><path d="M8 7H4V3"/><path d="M4.6 7A8 8 0 1 1 4 13"/><circle cx="12" cy="12" r="1.2"/></svg></button>
    <button class="slot" id="redo" title="Redo (Ctrl+Y)"><svg viewBox="0 0 24 24"><path d="M16 7h4V3"/><path d="M19.4 7A8 8 0 1 0 20 13"/><circle cx="12" cy="12" r="1.2"/></svg></button>
  </div>
  <div id="viewbar">
    <button class="rnd" id="tgrid" title="Grid (G)"><svg viewBox="0 0 24 24"><rect x="3.5" y="3.5" width="17" height="17" rx="1"/><path d="M9.2 3.5v17M14.8 3.5v17M3.5 9.2h17M3.5 14.8h17"/></svg></button>
    <button class="rnd" id="twalls" title="See through walls (W)"><svg viewBox="0 0 24 24"><rect x="2.5" y="3.5" width="8.5" height="4.5" rx=".6" fill="currentColor" fill-opacity="0.0" stroke-dasharray="1.5 1.3" stroke-opacity=".7"/><rect x="12.5" y="3.5" width="9" height="4.5" rx=".6" fill="currentColor" fill-opacity="0.0" stroke-dasharray="1.5 1.3" stroke-opacity=".7"/><rect x="2.5" y="10" width="4" height="4.5" rx=".6" fill="currentColor" fill-opacity="0.45"/><rect x="8" y="10" width="8" height="4.5" rx=".6" fill="currentColor" fill-opacity="0.4"/><rect x="17.5" y="10" width="4" height="4.5" rx=".6" fill="currentColor" fill-opacity="0.12" stroke-dasharray="1.5 1.3" stroke-opacity=".7"/><rect x="2.5" y="16.5" width="8.5" height="4.5" rx=".6" fill="currentColor" fill-opacity="0.95"/><rect x="12.5" y="16.5" width="9" height="4.5" rx=".6" fill="currentColor" fill-opacity="0.6"/></svg></button>
    <button class="rnd" id="tlight" title="Light from lamps, as at night (L)"><svg viewBox="0 0 24 24"><path d="M3.5 11a8.6 8.6 0 0 1 14.6-5.2L20.5 8"/><path d="M20.5 3.3V8h-4.7"/><path d="M20.5 13a8.6 8.6 0 0 1-14.6 5.2L3.5 16"/><path d="M3.5 20.7V16h4.7"/><rect x="10.1" y="12" width="3.8" height="5.6" rx=".5" fill="currentColor" fill-opacity=".3"/><path d="M12 12v-1.1"/><path d="M12 10.6c-1.3-.8-1.4-2.3-.3-3.8.3 1 .8 1.3 1.1 1.4-.1-.7.2-1.4.7-1.8.2 1.5 1 2.1.3 3.4-.3.6-1 1-1.8.8z" fill="currentColor" stroke-width=".9"/></svg></button>
    <button class="rnd" id="tref" title="Load the world again from disk"><svg viewBox="0 0 24 24"><path d="M3.5 11a8.6 8.6 0 0 1 14.6-5.2L20.5 8"/><path d="M20.5 3.3V8h-4.7"/><path d="M20.5 13a8.6 8.6 0 0 1-14.6 5.2L3.5 16"/><path d="M3.5 20.7V16h4.7"/><circle cx="12" cy="12" r="4.9"/><path d="M7.1 12h9.8M12 7.1c-1.7 1.5-1.7 8.3 0 9.8M12 7.1c1.7 1.5 1.7 8.3 0 9.8"/></svg></button>
  </div>
  <button id="tright" title="Hide the right panel">›</button>
  <div id="zoombar">
    <button id="zout" title="Zoom out (wheel)"><svg viewBox="0 0 24 24"><path d="M12 5 19 12 12 19 5 12z"/><path d="M9 12h6"/></svg></button>
    <input type="range" id="zr" min="0" max="100" step="1" title="Zoom (mouse wheel)">
    <button id="zin" title="Zoom in (wheel)"><svg viewBox="0 0 24 24"><path d="M12 3 21 12 12 21 3 12z"/><path d="M8.5 12h7M12 8.5v7"/></svg></button>
    <span class="zv" id="zv">100%</span>
  </div>
  <div id="banner">The game server is running: you can look around, but editing is off. Stop the server to edit.</div>
  <div id="coords">–</div>
  <div id="mini"><span class="t">MAP</span><canvas id="mcv" width="1024" height="1024" title="Click to go there · M for the big map"></canvas></div>
  <div id="tpl"><div class="mbox"><div class="mhd"><div class="ttl"></div><button class="btn ghost" onclick="closeTemplate()">✕</button></div><div class="mtabs"></div><div class="mbody"></div><div class="mft"></div></div></div>
  <div id="ipop"><input type="text" placeholder="Search an item by name or number"><div class="lst"></div></div>
  <div id="world"><span class="t">World map — click to go there · M or Esc to close</span><canvas id="wcv" width="1024" height="1024"></canvas></div>
  <div id="toast"></div>
</main>

<aside id="right">
  <div id="rscroll">
    <div class="sect">Tile</div>
    <div id="tile">Pick the select tool (<kbd>V</kbd>) and click a tile to see and change what is on it.</div>
    <div class="sect">Show</div>
    <div id="layers"></div>
    <div class="sect">Show flags</div>
    <div id="flagshow" class="flags2"></div>
    <div class="sect">Keys</div>
    <div class="keys">
      <kbd>V</kbd> select · <kbd>B</kbd> brush · <kbd>U</kbd> rectangle · <kbd>F</kbd> fill · <kbd>E</kbd> erase · <kbd>I</kbd> pick · <kbd>H</kbd> or <kbd>Space</kbd> move<br>
      Right-drag moves · wheel zooms · <kbd>[</kbd> <kbd>]</kbd> brush size<br>
      <kbd>Alt</kbd> paints the opposite (clears a flag, erases)<br>
      <kbd>Ctrl Z</kbd> / <kbd>Ctrl Y</kbd> undo / redo · <kbd>Ctrl S</kbd> save<br>
      <kbd>M</kbd> world map · <kbd>Ctrl K</kbd> search · <kbd>G</kbd> <kbd>W</kbd> <kbd>L</kbd> grid, walls, light
    </div>
  </div>
  <div id="foot">
    <div id="dirty">No unsaved changes</div>
    <div class="btns">
      <button class="btn pri" id="save">Save to the game</button>
      <button class="btn ghost" id="discard">Discard</button>
    </div>
    <button id="undosave" title="Put the world back as it was before the last save (from its backup)">Undo last save</button>
  </div>
</aside>

<section id="srv">
  <div class="sgrid">
    <div class="box">
      <h3>Game server</h3>
      <div class="big"><span class="dotst" id="sdot"></span><span id="sstate">…</span></div>
      <div class="facts" id="sfacts"></div>
      <div class="acts">
        <button class="btn pri" id="sstart">Start</button>
        <button class="btn sec" id="srestart">Restart</button>
        <button class="btn sec danger" id="sstop">Stop</button>
        <span style="color:var(--dim2);font-size:12px;margin-left:6px">Warn players</span>
        <select id="swarn"><option value="0">no wait</option><option value="30" selected>30 s</option><option value="60">1 min</option><option value="120">2 min</option><option value="300">5 min</option></select>
      </div>
      <div class="acts" style="margin-top:10px">
        <button class="btn sec" id="supcode" title="Stop, take the source Claude changed (claude-sync.sh get), rebuild, start">Update code &amp; restart</button>
        <button class="btn sec" id="supworld" title="Stop, take the world files from the Windows folder (claude-sync.sh get-world), start">Update world &amp; restart</button>
      </div>
      <div class="acts" style="margin-top:10px">
        <span style="color:var(--dim2);font-size:12px;margin-right:6px">Sync only</span>
        <button class="btn sec" id="ssend" title="Copy Ubuntu files to the Windows folder (claude-sync.sh send; world files only while stopped)">Send to Windows</button>
        <button class="btn sec" id="sget" title="Take changed source from Windows and rebuild, without restarting (claude-sync.sh get)">Get code</button>
        <button class="btn sec" id="sgetw" title="Take the world files from Windows (claude-sync.sh get-world; server must be stopped)">Get world</button>
      </div>
      <div class="jobbox" id="sjob"></div>
    </div>
    <div class="box">
      <h3>Announce</h3>
      <div class="row2"><input type="text" id="sann" placeholder="A message every player sees as [Server] …"><button class="btn sec" id="sannb">Send</button></div>
      <h3 style="margin-top:16px">Console</h3>
      <div class="row2"><input type="text" id="scmd" placeholder="help · who · raise Bob 5000 · gold Bob 50 · tell Bob hi · kick Bob"><button class="btn sec" id="scmdb">Run</button></div>
      <div id="conout"></div>
    </div>
    <div class="box wide">
      <h3>Players online <span id="pcount" style="color:var(--dim)"></span></h3>
      <div id="plist"></div>
    </div>
    <div class="box wide">
      <h3>Server log <label class="chk" style="margin-left:auto;text-transform:none;letter-spacing:0;font-weight:400"><input type="checkbox" id="lfollow" checked><span>follow</span></label>
        <input type="text" id="lfilter" placeholder="filter" style="width:180px;text-transform:none;letter-spacing:0;font-weight:400"></h3>
      <div id="logbox"></div>
    </div>
    <div class="box wide">
      <h3>Requests from Claude</h3>
      <div id="sreq" class="empty">None yet. When you ask Claude to check or restart the server, its requests show up here.</div>
    </div>
  </div>
</section>
</div>

<script>
'use strict';
const MAPX = 1024, CH = 32;
const $ = s => document.querySelector(s);
const cv = $('#cv'), ctx = cv.getContext('2d');
const base = document.createElement('canvas'), bctx = base.getContext('2d');
let W = 0, H = 0, cam = { x: 0, y: 0 }, zoom = 1;
let info = { running: false, online: 0, dirty: 0, undo: 0, redo: 0, areas: [], gen: 0, backups: 0 };
let pal = null, mode = 'map', tab = 'builder', tool = 'brush';
let brush = { kind: 'floor', s: 142, set: true };
let recent = [];
let size = 1;
const show = { floors: true, walls: true, items: true, chars: true, see: false, light: false, grid: false, names: true, npcnames: false };
try { show.npcnames = localStorage.getItem('myv2.npcnames') === '1'; } catch (e) {}
const flagOn = new Set();
let selTile = null;
const chunks = new Map(), sprites = new Map();
let hover = null, stroke = null, rect = null, panning = null, spaceDown = false, needDraw = true, baseDirty = true;

const FLAGS = ['blocks walking', 'blocks sight', 'indoors', 'under water', 'no lag', 'no monsters', 'bank', 'tavern',
  'no magic', 'death trap', 'no light', 'arena', 'lit', 'no expire', 'no fighting'];
const FCOL = ['#ef5a50', '#b48cff', '#5b8ff5', '#3cc9d8', '#8c96a8', '#47c98a', '#e8b44a', '#f08a3c', '#d468e8', '#ff5a3c', '#5d6470', '#f06ea6', '#ffe9a8', '#a6d65c', '#2fbfa0'];
const TOOLS = [     // the editor's own icon set: diamond tiles, quill, pickaxe, compass
  ['select', 'V', 'Select: look at a tile and change it', '<path d="M12 14 21 18.5 12 23 3 18.5z" opacity=".5"/><path d="M8 2v13l3.2-3 2.3 5 2-1-2.3-4.8H17z"/>'],
  ['brush', 'B', 'Brush: paint the chosen piece', '<g transform="rotate(45 12 12)"><rect x="10.6" y="0.5" width="2.8" height="11" rx="1.4"/><rect x="9.6" y="11.5" width="4.8" height="3" rx=".6"/><path d="M9.6 14.5h4.8v1.8c0 2.6-1.1 5-2.4 6.2-1.3-1.2-2.4-3.6-2.4-6.2z" fill="currentColor" fill-opacity=".35"/></g>'],
  ['rect', 'U', 'Rectangle: drag an area', '<rect x="4" y="6" width="16" height="12" stroke-dasharray="3 2.2"/><rect x="2.6" y="4.6" width="2.8" height="2.8" fill="currentColor"/><rect x="18.6" y="4.6" width="2.8" height="2.8" fill="currentColor"/><rect x="2.6" y="16.6" width="2.8" height="2.8" fill="currentColor"/><rect x="18.6" y="16.6" width="2.8" height="2.8" fill="currentColor"/>'],
  ['fill', 'F', 'Fill: a room (up to its walls, indoors or outdoors like the tile you click) or, with a floor, a patch of the same floor', '<rect x="7.6" y="7.6" width="4" height="4" fill="currentColor" fill-opacity=".35"/><rect x="12.4" y="7.6" width="4" height="4" fill="currentColor" fill-opacity=".35"/><rect x="7.6" y="12.4" width="4" height="4" fill="currentColor" fill-opacity=".35"/><rect x="12.4" y="12.4" width="4" height="4" fill="currentColor" fill-opacity=".35"/><path d="M12 5.6V1.2M10.2 3 12 1.2 13.8 3M12 18.4v4.4M10.2 21 12 22.8 13.8 21M5.6 12H1.2M3 10.2 1.2 12 3 13.8M18.4 12h4.4M21 10.2 22.8 12 21 13.8"/>'],
  ['erase', 'E', 'Erase: remove walls, objects and items (floor stays)', '<g transform="rotate(-38 12 12)"><rect x="3" y="8" width="18" height="8" rx="1.6"/><path d="M10 8v8"/><path d="M4.6 8h5.4v8H4.6A1.6 1.6 0 0 1 3 14.4V9.6A1.6 1.6 0 0 1 4.6 8z" fill="currentColor" fill-opacity=".35"/></g><path d="M13 21.5h8" opacity=".55"/>'],
  ['pick', 'I', 'Pick: take what is on a tile as the brush', '<g transform="rotate(45 12 12)"><rect x="9.6" y="0.6" width="4.8" height="5.4" rx="2.4" fill="currentColor" fill-opacity=".35"/><rect x="8.4" y="6" width="7.2" height="2" rx=".6"/><path d="M10.6 8h2.8v9.4L12 20.4l-1.4-3z"/><path d="M10.6 13h2.8" opacity=".55"/></g><path d="M4.2 18.2c-.8 1.1-1.3 1.9-1.3 2.5a1.3 1.3 0 0 0 2.6 0c0-.6-.5-1.4-1.3-2.5z" fill="currentColor" stroke="none"/>'],
  ['pan', 'H', 'Move the view', '<g transform="translate(12 12.4) scale(.56) translate(-12 -12)" stroke-width="2.7"><path d="M8 13V6a1.5 1.5 0 0 1 3 0v6M11 11V4a1.5 1.5 0 0 1 3 0v7M14 11V5.5a1.5 1.5 0 0 1 3 0V13M17 9.5a1.5 1.5 0 0 1 3 0V15a6 6 0 0 1-6 6h-1a7 7 0 0 1-5.5-2.7L4.3 14a1.6 1.6 0 0 1 2.4-2l1.3 1.3"/></g><path d="M12 4.2V.9M10.5 2.4 12 .9l1.5 1.5M12 20.2v3M10.5 21.7 12 23.2l1.5-1.5M4.2 12H.9M2.4 10.5.9 12l1.5 1.5M19.8 12h3.3M21.6 10.5 23.1 12l-1.5 1.5"/>'],
];

// ---------------------------------------------------------------- helpers
const RO = () => info.running && !info.live;     // view only: the server runs and live editing is not available
async function api(path, body) {
  const r = await fetch(path, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  return r.json();
}
let toastT = 0;
function toast(msg, bad) {
  const t = $('#toast'); t.textContent = msg; t.style.display = 'block';
  t.style.borderLeftColor = bad ? 'var(--bad)' : 'var(--gold)';
  clearTimeout(toastT); toastT = setTimeout(() => t.style.display = 'none', bad ? 6000 : 3500);
}
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const wx = (x, y) => 16 * (x + y), wy = (x, y) => 8 * (x - y);
function screenToTile(sx, sy) {
  const px = (sx - W / 2) / zoom + cam.x, py = (sy - H / 2) / zoom + cam.y;
  const u = (px - 32) / 16, v = (py - 56) / 8;
  return { x: Math.round((u + v) / 2), y: Math.round((u - v) / 2) };
}
function tileToScreen(x, y) { return { sx: (wx(x, y) + 32 - cam.x) * zoom + W / 2, sy: (wy(x, y) + 56 - cam.y) * zoom + H / 2 }; }
function centerOn(x, y) { cam.x = wx(x, y) + 32; cam.y = wy(x, y) + 56; redraw(); }
function redraw() { needDraw = true; baseDirty = true; }
function redrawTop() { needDraw = true; }

// ---------------------------------------------------------------- sprites
const waiting = new Map();
function sprite(n) {
  if (!n) return null;
  let s = sprites.get(n);
  if (s) return s.img;
  s = { img: null }; sprites.set(n, s);
  const im = new Image();
  im.onload = () => {
    const c = document.createElement('canvas'); c.width = im.width; c.height = im.height;
    const g = c.getContext('2d'); g.drawImage(im, 0, 0);
    try {
      const d = g.getImageData(0, 0, c.width, c.height), a = d.data;
      for (let i = 0; i < a.length; i += 4) if (a[i] > 240 && a[i + 1] < 16 && a[i + 2] > 240) a[i + 3] = 0;
      g.putImageData(d, 0, 0);
    } catch (e) {}
    s.img = c; redraw();
    const l = waiting.get(n); if (l) { waiting.delete(n); l.forEach(paintThumb); }
  };
  im.src = '/sprite/' + n;
  return null;
}
function thumb(n, w, h) {
  const c = document.createElement('canvas'); c.width = w; c.height = h || w; c.dataset.spr = n;
  paintThumb(c); return c;
}
function paintThumb(c) {
  const n = +c.dataset.spr, im = sprite(n), g = c.getContext('2d');
  g.clearRect(0, 0, c.width, c.height);
  if (!n) return;
  if (!im) { if (!waiting.has(n)) waiting.set(n, []); waiting.get(n).push(c); return; }
  const s = Math.min(c.width / im.width, c.height / im.height, 2);
  g.imageSmoothingEnabled = s < 1;
  g.drawImage(im, (c.width - im.width * s) / 2, (c.height - im.height * s) / 2 + (im.height > im.width ? 0 : c.height * .08), im.width * s, im.height * s);
}

// ---------------------------------------------------------------- map data
function chunk(cx, cy) {
  const k = cx + ',' + cy;
  let c = chunks.get(k);
  if (c) return c.data;
  c = { data: null }; chunks.set(k, c);
  api(`/api/region?x0=${cx * CH}&y0=${cy * CH}&x1=${cx * CH + CH - 1}&y1=${cy * CH + CH - 1}`).then(d => { c.data = d; redraw(); });
  return null;
}
function refetch(tiles) {
  const seen = new Set();
  for (const [x, y] of tiles) {
    const cx = Math.floor(x / CH), cy = Math.floor(y / CH), k = cx + ',' + cy;
    if (seen.has(k)) continue; seen.add(k);
    const old = chunks.get(k), c = { data: old ? old.data : null }; chunks.set(k, c);
    api(`/api/region?x0=${cx * CH}&y0=${cy * CH}&x1=${cx * CH + CH - 1}&y1=${cy * CH + CH - 1}`).then(d => { c.data = d; redraw(); });
  }
}
function T(x, y) {
  if (x < 0 || y < 0 || x >= MAPX || y >= MAPX) return null;
  const d = chunk(Math.floor(x / CH), Math.floor(y / CH));
  return d ? { d, i: (y - d.y0) * d.w + (x - d.x0) } : null;
}

// ---------------------------------------------------------------- drawing
function visible() {
  const pts = [[0, 0], [W, 0], [0, H], [W, H]].map(([sx, sy]) => {
    const px = (sx - W / 2) / zoom + cam.x, py = (sy - H / 2) / zoom + cam.y;
    const u = (px - 32) / 16, v = (py - 56) / 8;
    return [(u + v) / 2, (u - v) / 2];
  });
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  return { x0: Math.max(0, Math.floor(Math.min(...xs)) - 2), x1: Math.min(MAPX - 1, Math.ceil(Math.max(...xs)) + 8),
           y0: Math.max(0, Math.floor(Math.min(...ys)) - 8), y1: Math.min(MAPX - 1, Math.ceil(Math.max(...ys)) + 2) };
}
let g2 = bctx;
function put(n, x, y, a) {
  const im = sprite(n);
  if (!im) return;
  if (a !== undefined) g2.globalAlpha = a;
  g2.drawImage(im, wx(x, y) - im.width / 2 + 32, wy(x, y) - im.height + 64);
  if (a !== undefined) g2.globalAlpha = 1;
}
function diamond(x, y, c) {
  c = c || g2;
  const cx = wx(x, y) + 32, cy = wy(x, y) + 56;
  c.beginPath(); c.moveTo(cx - 16, cy); c.lineTo(cx, cy - 8); c.lineTo(cx + 16, cy); c.lineTo(cx, cy + 8); c.closePath();
}
function draw() {
  needDraw = false;
  const v = visible();
  if (baseDirty) {
    baseDirty = false;
    if (base.width !== W || base.height !== H) { base.width = W; base.height = H; }
    g2 = bctx;
    g2.setTransform(1, 0, 0, 1, 0, 0);
    g2.fillStyle = '#050506'; g2.fillRect(0, 0, W, H);
    g2.setTransform(zoom, 0, 0, zoom, W / 2 - cam.x * zoom, H / 2 - cam.y * zoom);
    g2.imageSmoothingEnabled = zoom < 1;
    if (show.floors) for (let y = v.y1; y >= v.y0; y--) for (let x = v.x0; x <= v.x1; x++) {
      const t = T(x, y);
      if (!t) continue;
      const g = t.d.g[t.i];
      if (g && g !== 1008) put(g, x, y);
    }
    const fl = [...flagOn];
    if (fl.length || show.grid || show.light) {
      g2.lineWidth = 1 / zoom;
      for (let y = v.y1; y >= v.y0; y--) for (let x = v.x0; x <= v.x1; x++) {
        const t = T(x, y);
        if (!t) continue;
        const f = t.d.fl[t.i];
        if (show.light && t.d.g[t.i] !== 1008) {
          const lit = (f >>> 12) & 1, l = lit ? 64 : t.d.li[t.i];
          const a = Math.max(0, Math.min(.86, 1 - l / 48));
          if (a > .02) { diamond(x, y); g2.fillStyle = `rgba(0,0,8,${a})`; g2.fill(); }
        }
        for (const b of fl) if ((f >>> b) & 1) { diamond(x, y); g2.fillStyle = FCOL[b] + '70'; g2.fill(); }
        if (show.grid && zoom >= .45) { diamond(x, y); g2.strokeStyle = 'rgba(255,255,255,.13)'; g2.stroke(); }
      }
    }
    const chars = show.chars && zoom >= .3;
    for (let y = v.y1; y >= v.y0; y--) for (let x = v.x0; x <= v.x1; x++) {
      const t = T(x, y);
      if (!t) continue;
      const d = t.d, i = t.i;
      if (show.walls && d.f[i]) put(d.f[i], x, y, show.see ? .28 : undefined);
      if (show.items && d.it[i]) put(d.it[i], x, y);
      if (chars && d.ch[i]) put(d.ch[i], x, y);
      else if (chars && d.pc && d.pc[i]) {     // waiting to (re)spawn: faded, on a dashed ring
        diamond(x, y); g2.setLineDash([3 / zoom, 3 / zoom]); g2.lineWidth = 1.5 / zoom; g2.strokeStyle = 'rgba(255,211,106,.85)'; g2.stroke(); g2.setLineDash([]);
        put(d.pc[i], x, y, .6);
      }
    }
    drawMini(v);
  }
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.drawImage(base, 0, 0);
  ctx.setTransform(zoom, 0, 0, zoom, W / 2 - cam.x * zoom, H / 2 - cam.y * zoom);
  if (rect) {
    ctx.fillStyle = 'rgba(214,164,67,.33)';
    for (let y = Math.min(rect.a.y, rect.b.y); y <= Math.max(rect.a.y, rect.b.y); y++)
      for (let x = Math.min(rect.a.x, rect.b.x); x <= Math.max(rect.a.x, rect.b.x); x++) { diamond(x, y, ctx); ctx.fill(); }
  }
  if (hover && tool !== 'pan') {
    ctx.lineWidth = 1.6 / zoom; ctx.strokeStyle = '#ffd36a';
    for (const [x, y] of footprint(hover.x, hover.y)) { diamond(x, y, ctx); ctx.stroke(); }
  }
  if (selTile) { diamond(selTile.x, selTile.y, ctx); ctx.lineWidth = 2.2 / zoom; ctx.strokeStyle = '#6fb0ff'; ctx.stroke(); }
  if (selPatrol && selTile) {    // its patrol route: stop to stop, and back to the first
    const P = selPatrol.slice(1), c = (p) => [wx(p[0], p[1]) + 32, wy(p[0], p[1]) + 56];
    ctx.lineWidth = 2 / zoom; ctx.strokeStyle = 'rgba(111,176,255,.9)'; ctx.setLineDash([6 / zoom, 4 / zoom]);
    ctx.beginPath(); P.forEach((p, i) => { const [a, b] = c(p); i ? ctx.lineTo(a, b) : ctx.moveTo(a, b); }); if (P.length > 1) ctx.closePath(); ctx.stroke(); ctx.setLineDash([]);
    ctx.font = `bold ${12 / zoom}px system-ui`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    P.forEach((p, i) => { const [a, b] = c(p); ctx.fillStyle = '#1b3a66'; ctx.beginPath(); ctx.arc(a, b, 8 / zoom, 0, 7); ctx.fill(); ctx.fillStyle = '#cfe4ff'; ctx.fillText(i + 1, a, b); });
  }
  // area names, in screen space
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  if (show.npcnames && show.chars && zoom >= .3) {     // names over the characters
    ctx.font = `600 ${zoom >= .7 ? 12 : 10}px system-ui, Segoe UI, sans-serif`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    for (let y = v.y1; y >= v.y0; y--) for (let x = v.x0; x <= v.x1; x++) {
      const t = T(x, y);
      if (!t || !t.d.nm) continue;
      const n = t.d.nm[t.i];
      if (!n) continue;
      const p = tileToScreen(x, y), ty = p.sy - 68 * zoom;
      if (p.sx < -60 || p.sx > W + 60 || ty < -20 || ty > H + 20) continue;
      const w = ctx.measureText(n[0]).width + 8;
      ctx.fillStyle = 'rgba(10,10,12,.62)'; ctx.fillRect(p.sx - w / 2, ty - 8, w, 16);
      ctx.fillStyle = n[1] === 1 ? '#8fc4ff' : n[1] === 2 ? 'rgba(255,211,106,.6)' : '#f3e6c4';
      ctx.fillText(n[0], p.sx, ty + 1);
    }
  }
  if (show.names && zoom >= .35) {
    ctx.font = '600 12px system-ui, Segoe UI, sans-serif'; ctx.textBaseline = 'middle';
    const used = [];
    for (const a of info.areas) {
      if (a[2] < v.x0 || a[0] > v.x1 || a[3] < v.y0 || a[1] > v.y1) continue;
      if ((a[2] - a[0]) * (a[3] - a[1]) < 12) continue;
      const p = tileToScreen((a[0] + a[2]) / 2, (a[1] + a[3]) / 2);
      if (p.sx < 0 || p.sy < 0 || p.sx > W || p.sy > H) continue;
      if (used.some(u => Math.abs(u[0] - p.sx) < 110 && Math.abs(u[1] - p.sy) < 22)) continue;
      used.push([p.sx, p.sy]);
      const w = ctx.measureText(a[4]).width + 14;
      ctx.fillStyle = 'rgba(20,18,12,.78)'; ctx.strokeStyle = 'rgba(214,164,67,.5)'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.roundRect(p.sx - w / 2, p.sy - 10, w, 20, 4); ctx.fill(); ctx.stroke();
      ctx.fillStyle = '#f3d79b'; ctx.textAlign = 'center'; ctx.fillText(a[4], p.sx, p.sy + 1);
    }
  }
}
function loop() {
  try {
    if (!W || !H) { const r = $('#view').getBoundingClientRect(); if (r.width && r.height) resize(); }   // the map area got its size
    else if (needDraw) draw();
  } catch (e) { console.error(e); }      // never let one bad frame stop the drawing for good
  requestAnimationFrame(loop);
}

// ---------------------------------------------------------------- minimap and world map
const mini = new Image(); let miniOk = false;
function drawMap(c, v) {
  const g = c.getContext('2d');
  g.drawImage(mini, 0, 0, 1024, 1024);
  if (!v) return;
  g.strokeStyle = '#ffd36a'; g.lineWidth = c === $('#mcv') ? 10 : 4;
  g.strokeRect(v.y0, v.x0, Math.max(10, v.y1 - v.y0), Math.max(10, v.x1 - v.x0));   // minimap: column = map y, row = map x
}
function drawMini(v) { if (miniOk) drawMap($('#mcv'), v); }
function mapClick(e) {
  const r = e.target.getBoundingClientRect();
  const x = Math.floor((e.clientY - r.top) / r.height * 1024), y = Math.floor((e.clientX - r.left) / r.width * 1024);
  if (destPick) { setDestination({ x, y }); return; }    // a portal's destination, picked on the world map
  centerOn(x, y);
}
$('#mcv').onclick = mapClick;
$('#wcv').onclick = e => { mapClick(e); toggleWorld(false); };
function toggleWorld(on) {
  if (!miniOk) return toast('No world map picture found (docs/world_minimap.png).', true);
  const w = $('#world'); on = on === undefined ? w.style.display !== 'grid' : on;
  w.style.display = on ? 'grid' : 'none';
  if (on) drawMap($('#wcv'), visible());
}

// ---------------------------------------------------------------- left panel
let npcSub = 'world', newNpc = null;    // NPCs tab: In the world / Blueprints; the + New NPC form
const TABS = { builder: 'Builder', floors: 'Floors', walls: 'Walls', objects: 'Objects', items: 'Items', npcs: 'NPCs', flags: 'Flags' };
const TAB_ICONS = {      // the editor's own icons, same set as the toolbar
  builder: '<path d="M14 4l6 6-3 3-6-6z"/><path d="M11 7 3.5 14.5a2 2 0 0 0 0 2.8l3.2 3.2a2 2 0 0 0 2.8 0L17 13"/>',
  floors: '<path d="M12 4 21 9.5 12 15 3 9.5z" fill="currentColor" fill-opacity=".25"/><path d="M12 4 21 9.5 12 15 3 9.5z"/><path d="M3 13.5 12 19l9-5.5" opacity=".6"/>',
  walls: '<path d="M3 5h18v14H3z"/><path d="M3 9.7h18M3 14.3h18M9 5v4.7M15 5v4.7M6 9.7v4.6M12 9.7v4.6M18 9.7v4.6M9 14.3V19M15 14.3V19"/>',
  objects: '<path d="M6 5h12l1 3v11H5V8z"/><path d="M5 8h14M5 13h14M10 13v3h4v-3"/>',
  items: '<path d="M19 3l-9.5 9.5M19 3v4l-8 8M19 3h-4l-8 8"/><path d="M6.5 13.5l4 4M4 20l3.5-3.5"/>',
  npcs: '<path d="M12 3c-4 0-6.5 3.5-6.5 8.5V21h13v-9.5C18.5 6.5 16 3 12 3z"/><path d="M8.5 13c.5-3 1.8-4.5 3.5-4.5s3 1.5 3.5 4.5c-1 1.5-2.2 2-3.5 2s-2.5-.5-3.5-2z"/>',
  flags: '<path d="M5 21V3"/><path d="M5 4h13l-3 4 3 4H5"/>',
  title: '<path d="M12 3 21 12 12 21 3 12z"/>',
};
// facing, named the way the minimap shows it (north = smaller x, west = smaller y); the game's DX_ numbers
const FACE = [[2, 'N', 'north (−x)'], [4, 'E', 'east (+y)'], [1, 'S', 'south (+x)'], [3, 'W', 'west (−y)']];
const FACEN = { 1: 'south', 2: 'north', 3: 'west', 4: 'east' };
function faceRow(cur, onpick, disabled) {
  const d = document.createElement('div'); d.className = 'face';
  d.innerHTML = '<span style="color:var(--dim2);font-size:12px;margin-right:2px">Facing</span>' + FACE.map(([v, k, t]) => `<button data-d="${v}" title="${t}" class="${v === cur ? 'on' : ''}" ${disabled ? 'disabled' : ''}>${k}</button>`).join('');
  d.querySelectorAll('button').forEach(b => b.onclick = () => { d.querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); onpick(+b.dataset.d); });
  return d;
}
function cats() {
  // [number, name, sprite, take, driver, blocks, item]
  const t = pal.templates;
  return {
    walls: t.filter(x => !x[3] && !x[6] && (x[5] & 2)),          // drawn into the tile and block sight: walls, trees, pillars
    objects: t.filter(x => !x[3] && !(!x[6] && (x[5] & 2))),
    items: t.filter(x => x[3]),
  };
}
function brushKey(b) { return b.kind + ':' + (b.kind === 'place' || b.kind === 'npc' ? b.t[0] : b.kind === 'flag' ? b.bit : b.kind === 'mix' ? b.items.map(i => i.s + 'x' + i.w).join(',') : b.s); }
// ---- floor mixes: several floors painted at random, each with a weight
let mixes = [];
try { mixes = JSON.parse(localStorage.getItem('myv2.mixes') || '[]'); } catch (e) {}
function saveMixes() { try { localStorage.setItem('myv2.mixes', JSON.stringify(mixes)); } catch (e) {} }
function mixPick(items) {
  let tot = 0; for (const i of items) tot += i.w;
  let r = Math.random() * tot;
  for (const i of items) { r -= i.w; if (r < 0) return i.s; }
  return items[items.length - 1].s;
}
function toggleMix(s) {   // Ctrl/Shift+click on a floor
  let items = brush.kind === 'mix' ? brush.items.map(i => ({ ...i })) : brush.kind === 'floor' ? [{ s: brush.s, w: 5 }] : [];
  const k = items.findIndex(i => i.s === s);
  if (k >= 0) items.splice(k, 1); else items.push({ s, w: 5 });
  if (!items.length) return;
  if (items.length === 1) setBrush({ kind: 'floor', s: items[0].s, set: false });
  else setBrush({ kind: 'mix', items, name: '' });
}
const avgCache = new Map();
function avgColor(n) {   // the average color of a floor sprite (to find look-alikes)
  if (avgCache.has(n)) return Promise.resolve(avgCache.get(n));
  return new Promise(res => {
    const done = () => {
      const im = sprites.get(n) && sprites.get(n).img;
      if (!im) return false;
      const d = im.getContext('2d').getImageData(0, 0, im.width, im.height).data;
      let r = 0, g = 0, b = 0, c = 0;
      for (let i = 0; i < d.length; i += 4) if (d[i + 3] > 200) { r += d[i]; g += d[i + 1]; b += d[i + 2]; c++; }
      const v = c ? [r / c, g / c, b / c] : null; avgCache.set(n, v); res(v); return true;
    };
    sprite(n);
    if (done()) return;
    let tries = 0; const t = setInterval(() => { if (done() || ++tries > 60) { clearInterval(t); if (!avgCache.has(n)) res(null); } }, 100);
  });
}
async function addSimilar() {
  const items = brush.kind === 'mix' ? brush.items : brush.kind === 'floor' ? [{ s: brush.s, w: 5 }] : null;
  if (!items) return;
  toast('Looking for floors that look alike…');
  const want = await Promise.all(items.map(i => avgColor(i.s)));
  const ref = want.filter(Boolean); if (!ref.length) return;
  const m = ref.reduce((a, v) => [a[0] + v[0] / ref.length, a[1] + v[1] / ref.length, a[2] + v[2] / ref.length], [0, 0, 0]);
  const cand = pal.floors.map(f => f[0]).filter(s => s !== 1008 && !items.some(i => i.s === s)).slice(0, 400);
  const cols = await Promise.all(cand.map(avgColor));
  const scored = cand.map((s, i) => [s, cols[i] ? Math.hypot(cols[i][0] - m[0], cols[i][1] - m[1], cols[i][2] - m[2]) : 1e9]).sort((a, b) => a[1] - b[1]);
  const add = scored.filter(x => x[1] < 28).slice(0, 4);
  if (!add.length) return toast('No floors that look close enough.', true);
  setBrush({ kind: 'mix', items: [...items.map(i => ({ ...i })), ...add.map(([s]) => ({ s, w: 2 }))], name: brush.name || '' }, true);
  toast('Added ' + add.map(a => a[0]).join(', ') + ' (lower weight: lower the sliders or remove any you don\'t like)');
}
function setBrush(b, keepTool) {
  brush = b;
  const k = brushKey(b);
  recent = [b, ...recent.filter(r => brushKey(r) !== k)].slice(0, 24);
  if (!keepTool && (tool === 'select' || tool === 'pick' || tool === 'pan' || tool === 'erase')) setTool('brush');
  card(); document.querySelectorAll('#palwrap [data-k]').forEach(el => el.classList.toggle('sel', el.dataset.k === k));
}
function card() {
  const c = $('#card'); c.innerHTML = ''; c.classList.toggle('mix', brush.kind === 'mix');
  if (brush.kind === 'mix') return mixCard(c);
  let spr = 0, t = '', s = '';
  if (brush.kind === 'floor') { spr = brush.s; t = 'Floor ' + brush.s; s = brush.set && pal && pal.sets[brush.s] ? 'Floor sprite ' + brush.s + ' (random variants ' + pal.sets[brush.s].join(', ') + ')' : 'Floor sprite ' + brush.s; }
  else if (brush.kind === 'place') { spr = brush.t[2]; t = brush.t[1]; s = `Template ${brush.t[0]} · ${brush.t[6] ? 'item' : 'drawn into the tile'}${brush.t[5] & 1 ? ' · blocks walking' : ''}`; }
  else if (brush.kind === 'object') { spr = brush.s; t = 'Object ' + brush.s; s = 'Picked from the map' + (brush.block & 1 ? ' · blocks walking' : '') + (brush.block & 2 ? ' · blocks sight' : ''); }
  else if (brush.kind === 'flag') { t = 'Flag: ' + FLAGS[brush.bit]; s = 'Paint sets it · Alt+paint clears it'; }
  else if (brush.kind === 'npc') { spr = brush.t[2]; t = brush.t[1]; s = `NPC template ${brush.t[0]} · ${brush.t[3]} · click a free tile to place one (it respawns there) · Alt+click removes an NPC`; }
  if (brush.kind === 'flag') { const d = document.createElement('div'); d.style.cssText = `width:40px;height:40px;border-radius:8px;background:${FCOL[brush.bit]};flex:none`; c.appendChild(d); }
  else c.appendChild(thumb(spr, 40));
  const d = document.createElement('div'); d.innerHTML = `<div class="t"></div><div class="s"></div>`;
  d.firstChild.textContent = t; d.lastChild.textContent = s; c.appendChild(d);
  if (brush.kind === 'npc') { const f = faceRow(brush.dir || 4, v => { brush.dir = v; }); f.style.marginTop = '6px'; d.appendChild(f); }
  if (brush.kind === 'npc' || brush.kind === 'place') {
    const m = document.createElement('div'); m.className = 'mixbtns'; m.style.marginTop = '6px';
    m.innerHTML = `<button title="Change this template: ${brush.kind === 'npc' ? 'name, look, stats, equipment, talk, patrol…' : 'name, look, stats, flags…'}">Edit template…</button>`;
    m.firstChild.onclick = () => openTemplate(brush.kind === 'npc' ? 'npc' : 'item', brush.t[0]); d.appendChild(m);
  }
  if (brush.kind === 'floor') {   // start a mix from this floor
    const m = document.createElement('div'); m.className = 'mixbtns'; m.style.marginTop = '6px';
    m.innerHTML = '<button data-a="sim" title="Make a mix: add floors whose color is close to this one">+ look-alikes</button>';
    m.firstChild.onclick = addSimilar; d.appendChild(m);
  }
}
function mixCard(c) {
  const tot = brush.items.reduce((a, i) => a + i.w, 0);
  c.innerHTML = `<div class="mixhd"><span class="t"></span><span class="s">${brush.items.length} floors</span></div>`;
  c.querySelector('.t').textContent = brush.name ? 'Mix: ' + brush.name : 'Floor mix';
  for (const it of brush.items) {
    const r = document.createElement('div'); r.className = 'mixrow';
    r.appendChild(thumb(it.s, 30));
    r.insertAdjacentHTML('beforeend', `<span class="num">${it.s}</span><input type="range" min="1" max="10" value="${it.w}" title="How often this one is painted"><span class="pct">${Math.round(it.w / tot * 100)}%</span><button class="x" title="Take it out of the mix">×</button>`);
    r.querySelector('input').oninput = e => { it.w = +e.target.value; const t2 = brush.items.reduce((a, i) => a + i.w, 0); c.querySelectorAll('.mixrow').forEach((row, k) => row.querySelector('.pct').textContent = Math.round(brush.items[k].w / t2 * 100) + '%'); };
    r.querySelector('.x').onclick = () => { const items = brush.items.filter(i => i !== it); items.length === 1 ? setBrush({ kind: 'floor', s: items[0].s, set: false }, true) : setBrush({ kind: 'mix', items, name: brush.name }, true); };
    c.appendChild(r);
  }
  const b = document.createElement('div'); b.className = 'mixbtns';
  b.innerHTML = '<button data-a="sim" title="Add floors whose color is close to these">+ look-alikes</button><button data-a="save" title="Keep this mix in the list (in this browser)">Save mix</button>';
  b.querySelector('[data-a=sim]').onclick = addSimilar;
  b.querySelector('[data-a=save]').onclick = () => {
    const name = prompt('Name for this mix (e.g. Aston grass):', brush.name || '');
    if (!name) return;
    mixes = mixes.filter(m => m.name !== name); mixes.unshift({ name, items: brush.items.map(i => ({ ...i })) }); saveMixes();
    brush.name = name; card(); leftUI(); toast('Saved the mix "' + name + '"');
  };
  c.appendChild(b);
  c.insertAdjacentHTML('beforeend', '<div class="s">Ctrl+click floors on the left to add or remove them.</div>');
}
function lazy(container, items, make) {
  container.innerHTML = '';
  let shown = 0;
  const more = () => {
    const end = Math.min(items.length, shown + 96);
    for (; shown < end; shown++) container.appendChild(make(items[shown]));
    if (shown < items.length) {
      const s = document.createElement('div'); s.style.cssText = 'height:10px;grid-column:1/-1'; container.appendChild(s);
      const io = new IntersectionObserver(es => { if (es[0].isIntersecting) { io.disconnect(); s.remove(); more(); } }, { root: $('#palwrap') });
      io.observe(s);
    }
  };
  more();
  if (!items.length) container.innerHTML = '<div class="empty" style="grid-column:1/-1">Nothing matches.</div>';
}
function cellFloor(s, n) {
  const c = document.createElement('div'); c.className = 'cell'; c.dataset.k = 'floor:' + s;
  if (brushKey(brush) === c.dataset.k) c.classList.add('sel');
  c.title = `Floor ${s}` + (n ? ` · on ${n} tiles` : '') + (pal.sets[s] ? ' · paints random variants' : '');
  c.appendChild(thumb(s, 64, 48)); const l = document.createElement('div'); l.className = 'lab'; l.textContent = s; c.appendChild(l);
  if (brush.kind === 'mix' && brush.items.some(i => i.s === s)) { c.classList.add('inmix'); c.insertAdjacentHTML('beforeend', '<span class="badge">mix</span>'); }
  c.title += ' · Ctrl+click: add to a mix';
  c.onclick = e => (e.ctrlKey || e.metaKey || e.shiftKey) ? toggleMix(s) : setBrush({ kind: 'floor', s, set: true });
  return c;
}
function cellMix(m, saved) {
  const c = document.createElement('div'); c.className = 'cell'; c.dataset.k = brushKey({ kind: 'mix', items: m.items });
  if (brushKey(brush) === c.dataset.k) c.classList.add('sel');
  c.title = (m.name || 'Mix') + ': ' + m.items.map(i => i.s).join(', ') + (saved ? ' · right-click to delete' : '');
  const cv = document.createElement('canvas'); cv.width = 64; cv.height = 48;
  const g = cv.getContext('2d'), n = Math.min(4, m.items.length);
  m.items.slice(0, 4).forEach((it, k) => { const t = thumb(it.s, 32, 24); setTimeout(() => g.drawImage(t, (k % 2) * 32, Math.floor(k / 2) * 24 + (n <= 2 ? 12 : 0)), 300); });
  c.appendChild(cv);
  const l = document.createElement('div'); l.className = 'lab'; l.textContent = m.name || 'mix'; c.appendChild(l);
  c.onclick = () => setBrush({ kind: 'mix', items: m.items.map(i => ({ ...i })), name: m.name });
  if (saved) c.oncontextmenu = e => { e.preventDefault(); if (confirm('Delete the mix "' + m.name + '"?')) { mixes = mixes.filter(x => x !== m); saveMixes(); leftUI(); } };
  return c;
}
function cellFlag(b) {
  const c = document.createElement('div'); c.className = 'cell'; c.dataset.k = 'flag:' + b;
  if (brushKey(brush) === c.dataset.k) c.classList.add('sel');
  c.title = 'Paint the ' + FLAGS[b] + ' flag (Alt+paint clears it)';
  c.innerHTML = `<div class="sw" style="background:${FCOL[b]}"></div><div class="lab"></div>`;
  c.lastChild.textContent = FLAGS[b];
  c.onclick = () => { setBrush({ kind: 'flag', bit: b }); if (!flagOn.has(b)) { flagOn.add(b); layersUI(); redraw(); } };
  return c;
}
function cellTemp(t) {
  const c = document.createElement('div'); c.className = 'cell'; c.dataset.k = 'place:' + t[0];
  if (brushKey(brush) === c.dataset.k) c.classList.add('sel');
  c.title = `${t[1]} · template ${t[0]} · ${t[6] ? 'item' : 'drawn into the tile'}${t[5] & 1 ? ' · blocks walking' : ''}${t[5] & 2 ? ' · blocks sight' : ''}`;
  c.appendChild(thumb(t[2], 64, 64)); const l = document.createElement('div'); l.className = 'lab'; l.textContent = t[1]; c.appendChild(l);
  c.onclick = () => setBrush({ kind: 'place', t });
  c.oncontextmenu = e => { e.preventDefault(); openTemplate('item', t[0]); };
  c.title += ' · right-click to edit the template';
  return c;
}
function cellNpc(t) {
  const c = document.createElement('div'); c.className = 'cell'; c.dataset.k = 'npc:' + t[0];
  if (brushKey(brush) === c.dataset.k) c.classList.add('sel');
  c.title = `${t[1]} · template ${t[0]} · ${t[3]}${t[7] ? ' · placed with the editor' : ''} · ${t[4]} in the world` + (t[5] || t[6] ? ` · spawns at ${t[5]}, ${t[6]}` : '');
  c.appendChild(thumb(t[2], 64, 64)); const l = document.createElement('div'); l.className = 'lab'; l.textContent = t[1]; c.appendChild(l);
  c.onclick = () => setBrush({ kind: 'npc', t, dir: brush.kind === 'npc' ? brush.dir : 4 });
  c.oncontextmenu = e => { e.preventDefault(); openTemplate('npc', t[0]); };
  c.title += ' · right-click to edit';
  return c;
}
function cellRecent(b) {
  if (b.kind === 'npc') return cellNpc(b.t);
  if (b.kind === 'mix') return cellMix(b, false);
  if (b.kind === 'floor') return cellFloor(b.s, 0);
  if (b.kind === 'flag') return cellFlag(b.bit);
  if (b.kind === 'place') return cellTemp(b.t);
  const c = document.createElement('div'); c.className = 'cell'; c.dataset.k = brushKey(b);
  c.appendChild(thumb(b.s, 64, 64)); const l = document.createElement('div'); l.className = 'lab'; l.textContent = 'obj ' + b.s; c.appendChild(l);
  c.onclick = () => setBrush(b); return c;
}
function leftUI() {
  const tabs = $('#tabs'), w = $('#palwrap'), q = $('#lsearch').value.trim().toLowerCase();
  if (mode === 'map') {
    tabs.innerHTML = Object.entries(TABS).map(([k, v]) => `<button data-tab="${k}" class="${k === tab ? 'on' : ''}"><svg viewBox="0 0 24 24">${TAB_ICONS[k]}</svg>${v}</button>`).join('');
    tabs.querySelectorAll('button').forEach(b => b.onclick = () => { tab = b.dataset.tab; $('#lsearch').value = ''; leftUI(); });
    $('#lsearch').style.display = ''; $('#card').style.display = '';
    $('#lsearch').placeholder = 'Search name or number';
  } else {
    tabs.innerHTML = `<button class="on title"><svg viewBox="0 0 24 24">${TAB_ICONS.title}</svg>${{ npcs: 'NPCs and players', players: 'Player characters', history: 'History', help: 'Help' }[mode]}</button>`;
    $('#lsearch').style.display = mode === 'npcs' || mode === 'players' ? '' : 'none'; $('#card').style.display = 'none';
    $('#lsearch').placeholder = 'Search a name';
  }
  w.innerHTML = '';
  if (!pal && mode === 'map') { w.innerHTML = '<div class="empty">Loading…</div>'; return; }
  const sect = t => { const s = document.createElement('div'); s.className = 'sect'; s.style.padding = '8px 2px 8px'; s.textContent = t; w.appendChild(s); };
  const grid = () => { const g = document.createElement('div'); g.className = 'grid'; w.appendChild(g); return g; };
  const match = (name, num) => !q || name.toLowerCase().includes(q) || String(num) === q || String(num).startsWith(q);
  function mixSection(withSets) {
    const saved = mixes.filter(m => match(m.name, ''));
    const sets = withSets ? Object.entries(pal.sets).map(([k, v]) => ({ name: 'set ' + k, items: v.map(s => ({ s, w: 5 })) })) : [];
    if (!saved.length && !sets.length) return;
    sect(saved.length ? 'Floor mixes' + (sets.length ? ' · and the game\'s own sets' : '') : 'The game\'s own floor sets');
    const g = grid();
    saved.forEach(m => g.appendChild(cellMix(m, true)));
    sets.forEach(m => g.appendChild(cellMix(m, false)));
  }
  if (mode === 'map') {
    const C = cats();
    if (tab === 'builder') {
      if (match('chest', '')) { sect('Chests'); grid().appendChild(cellChest()); }
      if (recent.length) { sect('Recently used'); lazy(grid(), recent.filter(b => match(b.kind === 'place' ? b.t[1] : b.kind === 'flag' ? FLAGS[b.bit] : b.kind === 'mix' ? (b.name || 'mix') : '', b.kind === 'place' ? b.t[0] : b.s ?? '')), cellRecent); }
      mixSection();
      sect('Floors and flags');
      const g = grid();
      const fl = FLAGS.map((f, i) => i).filter(i => match(FLAGS[i], ''));
      const fs = pal.floors.filter(([s]) => match('', s)).slice(0, 60);
      lazy(g, [...fl.map(b => ['f', b]), ...fs.map(f => ['g', f])], ([k, v]) => k === 'f' ? cellFlag(v) : cellFloor(v[0], v[1]));
      sect('Walls'); lazy(grid(), C.walls.filter(t => match(t[1], t[0])).slice(0, 24), cellTemp);
      sect('Objects'); lazy(grid(), C.objects.filter(t => match(t[1], t[0])).slice(0, 24), cellTemp);
    } else if (tab === 'floors') {
      const list = pal.floors.filter(([s]) => match('', s));
      if (/^\d+$/.test(q) && !list.some(([s]) => String(s) === q)) list.unshift([+q, 0]);
      if (!q) mixSection(true);
      sect('Floors · by how often they are used · Ctrl+click to mix'); lazy(grid(), list, f => cellFloor(f[0], f[1]));
    } else if (tab === 'npcs') {
      const all = pal.npcs || [], blue = all.filter(t => !t[8]), made = blue.filter(t => t[7]);
      const seg = document.createElement('div'); seg.className = 'seg';
      seg.innerHTML = `<button data-s="world" class="${npcSub === 'world' ? 'on' : ''}">In the world</button><button data-s="blue" class="${npcSub === 'blue' ? 'on' : ''}">Blueprints · ${blue.length}</button>`;
      seg.querySelectorAll('button').forEach(b => b.onclick = () => { npcSub = b.dataset.s; leftUI(); });
      w.appendChild(seg);
      if (npcSub === 'world') {
        const box = document.createElement('div'); box.className = 'list'; w.appendChild(box);
        box.innerHTML = '<div class="empty">Loading…</div>';
        api('/api/npcworld').then(list => {
          if (mode !== 'map' || tab !== 'npcs' || npcSub !== 'world') return;
          list = list.filter(c => !q || c[1].toLowerCase().includes(q) || String(c[4]) === q || (c[8] || '').toLowerCase().includes(q));
          list.sort((a, b) => a[1].localeCompare(b[1]) || a[4] - b[4]);
          box.innerHTML = '';
          const s2 = document.createElement('div'); s2.className = 'sect'; s2.style.padding = '2px 2px 8px';
          s2.textContent = `${list.length} NPC${list.length === 1 ? '' : 's'} · click to go there · right-click to edit`; box.appendChild(s2);
          lazy(box, list, c => {
            const r = document.createElement('div'); r.className = 'row';
            const th = thumb(c[5], 34); if (c[6] === 'waiting') th.style.opacity = .45; r.appendChild(th);
            const d = document.createElement('div'); d.style.flex = '1'; d.style.minWidth = '0'; d.innerHTML = '<div></div><div class="n"></div>';
            d.firstChild.textContent = c[1];
            d.lastChild.textContent = `${c[6] === 'waiting' ? 'respawning · ' : ''}${c[8] ? c[8] + ' · ' : ''}${c[2]}, ${c[3]} · template ${c[4]}`;
            r.appendChild(d);
            const cp = document.createElement('button'); cp.className = 'sm'; cp.textContent = 'Copy'; cp.title = 'Place copies of it: pick this as the NPC brush';
            cp.onclick = e => { e.stopPropagation(); const t = all.find(x => x[0] === c[4]); if (t) setBrush({ kind: 'npc', t, dir: 4 }); else toast('That template is not in the list (a player start template?).', true); };
            r.appendChild(cp);
            r.onclick = () => { centerOn(c[2], c[3]); selectTile(c[2], c[3]); };
            r.oncontextmenu = e => { e.preventDefault(); openTemplate('npc', c[4]); };
            return r;
          });
        });
      } else {
        // + New NPC
        const nb = document.createElement('button'); nb.className = 'btn pri'; nb.style.cssText = 'width:100%;margin:2px 0 8px'; nb.textContent = '+ New NPC…';
        w.appendChild(nb);
        const form = document.createElement('div'); form.className = 'newnpc'; form.style.display = newNpc ? '' : 'none'; w.appendChild(form);
        nb.onclick = () => { newNpc = newNpc ? null : { name: '', kind: 'friendly', sprite: 0 }; leftUI(); };
        if (newNpc) {
          form.innerHTML = `<div class="lb">Name</div><input type="text" maxlength="39" class="nn" placeholder="e.g. Old Sage">
            <div class="lb">Kind</div><div class="seg k"><button data-k="friendly">Friendly</button><button data-k="merchant">Merchant</button><button data-k="enemy">Enemy</button></div>
            <div class="lb">Look · pick one</div><div class="looks"></div>
            <div class="hint">It starts as a plain ${newNpc.kind} (the game's ${newNpc.kind === 'merchant' ? 'Ruth' : newNpc.kind === 'enemy' ? 'Thief' : 'townsfolk'}) without its own lines, patrol or quest. Afterwards: set its rank, gear and lines, then place it with the NPC brush.</div>
            <button class="btn pri go" style="width:100%;margin-top:8px">Create</button>`;
          const nn = form.querySelector('.nn'); nn.value = newNpc.name; nn.oninput = () => newNpc.name = nn.value;
          form.querySelectorAll('.k button').forEach(b => { b.classList.toggle('on', b.dataset.k === newNpc.kind); b.onclick = () => { newNpc.kind = b.dataset.k; leftUI(); }; });
          const looks = form.querySelector('.looks'), seen = new Set();
          for (const t of all) {
            if (!t[9] || seen.has(t[9])) continue; seen.add(t[9]);
            const c = document.createElement('div'); c.className = 'look' + (newNpc.sprite === t[9] ? ' on' : ''); c.title = 'Looks like ' + t[1];
            c.appendChild(thumb(t[9] + 8, 40, 48)); c.onclick = () => { newNpc.sprite = t[9]; looks.querySelectorAll('.look').forEach(x => x.classList.toggle('on', x === c)); };
            looks.appendChild(c);
          }
          form.querySelector('.go').onclick = async () => {
            if (RO()) return toast('The game server is running and live editing is not available.', true);
            if (!newNpc.name.trim()) return toast('Give it a name first.', true);
            const r = await api('/api/edit', { ops: [{ op: 'ctempblank', kind: newNpc.kind, name: newNpc.name.trim(), sprite: newNpc.sprite || 0 }], label: 'new NPC ' + newNpc.name });
            if (r.error || !r.made) return toast(r.error || (r.msgs || []).join('\n') || 'Could not make it.', true);
            Object.assign(info, { dirty: r.dirty ?? info.dirty, undo: r.undo ?? info.undo }); status();
            pal.npcs = await api('/api/npcs'); newNpc = null; leftUI();
            const row = pal.npcs.find(x => x[0] === r.made[1]); if (row) setBrush({ kind: 'npc', t: row, dir: 4 });
            openTemplate('npc', r.made[1]);
            toast('Made. Set it up here, then click a free tile on the map to place it (the NPC brush is ready).');
          };
        }
        const mine = made.filter(t => match(t[1], t[0])), game = blue.filter(t => !t[7] && match(t[1], t[0]));
        if (mine.length) { sect('Your new NPCs · not placed yet'); lazy(grid(), mine, cellNpc); }
        if (game.length) { sect("The game's own · spawned by its code (pentagrams, labyrinth, summons…)"); lazy(grid(), game.sort((a, b) => a[1].localeCompare(b[1])), cellNpc); }
        if (!mine.length && !game.length) w.insertAdjacentHTML('beforeend', '<div class="empty">Nothing matches.</div>');
      }
    } else if (tab === 'flags') {
      sect('Paint a flag on tiles'); lazy(grid(), FLAGS.map((f, i) => i).filter(i => match(FLAGS[i], '')), cellFlag);
    } else {
      const list = C[tab].filter(t => match(t[1], t[0]));
      if (tab === 'objects' && match('chest', '')) { sect('Chests · put one in and choose what it gives'); grid().appendChild(cellChest()); }
      sect({ walls: 'Walls · drawn into the tile, they block', objects: 'Objects · furniture, decoration, doors, chests…', items: 'Items · things players can pick up' }[tab]);
      lazy(grid(), list, cellTemp);
    }
  } else if (mode === 'npcs') {
    w.innerHTML = '<div class="empty">Loading…</div>';
    api('/api/chars').then(list => {
      if (mode !== 'npcs') return;
      list = list.filter(c => !q || c[1].toLowerCase().includes(q) || String(c[4]) === q);
      list.sort((a, b) => b[5] - a[5] || a[1].localeCompare(b[1]));
      const box = document.createElement('div'); box.className = 'list'; w.innerHTML = ''; w.appendChild(box);
      const s = document.createElement('div'); s.className = 'sect'; s.style.padding = '2px 2px 8px'; s.textContent = `${list.length} in the world · click to go there`; box.appendChild(s);
      lazy(box, list, c => {
        const r = document.createElement('div'); r.className = 'row';
        r.appendChild(thumb(c[6], 34));
        const d = document.createElement('div'); d.innerHTML = '<div></div><div class="n"></div>';
        d.firstChild.textContent = c[1]; d.lastChild.textContent = `${c[5] ? (c[7] ? 'player · online' : 'player · offline') : 'template ' + c[4]} · ${c[2]}, ${c[3]}`;
        r.appendChild(d); r.onclick = () => { centerOn(c[2], c[3]); selectTile(c[2], c[3]); };
        return r;
      });
    });
  } else if (mode === 'players') {
    w.innerHTML = '<div class="empty">Loading…</div>';
    api('/api/players').then(list => {
      if (mode !== 'players') return;
      list = list.filter(p => !q || p.name.toLowerCase().includes(q) || String(p.c) === q);
      const box = document.createElement('div'); box.className = 'list'; w.innerHTML = ''; w.appendChild(box);
      const s = document.createElement('div'); s.className = 'sect'; s.style.padding = '2px 2px 8px';
      s.textContent = `${list.length} character${list.length === 1 ? '' : 's'} · ${list.filter(p => p.online).length} online · click to open`; box.appendChild(s);
      lazy(box, list, p => {
        const r = document.createElement('div'); r.className = 'row';
        r.appendChild(thumb(p.sprite, 34));
        const d = document.createElement('div'); d.innerHTML = '<div></div><div class="n"></div>';
        d.firstChild.innerHTML = (p.online ? '<span style="color:var(--ok)">● </span>' : '') + esc(p.name);
        d.lastChild.textContent = `${p.rank} · ${p.kin} · ${p.online ? 'online' : p.login ? 'last seen ' + new Date(p.login * 1000).toLocaleDateString() : 'never'}`;
        r.appendChild(d); r.onclick = () => openPlayer(p.c);
        return r;
      });
    });
  } else if (mode === 'history') {
    w.innerHTML = '<div class="empty">Loading…</div>';
    api('/api/history').then(h => {
      if (mode !== 'history') return;
      const box = document.createElement('div'); box.className = 'list'; w.innerHTML = ''; w.appendChild(box);
      const s = document.createElement('div'); s.className = 'sect'; s.style.padding = '2px 2px 8px'; s.textContent = 'This session, newest first'; box.appendChild(s);
      const items = h.history.slice().reverse();
      if (!items.length) box.insertAdjacentHTML('beforeend', '<div class="empty">Nothing changed yet.</div>');
      for (const e of items) {
        const r = document.createElement('div'); r.className = 'row';
        r.innerHTML = `<div><div></div><div class="n"></div></div>`;
        r.firstChild.firstChild.textContent = e.what;
        r.querySelector('.n').textContent = e.t + (e.tiles ? ` · ${e.tiles} tile${e.tiles === 1 ? '' : 's'} · ${e.x}, ${e.y}` : '');
        if (e.tiles) r.onclick = () => centerOn(e.x, e.y);
        box.appendChild(r);
      }
      const s2 = document.createElement('div'); s2.className = 'sect'; s2.style.padding = '14px 2px 8px'; s2.textContent = 'Backups from saves'; box.appendChild(s2);
      if (!h.backups.length) box.insertAdjacentHTML('beforeend', '<div class="empty">None yet: every save keeps a copy of the files from before it.</div>');
      h.backups.slice().reverse().forEach((b, i) => {
        const r = document.createElement('div'); r.className = 'row';
        r.innerHTML = `<div><div class="mono"></div><div class="n"></div></div>`;
        r.querySelector('.mono').textContent = b.replace(/^(\d{4})(\d\d)(\d\d)-(\d\d)(\d\d)(\d\d)$/, '$1-$2-$3 $4:$5:$6');
        r.querySelector('.n').textContent = i === 0 ? 'the world before the last save · "Undo last save" goes back to it' : 'the world before an earlier save';
        box.appendChild(r);
      });
    });
  } else if (mode === 'help') {
    w.innerHTML = `<div class="keys" style="padding:4px 2px">
      <p><b style="color:var(--gold2)">Editing</b> works while the game server is stopped. While it runs you can look around: NPCs and players are shown live.</p>
      <p><b style="color:var(--gold2)">Pick something</b> on the left (a floor, a flag, a wall, an object or an item), then paint it with the
      <b>brush</b>, a <b>rectangle</b> or <b>fill</b>. Fill covers the room you click into (up to its walls), or with a floor, the patch of the same floor.</p>
      <p><b style="color:var(--gold2)">Alt</b> paints the opposite: with a flag it clears it, with a wall/object/item it erases.</p>
      <p><b style="color:var(--gold2)">Select</b> (V) a tile to see everything on it in the right panel and change it there: floor, object, item, flags.</p>
      <p><b style="color:var(--gold2)">Save to the game</b> writes the map; the files from before are kept as a backup, and <b>Undo last save</b> puts them back. Afterwards the lighting can be recomputed with <span class="mono">./server light</span> (button in the right panel after a save).</p>
      <p><b style="color:var(--gold2)">NPCs</b> (tab NPCs): pick one, choose where it faces, click a free tile. You get your own copy of it (a new template from 2000 up) that spawns and respawns on that tile, with its items, about a second after the server starts; until then it shows faded. Select an NPC to turn it, move it or remove it. Alt+click with an NPC picked removes the NPC on that tile.</p>
      <p><b style="color:var(--gold2)">Pentagrams</b> still need build mode in the game (they are numbered there).</p></div>`;
  }
}
$('#lsearch').oninput = () => leftUI();
document.querySelectorAll('nav button').forEach(b => b.onclick = () => {
  mode = b.dataset.m; document.querySelectorAll('nav button').forEach(x => x.classList.toggle('on', x === b)); $('#lsearch').value = '';
  $('#app').classList.toggle('srvmode', mode === 'server');
  if (mode === 'server') { srvRefresh(); logRefresh(true); return; }
  leftUI(); setTimeout(resize, 0);
});

// ---------------------------------------------------------------- right panel
function layersUI() {
  const L = [['floors', 'Floors'], ['walls', 'Walls and objects'], ['items', 'Items'], ['chars', 'Characters'], ['npcnames', 'NPC and player names (N)'], ['see', 'See through walls (W)'], ['light', 'Light from lamps (L)'], ['grid', 'Grid (G)'], ['names', 'Area names']];
  $('#layers').innerHTML = L.map(([k, v]) => `<label class="chk"><input type="checkbox" data-l="${k}" ${show[k] ? 'checked' : ''}><span>${v}</span></label>`).join('');
  $('#layers').querySelectorAll('input').forEach(i => i.onchange = () => { show[i.dataset.l] = i.checked; toggles(); redraw(); try { localStorage.setItem('myv2.npcnames', show.npcnames ? '1' : '0'); } catch (e) {} });
  $('#flagshow').innerHTML = FLAGS.map((f, i) => `<label class="chk"><input type="checkbox" data-f="${i}" ${flagOn.has(i) ? 'checked' : ''}><span class="dot" style="background:${FCOL[i]}"></span><span>${f}</span></label>`).join('');
  $('#flagshow').querySelectorAll('input').forEach(i => i.onchange = () => { const b = +i.dataset.f; i.checked ? flagOn.add(b) : flagOn.delete(b); redraw(); });
  toggles();
}
function toggles() {
  $('#tgrid').classList.toggle('on', show.grid); $('#twalls').classList.toggle('on', show.see); $('#tlight').classList.toggle('on', show.light);
}
function flipShow(k) { show[k] = !show[k]; layersUI(); redraw(); }
$('#tgrid').onclick = () => flipShow('grid'); $('#twalls').onclick = () => flipShow('see'); $('#tlight').onclick = () => flipShow('light');
$('#tright').onclick = () => {
  const hid = $('#app').classList.toggle('noright');
  $('#tright').textContent = hid ? '‹' : '›'; $('#tright').title = hid ? 'Show the right panel' : 'Hide the right panel';
  setTimeout(resize, 0);
};

let selPatrol = null;   // the patrol route of the selected NPC: [[x, y], ...]
async function selectTile(x, y) {
  selTile = { x, y }; selPatrol = null; redrawTop();
  const r = await api(`/api/tile?x=${x}&y=${y}`);
  if (!selTile || selTile.x !== x || selTile.y !== y) return;
  const ro = RO();
  const el = $('#tile');
  el.innerHTML = `<div class="hd mono">${x}, ${y}</div><div>${esc(r.zone || 'no zone')}</div>
    <div class="kv">
      <span class="k">Floor</span><span class="v" id="tf"></span>
      <span class="k">Object</span><span class="v" id="to"></span>
      <span class="k">Item</span><span class="v" id="ti"></span>
      ${r.char || r.pending ? `<span class="k">${r.char && r.char.player ? 'Player' : 'NPC'}</span><span class="v" id="tc"></span>` : ''}
      <span class="k">Light</span><span class="v">${r.light}</span>
    </div>
    <div class="flg" id="tfl"></div>`;
  const tf = $('#tf'); tf.appendChild(thumb(r.floor, 28));
  const fin = document.createElement('input'); fin.type = 'number'; fin.value = r.floor; fin.disabled = ro; fin.title = 'Type a floor sprite number';
  fin.onchange = () => edit([{ op: 'floor', x, y, s: +fin.value, set: false }], 'floor ' + fin.value, true);
  tf.appendChild(fin);
  const to = $('#to');
  if (r.object) {
    to.appendChild(thumb(r.object, 28)); to.insertAdjacentHTML('beforeend', `<span class="nm mono">${r.object}${r.flags.includes('move block') ? ' · blocks' : ''}</span>`);
    if (!ro) { const b = document.createElement('button'); b.className = 'x'; b.textContent = 'remove'; b.onclick = () => edit([{ op: 'erase', x, y }], 'erase', true); to.appendChild(b); }
  } else to.textContent = '–';
  const ti = $('#ti');
  if (r.item) {
    ti.appendChild(thumb(r.item.sprite, 28));
    const n = document.createElement('span'); n.className = 'nm'; n.textContent = r.item.name; n.title = `template ${r.item.temp} · driver ${r.item.driver}${r.item.desc ? '\n' + r.item.desc : ''}`; ti.appendChild(n);
    if (!ro) { const b = document.createElement('button'); b.className = 'x'; b.textContent = 'remove'; b.onclick = () => edit([{ op: 'erase', x, y }], 'erase', true); ti.appendChild(b); }
  } else ti.textContent = '–';
  if (r.char) { const n = document.createElement('span'); n.className = 'nm'; n.textContent = `${r.char.name} (template ${r.char.temp})`; $('#tc').appendChild(n); }
  if (r.pending) { $('#tc').appendChild(thumb(r.pending.sprite, 28)); const n = document.createElement('span'); n.className = 'nm'; n.textContent = `${r.pending.name} (template ${r.pending.temp}) · spawns here`; $('#tc').appendChild(n); }
  if ((r.char && !r.char.player) || r.pending) npcEditor(el, r, x, y, ro);
  const pr = (r.char || r.pending || {}).patrol;
  if (pr && pr.length) { selPatrol = [[x, y], ...pr]; redrawTop(); }
  if (r.item) { lootEditor(el, r, x, y, ro); itemEditor(el, r, x, y, ro); }
  const fl = $('#tfl');
  FLAGS.forEach((f, i) => {
    const on = r.flags.includes({ 'blocks walking': 'move block', 'blocks sight': 'sight block', 'no fighting': 'no fight' }[f] || f);
    const l = document.createElement('label'); l.className = 'chk';
    l.innerHTML = `<input type="checkbox" ${on ? 'checked' : ''} ${ro ? 'disabled' : ''}><span class="dot" style="background:${FCOL[i]}"></span><span></span>`;
    l.lastChild.textContent = f;
    l.firstChild.onchange = e => edit([{ op: 'flag', x, y, bit: i, mode: e.target.checked ? 1 : 0 }], (e.target.checked ? 'set ' : 'cleared ') + f, true);
    fl.appendChild(l);
  });
}


// ---- loot: chests, flowers, shelves... (item drivers that give something when used)
const LOOT = { 1: 'gives one item', 42: 'gives one item at random', 59: 'gives gold', 30: 'needs an item in the hand, which it takes', 53: 'gives an item engraved with the player\'s name', 54: 'gives an item and alerts the monsters nearby', 75: 'MyV2 chest' };
const LEGACY_TIER = { 57: ['bronze', 'helm'], 59: ['bronze', 'armor'], 63: ['steel', 'helm'], 65: ['steel', 'armor'], 69: ['golden', 'helm'], 71: ['golden', 'armor'],
  75: ['crystal', 'helm'], 76: ['crystal', 'armor'], 94: ['titanium', 'helm'], 95: ['titanium', 'armor'], 981: ['emerald', 'helm'], 982: ['emerald', 'armor'] };
const METALS = [['any', 'any metal'], ['bronze', 'Bronze'], ['steel', 'Steel'], ['golden', 'Golden'], ['emerald', 'Emerald'], ['crystal', 'Crystal'], ['titanium', 'Titanium']];
const durText = t => { const s2 = Math.round(t / 18); return s2 >= 3600 ? (s2 / 3600).toFixed(s2 % 3600 ? 1 : 0) + ' h' : s2 >= 60 ? Math.round(s2 / 60) + ' min' : s2 + ' s'; };
function legacyRewards(it) {     // what an old-style loot item gives, as editor rewards
  const d = it.data, out = [];
  if (it.driver === 59) out.push({ type: 'gold', v: d[0] * 100, w: 1 });
  else if (it.driver === 42) {
    const cnt = {}; for (const v of d) if (v) cnt[v] = (cnt[v] || 0) + 1;
    const LV = { bronze: 3, steel: 6, golden: 9, emerald: 12, crystal: 15, titanium: 18 };     // as the old chests made them
    for (const [t, w] of Object.entries(cnt)) { const lt = LEGACY_TIER[t]; out.push(lt ? { type: 'tier', tiers: ['magic'], metals: [lt[0]], piece: lt[1], lo: LV[lt[0]] - 1, hi: LV[lt[0]] + 1, w } : { type: 'item', v: +t, w }); }
  } else if (d[0]) out.push({ type: 'item', v: d[0], w: 1 });
  return out;
}
function rewardText(r) {
  if (r.type === 'gold') return `${Math.floor(r.v / 100)}G ${r.v % 100}S`;
  if (r.type === 'nothing') return 'nothing ("It\'s empty...")';
  if (r.type === 'tier') return `a new ${(r.tiers || ['magic']).join('/')} ${r.metals === 'fit' || !r.metals ? '' : r.metals.join('/') + ' '}${r.piece === 'any' ? 'helmet or armor' : r.piece === 'helm' ? 'helmet' : 'body armor'}${r.lo ? `, level ${r.lo}${r.hi > r.lo ? '-' + r.hi : ''}` : ''}`;
  return (iname(r.v) || 'template ' + r.v) + (r.type === 'unique' ? ' (only once on the server)' : '');
}
// the chest on a tile: a short summary in the side panel; the editing happens in the big window (openChest)
async function lootEditor(el, r, x, y, ro) {
  const it = r.item;
  if (!(it.driver in LOOT)) return;
  const box = document.createElement('div'); box.className = 'ied'; el.appendChild(box);
  const tk = await api(`/api/chest?x=${x}&y=${y}`);
  if (!box.isConnected) return;
  const isNew = it.driver === 75, C = isNew ? tk.chest : null;
  const rw = C ? C.rewards : legacyRewards(it), tot = rw.reduce((a, b) => a + (+b.w || 0), 0) || 1;
  box.innerHTML = `<div class="lb" style="color:var(--gold2)">${isNew ? 'Chest' : 'Loot · ' + esc(LOOT[it.driver])}</div><div class="note"></div>`;
  const ul = box.querySelector('.note');
  ul.innerHTML = rw.length ? rw.map(q => `${esc(rewardText(q))}${rw.length > 1 ? ` <span class="hint">· ${Math.round((+q.w || 0) / tot * 100)}%</span>` : ''}`).join('<br>')
    : `<span class="hint">${isNew ? 'no rewards set yet: it is empty' : 'nothing set'}</span>`;
  if (it.driver === 30) ul.innerHTML += `<br><span class="hint">takes: ${esc(iname(it.data[1]) || 'template ' + it.data[1])}</span>`;
  ul.innerHTML += `<br><span class="hint">opens again after ${C ? durText((C.refill || 0) * 18) : durText(it.duration)}${C && C.once ? ' · once per player' : ''}</span>`;
  const b = document.createElement('button'); b.className = 'sm'; b.style.marginTop = '6px';
  b.textContent = isNew ? 'Edit chest…' : 'Convert to an editor chest…';
  b.title = 'Opens the chest editor: weighted rewards with items, gold, tier armor, once-only items, once per player, its own refill time';
  b.onclick = () => openChest(x, y);
  box.append(b);
}

async function openChest(x, y) {
  if (tplDirty() && !confirm('You have changes here you did not apply. Leave them?')) return;
  const [r, tk] = await Promise.all([api(`/api/tile?x=${x}&y=${y}`), api(`/api/chest?x=${x}&y=${y}`)]);
  const it = r.item;
  if (!it || !(it.driver in LOOT)) return toast(`There is no chest on ${x}, ${y}.`, true);
  const isNew = it.driver === 75;
  let C = isNew && tk.chest ? JSON.parse(JSON.stringify(tk.chest)) : null;
  if (isNew && !C) C = { refill: 3600, once: 0, rewards: [] };
  TP = { kind: 'chest', t: x + ',' + y, x, y, it, isNew, name: it.name, C, orig: {}, cur: {}, tab: 'chest' };
  TP.Corig = JSON.stringify(C) + '|' + it.name;
  $('#tpl').classList.add('on'); $('#tpl').classList.remove('picking'); tplRender();
}
function chestDirty() { return TP && TP.kind === 'chest' && JSON.stringify(TP.C) + '|' + TP.name !== TP.Corig; }

const RW_TYPES = [['item', 'Item', 'One item from a template'], ['gold', 'Gold', 'A sum of money'], ['tier', 'Tier armor', 'A newly made magic, rare or epic helmet or body armor'],
  ['unique', 'Once on the server', 'An item only one player ever gets'], ['nothing', 'Nothing', '"It\'s empty..." (makes the good things rarer)']];
const RW_COL = { item: '#8fb6d8', gold: '#e2b84a', tier: '#b58be0', unique: '#e0775a', nothing: '#6f675a' };
function newReward(type, w) {
  return type === 'tier' ? { type, tiers: ['magic'], metals: 'fit', piece: 'any', lo: 1, hi: 6, w } : type === 'gold' ? { type, v: 1000, w } : type === 'nothing' ? { type, w } : { type, v: 0, w };
}
function chestRender(el) {
  const it = TP.it, ro = RO();
  el.querySelector('.ttl').innerHTML = '';
  el.querySelector('.ttl').append(thumb(it.sprite, 34));
  el.querySelector('.ttl').insertAdjacentHTML('beforeend', '<span style="vertical-align:middle;margin-left:8px"></span><small></small>');
  el.querySelector('.ttl span').textContent = TP.name || 'Chest';
  el.querySelector('.ttl small').textContent = `chest on ${TP.x}, ${TP.y}${TP.isNew ? '' : ' · ' + LOOT[it.driver]}`;
  el.querySelector('.mtabs').innerHTML = '<button class="on">Rewards</button>';
  const body = el.querySelector('.mbody'); body.innerHTML = '';
  const again = () => { const st = body.scrollTop; chestRender(el); el.querySelector('.mbody').scrollTop = st; };
  const ft = el.querySelector('.mft');
  if (!TP.C) {        // an old-style one: what it gives now, and Convert
    const rw = legacyRewards(it), tot = rw.reduce((a, b) => a + b.w, 0);
    body.innerHTML = `<h4>What it gives now</h4><div class="note2"></div>
      <h4>Make it an editor chest</h4><div class="hint" style="max-width:640px">Then you choose its rewards here: items, gold, newly made tier armor and items only one player ever gets, each with a chance.
      You also set how long it stays empty after it is opened, and whether each player gets something from it only once. What it gives now is filled in to start with.</div>`;
    const n2 = body.querySelector('.note2');
    n2.innerHTML = (rw.length ? rw.map(q => `${esc(rewardText(q))}${rw.length > 1 ? ` <span class="hint">· ${Math.round(q.w / tot * 100)}%</span>` : ''}`).join('<br>') : '<span class="hint">nothing set</span>')
      + (it.driver === 30 ? `<br><span class="hint">takes: ${esc(iname(it.data[1]) || 'template ' + it.data[1])}</span>` : '')
      + `<br><span class="hint">opens again after ${durText(it.duration)}</span>`;
    ft.innerHTML = '<span class="sp"></span><button class="btn ghost" id="tcancel">Close</button><button class="btn pri" id="tconv">Convert…</button>';
    $('#tcancel').onclick = closeTemplate;
    $('#tconv').disabled = ro;
    $('#tconv').onclick = () => {
      if ([30, 53, 54].includes(it.driver) && !confirm('Converting drops its special part (' + LOOT[it.driver] + '). Convert anyway?')) return;
      TP.C = { refill: Math.round(it.duration / 18), once: 0, rewards: rw.length ? rw : [newReward('item', 1)] }; again();
    };
    return;
  }
  const C = TP.C;
  // --- how it opens
  body.insertAdjacentHTML('beforeend', '<h4>The chest</h4>');
  const g = document.createElement('div'); g.className = 'grid2'; body.append(g);
  const nm = document.createElement('input'); nm.type = 'text'; nm.maxLength = 39; nm.value = TP.name; nm.oninput = () => { TP.name = nm.value; };
  const rf = document.createElement('div'); rf.className = 'ipick';
  rf.append(num(() => Math.round((C.refill || 0) / 60), v => { C.refill = v * 60; }, 0, 100000), 'minutes', Object.assign(document.createElement('span'), { className: 'hint', textContent: '(0 = right away; 60 = an hour)' }));
  g.append(Object.assign(document.createElement('div'), { className: 'lb', textContent: 'Name players see' }), nm,
    Object.assign(document.createElement('div'), { className: 'lb', textContent: 'Stays empty for' }), rf,
    Object.assign(document.createElement('div'), { className: 'lb', textContent: 'Once per player' }),
    chk('Each player gets something from it only once (others still can)', () => !!C.once, on => C.once = on ? 1 : 0));
  // --- the chances
  const tot = C.rewards.reduce((a, b) => a + (+b.w || 0), 0) || 1;
  body.insertAdjacentHTML('beforeend', `<h4>Rewards <span class="hint" style="font-weight:400">· one is drawn by its chance each time it is opened</span></h4>`);
  if (C.rewards.length) {
    const bar = document.createElement('div'); bar.className = 'cbar';
    C.rewards.forEach((q, i) => { const s = document.createElement('div'); s.style.flex = String(+q.w || 0); s.style.background = RW_COL[q.type]; s.title = `${i + 1}. ${rewardText(q)} · ${Math.round((+q.w || 0) / tot * 100)}%`; s.textContent = i + 1; bar.append(s); });
    body.append(bar);
  } else body.insertAdjacentHTML('beforeend', '<div class="hint">No rewards yet: it is empty. Add one below.</div>');
  const list = document.createElement('div'); list.className = 'rwl'; body.append(list);
  C.rewards.forEach((q, i) => {
    const card = document.createElement('div'); card.className = 'rwc'; card.style.borderLeftColor = RW_COL[q.type];
    const hd = document.createElement('div'); hd.className = 'rwh';
    hd.insertAdjacentHTML('beforeend', `<b>${i + 1}</b>`);
    const ty = document.createElement('div'); ty.className = 'seg2';
    for (const [v, l, tip] of RW_TYPES) {
      const b = document.createElement('button'); b.textContent = l; b.title = tip; b.className = q.type === v ? 'on' : '';
      b.onclick = () => { if (q.type !== v) { C.rewards[i] = (v === 'unique' && q.type === 'item') || (v === 'item' && q.type === 'unique') ? { ...q, type: v } : newReward(v, q.w); again(); } };
      ty.append(b);
    }
    hd.append(ty, Object.assign(document.createElement('span'), { className: 'sp' }));
    const wt = document.createElement('div'); wt.className = 'ipick';
    wt.append('chance weight', num(() => q.w, v => { q.w = v; again(); }, 1, 1000), Object.assign(document.createElement('span'), { className: 'pct', textContent: Math.round((+q.w || 0) / tot * 100) + '%' }));
    const up = document.createElement('button'); up.className = 'sm'; up.textContent = '↑'; up.title = 'Move up'; up.disabled = !i;
    up.onclick = () => { C.rewards.splice(i - 1, 0, C.rewards.splice(i, 1)[0]); again(); };
    const cp = document.createElement('button'); cp.className = 'sm'; cp.textContent = 'Copy'; cp.title = 'Add a copy of this reward';
    cp.onclick = () => { C.rewards.splice(i + 1, 0, JSON.parse(JSON.stringify(q))); again(); };
    const xx = document.createElement('button'); xx.className = 'sm'; xx.textContent = '×'; xx.title = 'Remove this reward';
    xx.onclick = () => { C.rewards.splice(i, 1); again(); };
    hd.append(wt, up, cp, xx); card.append(hd);
    const bd = document.createElement('div'); bd.className = 'grid2'; card.append(bd);
    const row = (l, e) => { bd.append(Object.assign(document.createElement('div'), { className: 'lb', textContent: l }), e); };
    if (q.type === 'item' || q.type === 'unique') {
      row('Item', ipick(() => q.v, v => { q.v = v; }, { filter: t => t[3], none: 'pick one' }));
      if (q.type === 'unique') bd.append(document.createElement('div'), Object.assign(document.createElement('div'), { className: 'hint', textContent: 'Only one player ever gets it from this chest; after that it is left out of the draw. (Items marked Unique are also left out while a copy exists anywhere.)' }));
    } else if (q.type === 'gold') {
      const d2 = document.createElement('div'); d2.className = 'ipick';
      d2.append(num(() => Math.floor(q.v / 100), v => { q.v = v * 100 + q.v % 100; }, 0), 'gold', num(() => q.v % 100, v => { q.v = Math.floor(q.v / 100) * 100 + v; }, 0, 99), 'silver');
      row('Amount', d2);
    } else if (q.type === 'tier') {
      const chips = (opts, has, toggle) => { const d2 = document.createElement('div'); d2.className = 'chips';
        for (const [v, l] of opts) { const b2 = document.createElement('button'); b2.className = 'chip' + (has(v) ? ' on' : ''); b2.textContent = l; b2.onclick = () => { toggle(v); again(); }; d2.append(b2); }
        return d2; };
      q.tiers = q.tiers || ['magic'];
      row('Tier', chips([['magic', 'Magic'], ['rare', 'Rare'], ['epic', 'Epic']], v => q.tiers.includes(v),
        v => { q.tiers = q.tiers.includes(v) ? q.tiers.filter(x => x !== v) : [...q.tiers, v]; if (!q.tiers.length) q.tiers = [v]; }));
      const lv = document.createElement('div'); lv.className = 'ipick';
      lv.append(num(() => q.lo || 1, v => { q.lo = v; if ((q.hi || 0) < v) q.hi = v; again(); }, 1, 20), 'to', num(() => q.hi || q.lo || 1, v => { q.hi = Math.max(v, q.lo || 1); if (!q.lo) q.lo = 1; again(); }, 1, 20));
      row('Level', lv);
      row('Metal', chips([['fit', 'Fits the level'], ...METALS.slice(1)], v => v === 'fit' ? q.metals === 'fit' : Array.isArray(q.metals) && q.metals.includes(v),
        v => { if (v === 'fit') q.metals = 'fit'; else { const cur = Array.isArray(q.metals) ? q.metals : []; q.metals = cur.includes(v) ? cur.filter(x => x !== v) : [...cur, v]; if (!q.metals.length) q.metals = 'fit'; } }));
      row('Piece', chips([['any', 'Helmet or body armor'], ['helm', 'Helmet'], ['armor', 'Body armor']], v => (q.piece || 'any') === v, v => { q.piece = v; }));
      bd.append(document.createElement('div'), Object.assign(document.createElement('div'), { className: 'hint',
        textContent: (q.tiers.length > 1 ? 'Several tiers: drawn like monster drops (Magic 70 : Rare 22 : Epic 8). ' : '') +
          (q.metals === 'fit' ? 'Metal: one that fits the level, like monster drops (Bronze 1-6, Steel 1-20, Golden 5-14, Emerald 9-17, Crystal 11-20, Titanium 16-20).' : 'Metal: one of these, at a level in your range.') + (q.lo ? '' : ' Level: the old chest\'s own range (set one to change it).') }));
    } else row('', Object.assign(document.createElement('div'), { className: 'hint', textContent: 'The player gets nothing ("It\'s empty..."). Use it to make the other rewards rarer.' }));
    list.append(card);
  });
  const ad = document.createElement('div'); ad.className = 'rwadd';
  ad.append(Object.assign(document.createElement('span'), { className: 'hint', textContent: 'Add:' }));
  for (const [v, l, tip] of RW_TYPES) { const b = document.createElement('button'); b.className = 'btn sec'; b.textContent = '+ ' + l; b.title = tip; b.onclick = () => { C.rewards.push(newReward(v, 1)); again(); setTimeout(() => { const m = el.querySelector('.mbody'); m.scrollTop = m.scrollHeight; }, 0); }; ad.append(b); }
  body.append(ad);
  ft.innerHTML = `<span class="hint">${TP.isNew ? '' : 'Saving makes it an editor chest. '}${info.running ? 'Live: goes straight into the running game.' : ''}</span><span class="sp"></span><button class="btn ghost" id="tcancel">Close</button><button class="btn pri" id="tapply">${TP.isNew ? 'Save chest' : 'Save and convert'}</button>`;
  $('#tcancel').onclick = closeTemplate;
  $('#tapply').disabled = ro;
  $('#tapply').onclick = async () => {
    if (C.rewards.some(q => (q.type === 'item' || q.type === 'unique') && !q.v)) return toast('Pick an item for every item reward.', true);
    const r2 = await api('/api/chest', { x: TP.x, y: TP.y, chest: C });
    if (r2.error) return toast(r2.error, true);
    const op = { op: 'itemedit', x: TP.x, y: TP.y };
    if (!TP.isNew) op.driver = 75;
    if (TP.name !== TP.it.name) op.name = TP.name;
    if (Object.keys(op).length > 3) await edit([op], `${TP.isNew ? 'chest' : 'converted ' + TP.it.name + ' to an editor chest'} at ${TP.x},${TP.y}`, false);
    TP.isNew = true; TP.it = { ...TP.it, driver: 75, name: TP.name };
    TP.Corig = JSON.stringify(C) + '|' + TP.name;
    toast('Chest: ' + r2.msg); chestRender(el);
    if (selTile && selTile.x === TP.x && selTile.y === TP.y) selectTile(TP.x, TP.y);
  };
}

// ---- + Chest: one plain chest for the whole map; each one placed gets its own rewards
async function chestBrush() {
  let row = pal.templates.find(t => t[4] === 75 && t[1] === 'Chest') || pal.templates.find(t => t[4] === 75);
  if (!row) {
    if (RO()) return toast('The game server is running and live editing is not available.', true);
    const src = pal.templates.find(t => t[1] === 'Treasure Chest' && t[4] === 42) || pal.templates.find(t => /chest/i.test(t[1]) && !t[3]);
    if (!src) return toast('No chest template found to start from.', true);
    const r = await api('/api/edit', { ops: [{ op: 'itempnew', from: src[0], name: 'Chest' }], label: 'new item template Chest' });
    if (r.error || !r.made) return toast(r.error || (r.msgs || []).join('\n') || 'Could not make it.', true);
    const t = r.made[1];
    await edit([{ op: 'itempset', t, fields: { driver: 75, data: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] }, update_map: false }], 'Chest template ' + t + ' is an editor chest');
    const it = await api('/api/itemp?t=' + t);
    row = [t, it.name, it.sprite[0], bit(it.flags, 2) ? 1 : 0, it.driver, (bit(it.flags, 0) ? 1 : 0) | (bit(it.flags, 1) ? 2 : 0),
      (bit(it.flags, 2) || bit(it.flags, 4) || bit(it.flags, 5) || bit(it.flags, 9) || bit(it.flags, 10)) ? 1 : 0];
    pal.templates.push(row);
  }
  setBrush({ kind: 'place', t: row });
  if (mode === 'map') leftUI();
  toast('Chest brush ready: click a free spot on the map; its rewards window opens.');
}
function cellChest() {
  const c = document.createElement('div'); c.className = 'cell chestcell';
  const row = pal.templates.find(t => t[4] === 75 && t[1] === 'Chest');
  c.dataset.k = row ? 'place:' + row[0] : 'chest:new';
  if (brushKey(brush) === c.dataset.k) c.classList.add('sel');
  c.title = 'A plain chest. Click a spot on the map to put one there, then choose what it gives. Every chest you place has its own rewards.';
  c.appendChild(thumb(row ? row[2] : 220, 64, 64)); const l = document.createElement('div'); l.className = 'lab'; l.textContent = '+ Chest'; c.appendChild(l);
  c.onclick = chestBrush;
  return c;
}

// ---- the NPC on the selected tile: facing, move, remove
let npcPick = null;    // {x, y}: the next click on the map moves this NPC there
function npcEditor(el, r, x, y, ro) {
  const c = r.char || r.pending, live = !!r.char;
  const box = document.createElement('div'); box.className = 'ied';
  let note = '';
  if (c.home) note = `Spawns at ${c.home[0]}, ${c.home[1]}` + (c.made ? ' · placed with the editor' : '') + (live ? '' : ' · appears when the server runs');
  else if (live) note = c.respawns ? `Its template spawns at another spot: this one was made by a spawner or quest. Moving or removing it changes only this one.` : 'Does not respawn (made by a spawner, a quest or a god).';
  if (c.count > 1) note += ` · ${c.count} of this template are in the world`;
  box.innerHTML = `<div class="lb">NPC</div><div class="note"></div><div class="fr"></div>
    <div class="dest"><button class="sm mv" title="Then click the free tile it should go to">Move (pick on map)</button><button class="sm rm">Remove</button><button class="sm ed" title="Name, look, stats, equipment, what it says, patrol route…">Edit NPC…</button></div>`;
  box.querySelector('.note').textContent = note;
  box.querySelector('.fr').appendChild(faceRow(c.dir || 0, d => edit([{ op: 'npcdir', x, y, dir: d }], `${c.name} faces ${FACEN[d]}`, true), ro || (!live && !c.home)));
  const mv = box.querySelector('.mv'), rm = box.querySelector('.rm');
  box.querySelector('.ed').onclick = () => openTemplate('npc', c.temp);
  mv.disabled = rm.disabled = ro;
  mv.onclick = () => { npcPick = { x, y, name: c.name }; mv.classList.add('on'); cv.style.cursor = 'cell'; toast(`Click the free tile ${c.name} should move to. (Esc cancels)`); };
  rm.onclick = () => {
    const perm = c.home ? (c.made ? 'It was placed with the editor; it is taken out completely.' : 'It will not respawn any more (its template stops respawning).') : 'Only this one goes.';
    if (!confirm(`Remove ${c.name} from ${x}, ${y}? ${perm} (Ctrl+Z undoes it before you save.)`)) return;
    edit([{ op: 'npcremove', x, y }], 'removed ' + c.name, true);
  };
  el.appendChild(box);
}
function moveNpc(t) {
  const p = npcPick; npcPick = null; setTool(tool);
  edit([{ op: 'npcmove', x: p.x, y: p.y, tx: t.x, ty: t.y }], `moved ${p.name} to ${t.x},${t.y}`, false).then(() => selectTile(t.x, t.y));
}

// ---- the item on the selected tile: name, description, where a portal leads, data values
let destPick = null;   // {x, y}: the next click on the map sets where this portal leads
function itemEditor(el, r, x, y, ro) {
  const it = r.item, tele = it.driver === 6;
  const box = document.createElement('div'); box.className = 'ied';
  box.innerHTML = `<div class="lb">Item name</div><input type="text" maxlength="39" class="nm2">
    <div class="lb">Description (what players read when they look at it)</div><textarea maxlength="199" class="ds2"></textarea>
    ${tele ? `<div class="lb">Leads to</div><div class="dest">x <input type="number" class="dx"> y <input type="number" class="dy">
      <button class="sm pk" title="Then click the spot on the map">Pick on map</button><button class="sm gt">Go there</button></div>
      ${it.data[2] ? '<div class="warn">This is a labyrinth portal (data 2 = ' + it.data[2] + '): it takes players to their next lab part, not to x, y. <button class="sm np">Make it a normal portal</button></div>' : ''}` : ''}
    <details><summary class="lb" style="cursor:pointer">Data values (advanced, driver ${it.driver})</summary><div class="dgrid">${it.data.map((v, i) => `<input type="number" data-i="${i}" value="${v}" title="data[${i}]">`).join('')}</div></details>
    <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap"><button class="btn pri" style="padding:5px 12px">Save item</button><button class="sm et" title="Change what every ${esc(it.name)} is made from: look, stats, flags…">Edit its template…</button><button class="sm qr" title="What happens when a player uses it, by quest step (a portal that leads elsewhere, a door that only opens after a quest…)">Quest rules…</button></div>`;
  el.appendChild(box);
  const nm = box.querySelector('.nm2'), ds = box.querySelector('.ds2');
  nm.value = it.name; ds.value = it.desc || '';
  if (tele) { box.querySelector('.dx').value = it.data[0]; box.querySelector('.dy').value = it.data[1]; }
  box.querySelectorAll('.dgrid input').forEach(i => { if (tele && (i.dataset.i === '0' || i.dataset.i === '1')) i.disabled = true; });
  box.querySelectorAll('input,textarea,button').forEach(e => e.disabled = ro);
  const collect = () => {
    const data = {};
    box.querySelectorAll('.dgrid input').forEach(i => { if (+i.value !== it.data[+i.dataset.i]) data[i.dataset.i] = +i.value; });
    if (tele) { data[0] = +box.querySelector('.dx').value; data[1] = +box.querySelector('.dy').value; }
    return { op: 'itemedit', x, y, name: nm.value, desc: ds.value, data };
  };
  box.querySelector('.btn').onclick = () => edit([collect()], 'item ' + nm.value, true);
  box.querySelector('.et').disabled = false; box.querySelector('.et').onclick = () => openTemplate('item', it.temp);
  box.querySelector('.qr').disabled = false; box.querySelector('.qr').onclick = () => openTemplate('use', [x, y, it.name]);
  if (tele) {
    const pk = box.querySelector('.pk');
    pk.onclick = () => { destPick = { x, y }; pk.classList.add('on'); toast('Click the spot on the map where this portal should lead. (Esc cancels)'); cv.style.cursor = 'cell'; };
    const np = box.querySelector('.np');
    if (np) np.onclick = () => edit([{ op: 'itemedit', x, y, data: { 2: 0, 3: 0 } }], 'normal portal', true);
    box.querySelector('.gt').onclick = () => { const dx = +box.querySelector('.dx').value, dy = +box.querySelector('.dy').value; centerOn(dx, dy); toast('That is where it leads. Its own spot: ' + x + ', ' + y); };
  }
}
function setDestination(t) {
  const d = destPick; destPick = null; setTool(tool);
  edit([{ op: 'itemedit', x: d.x, y: d.y, data: { 0: t.x, 1: t.y } }], `portal at ${d.x},${d.y} leads to ${t.x},${t.y}`, false)
    .then(() => { toast(`The portal at ${d.x}, ${d.y} now leads to ${t.x}, ${t.y}.`); centerOn(d.x, d.y); selectTile(d.x, d.y); });
}

// ---------------------------------------------------------------- template editor (NPCs and items)
const ATTRS = ['Braveness', 'Willpower', 'Intuition', 'Agility', 'Strength'];
const SKILLS = ['Hand to Hand', 'Karate', 'Dagger', 'Sword', 'Axe', 'Staff', 'Two-Handed', 'Lock-Picking', 'Stealth', 'Perception',
  'Swimming', 'Magic Shield', 'Bartering', 'Repair', 'Light', 'Recall', 'Guardian Angel', 'Protection', 'Enhance Weapon', 'Stun',
  'Curse', 'Bless', 'Identify', 'Resistance', 'Blast', 'Dispel Magic', 'Heal', 'Ghost Companion', 'Regenerate', 'Rest',
  'Meditate', 'Sense Magic', 'Immunity', 'Surround Hit', 'Concentrate', 'Warcry', 'Two-Handed Axe'];
const WEAR = ['Head', 'Neck', 'Body', 'Arms', 'Belt', 'Legs', 'Feet', 'Left hand (shield)', 'Right hand (weapon)', 'Cloak', 'Left ring', 'Right ring'];
const CTEXT = [
  [2, 'Greeting', 'said when a player comes close (needs "Greets players" on the Behaviour tab)'],
  [6, 'Keyword', 'a word players can say to make it stop attacking them (the password)'],
  [7, 'Reply to the keyword', ''],
  [8, 'Warning', 'said before it attacks someone coming too close (Attack distance)'],
  [1, 'Attacking', 'said when it attacks someone'],
  [0, 'Killed an enemy', ''],
  [3, 'Dying words', 'said when it is killed (chance: Dying words chance)'],
  [4, 'Shouting for help', ''],
  [5, 'Coming to help', ''],
];
const AREAS = [[0, 'Only general things'], [4, 'Aston (the city)'], [1, 'Thieves'], [5, 'Thieves 2'], [2, 'The castle'], [3, 'Grolms'],
  [6, 'The tomb'], [7, 'Joe'], [8, 'Purple'], [9, 'Skeleton lord'], [10, 'Outlaws'], [11, 'Magic maze'], [12, 'Lizards'],
  [13, 'Underground I'], [14, 'Knights'], [15, 'The mine'], [16, 'The stronghold'], [17, 'The nest'],
  [21, 'Riddle 1'], [22, 'Riddle 2'], [23, 'Riddle 3'], [24, 'Riddle 4'], [25, 'Riddle 5'], [12345, 'Everything']];
const DATA_NAMES = { 0: 'Driver 1', 1: 'Driver 2', 2: 'Driver 3', 3: 'Driver 4', 4: 'Driver 5', 5: 'Driver 6', 6: 'Driver 7', 7: 'Driver 8', 8: 'Driver 9', 9: 'Driver 10',
  10: 'Patrol 1', 11: 'Patrol 2', 12: 'Patrol 3', 13: 'Patrol 4', 14: 'Patrol 5', 15: 'Patrol 6', 16: 'Patrol 7', 17: 'Patrol 8', 18: 'Patrol 9',
  20: 'Close door', 21: 'Close door', 22: 'Close door', 23: 'Close door', 24: 'Prevent fights', 25: 'Special driver', 26: 'Special sub-driver',
  29: 'Resting position', 30: 'Resting dir', 31: 'Protect template', 32: 'Light to keep lit', 33: 'Light to keep lit', 34: 'Light to keep lit', 35: 'Light to keep lit',
  37: 'Greet everyone', 41: 'Street light template', 42: 'Group', 43: 'Attack all but group', 44: 'Attack all but group', 45: 'Attack all but group',
  46: 'Attack all but group', 47: 'Donate trash', 48: 'Dying words %', 49: 'Wants item', 50: 'Teaches skill', 51: 'Gives exp', 52: 'Shout help code',
  53: 'Come help code', 59: 'Protect group', 60: 'Random walk time', 62: 'Create light', 64: 'Self destruct', 66: 'Gives item', 68: 'Knowledge level',
  69: 'Accepts money', 71: 'Talkativity', 72: 'Area of knowledge', 73: 'Random walk max dist', 79: 'Rest at patrol stops', 93: 'Attack distance', 95: 'Keyword action' };
const NPC_FLAGS = [[4, 'Respawns'], [10, 'Merchant (sells its backpack)'], [0, 'Immortal'], [16, 'Sees in the dark'], [19, 'Undead (holy water hurts)'],
  [18, 'Never sleeps'], [15, 'Invisible'], [27, 'Simple animation'], [31, 'Ignores spells'], [12, 'No HP regeneration']];
const ITEM_FLAGS = [
  ['What it is', [[8, 'Armor'], [16, 'Sword'], [17, 'Dagger'], [18, 'Axe'], [19, 'Staff / club'], [20, 'Two-handed'], [24, 'Magic'], [25, 'Misc'], [28, 'Unique'], [3, 'Money']]],
  ['What players can do', [[2, 'Pick it up'], [4, 'Look at it'], [5, 'Look (special)'], [9, 'Use it'], [10, 'Use (special, driver)'], [21, 'Using it destroys it'], [22, 'Can be turned on'], [23, 'Can be turned off']]],
  ['On the map', [[0, 'Blocks walking'], [1, 'Blocks sight'], [32, 'Hidden (data 9 = how hard to see)'], [33, 'Does something when stepped on']]],
  ['Rules', [[38, 'Never expires'], [34, 'Can\'t go in the depot'], [12, 'Destroyed in shops (quest item)'], [30, 'Destroyed when leaving the labyrinth'], [29, 'Donate (cheap)'], [31, 'Fixed price'], [7, 'Can\'t be repaired'], [40, 'Needs identifying'], [11, 'Single age'], [14, 'Expires when inactive'], [15, 'Expires when active'], [35, 'Ages faster in light']]]];
const PLACES = [[1, 'Head'], [2, 'Neck'], [4, 'Body'], [8, 'Arms'], [32, 'Belt'], [64, 'Legs'], [128, 'Feet'], [256, 'Weapon hand'], [512, 'Shield hand'], [1024, 'Cloak'], [2048, 'Two-handed'], [4096, 'Ring']];

const RANK_NAMES = ['Private', 'Private First Class', 'Lance Corporal', 'Corporal', 'Sergeant', 'Staff Sergeant', 'Master Sergeant', 'First Sergeant',
  'Sergeant Major', 'Second Lieutenant', 'First Lieutenant', 'Captain', 'Major', 'Lieutenant Colonel', 'Colonel', 'Brigadier General', 'Major General',
  'Lieutenant General', 'General', 'Field Marshal', 'Knight of Astonia', 'Baron of Astonia', 'Earl of Astonia', 'Warlord of Astonia'];
const RANK_PTS = [50, 850, 4900, 17700, 48950, 113750, 233800, 438600, 766650, 1266650, 1998700, 3035500, 4463550, 6384350, 8915600,
  12192400, 16368450, 21617250, 28133300, 36133300, 49014500, 63000600, 80977100];      // helper.c points2rank()
const rankOf = p => { let i = 0; while (i < RANK_PTS.length && p >= RANK_PTS[i]) i++; return i; };
function npcPoints(c) {     // an NPC's experience value, as the server's reset_char() works it out from its stats
  let p = 0;
  for (let z = 0; z < 5; z++) for (let m = 10; m < c.attrib[z * 6]; m++) p += Math.floor(m * m * m * 3 / 20);
  for (let m = 50; m < c.hp[0]; m++) p += m * 3;
  for (let m = 50; m < c.end[0]; m++) p += Math.floor(m * 2 / 2);
  for (let m = 50; m < c.mana[0]; m++) p += m * 3;
  for (let z = 0; z < 50; z++) { if (z === 7 || z === 8 || z === 9) continue; for (let m = 1; m < c.skill[z * 6]; m++) p += Math.max(m, Math.floor(m * m * m * 2 / 40)); }
  return p;
}
const bit = (f, b) => Math.floor(f / 2 ** b) % 2 === 1;
const setBit = (f, b, on) => bit(f, b) === on ? f : f + (on ? 1 : -1) * 2 ** b;
const pos = v => v ? [v % 1024, Math.floor(v / 1024)] : null;

let TP = null;   // {kind: 'npc'|'item', t, orig, cur, tab}
function talkDirty() { return TP && TP.talk && JSON.stringify(TP.talk) !== TP.talkOrig; }
function tplDirty() { return TP && (chestDirty() || Object.keys(tplChanged()).length || (TP.kind === 'player' && TP.nopass) || talkDirty() || (TP.kind === 'npc' && JSON.stringify(TP.cur.text) !== JSON.stringify(TP.orig.text))); }
function openTemplate(kind, t) {
  if (tplDirty() && !(TP.kind === kind && TP.t === t) && !confirm('You have changes here you did not apply. Leave them?')) return;
  if (kind === 'use') {    // quest rules of the item on a tile: t = [x, y, name]
    api(`/api/talk?at=${t[0]},${t[1]}`).then(tk => {
      TP = { kind, t: t[0] + ',' + t[1], x: t[0], y: t[1], orig: { name: t[2] }, cur: { name: t[2] }, tab: 'conv' };
      TP.talk = { entries: tk.entries || [], quests: tk.quests || {}, steps: tk.steps || {} }; TP.talkOrig = JSON.stringify(TP.talk);
      $('#tpl').classList.add('on'); $('#tpl').classList.remove('picking'); tplRender();
    });
    return;
  }
  Promise.all([api(`/api/${kind === 'npc' ? 'ctemp' : 'itemp'}?t=${t}`), kind === 'npc' ? api('/api/talk?t=' + t) : null]).then(([r, tk]) => {
    if (r.error) return toast(r.error, true);
    TP = { kind, t, orig: JSON.parse(JSON.stringify(r)), cur: r, tab: TP && TP.kind === kind ? TP.tab : 'general' };
    if (tk) { TP.talk = { entries: tk.entries || [], quests: tk.quests || {}, steps: tk.steps || {} }; TP.talkOrig = JSON.stringify(TP.talk); }
    $('#tpl').classList.add('on'); $('#tpl').classList.remove('picking');
    tplRender();
  });
}
function closeTemplate() { if (tplDirty() && !confirm('Close without applying your changes?')) return; TP = null; $('#tpl').classList.remove('on', 'picking'); $('#ipop').style.display = 'none'; }
function tplTabs() {
  if (TP.kind === 'use') return { conv: 'Quest rules' };
  if (TP.kind === 'player') return { overview: 'Overview', stats: 'Stats & skills', gear: 'Worn & backpack', depot: 'Depot', history: 'History', account: 'Account' };
  return TP.kind === 'npc'
    ? { general: 'General', stats: 'Stats & skills', gear: 'Equipment & stock', behave: 'Behaviour', patrol: 'Patrol route', talk: 'Talk & quest', conv: 'Conversations', adv: 'Advanced' }
    : { general: 'General', stats: 'Stats & requirements', adv: 'Advanced' };
}
function tplRender() {
  const c = TP.cur, el = $('#tpl');
  if (TP.kind === 'chest') return chestRender(el);
  if (TP.kind === 'use') {
    el.querySelector('.ttl').innerHTML = '<span style="vertical-align:middle"></span><small></small>';
    el.querySelector('.ttl span').textContent = 'Quest rules: ' + (c.name || 'item');
    el.querySelector('.ttl small').textContent = `on ${TP.x}, ${TP.y} · when a player uses it`;
    el.querySelector('.mtabs').innerHTML = '<button class="on">Quest rules</button>';
    const body = el.querySelector('.mbody'); body.innerHTML = ''; NPC_TABS.conv(body, c);
    el.querySelector('.mft').innerHTML = '<span class="sp"></span><button class="btn ghost" id="tcancel">Close</button><button class="btn pri" id="tapply">Apply</button>';
    $('#tcancel').onclick = closeTemplate;
    $('#tapply').onclick = async () => {
      const tr = await api('/api/talk', { at: [TP.x, TP.y], entries: TP.talk.entries, quests: TP.talk.quests, steps: TP.talk.steps });
      toast(tr.error || 'Quest rules: ' + tr.msg, !!tr.error); TP.talkOrig = JSON.stringify(TP.talk);
    };
    return;
  }
  if (TP.kind === 'player') {
    el.querySelector('.ttl').innerHTML = '';
    el.querySelector('.ttl').append(thumb(c.sprite + 8, 34));
    el.querySelector('.ttl').insertAdjacentHTML('beforeend', '<span style="vertical-align:middle;margin-left:8px"></span><small></small>');
    el.querySelector('.ttl span').textContent = c.name;
    el.querySelector('.ttl small').textContent = `${c.rank} · ${c.kin_name} · ${c.online ? 'online' : 'offline'} · character ${c.c}`;
    el.querySelector('.mtabs').innerHTML = Object.entries(tplTabs()).map(([k, v]) => `<button data-k="${k}" class="${k === TP.tab ? 'on' : ''}">${v}</button>`).join('');
    el.querySelectorAll('.mtabs button').forEach(bt => bt.onclick = () => { TP.tab = bt.dataset.k; tplRender(); });
    const body = el.querySelector('.mbody'); body.innerHTML = ''; PLAYER_TABS[TP.tab](body, c);
    el.querySelector('.mft').innerHTML = `<span class="hint">${c.online ? 'Live: Apply changes the character in the running game.' : info.running ? 'Offline character: Apply changes it in the running game\'s files.' : 'Server stopped: Apply, then Save to the game.'}</span><span class="sp"></span><button class="btn ghost" id="tcancel">Close</button><button class="btn pri" id="tapply">Apply</button>`;
    $('#tcancel').onclick = closeTemplate;
    $('#tapply').onclick = async () => {
      if (RO()) return toast('The game server is running and live editing is not available.', true);
      const f = tplChanged(), op = { op: 'pset', c: c.c, fields: f };
      delete f.bank; if (c.bank !== TP.orig.bank) op.bank = c.bank;
      if (TP.nopass) op.nopass = 1;
      if (!Object.keys(f).length && op.bank === undefined && !op.nopass) return toast('Nothing changed.');
      await edit([op], 'changed player ' + c.name);
      TP.nopass = false; TP.orig = JSON.parse(JSON.stringify(TP.cur)); openPlayer(c.c);
    };
    if (RO()) $('#tapply').disabled = true;
    return;
  }
  el.querySelector('.ttl').innerHTML = '';
  el.querySelector('.ttl').append(thumb(TP.kind === 'npc' ? c.sprite + 8 : c.sprite[0], 34));
  el.querySelector('.ttl').insertAdjacentHTML('beforeend', `<span style="vertical-align:middle;margin-left:8px"></span><small></small>`);
  el.querySelector('.ttl span').textContent = c.name || '(no name)';
  el.querySelector('.ttl small').textContent = TP.kind === 'npc'
    ? `${RANK_NAMES[rankOf(npcPoints(c))]} · NPC template ${TP.t}${c.made ? ' · made with the editor' : ''} · ${c.count} in the world${c.pending ? ' · ' + c.pending + ' waiting to spawn' : ''}${c.x || c.y ? ` · spawns at ${c.x}, ${c.y}` : ' · not placed'}`
    : `Item template ${TP.t}${c.made ? ' · made with the editor' : ''} · ${c.onmap} lying on the map`;
  const tabs = tplTabs();
  el.querySelector('.mtabs').innerHTML = Object.entries(tabs).map(([k, v]) => `<button data-k="${k}" class="${k === TP.tab ? 'on' : ''}">${v}</button>`).join('');
  el.querySelectorAll('.mtabs button').forEach(b => b.onclick = () => { TP.tab = b.dataset.k; tplRender(); });
  const body = el.querySelector('.mbody'); body.innerHTML = '';
  (TP.kind === 'npc' ? NPC_TABS : ITEM_TABS)[TP.tab](body, c);
  const ft = el.querySelector('.mft');
  ft.innerHTML = TP.kind === 'npc'
    ? `<label class="chk"><input type="checkbox" id="tresp" checked><span>Respawn the ones in the world with the changes</span></label>`
    : `<label class="chk"><input type="checkbox" id="tmap" checked><span>Also change the ${c.onmap} on the map (where they still have the old value)</span></label>`;
  ft.insertAdjacentHTML('beforeend', `<span class="sp"></span><button class="btn sec" id="tnew">Save as a new ${TP.kind === 'npc' ? 'NPC' : 'item'}…</button>
    <button class="btn ghost" id="tcancel">Close</button><button class="btn pri" id="tapply">Apply</button>`);
  $('#tcancel').onclick = closeTemplate;
  $('#tapply').onclick = () => tplApply(false);
  $('#tnew').onclick = () => tplApply(true);
  if (RO()) { $('#tapply').disabled = $('#tnew').disabled = true; $('#tapply').title = 'The game server is running: editing is off.'; }
  else if (info.running) $('#tapply').title = 'Live: goes straight into the running game';
}
function tplChanged() {
  const out = {}, o = TP.orig, c = TP.cur;
  if (TP.kind === 'use' || TP.kind === 'chest') return out;
  for (const k of Object.keys(c)) {
    if (['t', 'count', 'pending', 'made', 'names', 'onmap', 'text', 'items', 'item', 'worn', 'depot', 'citem', 'rank', 'kin_name', 'ip', 'quests', 'online', 'c'].includes(k)) continue;
    if (JSON.stringify(c[k]) !== JSON.stringify(o[k])) out[k] = c[k];
  }
  return out;
}
async function tplApply(asNew) {
  if (RO()) return toast('The game server is running: editing is off.', true);
  const f = tplChanged(), text = TP.kind === 'npc' && JSON.stringify(TP.cur.text) !== JSON.stringify(TP.orig.text) ? TP.cur.text : null;
  let t = TP.t;
  if (asNew) {
    const name = prompt(`Name for the new ${TP.kind === 'npc' ? 'NPC' : 'item'}:`, TP.cur.name);
    if (!name) return;
    const r = await api('/api/edit', { ops: [{ op: TP.kind === 'npc' ? 'ctempnew' : 'itempnew', from: TP.t, name }], label: 'new template ' + name });
    if (r.error || !r.made) return toast(r.error || (r.msgs || []).join('\n') || 'Could not make it.', true);
    t = r.made[1];
    f.name = name; f.reference = TP.kind === 'npc' ? name : name.toLowerCase();
  }
  if (TP.kind === 'npc' && TP.talk && TP.talk.entries.some(e => e.when === 'near') && !TP.cur.data[37]) { TP.cur.data[37] = 1; f.data = TP.cur.data; }
  if (TP.talk && (talkDirty() || (asNew && TP.talk.entries.length))) {
    const tr = await api('/api/talk', { t, entries: TP.talk.entries, quests: TP.talk.quests, steps: TP.talk.steps });
    toast(tr.error || 'Conversations: ' + tr.msg, !!tr.error);
    TP.talkOrig = JSON.stringify(TP.talk);
  }
  if (Object.keys(f).length || text) {
    const op = TP.kind === 'npc' ? { op: 'ctempset', t, fields: f, text, respawn: asNew ? false : $('#tresp').checked }
      : { op: 'itempset', t, fields: f, update_map: asNew ? false : $('#tmap').checked };
    await edit([op], `${asNew ? 'new' : 'changed'} ${TP.kind === 'npc' ? 'NPC' : 'item'} template ${t} (${f.name || TP.cur.name})`);
  } else if (!asNew && !TP.talk) return toast('Nothing changed.');
  if (TP.kind === 'item') {     // the palette and the map show the new name and look
    const i = pal.templates.findIndex(x => x[0] === t), r = await api('/api/itemp?t=' + t);
    const row = [t, r.name, r.sprite[0], bit(r.flags, 2) ? 1 : 0, r.driver, (bit(r.flags, 0) ? 1 : 0) | (bit(r.flags, 1) ? 2 : 0),
      (bit(r.flags, 2) || bit(r.flags, 4) || bit(r.flags, 5) || bit(r.flags, 9) || bit(r.flags, 10)) ? 1 : 0];
    if (i >= 0) pal.templates[i] = row; else pal.templates.push(row);
    chunks.clear(); redraw();
    if (asNew) setBrush({ kind: 'place', t: row });
  } else if (asNew) {
    const n = await api('/api/npcs'); pal.npcs = n;
    const row = n.find(x => x[0] === t); if (row) setBrush({ kind: 'npc', t: row, dir: 4 });
    toast(`New NPC ${t} made. Click a free tile to place it.`);
  } else chunks.clear(), redraw();
  if (mode === 'map') leftUI();
  TP.orig = JSON.parse(JSON.stringify(TP.cur));
  openTemplate(TP.kind, t);
}

// ---- small form builders
function row(box, label, input, hint) {
  const l = document.createElement('div'); l.className = 'lb'; l.textContent = label; box.appendChild(l);
  const d = document.createElement('div'); if (input) d.append(input);
  if (hint) { const h = document.createElement('div'); h.className = 'hint'; h.textContent = hint; d.append(h); }
  box.appendChild(d); return d;
}
function grid2(body, title) {
  if (title) { const h = document.createElement('h4'); h.textContent = title; body.appendChild(h); }
  const g = document.createElement('div'); g.className = 'grid2'; body.appendChild(g); return g;
}
function txt(get, set, max, area) {
  const i = document.createElement(area ? 'textarea' : 'input'); if (!area) i.type = 'text'; i.maxLength = max; i.value = get();
  i.oninput = () => set(i.value); return i;
}
function num(get, set, min, max) {
  const i = document.createElement('input'); i.type = 'number'; i.value = get(); if (min !== undefined) i.min = min; if (max !== undefined) i.max = max;
  i.onchange = () => { let v = Math.round(+i.value || 0); if (min !== undefined) v = Math.max(min, v); if (max !== undefined) v = Math.min(max, v); i.value = v; set(v); };
  return i;
}
function sel(opts, get, set) {
  const s = document.createElement('select');
  s.innerHTML = opts.map(([v, l]) => `<option value="${v}">${esc(l)}</option>`).join('');
  if (!opts.some(o => o[0] === get())) s.insertAdjacentHTML('beforeend', `<option value="${get()}">${get()} (other)</option>`);
  s.value = get(); s.onchange = () => set(+s.value); return s;
}
function chk(label, get, set) {
  const l = document.createElement('label'); l.innerHTML = '<input type="checkbox"><span></span>';
  l.lastChild.textContent = label; l.firstChild.checked = get(); l.firstChild.onchange = () => set(l.firstChild.checked); return l;
}
function chks(items) { const d = document.createElement('div'); d.className = 'chks'; items.forEach(i => d.append(i)); return d; }
function iname(t) { const x = t && pal.templates.find(r => r[0] === t); return x ? x[1] : ''; }
function ipick(get, set, opts) {   // an item template: number, name, Pick…, ×
  const d = document.createElement('div'); d.className = 'ipick';
  const n = document.createElement('input'); n.type = 'number'; n.min = 0; n.value = get() || 0;
  const th = thumb(0, 24); const nm = document.createElement('span'); nm.className = 'nm';
  const show = () => { const v = +n.value; const x = v && pal.templates.find(r => r[0] === v); nm.textContent = v ? (x ? x[1] : 'template ' + v + ' (empty!)') : (opts && opts.none) || 'none'; nm.classList.toggle('none', !v); th.dataset.spr = x ? x[2] : 0; paintThumb(th); };
  n.onchange = () => { set(+n.value || 0); show(); };
  const b = document.createElement('button'); b.className = 'sm'; b.textContent = 'Pick…';
  b.onclick = () => itemPopup(b, v => { n.value = v; set(v); show(); }, opts && opts.filter);
  const x = document.createElement('button'); x.className = 'sm'; x.textContent = '×'; x.title = 'Empty';
  x.onclick = () => { n.value = 0; set(0); show(); };
  const e = document.createElement('button'); e.className = 'sm'; e.textContent = 'Edit'; e.title = 'Open this item template';
  e.onclick = () => { if (+n.value) openTemplate('item', +n.value); };
  d.append(n, th, nm, b, x, e); show(); return d;
}
function itemPopup(anchor, pick, filter) {
  const p = $('#ipop'), r = anchor.getBoundingClientRect();
  p.style.display = 'flex'; p.style.left = Math.min(window.innerWidth - 350, r.left) + 'px'; p.style.top = Math.min(window.innerHeight - 390, r.bottom + 4) + 'px';
  const q = p.querySelector('input'), lst = p.querySelector('.lst'); q.value = ''; q.placeholder = 'Search an item by name or number';
  const fill = () => {
    const s = q.value.trim().toLowerCase();
    const items = pal.templates.filter(t => (!filter || filter(t)) && (!s || t[1].toLowerCase().includes(s) || String(t[0]) === s)).slice(0, 80);
    lst.innerHTML = '';
    for (const t of items) {
      const e = document.createElement('div'); e.className = 'r'; e.append(thumb(t[2], 26));
      const a = document.createElement('span'); a.textContent = t[1]; e.append(a);
      const b = document.createElement('span'); b.className = 'n'; b.textContent = t[0]; e.append(b);
      e.onmousedown = ev => { ev.preventDefault(); p.style.display = 'none'; pick(t[0]); };
      lst.append(e);
    }
    if (!items.length) lst.innerHTML = '<div class="hint" style="padding:6px">Nothing matches.</div>';
  };
  q.oninput = fill; fill(); setTimeout(() => q.focus(), 0);
}
document.addEventListener('mousedown', e => { const p = $('#ipop'); if (p.style.display !== 'none' && !p.contains(e.target)) p.style.display = 'none'; });

// ---- picking a spot on the map from inside the editor (patrol stops)
let tplPick = null;
function pickSpot(msg, done) {
  tplPick = done; $('#tpl').classList.add('picking'); cv.style.cursor = 'cell'; toast(msg + ' (Esc cancels)');
}
function tplPicked(t) { const f = tplPick; tplPick = null; $('#tpl').classList.remove('picking'); setTool(tool); if (f && t) f(t); tplRender(); }

// ---- NPC tabs
const NPC_TABS = {
  general(b, c) {
    const g = grid2(b);
    row(g, 'Name', txt(() => c.name, v => { const same = c.reference === c.name; c.name = v; if (same) c.reference = v; }, 39), 'Names must be unique for players to tell them apart; the reference is used in sentences ("the guard").');
    row(g, 'Reference', txt(() => c.reference, v => c.reference = v, 39));
    row(g, 'Description', txt(() => c.description, v => c.description = v, 199, true), 'What players read when they look at it.');
    const sp = document.createElement('div'); sp.className = 'ipick';
    const th = thumb(c.sprite + 8, 48);
    sp.append(num(() => c.sprite, v => { c.sprite = v; th.dataset.spr = v + 8; paintThumb(th); }, 0, 65535), th);
    row(g, 'Look (sprite base)', sp, 'Copy the number from another NPC to look like it.');
    row(g, 'Facing', faceRow(c.dir, v => c.dir = v));
    row(g, 'Alignment', num(() => c.alignment, v => c.alignment = v, -32768, 32767), 'Below 0: an enemy (players may attack it, it drops loot). Above 0: friendly.');
    const gold = document.createElement('div'); gold.className = 'ipick';
    gold.append(num(() => Math.floor(c.gold / 100), v => c.gold = v * 100 + c.gold % 100, 0), document.createTextNode(' gold '),
      num(() => c.gold % 100, v => c.gold = Math.floor(c.gold / 100) * 100 + v, 0, 99), document.createTextNode(' silver'));
    row(g, 'Money it carries', gold);
    row(g, 'Class', num(() => c.class, v => c.class = v), 'Monster class (some quests count kills of a class).');
    const g2 = grid2(b, 'Flags');
    row(g2, '', chks(NPC_FLAGS.map(([bt, l]) => chk(l, () => bit(c.flags, bt), on => c.flags = setBit(c.flags, bt, on)))));
  },
  stats(b, c) {
    const sc = document.createElement('div'); sc.className = 'ipick';
    const pct = num(() => 100, () => {}, 10, 400);
    const go = document.createElement('button'); go.className = 'sm'; go.textContent = 'Scale everything';
    go.onclick = () => {
      const p = +pct.value / 100, cl = (v, m) => Math.max(0, Math.min(m, Math.round(v * p)));
      for (let z = 0; z < 5; z++) { c.attrib[z * 6] = cl(c.attrib[z * 6], 250); c.attrib[z * 6 + 2] = Math.max(c.attrib[z * 6 + 2], c.attrib[z * 6]); }
      for (const k of ['hp', 'end', 'mana']) { c[k][0] = cl(c[k][0], 999); c[k][2] = Math.max(c[k][2], c[k][0]); }
      for (let z = 0; z < 50; z++) if (c.skill[z * 6]) { c.skill[z * 6] = cl(c.skill[z * 6], 250); c.skill[z * 6 + 2] = Math.max(c.skill[z * 6 + 2], c.skill[z * 6]); }
      tplRender(); toast('Scaled to ' + pct.value + '% (press Apply to keep it)');
    };
    sc.append(pct, document.createTextNode(' % '), go);
    const g = grid2(b);
    // rank: comes from the stats (the server works it out again at every respawn), so it is set by scaling them
    const rk = document.createElement('div'); rk.className = 'ipick';
    const now = npcPoints(c), cur = rankOf(now);
    const rs = sel(RANK_NAMES.map((n, i) => [i, `${i} · ${n}`]), () => cur, () => {});
    const go2 = document.createElement('button'); go2.className = 'sm'; go2.textContent = 'Scale to this rank';
    go2.onclick = () => {
      const want = +rs.value, lo = want ? RANK_PTS[want - 1] : 0, hi = want < RANK_PTS.length ? RANK_PTS[want] : Infinity;
      const base = JSON.parse(JSON.stringify({ attrib: c.attrib, hp: c.hp, end: c.end, mana: c.mana, skill: c.skill }));
      const scaled = f => {
        const t = JSON.parse(JSON.stringify(base)), cl = (v, m) => Math.max(0, Math.min(m, Math.round(v * f)));
        for (let z = 0; z < 5; z++) { t.attrib[z * 6] = Math.max(1, cl(base.attrib[z * 6], 250)); t.attrib[z * 6 + 2] = Math.max(t.attrib[z * 6 + 2], t.attrib[z * 6]); }
        for (const k of ['hp', 'end', 'mana']) { t[k][0] = cl(base[k][0], 999); t[k][2] = Math.max(t[k][2], t[k][0]); }
        for (let z = 0; z < 50; z++) if (base.skill[z * 6]) { t.skill[z * 6] = Math.max(1, cl(base.skill[z * 6], 250)); t.skill[z * 6 + 2] = Math.max(t.skill[z * 6 + 2], t.skill[z * 6]); }
        return t;
      };
      let a = 0.02, z = 40, best = null;                // the smallest scale that reaches the rank
      if (npcPoints(scaled(z)) < lo) return toast(`It can't reach ${RANK_NAMES[want]} by scaling (its stats hit the maximum). Give it more skills first.`, true);
      for (let k = 0; k < 40; k++) { const m = (a + z) / 2, p = npcPoints(scaled(m)); if (p >= lo) { z = m; best = m; } else a = m; }
      const t = scaled(best ?? z), p = npcPoints(t);
      if (p >= hi) return toast(`Its stats can't be scaled finely enough to land exactly on ${RANK_NAMES[want]} (it jumps to ${RANK_NAMES[rankOf(p)]}). Try the rank next to it, or change a few values by hand.`, true);
      Object.assign(c, t); tplRender();
      toast(`Now ${RANK_NAMES[rankOf(p)]} (${p.toLocaleString()} points, stats × ${(best ?? z).toFixed(2)}). Press Apply to keep it.`);
    };
    rk.append(rs, go2);
    row(g, 'Rank', rk, `Now ${RANK_NAMES[cur]} (${now.toLocaleString()} points). An NPC's rank comes from its stats; this scales them all until it is the rank you pick. It also sets the experience players get for killing it.`);
    row(g, 'Make it stronger or weaker', sc, 'Attributes, hit points, endurance, mana and skills together. 120 = 20% stronger.');
    const cols = document.createElement('div'); cols.className = 'cols'; b.append(cols);
    const t1 = document.createElement('table'); t1.className = 'st'; t1.innerHTML = '<tr><th>Attribute</th><th>Value</th></tr>';
    const put = (t, name, get, set, max) => { const r = t.insertRow(); r.insertCell().textContent = name; r.insertCell().append(num(get, set, 0, max)); };
    ATTRS.forEach((a, z) => put(t1, a, () => c.attrib[z * 6], v => { c.attrib[z * 6] = v; c.attrib[z * 6 + 2] = Math.max(c.attrib[z * 6 + 2], v); }, 250));
    put(t1, 'Hit points', () => c.hp[0], v => { c.hp[0] = v; c.hp[2] = Math.max(c.hp[2], v); }, 999);
    put(t1, 'Endurance', () => c.end[0], v => { c.end[0] = v; c.end[2] = Math.max(c.end[2], v); }, 999);
    put(t1, 'Mana', () => c.mana[0], v => { c.mana[0] = v; c.mana[2] = Math.max(c.mana[2], v); }, 999);
    const h = document.createElement('div');
    h.innerHTML = '<h4>Body</h4>'; h.append(t1);
    const t3 = document.createElement('table'); t3.className = 'st';
    put(t3, 'Weapon bonus', () => c.weapon_bonus, v => c.weapon_bonus = v, 255);
    put(t3, 'Armor bonus', () => c.armor_bonus, v => c.armor_bonus = v, 255);
    put(t3, 'Damage to attackers', () => c.gethit_dam, v => c.gethit_dam = v, 127);
    put(t3, 'Glows (light)', () => c.light_bonus, v => c.light_bonus = v, 255);
    const r = t3.insertRow(); r.insertCell().textContent = 'Speed'; r.insertCell().append(num(() => c.speed_mod, v => c.speed_mod = v, -128, 127));
    h.insertAdjacentHTML('beforeend', '<h4>Bonuses</h4>'); h.append(t3);
    cols.append(h);
    const t2 = document.createElement('table'); t2.className = 'st'; t2.innerHTML = '<tr><th>Skill</th><th>Value</th></tr>';
    SKILLS.forEach((s, z) => put(t2, s, () => c.skill[z * 6], v => { c.skill[z * 6] = v; c.skill[z * 6 + 2] = Math.max(c.skill[z * 6 + 2], v); }, 250));
    const h2 = document.createElement('div'); h2.innerHTML = '<h4>Skills (0 = doesn\'t have it)</h4>'; h2.append(t2); cols.append(h2);
    b.insertAdjacentHTML('beforeend', `<div class="note">Rank and the experience players get for killing it are worked out from these values: now ${npcPoints(c).toLocaleString()} points, ${RANK_NAMES[rankOf(npcPoints(c))]}.</div>`);
  },
  gear(b, c) {
    const g = grid2(b, 'Worn (it fights with these)');
    WEAR.forEach((w, i) => row(g, w, ipick(() => c.worn[i], v => c.worn[i] = v)));
    const g2 = grid2(b, bit(c.flags, 10) ? 'Backpack: what it sells (merchant)' : 'Backpack (dropped when it dies)');
    const free = c.item.findIndex(v => !v);
    for (let i = 0; i < 40; i++) {
      if (!c.item[i] && i !== free) continue;
      row(g2, c.item[i] ? 'Slot ' + (i + 1) : 'Add', ipick(() => c.item[i], v => { c.item[i] = v; tplRender(); }));
    }
    const g3 = grid2(b, 'In its hand');
    row(g3, 'Carried item', ipick(() => c.citem, v => c.citem = v), 'Rarely used.');
  },
  behave(b, c) {
    const d = c.data, g = grid2(b, 'Fighting');
    row(g, 'Takes part in fights', sel([[0, 'Stays out of fights'], [1, 'Defends good people'], [-1, 'Defends evil people']], () => d[24], v => d[24] = v));
    row(g, 'Attack distance', num(() => d[93], v => d[93] = v, 0, 100), 'Warns (Warning text), then attacks anyone who comes closer than this. 0 = off.');
    row(g, 'Keyword', sel([[0, 'Normal'], [1, 'Attacks unless the keyword is said'], [2, 'Only attacks near its resting spot']], () => d[95], v => d[95] = v), 'The keyword itself is on Talk & quest.');
    row(g, 'Group', num(() => d[42], v => d[42] = v), 'NPCs with the same group number belong together.');
    const ab = document.createElement('div'); ab.className = 'ipick';
    for (let i = 43; i <= 46; i++) ab.append(num(() => d[i], v => d[i] = v));
    row(g, 'Attacks everyone but groups', ab, 'If the first is set, it attacks every character not in one of these groups.');
    row(g, 'Helps group', num(() => d[59], v => d[59] = v), 'Comes to help members of this group.');
    row(g, 'Shouts for help, code', num(() => d[52], v => d[52] = v), 'When attacked; NPCs with the same "comes to help" code come running.');
    row(g, 'Comes to help, code', num(() => d[53], v => d[53] = v));
    const g2 = grid2(b, 'Moving around');
    row(g2, 'Random walk every', num(() => Math.round(d[60] / 18), v => d[60] = v * 18, 0), 'seconds (0 = stays put). A patrol route is on its own tab.');
    row(g2, 'Random walk at most', num(() => d[73], v => d[73] = v, 0), 'tiles from its resting spot (0 = no limit).');
    row(g2, 'Resting spot', document.createTextNode(d[29] ? pos(d[29]).join(', ') : '— (set when it is placed)'), 'Where it goes back to. Move the NPC on the map to change it.');
    const g3 = grid2(b, 'Other');
    row(g3, 'Greets players', chk('Says its greeting to players who come close', () => !!d[37], on => d[37] = on ? 1 : 0));
    row(g3, 'Light', sel([[0, 'Never'], [1, 'Lights a torch when dark'], [2, 'When dark and not resting'], [3, 'When dark and fighting']], () => d[62], v => d[62] = v));
    row(g3, 'Picks up trash', num(() => d[47], v => d[47] = v), '1 = picks up and destroys garbage lying around.');
    row(g3, 'Disappears after', num(() => d[64], v => d[64] = v, 0), 'ticks (18 per second; 0 = never). For summons.');
  },
  patrol(b, c) {
    const d = c.data;
    b.insertAdjacentHTML('beforeend', '<div class="note">It walks from stop to stop and then starts again at the first one. Up to 9 stops. Leave it empty for an NPC that stays at its resting spot. A stop counts as reached within 4 tiles, so space them out. Like every NPC, it only moves while a player is near (or with "Never sleeps").</div>');
    const box = document.createElement('div'); b.append(box);
    const stops = []; for (let i = 10; i <= 18; i++) if (d[i]) stops.push(pos(d[i]));
    const save = () => { for (let i = 0; i < 9; i++) d[10 + i] = stops[i] ? stops[i][0] + stops[i][1] * 1024 : 0; };
    stops.forEach((p, i) => {
      const r = document.createElement('div'); r.className = 'stop';
      r.innerHTML = `<b style="color:var(--gold2)">${i + 1}</b>`;
      r.append(num(() => p[0], v => { p[0] = v; save(); }, 0, 1023), num(() => p[1], v => { p[1] = v; save(); }, 0, 1023));
      const a = document.createElement('div'); a.className = 'ipick';
      const mk = (t, f) => { const x = document.createElement('button'); x.className = 'sm'; x.textContent = t; x.onclick = f; a.append(x); };
      mk('Pick on map', () => pickSpot(`Click stop ${i + 1}`, t => { p[0] = t.x; p[1] = t.y; save(); }));
      if (i > 0) mk('↑', () => { [stops[i - 1], stops[i]] = [stops[i], stops[i - 1]]; save(); tplRender(); });
      mk('Remove', () => { stops.splice(i, 1); save(); tplRender(); });
      r.append(a); box.append(r);
    });
    if (stops.length < 9) {
      const add = document.createElement('button'); add.className = 'btn sec'; add.textContent = '+ Add a stop (pick on map)';
      add.onclick = () => pickSpot(`Click stop ${stops.length + 1}`, t => { stops.push([t.x, t.y]); save(); });
      b.append(add);
    }
    const g = grid2(b, 'Timing');
    row(g, 'Waits at each stop', num(() => Math.round(d[79] / 18), v => d[79] = v * 18, 0), 'seconds');
  },
  talk(b, c) {
    const g = grid2(b, 'What it says');
    b.insertAdjacentHTML('afterbegin', '<div class="note">Write <b>%s</b> where the player\'s name goes. Its own answers to what players say, and quest steps, are on the <b>Conversations</b> tab.</div>');
    CTEXT.forEach(([i, l, h]) => row(g, l, txt(() => c.text[i], v => c.text[i] = v, 159), h));
    row(g, 'Dying words chance', num(() => c.data[48], v => c.data[48] = v, 0, 100), '% chance it says its dying words.');
    const g2 = grid2(b, 'Knowledge (answers to players\' questions)');
    row(g2, 'Knows about', sel(AREAS, () => c.data[72], v => c.data[72] = v), 'Which part of the world it can tell players about (the game\'s built-in answers).');
    row(g2, 'How much it knows', num(() => c.data[68], v => c.data[68] = v, 0), 'Higher answers harder questions.');
    row(g2, 'Talkativity', num(() => c.data[71], v => c.data[71] = v, 0));
    const g3 = grid2(b, 'Quest: bring me an item');
    row(g3, 'Wants', ipick(() => c.data[49], v => c.data[49] = v, { none: 'nothing' }), 'When a player gives it this item, it thanks them and gives the rewards below.');
    row(g3, 'Teaches the skill', sel([[0, 'nothing'], ...SKILLS.map((s, i) => [i, s])], () => c.data[50], v => c.data[50] = v));
    row(g3, 'and gives experience', num(() => c.data[51], v => c.data[51] = v, 0), 'only together with a skill');
    row(g3, 'Gives back the item', ipick(() => c.data[66], v => c.data[66] = v, { none: 'nothing' }));
  },
  conv(b, c) {
    const T = TP.talk, E = T.entries, Q = T.quests, S = T.steps, isUse = TP.kind === 'use';
    if (isUse) b.insertAdjacentHTML('beforeend', `<div class="note">What happens when a player uses this item (a portal, door, lever, chest…). The first rule whose conditions fit the player is used,
      and it <b>replaces</b> what the item normally does, unless it has the action "then the item works as usual". If no rule fits, the item works as usual.
      Example for a portal: "quest 3 is at least 5 → send the player to the lair", then "always → tell: The portal is dark."
      Try it in the server console: <span class="mono">talkuse &lt;player&gt; ${TP.x} ${TP.y}</span>. The rules belong to the tile, so they stay if you replace the item there.</div>`);
    else b.insertAdjacentHTML('beforeend', `<div class="note">What happens when a player talks to it, hands it an item, or kills something for its quests.
      For each player the first line whose trigger and conditions fit is used, so put special cases above general ones.
      <b>%s</b> = the player's name, <b>{q2}</b> = how far they are in quest 2. Quests are numbered 1-255; every player starts each at step 0, and all NPCs share them, so a quest chain can lead from one NPC to the next.
      Try it without logging in, in the server console: <span class="mono">talktest ${TP.t} &lt;player&gt; &lt;what they say&gt;</span> · <span class="mono">talkkill &lt;player&gt; &lt;template&gt;</span> · <span class="mono">quest &lt;player&gt;</span>.</div>`);
    const qopts = (cur) => {   // the named quests, a few free numbers after them, and the one in use
      const named = Object.keys(Q).map(Number).filter(n => Q[n]), top = Math.max(0, ...named);
      const ns = new Set([...named, ...Array.from({ length: 5 }, (_, i) => top + 1 + i)].filter(n => n >= 1 && n <= 255));
      for (const e2 of E) { for (const x of e2.conds) if (x.n) ns.add(+x.n); for (const x of e2.acts) if (x.n) ns.add(+x.n); }
      return [...ns].sort((a, b2) => a - b2).map(n => [n, Q[n] ? `${n} · ${Q[n]}` : `${n} · (unnamed)`]);
    };
    const OPN = [['=', 'is'], ['!=', 'is not'], ['<', 'is below'], ['>', 'is above'], ['<=', 'is at most'], ['>=', 'is at least']];
    const selS = (opts, get, set) => { const s = document.createElement('select'); s.innerHTML = opts.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join(''); s.value = get(); s.onchange = () => set(s.value); return s; };
    const line = (items) => { const d = document.createElement('div'); d.className = 'ipick'; d.style.margin = '4px 0'; items.forEach(i => d.append(typeof i === 'string' ? document.createTextNode(i) : i)); return d; };
    const xb = (f) => { const x = document.createElement('button'); x.className = 'sm'; x.textContent = '×'; x.onclick = () => { f(); tplRender(); }; return x; };
    const areaIn = (get, set) => { const i = txt(get, set, 60); i.setAttribute('list', 'areanames'); i.placeholder = 'part of an area name, e.g. Kwai'; i.style.width = '260px'; return i; };
    if (!$('#areanames')) { const dl = document.createElement('datalist'); dl.id = 'areanames'; dl.innerHTML = [...new Set(info.areas.map(a => a[4]))].sort().map(n => `<option value="${esc(n)}">`).join(''); document.body.append(dl); }
    const npcPick = (anchor, done) => {   // choose an NPC (fills its name)
      const p = $('#ipop'), r = anchor.getBoundingClientRect();
      p.style.display = 'flex'; p.style.left = Math.min(window.innerWidth - 350, r.left) + 'px'; p.style.top = Math.min(window.innerHeight - 390, r.bottom + 4) + 'px';
      const q = p.querySelector('input'), lst = p.querySelector('.lst'); q.value = ''; q.placeholder = 'Search an NPC by name or number';
      const fillL = () => {
        const s = q.value.trim().toLowerCase(), seen = new Set();
        const items = (pal.npcs || []).filter(t => (!s || t[1].toLowerCase().includes(s) || String(t[0]) === s) && !seen.has(t[1]) && seen.add(t[1])).slice(0, 80);
        lst.innerHTML = '';
        for (const t of items) {
          const e = document.createElement('div'); e.className = 'r'; e.append(thumb(t[2], 26));
          const a = document.createElement('span'); a.textContent = t[1]; e.append(a);
          const n2 = document.createElement('span'); n2.className = 'n'; n2.textContent = t[3]; e.append(n2);
          e.onmousedown = ev => { ev.preventDefault(); p.style.display = 'none'; done(t); };
          lst.append(e);
        }
      };
      q.oninput = fillL; fillL(); setTimeout(() => q.focus(), 0);
    };
    E.forEach((e, k) => {
      const card = document.createElement('div'); card.className = 'note'; card.style.cssText = 'margin:12px 0;color:var(--text)';
      const hd = document.createElement('div'); hd.className = 'ipick'; hd.innerHTML = `<b style="color:var(--gold2)">${k + 1}.</b>`;
      if (isUse) { e.when = 'use'; hd.insertAdjacentHTML('beforeend', '<span style="flex:1">When a player uses it</span>'); }
      else hd.append(selS([['say', 'When the player says'], ['near', 'When a player comes close'], ['give', 'When the player gives it'], ['money', 'When the player gives money'], ['kill', 'When the player kills']], () => e.when, v => { e.when = v; if (v === 'money' && !e.item) e.item = 100; tplRender(); }));
      if (e.when === 'say') { const w = txt(() => e.words, v => e.words = v, 200); w.placeholder = 'ring*   or   hello|hi'; w.style.flex = '1'; hd.append(w); }
      else if (e.when === 'kill') {
        const w = txt(() => e.words, v => e.words = v, 200); w.placeholder = 'NPC name (Spider*, Ghost|Skeleton) or #123,124'; w.style.flex = '1'; hd.append(w);
        const pk = document.createElement('button'); pk.className = 'sm'; pk.textContent = 'Pick NPC…'; pk.onclick = () => npcPick(pk, t => { e.words = e.words && !e.words.startsWith('#') ? e.words + '|' + t[1] : t[1]; tplRender(); }); hd.append(pk);
      }
      else if (e.when === 'money') { hd.append(' at least ', num(() => e.item || 1, v => e.item = v, 1), ' silver (100 = 1 gold)'); }
      else if (e.when === 'near') hd.insertAdjacentHTML('beforeend', '<span class="hint" style="flex:1">once per player, at most every 30 seconds</span>');
      else if (!isUse) hd.append(ipick(() => e.item, v => e.item = v));
      const sp = document.createElement('span'); sp.style.flex = e.when === 'give' ? '1' : '0'; hd.append(sp);
      const mk = (t, f, tip) => { const x = document.createElement('button'); x.className = 'sm'; x.textContent = t; x.title = tip || ''; x.onclick = () => { f(); tplRender(); }; hd.append(x); };
      if (k > 0) mk('↑', () => { [E[k - 1], E[k]] = [E[k], E[k - 1]]; }, 'Move up (checked earlier)');
      if (k < E.length - 1) mk('↓', () => { [E[k + 1], E[k]] = [E[k], E[k + 1]]; }, 'Move down');
      mk('Copy', () => E.splice(k + 1, 0, JSON.parse(JSON.stringify(e))), 'Duplicate this line');
      mk('Delete', () => { if (confirm('Delete this line?')) E.splice(k, 1); });
      card.append(hd);
      if (e.when === 'say') card.insertAdjacentHTML('beforeend', '<div class="hint">Every word must be in what they say. a|b = either word, ring* = ring, rings, ringmaster…</div>');
      if (e.when === 'near') card.insertAdjacentHTML('beforeend', '<div class="hint">Replaces its normal greeting when the conditions fit (Apply turns on "Greets players" for it). If no line fits, it says its normal greeting.</div>');
      if (e.when === 'money') card.insertAdjacentHTML('beforeend', '<div class="hint">Players hand money over by holding gold on the mouse and giving it to the NPC. With a line that fits, it keeps the money; otherwise it gives it back. Put bigger amounts above smaller ones.</div>');
      if (e.when === 'kill') card.insertAdjacentHTML('beforeend', '<div class="hint">Counts for the player who kills it (or whose companion does) and their group members who can see them, each only if the conditions fit them. Use a quest step as the condition so it only counts while that quest is active.</div>');
      const h = (t) => { const d = document.createElement('div'); d.className = 'lb'; d.style.cssText = 'margin-top:10px;color:var(--dim)'; d.textContent = t; card.append(d); };
      h('Only if');
      e.conds.forEach((cd, i) => {
        const ty = selS([['quest', 'quest step'], ['has', 'the player carries'], ['hasnot', 'the player does not carry'], ['rank', 'the player\'s rank'], ['skill', 'the player\'s skill'], ['gold', 'the player\'s money (silver)'], ['area', e.when === 'kill' ? 'it dies in the area' : 'the player is in the area']], () => cd.type,
          v => { e.conds[i] = v === 'quest' ? { type: v, n: 1, op: '=', v: 0 } : v === 'rank' ? { type: v, op: '<=', v: 1 } : v === 'skill' ? { type: v, n: 12, op: '>', v: 0 } : v === 'gold' ? { type: v, op: '>=', v: 100 } : v === 'area' ? { type: v, s: '' } : { type: v, t: 0 }; tplRender(); });
        const parts = [ty];
        if (cd.type === 'quest') parts.push(sel(qopts(), () => cd.n, v => cd.n = v), selS(OPN, () => cd.op, v => cd.op = v), num(() => cd.v, v => cd.v = v, 0, 65535));
        else if (cd.type === 'rank') { parts.push(selS(OPN, () => cd.op, v => cd.op = v), sel(RANK_NAMES.map((n2, i2) => [i2, `${i2} · ${n2}`]), () => cd.v, v => cd.v = v)); }
        else if (cd.type === 'skill') parts.push(sel(SKILLS.map((s2, i2) => [i2, s2]), () => cd.n, v => cd.n = v), selS(OPN, () => cd.op, v => cd.op = v), num(() => cd.v, v => cd.v = v, 0, 255), '(0 = doesn\'t know it)');
        else if (cd.type === 'gold') parts.push(selS(OPN, () => cd.op, v => cd.op = v), num(() => cd.v, v => cd.v = v, 0));
        else if (cd.type === 'area') parts.push(areaIn(() => cd.s, v => cd.s = v));
        else parts.push(ipick(() => cd.t, v => cd.t = v));
        parts.push(xb(() => e.conds.splice(i, 1)));
        card.append(line(parts));
      });
      if (!e.conds.length) card.insertAdjacentHTML('beforeend', '<div class="hint">always</div>');
      const ac = document.createElement('button'); ac.className = 'sm'; ac.textContent = '+ condition'; ac.onclick = () => { e.conds.push({ type: 'quest', n: 1, op: '=', v: 0 }); tplRender(); }; card.append(ac);
      h(e.when === 'kill' || isUse ? 'Message to the player (each line in turn)' : 'It answers aloud (each line is said in turn)');
      const ta = txt(() => e.answers.join('\n'), v => e.answers = v.split('\n'), 4000, true); ta.style.height = '64px'; card.append(ta);
      h('Then');
      e.acts.forEach((a, i) => {
        const ty = selS([['set', 'set quest step'], ['add', 'add to quest step'], ['item', 'give an item'], ['exp', 'give experience'], ['gold', 'give money (silver)'],
          ['luck', 'give luck'], ['skill', 'teach a skill'], ['take', 'take an item from the player'], ['keep', 'keep the item they gave'],
          ['takegold', 'take money from the player'], ['cast', 'cast a spell on the player'],
          ['tell', 'tell the player'], ['announce', 'announce to everyone'], ['teleport', 'send the player to'], ['pass', 'then the item works as usual']],
          () => a.type, v => { e.acts[i] = v === 'set' || v === 'add' ? { type: v, n: 1, v: 1 } : v === 'keep' || v === 'pass' ? { type: v } : v === 'tell' || v === 'announce' ? { type: v, s: '' } : v === 'teleport' ? { type: v, x: 512, y: 512 } : v === 'cast' ? { type: v, s: 'bless', v: 30 } : { type: v, v: 0 }; tplRender(); });
        const parts = [ty];
        if (a.type === 'set' || a.type === 'add') parts.push(sel(qopts(), () => a.n, v => a.n = v), a.type === 'set' ? ' to ' : ' + ', num(() => a.v, v => a.v = v, a.type === 'add' ? -65535 : 0, 65535));
        else if (a.type === 'item' || a.type === 'take') parts.push(ipick(() => a.v, v => a.v = v));
        else if (a.type === 'exp' || a.type === 'gold' || a.type === 'luck' || a.type === 'takegold') parts.push(num(() => a.v, v => a.v = v, a.type === 'luck' ? -1000 : 0), a.type === 'gold' || a.type === 'takegold' ? ' silver' : '');
        else if (a.type === 'cast') parts.push(selS([['bless', 'Bless'], ['protect', 'Protect'], ['enhance', 'Enhance Weapon'], ['mshield', 'Magic Shield'], ['light', 'Light'], ['heal', 'Heal']], () => a.s, v => a.s = v),
          ' power ', num(() => a.v, v => a.v = v, 1, 500), '(the game lowers it to what the player can take)');
        else if (a.type === 'skill') parts.push(sel(SKILLS.map((s2, i2) => [i2, s2]), () => a.v, v => a.v = v));
        else if (a.type === 'tell' || a.type === 'announce') { const t2 = txt(() => a.s, v => a.s = v, 300); t2.style.flex = '1'; t2.placeholder = a.type === 'announce' ? '%s has slain Argha the Thief!' : 'only the player sees this'; parts.push(t2); }
        else if (a.type === 'teleport') {
          parts.push(num(() => a.x, v => a.x = v, 1, 1022), num(() => a.y, v => a.y = v, 1, 1022));
          const pk = document.createElement('button'); pk.className = 'sm'; pk.textContent = 'Pick on map';
          pk.onclick = () => pickSpot('Click where the player should be sent', t => { a.x = t.x; a.y = t.y; }); parts.push(pk);
        }
        parts.push(xb(() => e.acts.splice(i, 1)));
        card.append(line(parts));
      });
      const aa = document.createElement('button'); aa.className = 'sm'; aa.textContent = '+ action'; aa.onclick = () => { e.acts.push({ type: 'set', n: 1, v: 1 }); tplRender(); }; card.append(aa);
      if (e.when === 'give' && !e.acts.some(a => a.type === 'keep')) card.insertAdjacentHTML('beforeend', '<div class="hint">It hands the item back unless "keep the item they gave" is among the actions.</div>');
      b.append(card);
    });
    const bar = document.createElement('div'); bar.className = 'ipick'; bar.style.gap = '10px';
    const add = document.createElement('button'); add.className = 'btn sec'; add.textContent = '+ Add a line';
    add.onclick = () => { E.push({ when: isUse ? 'use' : 'say', words: '', item: 0, conds: [], answers: [''], acts: [] }); tplRender(); };
    const kc = document.createElement('button'); kc.className = 'btn sec'; kc.textContent = '+ Kill counter…'; kc.title = '"Kill 5 spiders in Kwai Hall": makes the two lines that count the kills';
    bar.append(add); if (!isUse) bar.append(kc); b.append(bar);
    // the kill counter helper
    const kbox = document.createElement('div'); kbox.className = 'note'; kbox.style.display = 'none'; b.append(kbox);
    kc.onclick = () => {
      kbox.style.display = kbox.style.display === 'none' ? '' : 'none'; if (kbox.style.display === 'none') return;
      const K = { name: '', area: '', count: 5, quest: 1, step: 1, counter: 2, next: 2 };
      kbox.innerHTML = '<b style="color:var(--gold2)">Kill counter</b> · counts kills while a quest is at a step, then moves the quest on<div class="grid2" style="margin-top:8px"></div>';
      const g2 = kbox.querySelector('.grid2');
      const nm = txt(() => K.name, v => K.name = v, 200); nm.placeholder = 'Spider*  or  Ghost|Skeleton';
      const pk = document.createElement('button'); pk.className = 'sm'; pk.textContent = 'Pick NPC…'; pk.onclick = () => npcPick(pk, t => { K.name = K.name ? K.name + '|' + t[1] : t[1]; nm.value = K.name; });
      row(g2, 'Kill', line([nm, pk]));
      row(g2, 'In the area (optional)', areaIn(() => K.area, v => K.area = v));
      row(g2, 'How many', num(() => K.count, v => K.count = v, 1, 1000));
      row(g2, 'While quest', line([sel(qopts(), () => K.quest, v => K.quest = v), ' is at step ', num(() => K.step, v => K.step = v, 0, 65535)]));
      row(g2, 'Count them in quest', sel(qopts(), () => K.counter, v => K.counter = v), 'A quest number of its own, used only as the counter (shown with {q' + 'N} in messages).');
      row(g2, 'Then set the quest to step', num(() => K.next, v => K.next = v, 0, 65535), 'Reward the player when they come back: a line for that step.');
      const go = document.createElement('button'); go.className = 'btn pri'; go.textContent = 'Add the two lines';
      go.onclick = () => {
        if (!K.name.trim()) return toast('Which NPC should be killed?', true);
        if (K.counter === K.quest) return toast('The counter needs a quest number of its own.', true);
        const conds = [{ type: 'quest', n: K.quest, op: '=', v: K.step }]; if (K.area.trim()) conds.push({ type: 'area', s: K.area.trim() });
        const what = K.name.split('|')[0].replace('*', '');
        E.push({ when: 'kill', words: K.name, item: 0, conds: [...conds, { type: 'quest', n: K.counter, op: '>=', v: K.count - 1 }], answers: [`${what}: ${K.count}/${K.count}. Done! Return to ${c.name}.`],
          acts: [{ type: 'set', n: K.counter, v: K.count }, { type: 'set', n: K.quest, v: K.next }] });
        E.push({ when: 'kill', words: K.name, item: 0, conds: JSON.parse(JSON.stringify(conds)), answers: [`${what}: {q${K.counter}}/${K.count}`], acts: [{ type: 'add', n: K.counter, v: 1 }] });
        if (!Q[K.counter]) Q[K.counter] = (Q[K.quest] || 'Quest ' + K.quest) + ' (count)';
        tplRender(); toast('Added: the last kill (above) and the counting line (below). Press Apply to keep them.');
      };
      kbox.append(go);
    };
    // quest names and journal steps
    const h4 = document.createElement('h4'); h4.textContent = 'Quests (shared by all NPCs) · the player sees the step texts with #journal'; b.append(h4);
    const shown = new Set(Object.keys(Q).map(Number).filter(n => Q[n]).concat(Object.keys(S).map(Number).filter(n => S[n] && S[n].length)));
    shown.add(Math.max(0, ...shown) + 1);
    for (const i of [...shown].sort((a, b2) => a - b2)) {
      if (i < 1 || i > 255) continue;
      const box = document.createElement('div'); box.className = 'note'; box.style.margin = '6px 0';
      const nmI = txt(() => Q[i] || '', v => { if (v.trim()) Q[i] = v; else delete Q[i]; }, 59); nmI.placeholder = 'name, e.g. The lost ring'; nmI.style.flex = '1';
      box.append(line([`Quest ${i} `, nmI]));
      (S[i] || []).forEach((st, j) => {
        const tx = txt(() => st[1], v => st[1] = v, 300); tx.style.flex = '1'; tx.placeholder = 'what the journal says at this step';
        box.append(line(['  step ', num(() => st[0], v => st[0] = v, 0, 65535), tx, xb(() => S[i].splice(j, 1))]));
      });
      const as = document.createElement('button'); as.className = 'sm'; as.textContent = '+ journal step';
      as.onclick = () => { (S[i] = S[i] || []).push([(S[i] && S[i].length ? Math.max(...S[i].map(x => x[0])) : 0) + 1, '']); tplRender(); };
      box.append(as); b.append(box);
    }
  },
  adv(b, c) {
    b.insertAdjacentHTML('beforeend', '<div class="note">Every driver value of the template. The other tabs set the usual ones; these are for special NPCs (data 0-9 depend on the special driver).</div>');
    const g = document.createElement('div'); g.className = 'dgrid'; b.append(g);
    for (let i = 0; i < 100; i++) {
      if (i === 99) continue;
      const l = document.createElement('label'); l.innerHTML = `<span>${i} · ${esc(DATA_NAMES[i] || '')}</span>`;
      l.append(num(() => c.data[i], v => c.data[i] = v)); g.append(l);
    }
  },
};

// ---- item tabs
const ITEM_TABS = {
  general(b, c) {
    const g = grid2(b);
    row(g, 'Name', txt(() => c.name, v => { const same = c.reference === c.name.toLowerCase(); c.name = v; if (same) c.reference = v.toLowerCase(); }, 39));
    row(g, 'Reference', txt(() => c.reference, v => c.reference = v, 39), 'Used in sentences ("a pair of boots").');
    row(g, 'Description', txt(() => c.description, v => c.description = v, 199, true), 'What players read when they look at it.');
    for (const k of [0, 1]) {
      const sp = document.createElement('div'); sp.className = 'ipick'; const th = thumb(c.sprite[k], 48);
      sp.append(num(() => c.sprite[k], v => { c.sprite[k] = v; th.dataset.spr = v; paintThumb(th); }, -32768, 32767), th);
      row(g, k ? 'Look when on/active' : 'Look', sp, k ? 'For doors, torches and the like (0 = same).' : '');
    }
    const val = document.createElement('div'); val.className = 'ipick';
    val.append(num(() => Math.floor(c.value / 100), v => c.value = v * 100 + c.value % 100, 0), document.createTextNode(' gold '),
      num(() => c.value % 100, v => c.value = Math.floor(c.value / 100) * 100 + v, 0, 99), document.createTextNode(' silver'));
    row(g, 'Value', val, 'What merchants pay for it.');
    row(g, 'Min. rank to wear', num(() => c.min_rank, v => c.min_rank = v, 0, 127));
    row(g, 'Driver', num(() => c.driver, v => c.driver = v, 0, 255), 'The special code it runs when used (6 = portal, 1 = door, …). Its values are on Advanced.');
    for (const [title, fl] of ITEM_FLAGS) { const g2 = grid2(b, title); row(g2, '', chks(fl.map(([bt, l]) => chk(l, () => bit(c.flags, bt), on => c.flags = setBit(c.flags, bt, on))))); }
    const g3 = grid2(b, 'Worn on');
    row(g3, '', chks(PLACES.map(([v, l]) => chk(l, () => !!(c.placement & v), on => c.placement = on ? c.placement | v : c.placement & ~v))));
  },
  stats(b, c) {
    b.insertAdjacentHTML('beforeend', '<div class="note"><b>When worn</b> adds to the player while worn (or a spell while it lasts), <b>When active</b> while it is turned on, <b>Needed</b> is what the player must have to wear or use it.</div>');
    const cols = document.createElement('div'); cols.className = 'cols'; b.append(cols);
    const mk = () => { const t = document.createElement('table'); t.className = 'st'; t.innerHTML = '<tr><th></th><th>When worn</th><th>When active</th><th>Needed</th></tr>'; return t; };
    const put3 = (t, name, arr, base, lo, hi) => { const r = t.insertRow(); r.insertCell().textContent = name; for (let k = 0; k < 3; k++) r.insertCell().append(num(() => arr[base + k], v => arr[base + k] = v, lo, hi)); };
    const t1 = mk();
    ATTRS.forEach((a, z) => put3(t1, a, c.attrib, z * 3, -128, 127));
    put3(t1, 'Hit points', c.hp, 0, -32768, 32767); put3(t1, 'Endurance', c.end, 0, -32768, 32767); put3(t1, 'Mana', c.mana, 0, -32768, 32767);
    const t3 = document.createElement('table'); t3.className = 'st'; t3.innerHTML = '<tr><th></th><th>Normal</th><th>Active</th></tr>';
    const put2 = (name, arr, lo, hi) => { const r = t3.insertRow(); r.insertCell().textContent = name; for (let k = 0; k < 2; k++) r.insertCell().append(num(() => arr[k], v => arr[k] = v, lo, hi)); };
    put2('Armor value', c.armor, -128, 127); put2('Weapon value', c.weapon, -128, 127); put2('Light', c.light, -32768, 32767); put2('Damage to attackers', c.gethit_dam, -128, 127);
    const h = document.createElement('div'); h.innerHTML = '<h4>Attributes</h4>'; h.append(t1); h.insertAdjacentHTML('beforeend', '<h4>Armor, weapon, light</h4>'); h.append(t3); cols.append(h);
    const t2 = mk(); SKILLS.forEach((s, z) => put3(t2, s, c.skill, z * 3, -128, 127));
    const h2 = document.createElement('div'); h2.innerHTML = '<h4>Skills</h4>'; h2.append(t2); cols.append(h2);
  },
  adv(b, c) {
    const g = grid2(b);
    row(g, 'Lasts (inactive)', num(() => c.max_age[0], v => c.max_age[0] = v, 0), 'ticks before it decays (18 per second; 0 = forever)');
    row(g, 'Lasts (active)', num(() => c.max_age[1], v => c.max_age[1] = v, 0));
    row(g, 'Max damage', num(() => c.max_damage, v => c.max_damage = v, 0), 'how much it can take before it breaks (0 = never)');
    row(g, 'Duration', num(() => c.duration, v => c.duration = v, 0), 'of a spell or an effect');
    row(g, 'Cost', num(() => c.cost, v => c.cost = v, 0)); row(g, 'Power', num(() => c.power, v => c.power = v, 0));
    row(g, 'Changes the player\'s look', num(() => c.sprite_override, v => c.sprite_override = v, 0, 65535), 'sprite (potions, costumes)');
    row(g, 'Animation', (() => { const d = document.createElement('div'); d.className = 'ipick'; d.append(num(() => c.status[0], v => c.status[0] = v, 0, 255), num(() => c.status[1], v => c.status[1] = v, 0, 255)); return d; })(), '0/1 still, 16 = 4-frame loop …');
    const h = document.createElement('h4'); h.textContent = `Driver values (driver ${c.driver})`; b.append(h);
    const dg = document.createElement('div'); dg.className = 'dgrid'; b.append(dg);
    for (let i = 0; i < 10; i++) { const l = document.createElement('label'); l.innerHTML = `<span>data ${i}${c.driver === 6 && i < 2 ? (i ? ' · portal y' : ' · portal x') : ''}</span>`; l.append(num(() => c.data[i], v => c.data[i] = v)); dg.append(l); }
  },
};

// ---------------------------------------------------------------- player characters
const PFLAGS = [[11, 'Staff'], [23, 'Imp (can impersonate monsters)'], [1, 'God'], [45, 'Greater god'], [2, 'Creator (#build)'], [0, 'Immortal'],
  [9, 'No shout'], [8, 'No tell'], [24, 'Muted until tomorrow'], [25, "Can't change description"], [40, 'Golden list'], [41, 'Black list'], [30, 'Hidden in #who']];
const fmtDate = t => t ? new Date(t * 1000).toLocaleString() : '–';
const fmtDur = ticks => { const s = Math.floor(ticks / 18), h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60); return h ? `${h} h ${m} min` : `${m} min`; };
async function openPlayer(c) {
  if (tplDirty() && !(TP.kind === 'player' && TP.t === c) && !confirm('You have changes here you did not apply. Leave them?')) return;
  const r = await api('/api/pchar?c=' + c);
  if (r.error) return toast(r.error, true);
  TP = { kind: 'player', t: c, orig: JSON.parse(JSON.stringify(r)), cur: r, tab: TP && TP.kind === 'player' ? TP.tab : 'overview', hist: null };
  $('#tpl').classList.add('on'); $('#tpl').classList.remove('picking'); tplRender();
}
async function playerItem(op) {    // add or remove an item right away, keep the other unapplied changes
  await edit([op], (op.op === 'padditem' ? 'gave ' : 'took an item from ') + TP.cur.name);
  const r = await api('/api/pchar?c=' + TP.t);
  if (r.error) return toast(r.error, true);
  for (const k of ['items', 'item', 'worn', 'depot', 'citem']) { TP.cur[k] = r[k]; TP.orig[k] = JSON.parse(JSON.stringify(r[k])); }
  tplRender();
}
const PLAYER_TABS = {
  overview(b, c) {
    if (c.online) b.insertAdjacentHTML('beforeend', '<div class="note"><b style="color:var(--ok)">Online now.</b> Changes go into the game as soon as you apply them (the server works out their values again and updates their screen).</div>');
    const g = grid2(b);
    row(g, 'Name', document.createTextNode(c.name), 'Player names are not changed here.');
    row(g, 'Description', txt(() => c.description, v => c.description = v, 199, true));
    const ex = document.createElement('div'); ex.className = 'ipick';
    const rk = document.createElement('span'); rk.className = 'hint';
    const showRank = () => { let i = 0; for (const p of [50, 850, 4900, 17700, 48950, 113750, 233800, 438600, 766650, 1266650, 1998700, 3035500, 4463550, 6384350, 8915600, 12192400, 16368450, 21617250, 28133300, 36133300, 49014500, 63000600, 80977100]) if (c.points_tot >= p) i++; rk.textContent = ' → ' + ['Private', 'Private First Class', 'Lance Corporal', 'Corporal', 'Sergeant', 'Staff Sergeant', 'Master Sergeant', 'First Sergeant', 'Sergeant Major', 'Second Lieutenant', 'First Lieutenant', 'Captain', 'Major', 'Lieutenant Colonel', 'Colonel', 'Brigadier General', 'Major General', 'Lieutenant General', 'General', 'Field Marshal', 'Knight of Astonia', 'Baron of Astonia', 'Earl of Astonia', 'Warlord of Astonia'][i]; };
    const tot = num(() => c.points_tot, v => { c.points += v - c.points_tot; c.points_tot = v; showRank(); un.value = c.points; }, 0);
    tot.style.width = '130px'; ex.append(tot, rk); showRank();
    row(g, 'Experience (total)', ex, 'Sets the rank. Changing it changes the unspent experience by the same amount.');
    const un = num(() => c.points, v => c.points = v, 0); un.style.width = '130px';
    row(g, 'Unspent experience', un, 'What they can still spend on attributes and skills.');
    const money = (get, set) => { const d = document.createElement('div'); d.className = 'ipick'; d.append(num(() => Math.floor(get() / 100), v => set(v * 100 + get() % 100), 0), ' gold ', num(() => get() % 100, v => set(Math.floor(get() / 100) * 100 + v), 0, 99), ' silver'); return d; };
    row(g, 'Money carried', money(() => c.gold, v => c.gold = v));
    row(g, 'Bank', money(() => c.bank, v => c.bank = v), 'Pays the depot rent.');
    row(g, 'Luck', num(() => c.luck, v => c.luck = v, -100000, 100000));
    const tp = document.createElement('div'); tp.className = 'ipick';
    tp.append(num(() => c.temple_x, v => c.temple_x = v, 0, 1023), num(() => c.temple_y, v => c.temple_y = v, 0, 1023));
    const pk = document.createElement('button'); pk.className = 'sm'; pk.textContent = 'Pick on map'; pk.onclick = () => pickSpot('Click their new recall / respawn point', t => { c.temple_x = t.x; c.temple_y = t.y; }); tp.append(pk);
    row(g, 'Recall point (temple)', tp, 'Where #recall and dying take them.');
    const px = c.online ? c.x : c.tavern_x, py = c.online ? c.y : c.tavern_y;
    const ps = document.createElement('div'); ps.className = 'ipick'; ps.append(`${px}, ${py} `);
    const gt = document.createElement('button'); gt.className = 'sm'; gt.textContent = 'Show on map'; gt.onclick = () => { closeTemplate(); centerOn(px, py); selectTile(px, py); }; ps.append(gt);
    row(g, c.online ? 'Standing at' : 'Comes back at', ps, c.online ? '' : 'Where they appear when they log in next.');
    const qs = Object.entries(c.quests || {});
    const g2 = grid2(b, 'Quest steps');
    row(g2, '', document.createTextNode(qs.length ? qs.map(([n, v]) => `quest ${n} = ${v}`).join(' · ') : 'none'), 'Change them in the server console: quest ' + c.name + ' <n> <value>');
  },
  stats(b, c) {
    b.insertAdjacentHTML('beforeend', '<div class="note"><b>Value</b> is what they have; <b>Max</b> is the most their class can reach. Only skills their class can learn (Max above 0) are listed, plus any they have.</div>');
    const cols = document.createElement('div'); cols.className = 'cols'; b.append(cols);
    const mk = () => { const t = document.createElement('table'); t.className = 'st'; t.innerHTML = '<tr><th></th><th>Value</th><th>Max</th></tr>'; return t; };
    const put = (t, name, arr, i, step, hi) => { const r = t.insertRow(); r.insertCell().textContent = name; r.insertCell().append(num(() => arr[i], v => arr[i] = v, 0, hi)); r.insertCell().append(num(() => arr[i + 2], v => arr[i + 2] = v, 0, hi)); };
    const t1 = mk(); ATTRS.forEach((a, z) => put(t1, a, c.attrib, z * 6, 6, 255));
    put(t1, 'Hit points', c.hp, 0, 0, 65535); put(t1, 'Endurance', c.end, 0, 0, 65535); put(t1, 'Mana', c.mana, 0, 0, 65535);
    const h = document.createElement('div'); h.innerHTML = '<h4>Body</h4>'; h.append(t1); cols.append(h);
    const t2 = mk(); SKILLS.forEach((s2, z) => { if (c.skill[z * 6 + 2] || c.skill[z * 6]) put(t2, s2, c.skill, z * 6, 6, 255); });
    const h2 = document.createElement('div'); h2.innerHTML = '<h4>Skills</h4>'; h2.append(t2); cols.append(h2);
  },
  gear(b, c) { playerSlots(b, c, 'worn', 'Worn', WEAR); playerSlots(b, c, 'citem', 'In the hand (on the mouse)', ['Held']); playerSlots(b, c, 'item', 'Backpack', null, 40); },
  depot(b, c) { b.insertAdjacentHTML('beforeend', `<div class="note">Rent paid so far: ${Math.floor(c.depot_cost / 100)}G ${c.depot_cost % 100}S. Bank: ${Math.floor(c.bank / 100)}G ${c.bank % 100}S (on the Overview tab).</div>`); playerSlots(b, c, 'depot', 'Depot', null, 62); },
  history(b, c) {
    const g = grid2(b);
    row(g, 'Created', document.createTextNode(fmtDate(c.creation_date)));
    row(g, 'Last login', document.createTextNode(fmtDate(c.login_date)));
    row(g, 'Last logout', document.createTextNode(c.online ? 'online now' : fmtDate(c.logout_date)));
    row(g, 'Time played', document.createTextNode(fmtDur(c.total_online_time) + (c.online ? ` (this session ${fmtDur(c.current_online_time)})` : '')));
    row(g, 'Last address', document.createTextNode(c.ip || '–'));
    const box = document.createElement('div'); b.append(box);
    const show = () => {
      const H = TP.hist; box.innerHTML = '';
      if (!H) { box.innerHTML = '<div class="hint">Reading the server log…</div>'; return; }
      const f = document.createElement('div'); f.className = 'ipick'; f.style.margin = '14px 0 6px';
      const s = document.createElement('select'); s.innerHTML = '<option value="">everything</option><option value="session">logins and logouts</option><option value="kill">kills</option><option value="death">deaths</option><option value="other">other</option>';
      s.value = TP.histF || ''; s.onchange = () => { TP.histF = s.value; show(); };
      f.append(`From the server log: ${H.length} entr${H.length === 1 ? 'y' : 'ies'} · show `, s); box.append(f);
      const list = H.filter(e => !TP.histF || (TP.histF === 'session' ? e.kind === 'login' || e.kind === 'logout' : e.kind === TP.histF)).slice().reverse();
      const t = document.createElement('table'); t.className = 'st'; t.style.width = '100%';
      const col = { login: 'var(--ok)', logout: 'var(--dim)', kill: 'var(--gold2)', death: 'var(--bad)', other: 'var(--text)' };
      for (const e of list.slice(0, 400)) {
        const r = t.insertRow();
        r.insertCell().innerHTML = `<span class="mono" style="color:var(--dim)">${esc(e.t)}</span>`;
        const m = r.insertCell(); m.style.color = col[e.kind]; m.textContent = e.text;
        const w = r.insertCell(); w.innerHTML = `<span class="mono hint">${e.x},${e.y}</span>`; w.style.cursor = 'pointer'; w.title = 'Show on the map';
        w.onclick = () => { closeTemplate(); centerOn(e.x, e.y); };
      }
      if (!list.length) box.insertAdjacentHTML('beforeend', '<div class="hint">Nothing in the server log for this character (the log only covers what the server wrote since it was last cleared).</div>');
      box.append(t);
    };
    show();
    if (!TP.hist) api('/api/phist?c=' + c.c).then(h => { if (TP && TP.kind === 'player') { TP.hist = h; if (TP.tab === 'history') show(); } });
  },
  account(b, c) {
    const g = grid2(b);
    const a = document.createElement('a'); a.className = 'btn sec'; a.href = '/api/moa?c=' + c.c; a.download = c.name + '.moa'; a.textContent = 'Download ' + c.name + '.moa';
    row(g, 'Character file', a, 'For a player who lost theirs: in the client, Load it, then log in. Anyone with this file can play the character, so send it only to its owner.');
    const pw = bit(c.flags, 42);
    row(g, 'Password', pw ? chk('Remove the password (on Apply)', () => !!TP.nopass, on => TP.nopass = on) : document.createTextNode('none set'), pw ? 'For a player who forgot it. They can set a new one in the game.' : '');
    row(g, 'Character number', document.createTextNode(c.c));
    const g2 = grid2(b, 'Rights and flags');
    row(g2, '', chks(PFLAGS.map(([bt, l]) => chk(l, () => bit(c.flags, bt), on => c.flags = setBit(c.flags, bt, on)))));
  },
};
function playerSlots(b, c, where, title, names, count) {
  const g = grid2(b, title);
  const list = where === 'citem' ? [c.items.citem] : c.items[where];
  const n = names ? names.length : count;
  const free = list.findIndex(v => !v);
  for (let i = 0; i < n; i++) {
    const it = list[i];
    if (!it && !names && i !== free) continue;
    const d = document.createElement('div'); d.className = 'ipick';
    if (it) {
      d.append(thumb(it.sprite, 28));
      const nm = document.createElement('span'); nm.className = 'nm'; nm.textContent = it.name; nm.title = `item ${it.i} · template ${it.temp} · worth ${Math.floor(it.value / 100)}G ${it.value % 100}S${it.desc ? '\n' + it.desc : ''}`; d.append(nm);
      const e = document.createElement('button'); e.className = 'sm'; e.textContent = 'Template…'; e.onclick = () => openTemplate('item', it.temp); d.append(e);
      const x = document.createElement('button'); x.className = 'sm'; x.textContent = 'Remove';
      x.onclick = () => { if (confirm(`Take ${it.name} away from ${c.name}? (Ctrl+Z undoes it)`)) playerItem({ op: 'pdelitem', c: c.c, where, slot: i }); }; d.append(x);
    } else {
      const s = document.createElement('span'); s.className = 'nm none'; s.textContent = 'empty'; d.append(s);
      const ad = document.createElement('button'); ad.className = 'sm'; ad.textContent = '+ Give an item…';
      const PLW = [1, 2, 4, 8, 32, 64, 128, 512, 256 | 2048, 1024, 4096, 4096];   // what fits each worn slot (PL_ bits)
      ad.onclick = () => itemPopup(ad, t => playerItem({ op: 'padditem', c: c.c, where, slot: i, t }), where === 'worn' ? (t => (t[7] || 0) & PLW[i]) : (t => t[3])); d.append(ad);
    }
    row(g, names ? names[i] : (it ? 'Slot ' + (i + 1) : 'Add'), d);
  }
}

// ---------------------------------------------------------------- editing
function footprint(x, y) {
  const out = [], o = Math.floor((size - 1) / 2);
  for (let dy = 0; dy < size; dy++) for (let dx = 0; dx < size; dx++) out.push([x - o + dx, y - o + dy]);
  return out;
}
function opFor(x, y, alt) {
  const b = brush;
  if (tool === 'erase' || (alt && (b.kind === 'place' || b.kind === 'object'))) return { op: 'erase', x, y };
  if (b.kind === 'flag') return { op: 'flag', x, y, bit: b.bit, mode: alt ? 0 : 1 };
  if (alt) return null;
  if (b.kind === 'floor') return { op: 'floor', x, y, s: b.s, set: b.set };
  if (b.kind === 'mix') return { op: 'floor', x, y, s: mixPick(b.items), set: false };
  if (b.kind === 'object') return { op: 'object', x, y, s: b.s, block: b.block };
  if (b.kind === 'place') return { op: 'place', x, y, t: b.t[0] };
  return null;
}
function label(alt) {
  if (tool === 'erase') return 'erase';
  const b = brush;
  if (b.kind === 'flag') return (alt ? 'cleared ' : 'set ') + FLAGS[b.bit];
  if (alt) return 'erase';
  return b.kind === 'floor' ? 'floor ' + b.s : b.kind === 'mix' ? (b.name ? 'mix ' + b.name : 'floor mix ' + b.items.map(i => i.s).join('/')) : b.kind === 'place' ? b.t[1] : 'object ' + b.s;
}
function preview(op) {
  const t = T(op.x, op.y);
  if (!t) return;
  const d = t.d, i = t.i;
  if (op.op === 'floor') d.g[i] = op.s;
  else if (op.op === 'object') d.f[i] = op.s;
  else if (op.op === 'place') { if (brush.t && brush.t[6]) { if (!d.it[i]) { d.it[i] = brush.t[2]; d.f[i] = 0; } } else if (brush.t) d.f[i] = brush.t[2]; }
  else if (op.op === 'erase') { d.f[i] = 0; d.it[i] = 0; }
  else if (op.op === 'flag') { const b = 1 << op.bit; d.fl[i] = op.mode === 1 ? (d.fl[i] | b) : (d.fl[i] & ~b); }
  redraw();
}
async function edit(ops, lbl, reselect) {
  if (!ops.length) return;
  if (RO()) { toast('The game server is running and live editing is not available (the server needs "Update code & restart" once).', true); refetch(ops.filter(o => o.x !== undefined).map(o => [o.x, o.y])); return; }
  const r = await api('/api/edit', { ops, label: lbl });
  if (r.error) toast(r.error, true);
  else if (r.msgs && r.msgs.length) toast([...new Set(r.msgs)].slice(0, 3).join('\n'), true);
  Object.assign(info, { dirty: r.dirty ?? info.dirty, undo: r.undo ?? info.undo, redo: r.redo ?? info.redo }); status();
  if (r.live && ops.some(o => o.op.startsWith('npc') || o.op.includes('temp'))) { chunks.clear(); redraw(); }
  refetch(ops.filter(o => o.x !== undefined).flatMap(o => o.tx !== undefined ? [[o.x, o.y], [o.tx, o.ty]] : [[o.x, o.y]]));
  if (r.ok !== false && ops.some(o => o.op.startsWith('npc'))) api('/api/npcs').then(n => { if (Array.isArray(n) && pal) { pal.npcs = n; if (mode === 'map' && tab === 'npcs') leftUI(); } });
  if (selTile && (reselect || ops.some(o => o.x === selTile.x && o.y === selTile.y))) selectTile(selTile.x, selTile.y);
  if (mode === 'history') leftUI();
  if (ops.length === 1 && ops[0].op === 'place' && !r.error && !(r.msgs && r.msgs.length)) {
    const pt = pal.templates.find(t => t[0] === ops[0].t);
    if (pt && pt[4] === 75) { selectTile(ops[0].x, ops[0].y); openChest(ops[0].x, ops[0].y); }
  }
}
async function undoRedo(w) {
  if (RO()) return;
  const r = await api('/api/' + w, {});
  if (r.error) return toast(r.error, true);
  if (r.note) toast(r.note);
  Object.assign(info, { dirty: r.dirty, undo: r.undo, redo: r.redo }); status();
  if (r.tiles && r.tiles.length) { refetch(r.tiles); toast((w === 'undo' ? 'Undone: ' : 'Redone: ') + r.tiles.length + ' tile(s)'); if (selTile) selectTile(selTile.x, selTile.y); }
  else if (r.done) { chunks.clear(); redraw(); toast(w === 'undo' ? 'Undone.' : 'Redone.'); if (selTile) selectTile(selTile.x, selTile.y); }
  if (mode === 'history') leftUI();
}
function fill(x, y, alt) {
  const s = T(x, y);
  if (!s) return;
  const byFloor = brush.kind === 'floor' && tool !== 'erase' && !alt;
  const g0 = s.d.g[s.i];
  const ok = (t) => {
    if (!t) return false;
    const g = t.d.g[t.i];
    if (byFloor) return g === g0;
    // a room: up to its walls and the edge of the void, and only indoors (or only outdoors) like where you clicked
    return g !== 1008 && !(t.d.fl[t.i] & 1) && ((t.d.fl[t.i] >>> 2) & 1) === in0;
  };
  const in0 = (s.d.fl[s.i] >>> 2) & 1;
  if (!ok(s)) return toast(byFloor ? 'Nothing to fill there.' : 'That tile is a wall: click inside a room.', true);
  const seen = new Set([x + ',' + y]), q = [[x, y]], ops = [];
  while (q.length) {
    const [cx, cy] = q.pop();
    const op = opFor(cx, cy, alt); if (op) ops.push(op);
    if (ops.length > 20000) return toast('That area is too big to fill (over 20000 tiles).', true);
    const here = T(cx, cy);
    if (!byFloor && here && here.d.it[here.i] && (cx !== x || cy !== y)) continue;   // a door or other item: filled, but the fill doesn't go past it
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = cx + dx, ny = cy + dy, k = nx + ',' + ny;
      if (seen.has(k)) continue; seen.add(k);
      const t = T(nx, ny);
      if (!t) { if (nx >= 0 && ny >= 0 && nx < MAPX && ny < MAPX) return toast('Part of that area is not loaded yet: zoom out a little and try again.', true); continue; }
      if (ok(t) || (!byFloor && t.d.it[t.i] && t.d.g[t.i] !== 1008)) q.push([nx, ny]);
    }
  }
  ops.forEach(preview);
  edit(ops, label(alt) + ' (fill)');
}
async function pick(x, y) {
  const r = await api(`/api/tile?x=${x}&y=${y}`);
  if (r.item) {
    const t = pal.templates.find(t => t[0] === r.item.temp);
    if (t) { setBrush({ kind: 'place', t }); toast('Picked ' + t[1]); return; }
  }
  if (r.object) { setBrush({ kind: 'object', s: r.object, block: (r.flags.includes('move block') ? 1 : 0) | (r.flags.includes('sight block') ? 2 : 0) }); toast('Picked object ' + r.object); return; }
  setBrush({ kind: 'floor', s: r.floor, set: false }); toast('Picked floor ' + r.floor);
}

// ---------------------------------------------------------------- tools
function setTool(t) {
  tool = t;
  document.querySelectorAll('#toolgrp button').forEach(b => b.classList.toggle('on', b.dataset.t === t));
  cv.style.cursor = t === 'pan' ? 'grab' : t === 'select' ? 'default' : 'crosshair';
  redrawTop();
}
$('#toolgrp').innerHTML = TOOLS.map(([t, k, tip, path]) => `<button class="slot" data-t="${t}" title="${tip} (${k})"><svg viewBox="0 0 24 24">${path}</svg><i>${k}</i></button>`).join('');
document.querySelectorAll('#toolgrp button').forEach(b => b.onclick = () => setTool(b.dataset.t));
$('#size').onchange = e => { size = +e.target.value; $('#szbtn span').textContent = size; redrawTop(); };
$('#szbtn').onclick = () => stepSize(1);
$('#szbtn').oncontextmenu = e => { e.preventDefault(); stepSize(-1); };
function stepSize(d) {
  const o = [...$('#size').options].map(o => +o.value), i = Math.max(0, Math.min(o.length - 1, o.indexOf(size) + d));
  size = o[i]; $('#size').value = size; $('#szbtn span').textContent = size; redrawTop();
}

// ---------------------------------------------------------------- input
function resize() {
  const r = $('#view').getBoundingClientRect();
  W = cv.width = Math.floor(r.width); H = cv.height = Math.floor(r.height); redraw();
}
window.addEventListener('resize', resize);
cv.addEventListener('contextmenu', e => e.preventDefault());
function zoomAt(f, sx, sy) {
  if (sx === undefined) { sx = W / 2; sy = H / 2; }
  const px = (sx - W / 2) / zoom + cam.x, py = (sy - H / 2) / zoom + cam.y;
  zoom = Math.min(3, Math.max(.15, zoom * f));
  cam.x = px - (sx - W / 2) / zoom; cam.y = py - (sy - H / 2) / zoom;
  $('#zv').textContent = Math.round(zoom * 100) + '%';
  $('#zr').value = Math.round(Math.log(zoom / .15) / Math.log(20) * 100);
  redraw();
}
$('#zr').oninput = e => zoomAt(.15 * Math.pow(20, +e.target.value / 100) / zoom);
$('#zr').value = Math.round(Math.log(1 / .15) / Math.log(20) * 100);
$('#zin').onclick = () => zoomAt(1.25); $('#zout').onclick = () => zoomAt(1 / 1.25);
cv.addEventListener('wheel', e => {
  e.preventDefault();
  const r = cv.getBoundingClientRect();
  zoomAt(e.deltaY < 0 ? 1.15 : 1 / 1.15, e.clientX - r.left, e.clientY - r.top);
}, { passive: false });
cv.addEventListener('mousedown', e => {
  $('#results').style.display = 'none';
  const r = cv.getBoundingClientRect(), sx = e.clientX - r.left, sy = e.clientY - r.top, t = screenToTile(sx, sy);
  if (e.button === 1 || e.button === 2 || (e.button === 0 && (spaceDown || tool === 'pan'))) { panning = { sx, sy, cx: cam.x, cy: cam.y }; cv.style.cursor = 'grabbing'; e.preventDefault(); return; }
  if (e.button !== 0) return;
  if (destPick) { if (RO()) { destPick = null; return toast('The game server is running: editing is off.', true); } setDestination(t); return; }
  if (tplPick) { tplPicked(t); return; }
  if (npcPick) { if (RO()) { npcPick = null; return toast('The game server is running: editing is off.', true); } moveNpc(t); return; }
  if (tool === 'select') { selectTile(t.x, t.y); return; }
  if (tool === 'pick') { pick(t.x, t.y); return; }
  if (RO()) { toast('The game server is running: editing is off.', true); return; }
  if (brush.kind === 'npc' && tool !== 'erase') {     // NPCs go one at a time
    if (e.altKey) edit([{ op: 'npcremove', x: t.x, y: t.y }], 'removed an NPC');
    else edit([{ op: 'npcplace', x: t.x, y: t.y, t: brush.t[0], dir: brush.dir || 4 }], `placed ${brush.t[1]} (facing ${FACEN[brush.dir || 4]})`);
    return;
  }
  if (tool === 'fill') { fill(t.x, t.y, e.altKey); return; }
  if (tool === 'rect' || e.shiftKey) { rect = { a: t, b: t, alt: e.altKey }; redrawTop(); return; }
  stroke = { ops: [], seen: new Set(), alt: e.altKey };
  paintAt(t);
});
function paintAt(t) {
  for (const [x, y] of footprint(t.x, t.y)) {
    const k = x + ',' + y;
    if (stroke.seen.has(k)) continue;
    stroke.seen.add(k);
    const op = opFor(x, y, stroke.alt);
    if (op) { stroke.ops.push(op); preview(op); }
  }
  if (!stroke.ops.length && brush.kind !== 'flag' && stroke.alt) toast('Alt with a floor does nothing: use the eraser for objects.', true);
}
window.addEventListener('mousemove', e => {
  const r = cv.getBoundingClientRect(), sx = e.clientX - r.left, sy = e.clientY - r.top;
  if (panning) { cam.x = panning.cx - (sx - panning.sx) / zoom; cam.y = panning.cy - (sy - panning.sy) / zoom; redraw(); return; }
  if (e.target !== cv && !stroke && !rect) { if (hover) { hover = null; redrawTop(); } return; }
  const t = screenToTile(sx, sy);
  if (!hover || hover.x !== t.x || hover.y !== t.y) {
    hover = t; redrawTop();
    const d = T(t.x, t.y);
    let s = `${t.x}, ${t.y}`;
    const z = info.areas.filter(a => a[0] <= t.x && t.x <= a[2] && a[1] <= t.y && t.y <= a[3]).map(a => a[4]);
    if (z.length) s += ' · ' + z[z.length - 1];
    if (d) { s += ` · floor ${d.d.g[d.i]}`; if (d.d.f[d.i]) s += ` · wall ${d.d.f[d.i]}`; if (d.d.it[d.i]) s += ' · item'; if (d.d.ch[d.i]) s += ' · NPC'; else if (d.d.pc && d.d.pc[d.i]) s += ' · NPC (spawns)'; }
    $('#coords').textContent = s;
  }
  if (rect) { rect.b = t; redrawTop(); return; }
  if (stroke) paintAt(t);
});
window.addEventListener('mouseup', () => {
  if (panning) { panning = null; setTool(tool); return; }
  if (rect) {
    const x0 = Math.min(rect.a.x, rect.b.x), x1 = Math.max(rect.a.x, rect.b.x), y0 = Math.min(rect.a.y, rect.b.y), y1 = Math.max(rect.a.y, rect.b.y), alt = rect.alt;
    rect = null;
    if ((x1 - x0 + 1) * (y1 - y0 + 1) > 40000) { toast('That area is too big (at most 200×200 at once).', true); redrawTop(); return; }
    const ops = [];
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) { const op = opFor(x, y, alt); if (op) { ops.push(op); preview(op); } }
    edit(ops, label(alt) + ` (${x1 - x0 + 1}×${y1 - y0 + 1})`); return;
  }
  if (stroke) {
    const s = stroke; stroke = null;
    const p = edit(s.ops, label(s.alt));
    // a portal: ask right away where it should lead
    if (!s.alt && brush.kind === 'place' && brush.t[4] === 6 && s.ops.length === 1 && s.ops[0].op === 'place') {
      const o = s.ops[0];
      p.then(() => { selectTile(o.x, o.y); destPick = { x: o.x, y: o.y }; cv.style.cursor = 'cell';
        toast('Portal placed. Now click where it should lead: here on the map, or press M and click on the world map. (Esc: decide later)'); });
    }
  }
});
window.addEventListener('keydown', e => {
  const k = e.key.toLowerCase();
  if (TP && k === 'escape') { if (tplPick) tplPicked(null); else if ($('#ipop').style.display === 'flex') $('#ipop').style.display = 'none'; else closeTemplate(); return; }
  if (TP && !tplPick) return;      // the template editor is open: its fields get the keys
  if ((e.ctrlKey || e.metaKey) && k === 'k') { e.preventDefault(); $('#q').focus(); $('#q').select(); return; }
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') {
    if (k === 'escape') e.target.blur();
    return;
  }
  if (e.ctrlKey || e.metaKey) {
    if (k === 'z' && !e.shiftKey) { e.preventDefault(); undoRedo('undo'); }
    else if (k === 'y' || (k === 'z' && e.shiftKey)) { e.preventDefault(); undoRedo('redo'); }
    else if (k === 's') { e.preventDefault(); save(); }
    return;
  }
  if (k === ' ') { spaceDown = true; cv.style.cursor = 'grab'; e.preventDefault(); return; }
  if (k === 'escape') { if (destPick || npcPick) { destPick = npcPick = null; setTool(tool); toast('Cancelled.'); return; } toggleWorld(false); rect = null; selTile = null; redrawTop(); return; }
  const map = { v: 'select', b: 'brush', u: 'rect', f: 'fill', e: 'erase', i: 'pick', h: 'pan' };
  if (map[k]) return setTool(map[k]);
  if (k === '[') return stepSize(-1);
  if (k === ']') return stepSize(1);
  if (k === 'g') return flipShow('grid');
  if (k === 'w') return flipShow('see');
  if (k === 'l') return flipShow('light');
  if (k === 'm') return toggleWorld();
  if (k === 'n') { flipShow('npcnames'); try { localStorage.setItem('myv2.npcnames', show.npcnames ? '1' : '0'); } catch (e) {} return; }
  const step = 160 / zoom;
  if (k === 'arrowleft') { cam.x -= step; redraw(); } else if (k === 'arrowright') { cam.x += step; redraw(); }
  else if (k === 'arrowup') { cam.y -= step; redraw(); } else if (k === 'arrowdown') { cam.y += step; redraw(); }
});
window.addEventListener('keyup', e => { if (e.key === ' ') { spaceDown = false; setTool(tool); } });
window.addEventListener('blur', () => { spaceDown = false; });

// ---------------------------------------------------------------- search
let sq = 0, sres = [], sact = 0;
$('#q').addEventListener('input', async () => {
  const q = $('#q').value, id = ++sq;
  if (!q.trim()) { $('#results').style.display = 'none'; return; }
  const r = await api('/api/search?q=' + encodeURIComponent(q));
  if (id !== sq) return;
  sres = r; sact = 0; results();
});
$('#q').addEventListener('keydown', e => {
  if (e.key === 'ArrowDown') { sact = Math.min(sres.length - 1, sact + 1); results(); e.preventDefault(); }
  else if (e.key === 'ArrowUp') { sact = Math.max(0, sact - 1); results(); e.preventDefault(); }
  else if (e.key === 'Enter' && sres[sact]) { choose(sres[sact]); }
  else if (e.key === 'Escape') { $('#results').style.display = 'none'; $('#q').blur(); }
});
$('#q').addEventListener('focus', () => { if (sres.length && $('#q').value.trim()) $('#results').style.display = 'block'; });
function results() {
  const box = $('#results'); box.innerHTML = '';
  if (!sres.length) { box.innerHTML = '<div class="r" style="cursor:default;color:var(--dim)">Nothing found.</div>'; box.style.display = 'block'; return; }
  sres.forEach((r, i) => {
    const el = document.createElement('div'); el.className = 'r' + (i === sact ? ' act' : '');
    el.innerHTML = `<span class="ty">${{ place: 'place', npc: 'NPC', player: 'player', item: 'item' }[r.type]}</span>`;
    if (r.sprite) el.appendChild(thumb(r.sprite, 30)); else { const s = document.createElement('span'); s.style.width = '30px'; el.appendChild(s); }
    const n = document.createElement('span'); n.textContent = r.name; el.appendChild(n);
    const sub = document.createElement('span'); sub.className = 'sub mono';
    sub.textContent = r.type === 'item' ? 'template ' + r.t + ' · use as brush' : `${r.x}, ${r.y}` + (r.type === 'player' ? (r.online ? ' · online' : ' · offline') : '');
    el.appendChild(sub);
    el.onmousedown = e => { e.preventDefault(); choose(r); };
    box.appendChild(el);
  });
  box.style.display = 'block';
  const a = box.querySelector('.act'); if (a) a.scrollIntoView({ block: 'nearest' });
}
function choose(r) {
  $('#results').style.display = 'none'; $('#q').blur();
  if (r.type === 'item') {
    const t = pal && pal.templates.find(t => t[0] === r.t);
    if (t) { setBrush({ kind: 'place', t }); mode = 'map'; tab = t[3] ? 'items' : cats().walls.includes(t) ? 'walls' : 'objects'; document.querySelectorAll('nav button').forEach(x => x.classList.toggle('on', x.dataset.m === 'map')); $('#lsearch').value = String(t[0]); leftUI(); toast('Brush: ' + t[1]); }
    return;
  }
  centerOn(r.x, r.y); selectTile(r.x, r.y);
}
document.addEventListener('mousedown', e => { if (!$('#search').contains(e.target)) $('#results').style.display = 'none'; });

// ---------------------------------------------------------------- saving and status
async function save() {
  if (info.running) return toast('Stop the game server first.', true);
  if (!info.dirty) return toast('Nothing to save.');
  const r = await api('/api/save', {});
  if (r.error) return toast(r.error, true);
  info.dirty = r.dirty; await refreshInfo(); toast(r.msg + (r.dirty === 0 ? '\nTip: ./server light recomputes the lighting (the Relight button below).' : ''), r.dirty !== 0);
  relightBtn(r.dirty === 0);
  if (mode === 'history') leftUI();
}
$('#save').onclick = save;
$('#discard').onclick = async () => {
  if (!info.dirty) return toast('Nothing to discard.');
  if (!confirm('Throw away all unsaved changes?')) return;
  const r = await api('/api/reload', {});
  chunks.clear(); redraw(); relightBtn(false); toast('Changes discarded.'); await refreshInfo(); if (selTile) selectTile(selTile.x, selTile.y);
};
$('#undosave').onclick = async () => {
  if (info.running) return toast('Stop the game server first.', true);
  if (info.dirty) return toast('Save or discard the current changes first.', true);
  if (!confirm('Put the world back as it was before the last save? (The newer files are replaced by that backup.)')) return;
  const r = await api('/api/restore', {});
  if (r.error) return toast(r.error, true);
  chunks.clear(); redraw(); toast(r.msg); relightBtn(false); await refreshInfo();
  if (mode === 'history') leftUI();
};
$('#tref').onclick = async () => {
  if (info.dirty && !confirm('Throw away the unsaved changes and load the world from disk again?')) return;
  const r = await api('/api/reload', {}); chunks.clear(); redraw(); toast(r.msg); refreshInfo();
};
function relightBtn(on) {
  let b = $('#relight');
  if (!on) { if (b) b.remove(); return; }
  if (b) return;
  b = document.createElement('button'); b.id = 'relight'; b.className = 'btn ghost'; b.style.cssText = 'padding:0;margin:8px 0 0 14px;font-size:12px'; b.textContent = 'Relight the world'; b.title = 'Recompute the lighting of the whole world (./server light)';
  b.onclick = async () => {
    if (!confirm('Recompute the lighting of the whole world? It takes a minute or two.')) return;
    toast('Relighting… a minute or two.');
    const r = await api('/api/relight', {});
    if (r.error) return toast(r.error, true);
    chunks.clear(); redraw(); toast(r.msg); b.remove(); refreshInfo();
  };
  $('#undosave').insertAdjacentElement('afterend', b);
}
function status() {
  const p = $('#pill');
  p.className = info.running ? 'up' : 'down';
  p.textContent = info.running ? `Server up · ${info.online} online${info.live ? ' · live editing' : ''}` : 'Server stopped · editing on';
  $('#banner').style.display = info.running ? 'block' : 'none';
  $('#view').classList.toggle('hasban', !!info.running);
  $('#banner').classList.toggle('live', !!info.live);
  $('#banner').textContent = info.live ? 'Live editing: every change goes straight into the running game, and players see it right away. Ctrl+Z undoes it.'
    : 'The game server is running: you can look around, but editing is off. (Live editing needs the newer server: "Update code & restart" on the Server page.)';
  const d = $('#dirty');
  d.textContent = info.running ? (info.live ? 'Live: nothing to save, changes are in the game' : 'View only while the server runs') : info.dirty ? `${info.dirty} unsaved change${info.dirty === 1 ? '' : 's'}` : 'No unsaved changes';
  d.classList.toggle('on', !!info.dirty);
  $('#save').disabled = info.running || !info.dirty;
  $('#discard').disabled = !info.dirty;
  $('#undo').disabled = RO() || !info.undo;
  $('#redo').disabled = RO() || !info.redo;
  $('#undosave').disabled = info.running || !!info.dirty || !info.backups;
}
async function refreshInfo() {
  const r = await api('/api/info');
  const first = !info.areas.length, gen = info.gen;
  Object.assign(info, r); status();
  if (gen && r.gen !== gen) { chunks.clear(); redraw(); if (selTile && !$('#tile').contains(document.activeElement)) selectTile(selTile.x, selTile.y); }
  if (r.minimap && !miniOk && !mini.src) { mini.onload = () => { miniOk = true; $('#mini').style.display = 'block'; redraw(); }; mini.src = '/minimap.png'; }
  if (first) redraw();
}

// ---------------------------------------------------------------- server page
let srvSt = null;
function fmtUp(s) { if (s == null) return '–'; const d = Math.floor(s / 86400), h = Math.floor(s / 3600) % 24, m = Math.floor(s / 60) % 60; return (d ? d + 'd ' : '') + (d || h ? h + 'h ' : '') + m + 'm'; }
async function srvRefresh() {
  if (mode !== 'server') return;
  const st = await api('/api/srv/status'); srvSt = st;
  $('#sdot').className = 'dotst' + (st.running ? ' up' : '');
  $('#sstate').textContent = st.running ? 'Running' : 'Stopped';
  $('#sfacts').innerHTML = st.running
    ? `<span>Players online <b>${st.online}</b></span><span>Up <b>${fmtUp(st.uptime)}</b></span>` + (st.port ? '' : '<span style="color:var(--gold2)">control port not answering: the running ./server is older than this feature (Update code &amp; restart)</span>')
    : '<span>Start it here; it keeps running when you close the editor. Its output goes to server.log.</span>';
  const busy = st.job && !st.job.done;
  $('#sstart').disabled = st.running || busy; $('#srestart').disabled = !st.running || busy; $('#sstop').disabled = !st.running || busy;
  $('#supcode').disabled = busy; $('#supworld').disabled = busy; $('#ssend').disabled = busy; $('#sget').disabled = busy; $('#sgetw').disabled = st.running || busy;
  const jb = $('#sjob');
  if (st.job) { jb.style.display = 'block'; jb.textContent = `${st.job.name} · ${st.job.done ? (st.job.ok ? 'finished' : 'failed') : 'working…'}\n` + st.job.log.join('\n'); jb.scrollTop = jb.scrollHeight; }
  // players
  $('#pcount').textContent = st.running ? '· ' + st.players.length : '';
  const pl = $('#plist');
  if (!st.running) pl.innerHTML = '<div class="empty">The server is stopped.</div>';
  else if (!st.players.length) pl.innerHTML = '<div class="empty">Nobody online.</div>';
  else {
    pl.innerHTML = '<table class="pl"><tr><th>Name</th><th>Rank</th><th>Where</th><th></th><th></th></tr></table>';
    const t = pl.firstChild;
    for (const p of st.players) {
      const r = t.insertRow();
      r.insertCell().textContent = p.name + (p.role ? ` (${p.role})` : '');
      r.insertCell().textContent = p.rank;
      const w = r.insertCell(); w.className = 'w'; w.textContent = `${p.x}, ${p.y}` + (p.where ? ' · ' + p.where : '');
      const a = r.insertCell();
      for (const [lbl, fn] of [['Map', () => { document.querySelector('nav button[data-m=map]').click(); setTimeout(() => { centerOn(p.x, p.y); selectTile(p.x, p.y); }, 50); }],
        ['Tell', async () => { const m = prompt('Message to ' + p.name + ':'); if (m) runCmd('tell ' + p.name + ' ' + m); }],
        ['Gold', async () => { const m = prompt('How much gold for ' + p.name + '?', '10'); if (m && +m > 0) runCmd('gold ' + p.name + ' ' + (+m)); }],
        ['Exp', async () => { const m = prompt('How much experience for ' + p.name + '?', '1000'); if (m && +m > 0) runCmd('raise ' + p.name + ' ' + (+m)); }],
        ['Kick', async () => { if (confirm('Kick ' + p.name + '?')) runCmd('kick ' + p.name); }]]) {
        const b = document.createElement('button'); b.textContent = lbl; b.onclick = fn; a.appendChild(b);
      }
      r.insertCell().textContent = '';
    }
  }
  // Claude's requests
  const rq = $('#sreq');
  if (st.requests && st.requests.length) {
    rq.className = ''; rq.innerHTML = '';
    for (const e of st.requests.slice().reverse()) {
      const d = document.createElement('div'); d.className = 'req';
      d.innerHTML = '<span class="mono"></span> · <b></b> <span></span>';
      d.children[0].textContent = e.time; d.children[1].textContent = e.action + (e.cmd ? ': ' + e.cmd : ''); d.children[2].textContent = '— ' + e.result + (e.note ? ' · ' + e.note : '');
      rq.appendChild(d);
    }
  }
}
async function runCmd(cmd) {
  const o = $('#conout');
  o.textContent += '> ' + cmd + '\n';
  const r = await api('/api/srv/cmd', { cmd });
  o.textContent += (r.error ? r.error + '\n' : (r.output || '(no answer)\n'));
  o.scrollTop = o.scrollHeight;
  srvRefresh();
}
$('#scmdb').onclick = () => { const c = $('#scmd').value.trim(); if (c) { runCmd(c); $('#scmd').value = ''; } };
$('#scmd').addEventListener('keydown', e => { if (e.key === 'Enter') $('#scmdb').click(); });
$('#sannb').onclick = () => { const t = $('#sann').value.trim(); if (t) { runCmd('announce ' + t); $('#sann').value = ''; } };
$('#sann').addEventListener('keydown', e => { if (e.key === 'Enter') $('#sannb').click(); });
async function job(action, ask) {
  if (ask && !confirm(ask)) return;
  const r = await api('/api/srv/action', { action, warn: +$('#swarn').value });
  if (r.error) toast(r.error, true);
  srvRefresh();
}
$('#sstart').onclick = () => job('start');
$('#srestart').onclick = () => job('restart', 'Restart the game server? Players online are warned first (' + $('#swarn').selectedOptions[0].text + ').');
$('#sstop').onclick = () => job('stop', 'Stop the game server? Players online are warned first (' + $('#swarn').selectedOptions[0].text + ').');
$('#supcode').onclick = () => job('update-code', 'Stop the server, take the updated source (claude-sync.sh get), rebuild and start again?');
$('#supworld').onclick = () => job('update-world', 'Stop the server, take the world files from the Windows folder (claude-sync.sh get-world; a backup is made) and start again?');
$('#ssend').onclick = () => job('send', 'Copy the Ubuntu files to the Windows folder (claude-sync.sh send)?');
$('#sget').onclick = () => job('get', 'Take the changed source from Windows and rebuild (claude-sync.sh get)? The running server keeps going; the new build is used at the next restart.');
$('#sgetw').onclick = () => job('get-world', 'Take the world files from the Windows folder (claude-sync.sh get-world; a backup is made)?');
let logLines = [];
async function logRefresh(force) {
  if (mode !== 'server') return;
  if (!force && !$('#lfollow').checked) return;
  const r = await api('/api/srv/log?n=400'); logLines = r.log || []; logDraw();
}
function logDraw() {
  const f = $('#lfilter').value.toLowerCase(), b = $('#logbox');
  b.textContent = logLines.filter(l => !f || l.toLowerCase().includes(f)).join('\n') || '(server.log is empty)';
  if ($('#lfollow').checked) b.scrollTop = b.scrollHeight;
}
$('#lfilter').oninput = logDraw;
setInterval(srvRefresh, 3000);
setInterval(() => logRefresh(false), 3000);

// ---------------------------------------------------------------- start
(async function start() {
  resize();
  layersUI(); setTool('brush'); leftUI();
  await refreshInfo();
  pal = await api('/api/palette');
  card(); leftUI();
  const m = location.hash.match(/(\d+),(\d+)/);
  if (m) centerOn(+m[1], +m[2]); else centerOn(512, 512);
  setInterval(refreshInfo, 4000);
  setInterval(() => { const c = screenToTile(W / 2, H / 2); history.replaceState(null, '', '#' + c.x + ',' + c.y); }, 1000);
  loop();
})();
</script>
</body>
</html>
'''

if __name__ == '__main__':
    main()
