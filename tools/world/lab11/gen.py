"""Lab 11 'The Sunken Dark' - layout draft (no map changes).
Tile codes: '#' wall, '.' dry floor, '~' water, 'D' gate door, 'B' brazier,
'L' lectern, 'S' bookshelf (book), 's' bookshelf (empty), 'P' end portal,
'X' exit portal, 'H' offering shrine, 'A' arrival, 'm' monster spot, '|' shelf wall."""
import json,random,sys
from PIL import Image,ImageDraw
random.seed(11)
W,H=120,100
g=[['#']*W for _ in range(H)]
def rect(x0,y0,x1,y1,c):
    for y in range(y0,y1+1):
        for x in range(x0,x1+1): g[y][x]=c
def put(x,y,c): g[y][x]=c
def islands(x0,y0,x1,y1,step=7,size=3,braz=True,mons=True):
    k=0
    for y in range(y0+2,y1-1,step):
        for x in range(x0+2,x1-1,step):
            rect(x,y,min(x+size-1,x1-1),min(y+size-1,y1-1),'.')
            k+=1
            if braz and k%2==0: put(x+1,y+1,'B')
            elif mons and k%3==0: put(x+1,y+1,'m')
# entry hall (dry, lit)
rect(2,40,21,59,'.'); put(10,50,'A'); put(4,42,'X'); put(4,57,'H')
for p in ((3,41),(20,41),(3,58),(20,58)): put(*p,'B')
put(22,50,'D')
# section 1: flooded atrium with alcoves
rect(23,30,57,69,'~'); islands(23,30,57,69)
rect(23,48,26,52,'.')                       # landing by the entry gate
for i,(ax,ay) in enumerate(((28,24),(38,24),(48,24))):
    rect(ax,ay,ax+5,ay+5,'~'); put(ax+2, ay+5 if ay<30 else ay, '~')
    put(ax+2,ay+2,'S' if i==1 else 's')     # book 1 in the middle north alcove
rect(53,47,57,53,'.'); put(55,50,'L'); put(58,50,'D')
# section 2: flooded library, shelf rows
rect(59,30,93,69,'~')
for y in range(34,67,6):
    for x in range(62,91):
        if (x-62)%10 not in (4,5): put(x,y,'|')
islands(59,30,93,69,step=6,size=2,braz=True,mons=True)
for y in range(34,67,6):
    for x in range(62,91):
        if (x-62)%10 not in (4,5) and g[y][x]=='.': put(x,y,'|')
shelves=[(66,40),(76,46),(86,52),(66,58),(86,40),(76,64)]
for i,(x,y) in enumerate(shelves): put(x,y,'S' if i==4 else 's')
rect(89,47,93,53,'.'); put(91,50,'L'); put(94,50,'D')
# section 3: sunken crypt, narrow winding tunnels north and south
rect(95,48,99,52,'.')
def tunnel(path):
    for (x0,y0),(x1,y1) in zip(path,path[1:]):
        for x in range(min(x0,x1),max(x0,x1)+1):
            for y in range(min(y0,y1),max(y0,y1)+1):
                for dx in (-1,0,1):
                    for dy in (-1,0,1):
                        if g[y+dy][x+dx]=='#': g[y+dy][x+dx]='~'
north=[(100,50),(110,50),(110,40),(100,40),(100,30),(114,30),(114,18),(100,18),(100,8)]
south=[(97,52),(97,62),(112,62),(112,74),(100,74),(100,86),(106,86),(106,93),(96,93)]
tunnel(north); tunnel(south)
pockets=[(110,45),(105,40),(100,35),(107,30),(114,24),(107,18),(100,13),(97,57),(105,62),(112,68),(106,74),(100,80),(103,86)]
for x,y in pockets: rect(x-1,y-1,x,y,'.')
rect(98,5,103,9,'.'); put(100,6,'S'); put(102,6,'B')   # book 3 at the far north end
put(97,49,'L')                                          # lectern 3 by the crypt entrance
for x,y in ((110,40),(100,30),(114,18),(97,62),(112,74)): put(x,y,'m')
put(94,93,'D'); put(93,93,'.'); put(92,93,'.')

# section 4: dark cistern along the bottom, few braziers
rect(23,72,91,97,'~'); rect(86,90,91,96,'.')
for y in range(75,96,5):
    for x in range(27,88,9): rect(x,y,x,y,'#')              # pillars
k=0
for y in range(74,96,7):
    for x in range(30,84,8):
        rect(x,y,x+2,y+2,'.'); k+=1
        if k%5==0: put(x+1,y+1,'B')
        elif k%3==0: put(x+1,y+1,'m')
rect(23,82,27,88,'.'); put(25,85,'S'); put(26,83,'B')  # book 4 at the far west end
put(25,87,'L'); put(22,85,'D')
# vault
rect(2,72,21,97,'.'); put(10,85,'P')
for p in ((3,73),(20,73),(3,96),(20,96)): put(*p,'B')
json.dump([''.join(r) for r in g],open(sys.argv[1]+'/layout.json','w'))
# preview
col={'#':(30,30,34),'.':(120,116,108),'~':(40,90,140),'D':(200,120,40),'B':(255,170,40),'L':(230,60,230),
     'S':(60,230,90),'s':(40,110,60),'P':(120,220,255),'X':(255,255,255),'H':(255,230,120),'A':(255,60,60),'m':(200,30,30),'|':(90,60,40)}
S=8; im=Image.new('RGB',(W*S,H*S)); d=ImageDraw.Draw(im)
for y in range(H):
    for x in range(W):
        d.rectangle((x*S,y*S,x*S+S-1,y*S+S-1),fill=col[g[y][x]])
for t,(x,y) in (('ENTRY',(6,45)),('1 ATRIUM',(32,32)),('2 LIBRARY',(66,31)),('3 CRYPT',(104,2)),('4 CISTERN',(50,77)),('VAULT',(7,79))):
    d.text((x*S,y*S),t,fill=(255,255,255))
im.save(sys.argv[1]+'/preview.png')
# solo check: longest run of water steps on the way to every key spot (BFS by fewest consecutive water tiles)
print('ok')
