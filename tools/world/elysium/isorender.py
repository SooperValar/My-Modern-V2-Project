import sys,os
tsv,out=sys.argv[1],sys.argv[2]; ALPHA=float(sys.argv[3]) if len(sys.argv)>3 else 1.0
exec(open(os.path.expanduser('~/tq/sprload.py')).read())
from PIL import Image
T={}
for l in open(tsv):
    f=l.rstrip('\n').split('\t'); T[int(f[0]),int(f[1])]=f
xs=[k[0] for k in T]; ys=[k[1] for k in T]
X0,X1,Y0,Y1=min(xs),max(xs),min(ys),max(ys)
cache={}
def L(n):
    if n not in cache:
        try: cache[n]=load(n)
        except Exception: cache[n]=None
    return cache[n]
# screen pos of tile centre: north (small x) up-left
def scr(x,y): return ((x-X0)+(y-Y0))*16, ((x-X0)-(y-Y0))*8   # the client: rx=16(x+y), ry=8(x-y)
pts=[scr(x,y) for x in (X0,X1) for y in (Y0,Y1)]
mnx=min(p[0] for p in pts)-64; mny=min(p[1] for p in pts)-120
W=max(p[0] for p in pts)-mnx+64; H=max(p[1] for p in pts)-mny+40
im=Image.new('RGBA',(W,H),(0,0,0,255))
def blit(n,x,y,a=1.0):
    s=L(n)
    if s is not None and a<1.0:
        s=s.copy(); s.putalpha(s.getchannel('A').point(lambda v:int(v*a)))
    if s is None: return
    cx,cy=scr(x,y); cx-=mnx; cy-=mny
    im.alpha_composite(s,(cx-s.width//2+32, cy-s.height+64)) if cx-s.width//2+32>=0 and cy-s.height+64>=0 else None
order=sorted(T,key=lambda k:(-k[1],k[0]))   # the client: y from high to low, x low to high
for k in order:
    f=T[k]
    if int(f[2]) and int(f[2])!=1008: blit(int(f[2]),*k)
for k in order:
    f=T[k]
    if int(f[3]): blit(int(f[3]),*k,a=ALPHA)
    if f[7]: blit(int(f[7]),*k)
    if f[11]: blit(int(f[11]) if int(f[11])>1000 else 0,*k)
im.save(out); print(im.size)
