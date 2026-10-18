#!/usr/bin/env python3
"""Character sprite sheet: every character sprite base with the NPCs/races that use it.

#sprite number = (base-2000)/1024, as in god_spritechange().
Usage: python3 charsheet.py <client folder> <server folder> <out.png>
A character's sprite is a base number (spaced 1024 apart); its frames are
base+0..55 idle (8 directions x 8), then walking, fighting etc.
Shown: the idle frame facing the viewer (south on screen), base+48.
"""
import struct,os,sys,collections
sys.argv,argv=[sys.argv[0],sys.argv[1],'/tmp'],sys.argv
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'spritesheets.py')).read().split('ids=sorted')[0])
from PIL import Image,ImageDraw,ImageFont
try: BIG=ImageFont.load_default(size=18)
except Exception: BIG=None
C,S,OUT=argv[1],argv[2],argv[3]
CS=3605; names=collections.defaultdict(collections.Counter); live=collections.Counter()
for fn in ('tchar.dat','char.dat'):
    d=open(os.path.join(S,'.dat',fn),'rb').read()
    for i in range(len(d)//CS):
        o=i*CS
        if d[o]==0: continue
        sp=struct.unpack_from('<H',d,o+297)[0]
        if not sp: continue
        if fn=='tchar.dat': names[sp][d[o+1:o+41].split(b'\0')[0].decode('latin1')]+=1
        else: live[sp]+=1
bases=sorted(set(names)|{b for b in range(976,40000,1024) if load(b+48)}|{b for b in range(2000,40000,1024) if load(b+48)})
bases=[b for b in bases if load(b+48)]
CW,CH=380,150; COLS=4
rows=(len(bases)+COLS-1)//COLS
sheet=Image.new('RGB',(COLS*CW,rows*CH+30),(40,40,48)); dr=ImageDraw.Draw(sheet)
dr.text((8,8),'Character sprites: the number used by #sprite <character> <number>, facing the viewer (2x), and the NPC templates using it',fill=(255,255,255))
for k,b in enumerate(bases):
    x,y=(k%COLS)*CW,(k//COLS)*CH+30
    dr.rectangle([x+2,y+2,x+CW-3,y+CH-3],outline=(80,80,95))
    im=load(b+48)
    if im:
        im2=im.resize((im.width*2,im.height*2),Image.NEAREST)
        sheet.paste(im2,(x+6,y+CH-6-im2.height),im2)
    dr.text((x+150,y+6),'#sprite %d'%((b-2000)//1024),fill=(255,230,120),font=BIG)
    dr.text((x+270,y+12),'(base %d)'%b,fill=(150,150,165))
    dr.text((x+150,y+28),('in use: %d'%live[b]) if live[b] else ('' if names[b] else 'not used by any template'),fill=(150,220,150))
    tx=x+150; ty=y+44
    for n,c in names[b].most_common(6):
        dr.text((tx,ty),(n if c==1 else '%s (%d)'%(n,c))[:28],fill=(220,220,230)); ty+=14
    if len(names[b])>6: dr.text((tx,ty),'+%d more names'%(len(names[b])-6),fill=(160,160,170))
sheet.save(OUT); print(len(bases),'bases ->',OUT)
