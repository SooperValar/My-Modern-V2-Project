from PIL import Image
import os,sys
OUT=sys.argv[1]
GL=(170,215,250,190); GLE=(80,140,200,255); GLH=(235,250,255,230)
SA=(232,190,70,255); SAD=(180,130,40,255); SAH=(255,230,140,255)
FR=(205,160,45,255); FRD=(120,85,20,255); FRH=(250,215,110,255)
def bulb(px,top,upper):
    # rows of an hourglass bulb: width shrinks toward the neck
    rows=range(6,15) if upper else range(17,26)
    for i,y in enumerate(rows):
        k=i if upper else 8-i          # 0 at the wide end
        half=max(1,5-k*4//8)
        x0,x1=16-half,15+half
        for x in range(x0,x1+1):
            c=GLE if x in (x0,x1) else GL
            px[x,y]=c
        if half>2: px[x0+1,y]=GLH
def neck(px):
    for y in (15,16): px[15,y]=GLE; px[16,y]=GL
def cap(px,y):
    for x in range(9,23):
        px[x,y]=FRH if y%2==0 else FRD
        px[x,y+1]=FR
def posts(px,y0,y1):
    for y in range(y0,y1+1):
        px[9,y]=FRD; px[22,y]=FR
def sand(px,upper_amount,lower_amount):
    # lower bulb: a heap from the bottom; upper: what's left at the top
    for y in range(25,25-lower_amount,-1):
        for x in range(10,22):
            if px[x,y][3] and px[x,y] not in (GLE,): px[x,y]=SA if (x+y)%3 else SAD
    for y in range(14,14-upper_amount,-1):
        for x in range(10,22):
            if px[x,y][3] and px[x,y]!=GLE: px[x,y]=SA if (x+y)%3 else SAH
    px[15,16]=SAH; px[16,17]=SA
def new(): return Image.new('RGBA',(32,32),(0,0,0,0))
def save(im,n): im.save(os.path.join(OUT,'%05d.png'%n))
# 18121 top: cap + upper bulb + short posts
im=new();p=im.load();cap(p,4);bulb(p,True,True);posts(p,6,14);save(im,18121)
# 18123 middle: neck with a bit of glass either side and post pieces
im=new();p=im.load()
for y in range(12,20):
    w=1 if y in (15,16) else (2 if y in (14,17) else 3)
    for x in range(16-w,16+w): p[x,y]=GLE if x in (16-w,15+w) else GL
for y in range(12,20): p[9,y]=FRD; p[22,y]=FR
save(im,18123)
# 18122 bottom: lower bulb + cap + posts
im=new();p=im.load();bulb(p,False,False);cap(p,26);posts(p,17,25);save(im,18122)
# 18124 top+middle
im=new();p=im.load();cap(p,4);bulb(p,True,True);neck(p);posts(p,6,18);save(im,18124)
# 18125 bottom+middle
im=new();p=im.load();neck(p);bulb(p,False,False);cap(p,26);posts(p,13,25);save(im,18125)
# 18128 empty hourglass (all three glass parts, no sand)
im=new();p=im.load();cap(p,4);bulb(p,True,True);neck(p);bulb(p,False,False);cap(p,26);posts(p,6,25);save(im,18128)
# 18126 hourglass of time (complete, with sand)
im=new();p=im.load();cap(p,4);bulb(p,True,True);neck(p);bulb(p,False,False);cap(p,26);posts(p,6,25);sand(p,3,4);save(im,18126)
# 18127 sands of time: a small glowing heap
im=new();p=im.load()
for i,y in enumerate(range(21,27)):
    half=2+i*5//5+i
    for x in range(16-half,16+half):
        p[x,y]=SAH if (x*7+y*3)%5==0 else (SA if (x+y)%4 else SAD)
for x,y in ((12,17),(19,16),(16,14),(21,19),(10,20)): p[x,y]=(255,245,190,230)
save(im,18127)
# preview sheet
sheet=Image.new('RGBA',(8*36,36),(40,40,48,255))
for i,n in enumerate((18121,18123,18122,18124,18125,18128,18127,18126)):
    sheet.alpha_composite(Image.open(os.path.join(OUT,'%05d.png'%n)),(i*36+2,2))
sheet.resize((sheet.width*4,sheet.height*4),Image.NEAREST).save(os.path.join(OUT,'preview.png'))
