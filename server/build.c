/*************************************************************************

This file is part of 'Mercenaries of Astonia v2'
Copyright (c) 1997-2001 Daniel Brockhaus (joker@astonia.com)
All rights reserved.

**************************************************************************/

#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <stdlib.h>

#include "server.h"

int diffi=21;

int build_item(int nr,int x,int y)
{
	int in,n,m;

	if (x<0 || x>=MAPX || y<0 || y>=MAPY) return 0;

	if (map[x+y*MAPX].it) return 0;

	xlog("build: add item %d at %d,%d",nr,x,y);

	if (map[x+y*MAPX].fsprite) map[x+y*MAPX].fsprite=0;

	if (it_temp[nr].flags&(IF_TAKE|IF_LOOK|IF_LOOKSPECIAL|IF_USE|IF_USESPECIAL)) {
		in=god_create_item(nr);

		if (it[in].driver==33) {
			for (n=1,m=0; n<MAXITEM; n++) {
				if (it[n].used==USE_EMPTY) continue;
				if (it[n].driver==33) m=max(it[n].data[0],m);
			}

			m++;
			do_area_log(0,0,x,y,1,"Respawn point %d, Level %d.\n",m,diffi);
			it[in].data[0]=m;
			it[in].data[9]=diffi;	// difficulty level
			it[in].temp=0; // make sure it isnt reset when doing #reset
		}

		map[x+y*MAPX].it=in;

		it[in].x=(short)x;
		it[in].y=(short)y;
		it[in].carried=0;		
	} else {
		map[x+y*MAPX].fsprite=it_temp[nr].sprite[0];
		if (it_temp[nr].flags&IF_MOVEBLOCK) map[x+y*MAPX].flags|=MF_MOVEBLOCK;
		if (it_temp[nr].flags&IF_SIGHTBLOCK) map[x+y*MAPX].flags|=MF_SIGHTBLOCK;		
                return 0;
	}

	return in;
}

static void ub_save(int x,int y);

void build_drop(int x,int y,int in)
{
	int nr;

	if (x<0 || x>=MAPX || y<0 || y>=MAPY) return;
	ub_save(x,y);

	if (in&0x40000000) {
		if (in&(MF_INDOORS|MF_SIGHTBLOCK)) {
			// indoor tiles keep a stored amount of daylight: recompute it
			// around here, or a newly roofed area stays dark (or bright)
			remove_lights(x,y);
			map[x+y*MAPX].flags^=in&0xfffffff;
			add_lights(x,y);
		} else map[x+y*MAPX].flags^=in&0xfffffff;
		return;
	}
	if (in&0x20000000) {
		nr=in&0xfffffff;
		if (nr==1003) { // hack for jungle ground
			nr+=RANDOM(4);
			if (nr>1003) nr++;
		}
		if (nr==542) { // hack for street ground
			nr+=RANDOM(9);
		}
		if (nr==551) { // hack for grass ground
			nr+=RANDOM(4);
		}
		if (nr==133) { // hack for parkett ground
			nr+=RANDOM(9);
		}
		if (nr==142) { // hack for parkett ground
			nr+=RANDOM(4);
		}
		if (nr==170) { // hack for stone ground
			nr+=RANDOM(6);
		}
		if (nr==704) {
			static int tab[4]={704,659,660,688};
			nr=tab[RANDOM(4)];
		}
		if (nr==950) {
			nr+=RANDOM(9);
		}
		if (nr==959) {
			nr+=(x%3)*3+(y%3);
		}
		if (nr==16670) nr+=RANDOM(4);
		if (nr==16933) {
			static int tab[4]={16933,16957,16958,16959};
			nr=tab[RANDOM(4)];
		}

		map[x+y*MAPX].sprite=nr;
		return;
	}

	nr=build_item(in,x,y);
	if (!nr) return;

	if (it[nr].active) {
		if (it[nr].light[1])
			do_add_light(x,y,it[nr].light[1]);
	} else {
		if (it[nr].light[0])
			do_add_light(x,y,it[nr].light[0]);
	}
}


void build_remove(int x,int y)
{
	int nr;

	if (x<0 || x>=MAPX || y<0 || y>=MAPY) return;
	ub_save(x,y);

	map[x+y*MAPX].fsprite=0;
	map[x+y*MAPX].flags&=~(MF_MOVEBLOCK|MF_SIGHTBLOCK);

	nr=map[x+y*MAPX].it;
	if (!nr) return;

	if (it[nr].active) {
		if (it[nr].light[1])
			do_add_light(x,y,-it[nr].light[1]);
	} else {
		if (it[nr].light[0])
			do_add_light(x,y,-it[nr].light[0]);
	}

	it[nr].used=0;
	map[x+y*MAPX].it=0;

	xlog("build: remove item from %d,%d",x,y);
}

/* ---- build undo -----------------------------------------------------------
 * Every tile a build action changes is saved here first (floor, object sprite,
 * flags and item). One click, or one area, is one action; #undo restores the
 * newest action of that god.
 */
#define UNDO_MAX	20000

struct bundo {
	int cn,grp,x,y;
	unsigned short sprite,fsprite;
	unsigned long long flags;
	unsigned int it;
	int temp;
};

static struct bundo ub[UNDO_MAX];
static int ub_cnt=0,ub_grp=0,ub_cur_cn=0,ub_cur_grp=0;

void build_undo_begin(int cn)
{
	ub_cur_cn=cn;
	ub_cur_grp=++ub_grp;
}

static void ub_save(int x,int y)
{
	struct bundo *u;
	int m=x+y*MAPX;

	if (!ub_cur_cn) return;
	if (ub_cnt>=UNDO_MAX) {	// full: forget the oldest quarter
		memmove(ub,ub+UNDO_MAX/4,sizeof(struct bundo)*(UNDO_MAX-UNDO_MAX/4));
		ub_cnt-=UNDO_MAX/4;
	}
	u=&ub[ub_cnt++];
	u->cn=ub_cur_cn; u->grp=ub_cur_grp; u->x=x; u->y=y;
	u->sprite=map[m].sprite; u->fsprite=map[m].fsprite; u->flags=map[m].flags;
	u->it=map[m].it; u->temp=map[m].it ? it[map[m].it].temp : 0;
}

static void ub_item_light(int x,int y,int in,int sign)
{
	int l=it[in].active ? it[in].light[1] : it[in].light[0];
	if (l) do_add_light(x,y,l*sign);
}

void build_undo(int cn)
{
	int n,grp=0,m,cur,in,cnt=0,lost=0,left=0;
	struct bundo *u;

	for (n=ub_cnt-1; n>=0; n--) if (ub[n].cn==cn) { grp=ub[n].grp; break; }
	if (!grp) { do_char_log(cn,0,"Nothing to undo.\n"); return; }

	for (n=ub_cnt-1; n>=0; n--) {
		u=&ub[n];
		if (u->cn!=cn || u->grp!=grp) continue;
		m=u->x+u->y*MAPX;

		cur=map[m].it;
		if ((unsigned int)cur!=u->it) {
			if (cur) { ub_item_light(u->x,u->y,cur,-1); it[cur].used=USE_EMPTY; map[m].it=0; }
			if (u->it) {	// the item was removed: make a new one from its template
				if (u->temp>0 && (in=god_create_item(u->temp))) {
					map[m].it=in; it[in].x=u->x; it[in].y=u->y; it[in].carried=0;
					ub_item_light(u->x,u->y,in,1);
				} else lost++;
			}
		}
		if ((map[m].flags^u->flags)&(MF_INDOORS|MF_SIGHTBLOCK)) {
			remove_lights(u->x,u->y);
			map[m].flags=u->flags;
			add_lights(u->x,u->y);
		} else map[m].flags=u->flags;
		map[m].sprite=u->sprite;
		map[m].fsprite=u->fsprite;
		cnt++;
		u->cn=0;	// used up
	}
	// drop the used-up entries from the end
	while (ub_cnt>0 && ub[ub_cnt-1].cn==0) ub_cnt--;

	for (n=0,grp=0; n<ub_cnt; n++) if (ub[n].cn==cn && ub[n].grp!=grp) { grp=ub[n].grp; left++; }
	do_char_log(cn,1,"Undid the last build action (%d tile%s).%s %d more can be undone.\n",cnt,cnt==1 ? "" : "s",
		lost ? " Some items could not be brought back." : "",left);
}

/* ---- #clear: remove every object and item in a rectangle -------------------
 * #clear in build mode, then left-click two corners on the map. Floors stay;
 * walls, tables and other objects and all items go. One #undo brings it back.
 * #clear again before the second corner cancels. */
static unsigned char clear_state[MAXCHARS];	// 0 off, 1 first corner next, 2 second corner next
static unsigned short clear_x[MAXCHARS],clear_y[MAXCHARS];
#define CLEAR_MAX	100	// at most 100x100 tiles at once

void build_clear_cmd(int cn)
{
	if (!IS_BUILDING(cn)) { do_char_log(cn,0,"#clear works in build mode (#build).\n"); return; }
	if (clear_state[cn]) { clear_state[cn]=0; do_char_log(cn,1,"Clear cancelled.\n"); return; }
	clear_state[cn]=1;
	do_char_log(cn,1,"Clear: left-click the first corner, then the opposite corner. Objects and items in between are removed, floors stay. #clear again cancels.\n");
}

/* a left-click on the map in build mode: 1 if it was a #clear corner */
int build_clear_click(int cn,int x,int y)
{
	int xs,ys,xe,ye,cnt=0,m;

	if (cn<1 || cn>=MAXCHARS || !clear_state[cn]) return 0;
	if (x<0 || x>=MAPX || y<0 || y>=MAPY) return 1;
	if (clear_state[cn]==1) {
		clear_x[cn]=x; clear_y[cn]=y; clear_state[cn]=2;
		do_char_log(cn,1,"First corner %d,%d. Now the opposite corner.\n",x,y);
		return 1;
	}
	xs=min(x,clear_x[cn]); xe=max(x,clear_x[cn]);
	ys=min(y,clear_y[cn]); ye=max(y,clear_y[cn]);
	clear_state[cn]=0;
	if (xe-xs+1>CLEAR_MAX || ye-ys+1>CLEAR_MAX) {
		do_char_log(cn,0,"That's %dx%d tiles; #clear does at most %dx%d at once. Nothing removed.\n",xe-xs+1,ye-ys+1,CLEAR_MAX,CLEAR_MAX);
		return 1;
	}
	build_undo_begin(cn);
	for (x=xs; x<=xe; x++) for (y=ys; y<=ye; y++) {
		m=x+y*MAPX;
		if (!map[m].fsprite && !map[m].it) continue;
		build_remove(x,y);
		cnt++;
	}
	do_char_log(cn,1,"Cleared %d tile(s) in %d,%d - %d,%d. #undo puts them back.\n",cnt,xs,ys,xe,ye);
	chlog(cn,"build: cleared %d,%d - %d,%d (%d tiles)",xs,ys,xe,ye,cnt);
	return 1;
}

void build_clear_reset(int cn)
{
	if (cn>0 && cn<MAXCHARS) clear_state[cn]=0;
}
