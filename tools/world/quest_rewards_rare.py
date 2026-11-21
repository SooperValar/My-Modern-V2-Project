#!/usr/bin/env python3
"""Quest rewards at Rare strength (Nov 21; Cody: "set them to rare strength but I'd like to redo what bonuses they get" -
his table). Budget = 2 x max(rank, 8): an attribute point costs 2, a skill point 1; plus one of hit points / endurance /
mana at about rank x 3. The Amulet of the Still Mind (28 of 26) and the Rat-Catcher's Ring (8 of 16) stay as Cody set
them; the Scaled Belt and the Belt of the Colossus keep their armor. Three amulets regenerate like the Amulet of Ankh at
half its rate (server: svr_do.c ankh_half): Greyfang hit points only, the Still Mind and Shrike's Eye all three.

    quest_rewards_rare.py <.dat folder> [--dry]

Changes the item templates and every copy already in the world (the bonuses only: names, looks and the rest stay)."""
import sys, os, struct
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'mapedit')); sys.argv_ = sys.argv; sys.argv = ['x']
import mapedit as me
dat = sys.argv_[1]; dry = '--dry' in sys.argv_
W = me.World(dat, os.path.dirname(os.path.abspath(dat)), os.path.join(dat, 'mapedit-areas.json'))
BRA, WIL, INT, AGI, STR = 0, 1, 2, 3, 4
AN = ['Brav', 'Will', 'Int', 'Agil', 'Str']
SK = {'Sword': 3, 'Protection': 17, 'Stealth': 8, 'Bartering': 12, 'Repair': 13, 'Regenerate': 28, 'Meditate': 30, 'Bless': 21,
      'Swimming': 10, 'Resistance': 23, 'Immunity': 32, 'Ghost Companion': 27, 'Two-Handed': 6, 'Rest': 29, 'Enhance Weapon': 18,
      'Blast': 24, 'Greataxe': 36, 'Perception': 9, 'Curse': 20, 'Sense Magic': 31, 'Heal': 26}
# template: rank (for the hit points), attributes, skills, 'hp' / 'end' / 'mana', new description (None: keep)
R = {
 2004: (4, {BRA: 2, AGI: 2}, {'Sword': 4, 'Protection': 2, 'Stealth': 2}, 'hp', None),
 2005: (5, {INT: 2, WIL: 2}, {'Bartering': 4, 'Repair': 4}, 'mana', None),
 2019: (7, {STR: 4}, {'Regenerate': 8}, 'end', "Old Greyfang's fang on a leather thong, set in silver by Huntmaster Edda. It gives its wearer the old wolf's strength, and wounds close even on the hunt."),
 2030: (8, {WIL: 3, INT: 1}, {'Meditate': 4, 'Bless': 2, 'Protection': 2}, 'mana', None),
 2031: (9, {AGI: 3, INT: 2}, {'Swimming': 8}, 'end', None),
 2053: (10, {BRA: 3, STR: 2}, {'Resistance': 5, 'Immunity': 5}, 'hp', None),
 2054: (10, {INT: 3, WIL: 2}, {'Ghost Companion': 5, 'Meditate': 5}, 'mana', "A silver ring with a violet stone, given by Petra the scholar. The spirits come more readily, and the mind rests more deeply, for whoever wears it."),
 2062: (11, {AGI: 4, STR: 2}, {'Two-Handed': 6, 'Rest': 4}, 'hp', None),
 2067: (12, {INT: 4, WIL: 2}, {'Protection': 4, 'Enhance Weapon': 4, 'Blast': 4}, 'mana', "An iron band set with a stone that glows like an ember, forged by Hagar from the Foundry Heart. The spells of whoever wears it burn hotter."),
 2068: (12, {STR: 4, AGI: 2}, {'Greataxe': 6, 'Immunity': 4, 'Repair': 2}, 'hp', None),
 2085: (13, {BRA: 4, AGI: 3}, {'Perception': 6, 'Stealth': 6}, 'end', None),
 2086: (13, {INT: 4, BRA: 4}, {'Meditate': 4, 'Rest': 4, 'Regenerate': 4}, 'mana', None),
 2077: (14, {INT: 4, WIL: 3}, {'Blast': 6, 'Curse': 6, 'Sense Magic': 2}, 'mana', None),
 2081: (15, {BRA: 4, AGI: 4}, {'Sword': 6, 'Protection': 4, 'Enhance Weapon': 4}, 'hp', None),
 2082: (15, {WIL: 4, STR: 4}, {'Heal': 8, 'Resistance': 6}, 'hp', "Shrike's red stone eye in a silver setting, made for Rhea by Hagar. Whoever wears it shrugs off harm and mends quickly."),
 2023: (2, {AGI: 3}, {'Perception': 2}, 'hp', None),
}
F = me.IT_FIELDS
def show(buf, o):
    a = struct.unpack_from(F['attrib'][1], buf, o + F['attrib'][0]); s = struct.unpack_from(F['skill'][1], buf, o + F['skill'][0])
    h = [struct.unpack_from('<3h', buf, o + F[k][0])[0] for k in ('hp', 'end', 'mana')]
    out = ['%+d %s' % (a[i * 3], AN[i]) for i in range(5) if a[i * 3]]
    out += ['%+d %s' % (s[i * 3], next((n for n, v in SK.items() if v == i), 'skill %d' % i)) for i in range(50) if s[i * 3]]
    out += ['%+d %s' % (v, k) for v, k in zip(h, ('HP', 'End', 'Mana')) if v]
    av = struct.unpack_from('2b', buf, o + F['armor'][0])[0]
    if av: out.append('armor %d' % av)
    return ', '.join(out)
def setit(buf, o, spec):
    rank, at, sk, hem, desc = spec
    a = list(struct.unpack_from(F['attrib'][1], buf, o + F['attrib'][0])); s = list(struct.unpack_from(F['skill'][1], buf, o + F['skill'][0]))
    for i in range(5): a[i * 3] = at.get(i, 0)
    for i in range(50): s[i * 3] = 0
    for n, v in sk.items(): s[SK[n] * 3] = v
    struct.pack_into(F['attrib'][1], buf, o + F['attrib'][0], *a); struct.pack_into(F['skill'][1], buf, o + F['skill'][0], *s)
    for k in ('hp', 'end', 'mana'):
        h = list(struct.unpack_from('<3h', buf, o + F[k][0])); h[0] = rank * 3 if k == hem else 0
        struct.pack_into('<3h', buf, o + F[k][0], *h)
    if desc:
        b = desc.encode('latin-1')[:199]; buf[o + 81:o + 281] = b + b'\0' * (200 - len(b))
inst = {}
for k in range(1, me.MAXITEM):
    o = k * me.ITEM_SIZE
    if W.item[o] and struct.unpack_from('<H', W.item, o + me.I_TEMP)[0] in R: inst.setdefault(struct.unpack_from('<H', W.item, o + me.I_TEMP)[0], []).append(k)
for t, spec in R.items():
    o = t * me.ITEM_SIZE; nm = W.titem[o + 1:o + 41].split(b'\0')[0].decode('latin-1')
    before = show(W.titem, o); setit(W.titem, o, spec); after = show(W.titem, o)
    for k in inst.get(t, []): setit(W.item, k * me.ITEM_SIZE, spec)
    print('%-26s r%-2d %s\n%31s-> %s%s' % (nm, spec[0], before, '', after, ('   (+%d in the world)' % len(inst[t])) if t in inst else ''))
if not dry:
    W.touched |= {'titem.dat', 'item.dat'}; print(W.save())
