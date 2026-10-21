/* Place items from templates on the map, optionally making new templates first.
 *   place_items <server .dat folder> <spec file>         (server stopped!)
 * Spec lines:
 *   newtemp <new> <copy-from> <name...>          new template = copy of another, with this name
 *   data <temp> <d0> <d1> <d2> <d3> <d4>         set a template's data[0..4]
 *   place <temp> <x> <y>                          put a copy of the template on that tile
 *   remove <x> <y>                                take the item off that tile
 * Lines starting with # are comments.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "gendefs.h"
#include "data.h"

static struct item ti[MAXTITEM];

int main(int argc,char **argv)
{
	char fn[512],line[512],name[200]; FILE *f,*sf,*itf,*mf; static struct item it; struct map m;
	int a,b,c,d0,d1,d2,d3,d4,n,ln=0,placed=0,made=0;

	sprintf(fn,"%s/titem.dat",argv[1]); f=fopen(fn,"r+b"); if (!f) { perror(fn); return 1; }
	fread(ti,sizeof(struct item),MAXTITEM,f);
	sf=fopen(argv[2],"r"); if (!sf) { perror(argv[2]); return 1; }
	sprintf(fn,"%s/item.dat",argv[1]); itf=fopen(fn,"r+b");
	sprintf(fn,"%s/map.dat",argv[1]); mf=fopen(fn,"r+b");
	while (fgets(line,sizeof(line),sf)) {
		ln++;
		if (line[0]=='#' || line[0]=='\n') continue;
		if (sscanf(line,"newtemp %d %d %199[^\n]",&a,&b,name)==3) {
			if (ti[a].used) { printf("line %d: template %d is already used, skipped\n",ln,a); continue; }
			ti[a]=ti[b]; ti[a].temp=a; strncpy(ti[a].name,name,sizeof(ti[a].name)-1); made++;
		} else if (sscanf(line,"data %d %d %d %d %d %d",&a,&d0,&d1,&d2,&d3,&d4)==6) {
			ti[a].data[0]=d0; ti[a].data[1]=d1; ti[a].data[2]=d2; ti[a].data[3]=d3; ti[a].data[4]=d4;
		} else if (sscanf(line,"place %d %d %d",&a,&b,&c)==3) {
			long mpos=(long)(b+c*MAPX)*sizeof(struct map);
			fseek(mf,mpos,SEEK_SET); fread(&m,sizeof(m),1,mf);
			if (m.it) { printf("line %d: tile %d,%d already has item %d, skipped\n",ln,b,c,m.it); continue; }
			for (n=1; n<MAXITEM; n++) { fseek(itf,(long)n*sizeof(it),SEEK_SET); if (fread(&it,sizeof(it),1,itf)!=1 || !it.used) break; }
			it=ti[a]; it.used=USE_ACTIVE; it.temp=a; it.x=b; it.y=c; it.carried=0;
			fseek(itf,(long)n*sizeof(it),SEEK_SET); fwrite(&it,sizeof(it),1,itf);
			m.it=n;	// blocking comes from the item flags at run time, like the original items
			fseek(mf,mpos,SEEK_SET); fwrite(&m,sizeof(m),1,mf);
			printf("%s placed as item %d at %d,%d\n",ti[a].name,n,b,c); placed++;
		} else if (sscanf(line,"remove %d %d",&b,&c)==2) {
			long mpos=(long)(b+c*MAPX)*sizeof(struct map);
			fseek(mf,mpos,SEEK_SET); fread(&m,sizeof(m),1,mf);
			if (!m.it) { printf("line %d: no item at %d,%d\n",ln,b,c); continue; }
			fseek(itf,(long)m.it*sizeof(it),SEEK_SET); fread(&it,sizeof(it),1,itf);
			printf("%s (item %d) removed from %d,%d\n",it.name,m.it,b,c);
			it.used=USE_EMPTY; fseek(itf,(long)m.it*sizeof(it),SEEK_SET); fwrite(&it,sizeof(it),1,itf);
			m.it=0; fseek(mf,mpos,SEEK_SET); fwrite(&m,sizeof(m),1,mf);
		} else printf("line %d not understood: %s",ln,line);
	}
	fseek(f,0,SEEK_SET); fwrite(ti,sizeof(struct item),MAXTITEM,f);
	fclose(f); fclose(itf); fclose(mf); fclose(sf);
	printf("%d new template(s), %d item(s) placed\n",made,placed);
	return 0;
}
