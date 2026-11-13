/*************************************************************************

MyV2: waypoints. A waypoint is a 3x3 circle on the ground. A player who
clicks it has found it; the client then shows the travel window with every
waypoint, and the player may travel, for free, to any other waypoint he has
found. Standing at a waypoint is needed to travel.

The waypoints are kept in .dat/waypoints.dat (written by the MyV2 Editor's
Waypoints tab; "wpreload" on the console reads it again):

    next <n>                                        the next free number
    wp <nr> <x> <y> <look> <picture> <name>|<line>  one waypoint, in list order

nr 1-255, never used twice (so a deleted waypoint is not "found" by anybody
when a new one is made); x y the middle of the circle; look 0 = rune circle
(sprites 18300-18308, lit +10), 1 = pentagram (18320-18328, lit +10);
picture = the sprite shown in the travel window (0: a stock picture).

The nine ground pieces are items the server makes and removes itself from
this list (item driver 76, no template): nothing to place by hand. A player
sees the lit (blue) pieces of the waypoints he has found (wp_item_sprite).

Who found what: .dat/wpfound.dat, a row per character (256 bits), like
clears.dat.

*************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>

#include "server.h"

#define WP_FILE		DATDIR"/waypoints.dat"
#define WPF_FILE	DATDIR"/wpfound.dat"
#define WP_DRIVER	76
#define MAXWP		256		// numbers 1-255
#define WP_SHOWN	200		// rows sent to a client at most
#define WP_CLIENT	0x020F05	// the first client with the travel window
#define WP_HDR		16
#define WP_SOUND	19		// sfx/19.wav (new with client 2.15.05)

struct waypoint { int nr,x,y,look,pic; char name[32],line[40]; };
static struct waypoint wp[MAXWP];
static int nwp=0,wp_loaded=0;

struct wprow { int stamp; unsigned char found[MAXWP/8]; };
static struct wprow *wprows=NULL;
static unsigned char *wphave=NULL;
static int wpfd=-2;

static int wp_base(int look) { return look==1 ? 18320 : 18300; }

/* ---- who found what ---- */

static void wpf_open(void)
{
	char hdr[WP_HDR];
	wpfd=open(WPF_FILE,O_RDWR|O_CREAT,0600);
	if (wpfd<0) { xlog("cannot open %s",WPF_FILE); return; }
	if (pread(wpfd,hdr,WP_HDR,0)==WP_HDR && !memcmp(hdr,"MYV2WPF1",8)) return;
	memset(hdr,0,WP_HDR); memcpy(hdr,"MYV2WPF1",8); *(int*)(hdr+8)=MAXWP;
	if (pwrite(wpfd,hdr,WP_HDR,0)!=WP_HDR) xlog("cannot write %s",WPF_FILE);
}

static struct wprow *wprow(int co)
{
	struct wprow *r;
	if (co<1 || co>=MAXCHARS) return NULL;
	if (!wprows) {
		wprows=calloc(MAXCHARS,sizeof(struct wprow)); wphave=calloc(MAXCHARS,1);
		if (!wprows || !wphave) { xlog("waypoints: out of memory"); wprows=NULL; return NULL; }
	}
	r=wprows+co;
	if (!wphave[co]) {
		if (wpfd==-2) wpf_open();
		if (wpfd<0 || pread(wpfd,r,sizeof(*r),WP_HDR+(off_t)co*sizeof(*r))!=sizeof(*r)) memset(r,0,sizeof(*r));
		wphave[co]=1;
	}
	if (r->stamp!=(int)ch[co].creation_date) { memset(r,0,sizeof(*r)); r->stamp=ch[co].creation_date; }	// another character in this slot
	return r;
}

static void wprow_put(int co)
{
	struct wprow *r=wprows+co;
	if (wpfd>=0 && pwrite(wpfd,r,sizeof(*r),WP_HDR+(off_t)co*sizeof(*r))!=sizeof(*r)) xlog("cannot write %s",WPF_FILE);
}

static int wp_found(int co,int nr)
{
	struct wprow *r=wprow(co);
	if (!r || nr<1 || nr>=MAXWP) return 0;
	return (r->found[nr>>3]>>(nr&7))&1;
}

static void wp_setfound(int co,int nr,int on)
{
	struct wprow *r=wprow(co);
	if (!r || nr<1 || nr>=MAXWP) return;
	if (on) r->found[nr>>3]|=(unsigned char)(1<<(nr&7)); else r->found[nr>>3]&=(unsigned char)~(1<<(nr&7));
	wprow_put(co);
}

/* ---- the list and its ground pieces ---- */

/* the waypoint (index) whose circle, plus "reach" tiles around it, holds x,y; -1 none */
static int wp_at(int x,int y,int reach)
{
	int n;
	for (n=0; n<nwp; n++) if (abs(x-wp[n].x)<=1+reach && abs(y-wp[n].y)<=1+reach) return n;
	return -1;
}

static void wp_make_piece(int w,int dx,int dy)
{
	int x=wp[w].x+dx,y=wp[w].y+dy,m,in,spr;
	if (!SANEXY(x,y)) return;
	m=x+y*MAPX; spr=wp_base(wp[w].look)+(dx+1)*3+(dy+1);
	if ((in=map[m].it)!=0) {
		if (IS_SANEITEM(in) && it[in].driver==WP_DRIVER && it[in].temp==0) {	// ours already: keep it up to date
			it[in].sprite[0]=it[in].sprite[1]=(short)spr;
			snprintf(it[in].description,sizeof(it[in].description),"A waypoint: %s.",wp[w].name);
		} else xlog("waypoint %d (%s): %d,%d holds another item (%s), no circle piece there",wp[w].nr,wp[w].name,x,y,IS_SANEITEM(in) ? it[in].name : "?");
		return;
	}
	in=get_free_item();
	if (!in) { xlog("waypoints: no free item"); return; }
	memset(&it[in],0,sizeof(struct item));
	it[in].used=USE_ACTIVE;
	strcpy(it[in].name,"Waypoint"); strcpy(it[in].reference,"waypoint");
	snprintf(it[in].description,sizeof(it[in].description),"A waypoint: %s.",wp[w].name);
	it[in].flags=IF_LOOK|IF_USE|IF_USESPECIAL|IF_NOEXPIRE;
	it[in].sprite[0]=it[in].sprite[1]=(short)spr;
	it[in].driver=WP_DRIVER;
	it[in].x=(unsigned short)x; it[in].y=(unsigned short)y;
	map[m].it=in;
}

/* make the pieces of every waypoint, remove the pieces that belong to none. Returns pieces removed. */
static int wp_sync_items(void)
{
	int n,dx,dy,in,x,y,gone=0;

	for (in=1; in<MAXITEM; in++) {
		if (it[in].used==USE_EMPTY || it[in].driver!=WP_DRIVER || it[in].temp!=0 || it[in].carried) continue;
		x=it[in].x; y=it[in].y;
		if (wp_at(x,y,0)>=0) continue;
		if (SANEXY(x,y) && map[x+y*MAPX].it==in) map[x+y*MAPX].it=0;
		it[in].used=USE_EMPTY; gone++;
	}
	for (n=0; n<nwp; n++)
		for (dx=-1; dx<=1; dx++) for (dy=-1; dy<=1; dy++) wp_make_piece(n,dx,dy);
	return gone;
}

/* read the list. Returns the number of waypoints, -1 if the file can't be read (the list stays as it was;
 * no file at all = no waypoints). */
int wp_load(void)
{
	static struct waypoint tmp[MAXWP];
	FILE *fp; char line[256],*s,*t; int n=0,nr,x,y,look,pic,off,k;

	wp_loaded=1;
	fp=fopen(WP_FILE,"r");
	if (fp) {
		while (fgets(line,sizeof(line),fp)) {
			line[strcspn(line,"\r\n")]=0;
			if (strncmp(line,"wp ",3)) continue;
			if (sscanf(line+3,"%d %d %d %d %d %n",&nr,&x,&y,&look,&pic,&off)<5) continue;
			if (nr<1 || nr>=MAXWP || x<2 || y<2 || x>=MAPX-2 || y>=MAPY-2 || n>=MAXWP-1) continue;
			for (k=0; k<n; k++) if (tmp[k].nr==nr) break;
			if (k<n) continue;
			s=line+3+off; t=strchr(s,'|');
			if (t) *t++=0; else t="";
			memset(&tmp[n],0,sizeof(tmp[n]));
			tmp[n].nr=nr; tmp[n].x=x; tmp[n].y=y; tmp[n].look=look; tmp[n].pic=pic;
			strncpy(tmp[n].name,s,sizeof(tmp[n].name)-1); strncpy(tmp[n].line,t,sizeof(tmp[n].line)-1);
			if (!tmp[n].name[0]) sprintf(tmp[n].name,"Waypoint %d",nr);
			n++;
		}
		fclose(fp);
	} else if (access(WP_FILE,F_OK)==0) { xlog("cannot read %s",WP_FILE); return -1; }
	memcpy(wp,tmp,sizeof(wp)); nwp=n;
	k=wp_sync_items();
	xlog("Waypoints: %d loaded%s",nwp,k ? " (old circle pieces removed)" : "");
	return nwp;
}

int wp_count(void) { if (!wp_loaded) wp_load(); return nwp; }

/* the sprite a player sees for a circle piece: lit when he has found that waypoint */
int wp_item_sprite(int cn,int in)
{
	int w;
	if (!wp_loaded) wp_load();
	if (!IS_SANEPLAYER(cn) || (w=wp_at(it[in].x,it[in].y,0))<0) return it[in].sprite[0];
	return it[in].sprite[0]+(wp_found(cn,wp[w].nr) ? 10 : 0);
}

/* ---- the travel window ----
 * SV_WAYPOINT, 80 bytes, one per row: [1] row, [2] rows in all (0: close the window), [3] 1 found + 2 you are here,
 * [4] picture sprite (short), [6] the waypoint's number, [8] name (32), [40] line (40). Rows not found carry
 * no name, line or picture. */
static void wp_send(int nr,int cn,int here)
{
	unsigned char buf[80]; int n,cnt=min(nwp,WP_SHOWN),f;

	for (n=0; n<cnt; n++) {
		memset(buf,0,sizeof(buf));
		f=wp_found(cn,wp[n].nr);
		buf[0]=SV_WAYPOINT; buf[1]=(unsigned char)n; buf[2]=(unsigned char)cnt;
		buf[3]=(unsigned char)((f ? 1 : 0)|(n==here ? 2 : 0));
		if (f) {
			*(unsigned short*)(buf+4)=(unsigned short)wp[n].pic;
			buf[6]=(unsigned char)wp[n].nr;
			memcpy(buf+8,wp[n].name,31); memcpy(buf+40,wp[n].line,39);
		}
		xsend(nr,buf,80);
	}
}

/* a player clicks a circle piece */
int use_waypoint(int cn,int in)
{
	int w,nr;

	if (!wp_loaded) wp_load();
	if (!IS_SANEPLAYER(cn)) return 0;
	if ((w=wp_at(it[in].x,it[in].y,0))<0) { do_char_log(cn,0,"This waypoint is dormant.\n"); return 0; }

	if (!wp_found(cn,wp[w].nr)) {
		wp_setfound(cn,wp[w].nr,1);
		do_char_log(cn,1,"You found the waypoint %s. The circle lights up for you.\n",wp[w].name);
		chlog(cn,"Found waypoint %d (%s)",wp[w].nr,wp[w].name);
		fx_add_effect(6,0,wp[w].x,wp[w].y,0);
	}
	nr=ch[cn].player;
	if (nr<1 || nr>=MAXPLAYER) return 1;
	if (player[nr].version<WP_CLIENT) {
		do_char_log(cn,0,"To travel between waypoints you need the newest version of the game. Start it with Launcher.exe.\n");
		return 1;
	}
	wp_send(nr,cn,w);
	return 1;
}

/* CL_CMD_WAYPOINT: [1] the number of the waypoint to travel to */
void plr_cmd_waypoint(int nr)
{
	int cn=player[nr].usnr,to=player[nr].inbuf[1],here,n,in2;

	if (!wp_loaded) wp_load();
	if (!IS_SANEPLAYER(cn) || ch[cn].used!=USE_ACTIVE) return;
	if ((here=wp_at(ch[cn].x,ch[cn].y,1))<0 || !wp_found(cn,wp[here].nr)) {
		do_char_log(cn,0,"You must stand at a waypoint you have found to travel.\n"); return;
	}
	for (n=0; n<nwp; n++) if (wp[n].nr==to) break;
	if (n>=nwp || !wp_found(cn,to)) { do_char_log(cn,0,"You have not found that waypoint.\n"); return; }
	if (n==here) { do_char_log(cn,0,"You are already there.\n"); return; }

	// what a teleport takes away: labyrinth items
	if ((in2=ch[cn].citem) && !(in2&0x80000000) && is_nolab_item(in2)) {
		ch[cn].citem=0; it[in2].used=USE_EMPTY;
		do_char_log(cn,1,"Your %s vanished.\n",it[in2].reference);
	}
	for (in2=0,to=0; to<40; to++) {
		if ((in2=ch[cn].item[to]) && is_nolab_item(in2)) {
			ch[cn].item[to]=0; it[in2].used=USE_EMPTY;
			do_char_log(cn,1,"Your %s vanished.\n",it[in2].reference);
		}
	}

	fx_add_effect(6,0,ch[cn].x,ch[cn].y,0);
	do_area_sound(cn,0,ch[cn].x,ch[cn].y,WP_SOUND);		// those left behind hear it
	if (!god_transfer_char(cn,wp[n].x,wp[n].y)) {
		do_char_log(cn,0,"Something blocks the waypoint %s. Try again in a moment.\n",wp[n].name); return;
	}
	fx_add_effect(6,0,ch[cn].x,ch[cn].y,0);
	char_play_sound(cn,WP_SOUND,-150,0);
	do_area_sound(cn,0,ch[cn].x,ch[cn].y,WP_SOUND);
	do_update_char(cn);
	do_char_log(cn,1,"You travel to %s.\n",wp[n].name);
	chlog(cn,"Waypoint travel %s -> %s (%d,%d)",wp[here].name,wp[n].name,wp[n].x,wp[n].y);
}

/* ---- console (console.c): wplist, wpfound <player> [all | none | <nr>] ---- */
void wp_console_list(void (*out)(char *format,...))
{
	int n;
	if (!wp_loaded) wp_load();
	if (!nwp) out("  No waypoints (.dat/waypoints.dat).\n");
	for (n=0; n<nwp; n++) out("  %3d  %4d,%-4d  %s  picture %d  %s | %s\n",wp[n].nr,wp[n].x,wp[n].y,wp[n].look ? "pentagram" : "runes",wp[n].pic,wp[n].name,wp[n].line);
}

void wp_console_found(int co,char *what,void (*out)(char *format,...))
{
	int n,c=0;
	if (!wp_loaded) wp_load();
	if (what && *what) {
		if (!strcmp(what,"all")) for (n=0; n<nwp; n++) wp_setfound(co,wp[n].nr,1);
		else if (!strcmp(what,"none")) for (n=1; n<MAXWP; n++) { if (wp_found(co,n)) wp_setfound(co,n,0); }
		else if (atoi(what)>0) wp_setfound(co,atoi(what),!wp_found(co,atoi(what)));
	}
	for (n=0; n<nwp; n++) if (wp_found(co,wp[n].nr)) { out("  %3d  %s\n",wp[n].nr,wp[n].name); c++; }
	out("  %s has found %d of %d waypoints.\n",ch[co].name,c,nwp);
}
