/* mapflags <server .dat folder> <list>   (server stopped!)
 * List lines: "<x> <y> clear <bit>..." or "<x> <y> set <bit>..." (map flag bits, e.g. 2 indoors, 5 no monsters, 14 no fighting). */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "gendefs.h"
#include "data.h"
int main(int argc,char**argv){ char fn[512],line[256],w[16]; FILE*f,*l; struct map m; int x,y,n=0,b,off;
	sprintf(fn,"%s/map.dat",argv[1]); f=fopen(fn,"r+b"); if(!f){perror(fn);return 1;} l=fopen(argv[2],"r"); if(!l){perror(argv[2]);return 1;}
	while(fgets(line,sizeof(line),l)){ if(sscanf(line,"%d %d %15s%n",&x,&y,w,&off)!=3) continue;
		long pos=(long)(x+y*MAPX)*sizeof(struct map); fseek(f,pos,SEEK_SET); if(fread(&m,sizeof(m),1,f)!=1) continue;
		char *p=line+off; while(sscanf(p,"%d%n",&b,&off)==1){ p+=off; if(!strcmp(w,"clear")) m.flags&=~(1ULL<<b); else if(!strcmp(w,"set")) m.flags|=(1ULL<<b); }
		fseek(f,pos,SEEK_SET); fwrite(&m,sizeof(m),1,f); n++; }
	fclose(f); printf("%d tiles changed (struct map is %zu bytes)\n",n,sizeof(struct map)); return 0; }
