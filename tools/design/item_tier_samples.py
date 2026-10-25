#!/usr/bin/env python3
"""Sample rolls for the item tier design (docs/ITEM_TIERS.md). Not game code.
    item_tier_samples.py [seed]  -> markdown on stdout

Rules used (current draft):
- budget = max(item level, 8) x tier multiplier (Magic 1, Rare 2, Epic 3)
- Magic: 1 bonus (the main attribute or one skill); Rare: main attribute + 1-2 skills;
  Epic: main attribute + secondary + 3 skills. Utility: skills only (1 / 2-3 / 4).
- the main attribute takes about half the budget, the rest is split randomly,
  every other bonus getting at least 20% of that rest
- 1 point = +1/2 attribute (rounded up) or +1 skill
- 10% of Fighter/Mage/Mercenary items have Braveness as main, the usual one secondary (Rare and up)
- hitpoints/endurance/mana per item level (halved even steps), rounded down
- metal from the item level; steel can drop at any level
"""
import random, sys
R = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
FIGHT = ['Hand to Hand','Dagger','Sword','Two-Handed','Two-Handed Axe','Surround Hit','Warcry','Resistance','Immunity','Regenerate','Rest']
MAGE = ['Bless','Enhance Weapon','Protection','Magic Shield','Heal','Blast','Curse','Stun','Ghost Companion','Dispel Magic','Dagger','Resistance','Concentrate','Meditate']
UTIL = ['Perception','Lock-Picking','Bartering','Repair','Light','Identify','Sense Magic','Swimming']
MERC = sorted(set(FIGHT+MAGE))+['Stealth']
PRE = {'Strength':'Strong','Agility':'Nimble','Intuition':'Wise','Willpower':'Willful','Braveness':'Brave','spread':'Balanced'}
SUF = {'Repair':'Mending','Lock-Picking':'Picking','Two-Handed Axe':'Cleaving','Surround Hit':'Sweeping','Ghost Companion':'the Companion','Hand to Hand':'Fists','Enhance Weapon':'Enhancing','Sense Magic':'Sensing','Dispel Magic':'Dispelling','Two-Handed':'Two Hands'}
HEM = {'Fighter':(1.5,1,.5),'Mage':(.5,1,1.5),'Mercenary':(1,1,1),'Utility':(.5,.5,.5)}
MUL = {'Magic':1,'Rare':2,'Epic':3}
EFFECTS = ['Regeneration','Clarity','Stamina','Warding','Light','Night sight','Water breathing','Thorns','Thrift','Wisdom']

def metal(lv):
    opts = ['Steel']
    if lv <= 6: opts += ['Bronze']*2
    if 5 <= lv <= 14: opts += ['Gold']*2
    if 9 <= lv <= 17: opts += ['Emerald']
    if 11 <= lv: opts += ['Crystal']*2
    if 16 <= lv: opts += ['Titanium']
    return R.choice(opts)

def split(total, n):
    """n random parts of total; every part gets at least 20% of total (at least 1)"""
    if n == 0: return []
    mn = max(1, total // 5)
    if mn * n > total: mn = max(1, total // n)
    free = total - mn * n
    cuts = sorted(R.randint(0, free) for _ in range(n-1))
    return [mn + b - a for a, b in zip([0]+cuts, cuts+[free])]

def roll(lv, tier, cat, piece):
    budget = max(lv, 8) * MUL[tier]	# minimum budget 8 (Magic at least +4, like today's modded armor)
    attrs, skills = {}, {}
    pool = {'Fighter':FIGHT,'Mage':MAGE,'Mercenary':MERC,'Utility':UTIL}[cat]
    if cat == 'Utility':
        n = {'Magic':1,'Rare':R.randint(2,3),'Epic':4}[tier]
        for s, p in zip(R.sample(pool, n), split(budget, n)): skills[s] = p
        main = None
    else:
        base = {'Fighter':['Strength','Agility'],'Mage':['Intuition','Willpower'],'Mercenary':['Strength','Agility','Intuition','Willpower','spread']}[cat]
        main = R.choice(base); second = None
        if R.random() < .10:
            second = main if main != 'spread' else R.choice(['Strength','Agility','Intuition','Willpower']); main = 'Braveness'
        if tier == 'Magic':
            if R.random() < .5: attrs[main] = budget
            else: skills[R.choice(pool)] = budget; main = None
        else:
            mp = (budget+1)//2; rest = budget-mp
            attrs[main] = mp
            nsk = R.randint(1,2) if tier == 'Rare' else 3
            parts = []
            if tier == 'Epic':
                if not second:
                    second = 'Braveness' if R.random() < .5 or main == 'spread' else R.choice([a for a in base[:-1] if a != main] if cat=='Mercenary' else [a for a in base if a != main])
                parts = split(rest, nsk+1); attrs[second] = parts.pop(0)
            elif second:	# Braveness main on a Rare: the usual main attribute comes second
                parts = split(rest, nsk+1); attrs[second] = parts.pop(0)
            else:
                parts = split(rest, nsk)
            for s, p in zip(R.sample(pool, nsk), parts): skills[s] = p
    # values
    out = []
    for a, p in attrs.items():
        v = (p+1)//2
        if a == 'spread': out.append('+%d Str/Agi/Int/Wil' % max(1, round(v/2)))
        else: out.append('+%d %s' % (v, a))
    for s, p in sorted(skills.items(), key=lambda x: -x[1]): out.append('+%d %s' % (p, s))
    h, e, m = (int(lv*x*MUL[tier]) for x in HEM[cat])
    hem = '+%d hp, +%d end, +%d mana' % (h, e, m)
    if tier == 'Epic': out.append('effect: %s' % R.choice(EFFECTS))
    # name
    met = metal(lv)
    pre = PRE.get(main, '') if main else ''
    topskill = max(skills, key=skills.get) if skills else None
    suf = ('of ' + SUF.get(topskill, topskill)) if topskill else ''
    if cat == 'Utility': name = '%s Utility %s %s' % (met, piece, suf)
    else: name = ' '.join(x for x in (pre, met, cat, piece, suf) if x)
    if tier == 'Magic' and cat != 'Utility' and attrs and skills: pass
    return name, ', '.join(out), hem

print('# Item tier samples\n')
print('Generated by `tools/design/item_tier_samples.py` with the draft rules in its header. Budget = max(item level, 8) x (Magic 1, Rare 2, Epic 3); 1 point = +1/2 attribute or +1 skill. Legendary items are hand-made, so none here.\n')
for lv in (3, 8, 13, 18):
    print('## Item level %d (needs rank %d)\n' % (lv, lv))
    print('| Tier | Name | Bonuses | Hitpoints / endurance / mana |')
    print('|---|---|---|---|')
    for tier in ('Magic', 'Magic', 'Rare', 'Rare', 'Epic', 'Epic'):
        cat = R.choices(['Fighter','Mercenary','Mage','Utility'], [30,30,30,10])[0]
        piece = R.choice(['Helmet','Armor'])
        n, b, h = roll(lv, tier, cat, piece)
        print('| %s | %s | %s | %s |' % (tier, n, b, h))
    print()
