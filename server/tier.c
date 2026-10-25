/* tier.c -- item tiers for helmets and body armor (docs/ITEM_TIERS.md)
 *
 * Magic (blue), Rare (yellow), Epic (purple), Legendary (orange). A tiered
 * item is a plain armor piece (its base template) with rolled bonuses on top.
 * The roll is kept in the item's spare future3[] fields (IT_TIER etc., data.h).
 *
 *  - budget = max(item level, 8) x tier step (Magic 1, Rare 2, Epic 3); one
 *    point = +1 skill or +1/2 attribute
 *  - category Fighter / Mercenary / Mage / Utility decides which bonuses roll
 *  - hitpoints, endurance and mana per item level by category, outside the budget
 *  - the item needs rank = item level, doesn't wear out, and costs the base
 *    price x tier step
 *  - the full name is built when shown (tier_name); the stored name is short
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "server.h"

static int tier_mult[5]={0,1,2,3,5};			// even steps, Legendary 5
static char *tier_word[5]={"","Magic","Rare","Epic","Legendary"};
static char *cat_word[5]={"","Fighter","Mercenary","Mage","Utility"};
static char *cat_short[5]={"","Fighter","Merc","Mage","Utility"};

// hitpoints / endurance / mana per item level at Magic, in tenths (halved scale)
static int cat_hem[5][3]={{0,0,0},{15,10,5},{10,10,10},{5,10,15},{5,5,5}};

static int fighter_sk[]={SK_HAND,SK_DAGGER,SK_SWORD,SK_TWOHAND,SK_AXE2H,SK_SURROUND,SK_WARCRY,SK_RESIST,SK_IMMUN,SK_REGEN,SK_REST,-1};
static int mage_sk[]={SK_BLESS,SK_ENHANCE,SK_PROTECT,SK_MSHIELD,SK_HEAL,SK_BLAST,SK_CURSE,SK_STUN,SK_GHOST,SK_DISPEL,SK_DAGGER,SK_RESIST,SK_CONCEN,SK_MEDIT,-1};
static int util_sk[]={SK_PERCEPT,SK_LOCK,SK_BARTER,SK_REPAIR,SK_LIGHT,SK_IDENT,SK_SENSE,SK_SWIM,-1};

static char *at_prefix[7]={"","Brave","Willful","Wise","Nimble","Strong","Balanced"};	// AT_*+1, 6 = spread

// metal templates: helmet, body armor, the item levels they drop at, and the
// "special" sprites (the old modded armor's, with the red gem; emerald's are new)
static struct { char *metal; int helm,body,from,to,spr_helm,spr_body; } metals[]={
	{"Bronze",	57,	59,	1,	6,	840,	845},
	{"Steel",	63,	65,	1,	20,	830,	835},	// steel at every level (Harakim wear it for good)
	{"Golden",	69,	71,	5,	14,	870,	875},
	{"Emerald",	981,	982,	9,	17,	18210,	18211},
	{"Crystal",	75,	76,	11,	20,	850,	855},
	{"Titanium",	94,	95,	16,	20,	860,	865},
};
#define NMETAL ((int)(sizeof(metals)/sizeof(metals[0])))

/* ---- helpers ---- */

static int pick_skill(int *pool,int *used,int nused)
{
	int n,cnt,k,s,tries;

	for (cnt=0; pool[cnt]!=-1; cnt++) ;
	for (tries=0; tries<50; tries++) {
		s=pool[RANDOM(cnt)];
		for (k=0; k<nused; k++) if (used[k]==s) break;
		if (k==nused) return s;
	}
	for (n=0; n<cnt; n++) {		// all taken? take the first free one
		for (k=0; k<nused; k++) if (used[k]==pool[n]) break;
		if (k==nused) return pool[n];
	}
	return pool[0];
}

// split total into n parts, each at least 20% of total (at least 1)
static void split(int total,int n,int *part)
{
	int mn,free,i,cut[8],j,t;

	if (n<1) return;
	mn=max(1,total/5);
	if (mn*n>total) mn=max(1,total/n);
	free=max(0,total-mn*n);
	for (i=0; i<n-1; i++) cut[i]=RANDOM(free+1);
	for (i=0; i<n-1; i++) for (j=i+1; j<n-1; j++) if (cut[j]<cut[i]) { t=cut[i]; cut[i]=cut[j]; cut[j]=t; }
	for (i=0; i<n; i++) part[i]=mn+(i==n-1 ? free : cut[i])-(i==0 ? 0 : cut[i-1]);
}

static void add_attrib(int in,int a,int points)
{
	int v=(points+1)/2,n;

	if (a==6) {			// spread over the four main attributes
		v=max(1,(v+1)/2);
		for (n=AT_WILL; n<=AT_STREN; n++) it[in].attrib[n][0]+=v;
	} else it[in].attrib[a-1][0]+=v;
}

static int roll_category(void)
{
	int r=RANDOM(100);
	if (r<30) return TCAT_FIGHTER;
	if (r<60) return TCAT_MERC;
	if (r<90) return TCAT_MAGE;
	return TCAT_UTILITY;
}

static int roll_effect(int cat)
{
	int w[TE_MAX+1],n,tot=0,r;

	for (n=1; n<=TE_MAX; n++) w[n]=2;
	if (cat==TCAT_FIGHTER) w[TE_THORNS]=4;
	if (cat==TCAT_MAGE) { w[TE_CLARITY]=4; w[TE_LASTING]=4; }
	for (n=1; n<=TE_MAX; n++) tot+=w[n];
	r=RANDOM(tot);
	for (n=1; n<=TE_MAX; n++) { if (r<w[n]) return n; r-=w[n]; }
	return 1;
}

/* the effect's strength at an item level, for effects that use percentages:
 * from lo at level 1 to hi at level 20 */
int tier_effect_pct(int level,int lo,int hi)
{
	level=max(1,min(20,level));
	return lo+(hi-lo)*(level-1)/19;
}

/* ---- the roll ---- */

// put the base template's values back (before a new roll)
static void reset_to_base(int in)
{
	int t=IT_TBASE(in),n;

	if (t<=0 || t>=MAXTITEM) return;
	for (n=0; n<5; n++) it[in].attrib[n][0]=it_temp[t].attrib[n][0];
	for (n=0; n<MAXSKILL; n++) it[in].skill[n][0]=it_temp[t].skill[n][0];
	it[in].hp[0]=it_temp[t].hp[0];
	it[in].end[0]=it_temp[t].end[0];
	it[in].mana[0]=it_temp[t].mana[0];
	it[in].light[0]=it_temp[t].light[0];
	it[in].gethit_dam[0]=it_temp[t].gethit_dam[0];
}

/* roll the bonuses of item in from its tier, category and level. With keep,
 * an upgrade: the attributes and skills it has stay and get the new budget,
 * plus one new skill. */
static void tier_roll(int in,int keep)
{
	int tier=IT_TIER(in),cat=IT_TCAT(in),level=IT_TLEVEL(in);
	int budget,main=0,second=0,nsk=0,sk[8],part[8],n,k,rest,mp,base[4],nbase,*pool,ksk[8],nk=0,kmain=0,ksecond=0;

	if (keep) {			// what the item has now, before resetting
		int t=IT_TBASE(in);
		kmain=IT_TPREFIX(in);
		for (n=0; n<5; n++) if (n+1!=kmain && it[in].attrib[n][0]>it_temp[t].attrib[n][0] && kmain!=6) ksecond=n+1;
		for (n=0; n<MAXSKILL && nk<7; n++) if (it[in].skill[n][0]>it_temp[t].skill[n][0]) ksk[nk++]=n;
	}
	reset_to_base(in);

	budget=max(level,8)*tier_mult[tier];

	switch(cat) {
		case TCAT_FIGHTER:	pool=fighter_sk; base[0]=AT_STREN+1; base[1]=AT_AGIL+1; nbase=2; break;
		case TCAT_MAGE:		pool=mage_sk; base[0]=AT_INT+1; base[1]=AT_WILL+1; nbase=2; break;
		case TCAT_UTILITY:	pool=util_sk; nbase=0; break;
		default:		pool=fighter_sk; base[0]=AT_STREN+1; base[1]=AT_AGIL+1; base[2]=AT_INT+1; base[3]=AT_WILL+1; nbase=4; break;
	}

	IT_TPREFIX(in)=0; IT_TSUFFIX(in)=0;

	if (cat==TCAT_UTILITY) {		// skills only
		if (keep && nk) { for (n=0; n<nk; n++) sk[n]=ksk[n]; nsk=nk; }
		else nsk=(tier==TIER_MAGIC) ? 1 : (tier==TIER_RARE ? 2+RANDOM(2) : 4);
		if (keep) { sk[nsk]=pick_skill(pool,sk,nsk); nsk++; }
		for (n=keep ? nk : 0; n<nsk; n++) sk[n]=pick_skill(pool,sk,n);
		split(budget,nsk,part);
		for (n=0; n<nsk; n++) it[in].skill[sk[n]][0]+=part[n];
	} else {
		int mskill[2]={0,0};
		if (cat==TCAT_MERC) { mskill[0]=1; }	// Mercenary pool: fighter and mage skills, and Stealth

		if (keep && kmain) {
			main=kmain; second=ksecond;
			if (main==AT_BRAVE+1 && !second) second=base[RANDOM(nbase)];	// Braveness first: the usual main attribute second
		}
		else {
			main=base[RANDOM(nbase)];
			if (cat==TCAT_MERC && !RANDOM(5)) main=6;			// spread over all four
			if (RANDOM(100)<10) { second=(main==6) ? base[RANDOM(4)] : main; main=AT_BRAVE+1; }	// Braveness first
		}

		if (tier==TIER_EPIC && !second) {
			if (RANDOM(100)<70 && main!=6) {			// the category's other main attribute
				do second=base[RANDOM(nbase)]; while (second==main && nbase>1);
				if (second==main) second=AT_BRAVE+1;
			} else second=AT_BRAVE+1;
		}

		if (tier==TIER_MAGIC && !keep) {		// one bonus: the main attribute or one skill
			if (RANDOM(2)) { add_attrib(in,main,budget); IT_TPREFIX(in)=main; }
			else {
				int s=(cat==TCAT_MERC) ? (RANDOM(3)==0 ? pick_skill(mage_sk,sk,0) : (RANDOM(12)==0 ? SK_STEALTH : pick_skill(fighter_sk,sk,0))) : pick_skill(pool,sk,0);
				it[in].skill[s][0]+=budget; IT_TSUFFIX(in)=s+1;
			}
		} else {
			mp=(budget+1)/2; rest=budget-mp;
			add_attrib(in,main,mp); IT_TPREFIX(in)=main;

			if (keep && nk) { for (n=0; n<nk; n++) sk[n]=ksk[n]; nsk=nk+1; }
			else nsk=(tier==TIER_RARE) ? 1+RANDOM(2) : (tier==TIER_EPIC ? 3 : 1);
			for (n=(keep ? nk : 0); n<nsk; n++) {
				if (cat==TCAT_MERC) {
					int s,tries=0;
					do {
						k=RANDOM(25);
						s=(k==0) ? SK_STEALTH : (k<13 ? pick_skill(fighter_sk,sk,n) : pick_skill(mage_sk,sk,n));
						for (k=0; k<n; k++) if (sk[k]==s) break;
					} while (k<n && ++tries<20);
					sk[n]=s;
				} else sk[n]=pick_skill(pool,sk,n);
			}
			k=nsk+(second ? 1 : 0);
			split(rest,k,part);
			if (second) add_attrib(in,second,part[nsk]);
			for (n=0; n<nsk; n++) it[in].skill[sk[n]][0]+=part[n];
		}
		(void)mskill;
	}

	// the strongest skill names the suffix
	for (n=0,k=-1; n<MAXSKILL; n++) {
		int d=it[in].skill[n][0]-it_temp[IT_TBASE(in)].skill[n][0];
		if (d>0 && (k==-1 || d>it[in].skill[k][0]-it_temp[IT_TBASE(in)].skill[k][0])) k=n;
	}
	if (k>=0) IT_TSUFFIX(in)=k+1;

	// hitpoints, endurance and mana
	it[in].hp[0]+=level*cat_hem[cat][0]*tier_mult[tier]/10;
	it[in].end[0]+=level*cat_hem[cat][1]*tier_mult[tier]/10;
	it[in].mana[0]+=level*cat_hem[cat][2]*tier_mult[tier]/10;

	// effects that work through existing item values
	if (tier>=TIER_EPIC) {
		if (IT_TEFFECT(in)==TE_THORNS) it[in].gethit_dam[0]+=max(1,level/2);
		if (IT_TEFFECT(in)==TE_LIGHT) it[in].light[0]+=8+level;
	}
}

// short skill words for the stored name (it holds only 39 characters)
static char *short_skill(int s)
{
	switch(s) {
		case SK_RESIST:		return "Resist";
		case SK_GHOST:		return "Companion";
		case SK_AXE2H:		return "2H Axe";
		case SK_TWOHAND:	return "2H";
		case SK_SURROUND:	return "Surround";
		case SK_ENHANCE:	return "Enhance";
		case SK_MSHIELD:	return "MShield";
		case SK_LOCK:		return "Lockpick";
		case SK_SENSE:		return "Sense";
		case SK_DISPEL:		return "Dispel";
		case SK_HAND:		return "H2H";
		case SK_CONCEN:		return "Concen";
		case SK_PERCEPT:	return "Percept";
		case SK_PROTECT:	return "Protect";
		case SK_IMMUN:		return "Immun";
		case SK_MEDIT:		return "Meditate";
		case SK_REGEN:		return "Regen";
		default:		return skilltab[s].name;
	}
}

// short stored name (for logs and god tools), description
static void tier_set_names(int in)
{
	char buf[200],metal[40],piece[40],*p;
	int t=IT_TBASE(in),pre=IT_TPREFIX(in),suf=IT_TSUFFIX(in);

	strcpy(metal,it_temp[t].name); p=strchr(metal,' ');
	if (p) { strcpy(piece,p+1); *p=0; } else { strcpy(piece,metal); metal[0]=0; }
	if (!strcmp(piece,"Helmet")) strcpy(piece,"Helm");

	snprintf(buf,sizeof(buf),"%s%s%s %s %s%s%s",
		pre ? at_prefix[pre] : "",pre ? " " : "",metal,cat_short[IT_TCAT(in)],piece,
		suf ? " of " : "",suf ? short_skill(suf-1) : "");
	strncpy(it[in].name,buf,39); it[in].name[39]=0;
	strncpy(it[in].reference,buf,39); it[in].reference[39]=0;
	it[in].reference[0]=tolower(it[in].reference[0]);

	snprintf(buf,sizeof(buf),"A %s %s, item level %d.",tier_word[IT_TIER(in)],tier_name(in),IT_TLEVEL(in));
	strncpy(it[in].description,buf,199); it[in].description[199]=0;
}

/* the full name players see: prefix, metal, category, piece, suffix */
char *tier_name(int in)
{
	static char buf[120];
	char metal[40],piece[40],*p;
	int t,pre,suf;

	if (!IS_SANEITEM(in) || !IT_TIER(in)) return IS_SANEITEM(in) ? it[in].name : "";
	t=IT_TBASE(in); pre=IT_TPREFIX(in); suf=IT_TSUFFIX(in);
	if (t<=0 || t>=MAXTITEM) return it[in].name;

	strcpy(metal,it_temp[t].name); p=strchr(metal,' ');
	if (p) { strcpy(piece,p+1); *p=0; } else { strcpy(piece,metal); metal[0]=0; }

	if (IT_TCAT(in)==TCAT_UTILITY)
		snprintf(buf,sizeof(buf),"%s Utility %s%s%s",metal,piece,suf ? " of " : "",suf ? skilltab[suf-1].name : "");
	else
		snprintf(buf,sizeof(buf),"%s%s%s %s %s%s%s",pre ? at_prefix[pre] : "",pre ? " " : "",metal,cat_word[IT_TCAT(in)],piece,
			suf ? " of " : "",suf ? skilltab[suf-1].name : "");
	return buf;
}

/* make a new tiered item from a plain helmet or body armor template */
int tier_create(int temp,int tier,int cat,int level)
{
	int in,n;

	if (temp<=0 || temp>=MAXTITEM || tier<TIER_MAGIC || tier>TIER_EPIC) return 0;
	if (!(it_temp[temp].placement&(PL_HEAD|PL_BODY))) return 0;
	if (!(in=god_create_item(temp))) return 0;

	if (cat<TCAT_FIGHTER || cat>TCAT_UTILITY) cat=roll_category();
	level=max(1,min(20,level));

	IT_TIER(in)=tier; IT_TCAT(in)=cat; IT_TLEVEL(in)=level; IT_TBASE(in)=temp;
	IT_TEFFECT(in)=(tier>=TIER_EPIC) ? roll_effect(cat) : 0;

	tier_roll(in,0);

	for (n=0; n<NMETAL; n++) {			// the special sprite of that metal and piece
		if (metals[n].helm==temp) it[in].sprite[0]=metals[n].spr_helm;
		if (metals[n].body==temp) it[in].sprite[0]=metals[n].spr_body;
	}

	it[in].temp=0;					// not the shop's plain stock any more
	it[in].min_rank=level;
	it[in].max_age[0]=it[in].max_age[1]=0;		// no wear
	it[in].max_damage=0;
	it[in].value=it_temp[temp].value*tier_mult[tier];
	it[in].flags|=IF_IDENTIFIED|IF_UPDATE;

	tier_set_names(in);
	return in;
}

/* one tier up (Magic -> Rare -> Epic): keeps its attributes and skills, rolls them
 * on the bigger budget and adds one skill (soulstones, later) */
int tier_upgrade(int in)
{
	if (!IS_SANEITEM(in) || IT_TIER(in)<TIER_MAGIC || IT_TIER(in)>=TIER_EPIC) return 0;
	IT_TIER(in)++;
	if (IT_TIER(in)==TIER_EPIC && !IT_TEFFECT(in)) IT_TEFFECT(in)=roll_effect(IT_TCAT(in));
	tier_roll(in,1);
	it[in].value=it_temp[IT_TBASE(in)].value*tier_mult[IT_TIER(in)];
	tier_set_names(in);
	it[in].flags|=IF_UPDATE;
	return 1;
}

/* new bonuses, same tier, category, level and effect (soulstones, later) */
int tier_reroll(int in)
{
	if (!IS_SANEITEM(in) || IT_TIER(in)<TIER_MAGIC || IT_TIER(in)>TIER_EPIC) return 0;
	tier_roll(in,0);
	tier_set_names(in);
	it[in].flags|=IF_UPDATE;
	return 1;
}

/* a plain helmet or body armor of a metal that fits the item level */
int tier_pick_template(int level,int helm)
{
	int n,cnt=0,ok[NMETAL];

	for (n=0; n<NMETAL; n++) if (level>=metals[n].from && level<=metals[n].to) ok[cnt++]=n;
	if (!cnt) return helm ? 63 : 65;
	n=ok[RANDOM(cnt)];
	return helm ? metals[n].helm : metals[n].body;
}

/* ---- drops ---- */

static int roll_tier(int strong)
{
	int r=RANDOM(100),t;

	if (r<70) t=TIER_MAGIC;
	else if (r<92) t=TIER_RARE;
	else t=TIER_EPIC;		// Epic 7%, and the 1% Legendary until Legendaries exist
	if (strong) {			// Strong monsters: the better of two rolls
		int t2=roll_tier(0);
		if (t2>t) t=t2;
	}
	return t;
}

/* a monster (co) killed by cn: maybe drop a tiered helmet or body armor into its body */
void tier_kill_drop(int cn,int co)
{
	int strong,rank,level,in,cc;

	if (!IS_SANECHAR(cn) || !IS_SANECHAR(co)) return;
	if (ch[co].flags&(CF_PLAYER|CF_LABKEEPER|CF_USURP)) return;
	cc=cn;
	if (!(ch[cc].flags&CF_PLAYER) && IS_SANECHAR(ch[cn].data[63])) cc=ch[cn].data[63];	// a player's companion
	if (!(ch[cc].flags&CF_PLAYER)) return;

	strong=!strncmp(ch[co].name,"Strong ",7);
	if (RANDOM(strong ? 5 : 100)) return;

	rank=points2rank(ch[co].points_tot);
	level=max(1,min(20,rank+RANDOM(3)-1));
	in=tier_create(tier_pick_template(level,RANDOM(2)),roll_tier(strong),0,level);
	if (!in) return;
	if (!god_give_char(in,co)) { it[in].used=USE_EMPTY; return; }
	chlog(cc,"Tier drop: %s (%s, level %d) from %s",it[in].name,tier_word[IT_TIER(in)],level,ch[co].name);
}

/* treasure chests that gave "of the Lion" armor: a Magic piece of that metal */
int tier_chest_item(int temp)
{
	int n,level=6;

	for (n=0; n<NMETAL; n++) if (metals[n].helm==temp || metals[n].body==temp) {
		static int lv[]={3,6,9,12,15,18};
		level=lv[n]+RANDOM(3)-1;
	}
	return tier_create(temp,TIER_MAGIC,0,level);
}

/* ---- display ---- */

int tier_font(int in)	// tooltip font for the name: 10 Common ... 14 Legendary
{
	if (!IS_SANEITEM(in)) return 1;
	if (IT_TIER(in)>=TIER_MAGIC && IT_TIER(in)<=TIER_LEGEND) return 10+IT_TIER(in);
	if (it[in].flags&IF_ARMOR) return 10;
	return 1;
}

/* the extra tooltip lines of a tiered item */
void tier_tip_lines(int in,char *l1,char *l2)
{
	int lv=IT_TLEVEL(in);

	l1[0]=l2[0]=0;
	if (!IT_TIER(in)) return;
	sprintf(l1,"%s %s, item level %d",tier_word[IT_TIER(in)],cat_word[IT_TCAT(in)],lv);
	switch(IT_TEFFECT(in)) {
		case TE_REGEN:	 sprintf(l2,"Regeneration: hp also while active (%d%%)",tier_effect_pct(lv,10,30)); break;
		case TE_CLARITY: sprintf(l2,"Clarity: mana also while active (%d%%)",tier_effect_pct(lv,10,30)); break;
		case TE_STAMINA: sprintf(l2,"Stamina: endurance also while active (%d%%)",tier_effect_pct(lv,10,30)); break;
		case TE_THORNS:	 sprintf(l2,"Thorns: hurts melee attackers"); break;
		case TE_LIGHT:	 sprintf(l2,"Light: shines in the dark"); break;
		case TE_WARDING: sprintf(l2,"Warding: curses and stuns -%d%%",tier_effect_pct(lv,5,25)); break;
		case TE_LASTING: sprintf(l2,"Lasting: your blessings last +%d%%",tier_effect_pct(lv,20,50)); break;
		case TE_ENLIGHT: sprintf(l2,"Enlightened: +%d%% experience from kills",tier_effect_pct(lv,1,5)); break;
	}
}

/* ---- god command: #tier <tier 1-3> <level 1-20> [f|m|c|u] [h|a] ---- */
void god_tier_item(int cn,char *a1,char *a2,char *a3,char *a4)
{
	int tier=atoi(a1),level=atoi(a2),cat=0,helm=RANDOM(2),in;

	if (tier<1 || tier>3 || level<1 || level>20) {
		do_char_log(cn,0,"Usage: #tier <1 Magic, 2 Rare, 3 Epic> <level 1-20> [f|m|c|u (Fighter, Mercenary, Mage, Utility)] [h|a (helmet, armor)]\n");
		return;
	}
	if (a3 && *a3) switch(tolower(*a3)) { case 'f': cat=TCAT_FIGHTER; break; case 'm': cat=TCAT_MERC; break; case 'c': cat=TCAT_MAGE; break; case 'u': cat=TCAT_UTILITY; break; }
	if (a4 && *a4) helm=(tolower(*a4)=='h');

	in=tier_create(tier_pick_template(level,helm),tier,cat,level);
	if (!in) { do_char_log(cn,0,"Could not create it.\n"); return; }
	if (!god_give_char(in,cn)) { it[in].used=USE_EMPTY; do_char_log(cn,0,"Your backpack is full.\n"); return; }
	do_char_log(cn,1,"Made: %s.\n",tier_name(in));
}
