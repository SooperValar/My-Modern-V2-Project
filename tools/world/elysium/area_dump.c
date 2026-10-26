#include <stdio.h>
#include <stdlib.h>
#include "gendefs.h"
#include "data.h"
static struct map m[MAPX*MAPY];
int main(int a,char**v){
 char p[512]; FILE*f;
 sprintf(p,"%s/map.dat",v[1]); f=fopen(p,"rb"); fread(m,sizeof(struct map),MAPX*MAPY,f); fclose(f);
 struct item *its=calloc(MAXITEM,sizeof(struct item)); sprintf(p,"%s/item.dat",v[1]); f=fopen(p,"rb"); fread(its,sizeof(struct item),MAXITEM,f); fclose(f);
 struct character *chs=calloc(MAXCHARS,sizeof(struct character)); sprintf(p,"%s/char.dat",v[1]); f=fopen(p,"rb"); fread(chs,sizeof(struct character),MAXCHARS,f); fclose(f);
 int x0=atoi(v[2]),x1=atoi(v[3]),y0=atoi(v[4]),y1=atoi(v[5]);
 for(int x=x0;x<=x1;x++)for(int y=y0;y<=y1;y++){struct map*q=&m[x+y*MAPX];
  printf("%d\t%d\t%d\t%d\t%llx",x,y,q->sprite,q->fsprite,(unsigned long long)q->flags);
  if(q->it&&q->it<MAXITEM){struct item*i=&its[q->it];printf("\t%d\t%s\t%d\t%d",i->temp,i->name,i->sprite[0],i->driver);}else printf("\t\t\t\t");
  if(q->ch&&q->ch<MAXCHARS){struct character*c=&chs[q->ch];printf("\t%d\t%s\t%d\t%d",c->temp,c->name,c->sprite,c->dir);}else printf("\t\t\t\t");
  printf("\n");}
 // characters whose spawn/home is here
 for(int n=1;n<MAXCHARS;n++){struct character*c=&chs[n]; if(!c->used) continue; if(c->x>=x0&&c->x<=x1&&c->y>=y0&&c->y<=y1) fprintf(stderr,"CH %d t%d %s @%d,%d\n",n,c->temp,c->name,c->x,c->y);}
}
