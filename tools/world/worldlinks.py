#!/usr/bin/env python3
"""List every portal / teleporter / ladder in the world and check where it lands.

Usage: python3 worldlinks.py <server folder> [world_minimap.png] [out folder]
Writes world_links.json, world_links.md and (if a minimap image is given)
world_links.png with every link drawn on the map.

Reads .dat/item.dat and .dat/map.dat directly (stop the server, or accept a
slightly stale snapshot), plus area.c for area names. Record offsets are for
the 64-bit build of the server in this repo (struct item = 634 bytes).
"""
import struct, re, os, sys, json, collections
S=sys.argv[1]; MM=sys.argv[2] if len(sys.argv)>2 else None; OUT=sys.argv[3] if len(sys.argv)>3 else '.'
items=open(os.path.join(S,'.dat','item.dat'),'rb').read(); ISZ=634; MAXITEM=len(items)//ISZ
mp=open(os.path.join(S,'.dat','map.dat'),'rb').read()
area=[]
for m in re.finditer(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*"([^"]+)",\s*(\d)\}',open(os.path.join(S,'area.c')).read()):
    x1,y1,x2,y2=map(int,m.groups()[:4]); area.append((x1,y1,x2,y2,m.group(5)))
def aname(x,y):
    best=None
    for x1,y1,x2,y2,n in area:
        if x1<=x<=x2 and y1<=y<=y2:
            a=(x2-x1)*(y2-y1)
            if best is None or a<best[0]: best=(a,n)
    return best[1] if best else '(unnamed)'
# item drivers that move a player somewhere (see use_driver.c)
KIND={6:'teleport',16:'ladder/hole',23:'teleport scroll',45:"Seyan'Du portal",46:'labyrinth exit',
      62:'step teleport',64:'Lab 8 money shrine',47:'arena portal',15:'labyrinth entrance',36:'special portal (code)',38:'special portal (code)'}
HOW={6:'data[0],data[1] (absolute); if data[2]!=0 the destination is chosen in code (use_labtransfer)',
     16:'data[0],data[1] = OFFSET from the item itself (moves with it)',
     23:'data[0],data[1] (absolute)',45:'data[0],data[1] (absolute)',46:'data[0],data[1] (absolute)',
     62:'data[0],data[1] (absolute)',64:'data[1],data[2] (absolute)',
     47:'data[0]=fighter drop point, data[1]/data[2]=arena box corners, all as x+y*1024',
     15:'destination per labyrinth level, hard-coded in use_labyrinth()',
     36:'hard-coded in step_portal1_lab13()',38:'hard-coded in step_portal2_lab13()'}
def blocked(x,y):
    o=(x+y*1024)*28
    fl=struct.unpack_from('<Q',mp,o+20)[0]; it=struct.unpack_from('<I',mp,o+12)[0]
    if fl&1: return True
    if it and it<MAXITEM and items[it*ISZ]==1 and struct.unpack_from('<Q',items,it*ISZ+281)[0]&1: return True
    return False
def landing(x,y):   # mirrors god_transfer_char(): exact tile, then fuzzy around it and 3 tiles away
    if not (0<=x<1024 and 0<=y<1024): return 'OFF MAP'
    if not blocked(x,y): return 'ok'
    for cx,cy in ((x,y),(x+3,y),(x-3,y),(x,y+3),(x,y-3)):
        for dx in range(-2,3):
            for dy in range(-2,3):
                if 0<=cx+dx<1024 and 0<=cy+dy<1024 and not blocked(cx+dx,cy+dy): return 'ok (next to it)'
    return 'NO FREE TILE'
out=[]
for i in range(1,MAXITEM):
    o=i*ISZ
    if items[o]==0: continue
    drv=items[o+593]
    if drv not in KIND: continue
    x,y,carried=struct.unpack_from('<HHH',items,o+529)
    if carried: continue
    name=items[o+1:o+41].split(b'\0')[0].decode('latin1')
    temp=struct.unpack_from('<H',items,o+295)[0]
    d=struct.unpack_from('<10i',items,o+594)
    dest=None
    if drv in (23,45,46,62) or (drv==6 and not d[2]): dest=(d[0],d[1])
    elif drv==16: dest=(x+d[0],y+d[1])
    elif drv==64: dest=(d[1],d[2])
    elif drv==47: dest=(d[0]%1024,d[0]//1024)
    r=dict(item=i,template=temp,kind=KIND[drv],driver=drv,name=name,x=x,y=y,area=aname(x,y),data=list(d[:4]))
    if dest: r.update(dest_x=dest[0],dest_y=dest[1],dest_area=aname(*dest),check=landing(*dest))
    elif drv==6: r['note']='lab-solved portal, destination in code'
    else: r['note']='destination in code'
    if drv==47: r['note']='arena box (%d,%d)-(%d,%d)'%(d[1]%1024,d[1]//1024,d[2]%1024,d[2]//1024)
    out.append(r)
out.sort(key=lambda r:(r['area'],r['kind'],r['x'],r['y']))
json.dump(out,open(os.path.join(OUT,'world_links.json'),'w'),indent=1)

# hard-coded coordinates in the server source (keep up to date when moving areas!)
CODE=[('use_driver.c','use_labyrinth()','Labyrinth entrance (Aston, 607,500): one destination per labyrinth level: 64,56  95,207  74,240  37,370  114,390  28,493  24,534  118,667  63,720  33,597'),
('use_driver.c','finish_laby_teleport()','512,512 (Temple of Skua)'),
('use_driver.c','step_portal1/2_lab13()','Lab 13 portals: scan areas x 48-80 / y 593-608'),
('helper.c','use_labtransfer()','lab-solved fight arena 174,166; back to 512,512'),
('lab9.c','destinations[]','Riddle Gorge rewards: 39,729  40,749  40,769  40,789  34,806'),
('gendefs.h','HOME_MERCENARY_X/Y','512,512: new characters, Skua temple (recall / death)'),
('svr_do.c / svr_god.c','temple_x/y','558,542 Temple of the Purple One; 813,165 staff temple; 512,512 Skua'),
('server.c','line ~632','recognizes temples at x 512 / 558 / 813'),
('svr_god.c','god_usurp()','10,10'),
('area.c','area[]','%d named rectangles (area names shown in game, used for this report)'%len(area)),
('char.dat / tchar.dat','temple_x/y, tavern_x/y, NPC positions','per character: recall/death temple, login tavern, NPC homes')]

L=['# World links','','Every portal, teleporter, ladder and hole in the world: where it is, where it sends you, and whether the landing spot is free.',
'Generated by `tools/world/worldlinks.py` from the server data. Coordinates are map x,y (what `#goto x y` uses).','',
'![links](world_links.png)','','## Summary','','| Kind | Count | Destination stored in |','|---|---|---|']
cnt=collections.Counter(r['driver'] for r in out)
for drv,n in sorted(cnt.items(),key=lambda t:-t[1]): L.append('| %s | %d | %s |'%(KIND[drv],n,HOW[drv]))
bad=[r for r in out if r.get('check','ok').startswith(('NO','OFF'))]
L+=['','**Landing check:** %s'%('all destinations have a free tile to land on.' if not bad else '%d problems, see below.'%len(bad)),'',
'## Coordinates hard-coded in the server source','','These are not in the data files; moving one of these places means editing the code and rebuilding.','',
'| File | Where | Coordinates |','|---|---|---|']
for f,w,c in CODE: L.append('| %s | %s | %s |'%(f,w,c))
L+=['','## All links by area','']
cur=None
for r in out:
    if r['area']!=cur:
        cur=r['area']; L+=['','### %s'%cur,'','| Item | Kind | Name | At | Goes to | Check |','|---|---|---|---|---|---|']
    to='%d,%d %s'%(r['dest_x'],r['dest_y'],r['dest_area']) if 'dest_x' in r else '*'+r['note']+'*'
    L.append('| %d | %s | %s | %d,%d | %s | %s |'%(r['item'],r['kind'],r['name'].replace('|','/'),r['x'],r['y'],to,r.get('check','')))
open(os.path.join(OUT,'world_links.md'),'w').write('\n'.join(L)+'\n')

if MM:
    from PIL import Image, ImageDraw
    im=Image.open(MM).convert('RGB').resize((2048,2048),Image.NEAREST)
    im=Image.blend(im,Image.new('RGB',im.size,(0,0,0)),0.35)
    dr=ImageDraw.Draw(im)
    col={16:(255,220,0),6:(0,230,255),62:(255,90,255),46:(255,60,60),45:(255,60,60),64:(120,255,120),47:(255,160,0),23:(255,255,255)}
    P=lambda x,y:(y*2+1,x*2+1)   # minimap orientation: column=y, row=x
    for r in out:
        c=col.get(r['driver'],(255,255,255))
        if 'dest_x' in r:
            dr.line([P(r['x'],r['y']),P(r['dest_x'],r['dest_y'])],fill=c,width=1)
            x,y=P(r['dest_x'],r['dest_y']); dr.ellipse([x-2,y-2,x+2,y+2],outline=c)
        x,y=P(r['x'],r['y']); dr.rectangle([x-2,y-2,x+2,y+2],fill=c)
    lg=[('ladder / hole',16),('teleport',6),('step teleport',62),('labyrinth exit / Seyan portal',46),('Lab 8 shrine',64),('arena',47),('in code (no line)',15)]
    for k,(t,d) in enumerate(lg):
        dr.rectangle([1700,1700+k*22,1712,1712+k*22],fill=col.get(d,(255,255,255))); dr.text((1720,1700+k*22),t,fill=(255,255,255))
    dr.text((1700,1700+len(lg)*22),'square = portal, circle = landing',fill=(200,200,200))
    im.save(os.path.join(OUT,'world_links.png'))
print(len(out),'links,',len(bad),'problems')
