"""Nov 16 (Cody): the shrine's sides turn with it. The game's shrine (S) shows its decorated gold front on the left face
and its shadowy side on the right. Turned (the front towards the wall named): W shows a plain side (left) and the front
(right); N shows the plain back (left) and the other plain side (right); E shows the shadowy side (left) and the plain
back (right). So only S and E show the shadowy side. Right faces are a little darker (the game's light, upper left).
The tops (statue, bowl): Cody's drawings for the temple shrine, the generated ones for the Seyan'Du shrine."""
import sys, random, numpy as np
from PIL import Image
exec(open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), 'wall_decor_shrines_base.py')).read().split("for i, s in enumerate((792, 914)):")[0])
random.seed(11)
def faces(base, orig, left, right):
    out = base.copy(); m = orig[..., 3] > 0; mi = orig[:, ::-1]
    plain = plain_left(orig)
    src_l = {'front': orig, 'shadow': mi, 'plain': plain}[left]
    src_r = {'front': mi, 'shadow': orig, 'plain': plain[:, ::-1]}[right]
    out[LF & m] = src_l[LF & m]
    k = 1.0 if right == 'shadow' else .78
    r = src_r.copy(); r[..., :3] *= k
    out[RF & m] = r[RF & m]
    return out
for i, s in enumerate((792, 914)):
    a = ld(s)
    for j, (left, right) in enumerate((('front', 'front'), ('front', 'front'), ('shadow', 'front'))):   # W, N, E: the shiny side everywhere but the shadowy one (Cody)
        n = 48020 + 3 * i + j
        top = np.array(Image.open('out/%05d.png' % n).convert('RGBA')).astype(float)
        save(n, faces(top, a, left, right))
print('ok')
