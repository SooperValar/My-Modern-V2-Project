/*************************************************************************
 MyV2: custom NPC dialogue, kill tracking and quest steps (written by the MyV2 Editor)

 .dat/npctalk.dat (text, one command per line, # = comment):
   quest <n> <name>               quest 1-31 and its name (the player's #journal shows it)
   step <n> <value> <text>        journal text for quest n at that step ("Bring a Potion of Life to the Captain.")
   npc <template> [comment]       the lines after this belong to this NPC (the quest giver)
   when say <words...>            a player says something near it: every word must be there,
                                  a|b = either, ring* = ring, rings, ...
   when give <item template>      a player hands it this item
   when kill <name>|#<t>,<t>...   a player (or their companion, or someone in their group nearby)
                                  kills an NPC with this name (Spider*, a|b) or these template numbers
   if quest <n> <op> <v>          op: = != < > <= >=
   if has <item template>         the player carries one   (if !has: does not)
   if rank <op> <v>
   if area <text>                 where it happens (the player; for kills: the victim) is in an
                                  area whose name contains this
   answer <text>                  the NPC says it aloud (%s = the player's name, {q2} = quest 2's value)
   tell <text>                    only the player sees it
   announce <text>                everyone online sees it
   set quest <n> <v> | add quest <n> <v>
   give item <t> | give exp <n> | give gold <silver> | give luck <n>
   teach skill <nr>               the player learns the skill (if they don't have it)
   take item <t>                  takes one from the player's backpack
   teleport <x> <y>
   keep                           (when give) the NPC keeps the item; otherwise it hands it back
   end
 For a player, the first entry whose trigger and conditions match is used.

 .dat/quest.dat: the quest steps of every character (31 per character), kept with the
 character's creation date so a new character in an old slot starts clean.
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
#define MAXSTEP 1000
#define MAXCOND 8
#define MAXEFF 16
#define POOL (768*1024)

enum { C_QUEST=1, C_HAS, C_HASNOT, C_RANK, C_AREA };
enum { E_ANSWER=1, E_SETQ, E_ADDQ, E_ITEM, E_EXP, E_GOLD, E_TAKE, E_KEEP, E_TELL, E_ANNOUNCE, E_LUCK, E_SKILL, E_TELEPORT };
enum { OP_EQ, OP_NE, OP_LT, OP_GT, OP_LE, OP_GE };
enum { T_SAY, T_GIVE, T_KILL };

struct tcond { char type, op; int n, v; };
struct teff { char type; int a, b; int str; };
struct tentry {
	int temp;		// the NPC it belongs to
	char trig;
	int give;		// item template for "when give"
	int words;		// pool offset: the words (say) or the victim (kill)
	struct tcond c[MAXCOND]; int nc;
	struct teff e[MAXEFF]; int ne;
};
struct tstep { char n; unsigned short v; int str; };
struct qrow { int stamp; unsigned short v[QVARS]; };

static struct tentry ent[MAXENT];
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
	char line[1024],w1[64],w2[64],op[8],*p,*q;
	int temp=0,n,v,x,y,ln=0,bad=0;
	struct tentry *e=NULL;

	nent=nstep=0; plen=1; pool[0]=0; talk_loaded=1;
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
		if (!strcmp(w1,"step")) {
			if (sscanf(q,"%d %d %n",&n,&v,&x)>=2 && n>=1 && n<=QVARS && nstep<MAXSTEP) {
				step[nstep].n=n; step[nstep].v=v; step[nstep].str=pool_add(q+x); nstep++;
			} else bad++;
			continue;
		}
		if (!strcmp(w1,"npc")) { temp=atoi(q); e=NULL; continue; }
		if (!strcmp(w1,"when")) {
			if (!temp || nent>=MAXENT) { bad++; e=NULL; continue; }
			e=&ent[nent++]; memset(e,0,sizeof(*e)); e->temp=temp;
			q+=strlen(w2); while (isspace((unsigned char)*q)) q++;
			if (!strcmp(w2,"give")) { e->trig=T_GIVE; e->give=atoi(q); }
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
			else if (!strcmp(w1,"teleport") && sscanf(q,"%d %d",&x,&y)==2 && x>0 && y>0 && x<MAPX && y<MAPY) { t->type=E_TELEPORT; t->a=x; t->b=y; e->ne++; }
			else if (!strcmp(w1,"keep")) { t->type=E_KEEP; e->ne++; }
			else bad++;
		}
	}
	fclose(f);
	xlog("NPC dialogue: %d entries, %d quest steps loaded from %s%s",nent,nstep,TALK_FILE,bad ? " (some lines not understood)" : "");
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
	if (!talk_loaded) talk_load();
	do_char_log(cn,1,"Your quests:\n");
	for (n=1; n<=QVARS; n++) {
		if (!(v=quest_get(cn,n))) continue;
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
	int n,in,keep=0;
	char buf[512];
	char *who=cn ? ch[cn].name : "The gods";
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
					if (god_give_char(in,co)) do_char_log(co,1,"%s gives you %s.\n",who,it[in].reference);
					else { it[in].used=USE_EMPTY; do_char_log(co,0,"Your backpack is full: %s could not give you %s.\n",who,it_temp[x->a].reference); }
				}
				break;
			case E_EXP:    if (x->a>0) do_give_exp(co,x->a,0,-1); break;
			case E_GOLD:
				if (x->a>0) { ch[co].gold+=x->a; do_update_char(co); do_char_log(co,1,"%s gives you %dG %dS.\n",who,x->a/100,x->a%100); }
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
				if ((in=carried(co,x->a))) { do_char_log(co,1,"You give %s to %s.\n",it[in].reference,who); god_take_from_char(in,co); it[in].used=USE_EMPTY; }
				break;
			case E_TELEPORT:
				if (god_transfer_char(co,x->a,x->b)) do_char_log(co,1,"You are taken away...\n");
				break;
			case E_KEEP:   keep=1; break;
		}
	}
	if (given && cn) {
		god_take_from_char(given,cn);
		if (keep) it[given].used=USE_EMPTY;
		else if (!god_give_char(given,co)) it[given].used=USE_EMPTY;
	}
	if (cn) ch[cn].data[92]=TICKS*60;	// stay awake a while
	return 1;
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
