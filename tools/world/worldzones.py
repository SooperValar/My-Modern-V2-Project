#!/usr/bin/env python3
"""Draw the zones on the world minimap.

Usage: python3 worldzones.py <server folder> <world_minimap.png> [out folder]
Reads <server folder>/.dat/zones.dat (written by the MyV2 Editor) if it exists, else the table
in area.c. A zone is a name made of one or more boxes (all boxes with the same name are one
zone, drawn in one colour). Writes world_zones.png and world_zones.md. A spot can be inside
several zones; the game then names each once, in table order, e.g. "Aston, Bank".
"""
import re, os, sys, colorsys
from PIL import Image, ImageDraw
S,MM=sys.argv[1],sys.argv[2]; OUT=sys.argv[3] if len(sys.argv)>3 else '.'
ZF=os.path.join(S,'.dat','zones.dat')
if os.path.exists(ZF):
    area=[(int(a),int(b),int(c),int(d),n.strip(),int(f)) for a,b,c,d,f,n in re.findall(r'(?m)^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([0-3])\s+(.+)$',open(ZF,encoding='latin-1').read())]
    SRC='`.dat/zones.dat` (written by the MyV2 Editor\'s Zones tab)'
else:
    src=open(os.path.join(S,'area.c')).read()
    area=[(int(a),int(b),int(c),int(d),n,int(f)) for a,b,c,d,n,f in re.findall(r'\{\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*"([^"]+)",\s*(\d)\}',src)]
    SRC='the `area[]` table in `server/area.c`'
names=list(dict.fromkeys(n for *_,n,f in area))
col={n:i for i,n in enumerate(names)}
Z=2
im=Image.open(MM).convert('RGB').resize((1024*Z,1024*Z),Image.NEAREST)
im=Image.blend(im,Image.new('RGB',im.size,(0,0,0)),0.4)
dr=ImageDraw.Draw(im)
# minimap orientation: column = map y, row = map x
for k,(x1,y1,x2,y2,n,f) in enumerate(area):
    r,g,b=colorsys.hsv_to_rgb((col[n]*0.618)%1,0.8,1); c=(int(r*255),int(g*255),int(b*255))
    dr.rectangle([y1*Z,x1*Z,y2*Z+Z-1,x2*Z+Z-1],outline=c)
for k,(x1,y1,x2,y2,n,f) in enumerate(area):
    r,g,b=colorsys.hsv_to_rgb((col[n]*0.618)%1,0.8,1); c=(int(r*255),int(g*255),int(b*255))
    w=(y2-y1)*Z; t=n if dr.textlength(n)<=w+40 else n[:max(3,int(w/6))]+'.'
    dr.text((y1*Z+2,x1*Z+1),t,fill=c)
im.save(os.path.join(OUT,'world_zones.png'))
P={0:'in',1:'in the',2:'on',3:'at'}
L=['# Zones','','Zones come from '+SRC+': boxes of map x1,y1 - x2,y2. Every box with the same name is part of one zone (odd shapes are several boxes).',
'Shown by `/who`, by NPCs when asked where you are, and in server logs. A spot inside several zones shows each name once, in table order.','',
'![zones](world_zones.png)','','| # | Name | x1,y1 | x2,y2 | Says |','|---|---|---|---|---|']
for k,(x1,y1,x2,y2,n,f) in enumerate(area): L.append('| %d | %s | %d,%d | %d,%d | "%s %s" |'%(k,n,x1,y1,x2,y2,P[f],n))
open(os.path.join(OUT,'world_zones.md'),'w').write('\n'.join(L)+'\n')
print(len(names),'zones in',len(area),'boxes')
