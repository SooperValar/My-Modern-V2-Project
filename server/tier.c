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

void souldestroy(int cn,int in);

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

	snprintf(buf,sizeof(buf),"%s %s %s, item level %d.",IT_TIER(in)==TIER_EPIC ? "An" : "A",tier_word[IT_TIER(in)],tier_name(in),IT_TLEVEL(in));
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

/* Soulstones from any enemy a player (or a player's companion) kills. The chance
 * follows the player's rank, so new players find them often and it tapers off:
 * 1 in (SOULDROP_BASE + SOULDROP_PER_RANK * rank) kills - 1 in 20 for a Private,
 * 1 in 80 at rank 10, 1 in 158 at rank 23. The stone is made like a Strong
 * enemy's: 10-15% of the enemy's experience value, its level from that. Strong
 * enemies already carry one and don't roll again. */
#define SOULDROP_BASE		20
#define SOULDROP_PER_RANK	6
void soul_kill_drop(int cn,int co)
{
	int cc,exp,rank,in;

	if (!IS_SANECHAR(cn) || !IS_SANECHAR(co)) return;
	if (ch[co].flags&(CF_PLAYER|CF_LABKEEPER|CF_USURP)) return;
	cc=cn;
	if (!(ch[cc].flags&CF_PLAYER) && IS_SANECHAR(ch[cn].data[63])) cc=ch[cn].data[63];	// a player's companion
	if (!(ch[cc].flags&CF_PLAYER)) return;
	if (!strncmp(ch[co].name,"Strong ",7)) return;
	if (RANDOM(SOULDROP_BASE+SOULDROP_PER_RANK*points2rank(ch[cc].points_tot))) return;

	exp=ch[co].points_tot/10+RANDOM(ch[co].points_tot/20+1);
	if (exp<1) return;
	rank=points2rank(exp);
	in=god_create_item(1146);
	if (!in) return;
	sprintf(it[in].name,"Soulstone");
	sprintf(it[in].reference,"soulstone");
	sprintf(it[in].description,"Level %d soulstone, holding %d exp.",rank,exp);
	it[in].data[0]=rank;
	it[in].data[1]=exp;
	it[in].temp=0;
	it[in].driver=68;
	if (!god_give_char(in,co)) { it[in].used=USE_EMPTY; return; }
	chlog(cc,"Soulstone drop: level %d from %s",rank,ch[co].name);
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

/* MyV2 chests: a new tiered helmet or body armor.
 * tiers: bit 1 Magic, 2 Rare, 3 Epic (with several, the odds of monster drops 70:22:8);
 * metals: bit 0 Bronze .. 5 Titanium, 0 = a metal that fits the level; piece: 1 helmet, 2 body armor, 0 either;
 * level from lo to hi (1-20); lo 0 = a level inside the metal's own range (older chest lines) */
int tier_chest_reward(int tiers,int metals_mask,int piece,int lo,int hi)
{
	static int odds[4]={0,70,22,8};
	int n,tot=0,r,tier=TIER_MAGIC,level,helm,cand[NMETAL],nc=0,m;

	for (n=TIER_MAGIC; n<=TIER_EPIC; n++) if (tiers&(1<<n)) tot+=odds[n];
	if (tot) { r=RANDOM(tot); for (n=TIER_MAGIC; n<=TIER_EPIC; n++) if (tiers&(1<<n)) { if (r<odds[n]) { tier=n; break; } r-=odds[n]; } }
	helm=piece==1 ? 1 : piece==2 ? 0 : RANDOM(2);
	for (n=0; n<NMETAL; n++) if (metals_mask&(1<<n)) cand[nc++]=n;

	if (lo<=0) {					// a level that fits the metal
		m=nc ? cand[RANDOM(nc)] : RANDOM(NMETAL);
		level=metals[m].from+RANDOM(metals[m].to-metals[m].from+1);
		return tier_create(helm ? metals[m].helm : metals[m].body,tier,0,level);
	}
	lo=max(1,min(20,lo)); hi=max(lo,min(20,hi));
	level=lo+RANDOM(hi-lo+1);
	if (!nc) return tier_create(tier_pick_template(level,helm),tier,0,level);	// the metal fits the level
	m=cand[RANDOM(nc)];
	return tier_create(helm ? metals[m].helm : metals[m].body,tier,0,level);
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
	l1[0]=l2[0]=0;
	if (!IT_TIER(in)) return;
	sprintf(l1,"%s %s, item level %d",tier_word[IT_TIER(in)],cat_word[IT_TCAT(in)],IT_TLEVEL(in));
}

/* the Epic effect for the tooltip: its name, then up to 3 short lines (at
 * most about 36 characters, like the description). Returns the number of lines. */
int tier_tip_effect(int in,char lines[4][60])
{
	int lv=IT_TLEVEL(in),act=tier_effect_pct(lv,10,30),rest=tier_effect_pct(lv,1,5);
	char *what=NULL;

	if (!IT_TIER(in) || !IT_TEFFECT(in)) return 0;
	switch(IT_TEFFECT(in)) {
		case TE_REGEN:		what="Hitpoints"; strcpy(lines[0],"Effect: Regeneration"); break;
		case TE_CLARITY:	what="Mana"; strcpy(lines[0],"Effect: Clarity"); break;
		case TE_STAMINA:	what="Endurance"; strcpy(lines[0],"Effect: Stamina"); break;
	}
	if (what) {
		sprintf(lines[1],"%s keep regenerating while",what);
		sprintf(lines[2],"moving or fighting (%d%% of normal),",act);
		sprintf(lines[3],"and %d%% faster while resting.",rest);
		return 4;
	}
	switch(IT_TEFFECT(in)) {
		case TE_THORNS:
			strcpy(lines[0],"Effect: Thorns");
			sprintf(lines[1],"Melee attackers take 1-%d damage.",max(1,lv/2));
			return 2;
		case TE_LIGHT:
			strcpy(lines[0],"Effect: Light");
			strcpy(lines[1],"You give off light.");
			return 2;
		case TE_WARDING:
			strcpy(lines[0],"Effect: Warding");
			strcpy(lines[1],"Curses and stuns on you");
			sprintf(lines[2],"wear off %d%% sooner.",tier_effect_pct(lv,5,25));
			return 3;
		case TE_LASTING:
			strcpy(lines[0],"Effect: Lasting");
			strcpy(lines[1],"Your Bless, Enhance Weapon,");
			sprintf(lines[2],"Protection and Light last %d%% longer.",tier_effect_pct(lv,20,50));
			return 3;
		case TE_ENLIGHT:
			strcpy(lines[0],"Effect: Enlightened");
			sprintf(lines[1],"%d%% more experience from kills.",tier_effect_pct(lv,1,5));
			return 2;
	}
	return 0;
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

/* ======================================================================
 * Part 2: soulstones, Soul Crucibles and upgrade stones
 *
 *  - soulstone on a plain helmet / body armor: it becomes Magic, item level =
 *    the stone's level (at most 20)
 *  - soulstone of the item's own level on a Magic / Rare / Epic piece: reroll
 *  - Soul Crucible (Lesser up to stone level 7, Soul Crucible 14, Greater 20):
 *    two soulstones go in (different levels: a warning, the lower level counts),
 *    an upgrade stone comes out; the crucible is used up
 *  - upgrade stone one level above the item: Magic -> Rare -> Epic; on an Epic
 *    it rerolls the special effect
 *  - soulstones are not used on weapons for now; Legendaries can't be changed
 * ====================================================================== */

#define SOULSTONE_TEMP	1146

// experience at the start of each rank (points2rank's thresholds)
static int rank_exp[24]={0,50,850,4900,17700,48950,113750,233800,438600,766650,1266650,1998700,
	3035500,4463550,6384350,8915600,12192400,16368450,21617250,28133300,36133300,49014500,63000600,80977100};

static int is_tier_piece(int temp)	// a plain helmet or body armor of the tier metals
{
	int n;
	for (n=0; n<NMETAL; n++) if (metals[n].helm==temp || metals[n].body==temp) return 1;
	return 0;
}

int tier_make_soulstone(int level,int exp)	// a soulstone like the ones Strong monsters carry
{
	int in;

	if (!exp) exp=rank_exp[max(0,min(23,level))]+1;
	if (!(in=god_create_item(SOULSTONE_TEMP))) return 0;
	level=points2rank(exp);
	sprintf(it[in].name,"Soulstone");
	sprintf(it[in].reference,"soulstone");
	sprintf(it[in].description,"Level %d soulstone, holding %d exp.",level,exp);
	it[in].data[0]=level;
	it[in].data[1]=exp;
	it[in].temp=0;
	it[in].driver=68;
	return in;
}

int tier_make_upstone(int level)
{
	int in;

	if (!(in=god_create_item(TIER_UPSTONE_TEMP))) return 0;
	it[in].data[0]=level;
	sprintf(it[in].name,"Upgrade Stone");
	sprintf(it[in].reference,"upgrade stone");
	sprintf(it[in].description,"A level %d upgrade stone. Use it with a level %d helmet or armor on your cursor to raise its tier.",level,level-1);
	it[in].temp=0;
	return in;
}

// take the item on the cursor away and put a new one there
static void replace_citem(int cn,int in2,int in3)
{
	it[in2].used=USE_EMPTY;
	ch[cn].citem=in3;
	it[in3].carried=cn;
	it[in3].flags|=IF_UPDATE;
	do_update_char(cn);
}

/* a soulstone (in) used with the item on the cursor (in2). Returns -1 when it
 * is not a tier matter (the old soulstone uses go on), else 0 or 1. */
int tier_soulstone(int cn,int in,int in2)
{
	int lv=it[in].data[0],in3;

	if (it[in2].flags&IF_WEAPON) {
		do_char_log(cn,0,"Soulstones can't be used on weapons yet.\n");
		return 0;
	}
	if (IT_TIER(in2)==TIER_LEGEND) {
		do_char_log(cn,0,"This item is too powerful to change.\n");
		return 0;
	}
	if (IT_TIER(in2)) {				// reroll
		if (lv!=IT_TLEVEL(in2)) {
			do_char_log(cn,0,"That needs a level %d soulstone (this one is level %d).\n",IT_TLEVEL(in2),lv);
			return 0;
		}
		tier_reroll(in2);
		souldestroy(cn,in);
		do_update_char(cn);
		do_char_log(cn,1,"The soulstone sinks into the armor. Its powers shift.\n");
		chlog(cn,"Soulstone reroll: %s",it[in2].name);
		return 1;
	}
	if (is_tier_piece(it[in2].temp)) {		// plain piece: becomes Magic
		if (!(in3=tier_create(it[in2].temp,TIER_MAGIC,0,min(20,max(1,lv))))) return 0;
		souldestroy(cn,in);
		replace_citem(cn,in2,in3);
		do_char_log(cn,1,"The soulstone sinks into the armor. Magical powers awaken in it.\n");
		chlog(cn,"Soulstone made %s",it[in3].name);
		return 1;
	}
	return -1;
}

/* driver 73: Soul Crucible. data[0] highest stone level, data[1] level inside
 * (0 empty), data[2] its experience, data[3] warning until (ticker), data[4]
 * the empty sprite (half +1, full +2), data[5] 1 when it holds an upgrade stone */
int use_soul_crucible(int cn,int in)
{
	int in2=ch[cn].citem,lv,in3;

	if (!it[in].carried) { do_char_log(cn,0,"Pick it up first.\n"); return 0; }

	if (!in2 || (in2&0x80000000)) {		// empty hand: take out what is inside
		if (it[in].data[5]) {
			if (!(in3=tier_make_upstone(it[in].data[1]))) return 0;
			god_take_from_char(in,cn); it[in].used=USE_EMPTY;
			ch[cn].citem=in3; it[in3].carried=cn;
			do_char_log(cn,1,"You take out the level %d upgrade stone. The crucible crumbles to dust.\n",it[in3].data[0]);
			do_update_char(cn);
			return 1;
		}
		if (it[in].data[1]) {
			if (!(in3=tier_make_soulstone(it[in].data[1],it[in].data[2]))) return 0;
			ch[cn].citem=in3; it[in3].carried=cn;
			it[in].data[1]=it[in].data[2]=0; it[in].sprite[0]=it[in].data[4]; it[in].flags|=IF_UPDATE;
			do_char_log(cn,1,"You take the soulstone back out.\n");
			do_update_char(cn);
			return 1;
		}
		do_char_log(cn,1,"A %s. Put two soulstones of the same level (up to level %d) into it to make an upgrade stone: hold a soulstone and use the crucible.\n",
			it[in].name,it[in].data[0]);
		return 0;
	}
	if (it[in].data[5]) { do_char_log(cn,0,"The crucible already holds an upgrade stone. Use it with an empty hand to take it out.\n"); return 0; }
	if (it[in2].driver!=68) { do_char_log(cn,0,"Only soulstones go into a soul crucible.\n"); return 0; }

	lv=it[in2].data[0];
	if (lv>it[in].data[0]) { do_char_log(cn,0,"This crucible is too weak for a level %d soulstone (up to level %d).\n",lv,it[in].data[0]); return 0; }

	if (!it[in].data[1]) {				// the first stone
		it[in].data[1]=lv; it[in].data[2]=it[in2].data[1];
		ch[cn].citem=0; it[in2].used=USE_EMPTY;
		it[in].sprite[0]=it[in].data[4]+1; it[in].flags|=IF_UPDATE;
		do_char_log(cn,1,"The level %d soulstone sinks into the crucible. Add a second one of the same level.\n",lv);
		do_update_char(cn);
		return 1;
	}

	if (lv!=it[in].data[1] && it[in].data[3]<globs->ticker) {	// different levels: warn once
		it[in].data[3]=globs->ticker+TICKS*15;
		do_char_log(cn,0,"The stones differ: level %d inside, level %d in your hand. The upgrade stone would only be level %d. Use the crucible again to combine them anyway.\n",
			it[in].data[1],lv,min(lv,it[in].data[1]));
		return 0;
	}

	lv=min(lv,it[in].data[1]);
	ch[cn].citem=0; it[in2].used=USE_EMPTY;
	it[in].data[1]=lv; it[in].data[2]=0; it[in].data[3]=0; it[in].data[5]=1;
	it[in].sprite[0]=it[in].data[4]+2; it[in].flags|=IF_UPDATE;
	do_char_log(cn,1,"The two soulstones melt together into a level %d upgrade stone. Use the crucible with an empty hand to take it out.\n",lv);
	chlog(cn,"Soul crucible: level %d upgrade stone",lv);
	do_update_char(cn);
	return 1;
}

// a different Epic effect (upgrade stone on an Epic)
static void tier_new_effect(int in)
{
	int old=IT_TEFFECT(in),lv=IT_TLEVEL(in),e,tries=0;

	do e=roll_effect(IT_TCAT(in)); while (e==old && ++tries<20);
	if (old==TE_LIGHT) it[in].light[0]-=8+lv;
	IT_TEFFECT(in)=e;
	if (e==TE_LIGHT) it[in].light[0]+=8+lv;	// Light: on the item (light doesn't add up anyway, the brightest counts)
	it[in].flags|=IF_UPDATE;
}

/* driver 74: upgrade stone, used with a helmet or armor on the cursor */
int use_upgrade_stone(int cn,int in)
{
	int in2=ch[cn].citem,lv=it[in].data[0],need;

	if (!in2 || (in2&0x80000000)) {
		do_char_log(cn,1,"A level %d upgrade stone. Hold a level %d Magic, Rare or Epic helmet or armor and use the stone with it.\n",lv,lv-1);
		return 0;
	}
	if (it[in2].flags&IF_WEAPON) { do_char_log(cn,0,"Upgrade stones can't be used on weapons yet.\n"); return 0; }
	if (IT_TIER(in2)==TIER_LEGEND) { do_char_log(cn,0,"This item is too powerful to change.\n"); return 0; }
	if (!IT_TIER(in2)) { do_char_log(cn,0,"Only Magic, Rare and Epic helmets and armor can be upgraded. A soulstone makes a plain piece Magic.\n"); return 0; }

	need=IT_TLEVEL(in2)+1;
	if (lv!=need) { do_char_log(cn,0,"That needs a level %d upgrade stone (item level %d + 1); this one is level %d.\n",need,IT_TLEVEL(in2),lv); return 0; }

	god_take_from_char(in,cn); it[in].used=USE_EMPTY;
	if (IT_TIER(in2)==TIER_EPIC) {
		tier_new_effect(in2);
		do_char_log(cn,1,"The armor's glow flickers and settles. Its special power has changed.\n");
	} else {
		tier_upgrade(in2);
		do_char_log(cn,1,"The armor's glow intensifies for a moment. Afterward, you feel it has become more powerful.\n");
	}
	chlog(cn,"Upgrade stone: %s",it[in2].name);
	do_update_char(cn);
	return 1;
}

/* god commands: #soullevel <level>, #upstone <level> */
void god_soul_level(int cn,char *a1,int up)
{
	int lv=atoi(a1),in;

	if (lv<1 || lv>23) { do_char_log(cn,0,"Usage: #%s <level 1-23>\n",up ? "upstone" : "soullevel"); return; }
	in=up ? tier_make_upstone(lv) : tier_make_soulstone(lv,0);
	if (!in) return;
	if (!god_give_char(in,cn)) { it[in].used=USE_EMPTY; do_char_log(cn,0,"Your backpack is full.\n"); return; }
	do_char_log(cn,1,"Made a level %d %s.\n",it[in].data[0],up ? "upgrade stone" : "soulstone");
}

/* ======================================================================
 * Part 3: the Epic special effects in the game
 * Several pieces with the same effect don't add up: the best one counts.
 * ====================================================================== */

/* the item level of the best worn Epic (or better) piece with effect e, 0 none */
int tier_char_effect(int cn,int e)
{
	int n,in,best=0;

	if (!IS_SANECHAR(cn) || !(ch[cn].flags&(CF_PLAYER|CF_USURP))) return 0;
	for (n=0; n<20; n++) {
		if (!(in=ch[cn].worn[n]) || !IS_SANEITEM(in)) continue;
		if (IT_TIER(in)<TIER_EPIC || IT_TEFFECT(in)!=e) continue;
		if (IT_TLEVEL(in)>best) best=IT_TLEVEL(in);
	}
	return best;
}

// pct percent of v, the fraction rounded at random (regeneration per tick is small)
static int pct_of(int v,int pct)
{
	int x=v*pct;
	return x/100+(RANDOM(100)<x%100 ? 1 : 0);
}

/* Regeneration / Clarity / Stamina, once a tick from do_regenerate(): standing
 * still gives +1..5% faster regeneration, anything else 10..30% of the standing rate */
void tier_regen(int cn,int standing,int moonmult,int nohp,int noend,int nomana)
{
	int lv,rate;

	if (!(ch[cn].flags&(CF_PLAYER|CF_USURP)) || ch[cn].stunned) return;

	if (!nohp && (lv=tier_char_effect(cn,TE_REGEN))) {
		rate=moonmult*2+(ch[cn].skill[SK_REGEN][0] ? ch[cn].skill[SK_REGEN][5]*moonmult/30 : 0);
		ch[cn].a_hp+=pct_of(rate,tier_effect_pct(lv,standing ? 1 : 10,standing ? 5 : 30));
	}
	if (!noend && (lv=tier_char_effect(cn,TE_STAMINA))) {
		rate=moonmult*4+(ch[cn].skill[SK_REST][0] ? ch[cn].skill[SK_REST][5]*moonmult/30 : 0);
		ch[cn].a_end+=pct_of(rate,tier_effect_pct(lv,standing ? 1 : 10,standing ? 5 : 30));
	}
	if (!nomana && (lv=tier_char_effect(cn,TE_CLARITY))) {
		rate=moonmult+(ch[cn].skill[SK_MEDIT][0] ? ch[cn].skill[SK_MEDIT][5]*moonmult/30 : 0);
		ch[cn].a_mana+=pct_of(rate,tier_effect_pct(lv,standing ? 1 : 10,standing ? 5 : 30));
	}
}

/* Thorns: damage to melee attackers, 1..(level/2); added in really_update_char()
 * from the best piece (not stored on the item, so two pieces don't add up) */
int tier_thorns(int cn)
{
	int lv=tier_char_effect(cn,TE_THORNS);
	return lv ? max(1,lv/2) : 0;
}

/* Warding: a curse or stun on co lasts 5..25% shorter */
int tier_ward(int co,int duration)
{
	int lv=tier_char_effect(co,TE_WARDING);
	if (!lv) return duration;
	return max(1,duration-duration*tier_effect_pct(lv,5,25)/100);
}

/* Lasting: Bless, Enhance Weapon, Protection and Light cast by cn last 20..50% longer */
int tier_lasting(int cn,int duration)
{
	int lv=tier_char_effect(cn,TE_LASTING);
	if (!lv) return duration;
	return duration+duration*tier_effect_pct(lv,20,50)/100;
}

/* Enlightened: experience from kills +1..5% */
int tier_enlightened(int cn,int p)
{
	int lv=tier_char_effect(cn,TE_ENLIGHT);
	if (!lv || p<=0) return p;
	return p+max(1,p*tier_effect_pct(lv,1,5)/100);
}

/* ======================================================================
 * Part 4: the glow (the client draws a faint outline in the tier colour)
 * ====================================================================== */

/* the glow of one item: its tier 1-4, 0 none */
int tier_item_glow(int in)
{
	if (!IS_SANEITEM(in) || it[in].used==USE_EMPTY) return 0;
	if (IT_TIER(in)>=TIER_MAGIC && IT_TIER(in)<=TIER_LEGEND) return IT_TIER(in);
	return 0;
}

static int special_item(int in,int backpack)
{
	if (!in || (in&0x80000000) || !IS_SANEITEM(in) || it[in].used==USE_EMPTY) return 0;
	if (IT_TIER(in)>=TIER_MAGIC) return 1;		// Magic, Rare, Epic, Legendary
	if (is_unique(in)) return 1;			// unique weapons and the like
	if (it[in].driver==68) return 1;		// a soulstone
	if (backpack && (it[in].flags&IF_MAGIC)) return 1;	// carried magic things: potions, scrolls, rings...
	return 0;
}

/* does this body (or its grave) glow? A player's always does while it holds
 * anything (their belongings); an NPC's only when it holds something special -
 * not for the weapon and armor it fought with, or gold */
static int body_has_items(int co)
{
	int n;

	if (!IS_SANECHAR(co) || !(ch[co].flags&CF_BODY)) return 0;
	if (ch[co].data[99]) {	// a player's body
		if (ch[co].gold) return 1;
		if (ch[co].citem && !(ch[co].citem&0x80000000)) return 1;
		for (n=0; n<40; n++) if (ch[co].item[n]) return 1;
		for (n=0; n<20; n++) if (ch[co].worn[n]) return 1;
		return 0;
	}
	if (special_item(ch[co].citem,1)) return 1;
	for (n=0; n<40; n++) if (special_item(ch[co].item[n],1)) return 1;
	for (n=0; n<20; n++) if (special_item(ch[co].worn[n],0)) return 1;
	return 0;
}

/* the glow of a map tile for the client: the item's tier (1-4), 5 for a grave
 * that holds something worth a look (body_has_items), +8 when the character
 * there is such a body */
int tier_tile_glow(int in,int cn)
{
	int g=0;

	if (in) {
		g=tier_item_glow(in);
		if (!g && IS_SANEITEM(in) && it[in].driver==7 && body_has_items(it[in].data[0])) g=5;
	}
	if (cn && body_has_items(cn)) g|=8;
	return g;
}

/* ======================================================================
 * Item marks: small text the client draws on an item in the backpack, worn
 * slots and shop/grave windows. Spell scrolls: the god's initial top left
 * (Ankh A, Ishtar I, Skua S, the plain "Spell of" none), charges top right.
 * ====================================================================== */
void item_marks(int in,unsigned char *letter,unsigned char *number)
{
	*letter=0; *number=255;		// 255: no number
	if (!IS_SANEITEM(in) || it[in].used==USE_EMPTY) return;
	if (it[in].driver==48) {	// spell scroll: data[1] power, data[2] charges
		int p=it[in].data[1];
		if (p>=300) *letter='S';
		else if (p>=150) *letter='I';
		else if (p>=75) *letter='A';
		*number=(unsigned char)min(254,(int)it[in].data[2]);
	}
}
