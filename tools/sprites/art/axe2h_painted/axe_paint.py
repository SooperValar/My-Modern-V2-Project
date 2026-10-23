import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
mask=np.load('mask.npy'); H,W=mask.shape
yy,xx=np.mgrid[0:H,0:W]
p0=np.array([340,330.]); p1=np.array([975,995.]); d=(p1-p0)/np.linalg.norm(p1-p0)
rx,ry=xx-p0[0],yy-p0[1]; along=rx*d[0]+ry*d[1]; perp=rx*d[1]-ry*d[0]
head=mask&(((np.abs(perp)>48)&(along<480))|(along<40)); haft=mask&~head
TIERS={ # blade dark/mid/light, cap colour
 'bronze':((100,70,34),(165,118,60),(222,172,98),(200,160,60)),
 'steel':((44,46,50),(125,124,128),(198,196,202),(200,170,60)),
 'gold':((70,58,10),(165,142,32),(250,238,110),(200,170,60)),
 'crystal':((36,40,110),(88,94,196),(190,196,255),(80,90,230)),
 'titanium':((4,4,6),(26,26,32),(78,78,90),(20,20,24)),
}
def lerp(a,b,t): return a+(b-a)*t
def paint(tier):
    dk,md,lt,cap=[np.array(c,float) for c in TIERS[tier]]
    img=np.zeros((H,W,3)); A=mask.astype(float)
    # head: light from the upper left, bright bevel along the outer cutting edges, dark socket in the middle
    dist=ndimage.distance_transform_edt(head)
    t=np.clip(1-(xx+yy-200)/900,0,1)                  # 1 upper-left .. 0 lower-right
    base=lerp(md[None,None,:],lt[None,None,:],(t*0.6)[...,None])
    base=lerp(base,dk[None,None,:],(np.clip((xx+yy-500)/700,0,1)*0.55)[...,None])
    edge=(dist<26)&head&(np.abs(perp)>110)          # cutting edges (far from the haft line)
    base[edge]=lerp(base[edge],lt*1.05,0.75)
    sock=head&(np.abs(perp)<70)&(along>-60)&(along<70)
    base[sock]=lerp(base[sock],dk,0.6)
    img[head]=base[head]
    # haft: wood, round (lit on one side), leather wrap and a metal cap at the end
    wd,wm,wl=np.array((58,34,16.)),np.array((112,68,32.)),np.array((160,104,54.))
    tw=np.clip((perp+40)/80,0,1)
    wood=lerp(wl[None,None,:],wd[None,None,:],tw[...,None])
    wood=lerp(wood,wm[None,None,:],0.35)
    wrap=haft&(along>700)&(along<880)
    band=((along//22)%2==0)
    lw=np.array((70,40,22.)); ld=np.array((38,22,12.))
    wood[wrap]=np.where(band[wrap][:,None],lw,ld)
    capm=haft&(along>=880)
    wood[capm]=lerp(cap[None,:],cap[None,:]*0.55,tw[capm][:,None])
    img[haft]=wood[haft]
    rgba=np.dstack([np.clip(img,0,255),A*255]).astype(np.uint8)
    im=Image.fromarray(rgba,'RGBA'); im=im.crop(im.getbbox())
    fit=30; s=min(fit/im.width,fit/im.height)
    sm=im.resize((round(im.width*s),round(im.height*s)),Image.LANCZOS)
    ar=np.array(sm).astype(int); al=ar[...,3]; ar[...,3]=np.where(al>100,255,0)
    # premultiply-ish fix: fringe pixels darker like the originals' edges
    fr=(al>100)&(al<230); ar[...,:3][fr]=(ar[...,:3][fr]*0.6).astype(int)
    ar[...,0]=(ar[...,0]>>3)<<3; ar[...,1]=(ar[...,1]>>2)<<2; ar[...,2]=(ar[...,2]>>3)<<3
    sm=Image.fromarray(ar.clip(0,255).astype(np.uint8),'RGBA')
    out=Image.new('RGBA',(32,32),(0,0,0,0)); out.paste(sm,(1,1),sm); return out
res={t:paint(t) for t in TIERS}
for t,im in res.items(): im.save('axe2h_%s.png'%t)
ref='/mnt/user-data/uploads/Client/Claude outputs/ref_weapons/'
refs={'bronze':'01505','steel':'01465','gold':'01490','crystal':'01485','titanium':'01655'}
Z=6; sheet=Image.new('RGB',(5*(32*Z+16)+16, 2*(32*Z)+150),(55,55,60)); dr=ImageDraw.Draw(sheet)
for i,t in enumerate(TIERS):
    x=16+i*(32*Z+16)
    a=res[t].resize((32*Z,32*Z),Image.NEAREST); sheet.paste(a,(x,10),a); dr.text((x,32*Z+12),'new 2H axe: '+t,fill=(255,255,0))
    r=Image.open(ref+refs[t]+'.png').convert('RGBA'); 
    for j,(im,bg) in enumerate(((res[t],(40,90,40)),(r,(40,90,40)),(res[t],(30,30,32)),(r,(30,30,32)))):
        xx2=x+j*44; y2=32*Z+40
        dr.rectangle((xx2-4,y2-4,xx2+36,y2+36),fill=bg); sheet.paste(im,(xx2,y2),im)
dr.text((16,32*Z+90),'actual size: new axe next to the matching 2H sword, on grass and on dark',fill=(255,255,0))
sheet.save('/mnt/user-data/outputs/axe2h_preview.png')
