"""Nov 16, second pass (Cody: the mirrors looked horrible, the shrines unchanged): round-mirror backs as wooden boards
like the pictures (48010, 48011); shrines turned whole (48020, 48023: the gold front faces down-right) and from behind with a
plain gold back panel and the statue turned in shadow (48021-48022, 48024-48025). Run after wall_decor.py, same args.
"""
import sys, random, numpy as np
from PIL import Image
sys.argv=['x','.','out']
src=open('wall_decor.py').read().split('S = {}')[0]
exec(src)
random.seed(5)
def top_mask(a):
    h, w = a.shape[:2]; t = np.zeros((h, w), bool)
    for x in range(w):
        yf = 30 + 0.5 * x if x < 16 else 38 - 0.5 * (x - 16)
        t[:int(yf), x] = True
    return t
def save(n,a): Image.fromarray(np.clip(a,0,255).astype(np.uint8),'RGBA').save('out/%05d.png'%n)
# round mirrors: a solid wooden back, like the pictures' backs (darker rim, a round batten)
def round_back(a):
    b=board(a, base=(96,64,38), rim=(54,34,20))
    m=op(a); ys,xs=np.nonzero(m); cy=(ys.min()+ys.max())/2
    for y,x in zip(ys,xs):
        if abs(y-cy)<1.0 and not edge(m)[y,x]: b[y,x,:3]=(64,42,24)     # the cross batten
    return b
save(48010, shift(round_back(ld(16553)), -16, 8, 64))
save(48011, shift(round_back(ld(16552)), 16, 8, 64))
# shrines: W = the whole shrine turned (its gold front now faces down-right); from behind = a plain gold back panel
# where the decorated front was, the dark side as it is, the statue turned and in shadow
def plain_front(a):
    out=a.copy()
    for y in range(64):
        for x in range(16):
            yf=30+0.5*x; yb=56+0.5*x
            if yf+1<y<yb-1 and a[y,x,3]>0:
                edge_px = x<1 or y<yf+2.5 or y>yb-2.5
                g=random.uniform(.92,1.04)
                out[y,x,:3]=(150,128,0) if edge_px else (205*g,176*g,0)
    return out
for k,(s,name) in enumerate(((792,'temple'),(914,'seyan'))):
    a=ld(s); t=top_mask(a)
    save(48020+3*k, mirror(a))                                  # facing W
    back=plain_front(a); mi=mirror(a); stat=t & op(mi); stat[30:]=False
    top=mi.copy(); top[stat,:3]*=.55
    nb=back.copy(); nb[t]=top[t]
    save(48021+3*k, nb)                                         # from behind, wall N
    save(48022+3*k, mirror(nb))                                 # from behind, wall E
print('ok')
