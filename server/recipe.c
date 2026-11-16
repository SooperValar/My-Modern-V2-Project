/* recipe.c -- MyV2 recipes: players make items by using one item with another (the Items page of the MyV2 Editor).
 *
 * .dat/recipes.dat (written by the editor, read again with the console's "recipereload"):
 *   recipe <item A> <item B> <result> <flags> <min rank> <text>
 * A player holds B under the mouse cursor and uses A (in his backpack or worn) - or, unless flag 4, holds A and
 * uses B. A and B are used up (a stack loses one), and the result goes into his backpack.
 * flags: 1 keep A, 2 keep B, 4 only this way round (B held, A used). min rank: the rank needed (0 = anyone).
 * text: what the player reads (empty: "You made <name>.").
 * Chains like the Lizard's Teeth Necklace are one recipe a step: Necklace + Tooth -> Necklace with one tooth,
 * Necklace with one tooth + Tooth -> ... Recipes come before the game's own combinations (the flasks, the
 * necklace): a recipe with the same two items replaces what the game did.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "server.h"

#define RECIPE_FILE	DATDIR"/recipes.dat"
#define RECIPE_MAX	2000

static struct recipe {
	int a,b,res,flags,rank;
	char text[200];
} rec[RECIPE_MAX];
static int nrec=0,rec_loaded=0;

int recipe_load(void)
{
	FILE *f;
	char line[1024],*p;
	struct recipe *r;
	int n;

	rec_loaded=1;
	nrec=0;
	if (!(f=fopen(RECIPE_FILE,"r"))) return 0;
	while (fgets(line,sizeof(line),f) && nrec<RECIPE_MAX) {
		if (strncmp(line,"recipe ",7)) continue;
		r=&rec[nrec];
		memset(r,0,sizeof(*r));
		n=0;
		if (sscanf(line+7,"%d %d %d %d %d %n",&r->a,&r->b,&r->res,&r->flags,&r->rank,&n)<5) continue;
		if (r->a<=0 || r->a>=MAXTITEM || r->b<=0 || r->b>=MAXTITEM || r->res<=0 || r->res>=MAXTITEM) continue;
		p=line+7+n;
		strncpy(r->text,p,sizeof(r->text)-1);
		for (p=r->text; *p; p++) if (*p=='\r' || *p=='\n') { *p=0; break; }
		nrec++;
	}
	fclose(f);
	return nrec;
}

static int free_slot(int cn)
{
	int n;

	for (n=0; n<40; n++) if (!ch[cn].item[n]) return 1;
	return 0;
}

static void use_up(int cn,int in)	// one of a stack, or the whole item
{
	if (stack_use_one(in)) { it[in].flags|=IF_UPDATE; return; }
	god_take_from_char(in,cn);
	it[in].used=USE_EMPTY;
}

/* cn uses item in (carried) while holding ch[cn].citem: 1 = a recipe did it (or said why not) */
int recipe_try(int cn,int in)
{
	int n,held,ta,tb,ia=0,ib=0,in3;
	struct recipe *r=NULL;

	if (!rec_loaded) recipe_load();
	if (!nrec || cn<=0 || cn>=MAXCHARS || !(ch[cn].flags&(CF_PLAYER|CF_USURP))) return 0;
	held=ch[cn].citem;
	if (!held || (held&0x80000000) || held>=MAXITEM || in<=0 || in>=MAXITEM || held==in) return 0;

	ta=it[in].temp; tb=it[held].temp;
	for (n=0; n<nrec; n++) {
		if (rec[n].a==ta && rec[n].b==tb) { r=&rec[n]; ia=in; ib=held; break; }
		if (!(rec[n].flags&4) && rec[n].a==tb && rec[n].b==ta) { r=&rec[n]; ia=held; ib=in; break; }
	}
	if (!r) return 0;

	if (r->rank && points2rank(ch[cn].points_tot)<r->rank) {
		do_char_log(cn,0,"You're not experienced enough to make that.\n");
		return 1;
	}
	// room for the result: a free backpack slot, or the cursor / a backpack slot that using up the two frees
	{
		int other=(held==ia) ? ib : ia, kh=(held==ia) ? (r->flags&1) : (r->flags&2), ko=(held==ia) ? (r->flags&2) : (r->flags&1);
		int room=free_slot(cn) || (!kh && stack_count(held)<2);
		for (n=0; n<40 && !room; n++) if (ch[cn].item[n]==other && !ko && stack_count(other)<2) room=1;
		if (!room) { do_char_log(cn,0,"You have no room for it.\n"); return 1; }
	}
	in3=god_create_item(r->res);
	if (!in3) { do_char_log(cn,0,"It didn't work.\n"); return 1; }

	chlog(cn,"Made %s from %s and %s (recipe)",it[in3].name,it[ia].name,it[ib].name);

	if (!(r->flags&1)) use_up(cn,ia);
	if (!(r->flags&2)) use_up(cn,ib);
	if (ch[cn].citem && it[ch[cn].citem].used==USE_EMPTY) ch[cn].citem=0;

	it[in3].flags|=IF_UPDATE;
	if (!god_give_char(in3,cn)) {
		if (!ch[cn].citem) { ch[cn].citem=in3; it[in3].carried=cn; }
		else { do_char_log(cn,0,"You have no room for it.\n"); it[in3].used=USE_EMPTY; }	// (can't happen: checked above)
	}
	if (r->text[0]) do_char_log(cn,1,"%s\n",r->text);
	else do_char_log(cn,1,"You made %s.\n",it[in3].name);
	char_play_sound(cn,ch[cn].sound+1,-150,0);
	do_update_char(cn);
	return 1;
}
