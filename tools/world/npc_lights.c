/* lights <char.dat> <map.dat> <item.dat> <titem.dat>: NPCs with light duties (data[32..35] keep burning, data[41] on/off template) */
#include <stdio.h>
#include <stdlib.h>
#include "gendefs.h"
#include "data.h"
static struct character c; static struct map m; static struct item t,tt;
FILE *mf,*fi,*ft;
int itemat(int x,int y,struct item*o){ fseek(mf,(long)(x+y*MAPX)*sizeof(m),SEEK_SET); fread(&m,sizeof(m),1,mf); if(!m.it) return 0; fseek(fi,(long)m.it*sizeof(*o),SEEK_SET); fread(o,sizeof(*o),1,fi); return 1;}
int main(int a,char**v){FILE*f=fopen(v[1],"rb"); mf=fopen(v[2],"rb"); fi=fopen(v[3],"rb"); ft=fopen(v[4],"rb"); long n=0;
 while(fread(&c,sizeof(c),1,f)==1){ if(c.used&&!(c.flags&CF_PLAYER)&&!(c.flags&CF_BODY)){ int any=0,i;
   for(i=32;i<36;i++) if(c.data[i]) any=1; if(c.data[41]) any=1;
   if(any){ printf("%s (t%d) at %d,%d:",c.name,c.temp,c.x,c.y);
     for(i=32;i<36;i++) if(c.data[i]){ int p=c.data[i],x=p%MAPX,y=p/MAPX; if(itemat(x,y,&t)) printf(" [%d,%d %s t%d drv%d]",x,y,t.name,t.temp,t.driver); else printf(" [%d,%d NOTHING]",x,y);}
     if(c.data[41]){ int cnt=0,x,y; fseek(ft,(long)c.data[41]*sizeof(tt),SEEK_SET); fread(&tt,sizeof(tt),1,ft);
       int hx=c.data[29]?c.data[29]%MAPX:c.x, hy=c.data[29]?c.data[29]/MAPX:c.y;
       for(y=hy-8;y<hy+8;y++) for(x=hx-8;x<hx+8;x++) if(itemat(x,y,&t)&&t.temp==c.data[41]) cnt++;
       printf(" | toggles '%s' (t%d): %d within 8 of home",tt.name,c.data[41],cnt);}
     printf("\n");}}
  n++;}}
