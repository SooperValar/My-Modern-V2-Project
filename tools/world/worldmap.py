#!/usr/bin/env python3
"""Render the whole world as the in-game minimap would show it (1 pixel per tile).

Usage: python3 worldmap.py <client folder> <server folder> [out.png]
Needs Pillow. Colors are the average color of each tile's sprite, like the client.
Orientation matches the minimap: column = map y, row = map x."""
import struct, zlib, io, os, sys
from PIL import Image
C=sys.argv[1]; S=os.path.join(sys.argv[2],'.dat'); OUT=sys.argv[3] if len(sys.argv)>3 else 'world_minimap.png'
MAXSPRITE=40000
gidx=open(C+'/gx00.idx','rb').read(); gdat=open(C+'/gx00.dat','rb')
pidx=struct.unpack('<%di'%(len(open(C+'/pnglib.idx','rb').read())//4),open(C+'/pnglib.idx','rb').read())
pdat=open(C+'/pnglib.dat','rb').read()
gfxdir={}
for f in os.listdir(C+'/GFX'):
    n,e=os.path.splitext(f)
    if n.isdigit(): gfxdir.setdefault(int(n),{})[e.lower()]=C+'/GFX/'+f
def avg565(px):  # list of (r5,g6,b5)
    if not px: return 0
    c=len(px); r=sum(p[0] for p in px)//c; g=sum(p[1] for p in px)//c; b=sum(p[2] for p in px)//c
    return (r<<11)|(g<<5)|b
def from_img(im):
    im=im.convert('RGBA'); px=[]
    for r,g,b,a in (im.get_flattened_data() if hasattr(im,'get_flattened_data') else im.getdata()):
        if a<128: continue
        r5,g6,b5=r>>3,g>>2,b>>3
        if (r5<<11|g6<<5|b5)==0xf81f: continue
        px.append((r5,g6,b5))
    return avg565(px)
cache={}
def avgcol(nr):
    if nr in cache: return cache[nr]
    v=0
    try:
        d=gfxdir.get(nr,{})
        if '.png' in d: v=from_img(Image.open(d['.png']))
        elif nr<len(pidx) and pidx[nr]: v=from_img(Image.open(io.BytesIO(pdat[pidx[nr]:])))
        elif '.bmp' in d: v=from_img(Image.open(d['.bmp']))
        elif nr<MAXSPRITE:
            xs,ys,off=struct.unpack_from('<3i',gidx,nr*12)
            if xs>0 and ys>0:
                gdat.seek(off); raw=gdat.read(xs*ys*2)
                px=[]
                for (p,) in struct.iter_unpack('<H',raw):
                    if p!=0xf81f: px.append((p>>11,(p>>5)&63,p&31))
                v=avg565(px)
    except Exception as e: print('sprite',nr,e,file=sys.stderr)
    cache[nr]=v; return v
items=open(S+'/item.dat','rb').read()
mp=open(S+'/map.dat','rb').read()
out=bytearray(1024*1024*3)
for mx in range(1024):
    for my in range(1024):
        o=(mx+my*1024)*28
        spr,fspr,ch,toch,it=struct.unpack_from('<HHIII',mp,o)
        v=avgcol(spr) if spr else 0
        obj=fspr
        if not obj and it and it<98304:
            io_=it*634
            if items[io_]==1:
                fl=struct.unpack_from('<Q',items,io_+281)[0]
                if not fl&(4|0x100000000):
                    act=struct.unpack_from('<i',items,io_+525)[0]
                    obj=struct.unpack_from('<H',items,io_+537+(2 if act else 0))[0]
        if obj: v=avgcol(obj) or v
        # minimap orientation: column = map y, row = map x
        p=(mx*1024+my)*3
        out[p]=((v>>11)&31)*255//31; out[p+1]=((v>>5)&63)*255//63; out[p+2]=(v&31)*255//31
im=Image.frombytes('RGB',(1024,1024),bytes(out))
im.save(OUT); print('wrote',OUT)
