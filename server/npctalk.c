/*************************************************************************
 MyV2: custom NPC dialogue and quest steps (written by the MyV2 Editor)

 .dat/npctalk.dat (text, one command per line, # = comment):
   quest <n> <name>               a quest variable 1-31 and its name (for the editor)
   npc <template> [comment]       the lines after this belong to this NPC template
   when say <words...>            a player says something: every word must be there,
                                  a|b = either, ring* = ring, rings, ...
   when give <item template>      a player hands it this item
   if quest <n> <op> <v>          op: = != < > <= >=
   if has <item template>         the player carries one   (if !has: does not)
   if rank <op> <v>
   answer <text>                  said aloud (%s = the player's name); several lines are said in turn
   set quest <n> <v> | add quest <n> <v>
   give item <t> | give exp <n> | give gold <silver>
   take item <t>                  takes one from the player's backpack
   keep                           (when give) the NPC keeps the item; otherwise it hands it back
   end
 The first entry of the NPC whose trigger and conditions match is used.

 .dat/quest.dat: the quest variables of every character (31 per character), kept
 with the character's creation date so a new character in an old slot starts clean.
**************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <unistd.h>
#include <fcntl.h>
#include "server.h"

#define TALK_FILE DATDIR"/npctalk.dat"
#define QUEST_FILE DATDIR"/quest.dat"
#define QVARS 31
#define MAXENT 3000
#define MAXCOND 8
#define MAXEFF 16
#define POOL (512*1024)

enum { C_QUEST=1, C_HAS, C_HASNOT, C_RANK };
enum { E_ANSWER=1, E_SETQ, E_ADDQ, E_ITEM, E_EXP, E_GOLD, E_TAKE, E_KEEP };
enum { OP_EQ, OP_NE, OP_LT, OP_GT, OP_LE, OP_GE };

struct tcond { char type, op; int n, v; };
struct teff { char type; int a, b; int str; };
struct tentry {
	int temp;
	int give;		// item template for "when give", 0 = "when say"
	int words;		// pool offset of the words
	struct tcond c[MAXCOND]; int nc;
	struct teff e[MAXEFF]; int ne;
};
struct qrow { int stamp; unsigned short v[QVARS]; };

static struct tentry ent[MAXENT];
static int nent=0, talk_loaded=0;
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

int talk_load(void)
{
	FILE *f;
	char line[1024],w1[64],w2[64],op[8],*p,*q;
	int temp=0,n,v,ln=0,bad=0;
	struct tentry *e=NULL;

	nent=0; plen=1; pool[0]=0; talk_loaded=1;
	f=fopen(TALK_FILE,"r");
	if (!f) return 0;
	while (fgets(line,sizeof(line),f)) {
		ln++;
		line[strcspn(line,"\r\n")]=0;
		for (p=line; isspace(*p); p++) ;
		if (!*p || *p=='#') continue;
		w1[0]=w2[0]=0;
		sscanf(p,"%63s %63s",w1,w2);
		q=p+strlen(w1); while (isspace(*q)) q++;		// the rest after the first word
		if (!strcmp(w1,"quest")) continue;
		if (!strcmp(w1,"npc")) { temp=atoi(q); e=NULL; continue; }
		if (!strcmp(w1,"when")) {
			if (!temp || nent>=MAXENT) { bad++; e=NULL; continue; }
			e=&ent[nent++]; memset(e,0,sizeof(*e)); e->temp=temp;
			q+=strlen(w2); while (isspace(*q)) q++;
			if (!strcmp(w2,"give")) e->give=atoi(q);
			else { for (char *s=q; *s; s++) *s=tolower(*s); e->words=pool_add(q); }
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
			else bad++;
			continue;
		}
		if (e->ne>=MAXEFF) { bad++; continue; }
		{
			struct teff *x=&e->e[e->ne];
			memset(x,0,sizeof(*x));
			if (!strcmp(w1,"answer")) { x->type=E_ANSWER; x->str=pool_add(q); e->ne++; }
			else if (!strcmp(w1,"set") && sscanf(q,"quest %d %d",&n,&v)==2 && n>=1 && n<=QVARS) { x->type=E_SETQ; x->a=n; x->b=v; e->ne++; }
			else if (!strcmp(w1,"add") && sscanf(q,"quest %d %d",&n,&v)==2 && n>=1 && n<=QVARS) { x->type=E_ADDQ; x->a=n; x->b=v; e->ne++; }
			else if (!strcmp(w1,"give") && sscanf(q,"item %d",&n)==1) { x->type=E_ITEM; x->a=n; e->ne++; }
			else if (!strcmp(w1,"give") && sscanf(q,"exp %d",&n)==1) { x->type=E_EXP; x->a=n; e->ne++; }
			else if (!strcmp(w1,"give") && sscanf(q,"gold %d",&n)==1) { x->type=E_GOLD; x->a=n; e->ne++; }
			else if (!strcmp(w1,"take") && sscanf(q,"item %d",&n)==1) { x->type=E_TAKE; x->a=n; e->ne++; }
			else if (!strcmp(w1,"keep")) { x->type=E_KEEP; e->ne++; }
			else bad++;
		}
	}
	fclose(f);
	xlog("NPC dialogue: %d entries loaded from %s%s",nent,TALK_FILE,bad ? " (some lines not understood)" : "");
	return bad;
}

/* ---- quest variables */
static struct qrow *qrow_get(int co,struct qrow *r)
{
	if (qfd==-2) {
		qfd=open(QUEST_FILE,O_RDWR|O_CREAT,0600);
		if (qfd<0) xlog("cannot open %s",QUEST_FILE);
	}
	memset(r,0,sizeof(*r));
	if (qfd>=0 && pread(qfd,r,sizeof(*r),(off_t)co*sizeof(*r))!=sizeof(*r)) memset(r,0,sizeof(*r));
	if (r->stamp!=(int)ch[co].creation_date) { memset(r,0,sizeof(*r)); r->stamp=ch[co].creation_date; }
	return r;
}

static void qrow_put(int co,struct qrow *r)
{
	if (qfd>=0 && pwrite(qfd,r,sizeof(*r),(off_t)co*sizeof(*r))!=sizeof(*r)) xlog("cannot write %s",QUEST_FILE);
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

/* ---- matching */
static int carried(int co,int temp)
{
	int n,in;
	for (n=0; n<40; n++) if ((in=ch[co].item[n]) && !(in&0x80000000) && in<MAXITEM && it[in].temp==temp) return in;
	if ((in=ch[co].citem) && !(in&0x80000000) && in<MAXITEM && it[in].temp==temp) return in;
	return 0;
}

static int said(char *words,char *text)
{
	char t[512],*w,*alt,grp[128],*sp,*sa;
	char tw[64][40];
	int n=0,i,ok,l;

	for (i=0; text[i] && i<511; i++) t[i]=isalnum((unsigned char)text[i]) ? tolower(text[i]) : ' ';
	t[i]=0;
	for (w=strtok_r(t," ",&sp); w && n<64; w=strtok_r(NULL," ",&sp)) { strncpy(tw[n],w,39); tw[n][39]=0; n++; }

	strncpy(t,words,511); t[511]=0;
	for (w=strtok_r(t," ",&sp); w; w=strtok_r(NULL," ",&sp)) {	// every group must be said
		strncpy(grp,w,127); grp[127]=0; ok=0;
		for (alt=strtok_r(grp,"|",&sa); alt && !ok; alt=strtok_r(NULL,"|",&sa)) {
			l=strlen(alt);
			for (i=0; i<n && !ok; i++) {
				if (l>1 && alt[l-1]=='*') { if (!strncmp(tw[i],alt,l-1)) ok=1; }
				else if (!strcmp(tw[i],alt)) ok=1;
			}
		}
		if (!ok) return 0;
	}
	return 1;
}

static int conds_ok(struct tentry *e,int co)
{
	int n;
	for (n=0; n<e->nc; n++) {
		struct tcond *c=&e->c[n];
		switch (c->type) {
			case C_QUEST:  if (!cmp_op(quest_get(co,c->n),c->op,c->v)) return 0; break;
			case C_HAS:    if (!carried(co,c->n)) return 0; break;
			case C_HASNOT: if (carried(co,c->n)) return 0; break;
			case C_RANK:   if (!cmp_op(points2rank(ch[co].points_tot),c->op,c->v)) return 0; break;
		}
	}
	return 1;
}

static void (*talk_echo)(char *)=NULL;
void talk_set_echo(void (*f)(char *)) { talk_echo=f; }

static void say_line(int cn,int co,char *s)
{
	char buf[512];
	int i,o=0;
	for (i=0; s[i] && o<480; i++) {
		if (s[i]=='%' && s[i+1]=='s') { o+=snprintf(buf+o,sizeof(buf)-o,"%s",ch[co].name); i++; }
		else buf[o++]=s[i];
	}
	buf[o]=0;
	do_sayx(cn,"%s",buf);
	if (talk_echo) talk_echo(buf);
}

static int run(struct tentry *e,int cn,int co,int given)
{
	int n,in,keep=0;
	for (n=0; n<e->ne; n++) {
		struct teff *x=&e->e[n];
		switch (x->type) {
			case E_ANSWER: say_line(cn,co,pool+x->str); break;
			case E_SETQ:   quest_set(co,x->a,x->b); break;
			case E_ADDQ:   quest_set(co,x->a,quest_get(co,x->a)+x->b); break;
			case E_ITEM:
				if (x->a>0 && x->a<MAXTITEM && it_temp[x->a].used && (in=god_create_item(x->a))) {
					if (god_give_char(in,co)) do_char_log(co,1,"%s gives you %s.\n",ch[cn].name,it[in].reference);
					else { it[in].used=USE_EMPTY; do_char_log(co,0,"Your backpack is full: %s could not give you %s.\n",ch[cn].name,it_temp[x->a].reference); }
				}
				break;
			case E_EXP:    if (x->a>0) do_give_exp(co,x->a,0,-1); break;
			case E_GOLD:
				if (x->a>0) { ch[co].gold+=x->a; do_update_char(co); do_char_log(co,1,"%s gives you %dG %dS.\n",ch[cn].name,x->a/100,x->a%100); }
				break;
			case E_TAKE:
				if ((in=carried(co,x->a))) { god_take_from_char(in,co); it[in].used=USE_EMPTY; do_char_log(co,1,"You give %s to %s.\n",it[in].reference,ch[cn].name); }
				break;
			case E_KEEP:   keep=1; break;
		}
	}
	if (given) {
		god_take_from_char(given,cn);
		if (keep) it[given].used=USE_EMPTY;
		else if (!god_give_char(given,co)) it[given].used=USE_EMPTY;
	}
	ch[cn].data[92]=TICKS*60;	// stay awake a while
	return 1;
}

/* a player said something near the NPC: 1 = answered */
int talk_custom_say(int cn,int co,char *text)
{
	int n;
	if (!talk_loaded) talk_load();
	if (!nent || !(ch[co].flags&CF_PLAYER)) return 0;
	for (n=0; n<nent; n++) {
		if (ent[n].temp!=ch[cn].temp || ent[n].give) continue;
		if (!said(pool+ent[n].words,text) || !conds_ok(&ent[n],co)) continue;
		return run(&ent[n],cn,co,0);
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
		if (ent[n].temp!=ch[cn].temp || ent[n].give!=it[in].temp) continue;
		if (!conds_ok(&ent[n],co)) continue;
		return run(&ent[n],cn,co,in);
	}
	return 0;
}

int talk_entries(void) { if (!talk_loaded) talk_load(); return nent; }
