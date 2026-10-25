/* godshop.c -- the gods' shops: every item template a player can carry, free,
 * sorted into categories, 38 per page with "Previous page" / "Next page" in the
 * last two slots.
 *
 *  - Elysium merchants (character templates GODSHOP_TEMP + category) serve gods
 *    and imps standing next to them; anyone else is turned away.
 *  - #godshop <category> (gods only) opens a category's shop from anywhere.
 *  - Quest items come out inert (template 0): no NPC accepts them, for the gods'
 *    live quests (LQ).
 *  - Every item taken is logged (character log and server log), so imps' use can
 *    be checked later.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "server.h"

static char *gs_name[GODSHOP_CATS]={"weapons","belts","armors","amulets","rings","keys","potions","quest","misc","scrolls"};

static int is_quest_temp(int t)		// an item some NPC asks for, or a labyrinth item
{
	int n;

	if (it_temp[t].flags&IF_LABYDESTROY) return 1;
	for (n=1; n<MAXTCHARS; n++) if (ch_temp[n].used && ch_temp[n].data[49]==t) return 1;
	return 0;
}

/* the category of an item template, -1 if the shops don't sell it */
static int gs_category(int t)
{
	struct item *x=&it_temp[t];

	if (!x->used || !x->name[0] || !(x->flags&IF_TAKE)) return -1;
	if (x->flags&(IF_SPELL|IF_MONEY)) return -1;
	if (x->flags&IF_UNIQUE) return -1;	// unique items stay unique: god weapons, Fire/Ice sets, Math caps, Helm of Shadows...
	if (t==169) return -1;			// the Grolm Crown (always unique, but has no unique flag)
	if (t>=GODSHOP_ARROW_TEMP && t<=GODSHOP_ARROW_TEMP+1) return -1;
	if (strstr(x->name,"Scroll") || x->driver==48) return 9;	// also the spell scrolls (Spell of Bless, Bless of Skua...)
	if (x->flags&IF_USEDESTROY) return 6;	// potions, flowers, drinks (some ales are held in the hand)
	if (x->driver==68 || x->driver==73 || x->driver==74) return 8;	// soulstones, crucibles, upgrade stones
	if ((x->flags&IF_WEAPON) || (x->placement&(PL_WEAPON|PL_TWOHAND|PL_SHIELD))) return 0;	// also torches and candles (left hand)
	if (x->placement&PL_BELT) return 1;
	if (x->placement&(PL_HEAD|PL_BODY|PL_ARMS|PL_LEGS|PL_FEET|PL_CLOAK)) return 2;
	if (x->placement&PL_NECK) return 3;
	if ((x->placement&PL_RING) && x->driver!=68) return 4;
	if (strstr(x->name,"Key") || strstr(x->name,"key")) return 5;
	if (is_quest_temp(t)) return 7;
	return 8;
}

static int gs_list(int cat,int *out)
{
	int t,cnt=0;
	for (t=1; t<MAXTITEM; t++) if (gs_category(t)==cat) out[cnt++]=t;
	return cnt;
}

int godshop_cat(int co)		// category + 1 for a gods' merchant, 0 otherwise
{
	if (!IS_SANECHAR(co)) return 0;
	if (ch[co].temp>=GODSHOP_TEMP && ch[co].temp<GODSHOP_TEMP+GODSHOP_CATS) return ch[co].temp-GODSHOP_TEMP+1;
	return 0;
}

static int gs_allowed(int cn)
{
	return IS_SANECHAR(cn) && (ch[cn].flags&(CF_GOD|CF_IMP));
}

static int *gs_page(int cn)
{
	static int dummy;
	int nr=ch[cn].player;
	if (nr<1 || nr>=MAXPLAYER) return &dummy;
	return &player[nr].gs_page;
}

/* fill merchant co's 40 slots with the page the viewer cn is on (for the shop
 * window and the tooltips) */
void godshop_fill(int cn,int co)
{
	int n,in,list[MAXTITEM],cnt,page=*gs_page(cn),cat=godshop_cat(co)-1;
	static int boot=0;	// a new number each server start: a page saved before a restart is never kept

	if (cat<0) return;
	if (!boot) boot=1+RANDOM(1000000);
	// the client asks again every second while the window is open: keep the page
	// if it is already this viewer's (data[7] boot, data[8] viewer, data[9] page+1)
	if (gs_allowed(cn) && ch[co].data[7]==boot && ch[co].data[8]==cn && ch[co].data[9]==page+1) return;

	for (n=0; n<40; n++) if ((in=ch[co].item[n])) { it[in].used=USE_EMPTY; ch[co].item[n]=0; }
	ch[co].data[8]=ch[co].data[9]=0;
	if (!gs_allowed(cn)) { do_sayx(co,"I only serve the gods and their helpers, %s.",ch[cn].name); return; }
	ch[co].data[7]=boot; ch[co].data[8]=cn; ch[co].data[9]=page+1;

	cnt=gs_list(cat,list);
	if (page*GODSHOP_PER_PAGE>=cnt) page=*gs_page(cn)=0;
	for (n=0; n<GODSHOP_PER_PAGE && page*GODSHOP_PER_PAGE+n<cnt; n++) {
		if (!(in=god_create_item(list[page*GODSHOP_PER_PAGE+n]))) continue;
		it[in].value=0; it[in].carried=co;
		ch[co].item[n]=in;
	}
	if (page>0 && (in=god_create_item(GODSHOP_ARROW_TEMP))) { it[in].carried=co; ch[co].item[38]=in; }
	if ((page+1)*GODSHOP_PER_PAGE<cnt && (in=god_create_item(GODSHOP_ARROW_TEMP+1))) { it[in].carried=co; ch[co].item[39]=in; }
}

/* cn clicked slot nr of a gods' merchant: turn the page, or take the item */
void godshop_take(int cn,int co,int nr)
{
	int list[MAXTITEM],cnt,page,cat=godshop_cat(co)-1,t,in;

	if (cat<0 || !gs_allowed(cn)) return;
	if (ch[cn].citem) { do_char_log(cn,0,"The gods' merchants don't buy anything. Put it away first.\n"); return; }

	page=*gs_page(cn);
	cnt=gs_list(cat,list);
	if (nr==38 || nr==39) {
		if (nr==38 && page>0) page--;
		if (nr==39 && (page+1)*GODSHOP_PER_PAGE<cnt) page++;
		*gs_page(cn)=page;
		do_char_log(cn,1,"%s, page %d of %d.\n",gs_name[cat],page+1,(cnt+GODSHOP_PER_PAGE-1)/GODSHOP_PER_PAGE);
		do_look_char(cn,co,1,0,0);
		return;
	}
	if (nr<0 || nr>=GODSHOP_PER_PAGE || page*GODSHOP_PER_PAGE+nr>=cnt) return;

	t=list[page*GODSHOP_PER_PAGE+nr];
	if (!(in=god_create_item(t))) { do_char_log(cn,0,"It couldn't be made.\n"); return; }
	if (cat==7) {			// live quest copy: no NPC takes it
		char buf[300];
		it[in].temp=0;
		snprintf(buf,sizeof(buf),"%s (A copy made by the gods: no one will accept it as the real thing.)",it[in].description);
		strncpy(it[in].description,buf,199); it[in].description[199]=0;
	}
	if (!god_give_char(in,cn)) { it[in].used=USE_EMPTY; do_char_log(cn,0,"Your backpack is full.\n"); return; }
	do_char_log(cn,1,"You take %s.\n",it[in].reference);
	chlog(cn,"Godshop: took %s (t=%d, %s)%s",it[in].name,t,gs_name[cat],(ch[cn].flags&CF_GOD) ? "" : " [imp]");
	xlog("GODSHOP: %s took %s (t=%d, %s)%s",ch[cn].name,it[in].name,t,gs_name[cat],(ch[cn].flags&CF_GOD) ? "" : " [imp]");
}

/* #godshop [category] (gods): open that shop from anywhere */
void god_godshop(int cn,char *arg)
{
	int cat,co,list[MAXTITEM];
	char buf[200];

	for (cat=0; cat<GODSHOP_CATS; cat++) if (arg && *arg && !strncasecmp(arg,gs_name[cat],strlen(arg))) break;
	if (!arg || !*arg || cat==GODSHOP_CATS) {
		buf[0]=0;
		for (cat=0; cat<GODSHOP_CATS; cat++) { char b2[40]; sprintf(b2,"%s%s (%d)",cat ? ", " : "",gs_name[cat],gs_list(cat,list)); strcat(buf,b2); }
		do_char_log(cn,1,"Usage: #godshop <category>. Categories: %s.\n",buf);
		return;
	}
	for (co=1; co<MAXCHARS; co++)
		if (ch[co].used==USE_ACTIVE && !(ch[co].flags&CF_BODY) && ch[co].temp==GODSHOP_TEMP+cat) break;
	if (co==MAXCHARS) { do_char_log(cn,0,"The %s merchant isn't there (Elysium).\n",gs_name[cat]); return; }

	*gs_page(cn)=0;
	do_look_char(cn,co,1,0,0);
}
