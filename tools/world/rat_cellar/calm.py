#!/usr/bin/env python3
"""Nov 16 (Cody): the cellar's ratlings leave players alone until one of them is attacked. driver.c: data[43..46] are
the groups an NPC does NOT attack (it attacks everyone else in sight): 0 = it attacks no one by itself. data[59] = 12
(the ratlings' group, data[42]) stays: they help any ratling that is attacked, and fight back when hit.
    calm.py <.dat folder>      (the game stopped: stop-send; then update-world, reload-editor)"""
import sys, os, json, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); DAT = sys.argv[1]
spec = importlib.util.spec_from_file_location('mapedit', os.environ.get('MAPEDIT', os.path.expanduser('~/mnt/Server/mapedit.py')))
me = importlib.util.module_from_spec(spec); spec.loader.exec_module(me)
W = me.World(DAT, os.path.dirname(os.path.abspath(DAT)), os.path.join(DAT, 'mapedit-areas.json'))
M = json.load(open(os.path.join(HERE, 'made.json')))
for t in M['young'] + [M['broodmother']]:
    d = list(me.tpl_read(W.tchar, t * me.CHAR_SIZE, me.CT_FIELDS)['data'])
    d[43] = d[44] = d[45] = d[46] = 0
    assert d[42] == 12 and d[59] == 12, (t, d[42], d[59])
    print(t, W.tname(t), W.apply([{'op': 'ctempset', 't': t, 'fields': {'data': d}, 'respawn': True}], 'calm ' + str(t)))
print(W.save())
