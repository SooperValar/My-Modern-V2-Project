/* Copy changed tiles (and their items) from one place on the map to another.
 *   town_apply <server .dat folder> <spec file>     (server stopped!)
 * Spec lines:
 *   offset <dx> <dy>          source = destination + (dx,dy)
 *   tile <x> <y>              copy sprite, fsprite, flags (low 32 bits), light, dlight and the item
 *   tiledata <x> <y> <d0> <d1>   after copying: data[0..1] of the item now on that tile
 *   itemdata <index> <d0> <d1>   data[0..1] of item <index>
 * Characters on the tiles are left alone (map ch / to_ch kept).
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "gendefs.h"
#include "data.h"
static struct map *M; static struct item *I;
int main(int argc,char**argv){
	char fn[512],line[256]; FILE*f; long nI; int ox=0,oy=0,x,y,a,b,idx,tiles=0,freed=0,made=0,free_from=1,ln=0;
	M=malloc(sizeof(struct map)*MAPX*MAPY); I=malloc(sizeof(struct item)*MAXITEM);
	sprintf(fn,"%s/map.dat",argv[1]); f=fopen(fn,"rb"); fread(M,sizeof(struct map),MAPX*MAPY,f); fclose(f);
	sprintf(fn,"%s/item.dat",argv[1]); f=fopen(fn,"rb"); nI=fread(I,sizeof(struct item),MAXITEM,f); fclose(f);
	printf("%ld items in item.dat (MAXITEM %d)\n",nI,MAXITEM);
	f=fopen(argv[2],"r"); if(!f){perror(argv[2]);return 1;}
	while(fgets(line,sizeof(line),f)){ ln++;
		if(sscanf(line,"offset %d %d",&a,&b)==2){ox=a;oy=b;continue;}
		if(sscanf(line,"tile %d %d",&x,&y)==2){
			struct map *d=&M[x+y*MAPX],*s=&M[(x+ox)+(y+oy)*MAPX];
			if(d->it){ I[d->it].used=USE_EMPTY; d->it=0; freed++; }
			d->sprite=s->sprite; d->fsprite=s->fsprite;
			d->flags=(d->flags&0xFFFFFFFF00000000ULL)|(s->flags&0xFFFFFFFFULL);
			d->light=s->light; d->dlight=s->dlight;
			if(s->it){
				int n; for(n=free_from;n<MAXITEM;n++) if(!I[n].used) break;
				if(n>=MAXITEM){printf("no free item slot\n");return 1;}
				free_from=n+1;
				I[n]=I[s->it]; I[n].x=x; I[n].y=y; I[n].carried=0; d->it=n; made++;
			}
			tiles++; continue;}
		if(sscanf(line,"tiledata %d %d %d %d",&x,&y,&a,&b)==4){ int n=M[x+y*MAPX].it; if(!n){printf("line %d: no item at %d,%d\n",ln,x,y);continue;} printf("%s at %d,%d: data %d,%d -> %d,%d\n",I[n].name,x,y,I[n].data[0],I[n].data[1],a,b); I[n].data[0]=a; I[n].data[1]=b; continue;}
		if(sscanf(line,"itemdata %d %d %d",&idx,&a,&b)==3){ printf("%s (item %d at %d,%d): data %d,%d -> %d,%d\n",I[idx].name,idx,I[idx].x,I[idx].y,I[idx].data[0],I[idx].data[1],a,b); I[idx].data[0]=a; I[idx].data[1]=b; continue;}
	}
	sprintf(fn,"%s/map.dat",argv[1]); f=fopen(fn,"r+b"); fwrite(M,sizeof(struct map),MAPX*MAPY,f); fclose(f);
	sprintf(fn,"%s/item.dat",argv[1]); f=fopen(fn,"r+b"); fwrite(I,sizeof(struct item),nI>free_from?nI:free_from,f); fclose(f);
	printf("%d tiles copied, %d old items removed, %d items placed\n",tiles,freed,made);
	return 0;
}
