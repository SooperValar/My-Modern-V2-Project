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
from collections import Counter
import argparse, collections, glob, io, json, mmap, os, re, shutil, struct, subprocess, sys, threading, time, zlib, random
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

def weapon_skill(fl):
    """the skill an item template is fought with when wielded (as get_fight_skill in svr_do.c), -1: not a weapon"""
    if fl & (1 << 18) and fl & (1 << 20): return 36       # greataxe
    for bitn, sk in ((16, 3), (17, 2), (18, 4), (19, 5), (20, 6)):
        if fl & (1 << bitn): return sk
    return -1

# the player classes whose maximums "Scale to this rank" can keep to (their male templates)
CLASS_CAPS = [('Mercenary', 2), ('Templar', 3), ('Harakim', 4), ("Seyan'Du", 13), ('Warrior-Mercenary', 547),
              ('Sorcerer-Mercenary', 546), ('Arch-Templar', 544), ('Arch-Harakim', 545)]

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
    steps, chests, chest, order, qrew, clears = {}, {}, None, {}, {}, {}
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
                elif k == 'first' and a:
                    chest['first'] = int(a[0])
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
            if k == 'clear' and len(a) >= 4:          # area clears (Quests page): id, exp, again as Seyan'Du, zone name
                c = clears.setdefault(int(a[0]), {'id': int(a[0]), 'label': '', 'npcs': []})
                c.update({'exp': int(a[1]), 'seyan': int(a[2]), 'zone': rest.split(None, 3)[3].strip()})
                continue
            if k == 'clearlabel' and a:
                clears.setdefault(int(a[0]), {'id': int(a[0]), 'npcs': [], 'exp': 0, 'seyan': 1, 'zone': ''})['label'] = rest.split(None, 1)[1].strip() if len(a) > 1 else ''
                continue
            if k == 'clearnpc' and a:
                clears.setdefault(int(a[0]), {'id': int(a[0]), 'npcs': [], 'exp': 0, 'seyan': 1, 'zone': '', 'label': ''})['npcs'] += [int(v) for v in a[1:] if v.isdigit()]
                continue
            if k == 'qreward' and len(a) >= 4:        # item quest: times, first times, gold (Quests page); then qstage lines
                v = [int(x) for x in a[1:7] if x.lstrip('-').isdigit()]
                old = qrew.get(int(a[0]), {})
                r = qrew[int(a[0])] = {'lim': v[0], 'first': v[1], 'gold': v[2], 'st': [], 'rmin': old.get('rmin', -1), 'rmax': old.get('rmax', -1)}
                if len(v) >= 6 and any(v[3:6]):      # the older one-step form
                    r['st'].append([0, v[3], v[4], v[5]])
            elif k == 'qrank' and len(a) >= 3:         # who may do it: lowest and highest rank, -1 = none
                r = qrew.setdefault(int(a[0]), {'lim': 0, 'first': 0, 'gold': 0, 'st': []})
                r['rmin'], r['rmax'] = int(a[1]), int(a[2])
            elif k == 'qclass' and len(a) >= 4:        # class rewards: group 1-3 (Templar, Mercenary + Seyan'Du, Harakim), skill, item (-1 = as for everyone)
                r = qrew.setdefault(int(a[0]), {'lim': 0, 'first': 0, 'gold': 0, 'st': []})
                r.setdefault('cls', {})[str(int(a[1]))] = [int(a[2]), int(a[3])]
            elif k == 'qstage' and len(a) >= 5 and int(a[0]) in qrew:
                qrew[int(a[0])]['st'].append([int(x) for x in a[1:5]])
            elif k == 'order' and len(a) >= 2:          # #quest list order (Quests page): template, place (-1 = not listed)
                order[int(a[0])] = int(a[1])
            elif k == 'quest' and a:
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
                elif a[0] in ('class', '!class') and len(a) > 1:   # the player's class: names joined by |
                    e['conds'].append({'type': 'class', 'not': a[0] == '!class', 'c': a[1].lower()})
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
    return {'names': quests, 'steps': steps, 'chests': chests, 'order': order, 'qrew': qrew, 'clears': clears}, npcs


def talk_text(quests, npcs, names):
    out = ['# MyV2 custom NPC dialogue, kill tracking and quest steps - written by the MyV2 Editor (the server reads it: npctalk.c)', '']
    qn, qs = quests.get('names', {}), quests.get('steps', {})
    od = {int(t): int(v) for t, v in (quests.get('order') or {}).items() if int(v)}
    if od:
        out.append('# #quest list: order <NPC template> <place> (-1 = not listed) - the Quests page')
        for t in sorted(od, key=lambda t: (od[t] < 0, abs(od[t]), t)):
            out.append('order %d %d %s' % (t, od[t], names.get(t, '')))
        out.append('')
    qr = {int(t): r for t, r in (quests.get('qrew') or {}).items() if r.get('lim') or r.get('first') or r.get('gold') or r.get('st')
          or r.get('rmin', -1) >= 0 or r.get('rmax', -1) >= 0 or r.get('cls')}
    if qr:
        out.append('# item quests: qreward <NPC template> <times, 0 = forever> <the first reward for the first n times> <its gold>,')
        out.append('# then qstage <NPC template> <times, 0 = every time after> <item> <exp> <gold> for each later reward (gold in silver)')
        for t in sorted(qr):
            r = qr[t]
            out.append('qreward %d %d %d %d %s' % (t, int(r.get('lim', 0)), int(r.get('first', 0)), int(r.get('gold', 0)), names.get(t, '')))
            for st in (r.get('st') or [])[:7]:
                out.append('qstage %d %d %d %d %d' % (t, *[max(0, int(v)) for v in (list(st) + [0] * 4)[:4]]))
            if r.get('rmin', -1) >= 0 or r.get('rmax', -1) >= 0:
                out.append('qrank %d %d %d' % (t, int(r.get('rmin', -1)), int(r.get('rmax', -1))))
            for g, v in sorted((r.get('cls') or {}).items()):
                if int(g) in (1, 2, 3) and (int(v[0]) >= 0 or int(v[1]) >= 0):
                    out.append('qclass %d %d %d %d   # %s' % (t, int(g), int(v[0]), int(v[1]), ('Templar line', 'Mercenary line and Seyan\'Du', 'Harakim line')[int(g) - 1]))
        out.append('')
    cl = quests.get('clears') or {}
    if cl:
        out.append('# area clears: clear <id> <exp> <again as Seyan\'Du 0/1> <zone>; clearlabel <id> <text>; clearnpc <id> <NPC templates> - the Quests page')
        for i in sorted(cl, key=int):
            c = cl[i]
            if not str(c.get('zone', '')).strip():
                continue
            out.append('clear %d %d %d %s' % (int(i), int(c.get('exp', 0)), 1 if c.get('seyan') else 0, ' '.join(str(c['zone']).split())))
            if str(c.get('label', '')).strip():
                out.append('clearlabel %d %s' % (int(i), ' '.join(str(c['label']).split())))
            cnp = [int(t) for t in c.get('npcs', []) if int(t) > 0][:64]
            for k in range(0, len(cnp), 16):
                out.append('clearnpc %d %s' % (int(i), ' '.join(str(t) for t in cnp[k:k + 16])))
        out.append('')
    for n in sorted(set(qn) | set(qs)):
        out.append('quest %d %s' % (n, ' '.join(str(qn.get(n, '')).split())))
        for v, t in sorted(qs.get(n, []), key=lambda x: int(x[0])):
            if str(t).strip():
                out.append('step %d %d %s' % (n, int(v), ' '.join(str(t).split())))
    for key, c in sorted(quests.get('chests', {}).items()):
        if not c.get('rewards') and not c.get('first'):
            continue
        x, y = key.split(',')
        out += ['', 'chest %d %d %s' % (int(x), int(y), names.get('chest ' + key, ''))]
        if int(c.get('refill', 0) or 0) > 0: out.append('refill %d' % int(c['refill']))
        if c.get('once'): out.append('once player')
        if int(c.get('first', 0) or 0) > 0: out.append('first %d' % int(c['first']))
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
                elif ty == 'class' and re.fullmatch(r'[a-z|]+', str(c.get('c', ''))): out.append('if %sclass %s' % ('!' if c.get('not') else '', c['c']))
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
# rugs: corners and sides placed by position, the middle filled at random (found on the game's own map).
# Directions as the minimap: north = smaller x, west = smaller y.
BUILTIN_RUGS = [
    {"name": "Red rug", "nw": 523, "n": 524, "ne": 525, "w": 530, "e": 526, "sw": 529, "s": 528, "se": 527, "fill": [[520, 312], [521, 249], [522, 264]], "from": [22, 596]},
    {"name": "Blue rug", "nw": 534, "n": 535, "ne": 536, "w": 541, "e": 537, "sw": 540, "s": 539, "se": 538, "fill": [[531, 57], [532, 21], [533, 51]], "from": [27, 522]},
]
RUG_KEYS = ('nw', 'n', 'ne', 'w', 'e', 'sw', 's', 'se')

BUILTIN_AREAS = [{"name":"City Park","floors":[[553,22.2],[551,18.6],[554,17.5],[552,17.4]],"scatter":[{"k":"o","s":1114,"b":3,"p":0.00985},
    {"k":"o","s":1238,"b":3,"p":0.00923},
    {"k":"o","s":1112,"b":3,"p":0.00862},
    {"k":"o","s":1240,"b":3,"p":0.00492},
    {"k":"o","s":880,"b":3,"p":0.00308},
    {"k":"t","t":16,"p":0.01415},
    {"k":"t","t":17,"p":0.01292},
    {"k":"t","t":45,"p":0.01108},
    {"k":"t","t":47,"p":0.01046},
    {"k":"t","t":1133,"p":0.00554}],"apart":True,"from":[578,566,633,596]},
    {"name":"Forest","floors":[[1118,98.1],[989,1.1]],"scatter":[{"k":"o","s":1114,"b":3,"p":0.01212},
    {"k":"o","s":1112,"b":3,"p":0.01204},
    {"k":"o","s":1238,"b":3,"p":0.01122},
    {"k":"o","s":880,"b":3,"p":0.00817},
    {"k":"o","s":1240,"b":3,"p":0.00718},
    {"k":"o","s":882,"b":3,"p":0.00454},
    {"k":"o","s":1116,"b":3,"p":0.00214},
    {"k":"o","s":884,"b":3,"p":0.00099},
    {"k":"t","t":47,"p":0.00899},
    {"k":"t","t":17,"p":0.00775},
    {"k":"t","t":1133,"p":0.00289},
    {"k":"t","t":45,"p":0.00148},
    {"k":"t","t":16,"p":0.00115}],"apart":True,"from":[480,300,600,400]},
    {"name":"Dense Forest","floors":[[1118,92.5]],"scatter":[{"k":"o","s":1238,"b":3,"p":0.07616},
    {"k":"o","s":1240,"b":3,"p":0.04572}],"apart":False,"from":[24,600,120,696]},
    {"name":"Jungle","floors":[[1006,26.1],[1003,25.4],[1007,24.1],[1005,23.6]],"scatter":[{"k":"o","s":358,"b":3,"p":0.01528},
    {"k":"o","s":340,"b":0,"p":0.01445},
    {"k":"o","s":360,"b":3,"p":0.01321},
    {"k":"o","s":350,"b":0,"p":0.01156},
    {"k":"o","s":356,"b":3,"p":0.01115},
    {"k":"o","s":354,"b":0,"p":0.00991},
    {"k":"o","s":342,"b":0,"p":0.0095},
    {"k":"o","s":352,"b":0,"p":0.00826},
    {"k":"t","t":201,"p":0.01404},
    {"k":"t","t":203,"p":0.00867},
    {"k":"t","t":202,"p":0.00702}],"apart":True,"from":[500,145,540,205]},
    {"name":"Cave","floors":[[1014,97.5]],"scatter":[{"k":"o","s":1274,"b":1,"p":0.01981},
    {"k":"o","s":1282,"b":0,"p":0.00696},
    {"k":"o","s":1280,"b":0,"p":0.00634},
    {"k":"o","s":1278,"b":1,"p":0.00608},
    {"k":"o","s":1276,"b":1,"p":0.00452},
    {"k":"t","t":171,"p":0.00506}],"apart":False,"from":[215,445,405,595]},
    {"name":"Fire Cave","floors":[[704,25.5],[659,25.5],[688,25.0],[660,24.1]],"scatter":[{"k":"o","s":674,"b":1,"p":0.00651},
    {"k":"o","s":678,"b":1,"p":0.00359},
    {"k":"o","s":682,"b":1,"p":0.00219},
    {"k":"o","s":686,"b":1,"p":0.0014},
    {"k":"t","t":522,"p":0.00322}],"apart":True,"from":[275,305,405,435]},
    {"name":"Ice Cave","floors":[[16672,21.9],[16670,21.6],[16673,20.7],[16671,20.6]],"scatter":[{"k":"o","s":16696,"b":1,"p":0.00698},
    {"k":"o","s":16690,"b":1,"p":0.00537},
    {"k":"o","s":16692,"b":1,"p":0.00322},
    {"k":"o","s":16694,"b":1,"p":0.00269},
    {"k":"t","t":812,"p":0.00725}],"apart":True,"from":[330,246,408,299]}]     # learned from the game's own areas (area_learn), walls and stray pieces left out


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
        for a, b, c, d, n, f in self.areas:
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

    # --- zones: names made of one or more boxes (every box with the same name is one zone).
    # .dat/zones.dat ("x1 y1 x2 y2 flag name", one box a line) when it exists, else the server's area.c table.
    def zones_path(self):
        return os.path.join(self.dat, 'zones.dat')

    def read_areas(self):
        out = []
        try:
            for line in open(self.zones_path(), encoding='latin-1'):
                m = re.match(r'\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([0-3])\s+(.+?)\s*$', line)
                if m and not line.lstrip().startswith('#'):
                    out.append([int(m.group(i)) for i in range(1, 5)] + [m.group(6), int(m.group(5))])
            if out:
                self.zone_src = 'zones.dat'
                return out
        except OSError:
            pass
        self.zone_src = 'area.c'
        try:
            src = open(self.area_file, encoding='latin-1').read()
        except OSError:
            return []
        for a, b, c, d, n, f in re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*"([^"]+)",\s*(\d)\s*\}', src):
            out.append([int(a), int(b), int(c), int(d), n, int(f)])
        return out

    def zone(self, x, y):
        names = []
        for a, b, c, d, n, f in self.areas:
            if a <= x <= c and b <= y <= d and n not in names:
                names.append(n)
        return ', '.join(names)

    def zones_save(self, zones, ctl=None):
        """zones: [{name, flag, boxes: [[x1, y1, x2, y2], ...]}, ...] in the order the game lists them"""
        rows, seen = [], set()
        for z in zones:
            n = re.sub(r'\s+', ' ', str(z.get('name', ''))).strip()
            if not n:
                return 'A zone has no name.'
            if len(n) > 45:
                return 'The name "%s" is too long (at most 45 letters).' % n
            if n.lower() in seen:
                return 'Two zones are called "%s": give one another name (or join their boxes).' % n
            seen.add(n.lower())
            f = int(z.get('flag', 0))
            if not 0 <= f <= 3:
                return 'Bad flag for "%s".' % n
            if not z.get('boxes'):
                return 'The zone "%s" has no boxes: draw one, or delete the zone.' % n
            for bx in z['boxes']:
                x1, y1, x2, y2 = [int(v) for v in bx[:4]]
                x1, x2, y1, y2 = min(x1, x2), max(x1, x2), min(y1, y2), max(y1, y2)
                x2, y2 = min(x2, MAPX - 1), min(y2, MAPY - 1)      # area.c had some boxes ending at 1024
                if x1 < 0 or y1 < 0 or x1 > x2 or y1 > y2:
                    return 'A box of "%s" is off the map.' % n
                rows.append([x1, y1, x2, y2, n, f])
        p = self.zones_path()
        if os.path.exists(p):
            bk = os.path.join(self.dat, 'mapedit-backups')
            os.makedirs(bk, exist_ok=True)
            shutil.copy2(p, os.path.join(bk, 'zones-%s.dat' % time.strftime('%Y%m%d-%H%M%S')))
        with open(p + '.tmp', 'w', encoding='latin-1', errors='replace') as fh:
            fh.write('# Zones: x1 y1 x2 y2 flag name - one box a line; boxes with the same name are one zone.\n'
                     '# flag: 0 "in", 1 "in the", 2 "on" (a street), 3 "at". Written by the MyV2 Editor.\n')
            for r in rows:
                fh.write('%d %d %d %d %d %s\n' % (r[0], r[1], r[2], r[3], r[5], r[4]))
        os.replace(p + '.tmp', p)
        self.areas = self.read_areas()
        if ctl and server_running():
            r = ctl.console('zonereload', 5)
            if r and 'Zones loaded' in r:
                return ''
            return 'later'
        return ''

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
                              struct.unpack_from('<H', self.titem, o + I_PLACEMENT)[0], weapon_skill(fl)])
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
            return {'names': {}, 'steps': {}, 'chests': {}, 'order': {}, 'qrew': {}, 'clears': {}}, {}

    def talk_save(self, quests, npcs, ctl=None):
        p = self.talk_path()
        if os.path.exists(p):
            bk = os.path.join(self.dat, 'mapedit-backups')
            os.makedirs(bk, exist_ok=True)
            shutil.copy2(p, os.path.join(bk, 'npctalk-%s.dat' % time.strftime('%Y%m%d-%H%M%S')))
        names = {t: self.tname(t) for t in list(npcs) + list((quests.get('order') or {}).keys()) + list((quests.get('qrew') or {}).keys()) if isinstance(t, int) and self.tchar is not None and 0 < t < MAXTCHARS}
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

    def quests_view(self):
        """the Quests page: every NPC that wants an item (the #quest list), and the chain quests of npctalk.dat"""
        qs, npcs = self.talk_load()
        order, qrew = qs.get('order', {}), qs.get('qrew', {})
        simple = []
        if self.tchar is not None:
            for t in range(1, MAXTCHARS):
                o = t * CHAR_SIZE
                if not self.tchar[o + C_USED]:
                    continue
                d = list(struct.unpack_from('<100i', self.tchar, o + C_DATA))
                if d[49] <= 0:
                    continue
                x, y = struct.unpack_from('<hh', self.tchar, o + C_X)
                where = self.zone(x, y) if (x or y) else ''
                simple.append({'t': t, 'name': self.tname(t), 'sprite': self.tchar_sprite(t, 4),
                               'x': x, 'y': y, 'where': where, 'data': d, 'hint': cstr(self.tchar[o + CT_TEXT + 2 * 160:o + CT_TEXT + 3 * 160]),
                               'order': order.get(t, 0), 'rew': dict({'lim': 0, 'first': 0, 'gold': 0, 'st': [], 'rmin': -1, 'rmax': -1}, **qrew.get(t, {})), 'puzzle': bool(d[50] == 0 and ('Labyrinth' in where or 'Tower' in where)),
                               'count': len(self.living(t)) + len([p for p in self.pending() if p[2] == t])})
        refs = {}
        for who, ents in npcs.items():
            label = ('tile %s' % who[1:]) if isinstance(who, str) else self.tname(who) if self.tchar is not None and 0 < who < MAXTCHARS else str(who)
            for e in ents:
                for c in e.get('conds', []):
                    if c.get('type') == 'quest':
                        refs.setdefault(c['n'], {}).setdefault(str(who), {'who': who, 'label': label, 'kinds': set()})['kinds'].add('checks')
                for a in e.get('acts', []):
                    if a.get('type') in ('set', 'add'):
                        refs.setdefault(a['n'], {}).setdefault(str(who), {'who': who, 'label': label, 'kinds': set()})['kinds'].add('moves it on' if a['type'] == 'add' else 'sets it')
        chain = []
        for n in sorted(set(qs['names']) | set(qs['steps']) | set(refs)):
            chain.append({'n': n, 'name': qs['names'].get(n, ''), 'steps': sorted(qs['steps'].get(n, []), key=lambda v: int(v[0])),
                          'refs': [{'who': r['who'], 'label': r['label'], 'kinds': sorted(r['kinds'])} for r in refs.get(n, {}).values()]})
        clears = sorted(qs.get('clears', {}).values(), key=lambda c: c['id'])
        return {'simple': simple, 'chain': chain, 'clears': clears}

    def zone_npcs(self, zone):
        """NPC templates whose spawn spot is inside the zone (any of its boxes): the candidates for an area clear"""
        boxes = [a for a in self.areas if a[4].lower() == str(zone).lower()]
        out = []
        if self.tchar is None or not boxes:
            return out
        for t in range(1, MAXTCHARS):
            o = t * CHAR_SIZE
            if not self.tchar[o + C_USED]:
                continue
            x, y = struct.unpack_from('<hh', self.tchar, o + C_X)
            if not (x or y) or not any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in boxes):
                continue
            fl = struct.unpack_from('<Q', self.tchar, o + C_FLAGS)[0]
            al = struct.unpack_from('<h', self.tchar, o + C_ALIGN)[0]
            out.append({'t': t, 'name': self.tname(t), 'x': x, 'y': y, 'sprite': self.tchar_sprite(t, 4),
                        'kind': 'merchant' if fl & CF_MERCHANT else 'enemy' if al < 0 else 'friendly'})
        return out

    def clears_save(self, clears, ctl=None):
        qs, npcs = self.talk_load()
        qs['clears'] = {int(c['id']): {'id': int(c['id']), 'exp': max(0, int(c.get('exp', 0))), 'seyan': 1 if c.get('seyan') else 0,
                                       'zone': str(c.get('zone', ''))[:45], 'label': str(c.get('label', ''))[:38],
                                       'npcs': [int(t) for t in c.get('npcs', [])][:64]}
                        for c in clears if 1 <= int(c.get('id', 0)) <= 64 and str(c.get('zone', '')).strip()}
        return self.talk_save(qs, npcs, ctl)

    # --- merchants: .dat/merchants.dat, read by the server (merch.c; console "merchreload")
    MK = (('armor', 1, 1 << 8), ('weapons', 2, (1 << 16) | (1 << 17) | (1 << 18) | (1 << 19) | (1 << 20)), ('magic', 4, 1 << 24), ('other', 8, 1 << 25))

    def class_caps(self):
        """the most a player of each class can have: attributes, hit points / endurance / mana, skills"""
        out = []
        for name, t in CLASS_CAPS:
            r = self.ctemp(t)
            if not r:
                continue
            out.append({'name': name, 'attrib': [r['attrib'][z * 6 + 2] for z in range(5)], 'hp': r['hp'][2], 'end': r['end'][2],
                        'mana': r['mana'][2], 'skill': [r['skill'][z * 6 + 2] for z in range(50)]})
        return out

    def merchants_path(self):
        return os.path.join(self.dat, 'merchants.dat')

    def merchants_file(self):
        out = {}
        try:
            with open(self.merchants_path(), encoding='latin-1') as fh:
                for line in fh:
                    a = line.split()
                    if len(a) < 2 or a[0] not in ('merchant', 'stock') or not a[1].isdigit():
                        continue
                    m = out.setdefault(int(a[1]), {'sell': 0, 'buy': 0, 'gold': 0, 'kinds': -1, 'stock': None})
                    if a[0] == 'stock':
                        m['stock'] = (m['stock'] or []) + [int(v) for v in a[2:] if v.isdigit()]
                    else:
                        for k, v in zip(a[2::2], a[3::2]):
                            if k in ('sell', 'buy', 'gold', 'kinds'):
                                try:
                                    m[k] = int(v)
                                except ValueError:
                                    pass
        except OSError:
            pass
        return out

    def _it_u(self, t, field):
        off, fmt = IT_FIELDS[field]
        return struct.unpack_from(fmt, self.titem, t * ITEM_SIZE + off)[0]

    def merchant_default(self, t):
        """what the game does for a merchant that is not in merchants.dat: his stock and what he buys"""
        r = tpl_read(self.tchar, t * CHAR_SIZE, {'data': CT_FIELDS['data'], 'item': CT_FIELDS['item']})
        st = []
        for v in list(r['data'][:10]) + list(r['item']):
            if 0 < v < MAXTITEM and v not in st:
                st.append(v)
        st.sort(key=lambda v: -self._it_u(v, 'value'))
        d0, kinds = r['data'][0], 0
        if 0 < d0 < MAXTITEM:
            fl = self._it_u(d0, 'flags')
            for _, bit, f in self.MK:
                if fl & f:
                    kinds |= bit
        return st, kinds

    def merchants(self):
        """every merchant template (not the gods' shops), with what he sells and buys"""
        if self.tchar is None:
            return []
        f, where, out = self.merchants_file(), {}, []
        for c in self.npc_world():
            if c[7] == 'merchant' and c[4] not in where:
                where[c[4]] = [c[2], c[3], c[8]]
        for t in range(1, MAXTCHARS):
            o = t * CHAR_SIZE
            if t == 1 or not self.tchar[o + C_USED] or 1180 <= t < 1190 or not self.t_u64(t, C_FLAGS) & CF_MERCHANT:
                continue
            st, kinds = self.merchant_default(t)
            m = f.get(t)
            out.append({'t': t, 'name': self.tname(t), 'sprite': self.tchar_sprite(t), 'where': where.get(t), 'custom': m is not None,
                        'stock': m['stock'] if m and m['stock'] is not None else st, 'dstock': st,
                        'kinds': m['kinds'] if m and m['kinds'] >= 0 else kinds, 'dkinds': kinds,
                        'sell': m['sell'] if m else 0, 'buy': m['buy'] if m else 0, 'gold': m['gold'] if m else 0,
                        'tgold': struct.unpack_from('<i', self.tchar, o + CT_FIELDS['gold'][0])[0]})
        return out

    def merchants_save(self, body, ctl=None):
        """one merchant's settings (or reset: back to the game's own); writes merchants.dat and has the game read it"""
        t = int(body.get('t', 0))
        if not (0 < t < MAXTCHARS) or self.tchar is None or not self.tchar[t * CHAR_SIZE + C_USED] or not self.t_u64(t, C_FLAGS) & CF_MERCHANT:
            return {'error': 'That is not a merchant.'}
        f = self.merchants_file()
        if body.get('reset'):
            f.pop(t, None)
        else:
            st, kinds = self.merchant_default(t)
            stock = [int(v) for v in body.get('stock') or [] if 0 < int(v) < MAXTITEM and self.titem[int(v) * ITEM_SIZE + I_USED]][:240]
            cl = lambda v, hi: max(0, min(int(v or 0), hi))
            m = {'sell': cl(body.get('sell'), 1000), 'buy': cl(body.get('buy'), 1000), 'gold': cl(body.get('gold'), 2000000000),
                 'kinds': cl(body.get('kinds'), 15), 'stock': stock}
            if m['stock'] == st:
                m['stock'] = None              # the game's own list: it follows the NPC's backpack again
            if m['kinds'] == kinds:
                m['kinds'] = -1
            if m['stock'] is None and m['kinds'] < 0 and not m['sell'] and not m['buy'] and not m['gold']:
                f.pop(t, None)
            else:
                f[t] = m
        p = self.merchants_path()
        if os.path.exists(p):
            bk = os.path.join(self.dat, 'mapedit-backups')
            os.makedirs(bk, exist_ok=True)
            shutil.copy2(p, os.path.join(bk, 'merchants-%s.dat' % time.strftime('%Y%m%d-%H%M%S')))
        with open(p + '.tmp', 'w', encoding='latin-1') as fh:
            fh.write('# Merchants (MyV2 Editor, Merchants tab; the server: merch.c, console "merchreload").\n'
                     '# merchant <template> sell <%> buy <%> gold <silver> kinds <1 armor, 2 weapons, 4 magic, 8 other; -1 the game\'s own>\n'
                     '# stock <template> <item templates...> (lines add up, in the shop\'s order). 0 = normal.\n')
            for k in sorted(f):
                m = f[k]
                fh.write('merchant %d sell %d buy %d gold %d kinds %d\n' % (k, m['sell'], m['buy'], m['gold'], m['kinds']))
                if m['stock'] is not None:
                    s = m['stock']
                    if not s:
                        fh.write('stock %d\n' % k)
                    for i in range(0, len(s), 30):
                        fh.write('stock %d %s\n' % (k, ' '.join(str(v) for v in s[i:i + 30])))
        os.replace(p + '.tmp', p)
        msg = 'saved'
        if ctl and server_running():
            r = ctl.console('merchreload', 5)
            msg = 'saved; the game has it now' if r and 'Merchants loaded' in r else 'saved; the game reads it at its next start (it did not answer)'
        return {'msg': msg}

    def quests_order_save(self, order, rewards=None, ctl=None):
        qs, npcs = self.talk_load()
        qs['order'] = {int(t): int(v) for t, v in order.items() if int(v) and 0 < int(t) < MAXTCHARS and -1 <= int(v) <= 30000}
        if rewards is not None:
            cl = lambda v: max(0, min(int(v or 0), 2000000000))
            rk = lambda v: max(-1, min(23, int(-1 if v is None else v)))
            qs['qrew'] = {int(t): {'lim': cl(r.get('lim')), 'first': cl(r.get('first')), 'gold': cl(r.get('gold')),
                                   'st': [[cl(v) for v in (list(x) + [0] * 4)[:4]] for x in (r.get('st') or [])[:7]],
                                   'rmin': rk(r.get('rmin')), 'rmax': rk(r.get('rmax')),
                                   'cls': {str(g): [max(-1, min(49, int(v[0]))), max(-1, min(MAXTITEM - 1, int(v[1])))]
                                           for g, v in (r.get('cls') or {}).items() if str(g) in ('1', '2', '3') and (int(v[0]) >= 0 or int(v[1]) >= 0)}}
                          for t, r in rewards.items() if 0 < int(t) < MAXTCHARS}
        return self.talk_save(qs, npcs, ctl)

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

    # --- area brushes: a floor mix plus scattered trees, plants, rocks... learned from a real area
    AREA_STOP = ('candle', 'shield', 'sign', 'torch', 'lamp', 'street', 'shrine', 'inscription', 'hole', 'door',
                 'chest', 'portal', 'book', 'table', 'chair', 'bed', 'lever', 'statue', 'pentagram', 'grave')

    def area_learn(self, x0, y0, x1, y1, name=''):
        """measure an area: its floors (weights), and how often each loose piece stands on a free tile"""
        x0, x1 = sorted((max(1, int(x0)), min(MAPX - 2, int(x1))))
        y0, y1 = sorted((max(1, int(y0)), min(MAPY - 2, int(y1))))
        with self.lock:
            T = {(x, y): self.tile(x, y) for y in range(y0 - 1, y1 + 2) for x in range(x0 - 1, x1 + 2)}
            blk = lambda x, y: (x, y) in T and T[(x, y)][1] and (T[(x, y)][7] & MF_MOVEBLOCK)
            # wall-like sprites: most of them have blocking pieces on two or more sides (walls run in lines)
            seen, walled = Counter(), Counter()
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    s = T[(x, y)][1]
                    if s and T[(x, y)][7] & MF_MOVEBLOCK:
                        seen[s] += 1
                        if sum(1 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)) if blk(x + dx, y + dy)) >= 2:
                            walled[s] += 1
            walls = {s for s in seen if walled[s] >= 0.5 * seen[s]}
            floors, objs, items, blockers = Counter(), Counter(), Counter(), []
            open_tiles = 0
            for y in range(y0, y1 + 1):
                for x in range(x0, x1 + 1):
                    t = T[(x, y)]
                    if t[1] in walls or t[0] in (0, 1008):
                        continue
                    open_tiles += 1
                    floors[t[0]] += 1
                    if t[1]:
                        objs[(t[1], t[7] & 3)] += 1
                        if t[7] & MF_MOVEBLOCK:
                            blockers.append((x, y))
                    i = t[4]
                    if i and 0 < i < MAXITEM and self.it_u8(i, I_USED):
                        tp = self.it_u16(i, I_TEMP)
                        if not (0 < tp < MAXTITEM) or not self.titem[tp * ITEM_SIZE + I_USED]:
                            continue
                        fl, drv = self.ti_u64(tp, I_FLAGS), self.titem[tp * ITEM_SIZE + I_DRIVER]
                        nm = self.titem[tp * ITEM_SIZE + I_NAME:tp * ITEM_SIZE + I_NAME + 40].split(b'\0')[0].decode('latin-1')
                        if fl & IF_TAKE or drv not in (0, 1, 42) or (drv == 0 and fl & IF_USE) or any(w in nm.lower() for w in self.AREA_STOP):
                            continue
                        items[tp] += 1
                        if fl & IF_MOVEBLOCK:
                            blockers.append((x, y))
            bset = set(blockers)
            close = sum(1 for x, y in blockers if any((x + dx, y + dy) in bset for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy))
            n = max(1, open_tiles)
            scatter = [{'k': 'o', 's': s, 'b': b, 'p': round(c / n, 5), 'n': c} for (s, b), c in objs.most_common() if c >= 2]
            scatter += [{'k': 't', 't': tp, 'p': round(c / n, 5), 'n': c} for tp, c in items.most_common() if c >= 2]
            fl_tot = sum(floors.values()) or 1
            return {'name': name or self.zone((x0 + x1) // 2, (y0 + y1) // 2) or 'New area',
                    'floors': [[f, round(c * 100 / fl_tot, 1)] for f, c in floors.most_common(12) if c * 100 >= fl_tot],
                    'scatter': scatter, 'apart': close < 0.25 * max(1, len(blockers)),
                    'from': [x0, y0, x1, y1], 'tiles': open_tiles, 'walls': sorted(walls)}

    def areas_path(self):
        return os.path.join(self.dat, 'mapedit-areas.json')

    def area_presets(self):
        user = {}
        try:
            user = {a['name']: a for a in json.load(open(self.areas_path(), encoding='utf-8'))}
        except (OSError, ValueError):
            pass
        out = [dict(a, builtin=1) for a in BUILTIN_AREAS if a['name'] not in user]
        own = {a['name'] for a in BUILTIN_AREAS}
        return out + [dict(a, builtin=0, hasdefault=1 if a['name'] in own else 0) for a in user.values()]

    # --- rugs (Floors tab): a rectangle's corners and sides by position, the middle at random
    def rugs_path(self):
        return os.path.join(self.dat, 'mapedit-rugs.json')

    def rugs(self):
        user = []
        try:
            user = json.load(open(self.rugs_path(), encoding='utf-8'))
        except (OSError, ValueError):
            pass
        names = {r['name'] for r in user}
        return [dict(r, builtin=1) for r in BUILTIN_RUGS if r['name'] not in names] + [dict(r, builtin=0) for r in user]

    def rug_save(self, rug=None, delete=None, rename=None):
        try:
            user = json.load(open(self.rugs_path(), encoding='utf-8'))
        except (OSError, ValueError):
            user = []
        if delete:
            user = [r for r in user if r['name'] != delete]
        if rename and rename[0] != rename[1]:
            for r in user:
                if r['name'] == rename[0]:
                    r['name'] = rename[1]
        if rug:
            r = {k: int(rug[k]) for k in RUG_KEYS}
            r['name'] = str(rug['name']).strip()[:40]
            r['fill'] = [[int(a), max(1, int(b))] for a, b in rug.get('fill', []) if int(a)]
            if rug.get('from'): r['from'] = [int(v) for v in rug['from'][:2]]
            user = [u for u in user if u['name'] != r['name']] + [r]
        json.dump(user, open(self.rugs_path(), 'w', encoding='utf-8'), indent=1)
        return self.rugs()

    def rug_learn(self, x0, y0, x1, y1):
        """a rug from the map: the rectangle's corner tiles, its sides (the most common floor on each), its middle"""
        x0, x1, y0, y1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)
        if x1 - x0 < 2 or y1 - y0 < 2:
            return {'error': 'Drag over the whole rug, its border included (at least 3 × 3).'}
        g = lambda x, y: self.tile(x, y)[0]
        most = lambda vals: collections.Counter(vals).most_common(1)[0][0]
        r = {'nw': g(x0, y0), 'ne': g(x0, y1), 'sw': g(x1, y0), 'se': g(x1, y1),
             'n': most([g(x0, y) for y in range(y0 + 1, y1)]), 's': most([g(x1, y) for y in range(y0 + 1, y1)]),
             'w': most([g(x, y0) for x in range(x0 + 1, x1)]), 'e': most([g(x, y1) for x in range(x0 + 1, x1)]),
             'fill': [[a, b] for a, b in collections.Counter(g(x, y) for x in range(x0 + 1, x1) for y in range(y0 + 1, y1)).most_common(8)],
             'from': [x0, y0], 'name': ''}
        return r

    def area_save(self, preset=None, delete=None):
        try:
            user = json.load(open(self.areas_path(), encoding='utf-8'))
        except (OSError, ValueError):
            user = []
        if delete:
            user = [a for a in user if a['name'] != delete]
        if preset:
            keep = ('name', 'floors', 'scatter', 'apart', 'from', 'dens')
            p = {k: preset[k] for k in keep if k in preset}
            user = [a for a in user if a['name'] != p['name']] + [p]
        json.dump(user, open(self.areas_path(), 'w', encoding='utf-8'), indent=1)
        self._areas = None

    def area_get(self, name):
        if getattr(self, '_areas', None) is None:
            self._areas = {a['name']: a for a in self.area_presets()}
        return self._areas.get(name)

    def area_pick(self, pr, x, y, t):
        """what an area brush puts on a free tile: None, ('o', sprite, block) or ('t', template)"""
        if t[1] or t[2] or t[3] or (t[4] and self.it_u8(t[4], I_USED)) or t[7] & MF_MOVEBLOCK or t[0] in (0, 1008):
            return None
        r, acc, dens = random.random(), 0.0, float(pr.get('dens', 1) or 0)
        for e in pr.get('scatter', []):
            if e.get('off'):
                continue
            acc += float(e.get('p', 0)) * dens
            if r < acc:
                if e['k'] == 'o':
                    b = int(e.get('b', 0)); pick = ('o', int(e['s']), b)
                else:
                    tp = int(e['t'])
                    if not (0 < tp < MAXTITEM) or not self.titem[tp * ITEM_SIZE + I_USED]:
                        return None
                    b = 1 if self.ti_u64(tp, I_FLAGS) & IF_MOVEBLOCK else 0; pick = ('t', tp)
                if b & 1 and pr.get('apart'):
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            if not (dx or dy):
                                continue
                            n = self.tile(x + dx, y + dy)
                            if n[7] & MF_MOVEBLOCK:
                                return None
                            i = n[4]
                            if i and 0 < i < MAXITEM and self.it_u8(i, I_USED) and self.it_u64(i, I_FLAGS) & IF_MOVEBLOCK:
                                return None
                return pick
        return None

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
                if k == 'area':               # an area brush: its floor mix, and maybe one of its loose pieces
                    pr = self.area_get(op.get('a', ''))
                    if not pr:
                        msgs.append('no area brush called %s' % op.get('a')); continue
                    if op.get('floor', True) and pr.get('floors'):     # also on the black void (new ground)
                        fs = [f for f in pr['floors'] if not (len(f) > 2 and f[2])] or pr['floors']     # [floor, weight, off]
                        t[0] = int(random.choices([f[0] for f in fs], weights=[max(0.01, float(f[1])) for f in fs])[0])
                        self.set_tile(x, y, t)
                    pick = self.area_pick(pr, x, y, t)
                    if not pick:
                        n += 1; continue
                    if pick[0] == 'o':
                        k, op = 'object', {'op': 'object', 'x': x, 'y': y, 's': pick[1], 'block': pick[2]}
                    else:
                        k, op = 'place', {'op': 'place', 'x': x, 'y': y, 't': pick[1]}
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
                    if 'sprite' in op:          # its look: [closed, open] (a chest's facing)
                        struct.pack_into('<2h', self.item, o + 537, int(op['sprite'][0]), int(op['sprite'][1]))
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
                                'undo': len(world.undo), 'redo': len(world.redo), 'areas': world.areas, 'zonesrc': world.zone_src,
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
            if u.path == '/api/areas':
                return self.js(BUILTIN_AREAS if q.get('defaults') else world.area_presets())
            if u.path == '/api/rugs':
                return self.js(world.rugs())
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
            if u.path == '/api/quests':
                return self.js(world.quests_view())
            if u.path == '/api/merchants':
                return self.js(world.merchants())
            if u.path == '/api/classcaps':
                return self.js(world.class_caps())
            if u.path == '/api/zonenpcs':
                return self.js(world.zone_npcs(q.get('zone', '')))
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
            if u.path == '/api/rugs':
                if body.get('learn'):
                    return self.js(world.rug_learn(*[int(v) for v in body['learn'][:4]]))
                if body.get('save') and not str(body['save'].get('name', '')).strip():
                    return self.js({'error': 'Give the rug a name.'})
                return self.js({'rugs': world.rug_save(body.get('save'), body.get('delete'), body.get('rename'))})
            if u.path == '/api/clears':
                return self.js({'msg': world.clears_save(body.get('clears') or [], ctl)})
            if u.path == '/api/merchants':
                return self.js(world.merchants_save(body, ctl))
            if u.path == '/api/questorder':
                return self.js({'msg': world.quests_order_save(body.get('order') or {}, body.get('rewards'), ctl)})
            if u.path == '/api/zones':
                err = world.zones_save(body.get('zones') or [], ctl)
                if err and err != 'later':
                    return self.js({'error': err})
                n = len({a[4] for a in world.areas})
                return self.js({'areas': world.areas, 'msg': 'Zones saved: %d zones in %d boxes. %s' % (n, len(world.areas),
                                'The game uses them now.' if server_running() and not err else
                                'The game reads them at its next start (the running server is older).' if err else
                                'The game uses them when the server starts.')})
            if u.path == '/api/areas':
                if body.get('learn'):
                    return self.js(world.area_learn(*body['learn'][:4], name=body.get('name', '')))
                if body.get('save') or body.get('delete'):
                    if body.get('save') and not str(body['save'].get('name', '')).strip():
                        return self.js({'error': 'Give the area brush a name.'})
                    world.area_save(body.get('save'), body.get('delete'))
                    return self.js({'msg': 'saved', 'areas': world.area_presets()})
                return self.js({'error': 'nothing to do'})
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
    handler = make_handler(world, sprites, page, a.minimap, ctl)
    httpd = None
    for port in [a.port] + [p for p in range(8090, 8100) if p != a.port]:
        try:
            httpd = ThreadingHTTPServer((a.host, port), handler)
            break
        except OSError as e:          # in use, or reserved by Windows (WSL mirrored networking reserves 8080 on some PCs)
            print('Port %d is not available (%s), trying another.' % (port, e.strerror or e))
    if httpd is None:
        sys.exit('No free port for the editor between 8090 and 8099: start it with --port <number>.')
    a.port = port
    print('MyV2 Editor: open http://localhost:%d in your browser.%s Ctrl+C to quit.' %
          (a.port, ' (The game server is running: view only.)' if server_running() else ''))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        if world.dirty:
            print('\nQuit with unsaved changes - they were not written.')
        print('Bye.')


PAGE = r'''@@PAGE@@'''

if __name__ == '__main__':
    main()
