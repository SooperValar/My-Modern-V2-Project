#!/usr/bin/env python3
"""Male Warrior-Mercenary (template 547) started Immunity and Surround Hit at 3, the female one (552) at 4:
both start at 4 now. Server stopped: python3 warrior_start.py <.dat folder>"""
import sys, os
CHAR_SIZE, SKILL = 3605, 387          # struct character: skill[50][6] at byte 387; [0] = the value it starts with
p = os.path.join(sys.argv[1], 'tchar.dat')
with open(p, 'r+b') as f:
    for t in (547, 552):
        for sk in (32, 33):           # Immunity, Surround Hit
            o = t * CHAR_SIZE + SKILL + sk * 6
            f.seek(o); old = f.read(1)[0]
            if old < 4:
                f.seek(o); f.write(bytes([4]))
            print('template %d skill %d: %d -> %d' % (t, sk, old, max(old, 4)))
