#!/usr/bin/env python3
"""Set an NPC's text line in its template and in the living NPCs of that template (server stopped):
    npc_text.py <.dat folder> <template> <line 0-9> <text...>
Line 2 is the greeting / #quest hint; {skill} = the skill it teaches that player (class rewards), {item} = what it wants."""
import sys, os, struct
CHAR_SIZE, C_USED, C_TEMP, CT_TEXT = 3605, 0, 319, 2005
dat, t, line, text = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), ' '.join(sys.argv[4:])
b = text.encode('latin-1')[:159]; b += b'\0' * (160 - len(b))
with open(os.path.join(dat, 'tchar.dat'), 'r+b') as f:
    f.seek(t * CHAR_SIZE + CT_TEXT + line * 160); f.write(b)
n = 0
with open(os.path.join(dat, 'char.dat'), 'r+b') as f:
    d = f.read()
    for c in range(len(d) // CHAR_SIZE):
        o = c * CHAR_SIZE
        if d[o + C_USED] and struct.unpack_from('<H', d, o + C_TEMP)[0] == t:
            f.seek(o + CT_TEXT + line * 160); f.write(b); n += 1
print('template %d line %d set; %d living NPC(s) updated' % (t, line, n))
