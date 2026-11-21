#!/usr/bin/env python3
"""First kills for every enemy type (Nov 20; Cody: "every enemy type should have an FK" - and the original game's
enemies without one too). "You just killed your first <class name>" pays do_char_score * 25 exp once per class.

    first_kills.py <.dat folder> [--dry]

Every enemy (alignment < 0, not a player) template and NPC:
  - an original monster (template below 2004) that already has a class keeps it (the game's own grouping); one
    without a class takes the class its namesakes among the originals have, if any;
  - our new ones (2004 on) and every one without a class get the class of their NAME: a name that is one of the game's
    own class names (helper.c npc_class: "Lizard Knight", "Flame", "Thief"...) takes that one; any other name a class
    of its own, numbered from 128 (kept in firstkill.dat by the server; 77-127 are
    left alone), named in npctalk.dat as "fk <class> <name>".
New monsters made later: the same rule (rerun this, or arealib's monster() gives a new name its own class)."""
import sys, os, re, struct, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'mapedit')); sys.argv_ = sys.argv; sys.argv = ['x']
import mapedit as me
dat = sys.argv_[1]; dry = '--dry' in sys.argv_
W = me.World(dat, os.path.dirname(os.path.abspath(dat)), os.path.join(dat, 'mapedit-areas.json'))
CLS = 1549; CF_PLAYER = 1 << 5; FIRST_NEW = 128; ORIG_LAST = 2003
src = open(os.path.join(ROOT, 'server', 'helper.c'), encoding='latin-1').read()
builtin = {}
for m in re.finditer(r'\{"([^"]*)"\},?\s*//\s*(\d+)', src[src.index('struct npc_class npc_class[]'):]):
    if m.group(1): builtin.setdefault(m.group(1), int(m.group(2)))
qs, npcs = W.talk_load(); fks = {int(k): v for k, v in (qs.get('fks') or {}).items()}
byname_fk = {v: k for k, v in fks.items()}

def rows(buf, maxn):
    for k in range(1, min(maxn, len(buf) // me.CHAR_SIZE)):
        o = k * me.CHAR_SIZE
        if not buf[o]: continue
        if struct.unpack_from('<h', buf, o + me.C_ALIGN)[0] >= 0: continue
        if struct.unpack_from('<Q', buf, o + me.C_FLAGS)[0] & CF_PLAYER: continue
        nm = buf[o + 1:o + 40].split(b'\0')[0].decode('latin-1').strip()
        if nm: yield k, o, nm
tpl = list(rows(W.tchar, me.MAXTCHARS)); chs = list(rows(W.char, me.MAXCHARS))
names = sorted({nm for _, _, nm in tpl} | {nm for _, _, nm in chs})
nxt = max([FIRST_NEW - 1] + list(fks)) + 1
def newclass(nm):
    global nxt
    if nm in builtin: return builtin[nm], 'game class'
    if nm in byname_fk: return byname_fk[nm], 'own'
    fks[nxt] = nm; byname_fk[nm] = nxt; nxt += 1; return nxt - 1, 'NEW'
# a template: an original one (below 2004) that has a class keeps it (the game's own grouping, e.g. weak / strong
# skeletons); our new ones and every one without a class: the class of its name
want_t, why = {}, {}
oc = collections.defaultdict(collections.Counter)      # the classes the original templates of each name have
for k, o, nm in tpl:
    c = struct.unpack_from('<i', W.tchar, o + CLS)[0]
    if k <= ORIG_LAST and c > 0: oc[nm][c] += 1
for k, o, nm in tpl:
    c = struct.unpack_from('<i', W.tchar, o + CLS)[0]
    if k <= ORIG_LAST and c > 0: want_t[k] = c; why.setdefault(nm, set()).add('kept')
    elif k <= ORIG_LAST and oc[nm]: want_t[k] = oc[nm].most_common(1)[0][0]; why.setdefault(nm, set()).add('like its namesakes')
    else: want_t[k], w = newclass(nm); why.setdefault(nm, set()).add(w)
# Cody (Nov 20): a name that spans many ranks with one first kill (the Towers' Swindlers, Mages, Archmages, the
# pentagram Sea Golems...) is split in strength tiers like the game's own ("Weak Spider", "Spider", "Strong Spider"):
# 3-4 ranks apart: normal / Strong; 5-8: Weak / normal / Strong; 9 and more: Weak / normal / Strong / Very Strong.
# The tier comes from each template's own rank within the ranks that name has in the world.
TIERS = {2: ['', 'Strong'], 3: ['Weak', '', 'Strong'], 4: ['Weak', '', 'Strong', 'Very Strong']}
tr = lambda k: me.points2rank(struct.unpack_from('<i', W.tchar, k * me.CHAR_SIZE + 709)[0])
live = collections.Counter(struct.unpack_from('<H', W.char, o + me.C_TEMP)[0] for _, o, _ in chs)
byname = collections.defaultdict(list)        # the original templates of a name and our new ones apart (Sea Golem:
for k, o, nm in tpl: byname[(nm, k <= ORIG_LAST)].append(k)       # the pentagram ones tiered, the Flooded Chapel's not)
tiered = {}
for (nm, _), ks in byname.items():
    if nm.split()[0] in ('Weak', 'Strong', 'Very'): continue
    inw = [k for k in ks if live[k]] or ks
    rs = [tr(k) for k in inw]; span = max(rs) - min(rs)
    if span < 3 or len({want_t[k] for k in inw}) > 1: continue
    n = 2 if span <= 4 else 3 if span <= 8 else 4
    for k in ks:
        i = max(0, min(n - 1, (tr(k) - min(rs)) * n // (span + 1)))
        tn = (TIERS[n][i] + ' ' + nm).strip()
        want_t[k], w = newclass(tn); why.setdefault(nm, set()).add('tiers'); tiered.setdefault(nm, set()).add(tn)
changed = collections.Counter(); final = collections.defaultdict(set)
for k, o, nm in tpl:
    if struct.unpack_from('<i', W.tchar, o + CLS)[0] != want_t[k]:
        struct.pack_into('<i', W.tchar, o + CLS, want_t[k]); changed['templates'] += 1
    final[nm].add(want_t[k])
for k, o, nm in chs:          # an NPC in the world: its template's class (no template: by its name)
    tp = struct.unpack_from('<H', W.char, o + me.C_TEMP)[0]
    c = want_t.get(tp)
    if c is None: c, w = newclass(nm); why.setdefault(nm, set()).add(w)
    if struct.unpack_from('<i', W.char, o + CLS)[0] != c:
        struct.pack_into('<i', W.char, o + CLS, c); changed['npcs'] += 1
    final[nm].add(c)
cname = lambda c: fks.get(c) or next((n for n, v in builtin.items() if v == c), '?')
for nm in names: print('  %-30s %s   %s' % (nm, ', '.join('%d %s' % (c, cname(c)) for c in sorted(final[nm])), '/'.join(sorted(why.get(nm, ())))))
print('split in tiers:', {k: sorted(v) for k, v in sorted(tiered.items())})
print('%d enemy names; new first kills %d (classes %d-%d); changed: %s' % (len(names), sum(1 for c in fks if c >= FIRST_NEW), FIRST_NEW, nxt - 1, dict(changed)))
# Cody (Nov 20): a named one-of-a-kind enemy says "You killed Red Harlan for the first time": a class with exactly one
# placed template (a spawn spot) and at most one NPC of it in the world -> "fkone <class>"
placed = collections.Counter(); inworld = collections.Counter()
for k, o, nm in tpl:
    x, y = struct.unpack_from('<hh', W.tchar, o + me.C_X)
    if x or y: placed[struct.unpack_from('<i', W.tchar, o + CLS)[0]] += 1
for k, o, nm in chs: inworld[struct.unpack_from('<i', W.char, o + CLS)[0]] += 1
one = sorted(c for c in set(placed) | set(inworld) if c > 0 and placed[c] <= 1 and inworld[c] <= 1 and (placed[c] or inworld[c]))
# a proper name ("Red Harlan", "Barrow King Ulfgar", "James") as it is; a title ("Broodmother", "Tower Guard") with "the"
GENERIC = set('''Bandit Quartermaster Poisoner Prime Golem Deep Grolm Chieftain Sea Sentinel Hag Wight Scribe Barrow Hatchery
Archmage Forgemaster Brass Colossus Flame Lord Gargoyle Bellkeeper Broodmother Fallen Abbot Ratling Duke Prince King Greenling
Tower Guard Warrior Sorceress Arch-Templar Seyan'Du Priest Mad Hermit Amazon Swordsman Swindler Mage Weak Strong Very Old
Master Captain Red the of Bog Witch Cinder'''.split())
proper = lambda n: any(w not in GENERIC for w in n.split())
fkn = set(fks.values())        # a strength tier of a repeated type ("Strong Amazon", and "Amazon" itself) is not one of a kind
tiers_all = {n for n in fkn if n.split()[0] in ('Weak', 'Strong', 'Very')} | {n for n in fkn if 'Strong ' + n in fkn or 'Weak ' + n in fkn}
one = [(c, '' if proper(cname(c)) else 'the') for c in one if cname(c) not in tiers_all]
print('one of a kind (%d):' % len(one), ', '.join(('the ' if a else '') + cname(c) for c, a in one))
if not dry:
    qs['fks'] = fks; qs['fkone'] = one; W.talk_save(qs, npcs)
    W.touched |= {'tchar.dat', 'char.dat'}       # the class is written straight into the buffers: save() must write them (Nov 20: it didn't)
    print(W.save())
