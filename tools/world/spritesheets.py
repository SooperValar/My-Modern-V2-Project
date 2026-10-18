#!/usr/bin/env python3
"""Contact sheets of every client sprite with its number.

Usage: python3 spritesheets.py <client folder> <out folder> [per_sheet]
Uses the same lookup order as the client: gfx\\NNNNN.png, pnglib.dat,
gfx\\NNNNN.bmp, gx00.dat. Magenta (0xF81F) is transparent.
"""
import struct,os,sys,io
import numpy as np
from PIL import Image,ImageDraw
C,OUT=sys.argv[1],sys.argv[2]; PER=int(sys.argv[3]) if len(sys.argv)>3 else 400
os.makedirs(OUT,exist_ok=True)
g=open(os.path.join(C,'gx00.idx'),'rb').read(); gd=open(os.path.join(C,'gx00.dat'),'rb')
p=open(os.path.join(C,'pnglib.idx'),'rb').read(); pidx=struct.unpack('<%di'%(len(p)//4),p); pdat=open(os.path.join(C,'pnglib.dat'),'rb').read()
gfx={}
gdir=os.path.join(C,'GFX') if os.path.isdir(os.path.join(C,'GFX')) else os.path.join(C,'gfx')
for f in os.listdir(gdir):
    n,e=os.path.splitext(f)
    if n.isdigit(): gfx.setdefault(int(n),{})[e.lower()]=os.path.join(gdir,f)
def keyed(im):
    a=np.array(im.convert('RGBA'))
    r,gg,b=a[...,0]>>3,a[...,1]>>2,a[...,2]>>3
    a[((r<<11)|(gg<<5)|b)==0xf81f,3]=0
    return Image.fromarray(a)
def load(nr):
    d=gfx.get(nr,{})
    if '.png' in d: return keyed(Image.open(d['.png']))
    if nr<len(pidx) and pidx[nr]: return keyed(Image.open(io.BytesIO(pdat[pidx[nr]:])))
    if '.bmp' in d: return keyed(Image.open(d['.bmp']))
    if nr*12+12<=len(g):
        xs,ys,off=struct.unpack_from('<3i',g,nr*12)
        if xs>0 and ys>0:
            gd.seek(off); raw=np.frombuffer(gd.read(xs*ys*2),dtype='<u2').reshape(ys,xs)
            rgba=np.zeros((ys,xs,4),np.uint8)
            rgba[...,0]=((raw>>11)&31)*255//31; rgba[...,1]=((raw>>5)&63)*255//63; rgba[...,2]=(raw&31)*255//31
            rgba[...,3]=np.where(raw==0xf81f,0,255)
            return Image.fromarray(rgba)
    return None
ids=sorted(set(i for i in range(len(g)//12) if struct.unpack_from('<i',g,i*12)[0]>0)|{i for i,v in enumerate(pidx) if v}|set(gfx))
COLS=20; CW,CH,TH=72,72,12
bg=(48,48,56)
idxlines=[]
for s in range(0,len(ids),PER):
    chunk=ids[s:s+PER]; rows=(len(chunk)+COLS-1)//COLS
    sheet=Image.new('RGB',(COLS*CW,rows*(CH+TH)),bg); dr=ImageDraw.Draw(sheet)
    for k,nr in enumerate(chunk):
        x,y=(k%COLS)*CW,(k//COLS)*(CH+TH)
        dr.rectangle([x,y,x+CW-1,y+CH+TH-1],outline=(70,70,80))
        try: im=load(nr)
        except Exception: im=None
        if im:
            w,h=im.size; sc=min(1,(CW-4)/w,(CH-4)/h)
            if sc<1: im=im.resize((max(1,int(w*sc)),max(1,int(h*sc))),Image.LANCZOS)
            sheet.paste(im,(x+(CW-im.width)//2,y+(CH-im.height)//2),im)
            tag='' if sc==1 else ' *'
        else: tag=' ?'
        dr.text((x+3,y+CH),str(nr)+tag,fill=(255,230,120))
    name='sprites_%05d-%05d.png'%(chunk[0],chunk[-1])
    sheet.save(os.path.join(OUT,name)); idxlines.append('%s  %d sprites'%(name,len(chunk)))
    print(name,flush=True)
open(os.path.join(OUT,'index.txt'),'w').write('Sprite sheets: number under each sprite. * = shrunk to fit, ? = could not load.\n'+'\n'.join(idxlines)+'\n')
