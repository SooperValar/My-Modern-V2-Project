/* One-off: open Lab 10 (Seasons Gorge) between Lab 9 and the Final Test.
 *   lab10_open <server .dat folder>        (server stopped!)
 * - Lab 9's end portal (template 1099 + its copies) leads to Lab 10's inn (52,838)
 * - Lab 10's end portal (1299 + copies) leads on to the Final Test (33,597)
 * - the hourglass needs four pieces: Top (Flora), Middle (Friga), Bottom (Aestas)
 *   and the new Sands of Time (Casas); Top+Middle+Bottom make the new Empty
 *   Hourglass, + Sands = Hourglass of Time, which takes you into the end room
 * Sprites 18121-18128 go in the client's gfx folder (tools/sprites/draw_hourglass.py).
 */
#include <stdio.h>
#include <string.h>
#include "gendefs.h"
#include "data.h"

#define T_TOP 1285
#define T_MID 1286
#define T_BOT 1287
#define T_TM  1288
#define T_MB  1289
#define T_FULL 1290
#define T_EMPTY 1313
#define T_SAND 1314

static struct item ti[MAXTITEM];

static void combo(int t,int a,int ra,int b,int rb)
{ ti[t].data[0]=a; ti[t].data[1]=ra; ti[t].data[2]=b; ti[t].data[3]=rb; }

static void sync(struct item *i)	// an item copy gets its template's new values
{
	int t=i->temp;
	if (t<T_TOP || (t>T_FULL && t!=T_EMPTY && t!=T_SAND)) return;
	memcpy(i->name,ti[t].name,sizeof(i->name)); memcpy(i->reference,ti[t].reference,sizeof(i->reference));
	memcpy(i->description,ti[t].description,sizeof(i->description));
	memcpy(i->data,ti[t].data,sizeof(i->data));
	i->driver=ti[t].driver; i->flags=ti[t].flags; i->sprite[0]=ti[t].sprite[0]; i->sprite[1]=ti[t].sprite[1];
}

int main(int argc,char **argv)
{
	char fn[512]; FILE *f; static struct item it; static struct character c; int n,cnt=0;

	sprintf(fn,"%s/titem.dat",argv[1]); f=fopen(fn,"r+b"); if (!f) { perror(fn); return 1; }
	fread(ti,sizeof(struct item),MAXTITEM,f);
	if (ti[T_EMPTY].used || ti[T_SAND].used) { printf("templates %d/%d already used - already patched?\n",T_EMPTY,T_SAND); return 1; }

	ti[1099].data[0]=52; ti[1099].data[1]=838;		// Lab 9 end -> Lab 10 inn
	ti[1299].data[0]=33; ti[1299].data[1]=597;		// Lab 10 end -> Final Test

	combo(T_TOP,T_MID,T_TM,T_MB,T_EMPTY);
	combo(T_MID,T_TOP,T_TM,T_BOT,T_MB);
	combo(T_BOT,T_MID,T_MB,T_TM,T_EMPTY);
	combo(T_TM,T_BOT,T_EMPTY,0,0);
	combo(T_MB,T_TOP,T_EMPTY,0,0);
	strcpy(ti[T_TM].description,"Top and middle of an hourglass. The bottom is missing.");
	strcpy(ti[T_MB].description,"Middle and bottom of an hourglass. The top is missing.");
	ti[T_TM].sprite[0]=18124; ti[T_MB].sprite[0]=18125;

	ti[T_EMPTY]=ti[T_TM]; ti[T_EMPTY].temp=T_EMPTY;
	strcpy(ti[T_EMPTY].name,"Empty Hourglass"); strcpy(ti[T_EMPTY].reference,"empty hourglass");
	strcpy(ti[T_EMPTY].description,"A whole hourglass, but there is no sand in it.");
	ti[T_EMPTY].sprite[0]=18128; combo(T_EMPTY,T_SAND,T_FULL,0,0);

	ti[T_SAND]=ti[T_BOT]; ti[T_SAND].temp=T_SAND;
	strcpy(ti[T_SAND].name,"Sands of Time"); strcpy(ti[T_SAND].reference,"sands of time");
	strcpy(ti[T_SAND].description,"A handful of glittering golden sand. It never stops moving.");
	ti[T_SAND].sprite[0]=18127; combo(T_SAND,T_EMPTY,T_FULL,0,0);

	strcpy(ti[T_FULL].name,"Hourglass of Time"); strcpy(ti[T_FULL].reference,"hourglass of time");
	strcpy(ti[T_FULL].description,"The sand inside flows upwards. Use it to step through time.");
	ti[T_FULL].driver=70; ti[T_FULL].flags|=IF_USE|IF_USESPECIAL; ti[T_FULL].sprite[0]=18126;

	fseek(f,0,SEEK_SET); fwrite(ti,sizeof(struct item),MAXTITEM,f); fclose(f);
	printf("titem.dat patched\n");

	// tchar: Casas carries the sands instead of a second bottom
	sprintf(fn,"%s/tchar.dat",argv[1]); f=fopen(fn,"r+b");
	fseek(f,1112L*sizeof(c),SEEK_SET); fread(&c,sizeof(c),1,f);
	for (n=0; n<40; n++) if (c.item[n]==T_BOT) { c.item[n]=T_SAND; cnt++; }
	fseek(f,1112L*sizeof(c),SEEK_SET); fwrite(&c,sizeof(c),1,f); fclose(f);
	printf("tchar.dat: Casas template %d item(s) changed\n",cnt);

	// item.dat: the copies in the world
	sprintf(fn,"%s/item.dat",argv[1]); f=fopen(fn,"r+b"); cnt=0;
	{
		static struct character C[MAXCHARS]; char cf[512]; FILE *g; int casas_items[40],nc=0;
		sprintf(cf,"%s/char.dat",argv[1]); g=fopen(cf,"rb"); fread(C,sizeof(struct character),MAXCHARS,g); fclose(g);
		for (n=1; n<MAXCHARS; n++) if (C[n].used && C[n].temp==1112) { int m; for (m=0; m<40; m++) if (C[n].item[m]) casas_items[nc++]=C[n].item[m]; }
		for (n=0; n<MAXITEM; n++) {
			long pos=(long)n*sizeof(it); int m,changed=0;
			fseek(f,pos,SEEK_SET); if (fread(&it,sizeof(it),1,f)!=1) break;
			if (!it.used) continue;
			for (m=0; m<nc; m++) if (casas_items[m]==n && it.temp==T_BOT) { it.temp=T_SAND; changed=1; }
			if (it.temp==1099) { it.data[0]=52; it.data[1]=838; changed=1; }
			if (it.temp==1299) { it.data[0]=33; it.data[1]=597; changed=1; }
			if ((it.temp>=T_TOP && it.temp<=T_FULL) || it.temp==T_SAND || it.temp==T_EMPTY) { sync(&it); changed=1; }
			if (changed) { fseek(f,pos,SEEK_SET); fwrite(&it,sizeof(it),1,f); cnt++; }
		}
	}
	fclose(f);
	printf("item.dat: %d item(s) updated\n",cnt);
	return 0;
}
