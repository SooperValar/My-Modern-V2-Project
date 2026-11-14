/* Remove NPCs (not players) of given templates inside a box, with everything they carry.
 *   remove_npcs <server .dat folder> <x1> <y1> <x2> <y2> <template> [template...]   (server stopped!)
 * Clears the character, its items (inventory, worn, spells, carried item) and its map links (ch / to_ch).
 * Matches on the NPC's position OR its resting spot (data[29]) inside the box.
 * Note: NPCs hatched by a spawner item (e.g. Spider's Web, driver 43) come back unless the spawner
 * is removed too (place_items "remove x y").
 */
#include <stdio.h>
#include <stdlib.h>
#include "gendefs.h"
#include "data.h"

static struct character c; static struct item I; static struct map m;

static void freeitem(FILE *itf,unsigned int in)
{
	if (!in || in>=MAXITEM) return;
	fseek(itf,(long)in*sizeof(I),SEEK_SET); fread(&I,sizeof(I),1,itf);
	I.used=USE_EMPTY; fseek(itf,(long)in*sizeof(I),SEEK_SET); fwrite(&I,sizeof(I),1,itf);
}

static void unlink_map(FILE *mf,long cn,int x,int y)
{
	for (int dx=-1; dx<=1; dx++) for (int dy=-1; dy<=1; dy++) {
		int xx=x+dx,yy=y+dy; if (xx<0||yy<0||xx>=MAPX||yy>=MAPY) continue;
		long mpos=(long)(xx+yy*MAPX)*sizeof(m);
		fseek(mf,mpos,SEEK_SET); fread(&m,sizeof(m),1,mf);
		int ch=0; if (m.ch==cn) { m.ch=0; ch=1; } if (m.to_ch==cn) { m.to_ch=0; ch=1; }
		if (ch) { fseek(mf,mpos,SEEK_SET); fwrite(&m,sizeof(m),1,mf); }
	}
}

int main(int argc,char **argv)
{
	char fn[512]; FILE *cf,*itf,*mf; long n=0; int removed=0;
	if (argc<7) { printf("usage: remove_npcs <.dat> <x1> <y1> <x2> <y2> <template...>\n"); return 1; }
	int x1=atoi(argv[2]),y1=atoi(argv[3]),x2=atoi(argv[4]),y2=atoi(argv[5]);
	sprintf(fn,"%s/char.dat",argv[1]); cf=fopen(fn,"r+b");
	sprintf(fn,"%s/item.dat",argv[1]); itf=fopen(fn,"r+b");
	sprintf(fn,"%s/map.dat",argv[1]); mf=fopen(fn,"r+b");
	if (!cf||!itf||!mf) { perror("open"); return 1; }
	while (fread(&c,sizeof(c),1,cf)==1) {
		int want=0;
		for (int a=6; a<argc; a++) if (c.temp==atoi(argv[a])) want=1;
		int rx=c.data[29]%MAPX, ry=c.data[29]/MAPX;
		int inbox=(c.x>=x1&&c.x<=x2&&c.y>=y1&&c.y<=y2) || (c.data[29]&&rx>=x1&&rx<=x2&&ry>=y1&&ry<=y2);
		if (n && c.used && want && inbox && !(c.flags&CF_PLAYER)) {
			for (int i=0; i<40; i++) freeitem(itf,c.item[i]);
			for (int i=0; i<20; i++) freeitem(itf,c.worn[i]);
			for (int i=0; i<20; i++) freeitem(itf,c.spell[i]);
			freeitem(itf,c.citem);
			unlink_map(mf,n,c.x,c.y);
			if (c.tox||c.toy) unlink_map(mf,n,c.tox,c.toy);
			printf("removed %s (char %ld, t%d) at %d,%d\n",c.name,n,c.temp,c.x,c.y);
			c.used=USE_EMPTY;
			fseek(cf,n*sizeof(c),SEEK_SET); fwrite(&c,sizeof(c),1,cf); fseek(cf,(n+1)*sizeof(c),SEEK_SET);
			removed++;
		}
		n++;
	}
	fclose(cf); fclose(itf); fclose(mf);
	printf("%d NPC(s) removed\n",removed);
	return 0;
}
