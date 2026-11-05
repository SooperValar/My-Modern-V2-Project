/* merch.c -- MyV2 merchants: stock lists with pages, what they buy, their own prices, seller's remorse.
 *
 * Settings: .dat/merchants.dat (written by the MyV2 Editor's Merchants tab, read again with the console's
 * "merchreload"):
 *   merchant <template> sell <pct> buy <pct> gold <silver> kinds <mask>
 *   stock <template> <item template>...        (lines add up; the order is the shop's order)
 * sell / buy: % of the normal price (0 = normal), gold: the most he pays for one item (0 = his own gold),
 * kinds: what he buys (1 armor, 2 weapons, 4 magic, 8 other; -1 = as before). A merchant template that is not in
 * the file works as before: his stock is his sale list (data[0..9]) plus his template's backpack, he buys the kind
 * of item data[0] is, at normal prices.
 *
 * The shop window has 40 slots: the stock (a display copy of each, made when shown), then the items players sold
 * him (kept in his depot[]). With more than 40: 38 a page and the page arrows in slots 38 / 39, each viewer on his
 * own page (player[].merch_page). The slots are filled again for each viewer before anything is shown or bought.
 *
 * Seller's remorse: what a player sells stays his to buy back for what he got, until he looks at someone else or
 * MERCH_REMORSE ticks pass. Then the merchant keeps it at his normal price - or destroys it if he would not sell
 * it (Fire / Ice set pieces, shop-destroy items, damaged ones).
 * Item fields used: future3[8] of a sold item = what the seller got (0 = kept for good), t_bought = the seller,
 * t_sold = when the remorse ends (globs->ticker); future3[8] = -1: a display copy of the stock.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "server.h"

int barter(int cn,int opr,int flag);

#define MERCH_FILE	DATDIR"/merchants.dat"
#define MERCH_MAX	160		// merchant templates in the file
#define MERCH_STOCK	240		// items in one merchant's stock list
#define MERCH_PER_PAGE	38
#define MERCH_REMORSE	(TICKS*60*10)	// 10 minutes
#define MK_ARMOR	1
#define MK_WEAPON	2
#define MK_MAGIC	4
#define MK_MISC		8

#define SAMPLE(in)	(it[in].future3[8]==-1)
#define PAID(in)	(it[in].future3[8])

static struct mconf {
	int temp,sell,buy,gold,kinds,hasstock,n;
	int stock[MERCH_STOCK];
} mconf[MERCH_MAX];
static int nmconf=0,merch_loaded=0;
static unsigned char tidied[MAXCHARS];	// his slots from before this server start were looked at

/* read merchants.dat; returns the number of merchants in it, -1 = error */
int merch_load(void)
{
	FILE *f;
	char line[4096],*p;
	int t,v,i,bad=0;
	struct mconf *m;

	merch_loaded=1;
	nmconf=0;
	if (!(f=fopen(MERCH_FILE,"r"))) return 0;
	while (fgets(line,sizeof(line),f)) {
		if (line[0]=='#' || line[0]=='\n' || line[0]=='\r') continue;
		if (!strncmp(line,"merchant ",9) || !strncmp(line,"stock ",6)) {
			int isstock=line[0]=='s';
			p=line+(isstock ? 6 : 9);
			t=strtol(p,&p,10);
			if (t<=0 || t>=MAXTCHARS) { bad++; continue; }
			for (i=0; i<nmconf && mconf[i].temp!=t; i++) ;
			if (i==nmconf) {
				if (nmconf>=MERCH_MAX) { bad++; continue; }
				m=&mconf[nmconf++];
				memset(m,0,sizeof(*m)); m->temp=t; m->kinds=-1;
			} else m=&mconf[i];
			if (isstock) {
				m->hasstock=1;
				while (1) {
					while (*p==' ' || *p=='\t') p++;
					if (!isdigit(*p)) break;
					v=strtol(p,&p,10);
					if (v>0 && v<MAXTITEM && m->n<MERCH_STOCK) m->stock[m->n++]=v;
				}
			} else {
				char w[32];
				while (sscanf(p," %31s %d",w,&v)==2) {
					if (!strcmp(w,"sell")) m->sell=v;
					else if (!strcmp(w,"buy")) m->buy=v;
					else if (!strcmp(w,"gold")) m->gold=v;
					else if (!strcmp(w,"kinds")) m->kinds=v;
					// skip the two words
					while (*p==' ' || *p=='\t') p++;
					while (*p && *p!=' ' && *p!='\t') p++;
					while (*p==' ' || *p=='\t') p++;
					while (*p && *p!=' ' && *p!='\t' && *p!='\n') p++;
				}
			}
		} else bad++;
	}
	fclose(f);
	if (bad) xlog("merchants.dat: %d line(s) not understood",bad);
	return nmconf;
}

static struct mconf *conf(int co)
{
	int i;
	if (!merch_loaded) merch_load();
	if (!IS_SANECHAR(co)) return NULL;
	for (i=0; i<nmconf; i++) if (mconf[i].temp==ch[co].temp) return &mconf[i];
	return NULL;
}

/* the stock list of merchant co (item templates, shop order) */
static int stock_list(int co,int *out)
{
	struct mconf *m=conf(co);
	int n,z,cnt=0,t,tmp;

	if (m && m->hasstock) {
		for (n=0; n<m->n; n++) out[cnt++]=m->stock[n];
		return cnt;
	}
	// as before: the sale list in data[0..9] plus the template's backpack, by value (dearest first)
	for (n=0; n<10; n++) if ((t=ch[co].data[n])>0 && t<MAXTITEM) {
		for (z=0; z<cnt && out[z]!=t; z++) ;
		if (z==cnt) out[cnt++]=t;
	}
	if ((tmp=ch[co].temp)>0 && tmp<MAXTCHARS) {
		for (n=0; n<40 && cnt<MERCH_STOCK; n++) {
			if ((t=ch_temp[tmp].item[n])<=0 || t>=MAXTITEM) continue;
			for (z=0; z<cnt && out[z]!=t; z++) ;
			if (z==cnt) out[cnt++]=t;
		}
	}
	for (n=1; n<cnt; n++) for (z=n; z>0 && it_temp[out[z]].value>it_temp[out[z-1]].value; z--) { t=out[z]; out[z]=out[z-1]; out[z-1]=t; }
	return cnt;
}

/* what merchant co buys: MK_* bits */
int merch_kinds(int co)
{
	struct mconf *m=conf(co);
	int t,k=0;

	if (m && m->kinds>=0) return m->kinds;
	t=ch[co].data[0];
	if (t<=0 || t>=MAXTITEM) return 0;
	if (it_temp[t].flags&IF_ARMOR) k|=MK_ARMOR;
	if (it_temp[t].flags&IF_WEAPON) k|=MK_WEAPON;
	if (it_temp[t].flags&IF_MAGIC) k|=MK_MAGIC;
	if (it_temp[t].flags&IF_MISC) k|=MK_MISC;
	return k;
}

int merch_buys(int co,int in)
{
	int k=merch_kinds(co);
	if (!in || (in&0x80000000)) return 0;
	if ((it[in].flags&IF_ARMOR) && (k&MK_ARMOR)) return 1;
	if ((it[in].flags&IF_WEAPON) && (k&MK_WEAPON)) return 1;
	if ((it[in].flags&IF_MAGIC) && (k&MK_MAGIC)) return 1;
	if ((it[in].flags&IF_MISC) && (k&MK_MISC)) return 1;
	return 0;
}

static int remorse_for(int cn,int in)	// may cn buy item in back for what he got?
{
	return PAID(in)>0 && it[in].t_bought==cn && globs->ticker<it[in].t_sold;
}

/* what cn pays merchant co for item in */
int merch_sell_price(int cn,int co,int in)
{
	struct mconf *m=conf(co);
	int pr;

	if (remorse_for(cn,in)) return PAID(in);
	pr=barter(cn,do_item_value(in),1);
	if (m && m->sell>0) pr=(int)((long long)pr*m->sell/100);
	return pr;
}

/* what merchant co pays cn for item in */
int merch_buy_price(int cn,int co,int in)
{
	struct mconf *m=conf(co);
	int pr;

	pr=barter(cn,do_item_value(in),0);
	if (m && m->buy>0) pr=(int)((long long)pr*m->buy/100);
	return pr;
}

static int depot_slot(int co,int in)
{
	int n;
	for (n=0; n<62; n++) if (ch[co].depot[n]==in) return n;
	return -1;
}

static void unslot(int co,int in)	// take a depot item out of the shop slots
{
	int n;
	for (n=0; n<40; n++) if (ch[co].item[n]==in) ch[co].item[n]=0;
}

/* the remorse of a sold item ends: kept at the normal price, or destroyed */
static void finalize(int co,int n)
{
	int in=ch[co].depot[n];

	if (!in) return;
	if (set_of_temp(it[in].temp) || (it[in].flags&IF_SHOPDESTROY) || it[in].damage_state) {
		unslot(co,in);
		ch[co].depot[n]=0;
		it[in].used=USE_EMPTY;
		return;
	}
	PAID(in)=0; it[in].t_bought=it[in].t_sold=0;
	it[in].current_damage=0; it[in].current_age[0]=it[in].current_age[1]=0;
}

/* check his depot: items that are gone, remorse that ended; and (once a server start) his old slots */
static void tidy(int co,int *stock,int scnt)
{
	int n,in,z,d;

	for (n=0; n<62; n++) {
		if (!(in=ch[co].depot[n])) continue;
		if (it[in].used!=USE_ACTIVE || it[in].carried!=co) { ch[co].depot[n]=0; continue; }
		if (PAID(in)>0 && globs->ticker>=it[in].t_sold) finalize(co,n);
	}
	if (tidied[co]) return;
	tidied[co]=1;
	// the slots as they were (an old shop, or the display of the last server start)
	for (n=0; n<40; n++) {
		if (!(in=ch[co].item[n])) continue;
		if (in&0x80000000) { ch[co].item[n]=0; continue; }
		if (it[in].used!=USE_ACTIVE || it[in].carried!=co) { ch[co].item[n]=0; continue; }
		if (SAMPLE(in) || depot_slot(co,in)>=0) continue;	// shown again below
		for (z=0; z<scnt && stock[z]!=it[in].temp; z++) ;
		if (z<scnt || it[in].temp==GODSHOP_ARROW_TEMP || it[in].temp==GODSHOP_ARROW_TEMP+1) { it[in].used=USE_EMPTY; ch[co].item[n]=0; continue; }
		// something a player sold him before: keep it, at his normal price
		for (d=0; d<62 && ch[co].depot[d]; d++) ;
		if (d<62) { ch[co].depot[d]=in; PAID(in)=0; it[in].t_bought=it[in].t_sold=0; }
		else it[in].used=USE_EMPTY;
		ch[co].item[n]=0;
	}
}

static int *page_of(int cn,int co)
{
	static int dummy,npc_co[MAXCHARS],npc_page[MAXCHARS];	// (no player: the console's "shop" test)
	int nr=IS_SANECHAR(cn) ? ch[cn].player : 0;
	if (!IS_SANECHAR(cn)) { dummy=0; return &dummy; }
	if (nr<1 || nr>=MAXPLAYER) {
		if (npc_co[cn]!=co) { npc_co[cn]=co; npc_page[cn]=0; }
		return &npc_page[cn];
	}
	if (player[nr].merch_co!=co) { player[nr].merch_co=co; player[nr].merch_page=0; }
	return &player[nr].merch_page;
}

/* put what should be in slot m: a display copy of item template t (t>0), or the depot item -t (t<0), or nothing */
static void set_slot(int co,int m,int t)
{
	int in=ch[co].item[m];

	if (t>0 && in && it[in].used==USE_ACTIVE && SAMPLE(in) && it[in].temp==t) return;	// already there
	if (t<0 && in==-t) return;
	if (in && !(in&0x80000000) && it[in].used==USE_ACTIVE && SAMPLE(in) && it[in].carried==co) it[in].used=USE_EMPTY;
	ch[co].item[m]=0;
	if (t>0) {
		if (!(in=god_create_item(t))) return;		// (a unique one that exists already)
		PAID(in)=-1; it[in].carried=co; it[in].x=it[in].y=0;
		ch[co].item[m]=in;
	} else if (t<0) ch[co].item[m]=-t;
}

/* the entries of merchant co's shop: item templates (>0) and depot items (<0, the item number) */
static int entries(int co,int *ent)
{
	int stock[MERCH_STOCK],scnt,n,cnt=0,in;

	scnt=stock_list(co,stock);
	tidy(co,stock,scnt);
	for (n=0; n<scnt; n++) ent[cnt++]=stock[n];
	for (n=0; n<62; n++) if ((in=ch[co].depot[n])) ent[cnt++]=-in;
	return cnt;
}

/* fill merchant co's 40 slots for viewer cn (before the shop is shown, a tooltip, or a trade) */
void merch_fill(int cn,int co)
{
	int ent[MERCH_STOCK+62],cnt,page,*pp,n,pages;
	struct mconf *m;

	if (!IS_SANECHAR(co) || !(ch[co].flags&CF_MERCHANT) || godshop_cat(co)) return;
	if ((m=conf(co)) && m->gold>0) ch[co].gold=m->gold;
	cnt=entries(co,ent);
	pp=page_of(cn,co);
	if (cnt<=40) {
		*pp=0;
		for (n=0; n<40; n++) set_slot(co,n,n<cnt ? ent[n] : 0);
		return;
	}
	pages=(cnt+MERCH_PER_PAGE-1)/MERCH_PER_PAGE;
	if (*pp>=pages) *pp=pages-1;
	if (*pp<0) *pp=0;
	page=*pp;
	for (n=0; n<MERCH_PER_PAGE; n++) set_slot(co,n,page*MERCH_PER_PAGE+n<cnt ? ent[page*MERCH_PER_PAGE+n] : 0);
	set_slot(co,38,page>0 ? GODSHOP_ARROW_TEMP : 0);
	set_slot(co,39,page<pages-1 ? GODSHOP_ARROW_TEMP+1 : 0);
}

/* cn stops dealing with merchant co (looks at someone else): his remorse there ends */
void merch_leave(int cn,int co)
{
	int n,in;
	if (!IS_SANECHAR(co) || !(ch[co].flags&CF_MERCHANT)) return;
	for (n=0; n<62; n++) if ((in=ch[co].depot[n]) && PAID(in)>0 && it[in].t_bought==cn) finalize(co,n);
}

/* cn looks at co: if he was dealing with another merchant, that one keeps what he sold */
void merch_look(int cn,int co)
{
	int nr=IS_SANECHAR(cn) ? ch[cn].player : 0,old;
	if (nr<1 || nr>=MAXPLAYER) return;
	old=player[nr].merch_co;
	if (old && old!=co) { merch_leave(cn,old); player[nr].merch_co=0; player[nr].merch_page=0; }
}

/* cn clicks slot nr of merchant co's shop (buy, or a page arrow); returns 1 if the window should be shown again */
int merch_take(int cn,int co,int nr)
{
	int in,pr,d,ent[MERCH_STOCK+62],cnt,pages,*pp,tmp;

	if (nr<0 || nr>=40) return 0;
	merch_fill(cn,co);
	if (!(in=ch[co].item[nr]) || (in&0x80000000)) return 0;
	if (SAMPLE(in) && (it[in].temp==GODSHOP_ARROW_TEMP || it[in].temp==GODSHOP_ARROW_TEMP+1)) {
		cnt=entries(co,ent); pages=(cnt+MERCH_PER_PAGE-1)/MERCH_PER_PAGE;
		pp=page_of(cn,co);
		if (it[in].temp==GODSHOP_ARROW_TEMP && *pp>0) (*pp)--;
		if (it[in].temp==GODSHOP_ARROW_TEMP+1 && *pp<pages-1) (*pp)++;
		do_char_log(cn,1,"%s's wares, page %d of %d.\n",ch[co].name,*pp+1,pages);
		return 1;
	}
	pr=merch_sell_price(cn,co,in);
	if (ch[cn].gold<pr) { do_char_log(cn,0,"You cannot afford that.\n"); return 0; }
	ch[co].item[nr]=0;
	d=depot_slot(co,in);
	if (SAMPLE(in)) PAID(in)=0;
	else { PAID(in)=0; it[in].t_bought=it[in].t_sold=0; if (d>=0) ch[co].depot[d]=0; }
	tmp=it[in].temp;
	if (!god_give_char(in,cn)) {		// full: back where it was
		if (d>=0) { ch[co].depot[d]=in; it[in].carried=co; }
		else it[in].used=USE_EMPTY;
		do_char_log(cn,0,"You cannot buy that because your inventory is full.\n");
		return 1;
	}
	ch[cn].gold-=pr;
	chlog(cn,"Bought %s",it[in].used==USE_ACTIVE ? it[in].name : it_temp[tmp].name);
	do_char_log(cn,1,"You bought a %s for %dG %dS.\n",it[in].used==USE_ACTIVE ? it[in].reference : it_temp[tmp].reference,pr/100,pr%100);
	if (tmp>0 && tmp<MAXTITEM) it_temp[tmp].t_bought++;
	return 1;
}

/* cn sells what is in his hand to merchant co */
void merch_sell(int cn,int co)
{
	int in=ch[cn].citem,pr,n,tmp;
	struct mconf *m=conf(co);

	if (!in) return;
	if (in&0x80000000) { do_char_log(cn,0,"You want to sell money? Weird!\n"); return; }
	if (!merch_buys(co,in)) { do_char_log(cn,0,"%s doesn't buy those.\n",ch[co].name); return; }
	pr=merch_buy_price(cn,co,in);
	if ((m && m->gold>0 ? m->gold : ch[co].gold)<pr) { do_char_log(cn,0,"%s cannot afford that.\n",ch[co].reference); return; }

	// room in his depot: else the oldest thing he keeps for good goes
	for (n=0; n<62 && ch[co].depot[n]; n++) ;
	if (n==62) {
		int k,o;
		for (k=0; k<62; k++) if ((o=ch[co].depot[k]) && PAID(o)<=0) break;
		if (k<62) { o=ch[co].depot[k]; unslot(co,o); it[o].used=USE_EMPTY; for (; k<61; k++) ch[co].depot[k]=ch[co].depot[k+1]; ch[co].depot[61]=0; n=61; }
	}

	ch[cn].citem=0;
	ch[cn].gold+=pr;
	chlog(cn,"Sold %s",it[in].name);
	do_char_log(cn,1,"You sold a %s for %dG %dS.\n",it[in].reference,pr/100,pr%100);
	tmp=it[in].temp;
	if (tmp>0 && tmp<MAXTITEM) it_temp[tmp].t_sold++;

	if (n>=62) { it[in].used=USE_EMPTY; return; }	// (all 62 waiting to be bought back: no room)
	ch[co].depot[n]=in;
	it[in].carried=co; it[in].x=it[in].y=0;
	PAID(in)=pr>0 ? pr : 1;
	it[in].t_bought=cn;
	it[in].t_sold=globs->ticker+MERCH_REMORSE;
	do_update_char(cn);
}

/* tooltip line for a shop slot: is it something cn sold and may buy back? */
int merch_remorse(int cn,int in)
{
	return in && !(in&0x80000000) && remorse_for(cn,in);
}
