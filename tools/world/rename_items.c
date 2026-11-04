/* Rename the items of one template that are already in the world (lying around, carried, in depots):
 *   rename_items <.dat dir> <template> <old text> <new text> [write]
 * Replaces <old text> by <new text> (first match, case as given) in each item's name, reference and description.
 * Without "write" it only shows what it would do. Server stopped. Build: gcc -I server -o rename_items tools/world/rename_items.c */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gendefs.h"
#include "data.h"

static char tolower_c(char c) { return c>='A' && c<='Z' ? c+32 : c; }

static int repl(char *s,int size,const char *a,const char *b)
{
	char buf[512],*p=strstr(s,a);
	if (!p) return 0;
	snprintf(buf,sizeof(buf),"%.*s%s%s",(int)(p-s),s,b,p+strlen(a));
	strncpy(s,buf,size-1); s[size-1]=0;
	return 1;
}

int main(int argc,char **argv)
{
	char p[512]; FILE *f; static struct item I; int t,n=0,w; long i;
	if (argc<5) { fprintf(stderr,"usage: %s <.dat dir> <template> <old> <new> [write]\n",argv[0]); return 1; }
	t=atoi(argv[2]); w=argc>5 && !strcmp(argv[5],"write");
	snprintf(p,sizeof p,"%s/item.dat",argv[1]);
	if (!(f=fopen(p,w ? "r+b" : "rb"))) { perror(p); return 1; }
	for (i=0; i<MAXITEM; i++) {
		fseek(f,i*sizeof I,SEEK_SET);
		if (fread(&I,sizeof I,1,f)!=1) break;
		if (!I.used || I.temp!=t) continue;
		char old[40]; strncpy(old,I.name,39); old[39]=0;
		int k=repl(I.name,sizeof(I.name),argv[3],argv[4]);
		k|=repl(I.reference,sizeof(I.reference),argv[3],argv[4]);
		{ char lo[64],ln[64]; int j; for (j=0; argv[3][j] && j<63; j++) lo[j]=tolower_c(argv[3][j]); lo[j]=0;
		  for (j=0; argv[4][j] && j<63; j++) ln[j]=tolower_c(argv[4][j]); ln[j]=0;
		  k|=repl(I.reference,sizeof(I.reference),lo,ln); k|=repl(I.description,sizeof(I.description),lo,ln); }
		if (!k) continue;
		printf("item %ld (%s, carried by %u): %s\n",i,old,I.carried,I.name); n++;
		if (w) { fseek(f,i*sizeof I,SEEK_SET); fwrite(&I,sizeof I,1,f); }
	}
	fclose(f);
	printf("%d item(s)%s\n",n,w ? " renamed" : " would be renamed (add: write)");
	return 0;
}
