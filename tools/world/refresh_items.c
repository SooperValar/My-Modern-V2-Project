/* Copy the stats of item templates onto the items of those templates that are already in the world
 * (lying around, carried, worn, in depots): armor, attribute / skill bonuses and requirements, hp / end / mana,
 * light, damage to attackers, weapon value, value, the unique flag. Keeps everything else (where it is, who has it, its state).
 *   refresh_items <.dat dir> <template>... [names] [write]   without "write" it only shows what it would do;
 *   "names" also copies the name, reference and description
 * Server stopped. Build: gcc -I server -o refresh_items tools/world/refresh_items.c */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gendefs.h"
#include "data.h"

int main(int argc,char **argv)
{
	char p[512]; FILE *tf,*f; static struct item T,I; int temps[64],nt=0,w=0,nm=0,n=0,k,a; long i;
	for (a=2; a<argc; a++) { if (!strcmp(argv[a],"write")) w=1; else if (!strcmp(argv[a],"names")) nm=1; else if (nt<64) temps[nt++]=atoi(argv[a]); }
	if (argc<3 || !nt) { fprintf(stderr,"usage: %s <.dat dir> <template>... [write]\n",argv[0]); return 1; }
	snprintf(p,sizeof p,"%s/titem.dat",argv[1]); if (!(tf=fopen(p,"rb"))) { perror(p); return 1; }
	snprintf(p,sizeof p,"%s/item.dat",argv[1]); if (!(f=fopen(p,w ? "r+b" : "rb"))) { perror(p); return 1; }
	for (i=0; i<MAXITEM; i++) {
		fseek(f,i*sizeof I,SEEK_SET);
		if (fread(&I,sizeof I,1,f)!=1) break;
		if (!I.used) continue;
		for (k=0; k<nt && temps[k]!=I.temp; k++) ;
		if (k==nt) continue;
		fseek(tf,(long)I.temp*sizeof T,SEEK_SET);
		if (fread(&T,sizeof T,1,tf)!=1) continue;
		printf("item %ld %s (template %d, carried by %d, at %d,%d): armor %d -> %d\n",i,I.name,I.temp,I.carried,I.x,I.y,I.armor[0],T.armor[0]);
		memcpy(I.armor,T.armor,sizeof I.armor);
		memcpy(I.attrib,T.attrib,sizeof I.attrib);
		memcpy(I.skill,T.skill,sizeof I.skill);
		memcpy(I.hp,T.hp,sizeof I.hp); memcpy(I.end,T.end,sizeof I.end); memcpy(I.mana,T.mana,sizeof I.mana);
		memcpy(I.weapon,T.weapon,sizeof I.weapon);
		memcpy(I.light,T.light,sizeof I.light); memcpy(I.gethit_dam,T.gethit_dam,sizeof I.gethit_dam);
		I.value=T.value;
		if (nm) { printf("  name %s -> %s\n",I.name,T.name); memcpy(I.name,T.name,sizeof I.name); memcpy(I.reference,T.reference,sizeof I.reference); memcpy(I.description,T.description,sizeof I.description); }
		I.flags=(I.flags&~IF_UNIQUE)|(T.flags&IF_UNIQUE);	// unique or not, like the template
		if (w) { fseek(f,i*sizeof I,SEEK_SET); fwrite(&I,sizeof I,1,f); }
		n++;
	}
	printf("%d item(s)%s\n",n,w ? " updated" : " would be updated (add \"write\")");
	return 0;
}
