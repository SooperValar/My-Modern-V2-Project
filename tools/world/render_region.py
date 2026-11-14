#!/usr/bin/env python3
"""iso preview of a map region: render.py <client> <dat> x0 y0 x1 y1 out.png [scale]"""
import struct,os,sys
argv=sys.argv; C,D=argv[1],argv[2]; x0,y0,x1,y1=map(int,argv[3:7]); OUTP=argv[7]; SC=float(argv[8]) if len(argv)>8 else 1
sys.argv=[argv[0],C,'/tmp']
src=open(os.path.expanduser('~/mnt/My-Modern-V2-Project/tools/world/spritesheets.py')).read().split('ids=sorted')[0]
exec(src)
from PIL import Image
m=open(D+'/map.dat','rb').read(); it=open(D+'/item.dat','rb').read(); ch=open(D+'/char.dat','rb').read()
cache={}
def L(n):
    if n not in cache:
        try: cache[n]=load(n)
        except Exception: cache[n]=None
    return cache[n]
def T(x,y): return struct.unpack_from('<HHIIIHhQ',m,(x+y*1024)*28)
def scr(x,y): return 16*(x+y), 8*(x-y)
pts=[scr(x,y) for x in (x0,x1) for y in (y0,y1)]
minx=min(p[0] for p in pts)-40; maxx=max(p[0] for p in pts)+40; miny=min(p[1] for p in pts)-120; maxy=max(p[1] for p in pts)+40
im=Image.new('RGBA',(maxx-minx,maxy-miny),(0,0,0,255))
def put(n,x,y):
    s=L(n)
    if s is None: return
    sx,sy=scr(x,y); W,H=s.size
    im.alpha_composite(s,(sx-minx-W//2, sy-miny+8-H)) if sx-minx-W//2>=0 and sy-miny+8-H>=0 else im.paste(s,(sx-minx-W//2, sy-miny+8-H),s)
tiles=[(x,y) for x in range(x0,x1+1) for y in range(y0,y1+1)]
order=sorted(tiles,key=lambda p:(p[0]-p[1],p[0]))
for x,y in order:
    sp=T(x,y)[0]
    if sp: put(sp,x,y)
for x,y in order:
    sp,fs,c,tc,i,dl,li,fl=T(x,y)
    if fs: put(fs,x,y)
    if i:
        o=i*634; isp=struct.unpack_from('<H',it,o+537)[0]; act=struct.unpack_from('<i',it,o+ 0)[0]
        if isp: put(isp,x,y)
    if c:
        o=c*3605; csp=struct.unpack_from('<H',ch,o+297)[0]
        if csp: put(csp+48,x,y)
im=im.convert('RGB')
if SC!=1: im=im.resize((int(im.width*SC),int(im.height*SC)))
im.save(OUTP); print(OUTP,im.size)
