#!/usr/bin/env python3
"""Render the whole world as the in-game minimap would show it (1 pixel per tile).

Usage: python3 worldmap.py <client folder> <server folder> [out.png]
Uses Pillow when it is there, else its own small PNG / BMP reader and PNG writer (Nov 18: the editor's Linux python
had no Pillow, and its "redraw minimap" button failed). Colors are the average color of each tile's sprite, like the client.
Orientation matches the minimap: column = map y, row = map x."""
import struct, zlib, io, os, sys
try:
    from PIL import Image
except ImportError:
    Image = None

def _png_rgba(data):
    """the pixels of an 8-bit PNG as (r, g, b, a) tuples (colour types 0, 2, 3, 4, 6), without Pillow"""
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    i, idat, pal, trns = 8, b'', None, None
    while i < len(data):
        l, t = struct.unpack('>I4s', data[i:i + 8]); c = data[i + 8:i + 8 + l]; i += 12 + l
        if t == b'IHDR': w, h, bd, ct, _, _, il = struct.unpack('>IIBBBBB', c)
        elif t == b'PLTE': pal = [tuple(c[k:k + 3]) for k in range(0, len(c), 3)]
        elif t == b'tRNS': trns = c
        elif t == b'IDAT': idat += c
        elif t == b'IEND': break
    if bd != 8 or il: raise ValueError('png: only 8-bit, not interlaced')
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]; raw = zlib.decompress(idat); st = w * bpp; prev = bytearray(st); out = []; p = 0
    for y in range(h):
        f = raw[p]; line = bytearray(raw[p + 1:p + 1 + st]); p += 1 + st
        for x in range(st):
            a = line[x - bpp] if x >= bpp else 0; b = prev[x]; cc = prev[x - bpp] if x >= bpp else 0
            if f == 1: line[x] = (line[x] + a) & 255
            elif f == 2: line[x] = (line[x] + b) & 255
            elif f == 3: line[x] = (line[x] + (a + b) // 2) & 255
            elif f == 4:
                pp = a + b - cc; pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - cc)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else cc)) & 255
        prev = line
        for x in range(w):
            q = line[x * bpp:(x + 1) * bpp]
            if ct == 6: out.append(tuple(q))
            elif ct == 2: out.append((q[0], q[1], q[2], 255))
            elif ct == 0: out.append((q[0], q[0], q[0], 255))
            elif ct == 4: out.append((q[0], q[0], q[0], q[1]))
            else: out.append(pal[q[0]] + ((trns[q[0]] if trns and q[0] < len(trns) else 255),))
    return out

def _bmp_rgba(data):
    """the pixels of an uncompressed 8 / 24 / 32-bit BMP, without Pillow"""
    off = struct.unpack_from('<I', data, 10)[0]; w, h = struct.unpack_from('<ii', data, 18); bpp = struct.unpack_from('<H', data, 28)[0]
    if struct.unpack_from('<I', data, 30)[0] not in (0, 3): raise ValueError('bmp: compressed')
    hh = abs(h); st = ((w * bpp + 31) // 32) * 4; out = []
    pal = [tuple(data[54 + k * 4:54 + k * 4 + 3][::-1]) for k in range(256)] if bpp == 8 else None
    for row in range(hh):
        y = hh - 1 - row if h > 0 else row; base = off + y * st
        for x in range(w):
            if bpp == 8: r, g, b = pal[data[base + x]]
            else: b, g, r = data[base + x * bpp // 8:base + x * bpp // 8 + 3]
            out.append((r, g, b, 255))
    return out

def _png_write(path, w, h, rgb):
    raw = b''.join(b'\0' + rgb[y * w * 3:(y + 1) * w * 3] for y in range(h))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))
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
    if isinstance(im, list): pixels = im
    else:
        im=im.convert('RGBA'); pixels = im.get_flattened_data() if hasattr(im,'get_flattened_data') else im.getdata()
    px=[]
    for r,g,b,a in pixels:
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
        if '.png' in d: v=from_img(Image.open(d['.png']) if Image else _png_rgba(open(d['.png'],'rb').read()))
        elif nr<len(pidx) and pidx[nr]: v=from_img(Image.open(io.BytesIO(pdat[pidx[nr]:])) if Image else _png_rgba(pdat[pidx[nr]:]))
        elif '.bmp' in d: v=from_img(Image.open(d['.bmp']) if Image else _bmp_rgba(open(d['.bmp'],'rb').read()))
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
if Image: Image.frombytes('RGB',(1024,1024),bytes(out)).save(OUT, format='PNG')
else: _png_write(OUT, 1024, 1024, bytes(out))
print('wrote',OUT)
