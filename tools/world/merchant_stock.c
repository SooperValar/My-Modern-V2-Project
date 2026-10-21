/* Sets the stock of a merchant template: its backpack (up to 40 item
 * templates), which update_shop() keeps restocked.
 *   merchant_stock <.dat dir> <char template> <item template>...
 * Run with the server stopped. Build against server/data.h:
 *   gcc -I server -o merchant_stock tools/world/merchant_stock.c */
#include <stdio.h>
#include <stdlib.h>
#include "gendefs.h"
#include "data.h"

static struct character c;
static struct item t[MAXTITEM];

int main(int argc,char **argv)
{
        char p[512]; FILE *f,*g; int id,n,cnt=argc-3;

        if (argc<4 || cnt>40) { fprintf(stderr,"usage: %s <.dat dir> <char template> <item template>... (max 40)\n",argv[0]); return 1; }
        snprintf(p,sizeof p,"%s/titem.dat",argv[1]);
        if (!(g=fopen(p,"rb")) || fread(t,sizeof(struct item),MAXTITEM,g)!=MAXTITEM) { perror(p); return 1; }
        fclose(g);
        snprintf(p,sizeof p,"%s/tchar.dat",argv[1]);
        if (!(f=fopen(p,"r+b"))) { perror(p); return 1; }
        id=atoi(argv[2]);
        if (id<1 || id>=MAXTCHARS) return 1;
        fseek(f,(long)id*sizeof c,SEEK_SET); fread(&c,sizeof c,1,f);
        if (!c.used || !(c.flags&CF_MERCHANT)) { fprintf(stderr,"%d (%s) is not a merchant template\n",id,c.name); return 1; }
        for (n=0; n<cnt; n++) {
                int in=atoi(argv[3+n]);
                if (in<1 || in>=MAXTITEM || !t[in].used) { fprintf(stderr,"bad item template %d\n",in); return 1; }
        }
        for (n=0; n<40; n++) c.item[n]= n<cnt ? atoi(argv[3+n]) : 0;
        fseek(f,(long)id*sizeof c,SEEK_SET); fwrite(&c,sizeof c,1,f); fclose(f);
        printf("%d (%s) now stocks %d items:\n",id,c.name,cnt);
        for (n=0; n<cnt; n++) printf("  %d %s\n",c.item[n],t[c.item[n]].name);
        return 0;
}
