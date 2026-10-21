/* Sets the animation status of an item template and of every item made from it.
 *   fix_item_status <.dat folder> <template> <status0> <status1>   (server stopped!)
 * Used for Lab 11's brazier: status 16 (fire animation) belongs to the lit state only. */
#include <stdio.h>
#include <stdlib.h>
#include "gendefs.h"
#include "data.h"

static struct item t[MAXTITEM];

int main(int argc,char **argv)
{
	char fn[512]; FILE *f; static struct item it; int temp,s0,s1,n,cnt=0;

	if (argc!=5) { fprintf(stderr,"usage: %s <.dat folder> <template> <status0> <status1>\n",argv[0]); return 1; }
	temp=atoi(argv[2]); s0=atoi(argv[3]); s1=atoi(argv[4]);
	if (temp<1 || temp>=MAXTITEM) return 1;
	sprintf(fn,"%s/titem.dat",argv[1]); if (!(f=fopen(fn,"r+b"))) { perror(fn); return 1; }
	fread(t,sizeof(struct item),MAXTITEM,f);
	t[temp].status[0]=s0; t[temp].status[1]=s1;
	fseek(f,(long)temp*sizeof(struct item),SEEK_SET); fwrite(&t[temp],sizeof(struct item),1,f); fclose(f);
	sprintf(fn,"%s/item.dat",argv[1]); if (!(f=fopen(fn,"r+b"))) { perror(fn); return 1; }
	for (n=1; n<MAXITEM; n++) {
		fseek(f,(long)n*sizeof(it),SEEK_SET); if (fread(&it,sizeof(it),1,f)!=1) break;
		if (!it.used || it.temp!=temp) continue;
		it.status[0]=s0; it.status[1]=s1;
		fseek(f,(long)n*sizeof(it),SEEK_SET); fwrite(&it,sizeof(it),1,f); cnt++;
	}
	fclose(f);
	printf("%s (%d): status %d/%d, %d item(s) updated\n",t[temp].name,temp,s0,s1,cnt);
	return 0;
}
