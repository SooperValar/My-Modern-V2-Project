/*************************************************************************
 MyV2: custom NPC dialogue, kill tracking and quest steps (written by the MyV2 Editor)

 .dat/npctalk.dat (text, one command per line, # = comment):
   quest <n> <name>               quest 1-255 and its name (the player's #journal shows it)
   step <n> <value> <text>        journal text for quest n at that step ("Bring a Potion of Life to the Captain.")
   npc <template> [comment]       the lines after this belong to this NPC (the quest giver)
   when say <words...>            a player says something near it: every word must be there,
                                  a|b = either, ring* = ring, rings, ...
   when give <item template>      a player hands it this item
   when kill <name>|#<t>,<t>...   a player (or their companion, or someone in their group nearby)
                                  kills an NPC with this name (Spider*, a|b) or these template numbers
   when near                      a player comes close (with "Greets players" on): each player at most once a minute;
                                  if no line fits, it says its normal greeting
   when money <silver>            a player hands it at least this much money (it keeps it; if no line fits, it refuses)
   at <x> <y> [comment]           the lines after this belong to the item on that tile (a portal, door, lever...)
   when use                       a player uses that item; if no line fits, the item works as usual
   if quest <n> <op> <v>          op: = != < > <= >=
   if has <item template>         the player carries one   (if !has: does not)
   if rank <op> <v>
   if skill <nr> <op> <v>         the player's skill (0 = doesn't know it; Bartering is 12)
   if gold <op> <silver>          money the player carries
   if area <text>                 where it happens (the player; for kills: the victim) is in an
                                  area whose name contains this
   answer <text>                  the NPC says it aloud (%s = the player's name, {q2} = quest 2's value)
   tell <text>                    only the player sees it
   announce <text>                everyone online sees it
   set quest <n> <v> | add quest <n> <v>
   give item <t> | give exp <n> | give gold <silver> | give luck <n>
   teach skill <nr>               the player learns the skill (if they don't have it)
   take item <t>                  takes one from the player's backpack
   take gold <silver>             takes money from the player (if they have it)
   cast <spell> <power>           the NPC casts it on the player: bless, protect, enhance, mshield, light, heal
                                  (the game lowers the power to what the player can take)
   teleport <x> <y>
   keep                           (when give) the NPC keeps the item; otherwise it hands it back
   pass                           (when use) afterwards the item works as usual (otherwise the line replaces it)
   end
 For a player, the first entry whose trigger and conditions match is used.

   chest <x> <y> [comment]        the item on that tile (driver 75) is a MyV2 chest; its lines:
   refill <seconds>               how long it stays open (empty) before it can be opened again
   once player                    each player gets something from it only once (else "It's empty")
   first <t>                      the first time each player opens it, they get this item instead of a
                                  draw. Players who haven't had theirs can take it even while the chest is open
                                  (empty); if it was closed, it opens and stays empty for its refill time, like a
                                  normal opening. After that, the player gets the normal draws like everyone else.
   reward item <t> <weight>       a reward, chosen at random by weight
   reward gold <silver> <weight>
   reward tier <tiers> <metals> <helm|armor|any> <level from> <level to> <weight>
                                  a tiered piece, made new. tiers: magic,rare,epic (one or more; with several,
                                  the odds of monster drops: 70:22:8); metals: fit (a metal that fits the
                                  level) or bronze,steel,golden,emerald,crystal,titanium (one or more);
                                  the level (1-20, also the rank needed) is picked in the range
                                  (the older form "<tier> <metal|any> <piece> <weight>" still works)
   reward unique <t> <weight>     an item this chest gives only once on the whole server
   reward nothing <weight>        "It's empty..."
   end
   (rewards that can't be given any more - a unique already given, an item marked Unique that
   exists somewhere - are left out of the draw; if nothing is left, the chest is empty)

 .dat/chestlog.dat: which player got something from which once-per-player chest, and which
 unique rewards were given (text, one line each).

 .dat/quest.dat: the quest steps of every character (255 per character), kept with the
 character's creation date so a new character in an old slot starts clean. (A file of the
 first version, 31 quests and no header, is converted when the server opens it.)
**************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <unistd.h>
#include <fcntl.h>
#include <time.h>
#include "server.h"

#define TALK_FILE DATDIR"/npctalk.dat"
#define QUEST_FILE DATDIR"/quest.dat"
#define QVARS 255
#define QHDR 16
#define OLDQVARS 31
#define MAXENT 3000
#define MAXSTEP 1000
#define MAXCOND 8
#define MAXEFF 16
#define POOL (768*1024)

enum { C_QUEST=1, C_HAS, C_HASNOT, C_RANK, C_AREA, C_SKILL, C_GOLD, C_CLASS };

/* classes, for "if class ..." lines and class rewards of item quests: the character's kindred bits */
static struct { char *name; unsigned int kin; } classname[]={
	{"templar",KIN_TEMPLAR},{"archtemplar",KIN_ARCHTEMPLAR},{"harakim",KIN_HARAKIM},{"archharakim",KIN_ARCHHARAKIM},
	{"mercenary",KIN_MERCENARY},{"warrior",KIN_WARRIOR},{"sorcerer",KIN_SORCERER},{"seyan",KIN_SEYAN_DU},
	{"templars",KIN_TEMPLAR|KIN_ARCHTEMPLAR},{"harakims",KIN_HARAKIM|KIN_ARCHHARAKIM},
	{"mercenaries",KIN_MERCENARY|KIN_WARRIOR|KIN_SORCERER|KIN_SEYAN_DU},{NULL,0}};
static const unsigned int class_groups[3]={KIN_TEMPLAR|KIN_ARCHTEMPLAR, KIN_MERCENARY|KIN_WARRIOR|KIN_SORCERER|KIN_SEYAN_DU, KIN_HARAKIM|KIN_ARCHHARAKIM};

/* the class group of character co for class rewards: 0 Templar / Arch-Templar, 1 Mercenary / Warrior / Sorcerer / Seyan'Du,
 * 2 Harakim / Arch-Harakim, -1 none */
int class_group(int co)
{
	int g;
	if (!IS_SANECHAR(co)) return -1;
	for (g=0; g<3; g++) if (ch[co].kindred&class_groups[g]) return g;
	return -1;
}

static unsigned int class_mask(char *s)		// "templar|archtemplar" -> kindred bits
{
	unsigned int m=0; int k; char w[32],*p=s;
	while (*p) {
		int n=0;
		while (*p=='|' || isspace((unsigned char)*p)) p++;
		while (*p && *p!='|' && !isspace((unsigned char)*p) && n<31) w[n++]=tolower((unsigned char)*p++);
		w[n]=0; if (!n) break;
		for (k=0; classname[k].name; k++) if (!strcmp(w,classname[k].name)) m|=classname[k].kin;
	}
	return m;
}
enum { E_ANSWER=1, E_SETQ, E_ADDQ, E_ITEM, E_EXP, E_GOLD, E_TAKE, E_KEEP, E_TELL, E_ANNOUNCE, E_LUCK, E_SKILL, E_TELEPORT, E_PASS, E_TAKEGOLD, E_CAST };
enum { OP_EQ, OP_NE, OP_LT, OP_GT, OP_LE, OP_GE };
enum { T_SAY, T_GIVE, T_KILL, T_USE, T_NEAR, T_MONEY };
static char *spellname[]={"bless","protect","enhance","mshield","light","heal",NULL};
int spell_bless(int cn,int co,int power);
int spell_protect(int cn,int co,int power);
int spell_enhance(int cn,int co,int power);
int spell_mshield(int cn,int co,int power);
int spell_light(int cn,int co,int power);
int spell_heal(int cn,int co,int power);

struct tcond { char type, op; int n, v; };
struct teff { char type; int a, b; int str; };
struct tentry {
	int temp;		// the NPC it belongs to
	char trig;
	int give;		// item template for "when give"; for "when use" the tile x
	int ux, uy;		// "when use": the tile
	int words;		// pool offset: the words (say) or the victim (kill)
	struct tcond c[MAXCOND]; int nc;
	struct teff e[MAXEFF]; int ne;
};
struct tstep { char n; unsigned short v; int str; };
struct qrow { int stamp; unsigned short v[QVARS]; };

/* chests */
#define MAXCHEST 600
#define MAXREW 16
enum { RW_ITEM=1, RW_GOLD, RW_TIER, RW_UNIQUE, RW_NOTHING };
struct reward { char type; int a, b, c, d, e, w; };
struct chest { int x, y, refill, once, first; struct reward r[MAXREW]; int nr; };
static struct chest chests[MAXCHEST];
static int nchest=0;
#define CHESTLOG DATDIR"/chestlog.dat"
static struct { int x, y, cn, stamp, when; char kind; } *opened=NULL;	// once-per-player chests already opened (P), first rewards given (F)
static int nopened=0, maxopened=0;
static int given_unique[512], ngiven=0;
static int chestlog_loaded=0;

static struct tentry ent[MAXENT];
static char hasnear[MAXTCHARS];		// templates with "when near" lines
#define QSTAGES 8
struct qstage { int times, item, exp, gold; };
struct qrew { int limit, first, gold1, nst; struct qstage st[QSTAGES]; int rmin1, rmax1; };	// rmin1/rmax1: rank + 1, 0 = none
static struct qrew qrew[MAXTCHARS];
/* item quests: what some classes get instead ("qclass <t> <classes, joined by |> <skill> <item>": -1 = as for everyone,
 * 0 = none); a quest's rules in file order, the first one that has the player's class counts */
#define MAXQCLS 2048
struct qcls { int t; unsigned int mask; int skill, item; };
static struct qcls qcls[MAXQCLS];
static int nqcls=0;
static const struct qcls *qcls_find(int t,int co)
{
	int n;
	if (!IS_PLAYER(co)) return NULL;
	for (n=0; n<nqcls; n++) if (qcls[n].t==t && (ch[co].kindred&qcls[n].mask)) return &qcls[n];
	return NULL;
}	// item quests: repeats and later rewards ("qreward")
static short qorder[MAXTCHARS];		// #quest: place in the list ("order <template> <n>", the editor's Quests page); 0 = by exp, -1 = not listed

/* ---- area clears (the editor's Quests page): kill every listed NPC of an area for an experience bonus.
 *   clear <id> <exp> <again as Seyan'Du 0/1> <zone name>      the area (a zone, any of its boxes)
 *   clearlabel <id> <text>                                    what the counter calls them ("Ghosts")
 *   clearnpc <id> <template>...                               the NPCs to kill (each placed NPC has its own template)
 * Progress per character in .dat/clears.dat. A kill counts for the killer (or a companion's master) and the members
 * of their group, each only while standing in the area. Once per character; with "again as Seyan'Du" once more
 * after becoming a Seyan'Du. A changed NPC list starts everyone's progress in that area again (not the done flag). */
#define MAXCLEAR	64
#define CLEARNPC	64
#define CLEAR_FILE	DATDIR"/clears.dat"
struct clear { int used, exp, seyan, n, t[CLEARNPC]; char zone[48], label[40]; unsigned short hash; };
static struct clear clears[MAXCLEAR+1];
static void clear_hashes(void);
static struct tstep step[MAXSTEP];
static int qname[QVARS+1];
static int nent=0, nstep=0, talk_loaded=0;
static char pool[POOL];
static int plen=0;
static int qfd=-2;

static int pool_add(char *s)
{
	int l=strlen(s)+1,o=plen;
	if (plen+l>POOL) return 0;
	memcpy(pool+plen,s,l); plen+=l;
	return o;
}

static int parse_op(char *s)
{
	if (!strcmp(s,"=") || !strcmp(s,"==")) return OP_EQ;
	if (!strcmp(s,"!=")) return OP_NE;
	if (!strcmp(s,"<")) return OP_LT;
	if (!strcmp(s,">")) return OP_GT;
	if (!strcmp(s,"<=")) return OP_LE;
	if (!strcmp(s,">=")) return OP_GE;
	return -1;
}

static int cmp_op(int a,int op,int b)
{
	switch (op) {
		case OP_EQ: return a==b; case OP_NE: return a!=b; case OP_LT: return a<b;
		case OP_GT: return a>b; case OP_LE: return a<=b; case OP_GE: return a>=b;
	}
	return 0;
}

static void lower(char *s) { for (; *s; s++) *s=tolower((unsigned char)*s); }

int talk_load(void)
{
	FILE *f;
	char line[1024],w1[64],w2[64],op[16],*p,*q;
	int temp=0,n,v,x,y,ln=0,bad=0,ax=0,ay=0;
	struct tentry *e=NULL;
	struct chest *ch_=NULL;

	nent=nstep=0; nchest=0; plen=1; pool[0]=0; talk_loaded=1;
	memset(hasnear,0,sizeof(hasnear));
	memset(qorder,0,sizeof(qorder));
	memset(qrew,0,sizeof(qrew));
	nqcls=0;
	memset(clears,0,sizeof(clears));
	memset(qname,0,sizeof(qname));
	f=fopen(TALK_FILE,"r");
	if (!f) return 0;
	while (fgets(line,sizeof(line),f)) {
		ln++;
		line[strcspn(line,"\r\n")]=0;
		for (p=line; isspace((unsigned char)*p); p++) ;
		if (!*p || *p=='#') continue;
		w1[0]=w2[0]=0;
		sscanf(p,"%63s %63s",w1,w2);
		q=p+strlen(w1); while (isspace((unsigned char)*q)) q++;		// the rest after the first word
		if (!strcmp(w1,"quest")) {
			n=atoi(q); while (*q && !isspace((unsigned char)*q)) q++; while (isspace((unsigned char)*q)) q++;
			if (n>=1 && n<=QVARS) qname[n]=pool_add(q);
			continue;
		}
		if (!strcmp(w1,"qreward")) {		// qreward <t> <limit> <first> <gold> [<item2> <exp2> <gold2>: the older one-step form]
			int a[7],k=sscanf(q,"%d %d %d %d %d %d %d",&a[0],&a[1],&a[2],&a[3],&a[4],&a[5],&a[6]);
			n=a[0];
			if ((k==4 || k==7) && n>0 && n<MAXTCHARS && a[1]>=0 && a[2]>=0 && a[3]>=0) {
				int r1=qrew[n].rmin1,r2=qrew[n].rmax1;
				memset(&qrew[n],0,sizeof(qrew[n]));
				qrew[n].rmin1=r1; qrew[n].rmax1=r2;
				qrew[n].limit=a[1]; qrew[n].first=a[2]; qrew[n].gold1=a[3];
				if (k==7 && (a[4] || a[5] || a[6])) { qrew[n].st[0].item=a[4]>0 && a[4]<MAXTITEM ? a[4] : 0; qrew[n].st[0].exp=a[5]>0 ? a[5] : 0; qrew[n].st[0].gold=a[6]>0 ? a[6] : 0; qrew[n].nst=1; }
			} else bad++;
			continue;
		}
		if (!strcmp(w1,"clear") || !strcmp(w1,"clearlabel") || !strcmp(w1,"clearnpc")) {	// area clears
			int id=0,ex=0,sy=0,k2=0;
			if (!strcmp(w1,"clear") && sscanf(q,"%d %d %d %n",&id,&ex,&sy,&k2)>=3 && id>=1 && id<=MAXCLEAR && q[k2]) {
				clears[id].used=1; clears[id].exp=ex; clears[id].seyan=sy;
				strncpy(clears[id].zone,q+k2,sizeof(clears[id].zone)-1); clears[id].zone[sizeof(clears[id].zone)-1]=0;
			} else if (!strcmp(w1,"clearlabel") && sscanf(q,"%d %n",&id,&k2)>=1 && id>=1 && id<=MAXCLEAR) {
				strncpy(clears[id].label,q+k2,sizeof(clears[id].label)-1); clears[id].label[sizeof(clears[id].label)-1]=0;
			} else if (!strcmp(w1,"clearnpc") && sscanf(q,"%d %n",&id,&k2)>=1 && id>=1 && id<=MAXCLEAR) {
				char *e2,*p2=q+k2; long tv;
				for (;;) { tv=strtol(p2,&e2,10); if (e2==p2) break; p2=e2; if (tv>0 && tv<MAXTCHARS && clears[id].n<CLEARNPC) clears[id].t[clears[id].n++]=tv; }
			} else bad++;
			continue;
		}
		if (!strcmp(w1,"qrank")) {		// qrank <t> <lowest rank> <highest rank> (-1 = none): who may do the quest
			int a[3];
			if (sscanf(q,"%d %d %d",&a[0],&a[1],&a[2])==3 && a[0]>0 && a[0]<MAXTCHARS && a[1]>=-1 && a[1]<=23 && a[2]>=-1 && a[2]<=23) {
				qrew[a[0]].rmin1=a[1]+1; qrew[a[0]].rmax1=a[2]+1;
			} else bad++;
			continue;
		}
		if (!strcmp(w1,"qclass")) {		// qclass <t> <classes joined by |> <skill, -1 = as for everyone, 0 = none> <item, -1 = as for everyone, 0 = none>
			int t2,sk,itm; char cl[200];
			if (sscanf(q,"%d %199s %d %d",&t2,cl,&sk,&itm)==4 && t2>0 && t2<MAXTCHARS && class_mask(cl) && sk>=-1 && sk<50 && itm>=-1 && itm<MAXTITEM && nqcls<MAXQCLS) {
				struct qcls *c=&qcls[nqcls++]; c->t=t2; c->mask=class_mask(cl); c->skill=sk; c->item=itm;
			} else bad++;
			continue;
		}
		if (!strcmp(w1,"qstage")) {		// qstage <t> <times, 0 = every time after> <item> <exp> <gold>: the next reward step
			int a[5];
			if (sscanf(q,"%d %d %d %d %d",&a[0],&a[1],&a[2],&a[3],&a[4])==5 && a[0]>0 && a[0]<MAXTCHARS && qrew[a[0]].nst<QSTAGES && a[1]>=0) {
				struct qstage *st=&qrew[a[0]].st[qrew[a[0]].nst++];
				st->times=a[1]; st->item=a[2]>0 && a[2]<MAXTITEM ? a[2] : 0; st->exp=a[3]>0 ? a[3] : 0; st->gold=a[4]>0 ? a[4] : 0;
			} else bad++;
			continue;
		}
		if (!strcmp(w1,"order")) {
			if (sscanf(q,"%d %d",&n,&v)==2 && n>0 && n<MAXTCHARS && v>=-1 && v<=30000) qorder[n]=v; else bad++;
			continue;
		}
		if (!strcmp(w1,"step")) {
			if (sscanf(q,"%d %d %n",&n,&v,&x)>=2 && n>=1 && n<=QVARS && nstep<MAXSTEP) {
				step[nstep].n=n; step[nstep].v=v; step[nstep].str=pool_add(q+x); nstep++;
			} else bad++;
			continue;
		}
		if (!strcmp(w1,"chest")) {
			e=NULL; ch_=NULL;
			if (sscanf(q,"%d %d",&x,&y)==2 && nchest<MAXCHEST) { ch_=&chests[nchest++]; memset(ch_,0,sizeof(*ch_)); ch_->x=x; ch_->y=y; }
			else bad++;
			continue;
		}
		if (ch_) {
			char a1[64],a2[64],a3[16];
			if (!strcmp(w1,"end")) { ch_=NULL; continue; }
			if (!strcmp(w1,"refill")) { ch_->refill=atoi(q); continue; }
			if (!strcmp(w1,"once")) { ch_->once=1; continue; }
			if (!strcmp(w1,"first")) { ch_->first=atoi(q); continue; }
			if (!strcmp(w1,"reward") && ch_->nr<MAXREW) {
				struct reward *r=&ch_->r[ch_->nr];
				memset(r,0,sizeof(*r));
				if (sscanf(q,"item %d %d",&n,&v)==2) { r->type=RW_ITEM; r->a=n; r->w=v; }
				else if (sscanf(q,"gold %d %d",&n,&v)==2) { r->type=RW_GOLD; r->a=n; r->w=v; }
				else if (sscanf(q,"unique %d %d",&n,&v)==2) { r->type=RW_UNIQUE; r->a=n; r->w=v; }
				else if (sscanf(q,"nothing %d",&v)==1) { r->type=RW_NOTHING; r->w=v; }
				else if (!strncmp(q,"tier ",5)) {
					static char *tiers[]={"","magic","rare","epic"}, *metal[]={"bronze","steel","golden","emerald","crystal","titanium"};
					char *tok,*sp2,list[64];
					int lo=0,hi=0,k=sscanf(q,"tier %63s %63s %15s %d %d %d",a1,a2,a3,&lo,&hi,&v);
					r->type=RW_TIER; r->a=r->b=0;
					if (k==4) { v=lo; lo=hi=0; }				// the older form: tier metal piece weight
					else if (k!=6) { r->type=0; }
					strncpy(list,a1,63); list[63]=0;
					for (tok=strtok_r(list,",",&sp2); tok; tok=strtok_r(NULL,",",&sp2)) for (n=1; n<4; n++) if (!strcmp(tok,tiers[n])) r->a|=1<<n;
					strncpy(list,a2,63); list[63]=0;
					for (tok=strtok_r(list,",",&sp2); tok; tok=strtok_r(NULL,",",&sp2)) for (n=0; n<6; n++) if (!strcmp(tok,metal[n])) r->b|=1<<n;
					r->c=!strcmp(a3,"helm") ? 1 : !strcmp(a3,"armor") ? 2 : 0;
					r->d=lo; r->e=hi; r->w=v;
					if (!r->a) r->type=0;
				}
				if (r->type && r->w>0) ch_->nr++; else bad++;
				continue;
			}
			bad++; continue;
		}
		if (!strcmp(w1,"npc")) { temp=atoi(q); ax=ay=0; e=NULL; continue; }
		if (!strcmp(w1,"at")) { if (sscanf(q,"%d %d",&ax,&ay)!=2) ax=ay=0; temp=0; e=NULL; continue; }
		if (!strcmp(w1,"when")) {
			if ((!temp && !ax) || nent>=MAXENT) { bad++; e=NULL; continue; }
			e=&ent[nent++]; memset(e,0,sizeof(*e)); e->temp=temp;
			q+=strlen(w2); while (isspace((unsigned char)*q)) q++;
			if (!strcmp(w2,"use") || ax) { e->trig=T_USE; e->ux=ax; e->uy=ay; if (!ax) { bad++; nent--; e=NULL; } }
			else if (!strcmp(w2,"near")) e->trig=T_NEAR;
			else if (!strcmp(w2,"money")) { e->trig=T_MONEY; e->give=atoi(q); }
			else if (!strcmp(w2,"give")) { e->trig=T_GIVE; e->give=atoi(q); }
			else if (!strcmp(w2,"kill")) { e->trig=T_KILL; lower(q); e->words=pool_add(q); }
			else { e->trig=T_SAY; lower(q); e->words=pool_add(q); }
			continue;
		}
		if (!e) { if (strcmp(w1,"end")) bad++; continue; }
		if (!strcmp(w1,"end")) { e=NULL; continue; }
		if (!strcmp(w1,"if") && e->nc<MAXCOND) {
			struct tcond *c=&e->c[e->nc];
			if (sscanf(q,"quest %d %7s %d",&n,op,&v)==3 && n>=1 && n<=QVARS && parse_op(op)>=0) { c->type=C_QUEST; c->n=n; c->op=parse_op(op); c->v=v; e->nc++; }
			else if (sscanf(q,"has %d",&n)==1) { c->type=C_HAS; c->n=n; e->nc++; }
			else if (sscanf(q,"!has %d",&n)==1) { c->type=C_HASNOT; c->n=n; e->nc++; }
			else if (sscanf(q,"rank %7s %d",op,&v)==2 && parse_op(op)>=0) { c->type=C_RANK; c->op=parse_op(op); c->v=v; e->nc++; }
			else if (!strncmp(q,"area ",5)) { c->type=C_AREA; lower(q+5); c->n=pool_add(q+5); e->nc++; }
			else if (sscanf(q,"skill %d %7s %d",&n,op,&v)==3 && n>=0 && n<50 && parse_op(op)>=0) { c->type=C_SKILL; c->n=n; c->op=parse_op(op); c->v=v; e->nc++; }
			else if (sscanf(q,"gold %7s %d",op,&v)==2 && parse_op(op)>=0) { c->type=C_GOLD; c->op=parse_op(op); c->v=v; e->nc++; }
			else if (!strncmp(q,"class ",6) && class_mask(q+6)) { c->type=C_CLASS; c->op=0; c->n=(int)class_mask(q+6); e->nc++; }
			else if (!strncmp(q,"!class ",7) && class_mask(q+7)) { c->type=C_CLASS; c->op=1; c->n=(int)class_mask(q+7); e->nc++; }
			else bad++;
			continue;
		}
		if (e->ne>=MAXEFF) { bad++; continue; }
		{
			struct teff *t=&e->e[e->ne];
			memset(t,0,sizeof(*t));
			if (!strcmp(w1,"answer")) { t->type=E_ANSWER; t->str=pool_add(q); e->ne++; }
			else if (!strcmp(w1,"tell")) { t->type=E_TELL; t->str=pool_add(q); e->ne++; }
			else if (!strcmp(w1,"announce")) { t->type=E_ANNOUNCE; t->str=pool_add(q); e->ne++; }
			else if (!strcmp(w1,"set") && sscanf(q,"quest %d %d",&n,&v)==2 && n>=1 && n<=QVARS) { t->type=E_SETQ; t->a=n; t->b=v; e->ne++; }
			else if (!strcmp(w1,"add") && sscanf(q,"quest %d %d",&n,&v)==2 && n>=1 && n<=QVARS) { t->type=E_ADDQ; t->a=n; t->b=v; e->ne++; }
			else if (!strcmp(w1,"give") && sscanf(q,"item %d",&n)==1) { t->type=E_ITEM; t->a=n; e->ne++; }
			else if (!strcmp(w1,"give") && sscanf(q,"exp %d",&n)==1) { t->type=E_EXP; t->a=n; e->ne++; }
			else if (!strcmp(w1,"give") && sscanf(q,"gold %d",&n)==1) { t->type=E_GOLD; t->a=n; e->ne++; }
			else if (!strcmp(w1,"give") && sscanf(q,"luck %d",&n)==1) { t->type=E_LUCK; t->a=n; e->ne++; }
			else if (!strcmp(w1,"teach") && sscanf(q,"skill %d",&n)==1 && n>=0 && n<50) { t->type=E_SKILL; t->a=n; e->ne++; }
			else if (!strcmp(w1,"take") && sscanf(q,"item %d",&n)==1) { t->type=E_TAKE; t->a=n; e->ne++; }
			else if (!strcmp(w1,"take") && sscanf(q,"gold %d",&n)==1 && n>0) { t->type=E_TAKEGOLD; t->a=n; e->ne++; }
			else if (!strcmp(w1,"cast") && sscanf(q,"%15s %d",op,&v)==2) {
				for (n=0; spellname[n] && strcmp(spellname[n],op); n++) ;
				if (spellname[n] && v>0) { t->type=E_CAST; t->a=n; t->b=v; e->ne++; } else bad++;
			}
			else if (!strcmp(w1,"teleport") && sscanf(q,"%d %d",&x,&y)==2 && x>0 && y>0 && x<MAPX && y<MAPY) { t->type=E_TELEPORT; t->a=x; t->b=y; e->ne++; }
			else if (!strcmp(w1,"keep")) { t->type=E_KEEP; e->ne++; }
			else if (!strcmp(w1,"pass")) { t->type=E_PASS; e->ne++; }
			else bad++;
		}
	}
	fclose(f);
	for (n=0; n<nent; n++) if (ent[n].trig==T_NEAR && ent[n].temp>0 && ent[n].temp<MAXTCHARS) hasnear[ent[n].temp]=1;
	clear_hashes();
	xlog("NPC dialogue: %d entries, %d quest steps loaded from %s%s",nent,nstep,TALK_FILE,bad ? " (some lines not understood)" : "");
	return bad;
}

/* ---- quest variables */
static void qopen(void)
{
	char hdr[QHDR];
	long size;
	int n;

	qfd=open(QUEST_FILE,O_RDWR|O_CREAT,0600);
	if (qfd<0) { xlog("cannot open %s",QUEST_FILE); return; }
	size=lseek(qfd,0,SEEK_END);
	if (size>=QHDR && pread(qfd,hdr,QHDR,0)==QHDR && !memcmp(hdr,"MYV2QST2",8)) return;
	{	// empty, or the first version (31 quests, no header): write the new layout
		static struct qrow r;
		struct { int stamp; unsigned short v[OLDQVARS]; } o;
		int fd2;
		char tmp[256];
		sprintf(tmp,"%s.new",QUEST_FILE);
		fd2=open(tmp,O_RDWR|O_CREAT|O_TRUNC,0600);
		if (fd2<0) { xlog("cannot write %s",tmp); close(qfd); qfd=-1; return; }
		memset(hdr,0,QHDR); memcpy(hdr,"MYV2QST2",8); *(int*)(hdr+8)=QVARS; *(int*)(hdr+12)=sizeof(struct qrow);
		if (write(fd2,hdr,QHDR)!=QHDR) xlog("cannot write %s",tmp);
		for (n=0; (long)(n+1)*sizeof(o)<=size && n<MAXCHARS; n++) {
			if (pread(qfd,&o,sizeof(o),(off_t)n*sizeof(o))!=sizeof(o)) break;
			memset(&r,0,sizeof(r)); r.stamp=o.stamp; memcpy(r.v,o.v,sizeof(o.v));
			if (pwrite(fd2,&r,sizeof(r),QHDR+(off_t)n*sizeof(r))!=sizeof(r)) break;
		}
		close(qfd); close(fd2);
		rename(tmp,QUEST_FILE);
		if (size) xlog("%s converted to %d quests per character",QUEST_FILE,QVARS);
		qfd=open(QUEST_FILE,O_RDWR,0600);
	}
}

static struct qrow *qrow_get(int co,struct qrow *r)
{
	if (qfd==-2) qopen();
	memset(r,0,sizeof(*r));
	if (qfd>=0 && pread(qfd,r,sizeof(*r),QHDR+(off_t)co*sizeof(*r))!=sizeof(*r)) memset(r,0,sizeof(*r));
	if (r->stamp!=(int)ch[co].creation_date) { memset(r,0,sizeof(*r)); r->stamp=ch[co].creation_date; }
	return r;
}

static void qrow_put(int co,struct qrow *r)
{
	if (qfd>=0 && pwrite(qfd,r,sizeof(*r),QHDR+(off_t)co*sizeof(*r))!=sizeof(*r)) xlog("cannot write %s",QUEST_FILE);
}

int quest_get(int co,int n)
{
	struct qrow r;
	if (n<1 || n>QVARS || co<1 || co>=MAXCHARS) return 0;
	return qrow_get(co,&r)->v[n-1];
}

void quest_set(int co,int n,int v)
{
	struct qrow r;
	if (n<1 || n>QVARS || co<1 || co>=MAXCHARS) return;
	qrow_get(co,&r);
	r.v[n-1]=v<0 ? 0 : v>65535 ? 65535 : v;
	qrow_put(co,&r);
}

static char *step_text(int n,int v)
{
	int k,best=-1;
	for (k=0; k<nstep; k++) if (step[k].n==n && step[k].v<=v && (best<0 || step[k].v>step[best].v)) best=k;
	return best<0 ? NULL : pool+step[best].str;
}

/* #journal: the player's quests and how far they got */
void talk_journal(int cn)
{
	int n,v,cnt=0;
	char *s;
	struct qrow r;
	if (!talk_loaded) talk_load();
	qrow_get(cn,&r);
	do_char_log(cn,1,"Your quests:\n");
	for (n=1; n<=QVARS; n++) {
		if (!(v=r.v[n-1])) continue;
		cnt++;
		s=step_text(n,v);
		do_char_log(cn,1,"  %s%s\n",qname[n] ? pool+qname[n] : "Quest",qname[n] ? "" : " (unnamed)");
		if (s && *s) do_char_log(cn,2,"    %s\n",s);
		else do_char_log(cn,2,"    (step %d)\n",v);
	}
	if (!cnt) do_char_log(cn,1,"  None yet. People around the world may have work for you.\n");
}

/* ---- matching */
static int carried(int co,int temp)
{
	int n,in;
	for (n=0; n<40; n++) if ((in=ch[co].item[n]) && !(in&0x80000000) && in<MAXITEM && it[in].temp==temp) return in;
	if ((in=ch[co].citem) && !(in&0x80000000) && in<MAXITEM && it[in].temp==temp) return in;
	return 0;
}

static int word_match(char *alt,char *w)
{
	int l=strlen(alt);
	if (l>1 && alt[l-1]=='*') return !strncmp(w,alt,l-1);
	return !strcmp(w,alt);
}

static int said(char *words,char *text)
{
	char t[512],*w,*alt,grp[128],*sp,*sa;
	char tw[64][40];
	int n=0,i,ok;

	for (i=0; text[i] && i<511; i++) t[i]=isalnum((unsigned char)text[i]) ? tolower(text[i]) : ' ';
	t[i]=0;
	for (w=strtok_r(t," ",&sp); w && n<64; w=strtok_r(NULL," ",&sp)) { strncpy(tw[n],w,39); tw[n][39]=0; n++; }

	strncpy(t,words,511); t[511]=0;
	for (w=strtok_r(t," ",&sp); w; w=strtok_r(NULL," ",&sp)) {	// every group must be said
		strncpy(grp,w,127); grp[127]=0; ok=0;
		for (alt=strtok_r(grp,"|",&sa); alt && !ok; alt=strtok_r(NULL,"|",&sa))
			for (i=0; i<n && !ok; i++) if (word_match(alt,tw[i])) ok=1;
		if (!ok) return 0;
	}
	return 1;
}

/* the victim of a kill: by name (a whole name; a|b, Spider*) or #12,13 (template numbers) */
static int victim_match(char *spec,int co)
{
	char t[512],nm[64],*w,*sp;
	int i;
	if (spec[0]=='#') {
		strncpy(t,spec+1,511); t[511]=0;
		for (w=strtok_r(t,", #",&sp); w; w=strtok_r(NULL,", #",&sp)) if (atoi(w)==ch[co].temp) return 1;
		return 0;
	}
	for (i=0; ch[co].name[i] && i<63; i++) nm[i]=tolower((unsigned char)ch[co].name[i]);
	nm[i]=0;
	strncpy(t,spec,511); t[511]=0;
	for (w=strtok_r(t,"|",&sp); w; w=strtok_r(NULL,"|",&sp)) {
		while (isspace((unsigned char)*w)) w++;
		i=strlen(w); while (i>0 && isspace((unsigned char)w[i-1])) w[--i]=0;
		if (*w && word_match(w,nm)) return 1;
	}
	return 0;
}

static int conds_ok(struct tentry *e,int co,int x,int y)
{
	int n;
	char area[512],*s;
	for (n=0; n<e->nc; n++) {
		struct tcond *c=&e->c[n];
		switch (c->type) {
			case C_QUEST:  if (!cmp_op(quest_get(co,c->n),c->op,c->v)) return 0; break;
			case C_HAS:    if (!carried(co,c->n)) return 0; break;
			case C_HASNOT: if (carried(co,c->n)) return 0; break;
			case C_RANK:   if (!cmp_op(points2rank(ch[co].points_tot),c->op,c->v)) return 0; break;
			case C_SKILL:  if (!cmp_op(ch[co].skill[c->n][0],c->op,c->v)) return 0; break;
			case C_GOLD:   if (!cmp_op(ch[co].gold,c->op,c->v)) return 0; break;
			case C_CLASS:  if (((ch[co].kindred&(unsigned int)c->n)!=0)==(c->op!=0)) return 0; break;	// op 1: "is not"

			case C_AREA:
				strncpy(area,get_area_m(x,y,0),511); area[511]=0;
				for (s=area; *s; s++) *s=tolower((unsigned char)*s);
				if (!strstr(area,pool+c->n)) return 0;
				break;
		}
	}
	return 1;
}

static void (*talk_echo)(char *)=NULL;
void talk_set_echo(void (*f)(char *)) { talk_echo=f; }

/* %s = the player's name, {q3} = the value of quest 3 */
static void fill(char *buf,int size,char *s,int co)
{
	int i,o=0,n;
	for (i=0; s[i] && o<size-40; i++) {
		if (s[i]=='%' && s[i+1]=='s') { o+=snprintf(buf+o,size-o,"%s",ch[co].name); i++; }
		else if (s[i]=='{' && s[i+1]=='q' && isdigit((unsigned char)s[i+2]) && (n=atoi(s+i+2))>=1 && n<=QVARS && strchr(s+i,'}')) {
			o+=snprintf(buf+o,size-o,"%d",quest_get(co,n)); i=strchr(s+i,'}')-s;
		}
		else buf[o++]=s[i];
	}
	buf[o]=0;
}

static int run(struct tentry *e,int cn,int co,int given)
{
	int n,in,keep=0,pass=0;
	char buf[512];
	char *who=cn ? ch[cn].name : NULL;
	for (n=0; n<e->ne; n++) {
		struct teff *x=&e->e[n];
		switch (x->type) {
			case E_ANSWER:
				fill(buf,sizeof(buf),pool+x->str,co);
				if (cn) do_sayx(cn,"%s",buf); else do_char_log(co,1,"%s\n",buf);
				if (talk_echo) talk_echo(buf);
				break;
			case E_TELL:
				fill(buf,sizeof(buf),pool+x->str,co);
				do_char_log(co,1,"%s\n",buf);
				if (talk_echo) talk_echo(buf);
				break;
			case E_ANNOUNCE:
				fill(buf,sizeof(buf),pool+x->str,co);
				do_announce(co,0,"%s\n",buf);
				if (talk_echo) talk_echo(buf);
				break;
			case E_SETQ:   quest_set(co,x->a,x->b); break;
			case E_ADDQ:   quest_set(co,x->a,quest_get(co,x->a)+x->b); break;
			case E_ITEM:
				if (x->a>0 && x->a<MAXTITEM && it_temp[x->a].used && (in=god_create_item(x->a))) {
					if (god_give_char(in,co)) { if (who) do_char_log(co,1,"%s gives you %s.\n",who,it[in].reference); else do_char_log(co,1,"You receive %s.\n",it[in].reference); }
					else { it[in].used=USE_EMPTY; do_char_log(co,0,"Your backpack is full: there was no room for %s.\n",it_temp[x->a].reference); }
				}
				break;
			case E_EXP:    if (x->a>0) do_give_exp(co,x->a,0,-1); break;
			case E_GOLD:
				if (x->a>0) { ch[co].gold+=x->a; do_update_char(co); if (who) do_char_log(co,1,"%s gives you %dG %dS.\n",who,x->a/100,x->a%100); else do_char_log(co,1,"You receive %dG %dS.\n",x->a/100,x->a%100); }
				break;
			case E_LUCK:
				ch[co].luck+=x->a;
				do_char_log(co,1,x->a>=0 ? "You feel luckier.\n" : "You feel less lucky.\n");
				break;
			case E_SKILL:
				if (!ch[co].skill[x->a][0] && ch[co].skill[x->a][2]) {
					ch[co].skill[x->a][0]=1; do_update_char(co);
					do_char_log(co,0,"You learned %s!\n",skilltab[x->a].name);
				} else if (!ch[co].skill[x->a][2]) do_char_log(co,1,"(%s is not a skill your class can learn.)\n",skilltab[x->a].name);
				break;
			case E_TAKE:
				if ((in=carried(co,x->a))) { if (who) do_char_log(co,1,"You give %s to %s.\n",it[in].reference,who); else do_char_log(co,1,"%s is used up.\n",it[in].name); god_take_from_char(in,co); it[in].used=USE_EMPTY; }
				break;
			case E_TELEPORT:
				if (god_transfer_char(co,x->a,x->b)) do_char_log(co,1,"You are taken away...\n");
				break;
			case E_KEEP:   keep=1; break;
			case E_PASS:   pass=1; break;
			case E_TAKEGOLD:
				if (ch[co].gold>=x->a) {
					ch[co].gold-=x->a; if (cn) ch[cn].gold+=x->a; do_update_char(co);
					do_char_log(co,1,"You give %s %dG %dS.\n",who ? who : "away",x->a/100,x->a%100);
				}
				break;
			case E_CAST:
				in=cn ? cn : co;	// an NPC casts it; for a kill or an item, the player's own magic
				switch (x->a) {
					case 0: spell_bless(in,co,x->b); break;
					case 1: spell_protect(in,co,x->b); break;
					case 2: spell_enhance(in,co,x->b); break;
					case 3: spell_mshield(in,co,x->b); break;
					case 4: spell_light(in,co,x->b); break;
					case 5: spell_heal(in,co,x->b); break;
				}
				break;
		}
	}
	if (given && cn) {
		god_take_from_char(given,cn);
		if (keep) it[given].used=USE_EMPTY;
		else if (!god_give_char(given,co)) it[given].used=USE_EMPTY;
	}
	if (cn) ch[cn].data[92]=TICKS*60;	// stay awake a while
	return pass ? 0 : 1;
}

/* a player said something near the NPC: 1 = answered */
int talk_custom_say(int cn,int co,char *text)
{
	int n;
	if (!talk_loaded) talk_load();
	if (!nent || !(ch[co].flags&CF_PLAYER)) return 0;
	for (n=0; n<nent; n++) {
		if (ent[n].temp!=ch[cn].temp || ent[n].trig!=T_SAY) continue;
		if (!said(pool+ent[n].words,text) || !conds_ok(&ent[n],co,ch[co].x,ch[co].y)) continue;
		return run(&ent[n],cn,co,0);
	}
	return 0;
}

/* does this NPC have its own greeting lines? (then talk_near_due() decides when it greets, not the game's
 * memory of the last four players, which would keep it from greeting the same player again for a long time) */
int talk_has_near(int cn)
{
	if (!talk_loaded) talk_load();
	return ch[cn].temp>0 && ch[cn].temp<MAXTCHARS && hasnear[ch[cn].temp];
}

/* each player at most once a minute per NPC (and the NPC not more than once every 2 seconds) */
int talk_near_due(int cn,int co)
{
	static struct { int cn,co,tick; } seen[1024];
	static int last[MAXCHARS];
	int n,free=-1,oldest=0;
	if (cn<1 || cn>=MAXCHARS) return 0;
	if (globs->ticker-last[cn]<TICKS*2 && last[cn]) return 0;
	for (n=0; n<1024; n++) {
		if (seen[n].cn==cn && seen[n].co==co) {
			if (globs->ticker-seen[n].tick<TICKS*60) return 0;
			seen[n].tick=globs->ticker; last[cn]=globs->ticker; return 1;
		}
		if (!seen[n].cn && free<0) free=n;
		if (seen[n].tick<seen[oldest].tick) oldest=n;
	}
	n=free>=0 ? free : oldest;
	seen[n].cn=cn; seen[n].co=co; seen[n].tick=globs->ticker; last[cn]=globs->ticker;
	return 1;
}

/* a player came close to an NPC that greets players: 1 = a line took it (no normal greeting) */
int talk_custom_near(int cn,int co)
{
	int n;
	if (!talk_loaded) talk_load();
	if (!nent || !(ch[co].flags&CF_PLAYER)) return 0;
	for (n=0; n<nent; n++) {
		if (ent[n].temp!=ch[cn].temp || ent[n].trig!=T_NEAR || !conds_ok(&ent[n],co,ch[co].x,ch[co].y)) continue;
		return run(&ent[n],cn,co,0);
	}
	return 0;
}

/* a player gave the NPC money (already moved to the NPC): 1 = a line took it (the NPC keeps it) */
int talk_custom_money(int cn,int co,int money)
{
	int n;
	if (!talk_loaded) talk_load();
	if (!nent || !(ch[co].flags&CF_PLAYER) || money<=0) return 0;
	for (n=0; n<nent; n++) {
		if (ent[n].temp!=ch[cn].temp || ent[n].trig!=T_MONEY || money<ent[n].give || !conds_ok(&ent[n],co,ch[co].x,ch[co].y)) continue;
		run(&ent[n],cn,co,0);
		return 1;
	}
	return 0;
}

/* a player gave the NPC an item (already in the NPC's hands): 1 = handled */
int talk_custom_give(int cn,int co,int in)
{
	int n;
	if (!talk_loaded) talk_load();
	if (!nent || !(ch[co].flags&CF_PLAYER) || !IS_SANEITEM(in)) return 0;
	for (n=0; n<nent; n++) {
		if (ent[n].temp!=ch[cn].temp || ent[n].trig!=T_GIVE || ent[n].give!=it[in].temp) continue;
		if (!conds_ok(&ent[n],co,ch[co].x,ch[co].y)) continue;
		return run(&ent[n],cn,co,in);
	}
	return 0;
}

/* a player uses the item in on the map: 1 = a line took care of it (the item's own use doesn't happen) */
int talk_custom_use(int cn,int in)
{
	int n,x,y;
	if (!talk_loaded) talk_load();
	if (!nent || !(ch[cn].flags&CF_PLAYER) || !IS_SANEITEM(in) || it[in].carried) return 0;
	x=it[in].x; y=it[in].y;
	for (n=0; n<nent; n++) {
		if (ent[n].trig!=T_USE || ent[n].ux!=x || ent[n].uy!=y) continue;
		if (!conds_ok(&ent[n],cn,ch[cn].x,ch[cn].y)) continue;
		return run(&ent[n],0,cn,0);
	}
	return 0;
}

/* for the console: as if the player used the item at x,y */
int talk_test_use(int co,int x,int y)
{
	int in;
	if (x<1 || y<1 || x>=MAPX || y>=MAPY || !(in=map[x+y*MAPX].it)) return -1;
	return talk_custom_use(co,in);
}

/* ---- chests ---- */
static void chestlog_load(void)
{
	FILE *f;
	char line[128];
	int x,y,c,st,t,wh;
	chestlog_loaded=1;
	if (!(f=fopen(CHESTLOG,"r"))) return;
	while (fgets(line,sizeof(line),f)) {
		wh=0;
		if ((line[0]=='P' || line[0]=='F') && sscanf(line+1," %d %d %d %d",&x,&y,&c,&st)==4) {
			if (line[0]=='F') sscanf(line+1," %*d %*d %*d %*d %d",&wh);	// F x y cn stamp when name
			if (nopened>=maxopened) { maxopened=maxopened ? maxopened*2 : 1024; opened=realloc(opened,maxopened*sizeof(*opened)); }
			opened[nopened].x=x; opened[nopened].y=y; opened[nopened].cn=c; opened[nopened].stamp=st; opened[nopened].kind=line[0]; opened[nopened].when=wh; nopened++;
		} else if (sscanf(line,"U %d",&t)==1 && ngiven<512) given_unique[ngiven++]=t;
	}
	fclose(f);
}

static void chestlog_add(char *line)
{
	FILE *f=fopen(CHESTLOG,"a");
	if (f) { fputs(line,f); fclose(f); }
}

static int chest_opened_by(struct chest *c,int co,char kind)	// 0 = no, else the record's number + 1
{
	int n;
	for (n=0; n<nopened; n++) if (opened[n].kind==kind && opened[n].x==c->x && opened[n].y==c->y && opened[n].cn==co && opened[n].stamp==(int)ch[co].creation_date) return n+1;
	return 0;
}

static void chest_mark(struct chest *c,int cn,char kind)
{
	char buf[160];
	if (nopened>=maxopened) { maxopened=maxopened ? maxopened*2 : 1024; opened=realloc(opened,maxopened*sizeof(*opened)); }
	opened[nopened].x=c->x; opened[nopened].y=c->y; opened[nopened].cn=cn; opened[nopened].stamp=ch[cn].creation_date; opened[nopened].kind=kind; opened[nopened].when=(int)time(NULL); nopened++;
	if (kind=='F') sprintf(buf,"F %d %d %d %d %d %s\n",c->x,c->y,cn,(int)ch[cn].creation_date,(int)time(NULL),ch[cn].name);
	else sprintf(buf,"P %d %d %d %d %s\n",c->x,c->y,cn,(int)ch[cn].creation_date,ch[cn].name);
	chestlog_add(buf);
}

static int unique_given(int t)
{
	int n;
	for (n=0; n<ngiven; n++) if (given_unique[n]==t) return 1;
	return 0;
}

static int item_exists(int t)	// a copy of this template anywhere (like the game's check for Unique items)
{
	int n;
	for (n=1; n<MAXITEM; n++) if (it[n].used!=USE_EMPTY && it[n].temp==t) return 1;
	return 0;
}

static int reward_possible(struct reward *r)
{
	switch (r->type) {
		case RW_ITEM:   return r->a>0 && r->a<MAXTITEM && it_temp[r->a].used && !((it_temp[r->a].flags&IF_UNIQUE) && item_exists(r->a));
		case RW_UNIQUE: return r->a>0 && r->a<MAXTITEM && it_temp[r->a].used && !unique_given(r->a) &&
				       !((it_temp[r->a].flags&IF_UNIQUE) && item_exists(r->a));	// (a Unique item also: none may exist)
		case RW_GOLD: case RW_TIER: case RW_NOTHING: return 1;
	}
	return 0;
}

/* a player opens a MyV2 chest (driver 75): 1 = it opens */
int talk_chest_open(int cn,int in)
{
	struct chest *c=NULL;
	int n,tot=0,r,in2=0;
	char buf[160];

	if (!talk_loaded) talk_load();
	if (!chestlog_loaded) chestlog_load();
	if (!cn || !IS_SANEITEM(in) || it[in].carried) return 0;
	for (n=0; n<nchest; n++) if (chests[n].x==it[in].x && chests[n].y==it[in].y) { c=&chests[n]; break; }
	if (!c) {
		if (it[in].active) { do_char_log(cn,1,"It's open - and empty.\n"); return 0; }
		do_char_log(cn,1,"It's empty...\n"); return 1;
	}
	if (c->refill>0) it[in].duration=c->refill*TICKS;

	// the first time this player opens it: the special first reward (if it can be given) - also while the chest is
	// open (empty). A closed chest opens (and stays empty for its refill time); an open one keeps its timer.
	if (c->first>0 && c->first<MAXTITEM && it_temp[c->first].used && !chest_opened_by(c,cn,'F') &&
	    !((it_temp[c->first].flags&IF_UNIQUE) && item_exists(c->first))) {
		if (!(in2=god_create_item(c->first))) return 0;
		if (!god_give_char(in2,cn)) {
			do_char_log(cn,0,"Your backpack is full, so you can't take the %s.\n",it[in2].reference);
			it[in2].used=USE_EMPTY;
			return 0;
		}
		do_char_log(cn,1,"You got %s.\n",it[in2].reference);
		chlog(cn,"Got %s (first reward) from %s at %d,%d",it[in2].name,it[in].name,it[in].x,it[in].y);
		chest_mark(c,cn,'F');
		return it[in].active ? 0 : 1;
	}

	if (it[in].active) { do_char_log(cn,1,"It's open - and empty.\n"); return 0; }

	if (c->once && chest_opened_by(c,cn,'P')) { do_char_log(cn,1,"You already took what was in it for you.\n"); return 0; }

	for (n=0; n<c->nr; n++) if (reward_possible(&c->r[n])) tot+=c->r[n].w;
	if (!tot) { do_char_log(cn,1,"It's empty...\n"); return 1; }
	r=RANDOM(tot);
	for (n=0; n<c->nr; n++) { if (!reward_possible(&c->r[n])) continue; if (r<c->r[n].w) break; r-=c->r[n].w; }
	if (n>=c->nr) return 1;

	switch (c->r[n].type) {
		case RW_NOTHING: do_char_log(cn,1,"It's empty...\n"); break;
		case RW_GOLD:
			ch[cn].gold+=c->r[n].a; do_update_char(cn);
			do_char_log(cn,1,"You found %dG %dS.\n",c->r[n].a/100,c->r[n].a%100);
			chlog(cn,"Got %dG %dS from %s",c->r[n].a/100,c->r[n].a%100,it[in].name);
			break;
		case RW_ITEM: case RW_UNIQUE: case RW_TIER:
			if (c->r[n].type==RW_TIER) in2=tier_chest_reward(c->r[n].a,c->r[n].b,c->r[n].c,c->r[n].d,c->r[n].e);
			else in2=god_create_item(c->r[n].a);
			if (!in2) { do_char_log(cn,1,"It's empty...\n"); break; }
			if (!god_give_char(in2,cn)) {
				do_char_log(cn,0,"Your backpack is full, so you can't take the %s.\n",it[in2].reference);
				it[in2].used=USE_EMPTY;
				return 0;			// stays closed: they can come back
			}
			do_char_log(cn,1,"You got %s.\n",it[in2].reference);
			chlog(cn,"Got %s from %s at %d,%d",it[in2].name,it[in].name,it[in].x,it[in].y);
			if (c->r[n].type==RW_UNIQUE) {
				if (ngiven<512) given_unique[ngiven++]=c->r[n].a;
				sprintf(buf,"U %d %s got it at %d,%d\n",c->r[n].a,ch[cn].name,it[in].x,it[in].y); chestlog_add(buf);
				xlog("Unique chest reward: %s got %s (template %d) at %d,%d",ch[cn].name,it[in2].name,c->r[n].a,it[in].x,it[in].y);
			}
			break;
	}
	if (c->once) chest_mark(c,cn,'P');
	return 1;
}

/* the NPC co was killed by cn: the player behind the kill (a companion's master), and their group
 * members who can see them, each get the first kill entry that fits them */
static int talk_kill_one(int p,int co)
{
	int n,cnt=0;
	for (n=0; n<nent; n++) {
		if (ent[n].trig!=T_KILL || !victim_match(pool+ent[n].words,co)) continue;
		if (!conds_ok(&ent[n],p,ch[co].x,ch[co].y)) continue;
		run(&ent[n],0,p,0);
		cnt=1;
		break;
	}
	return cnt;
}

void talk_custom_kill(int cn,int co)
{
	int p=0,n,m;
	if (!talk_loaded) talk_load();
	if (!nent || !IS_SANECHAR(cn) || !IS_SANECHAR(co) || (ch[co].flags&CF_PLAYER)) return;
	if (ch[cn].flags&CF_PLAYER) p=cn;
	else if ((m=ch[cn].data[63])>0 && m<MAXCHARS && (ch[m].flags&CF_PLAYER)) p=m;	// a companion: its master
	if (!p) return;
	talk_kill_one(p,co);
	for (n=1; n<10; n++)
		if ((m=ch[p].data[n])>0 && m<MAXCHARS && m!=p && (ch[m].flags&CF_PLAYER) && ch[m].used==USE_ACTIVE && isgroup(m,p) && do_char_can_see(p,m))
			talk_kill_one(m,co);
}

/* for the console: as if player co killed an NPC of template t */
int talk_test_kill(int co,int t,int *found)
{
	int n;
	if (!talk_loaded) talk_load();
	*found=0;
	for (n=1; n<MAXCHARS; n++) if (ch[n].used==USE_ACTIVE && ch[n].temp==t && !(ch[n].flags&(CF_PLAYER|CF_BODY))) { *found=1; return talk_kill_one(co,n); }
	return 0;
}

int talk_entries(void) { if (!talk_loaded) talk_load(); return nent; }

// #quest: where a quest giver goes in the list (0 = not set: by its exp, -1 = left out)
int talk_quest_order(int t)
{
	if (!talk_loaded) talk_load();
	if (t<1 || t>=MAXTCHARS) return 0;
	return qorder[t];
}

/* ---- item quests: rewards, repeats (the editor's Quests page; "qreward" lines in npctalk.dat)
 * qreward <template> <limit> <first> <gold>, then qstage <template> <times> <item> <exp> <gold> lines
 *   limit: how often one character may do it (0 = forever); first: how many times the first reward
 *   (the template's item + exp, plus gold) is given (0 = always); then each step in turn for its times,
 *   the last step from then on (e.g. 10,000 exp, 7,500, 5,000, then only the potion).
 * Gold in silver (100 = 1G). How often each character did it: questcount.dat, a row per character. */
#define QCOUNT_FILE DATDIR"/questcount.dat"
#define QCMAX 64
struct qcrow { int stamp; struct { unsigned short t, n; } e[QCMAX]; };
static int qcfd=-2;

static void qcopen(void)
{
	char hdr[QHDR];
	qcfd=open(QCOUNT_FILE,O_RDWR|O_CREAT,0600);
	if (qcfd<0) { xlog("cannot open %s",QCOUNT_FILE); return; }
	if (pread(qcfd,hdr,QHDR,0)==QHDR && !memcmp(hdr,"MYV2QCN1",8)) return;
	memset(hdr,0,QHDR); memcpy(hdr,"MYV2QCN1",8); *(int*)(hdr+8)=QCMAX;
	if (pwrite(qcfd,hdr,QHDR,0)!=QHDR) xlog("cannot write %s",QCOUNT_FILE);
}

static void qcrow_get(int co,struct qcrow *r)
{
	if (qcfd==-2) qcopen();
	memset(r,0,sizeof(*r));
	if (qcfd>=0 && pread(qcfd,r,sizeof(*r),QHDR+(off_t)co*sizeof(*r))!=sizeof(*r)) memset(r,0,sizeof(*r));
	if (r->stamp!=(int)ch[co].creation_date) { memset(r,0,sizeof(*r)); r->stamp=ch[co].creation_date; }
}

int quest_count(int co,int t)		// how often character co did template t's item quest
{
	struct qcrow r;
	int n;
	if (co<1 || co>=MAXCHARS || t<1 || t>=MAXTCHARS) return 0;
	qcrow_get(co,&r);
	for (n=0; n<QCMAX; n++) if (r.e[n].t==t) return r.e[n].n;
	return 0;
}

static void quest_count_add(int co,int t)
{
	struct qcrow r;
	int n,k=-1;
	if (co<1 || co>=MAXCHARS || t<1 || t>=MAXTCHARS) return;
	qcrow_get(co,&r);
	for (n=0; n<QCMAX; n++) {
		if (r.e[n].t==t) { if (r.e[n].n<65535) r.e[n].n++; k=n; break; }
		if (!r.e[n].t && k<0) k=-2-n;		// the first free slot
	}
	if (k<-1) { n=-2-k; r.e[n].t=t; r.e[n].n=1; }
	else if (k<0) { xlog("questcount: no room for template %d (character %d)",t,co); return; }
	if (qcfd>=0 && pwrite(qcfd,&r,sizeof(r),QHDR+(off_t)co*sizeof(r))!=sizeof(r)) xlog("cannot write %s",QCOUNT_FILE);
}

/* class rewards of item quests: the skill template t teaches character co (as data[50]: 0 = none) */
int quest_teach(int t,int co)
{
	const struct qcls *c;
	if (!talk_loaded) talk_load();
	if (t<1 || t>=MAXTCHARS) return 0;
	if ((c=qcls_find(t,co)) && c->skill>=0) return c->skill;
	return ch_temp[t].data[50];
}

/* ... and the item: the class's item replaces the quest's own item (the first reward, and later steps that give the same) */
int quest_class_item(int t,int co,int item,int stp)
{
	const struct qcls *c;
	if (!talk_loaded) talk_load();
	if (t<1 || t>=MAXTCHARS) return item;
	if (!(c=qcls_find(t,co)) || c->item<0) return item;
	if (stp==0 || item==ch_temp[t].data[66]) return c->item;
	return item;
}

int quest_has_class(int t)	// does template t's quest have class rewards?
{
	int n;
	if (!talk_loaded) talk_load();
	for (n=0; n<nqcls; n++) if (qcls[n].t==t) return 1;
	return 0;
}

/* what template t gives character co now: item, exp, gold (silver); left: times left (-1 = no limit).
 * later: 1 when this is the "after the first times" reward. Returns 1 if it gives anything. */
int quest_reward_now(int t,int co,int *item,int *exp,int *gold,int *left,int *later)
{
	struct qrew *r;
	int cnt;
	if (!talk_loaded) talk_load();
	*item=*exp=*gold=0; *left=-1; *later=0;
	if (t<1 || t>=MAXTCHARS) return 0;
	r=&qrew[t];
	cnt=(r->limit || r->first) && co ? quest_count(co,t) : 0;
	if (r->limit) *left=cnt>=r->limit ? 0 : r->limit-cnt;
	quest_reward_at(t,cnt,item,exp,gold,later);
	*item=quest_class_item(t,co,*item,*later);
	if (*item<0 || *item>=MAXTITEM) *item=0;
	return *item || *exp>0 || *gold>0;
}

int quest_reward_limit(int t)
{
	if (!talk_loaded) talk_load();
	return t>0 && t<MAXTCHARS ? qrew[t].limit : 0;
}

/* the reward of template t's item quest at turn-in number cnt+1 (cnt = times done before);
 * step: 0 = the first reward, 1.. = the steps after it */
void quest_reward_at(int t,int cnt,int *item,int *exp,int *gold,int *stp)
{
	struct qrew *r=&qrew[t];
	int k,c;
	*stp=0;
	if (!r->nst || !r->first || cnt<r->first) { *item=ch_temp[t].data[66]; *exp=ch_temp[t].data[51]; *gold=r->gold1; return; }
	c=cnt-r->first;
	for (k=0; k<r->nst-1; k++) {
		if (!r->st[k].times || c<r->st[k].times) break;
		c-=r->st[k].times;
	}
	*item=r->st[k].item; *exp=r->st[k].exp; *gold=r->st[k].gold; *stp=k+1;
}

int quest_reward_steps(int t)		// how many different rewards (1 = always the same)
{
	if (!talk_loaded) talk_load();
	if (t<1 || t>=MAXTCHARS || !qrew[t].first) return 1;
	return 1+qrew[t].nst;
}

int quest_gold_first(int t)		// a skill teacher's gold (given with the skill)
{
	if (!talk_loaded) talk_load();
	return t>0 && t<MAXTCHARS ? qrew[t].gold1 : 0;
}

/* the NPC cn got the item in it wants from player co, and teaches no skill: an item trade.
 * Returns 1 if it handled it (rewards given), 0 = nothing to give (as before: the NPC just keeps it). */
int talk_quest_trade(int cn,int co,int in)
{
	int t=ch[cn].temp,item,exp,gold,left,later,ni;

	if (!IS_PLAYER(co) || !quest_reward_now(t,co,&item,&exp,&gold,&left,&later)) return 0;
	if (left==0) return 0;
	if (qrew[t].limit || qrew[t].first) quest_count_add(co,t);
	god_take_from_char(in,cn);
	it[in].used=USE_EMPTY;
	if (item) {
		do_sayx(cn,"Here is your %s in exchange.",it_temp[item].reference);
		ni=god_create_item(item);
		if (ni) god_give_char(ni,co);
	}
	if (exp>0) do_give_exp(co,exp,0,-1);
	if (gold>0) { ch[co].gold+=gold; do_update_char(co); do_char_log(co,1,"%s gives you %dG %dS.\n",ch[cn].reference,gold/100,gold%100); }
	if (left==1) do_sayx(cn,"That was the last one I needed, %s. Thank you!",ch[co].name);
	return 1;
}

int talk_quest_maxed(int cn,int co)	// this player has done the item trade as often as it can be done
{
	int t=ch[cn].temp;
	if (!talk_loaded) talk_load();
	if (t<1 || t>=MAXTCHARS || !qrew[t].limit || !IS_PLAYER(co)) return 0;
	return quest_count(co,t)>=qrew[t].limit;
}

/* the ranks that may do template t's quest: 0 = this character may, -1 = rank too low, 1 = too high.
 * lo / hi: the lowest / highest rank (-1 = none) */
int quest_rank_check(int t,int co,int *lo,int *hi)
{
	int r;
	if (!talk_loaded) talk_load();
	*lo=*hi=-1;
	if (t<1 || t>=MAXTCHARS) return 0;
	*lo=qrew[t].rmin1-1; *hi=qrew[t].rmax1-1;
	if (co<1 || co>=MAXCHARS) return 0;
	r=points2rank(ch[co].points_tot);
	if (*lo>=0 && r<*lo) return -1;
	if (*hi>=0 && r>*hi) return 1;
	return 0;
}
struct clrow { int stamp; unsigned long long mask[MAXCLEAR+1]; unsigned char fl[MAXCLEAR+1]; unsigned short hash[MAXCLEAR+1]; };
#define CLR_DONE	1	// done (before Seyan'Du)
#define CLR_DONE2	2	// done as Seyan'Du
#define CLR_RUN2	4	// the progress now is the Seyan'Du run
static int clfd=-2;

static void clear_hashes(void)
{
	int a,k; unsigned h;
	for (a=1; a<=MAXCLEAR; a++) {
		for (h=5381,k=0; k<clears[a].n; k++) h=h*33+clears[a].t[k];
		clears[a].hash=(unsigned short)(h ? h : 1);
	}
}

static void clopen(void)
{
	char hdr[QHDR];
	clfd=open(CLEAR_FILE,O_RDWR|O_CREAT,0600);
	if (clfd<0) { xlog("cannot open %s",CLEAR_FILE); return; }
	if (pread(clfd,hdr,QHDR,0)==QHDR && !memcmp(hdr,"MYV2CLR1",8)) return;
	memset(hdr,0,QHDR); memcpy(hdr,"MYV2CLR1",8); *(int*)(hdr+8)=MAXCLEAR;
	if (pwrite(clfd,hdr,QHDR,0)!=QHDR) xlog("cannot write %s",CLEAR_FILE);
}

static void clrow_get(int co,struct clrow *r)
{
	if (clfd==-2) clopen();
	memset(r,0,sizeof(*r));
	if (clfd>=0 && pread(clfd,r,sizeof(*r),QHDR+(off_t)co*sizeof(*r))!=sizeof(*r)) memset(r,0,sizeof(*r));
	if (r->stamp!=(int)ch[co].creation_date) { memset(r,0,sizeof(*r)); r->stamp=ch[co].creation_date; }
}

static void clrow_put(int co,struct clrow *r)
{
	if (clfd>=0 && pwrite(clfd,r,sizeof(*r),QHDR+(off_t)co*sizeof(*r))!=sizeof(*r)) xlog("cannot write %s",CLEAR_FILE);
}

static int popcount64(unsigned long long m) { int c=0; while (m) { m&=m-1; c++; } return c; }

/* bring a row up to date for area a: a changed NPC list starts the progress again; a Seyan'Du who did it before
 * (and the area allows it) starts a second run. Returns 0 if this character can't get it (done). */
static int clear_ready(int co,int a,struct clrow *r)
{
	int seyan=(ch[co].kindred&KIN_SEYAN_DU)!=0;
	if (r->hash[a]!=clears[a].hash) { r->hash[a]=clears[a].hash; r->mask[a]=0; }
	if (r->fl[a]&CLR_DONE2) return 0;
	if (r->fl[a]&CLR_DONE) {
		if (!seyan || !clears[a].seyan) return 0;
		if (!(r->fl[a]&CLR_RUN2)) { r->fl[a]|=CLR_RUN2; r->mask[a]=0; }
	}
	return 1;
}

static void clear_credit(int p,int a,int k)
{
	struct clrow r;
	int cnt;
	if (!zone_has(clears[a].zone,ch[p].x,ch[p].y)) return;	// only while standing in the area
	clrow_get(p,&r);
	if (!clear_ready(p,a,&r)) { clrow_put(p,&r); return; }
	if (r.mask[a]&(1ULL<<k)) return;			// this one counted already
	r.mask[a]|=1ULL<<k;
	cnt=popcount64(r.mask[a]);
	do_char_log(p,2,"%d of %d %s in this area.\n",cnt,clears[a].n,clears[a].label[0] ? clears[a].label : "enemies");
	if (cnt>=clears[a].n) {
		r.fl[a]|=(r.fl[a]&CLR_RUN2) ? CLR_DONE2 : CLR_DONE;
		do_char_log(p,2,"You cleared %s!\n",clears[a].zone);
		if (clears[a].exp>0) do_give_exp(p,clears[a].exp,0,-1);
		chlog(p,"Cleared area %d (%s)%s, %d exp",a,clears[a].zone,(r.fl[a]&CLR_RUN2) ? " as Seyan'Du" : "",clears[a].exp);
	}
	clrow_put(p,&r);
}

/* the NPC co was killed by cn: every area clear that lists its template */
void clear_kill(int cn,int co)
{
	int p=0,a,k,n,m;
	if (!talk_loaded) talk_load();
	if (!IS_SANECHAR(cn) || !IS_SANECHAR(co) || (ch[co].flags&CF_PLAYER)) return;
	if (ch[cn].flags&CF_PLAYER) p=cn;
	else if ((m=ch[cn].data[63])>0 && m<MAXCHARS && (ch[m].flags&CF_PLAYER)) p=m;	// a companion: its master
	if (!p) return;
	for (a=1; a<=MAXCLEAR; a++) {
		if (!clears[a].used) continue;
		for (k=0; k<clears[a].n; k++) if (clears[a].t[k]==ch[co].temp) break;
		if (k==clears[a].n) continue;
		clear_credit(p,a,k);
		for (n=1; n<10; n++)
			if ((m=ch[p].data[n])>0 && m<MAXCHARS && m!=p && (ch[m].flags&CF_PLAYER) && ch[m].used==USE_ACTIVE && isgroup(m,p))
				clear_credit(m,a,k);
	}
}

/* #areas: every area clear and how far this character is */
void do_areas(int cn)
{
	struct clrow r;
	int a,shown=0,cnt,can;
	if (!talk_loaded) talk_load();
	clrow_get(cn,&r);
	for (a=1; a<=MAXCLEAR; a++) {
		if (!clears[a].used) continue;
		if (!shown) do_char_log(cn,1,"Areas to clear:\n");
		shown++;
		can=clear_ready(cn,a,&r);
		cnt=popcount64(r.mask[a]);
		if (!can) do_char_log(cn,3,"  %-24.24s cleared\n",clears[a].zone);
		else if (r.fl[a]&CLR_RUN2) do_char_log(cn,1,"  %-24.24s %d of %d %s (again as Seyan'Du)\n",clears[a].zone,cnt,clears[a].n,clears[a].label[0] ? clears[a].label : "enemies");
		else do_char_log(cn,1,"  %-24.24s %d of %d %s\n",clears[a].zone,cnt,clears[a].n,clears[a].label[0] ? clears[a].label : "enemies");
	}
	if (!shown) do_char_log(cn,1,"There are no areas to clear yet.\n");
}

/* console: as if player co killed the NPC of template t (it must be in the world) */
int clear_test(int co,int t)
{
	int n;
	if (!talk_loaded) talk_load();
	for (n=1; n<MAXCHARS; n++) if (ch[n].used==USE_ACTIVE && ch[n].temp==t && !(ch[n].flags&(CF_PLAYER|CF_BODY))) { clear_kill(co,n); return 1; }
	return 0;
}
