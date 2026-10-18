#!/usr/bin/env python3
"""Pack Tower floors II-XX into a compact block (one-off world edit).

Usage: python3 movetowers.py <server folder> <out folder>
Reads <server>/.dat/{map,item,char,tchar}.dat and <server>/area.c, writes the
edited copies to <out>/.dat/ and <out>/area.c. Nothing in <server> is changed.

What moves with each floor: every map tile (sprite, objects, flags, light),
the items lying in it, the NPCs standing in it, and their templates (respawn
position, resting spot, patrol stops). Ladders/holes get their offsets
recomputed, every teleport anywhere that lands in a moved floor is updated,
and the zone rectangles in area.c follow.
"""
import struct,re,os,sys,json
SRC,OUT=sys.argv[1],sys.argv[2]
rd=lambda f:bytearray(open(os.path.join(SRC,'.dat',f),'rb').read())
mp,items,chars,tchars=rd('map.dat'),rd('item.dat'),rd('char.dat'),rd('tchar.dat')
mp0=bytes(mp)
areasrc=open(os.path.join(SRC,'area.c')).read()
MS,IS,CS=28,634,3605
NI=len(items)//IS
ORDER=['II','III','IV','V','VI','VII','VIII','IX','X','XI','XII','XIII','XIV','XV','XVI','XVII','XVIII','XIX','XX']
ROWS=[['II','III','IV','V','VI'],['VII','VIII','IX','X','XI'],['XII','XIII','XIV','XV'],['XVI','XVII','XVIII'],['XIX','XX']]
GAP=3; X0,Y0=822,337
FILLER=(1008,0,0,0,0,0,0,0)
Z={}
for m in re.finditer(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*"Tower ([IVX]+)",',areasrc):
    if m.group(5)!='I': Z.setdefault(m.group(5),[]).append(tuple(map(int,m.groups()[:4])))
def empty0(x,y):
    s,f,ch,tc,it,dl,li,fl=struct.unpack_from('<HHIIIHhQ',mp0,(x+y*1024)*MS)
    return s in (1008,1052) and not f and not it and not fl
def inzone(x,y,skip=None):
    return any(x1<=x<=x2 and y1<=y<=y2 for k,v in Z.items() if k!=skip for x1,y1,x2,y2 in v)
# level rectangles: zone rects plus the walls just outside them
R={}
for k in ORDER:
    rs=Z[k]; x1=min(r[0] for r in rs); y1=min(r[1] for r in rs); x2=max(r[2] for r in rs); y2=max(r[3] for r in rs)
    for _ in range(2):
        if any(not empty0(x1-1,y) and not inzone(x1-1,y,k) for y in range(y1,y2+1)): x1-=1
        if any(not empty0(x2+1,y) and not inzone(x2+1,y,k) for y in range(y1,y2+1)): x2+=1
        if any(not empty0(x,y1-1) and not inzone(x,y1-1,k) for x in range(x1,x2+1)): y1-=1
        if any(not empty0(x,y2+1) and not inzone(x,y2+1,k) for x in range(x1,x2+1)): y2+=1
    R[k]=(x1,y1,x2,y2)
SH={}; x=X0
for row in ROWS:
    y=Y0; h=0
    for k in row:
        x1,y1,x2,y2=R[k]; SH[k]=(x-x1,y-y1); y+=y2-y1+1+GAP; h=max(h,x2-x1+1)
    x+=h+GAP
def owner(x,y):   # which floor a point belongs to (zone first, then rectangle)
    for k in ORDER:
        if any(x1<=x<=x2 and y1<=y<=y2 for x1,y1,x2,y2 in Z[k]): return k
    for k in ORDER:
        x1,y1,x2,y2=R[k]
        if x1<=x<=x2 and y1<=y<=y2: return k
    return None
def mv(x,y):
    k=owner(x,y)
    if not k: return x,y
    return x+SH[k][0],y+SH[k][1]
def mvm(m):  # map index form x+y*1024
    if not m: return m
    x,y=mv(m%1024,m//1024); return x+y*1024
log=[]
# ---- map: clear old floors (and the dark backdrop of II-V, and two stray objects), paste the floors
def setcell(x,y,v): struct.pack_into('<HHIIIHhQ',mp,(x+y*1024)*MS,*v)
cleared=0
for k in ORDER:
    x1,y1,x2,y2=R[k]
    for a in range(x1,x2+1):
        for b in range(y1,y2+1): setcell(a,b,FILLER); cleared+=1
for a in range(818,842):
    for b in range(335,405):
        if struct.unpack_from('<H',mp0,(a+b*1024)*MS)[0]==1052: setcell(a,b,FILLER)
for a,b in ((849,391),(850,392)): setcell(a,b,FILLER)
newcells={}
for k in ORDER:
    x1,y1,x2,y2=R[k]; dx,dy=SH[k]
    for a in range(x1,x2+1):
        for b in range(y1,y2+1):
            s,f,ch,tc,it,dl,li,fl=struct.unpack_from('<HHIIIHhQ',mp0,(a+b*1024)*MS)
            if (a+dx,b+dy) in newcells and s==1008 and not f and not fl: continue   # don't paste empty over a neighbour
            setcell(a+dx,b+dy,(s,f,0,0,0,dl,li,fl)); newcells[(a+dx,b+dy)]=k
# ---- items
nit=0
for i in range(1,NI):
    o=i*IS
    if items[o]==0: continue
    x,y,car=struct.unpack_from('<HHH',items,o+529)
    drv=items[o+593]; d=list(struct.unpack_from('<10i',items,o+594))
    if not car and owner(x,y):
        nx,ny=mv(x,y)
        struct.pack_into('<HH',items,o+529,nx,ny)
        if struct.unpack_from('<I',mp0,(x+y*1024)*MS+12)[0]==i:
            struct.pack_into('<I',mp,(nx+ny*1024)*MS+12,i)
        nit+=1
    else: nx,ny=x,y
    nd=d[:]
    if drv==16 and not car:                                  # relative: offset to destination
        tx,ty=mv(x+d[0],y+d[1]); nd[0],nd[1]=tx-nx,ty-ny
    elif drv in (6,23,45,46,62) and not (drv==6 and d[2]):  # absolute data[0],data[1]
        nd[0],nd[1]=mv(d[0],d[1])
    elif drv==64: nd[1],nd[2]=mv(d[1],d[2])
    elif drv==47: nd[0],nd[1],nd[2]=mvm(d[0]),mvm(d[1]),mvm(d[2])
    if nd!=d:
        struct.pack_into('<10i',items,o+594,*nd)
        log.append('item %d %s at %d,%d: data %s -> %s'%(i,items[o+1:o+41].split(b'\0')[0].decode('latin1'),nx,ny,d[:3],nd[:3]))
# ---- characters and templates
def movechars(buf,live):
    n=0
    for i in range(1,len(buf)//CS):
        o=i*CS
        if buf[o]==0: continue
        x,y=struct.unpack_from('<hh',buf,o+717)
        if x>0 and owner(x,y):
            nx,ny=mv(x,y); struct.pack_into('<hh',buf,o+717,nx,ny); n+=1
            if live and struct.unpack_from('<I',mp0,(x+y*1024)*MS+4)[0]==i:
                struct.pack_into('<I',mp,(nx+ny*1024)*MS+4,i)
            for off in (721,725):   # tox/toy, frx/fry
                a,b=struct.unpack_from('<hh',buf,o+off)
                if a>0 and owner(a,b): struct.pack_into('<hh',buf,o+off,*mv(a,b))
            a,b=struct.unpack_from('<HH',buf,o+1102)
            if a and owner(a,b): struct.pack_into('<HH',buf,o+1102,*mv(a,b))
        for off in (311,315):       # temple, tavern
            a,b=struct.unpack_from('<HH',buf,o+off)
            if a and owner(a,b): struct.pack_into('<HH',buf,o+off,*mv(a,b))
        dat=list(struct.unpack_from('<100i',buf,o+1605)); nd=dat[:]
        for k in list(range(10,19))+[29,54,76]:
            if 0<dat[k]<1024*1024: nd[k]=mvm(dat[k])
        if nd!=dat: struct.pack_into('<100i',buf,o+1605,*nd)
    return n
nch=movechars(chars,True); nt=movechars(tchars,False)
# ---- area.c
def zl(m):
    x1,y1,x2,y2=map(int,m.groups()[:4]); k=m.group(5)
    if k=='I' or k not in SH: return m.group(0)
    dx,dy=SH[k]
    return m.group(0).replace(m.group(1)+','+m.group(0).split(',',1)[1].split(',',1)[0] if False else m.group(0),'{%d,%d,       %d,%d,        "Tower %s",'%(x1+dx,y1+dy,x2+dx,y2+dy,k))
area2=re.sub(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*"Tower ([IVX]+)",',zl,areasrc)
os.makedirs(os.path.join(OUT,'.dat'),exist_ok=True)
for f,b in (('map.dat',mp),('item.dat',items),('char.dat',chars),('tchar.dat',tchars)):
    open(os.path.join(OUT,'.dat',f),'wb').write(b)
open(os.path.join(OUT,'area.c'),'w').write(area2)
json.dump({'rects':R,'shift':SH},open(os.path.join(OUT,'tower_move.json'),'w'),indent=1)
open(os.path.join(OUT,'tower_move.log'),'w').write('\n'.join(log)+'\n')
print('floors',len(ORDER),'items moved',nit,'NPCs moved',nch,'templates moved',nt,'link data changed',len(log))
