#!/usr/bin/env python3
"""A new animated monster for the game from a rigged, animated glTF model (Nov 15; first one: the Quaternius wolf, CC0).
Renders all 448 frames of a character sprite set with glrender.py (the game's camera, 64x64):
    base+  0..63    standing, 8 directions x 8 (the client shows frame 0 of each)
    base+ 64..127   walking, 8 directions x 8 (one walk cycle per tile)
    base+128..191   the 16 turns, 4 frames each (the in-between angles)
    base+192..447   8 actions x 4 directions (up, down, left, right) x 8 frames (attacks, use, pick up...)
Direction order everywhere: up, down, left, right, left-up, left-down, right-up, right-down.

    make_creature.py <model.gltf> <base> <out folder> [--length px] [--preview file.png]
"""
import sys, os, json
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glrender import Model, render, fur

# screen facing of each game direction: 0 = towards the viewer, + = turned to screen right
YAW = {'up': -45, 'down': 135, 'left': -135, 'right': 45, 'leftup': -90, 'leftdown': 180, 'rightup': 0, 'rightdown': 90}
DIRS = ['up', 'down', 'left', 'right', 'leftup', 'leftdown', 'rightup', 'rightdown']
TURNS = [('up', 'leftup'), ('leftup', 'left'), ('up', 'rightup'), ('rightup', 'right'), ('down', 'leftdown'), ('leftdown', 'left'),
         ('down', 'rightdown'), ('rightdown', 'right'), ('left', 'leftup'), ('leftup', 'up'), ('left', 'leftdown'), ('leftdown', 'down'),
         ('right', 'rightup'), ('rightup', 'up'), ('right', 'rightdown'), ('rightdown', 'down')]     # from svr_act.c act_turn_*
# the 8 action slots (client stattab): 0, 2, 3 are attacks; 1 picking up / dropping; 4-7 use, give, bow, magic...
ACTIONS = {0: 'Attack', 1: 'Eating', 2: 'Attack', 3: 'Attack', 4: 'Attack', 5: 'Idle_HitReact1', 6: 'Eating', 7: 'Attack'}


def turn_yaw(a, b, f):
    ya, yb = YAW[a], YAW[b]
    d = (yb - ya + 180) % 360 - 180
    return ya + d * f


def main():
    src, base, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    length = float(sys.argv[sys.argv.index('--length') + 1]) if '--length' in sys.argv else 46
    m = Model(src)
    for mat in m.J['materials']:      # flat colours are linear: to sRGB
        pb = mat.setdefault('pbrMetallicRoughness', {})
        pb['baseColorFactor'] = [c ** (1 / 2.2) for c in pb.get('baseColorFactor', [1, 1, 1, 1])[:3]] + [1]
    P, N, C = m.triangles('Idle', 0)
    lo, hi = P.reshape(-1, 3).min(0), P.reshape(-1, 3).max(0)
    L = max(hi[0] - lo[0], hi[2] - lo[2]); cx, cz = (lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2
    sc = length / L
    fix = lambda P: P - np.array([cx, lo[1], cz])
    tex = fur(3.0, 0.35)
    R = lambda anim, t, yaw: render(m, anim, t, yaw=yaw, scale=sc, fix=fix, tex=tex)
    ln = {a: m.anim_length(a) for a in m.anims}
    os.makedirs(out, exist_ok=True)
    frames = {}
    for d, dn in enumerate(DIRS):
        for f in range(8):
            frames[d * 8 + f] = R('Idle', ln['Idle'] * f / 8, YAW[dn])
            frames[64 + d * 8 + f] = R('Walk', ln['Walk'] * f / 8, YAW[dn])
    for k, (a, b) in enumerate(TURNS):
        for f in range(4):
            frames[128 + k * 4 + f] = R('Idle', 0, turn_yaw(a, b, (f + 1) / 5))
    for act, anim in ACTIONS.items():
        for d, dn in enumerate(DIRS[:4]):
            for f in range(8):
                frames[192 + act * 32 + d * 8 + f] = R(anim, ln[anim] * f / 8, YAW[dn])
    for k, im in frames.items():
        im.save(os.path.join(out, '%05d.png' % (base + k)))
    print('%d frames: %d..%d' % (len(frames), base, base + max(frames)))
    if '--preview' in sys.argv:
        rows = [[frames[d * 8] for d in range(8)], [frames[64 + 24 + f] for f in range(8)], [frames[192 + 8 + f] for f in range(8)],
                [frames[128 + k * 4 + 1] for k in range(8)]]
        sh = Image.new('RGBA', (66 * 8, 66 * len(rows)), (60, 60, 70, 255))
        for r, row in enumerate(rows):
            for k, i in enumerate(row): sh.paste(i, (k * 66, r * 66), i)
        sh.resize((sh.width * 3, sh.height * 3), Image.NEAREST).save(sys.argv[sys.argv.index('--preview') + 1])


if __name__ == '__main__':
    main()
