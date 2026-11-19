#!/usr/bin/env python3
"""The Quests page / #quest order (Cody, Nov 18): by the journey - Aston's skill teachers, Aston's other quests, the Eastern
Woods, Fenwatch, Stonehold, then Syleia - and by the lowest rank inside each. Unlisted (-1) quests stay unlisted.
Game stopped:   quest_order.py <.dat folder>"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from arealib import *
ORDER = [25, 50, 28, 64, 90, 91, 109, 108, 342, 343, 107, 111, 363,     # Aston's skill teachers (by exp)
         2141, 1097, 1145, 246,                                         # Mirela; the Spider Queen, the Ghost King, Robin
         2034, 2098, 2035, 2036, 2099, 2100, 'c4',                       # the Eastern Woods (rank 4-7), the Quarry chain
         2142, 2143, 2204, 2147, 2205, 2203, 2144, 2145, 2004,          # Fenwatch (rank 8-10), Robin's second
         2271, 2146, 2272, 2273,                                        # Fenwatch (rank 11)
         2277, 2317, 2280,                                              # Stonehold (rank 12)
         615]                                                           # Syleia (rank 18)
A = Area(sys.argv[1]); qs, _ = A.W.talk_load()
old = {int(t): int(v) for t, v in qs.get('order', {}).items()}
order = {t: -1 for t, v in old.items() if v == -1}
corder = {int(n): int(v) for n, v in qs.get('corder', {}).items()}
k = 0
for e in ORDER:
    k += 1
    if isinstance(e, str): corder[int(e[1:])] = k
    else: order[e] = k
missing = [t for t, v in old.items() if v > 0 and t not in order]
assert not missing, missing
print(A.W.quests_order_save(order, None, None, None, False, corder, None))
