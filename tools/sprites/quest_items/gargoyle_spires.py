#!/usr/bin/env python3
"""Item pictures and the cracked bell for the Gargoyle Spires (Nov 19), into <client>/GFX:
    gargoyle_spires.py <client folder> <3d Models folder>
44551 Gargoyle Horn (drawn: a curved horn of frost-grey stone, darker at the tip), 44552 Spire Bell Clapper (drawn: an
iron rod with a heavy bronze ball, green with verdigris), 44553 Shrike's Eye (drawn: a red stone eye with a black slit,
glowing), 44554 Warden's Girdle (drawn: a coiled belt of dark leather with steel studs and a granite-grey buckle),
44555 Shrike's Eye amulet (drawn: a silver chain, the red slit-eye stone in a silver setting).
World object 38463 the cracked bell (a great bronze bell fallen on its side, green with age, a crack down one side) and
38464 the same (its hide-walls copy: it is low); 38465 the bell frame it fell from (two timber posts, a beam, a broken
chain), 38466 its hide-walls form (stumps). Next free object: 38467."""
import os, subprocess, sys, math, random
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); C, M = sys.argv[1], sys.argv[2]
G = os.path.join(C, 'GFX'); ICON = os.path.join(HERE, '..', 'item_icon.py'); R2 = os.path.join(M, 'RPG Pack 2', 'OBJ')
def icon(nr, model, *a): subprocess.run([sys.executable, ICON, model, os.path.join(G, '%05d.png' % nr)] + [str(x) for x in a], check=True)
def clamp(c, a=255): return tuple(max(0, min(255, int(v))) for v in c) + (a,)
def outline(im, col=(20, 20, 24)):
    """a one-pixel dark outline round the shape (the game's items have one)"""
    px = im.load(); W, H = im.size; edge = []
    for y in range(H):
        for x in range(W):
            if px[x, y][3]: continue
            if any(0 <= x + dx < W and 0 <= y + dy < H and px[x + dx, y + dy][3] > 128 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))): edge.append((x, y))
    for x, y in edge: px[x, y] = col + (255,)
    return im

# ---- 44551 Gargoyle Horn: a curved horn lying on the ground, thick at the root, curling up to a point
im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load(); r = random.Random(44551)
for i in range(400):
    t = i / 399.0
    a = math.pi * (1.05 - 0.95 * t)                                  # the curve
    cx, cy = 15 + 10 * math.cos(a), 22 - 9 * math.sin(a) * (0.4 + 0.6 * t)
    w = 4.2 * (1 - t) ** 0.8 + 0.4
    for oy in range(-6, 7):
        for ox in range(-6, 7):
            if ox * ox + oy * oy > w * w: continue
            x, y = int(round(cx + ox)), int(round(cy + oy))
            if not (0 <= x < 32 and 0 <= y < 32): continue
            lit = 0.75 + 0.35 * (-ox - oy) / max(w, 1) / 1.4
            ring = 0.88 if int(t * 14) % 2 == 0 and t < 0.75 else 1.0        # growth ridges
            base = [168, 170, 176] if t < 0.7 else [168 - 150 * (t - 0.7), 170 - 150 * (t - 0.7), 176 - 140 * (t - 0.7)]
            px[x, y] = clamp([v * lit * ring * (0.95 + 0.1 * r.random()) for v in base])
outline(im).save(os.path.join(G, '44551.png'))

# ---- 44552 Spire Bell Clapper: a dark iron rod with a ring at the top and a heavy ball at the foot, bronze gone green
im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load(); r = random.Random(44552)
for y in range(32):
    for x in range(32):
        # lying diagonally: the rod from (8,8) to (19,19), the ball centred (22,22)
        t = ((x - 8) + (y - 8)) / 22.0; d = abs((x - 8) - (y - 8)) / 1.414
        if 0 <= t <= 0.62 and d <= 1.3:
            lit = 0.8 + 0.4 * ((x - y) / 3.0 * -1 + 0.5) / 2
            px[x, y] = clamp([64 * lit, 66 * lit, 72 * lit])
        rr = math.hypot(x - 21.5, y - 21.5)
        if rr <= 6.2:
            lit = 0.65 + 0.5 * (-(x - 21.5) - (y - 21.5)) / 12.4
            c = [150, 108, 48] if r.random() > 0.35 + 0.25 * ((x + y) % 3 == 0) else [74, 150, 122]      # bronze, verdigris
            if rr < 2.2 and x < 21 and y < 21: c = [230, 200, 140]                                        # a worn bright spot
            px[x, y] = clamp([v * lit for v in c])
        rr = math.hypot(x - 7, y - 7)
        if 1.4 <= rr <= 3.0: px[x, y] = clamp([88, 90, 96])                                              # the ring
outline(im).save(os.path.join(G, '44552.png'))

# ---- 44553 Shrike's Eye: a red stone eye, a black slit, a glow round it
im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load()
for y in range(32):
    for x in range(32):
        dx, dy = (x - 15.5) / 8.0, (y - 18.5) / 7.0; rr = math.hypot(dx, dy)
        if rr <= 1.0:
            lit = 1.0 - 0.45 * rr + 0.35 * max(0, -dx * 0.5 - dy * 0.7)
            c = [235 * lit, 40 * lit, 30 * lit]
            if abs(dx) < 0.14 * (1 - dy * dy) ** 0.5 + 0.02: c = [18, 4, 6]                                  # the slit
            if math.hypot(dx + 0.38, dy + 0.42) < 0.18: c = [255, 230, 210]                                  # the glint
            px[x, y] = clamp(c)
        elif rr <= 1.35: px[x, y] = clamp([255, 60, 40], int(150 * (1.35 - rr) / 0.35))                     # the glow
im.save(os.path.join(G, '44553.png'))

# ---- 44554 Warden's Girdle: a coiled belt of dark leather, steel studs, a granite-grey buckle
im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load()
for y in range(32):
    for x in range(32):
        dx, dy = (x - 15.5) / 12.5, (y - 19.5) / 7.5; rr = math.hypot(dx, dy)
        if 0.62 <= rr <= 1.0:
            lit = 0.72 + 0.30 * (-dx * 0.6 - dy * 0.8) / max(rr, 0.01) * (0.5 if rr < 0.8 else 1.0)
            if rr > 0.93 or rr < 0.67: lit *= 0.6
            c = (70, 48, 34) if dy < 0 else (86, 60, 42)
            a = math.atan2(dy, dx)
            if abs(rr - 0.81) < 0.07 and int((a + 4) * 4.5) % 2 == 0 and abs(math.sin(a * 9)) > 0.75: c, lit = (196, 200, 210), 1.0   # studs
            px[x, y] = clamp([v * lit for v in c])
for y in range(22, 30):                                              # the buckle, on the near side
    for x in range(11, 21):
        edge = x in (11, 20) or y in (22, 29); inner = 13 <= x <= 18 and 24 <= y <= 27
        if edge or not inner:
            lit = 1.15 if (x < 15 and y < 26) else 0.85
            px[x, y] = clamp([138 * lit, 140 * lit, 146 * lit])
        else: px[x, y] = clamp([60, 42, 30])
for y in range(24, 28): px[16, y] = clamp([210, 214, 222])           # the tongue
outline(im).save(os.path.join(G, '44554.png'))

# ---- 44555 Shrike's Eye amulet
im = Image.new('RGBA', (32, 32), (0, 0, 0, 0)); px = im.load()                       # drawn (Necklace2 came out too thin)
for i in range(90):                                                  # the chain: silver links round an ellipse
    a = 2 * math.pi * i / 90; x, y = 15.5 + 9.5 * math.cos(a), 15 + 7 * math.sin(a)
    if math.sin(a) > 0.93: continue                                  # open at the bottom, where the pendant hangs
    c = [200, 204, 214] if i % 3 else [120, 124, 134]
    px[int(round(x)), int(round(y))] = clamp(c)
for y in range(32):                                                  # the pendant: a silver setting, the red slit-eye stone
    for x in range(32):
        dx, dy = (x - 15.5) / 5.2, (y - 24.0) / 4.6; rr = math.hypot(dx, dy)
        if rr <= 1.0:
            if rr > 0.72: px[x, y] = clamp([190 - 60 * dy, 194 - 60 * dy, 204 - 60 * dy])
            else:
                lit = 1.0 - 0.4 * rr + 0.3 * max(0, -dx * 0.5 - dy * 0.7); c = [235 * lit, 40 * lit, 30 * lit]
                if abs(dx) < 0.12: c = [18, 4, 6]
                if math.hypot(dx + 0.3, dy + 0.35) < 0.16: c = [255, 230, 210]
                px[x, y] = clamp(c)
for y in (17, 18, 19): px[15, y] = clamp([200, 204, 214]); px[16, y] = clamp([140, 144, 152])
outline(im).save(os.path.join(G, '44555.png'))

# ---- 38463 / 38464 the cracked bell, fallen on its side: the mouth toward the viewer (down-left), green-bronze
W, H = 48, 48; im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); px = im.load(); r = random.Random(38463)
ax, ay = 0.85, 0.48                                                  # the bell's axis on screen (crown -> mouth), down-left... flipped below
for y in range(H):
    for x in range(W):
        # local coords along the axis (u: 0 crown .. 1 mouth) and across it (v)
        X, Y = x - 31.0, y - 26.0                                    # the crown at (31,26), the mouth toward (13,38)
        u = (-X * ax + Y * ay) / 21.0; v = (X * ay + Y * ax) / 1.0
        if not (0 <= u <= 1.0): continue
        rad = 5.5 + 7.5 * u ** 1.6 + (1.6 if u > 0.9 else 0)       # the flare and the lip
        if abs(v) > rad: continue
        s = v / rad                                                  # -1..1 across
        lit = 0.62 + 0.45 * (1 - abs(s + 0.35)) - 0.15 * u
        c = [150, 110, 50]
        if r.random() < 0.35 + 0.3 * (s > 0.2): c = [70, 146, 118]                                 # verdigris
        if abs(u - 0.82) < 0.025 or abs(u - 0.3) < 0.02: lit *= 0.7                              # bands
        if u > 0.97: lit *= 0.75
        if abs(s - 0.1 + 0.25 * u) < 0.05 and u > 0.35: c, lit = [24, 18, 12], 1                 # the crack
        px[x, y] = clamp([v_ * lit for v_ in c])
# the dark mouth: an ellipse at the open end
for y in range(H):
    for x in range(W):
        dx, dy = x - 12.5, y - 36.5
        e = (dx * ax - dy * ay) ** 2 / 2.4 ** 2 + (dx * ay + dy * ax) ** 2 / 13.5 ** 2
        if e <= 1: px[x, y] = clamp([18, 22, 20]) if e < 0.7 else clamp([110, 92, 52])
im = outline(im)
canvas = Image.new('RGBA', (64, 64), (0, 0, 0, 0)); canvas.alpha_composite(im, (8, 64 - 48 - 6))    # 32-px blocks (the client draws them centred, on the bottom edge)
for n in (38463, 38464): canvas.save(os.path.join(G, '%d.png' % n))
# ---- 38465 the bell frame the bell fell from (Cody: "some kind of frame that the bell used to hang from"): two heavy
# timber posts with iron bands, a crossbeam along the map's y (screen up-right) and braces, a broken chain from the beam's
# middle. Stands on the tile behind the fallen bell. 38466: its hide-walls form (the posts cut down to stumps).
from PIL import ImageDraw
def frame(low=False):
    W, H = 64, 96; im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); r = random.Random(38465)
    WOOD, DARK, LIGHT, IRON = (92, 66, 44), (54, 38, 26), (128, 96, 66), (70, 72, 78)
    posts = [(18, 87), (46, 73)]                                      # post feet: one map step along y = (+28, -14)... a short frame
    top = 22 if not low else 74                                       # the posts' tops (low: stumps)
    for (fx, fy) in posts:
        ty = fy - (87 - top)
        d.polygon([(fx - 4, fy), (fx - 4, ty), (fx, ty - 2), (fx, fy + 2)], fill=WOOD)            # the post's left (lit) face
        d.polygon([(fx, fy + 2), (fx, ty - 2), (fx + 4, ty), (fx + 4, fy)], fill=DARK)            # its right face
        d.polygon([(fx - 4, ty), (fx, ty - 2), (fx + 4, ty), (fx, ty + 2)], fill=LIGHT)           # its top
        for k in range(ty + 6, fy - 2, 9):                                                          # grain
            d.line([(fx - 3, k), (fx - 1, k + 1)], fill=DARK)
        for by in ((fy - 6), (ty + 8)) if not low else ((fy - 6),):                                  # iron bands
            if by > ty: d.line([(fx - 4, by), (fx, by + 2), (fx + 4, by)], fill=IRON, width=2)
    if not low:
        (ax, ay), (bx, by_) = (posts[0][0] - 6, top - 3), (posts[1][0] + 6, top - 3 - 14)          # the crossbeam
        d.polygon([(ax, ay), (bx, by_), (bx, by_ + 6), (ax, ay + 6)], fill=WOOD)
        d.polygon([(ax, ay), (bx, by_), (bx + 3, by_ - 2), (ax + 3, ay - 2)], fill=LIGHT)
        d.line([(ax, ay + 6), (bx, by_ + 6)], fill=DARK)
        for (fx, fy), sgn in zip(posts, (1, -1)):                                                   # braces
            px0, py0 = fx + 4 * sgn, top + 10 - (0 if sgn > 0 else 14)
            d.line([(px0, py0), (px0 + 8 * sgn, py0 - 9 - (7 if sgn > 0 else -7) * 0)], fill=DARK, width=3)
        mx, my = (ax + bx) // 2, (ay + by_) // 2 + 6                                                # the broken chain
        for k in range(4):
            cy = my + 2 + k * 4; cx = mx + (1 if k % 2 else 0)
            d.ellipse([cx - 1, cy - 2, cx + 2, cy + 2], outline=IRON if k < 3 else (110, 112, 120))
        d.line([(mx + 2, my + 18), (mx + 4, my + 20)], fill=(110, 112, 120))                        # the snapped last link
    else:
        for (fx, fy) in posts:                                                                        # splintered tops
            for k in range(-3, 4, 2): d.point((fx + k, top - 2 - r.randrange(3)), fill=LIGHT)
    return outline(im)
frame().save(os.path.join(G, '38465.png')); frame(low=True).save(os.path.join(G, '38466.png'))
print('gargoyle spires pictures: 44551-44555, 38463-38466')
