/* Builds an area from a spec file: map tiles, item and character templates,
 * placed items.        build_lab <server .dat folder> <spec file>   (server stopped!)
 * Afterwards run "server pop" (creates the new NPCs) and "server light".
 *
 * Spec lines (# = comment):
 *   tile <x> <y> <sprite> <fsprite> <flags hex>   set a map tile (keeps its item)
 *   it <temp> copy <from>                          new item template = copy of another
 *   it <temp> name|ref|desc <text...>
 *   it <temp> spr <s0> <s1> | flags <hex> | light <l0> <l1> | dur <ticks> | value <v>
 *   it <temp> d <i> <value>                        data[i]
 *   it <temp> driver <n>                           item driver
 *   it <temp> status <s0> <s1>                     animation (client): 0/1 still, 16 = 4-frame loop, ...
 *   place <temp> <x> <y>                           put a copy of the item template there
 *   clear <x0> <y0> <x1> <y1>                      remove every item lying in that rectangle
 *   killnpc <temp>                                 remove the living NPC(s) of that template ("server pop" makes new ones)
 *   movenpc <temp>                                 move the living NPC(s) of that template to its spawn position
 *   settemp <x> <y> <temp>                         fix the template number of the item on that tile
 *   ch <temp> copy <from>                          new character template = copy of another
 *   ch <temp> name|ref|desc <text...>
 *   ch <temp> pos <x> <y>                          spawn position (also the resting position)
 *   ch <temp> scale <percent>                      attributes, hp/end/mana and skills
 *   ch <temp> d <i> <value>                        data[i]
 *   ch <temp> setflags <hex> | clrflags <hex>
 *   ch <temp> items <temp>...                      backpack (also a merchant's stock)
 *   ch <temp> text <i> <text...>
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "gendefs.h"
#include "data.h"

static struct item ti[MAXTITEM];
static struct character tc[MAXTCHARS];
static char touched[MAXTCHARS];

/* experience value of a template, as reset_char() works it out */
static int template_points(struct character *t)
{
	int z,m,pts=0;
	for (z=0; z<5; z++) for (m=10; m<t->attrib[z][0]; m++) pts+=m*m*m*3/20;
	for (m=50; m<t->hp[0]; m++) pts+=m*3;
	for (m=50; m<t->end[0]; m++) pts+=m*2/2;
	for (m=50; m<t->mana[0]; m++) pts+=m*3;
	for (z=0; z<50; z++) {
		if (z==SK_PERCEPT || z==SK_STEALTH || z==SK_LOCK) continue;
		for (m=1; m<t->skill[z][0]; m++) { int v=m*m*m*2/40; pts+= v>m ? v : m; }
	}
	return pts;
}

static int sane_it(int n,int ln) { if (n<1 || n>=MAXTITEM) { printf("line %d: bad item template %d\n",ln,n); return 0; } return 1; }
static int sane_ch(int n,int ln) { if (n<1 || n>=MAXTCHARS) { printf("line %d: bad char template %d\n",ln,n); return 0; } return 1; }

int main(int argc,char **argv)
{
	char fn[512],line[1024],word[64],text[800]; FILE *tif,*tcf,*sf,*itf,*mf; static struct item it; struct map m;
	int a,b,c,d,i,n,ln=0,placed=0,tiles=0,lastit=1,off;
	unsigned long long fl;

	if (argc!=3) { fprintf(stderr,"usage: %s <.dat folder> <spec>\n",argv[0]); return 1; }
	sprintf(fn,"%s/titem.dat",argv[1]); tif=fopen(fn,"r+b"); if (!tif) { perror(fn); return 1; }
	fread(ti,sizeof(struct item),MAXTITEM,tif);
	sprintf(fn,"%s/tchar.dat",argv[1]); tcf=fopen(fn,"r+b"); if (!tcf) { perror(fn); return 1; }
	fread(tc,sizeof(struct character),MAXTCHARS,tcf);
	sprintf(fn,"%s/item.dat",argv[1]); itf=fopen(fn,"r+b"); if (!itf) { perror(fn); return 1; }
	sprintf(fn,"%s/map.dat",argv[1]); mf=fopen(fn,"r+b"); if (!mf) { perror(fn); return 1; }
	sf=fopen(argv[2],"r"); if (!sf) { perror(argv[2]); return 1; }

	while (fgets(line,sizeof(line),sf)) {
		ln++;
		line[strcspn(line,"\r\n")]=0;
		if (line[0]=='#' || !line[0]) continue;
		text[0]=0;

		if (sscanf(line,"tile %d %d %d %d %llx",&a,&b,&c,&d,&fl)==5) {
			long mpos=(long)(a+b*MAPX)*sizeof(struct map);
			fseek(mf,mpos,SEEK_SET); fread(&m,sizeof(m),1,mf);
			m.sprite=c; m.fsprite=d; m.flags=fl; m.light=0; m.dlight=0;
			fseek(mf,mpos,SEEK_SET); fwrite(&m,sizeof(m),1,mf); tiles++;

		} else if (sscanf(line,"it %d %63s %n",&a,word,&off)==2) {
			if (!sane_it(a,ln)) continue;
			strncpy(text,line+off,sizeof(text)-1);
			if (!strcmp(word,"copy")) { b=atoi(text); if (!sane_it(b,ln)) continue;
				if (ti[a].used) printf("line %d: item template %d was used (%s), overwritten\n",ln,a,ti[a].name);
				ti[a]=ti[b]; ti[a].temp=a; ti[a].used=USE_ACTIVE; }
			else if (!strcmp(word,"name")) { strncpy(ti[a].name,text,39); ti[a].name[39]=0; }
			else if (!strcmp(word,"ref")) { strncpy(ti[a].reference,text,39); ti[a].reference[39]=0; }
			else if (!strcmp(word,"desc")) { strncpy(ti[a].description,text,199); ti[a].description[199]=0; }
			else if (!strcmp(word,"spr")) sscanf(text,"%hd %hd",&ti[a].sprite[0],&ti[a].sprite[1]);
			else if (!strcmp(word,"flags")) sscanf(text,"%llx",&ti[a].flags);
			else if (!strcmp(word,"light")) sscanf(text,"%hd %hd",&ti[a].light[0],&ti[a].light[1]);
			else if (!strcmp(word,"status") && sscanf(text,"%d %d",&i,&b)==2) { ti[a].status[0]=i; ti[a].status[1]=b; }
			else if (!strcmp(word,"driver")) ti[a].driver=atoi(text);
			else if (!strcmp(word,"dur")) ti[a].duration=atoi(text);
			else if (!strcmp(word,"value")) ti[a].value=atoi(text);
			else if (!strcmp(word,"d") && sscanf(text,"%d %d",&i,&b)==2 && i>=0 && i<10) ti[a].data[i]=b;
			else printf("line %d not understood: %s\n",ln,line);

		} else if (sscanf(line,"place %d %d %d",&a,&b,&c)==3) {
			long mpos=(long)(b+c*MAPX)*sizeof(struct map);
			if (!sane_it(a,ln) || !ti[a].used) { printf("line %d: template %d unused\n",ln,a); continue; }
			fseek(mf,mpos,SEEK_SET); fread(&m,sizeof(m),1,mf);
			if (m.it) { printf("line %d: tile %d,%d already has item %d, skipped\n",ln,b,c,m.it); continue; }
			for (n=lastit; n<MAXITEM; n++) { fseek(itf,(long)n*sizeof(it),SEEK_SET); if (fread(&it,sizeof(it),1,itf)!=1 || !it.used) break; }
			if (n>=MAXITEM) { printf("line %d: no free item\n",ln); continue; }
			lastit=n+1;
			it=ti[a]; it.used=USE_ACTIVE; it.temp=a; it.x=b; it.y=c; it.carried=0; it.active=0;
			fseek(itf,(long)n*sizeof(it),SEEK_SET); fwrite(&it,sizeof(it),1,itf);
			m.it=n;
			fseek(mf,mpos,SEEK_SET); fwrite(&m,sizeof(m),1,mf);
			placed++;

		} else if (sscanf(line,"clear %d %d %d %d",&a,&b,&c,&d)==4) {
			int x,y,cnt=0;
			for (y=b; y<=d; y++) for (x=a; x<=c; x++) {
				long mpos=(long)(x+y*MAPX)*sizeof(struct map);
				fseek(mf,mpos,SEEK_SET); fread(&m,sizeof(m),1,mf);
				if (!m.it) continue;
				fseek(itf,(long)m.it*sizeof(it),SEEK_SET); fread(&it,sizeof(it),1,itf);
				it.used=USE_EMPTY; fseek(itf,(long)m.it*sizeof(it),SEEK_SET); fwrite(&it,sizeof(it),1,itf);
				m.it=0; fseek(mf,mpos,SEEK_SET); fwrite(&m,sizeof(m),1,mf); cnt++;
			}
			printf("cleared %d item(s) from %d,%d - %d,%d\n",cnt,a,b,c,d);

		} else if (sscanf(line,"killnpc %d",&a)==1) {
			static struct character cc; FILE *cf; long mpos; int k;
			if (!sane_ch(a,ln)) continue;
			sprintf(fn,"%s/char.dat",argv[1]); if (!(cf=fopen(fn,"r+b"))) { perror(fn); continue; }
			for (n=1; n<MAXCHARS; n++) {
				fseek(cf,(long)n*sizeof(cc),SEEK_SET); if (fread(&cc,sizeof(cc),1,cf)!=1) break;
				if (!cc.used || cc.temp!=a || (cc.flags&CF_PLAYER)) continue;
				if (cc.x>0 && cc.y>0) {
					mpos=(long)(cc.x+cc.y*MAPX)*sizeof(struct map);
					fseek(mf,mpos,SEEK_SET); fread(&m,sizeof(m),1,mf);
					if (m.ch==(unsigned)n) { m.ch=0; fseek(mf,mpos,SEEK_SET); fwrite(&m,sizeof(m),1,mf); }
				}
				for (k=0; k<60+1; k++) {	/* backpack, worn, cursor item */
					unsigned int in2= k<40 ? cc.item[k] : (k<60 ? cc.worn[k-40] : cc.citem);
					if (!in2 || (in2&0x80000000) || in2>=MAXITEM) continue;
					fseek(itf,(long)in2*sizeof(it),SEEK_SET); fread(&it,sizeof(it),1,itf);
					it.used=USE_EMPTY; fseek(itf,(long)in2*sizeof(it),SEEK_SET); fwrite(&it,sizeof(it),1,itf);
				}
				cc.used=USE_EMPTY;
				fseek(cf,(long)n*sizeof(cc),SEEK_SET); fwrite(&cc,sizeof(cc),1,cf);
				printf("%s (%d) at %d,%d removed\n",cc.name,n,cc.x,cc.y);
			}
			fclose(cf);

		} else if (sscanf(line,"movenpc %d",&a)==1) {
			static struct character cc; FILE *cf; long mpos; int nx,ny;
			if (!sane_ch(a,ln)) continue;
			nx=tc[a].x; ny=tc[a].y;
			sprintf(fn,"%s/char.dat",argv[1]); if (!(cf=fopen(fn,"r+b"))) { perror(fn); continue; }
			for (n=1; n<MAXCHARS; n++) {
				fseek(cf,(long)n*sizeof(cc),SEEK_SET); if (fread(&cc,sizeof(cc),1,cf)!=1) break;
				if (cc.used!=USE_ACTIVE || cc.temp!=a || (cc.flags&(CF_PLAYER|CF_BODY))) continue;
				if (cc.x>0 && cc.y>0) {
					mpos=(long)(cc.x+cc.y*MAPX)*sizeof(struct map);
					fseek(mf,mpos,SEEK_SET); fread(&m,sizeof(m),1,mf);
					if (m.ch==(unsigned)n) { m.ch=0; fseek(mf,mpos,SEEK_SET); fwrite(&m,sizeof(m),1,mf); }
				}
				mpos=(long)(nx+ny*MAPX)*sizeof(struct map);
				fseek(mf,mpos,SEEK_SET); fread(&m,sizeof(m),1,mf);
				if (m.ch) { printf("line %d: %d,%d is taken, %s not moved\n",ln,nx,ny,cc.name); continue; }
				m.ch=n; fseek(mf,mpos,SEEK_SET); fwrite(&m,sizeof(m),1,mf);
				printf("%s (%d) moved from %d,%d to %d,%d\n",cc.name,n,cc.x,cc.y,nx,ny);
				cc.x=cc.tox=nx; cc.y=cc.toy=ny; cc.data[29]=tc[a].data[29];
				fseek(cf,(long)n*sizeof(cc),SEEK_SET); fwrite(&cc,sizeof(cc),1,cf);
			}
			fclose(cf);

		} else if (sscanf(line,"settemp %d %d %d",&a,&b,&c)==3) {
			long mpos=(long)(a+b*MAPX)*sizeof(struct map);
			fseek(mf,mpos,SEEK_SET); fread(&m,sizeof(m),1,mf);
			if (!m.it) { printf("line %d: no item at %d,%d\n",ln,a,b); continue; }
			fseek(itf,(long)m.it*sizeof(it),SEEK_SET); fread(&it,sizeof(it),1,itf);
			it.temp=c; fseek(itf,(long)m.it*sizeof(it),SEEK_SET); fwrite(&it,sizeof(it),1,itf);
			printf("%s at %d,%d: template set to %d\n",it.name,a,b,c);

		} else if (sscanf(line,"ch %d %63s %n",&a,word,&off)==2) {
			struct character *t=&tc[a];
			if (!sane_ch(a,ln)) continue;
			touched[a]=1;
			strncpy(text,line+off,sizeof(text)-1);
			if (!strcmp(word,"copy")) { b=atoi(text); if (!sane_ch(b,ln)) continue;
				if (tc[a].used) printf("line %d: char template %d was used (%s), overwritten\n",ln,a,tc[a].name);
				tc[a]=tc[b]; tc[a].temp=a; tc[a].used=USE_ACTIVE; }
			else if (!strcmp(word,"name")) { strncpy(t->name,text,39); t->name[39]=0; }
			else if (!strcmp(word,"ref")) { strncpy(t->reference,text,39); t->reference[39]=0; }
			else if (!strcmp(word,"desc")) { strncpy(t->description,text,LENDESC-1); t->description[LENDESC-1]=0; }
			else if (!strcmp(word,"pos") && sscanf(text,"%d %d",&b,&c)==2) { t->x=b; t->y=c; t->data[29]=b+c*MAPX; }
			else if (!strcmp(word,"scale")) { int p=atoi(text),z,v;
				for (z=0; z<5; z++) { v=t->attrib[z][0]*p/100; if (v>250) v=250; t->attrib[z][0]=v; if (t->attrib[z][2]<v) t->attrib[z][2]=v; }
				v=t->hp[0]*p/100; if (v>999) v=999; t->hp[0]=v; if (t->hp[2]<v) t->hp[2]=v;
				v=t->end[0]*p/100; if (v>999) v=999; t->end[0]=v; if (t->end[2]<v) t->end[2]=v;
				v=t->mana[0]*p/100; if (v>999) v=999; t->mana[0]=v; if (t->mana[2]<v) t->mana[2]=v;
				for (z=0; z<50; z++) if (t->skill[z][0]) { v=t->skill[z][0]*p/100; if (v>250) v=250; t->skill[z][0]=v; if (t->skill[z][2]<v) t->skill[z][2]=v; } }
			else if (!strcmp(word,"d") && sscanf(text,"%d %d",&i,&b)==2 && i>=0 && i<100) t->data[i]=b;
			else if (!strcmp(word,"setflags")) { sscanf(text,"%llx",&fl); t->flags|=fl; }
			else if (!strcmp(word,"clrflags")) { sscanf(text,"%llx",&fl); t->flags&=~fl; }
			else if (!strcmp(word,"items")) { char *p=text; for (i=0; i<40; i++) { t->item[i]=(int)strtol(p,&p,10); } }
			else if (!strcmp(word,"text") && sscanf(text,"%d %n",&i,&off)==1 && i>=0 && i<10) { strncpy(t->text[i],text+off,sizeof(t->text[i])-1); t->text[i][sizeof(t->text[i])-1]=0; }
			else printf("line %d not understood: %s\n",ln,line);

		} else printf("line %d not understood: %s\n",ln,line);
	}
	for (n=1; n<MAXTCHARS; n++) if (touched[n] && tc[n].used) tc[n].points_tot=template_points(&tc[n]);
	fseek(tif,0,SEEK_SET); fwrite(ti,sizeof(struct item),MAXTITEM,tif);
	fseek(tcf,0,SEEK_SET); fwrite(tc,sizeof(struct character),MAXTCHARS,tcf);
	fclose(tif); fclose(tcf); fclose(itf); fclose(mf); fclose(sf);
	printf("%d tiles set, %d items placed\n",tiles,placed);
	return 0;
}
