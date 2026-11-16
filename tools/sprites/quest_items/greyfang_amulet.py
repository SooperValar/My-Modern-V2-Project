"""44521 Greyfang Amulet (Nov 16): the game's Lizard's Teeth Necklace (309) with its teeth made grey wolf teeth and
Old Greyfang's big yellowed fang hanging from the middle on a gold cap."""
import sys, numpy as np; from PIL import Image
a = np.array(Image.open(sys.argv[1]).convert('RGBA'))   # argv[1]: the game's sprite 309 (export_sprites.py), argv[2]: out
a[(a[..., 0] == 255) & (a[..., 1] == 0) & (a[..., 2] == 255), 3] = 0
teeth = (a[..., 3] > 0) & (a[..., :3].mean(-1) > 150)
for x in (14, 15, 16):                              # the middle teeth make room for the fang
    for y in range(25, 32):
        if teeth[y, x]: a[y, x, 3] = 0; teeth[y, x] = False
a[teeth, :3] = (188, 186, 178)
a = np.vstack([a[2:], np.zeros((2, 32, 4), np.uint8)])   # up 2 px: room for the fang
def px(x, y, c): a[y, x] = (*c, 255)
for x in (14, 15, 16): px(x, 24, (225, 185, 60))     # gold cap over the cord
px(15, 25, (170, 130, 35))
L, M, D = (244, 234, 200), (218, 200, 145), (150, 128, 80)
for y in range(25, 30): px(14, y, L); px(16, y, D)
for y in range(26, 30): px(15, y, M)
px(14, 25, (225, 185, 60)); px(16, 25, (170, 130, 35))
px(15, 30, M); px(16, 30, D); px(15, 31, D)            # the tip curls a little right
Image.fromarray(a, 'RGBA').save(sys.argv[2])
