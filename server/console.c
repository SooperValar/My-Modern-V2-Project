/* Server console: commands typed into the terminal the server runs in.
 *
 *   help                          this list
 *   who                           players online (name, rank, where)
 *   raise <player> <exp>          give experience
 *   lower <player> <exp>          take experience away
 *   gold <player> <gold> [silver] give money
 *   announce <text>               message to everyone online
 *   tell <player> <text>          message to one player
 *   kick <player>                 log a player out
 *   shutdown                      save and stop the server (like Ctrl+C)
 *
 * Read without blocking from stdin once per pass of the main loop; if stdin
 * is closed (server started in the background) that part switches off.
 *
 * The same commands also come over the control port: a TCP port on 127.0.0.1
 * only (CONSOLE_PORT, 5556), used by the MyV2 Editor's Server page. One line
 * in, the answer back, ending with a line "." - plus a few machine-readable
 * commands for it:
 *   status                        online=<n> ticker=<t> uptime=<seconds> pid=<pid>
 *   whotab                        one line per player online: name<TAB>rank<TAB>x<TAB>y<TAB>where<TAB>god/imp/staff<TAB>points
 * Everything done here is logged with "CONSOLE:".
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdarg.h>
#include <unistd.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <errno.h>
#include <time.h>
#include "server.h"

#define CONSOLE_PORT	5556

extern volatile int quit;
static int con_off=0;
static char con_buf[1024];
static int con_len=0;

// where answers go: the terminal, or the control port's client
static int con_to=-1;			// -1 = stdout, else the client socket
static char net_out[65536];
static int net_out_len=0;
static time_t con_started=0;

static void out(char *format,...)
{
	va_list args;
	char buf[2048];
	int n;

	va_start(args,format);
	n=vsnprintf(buf,sizeof(buf),format,args);
	va_end(args);
	if (n<0) return;
	if (n>=(int)sizeof(buf)) n=sizeof(buf)-1;
	if (con_to<0) { fputs(buf,stdout); fflush(stdout); return; }
	if (net_out_len+n<(int)sizeof(net_out)) { memcpy(net_out+net_out_len,buf,n); net_out_len+=n; }
}

/* a player by (the start of) their name, online or not */
static int con_player(char *name)
{
	int co;

	if (!name || !*name) { out("  Which player?\n"); return 0; }
	co=do_lookup_char(name);
	if (!co || !IS_SANECHAR(co) || !(ch[co].flags&CF_PLAYER)) { out("  No player called %s.\n",name); return 0; }
	return co;
}

static void con_who(void)
{
	int n,cnt=0;

	for (n=1; n<MAXCHARS; n++) {
		if (ch[n].used!=USE_ACTIVE || !(ch[n].flags&CF_PLAYER)) continue;
		out("  %-20s %-22s %s%s\n",ch[n].name,rank_name[min(23,max(0,points2rank(ch[n].points_tot)))],
			get_area_m(ch[n].x,ch[n].y,0),(ch[n].flags&CF_GOD) ? "  [god]" : ((ch[n].flags&CF_IMP) ? "  [imp]" : ""));
		cnt++;
	}
	out("  %d player%s online.\n",cnt,cnt==1 ? "" : "s");
}

static void con_announce(char *text)
{
	int n,cnt=0;

	if (!text || !*text) { out("  announce <text>\n"); return; }
	for (n=1; n<MAXCHARS; n++) {
		if (ch[n].used!=USE_ACTIVE || !(ch[n].flags&(CF_PLAYER|CF_USURP)) || !ch[n].player) continue;
		do_char_log(n,0,"[Server] %s\n",text);
		cnt++;
	}
	out("  Sent to %d player%s.\n",cnt,cnt==1 ? "" : "s");
	xlog("CONSOLE: announce: %s",text);
}

/* what comes after the first n words of the line */
static char *after(char *line,int n)
{
	char *p=line;
	while (n--) {
		while (isspace(*p)) p++;
		while (*p && !isspace(*p)) p++;
	}
	while (isspace(*p)) p++;
	return p;
}

static void con_edpatch(char *path);
static void con_echo(char *s) { out("  says: %s\n",s); }

static void con_cmd(char *line)
{
	char copy[1024],*w[5],*p;
	int n,co,v;

	strncpy(copy,line,sizeof(copy)-1); copy[sizeof(copy)-1]=0;
	for (n=0; n<5; n++) w[n]="";
	for (n=0,p=strtok(copy," \t"); n<5 && p; n++,p=strtok(NULL," \t")) w[n]=p;
	if (!*w[0]) return;
	for (p=w[0]; *p; p++) *p=tolower(*p);

	if (!strcmp(w[0],"status")) {
		int cnt=0;
		for (n=1; n<MAXCHARS; n++) if (ch[n].used==USE_ACTIVE && (ch[n].flags&CF_PLAYER)) cnt++;
		out("online=%d ticker=%d uptime=%ld pid=%d\n",cnt,globs->ticker,(long)(time(NULL)-con_started),(int)getpid());
		return;
	}
	if (!strcmp(w[0],"whotab")) {
		for (n=1; n<MAXCHARS; n++) {
			if (ch[n].used!=USE_ACTIVE || !(ch[n].flags&CF_PLAYER)) continue;
			out("%s\t%s\t%d\t%d\t%s\t%s\t%d\n",ch[n].name,rank_name[min(23,max(0,points2rank(ch[n].points_tot)))],ch[n].x,ch[n].y,
				get_area_m(ch[n].x,ch[n].y,0),(ch[n].flags&CF_GOD) ? "god" : (ch[n].flags&CF_IMP) ? "imp" : (ch[n].flags&CF_STAFF) ? "staff" : "",ch[n].points_tot);
		}
		return;
	}
	if (!strcmp(w[0],"edpatch")) { con_edpatch(after(line,1)); return; }
	if (!strcmp(w[0],"talktest")) {	// talktest <NPC template> <player> <text>: as if the player said it there
		int t=atoi(w[1]),cn=0;
		for (n=1; n<MAXCHARS; n++) if (ch[n].used==USE_ACTIVE && ch[n].temp==t && !(ch[n].flags&(CF_PLAYER|CF_BODY))) { cn=n; break; }
		if (!cn) { out("  No NPC of template %d in the world.\n",t); return; }
		if (!(co=con_player(w[2]))) return;
		talk_set_echo(con_echo);
		if (!talk_custom_say(cn,co,after(line,3))) out("  (no matching dialogue)\n");
		talk_set_echo(NULL);
		return;
	}
	if (!strcmp(w[0],"give")) {	// give <player> <item template> [count]: new items into the backpack (stacks merge)
		int t=atoi(w[2]),k,cnt=w[3][0] ? atoi(w[3]) : 1,in,given=0;
		if (!(co=con_player(w[1]))) return;
		if (t<1 || t>=MAXTITEM || it_temp[t].used==USE_EMPTY) { out("  No item template %d.\n",t); return; }
		for (k=0; k<cnt && k<100; k++) {
			if (!(in=god_create_item(t))) break;
			if (!god_give_char(in,co)) { it[in].used=USE_EMPTY; out("  The backpack is full.\n"); break; }
			given++;
		}
		out("  Gave %s %d x %s.\n",ch[co].name,given,it_temp[t].name);
		return;
	}
	if (!strcmp(w[0],"wear")) {	// wear <player> <item template>|off: a new item straight into its worn slot (test), or take all off
		int t=atoi(w[2]),in,k=-1,pl;
		if (!(co=con_player(w[1]))) return;
		if (!strcmp(w[2],"off")) { for (k=0; k<20; k++) if ((in=ch[co].worn[k])) { it[in].used=USE_EMPTY; ch[co].worn[k]=0; } really_update_char(co); out("  All worn items removed.\n"); return; }
		if (t<1 || t>=MAXTITEM || it_temp[t].used==USE_EMPTY) { out("  No item template %d.\n",t); return; }
		pl=it_temp[t].placement;
		if (pl&PL_HEAD) k=WN_HEAD; else if (pl&PL_BODY) k=WN_BODY; else if (pl&PL_ARMS) k=WN_ARMS; else if (pl&PL_LEGS) k=WN_LEGS;
		else if (pl&PL_FEET) k=WN_FEET; else if (pl&PL_CLOAK) k=WN_CLOAK; else if (pl&(PL_WEAPON|PL_TWOHAND)) k=WN_RHAND; else if (pl&PL_SHIELD) k=WN_LHAND;
		if (k<0) { out("  Not wearable this way.\n"); return; }
		if (!(in=god_create_item(t))) return;
		if (ch[co].worn[k]) it[ch[co].worn[k]].used=USE_EMPTY;
		ch[co].worn[k]=in; it[in].carried=co;
		really_update_char(co);
		out("  %s wears %s. Fire %d/6, Ice %d/6. AV %d, Agi %d, Str %d, Wil %d, Int %d, Blast %d, Stealth %d, 2H deflect %d.%d%%, crit %d.%d%%\n",
		    ch[co].name,it[in].name,set_pieces(co,SET_FIRE),set_pieces(co,SET_ICE),ch[co].armor,ch[co].attrib[AT_AGIL][5],ch[co].attrib[AT_STREN][5],
		    ch[co].attrib[AT_WILL][5],ch[co].attrib[AT_INT][5],ch[co].skill[SK_BLAST][5],ch[co].skill[SK_STEALTH][5],
		    wp2h_chance(co,0)/10,wp2h_chance(co,0)%10,wp2h_chance(co,1)/10,wp2h_chance(co,1)%10);
		return;
	}
	if (!strcmp(w[0],"fighttest")) {	// fighttest <player> <NPC template> <rounds> [back]: the player hits the NPC (or "back": the NPC hits the player); damage total (test server only)
		int t=atoi(w[2]),r=atoi(w[3]),back=!strcmp(w[4],"back"),cn=0,k,ii,chill=0,before; long long total=0;
		if (!(co=con_player(w[1]))) return;
		for (n=1; n<MAXCHARS; n++) if (ch[n].used==USE_ACTIVE && !(ch[n].flags&(CF_PLAYER|CF_BODY)) && ch[n].temp==t) { cn=n; break; }
		if (!cn) { out("  No NPC of template %d in the world.\n",t); return; }
		if (r<1) r=1;
		if (r>5000) r=5000;
		for (k=0; k<r; k++) {
			ch[co].a_hp=ch[co].hp[5]*1000; ch[cn].a_hp=ch[cn].hp[5]*1000;
			before=back ? ch[co].a_hp : ch[cn].a_hp;
			if (back) do_attack(cn,co,0); else do_attack(co,cn,0);
			total+=before-(back ? ch[co].a_hp : ch[cn].a_hp);
			for (ii=0; ii<20; ii++) if (ch[cn].spell[ii] && it[ch[cn].spell[ii]].temp==SPELL_CHILL) { chill++; it[ch[cn].spell[ii]].used=USE_EMPTY; ch[cn].spell[ii]=0; really_update_char(cn); }
		}
		ch[co].a_hp=ch[co].hp[5]*1000; ch[cn].a_hp=ch[cn].hp[5]*1000;
		out("  %d rounds, damage %s: %lld.%03lld hp (%lld.%03lld a round), %s chilled %d times.\n",r,back ? "taken by the player" : "done to the NPC",
		    total/1000,total%1000,total/r/1000,total/r%1000,ch[cn].name,chill);
		return;
	}
	if (!strcmp(w[0],"items")) {	// items <player>: the backpack and the hand, with stack counts
		int k,in;
		if (!(co=con_player(w[1]))) return;
		for (k=0; k<40; k++) if ((in=ch[co].item[k])) out("  %2d  %s%s%d\n",k,it[in].name,stack_count(in)>1 ? "  x" : (stack_kind(in)==2 ? "  charges " : "  "),stack_count(in)>1 ? stack_count(in) : (stack_kind(in)==2 ? (int)it[in].data[2] : 1));
		if ((in=ch[co].citem) && !(in&0x80000000)) out("  hand: %s x%d\n",it[in].name,stack_count(in));
		return;
	}
	if (!strcmp(w[0],"useslot")) {	// useslot <player> <slot>: use the item in that backpack slot (as the player)
		int k=atoi(w[2]),in;
		if (!(co=con_player(w[1]))) return;
		if (k<0 || k>39 || !(in=ch[co].item[k])) { out("  Nothing there.\n"); return; }
		use_driver(co,in,1);
		out("  used\n");
		return;
	}
	if (!strcmp(w[0],"cleartest")) {	// cleartest <player> <NPC template>: as if the player killed that NPC (area clears)
		if (!(co=con_player(w[1]))) return;
		if (!clear_test(co,atoi(w[2]))) out("  No NPC of template %d in the world.\n",atoi(w[2]));
		else out("  done (see the player's log; #areas)\n");
		return;
	}
	if (!strcmp(w[0],"questgive")) {	// questgive <player> <NPC template>: the player hands that NPC the item it wants
		int t=atoi(w[2]),cn=0,in,e0,g0;
		extern int npc_give(int cn,int co,int in,int money);
		if (!(co=con_player(w[1]))) return;
		for (n=1; n<MAXCHARS; n++) if (ch[n].used==USE_ACTIVE && !(ch[n].flags&(CF_PLAYER|CF_BODY)) && ch[n].temp==t) { cn=n; break; }
		if (!cn) { out("  No NPC of template %d in the world.\n",t); return; }
		if (ch[cn].data[49]<=0 || !(in=god_create_item(ch[cn].data[49]))) { out("  %s wants nothing.\n",ch[cn].name); return; }
		if (!god_give_char(in,cn)) { it[in].used=USE_EMPTY; out("  %s can't take it.\n",ch[cn].name); return; }
		e0=ch[co].points_tot; g0=ch[co].gold;
		talk_set_echo(con_echo);
		npc_give(cn,co,in,0);
		talk_set_echo(NULL);
		out("  %s: +%d exp, +%dG %dS, done %d time(s)\n",ch[co].name,ch[co].points_tot-e0,(ch[co].gold-g0)/100,(ch[co].gold-g0)%100,quest_count(co,t));
		return;
	}
	if (!strcmp(w[0],"talkkill")) {	// talkkill <player> <NPC template>: as if the player killed one
		int found;
		if (!(co=con_player(w[1]))) return;
		talk_set_echo(con_echo);
		if (!talk_test_kill(co,atoi(w[2]),&found)) out(found ? "  (no quest counts that kill now)\n" : "  No NPC of template %d in the world.\n",atoi(w[2]));
		talk_set_echo(NULL);
		return;
	}
	if (!strcmp(w[0],"talkuse")) {	// talkuse <player> <x> <y>: as if the player used the item there
		if (!(co=con_player(w[1]))) return;
		talk_set_echo(con_echo);
		v=talk_test_use(co,atoi(w[2]),atoi(w[3]));
		talk_set_echo(NULL);
		if (v<0) out("  No item on %s,%s.\n",w[2],w[3]);
		else if (!v) out("  (no rule took it: the item works as usual)\n");
		else out("  (a rule took it%s)\n",ch[co].used==USE_ACTIVE ? "" : "; teleport and messages only work for a player who is online");
		return;
	}
	if (!strcmp(w[0],"talknear") || !strcmp(w[0],"talkmoney")) {	// talknear <NPC template> <player> | talkmoney <NPC template> <player> <silver>
		int t=atoi(w[1]),cn=0,m=atoi(w[3]),r;
		for (n=1; n<MAXCHARS; n++) if (ch[n].used==USE_ACTIVE && ch[n].temp==t && !(ch[n].flags&(CF_PLAYER|CF_BODY))) { cn=n; break; }
		if (!cn) { out("  No NPC of template %d in the world.\n",t); return; }
		if (!(co=con_player(w[2]))) return;
		talk_set_echo(con_echo);
		if (w[0][4]=='n') r=talk_custom_near(cn,co);
		else { if (m<=0 || ch[co].gold<m) { talk_set_echo(NULL); out("  talkmoney <npc> <player> <silver> (and the player must have it)\n"); return; }
		       ch[co].gold-=m; ch[cn].gold+=m; r=talk_custom_money(cn,co,m); if (!r) { ch[co].gold+=m; ch[cn].gold-=m; } }
		talk_set_echo(NULL);
		if (!r) out("  (no line took it%s)\n",w[0][4]=='n' ? ": the normal greeting" : ": it refuses the money");
		return;
	}
	if (!strcmp(w[0],"chesttest")) {	// chesttest <player> <x> <y> [real]: as if the player opened the chest there (real: with its open/closed state)
		int x=atoi(w[2]),y=atoi(w[3]),in;
		if (!(co=con_player(w[1]))) return;
		if (x<1 || y<1 || x>=MAPX || y>=MAPY || !(in=map[x+y*MAPX].it)) { out("  No item on %d,%d.\n",x,y); return; }
		if (it[in].driver!=75) { out("  %s on %d,%d is not a MyV2 chest (driver %d).\n",it[in].name,x,y,it[in].driver); return; }
		if (!strcmp(w[4],"real")) {	// as in the game: an open chest stays open, an opened one starts its timer
			v=it[in].active;
			n=talk_chest_open(co,in);
			if (n && !v) it[in].active=it[in].duration;
			out("  %s · chest is %s (%d s left)\n",n ? "opened" : "did not open",it[in].active ? "open" : "closed",it[in].active/TICKS);
			return;
		}
		v=it[in].active; it[in].active=0;
		n=talk_chest_open(co,in);
		it[in].active=v;
		out("  %s (the result went to %s's log)\n",n ? "opened" : "did not open",ch[co].name);
		return;
	}
	if (!strcmp(w[0],"zone")) {
		int x=atoi(w[1]),y=atoi(w[2]);
		if (!w[1][0] || !w[2][0] || x<0 || y<0 || x>=MAPX || y>=MAPY) { out("  zone <x> <y>\n"); return; }
		out("  %d,%d: %s\n",x,y,get_area_m(x,y,1)[0] ? get_area_m(x,y,1) : "no zone");
		out("  #quest place: %s\n",get_area_street(x,y)[0] ? get_area_street(x,y) : "-");
		return;
	}
	if (!strcmp(w[0],"zonereload")) {
		n=zone_load();
		if (n>0) out("  Zones loaded: %d zones in %d boxes.\n",zone_count(),zone_boxes());
		else if (n==0) out("  No zones.dat: the built-in zones are used (%d zones in %d boxes).\n",zone_count(),zone_boxes());
		else out("  zones.dat could not be read; the zones stay as they were.\n");
		return;
	}
	if (!strcmp(w[0],"talkreload")) {
		n=talk_load();
		out("  NPC dialogue loaded: %d entries%s.\n",talk_entries(),n ? " (some lines were not understood)" : "");
		return;
	}
	if (!strcmp(w[0],"help") || !strcmp(w[0],"?")) {
		out("  Console commands:\n"
		    "  who                           players online\n"
		    "  raise <player> <exp>          give experience\n"
		    "  lower <player> <exp>          take experience away\n"
		    "  gold <player> <gold> [silver] give money\n"
		    "  announce <text>               message to everyone online\n"
		    "  tell <player> <text>          message to one player\n"
		    "  kick <player>                 log a player out\n"
		    "  quest <player> [<n> <value>]  show or set a player's quest steps\n"
		    "  talkreload                    read the NPC dialogue file again\n"
		    "  zonereload                    read the zones (.dat/zones.dat) again\n"
		    "  zone <x> <y>                  the zone names at a spot\n"
		    "  talktest <npc template> <player> <text>   try a conversation\n"
		    "  talkkill <player> <npc template>          try a quest kill\n"
		    "  talkuse <player> <x> <y>                  try using the item there\n"
		    "  talknear <npc template> <player>          try a player coming close\n"
		    "  talkmoney <npc template> <player> <silver>   try handing money over\n"
		    "  questgive <player> <npc template>         hand that NPC the item it wants\n"
		    "  cleartest <player> <npc template>         as if the player killed it (area clears)\n"
		    "  give <player> <item template> [count]     new items into the backpack\n"
		    "  items <player>                            the backpack, with stack counts\n"
		    "  useslot <player> <slot>                   use the item in that backpack slot\n"
		    "  shutdown                      save and stop the server\n");
	} else if (!strcmp(w[0],"quest")) {
		if (!(co=con_player(w[1]))) return;
		if (*w[2]) {
			n=atoi(w[2]);
			if (n<1 || n>255 || !*w[3]) { out("  quest <player> <1-255> <value>\n"); return; }
			quest_set(co,n,atoi(w[3]));
			out("  %s: quest %d = %d\n",ch[co].name,n,quest_get(co,n));
		} else {
			for (n=1,v=0; n<=255; n++) if (quest_get(co,n)) { out("  %s: quest %d = %d\n",ch[co].name,n,quest_get(co,n)); v++; }
			if (!v) out("  %s has no quest steps yet.\n",ch[co].name);
		}
	} else if (!strcmp(w[0],"who")) {
		con_who();
	} else if (!strcmp(w[0],"raise") || !strcmp(w[0],"lower")) {
		if (!(co=con_player(w[1]))) return;
		v=atoi(w[2]);
		if (v<=0) { out("  %s <player> <exp>, exp above 0\n",w[0]); return; }
		if (w[0][0]=='r') {
			ch[co].points+=v; ch[co].points_tot+=v;
			do_char_log(co,0,"You have been rewarded by the gods. You received %d experience points.\n",v);
			do_check_new_level(co);
		} else {
			ch[co].points-=v; ch[co].points_tot-=v;
			do_char_log(co,0,"You have been punished by the gods. You lost %d experience points.\n",v);
		}
		do_update_char(co);
		out("  %s %s by %d (now %d).\n",w[0][0]=='r' ? "Raised" : "Lowered",ch[co].name,v,ch[co].points_tot);
		xlog("CONSOLE: %s %s by %d",w[0],ch[co].name,v);
	} else if (!strcmp(w[0],"gold")) {
		if (!(co=con_player(w[1]))) return;
		v=atoi(w[2])*100+atoi(w[3]);
		if (v<=0) { out("  gold <player> <gold> [silver]\n"); return; }
		ch[co].gold+=v;
		do_char_log(co,0,"You have been rewarded by the gods. You received %dG %dS.\n",v/100,v%100);
		do_update_char(co);
		out("  Gave %s %dG %dS.\n",ch[co].name,v/100,v%100);
		xlog("CONSOLE: gold %s %dG %dS",ch[co].name,v/100,v%100);
	} else if (!strcmp(w[0],"announce")) {
		con_announce(after(line,1));
	} else if (!strcmp(w[0],"tell")) {
		if (!(co=con_player(w[1]))) return;
		p=after(line,2);
		if (!*p) { out("  tell <player> <text>\n"); return; }
		if (ch[co].used!=USE_ACTIVE) { out("  %s is not online.\n",ch[co].name); return; }
		do_char_log(co,0,"[Server] %s\n",p);
		out("  Told %s.\n",ch[co].name);
		xlog("CONSOLE: tell %s: %s",ch[co].name,p);
	} else if (!strcmp(w[0],"kick")) {
		if (!(co=con_player(w[1]))) return;
		if (ch[co].used!=USE_ACTIVE || !ch[co].player) { out("  %s is not online.\n",ch[co].name); return; }
		plr_logout(co,ch[co].player,LO_IDLE);
		ch[co].flags|=CF_KICKED;
		out("  Kicked %s.\n",ch[co].name);
		xlog("CONSOLE: kicked %s",ch[co].name);
	} else if (!strcmp(w[0],"shutdown")) {
		out("  Shutting down...\n");
		xlog("CONSOLE: shutdown");
		quit=1;
	} else out("  Unknown command \"%s\". Type help.\n",w[0]);
}

/* ---- live editing from the MyV2 Editor --------------------------------------
 * "edpatch <file>": the editor writes the changes it made to its copy of the world
 * into <file>; each change carries the bytes it expects to find, so nothing the game
 * changed in the meantime is overwritten. All or nothing: one mismatch and nothing
 * is applied. Then the NPC actions run (move, turn, remove, respawn a template).
 *
 * file: "MYV2PATCH1", u32 records, { u8 kind, u32 index, u16 offset, u16 len, old[len], new[len] }...,
 *       u32 actions, { u8 type, i32 a, b, c, d }...
 * kinds: 0 map, 1 item, 2 char, 3 char template, 4 item template, 5 effect
 * actions: 20 remove NPC a (template b), 21 move NPC a (template b) to c,d, 22 turn NPC a (template b) to c,
 *          23 respawn template a (as the game's reset) */
extern void reset_char(int n);

struct edrec { unsigned char kind; unsigned int idx; unsigned short off, len; long pos; };
#define ED_MAXREC 200000
#define ED_MAXACT 4096

static unsigned char *ed_base(int kind,unsigned int idx,int *size)
{
	switch (kind) {
		case 0: *size=sizeof(struct map); return idx<MAPX*MAPY ? (unsigned char*)&map[idx] : NULL;
		case 1: *size=sizeof(struct item); return idx<MAXITEM ? (unsigned char*)&it[idx] : NULL;
		case 2: *size=sizeof(struct character); return idx<MAXCHARS ? (unsigned char*)&ch[idx] : NULL;
		case 3: *size=sizeof(struct character); return idx<MAXTCHARS ? (unsigned char*)&ch_temp[idx] : NULL;
		case 4: *size=sizeof(struct item); return idx<MAXTITEM ? (unsigned char*)&it_temp[idx] : NULL;
		case 5: *size=sizeof(struct effect); return idx<MAXEFFECT ? (unsigned char*)&fx[idx] : NULL;
	}
	return NULL;
}

static int ed_light_of(int m)
{
	int in=map[m].it,v=0,cn=map[m].ch;
	if (in>0 && in<MAXITEM) v+=it[in].active ? it[in].light[1] : it[in].light[0];
	return v + ((cn>0 && cn<MAXCHARS) ? ch[cn].light : 0);
}

static void con_edpatch(char *path)
{
	static struct edrec rec[ED_MAXREC];
	static int act[ED_MAXACT][5];
	static unsigned char mark[MAPX*MAPY];
	unsigned char hdr[10],buf[8192],*p;
	unsigned int cnt,nact,n,k,i;
	int size,bad=0,x,y,m,x0=MAPX,y0=MAPY,x1=-1,y1=-1,lights=0,sight=0,cn,v,done=0;
	FILE *f;

	f=fopen(path,"rb");
	if (!f) { out("error cannot open %s\n",path); return; }
	if (fread(hdr,1,10,f)!=10 || memcmp(hdr,"MYV2PATCH1",10) || fread(&cnt,4,1,f)!=1 || cnt>ED_MAXREC) { out("error not a patch file\n"); fclose(f); return; }

	// 1. read and check every change
	for (n=0; n<cnt; n++) {
		if (fread(&rec[n].kind,1,1,f)!=1 || fread(&rec[n].idx,4,1,f)!=1 || fread(&rec[n].off,2,1,f)!=1 || fread(&rec[n].len,2,1,f)!=1) { out("error short file\n"); fclose(f); return; }
		rec[n].pos=ftell(f);
		p=ed_base(rec[n].kind,rec[n].idx,&size);
		if (!p || rec[n].off+rec[n].len>size || rec[n].len>sizeof(buf)) { out("error bad record %d\n",n); fclose(f); return; }
		if (fread(buf,1,rec[n].len,f)!=rec[n].len) { out("error short file\n"); fclose(f); return; }
		if (memcmp(buf,p+rec[n].off,rec[n].len)) {
			if (bad<20) out("conflict %d %u\n",rec[n].kind,rec[n].idx);
			bad++;
		}
		fseek(f,rec[n].len,SEEK_CUR);
	}
	if (fread(&nact,4,1,f)!=1) nact=0;
	if (nact>ED_MAXACT) nact=ED_MAXACT;
	for (n=0; n<nact; n++) if (fread(&hdr[0],1,1,f)!=1 || fread(&act[n][1],4,4,f)!=4) { nact=n; break; } else act[n][0]=hdr[0];
	for (n=0; n<nact; n++) {	// the NPCs the actions are for must still be there
		if (act[n][0]==23) continue;
		cn=act[n][1];
		if (cn<1 || cn>=MAXCHARS || ch[cn].used!=USE_ACTIVE || ch[cn].temp!=act[n][2] || (ch[cn].flags&(CF_PLAYER|CF_BODY))) {
			if (bad<20) out("conflict npc %d\n",cn);
			bad++;
		}
	}
	if (bad) { out("rejected %d conflicts (the game changed those since the editor looked)\n",bad); fclose(f); return; }

	// 2. which tiles change in a way that moves light around (items, sight, indoors)
	for (n=0; n<cnt; n++) {
		m=-1;
		if (rec[n].kind==0) {
			m=rec[n].idx;
			if (rec[n].off+rec[n].len<=4 && !(rec[n].off<20 && rec[n].off+rec[n].len>20)) m=-1;	// only the floor or object sprite
			if (rec[n].off<=20 && rec[n].off+rec[n].len>20) sight=1;
		} else if (rec[n].kind==1 && it[rec[n].idx].used==USE_ACTIVE && !it[rec[n].idx].carried) m=it[rec[n].idx].x+it[rec[n].idx].y*MAPX;
		if (m<0 || m>=MAPX*MAPY) continue;
		x=m%MAPX; y=m/MAPX; lights=1;
		if (x<x0) x0=x;
		if (y<y0) y0=y;
		if (x>x1) x1=x;
		if (y>y1) y1=y;
		for (i=max(1,y-LIGHTDIST); i<min(MAPY-1,y+1+LIGHTDIST); i++)
			memset(mark+i*MAPX+max(1,x-LIGHTDIST),1,min(MAPX-1,x+1+LIGHTDIST)-max(1,x-LIGHTDIST));
	}
	x0=max(1,x0-LIGHTDIST); y0=max(1,y0-LIGHTDIST); x1=min(MAPX-2,x1+LIGHTDIST); y1=min(MAPY-2,y1+LIGHTDIST);
	if (lights) for (y=y0; y<=y1; y++) for (x=x0; x<=x1; x++) {
		m=x+y*MAPX; if (!mark[m]) continue;
		if ((v=ed_light_of(m))) do_add_light(x,y,-v);
		map[m].dlight=0;
	}

	// 3. apply
	for (n=0; n<cnt; n++) {
		p=ed_base(rec[n].kind,rec[n].idx,&size);
		fseek(f,rec[n].pos+rec[n].len,SEEK_SET);
		if (fread(p+rec[n].off,1,rec[n].len,f)==rec[n].len) done++;
	}
	fclose(f);

	if (lights) for (y=y0; y<=y1; y++) for (x=x0; x<=x1; x++) {
		m=x+y*MAPX; if (!mark[m]) continue;
		mark[m]=0;
		if ((v=ed_light_of(m))) do_add_light(x,y,v);
		if (map[m].flags&MF_INDOORS) compute_dlight(x,y);
	}
	if (sight) { for (k=1; k<MAXCHARS; k++) see[k].x=see[k].y=0; reset_go(x0+LIGHTDIST,y0+LIGHTDIST); }
	for (n=0; n<cnt; n++)	// a changed character (a player's gold, stats, backpack...): work out its values again, refresh its client
		if (rec[n].kind==2 && rec[n].idx>0 && rec[n].idx<MAXCHARS && ch[rec[n].idx].used==USE_ACTIVE) do_update_char(rec[n].idx);

	// 4. NPC actions
	for (n=0; n<nact; n++) {
		cn=act[n][1];
		switch (act[n][0]) {
			case 20: god_destroy_items(cn); plr_map_remove(cn); ch[cn].used=USE_EMPTY; break;
			case 21:
				ch[cn].status=0; ch[cn].attack_cn=0; ch[cn].skill_nr=0; ch[cn].goto_x=0; ch[cn].misc_action=0;
				plr_map_remove(cn);
				if (!god_drop_char(cn,act[n][3],act[n][4])) { plr_map_set(cn); out("note %s could not be moved there\n",ch[cn].name); }
				else ch[cn].data[29]=act[n][3]+act[n][4]*MAPX;
				break;
			case 22: ch[cn].dir=act[n][3]; ch[cn].data[30]=act[n][3]; ch[cn].status=0; break;
			case 23: if (act[n][1]>0 && act[n][1]<MAXTCHARS) reset_char(act[n][1]); break;
		}
	}
	out("ok %d %d\n",done,nact);
	xlog("CONSOLE: MyV2 Editor live edit: %d changes, %d NPC actions",done,nact);
}

/* ---- the control port ---- */
static int lsock=-2, csock=-1;
static char cbuf[2048];
static int clen=0;

static void net_open(void)
{
	struct sockaddr_in a;
	int one=1;

	lsock=socket(AF_INET,SOCK_STREAM,0);
	if (lsock<0) { xlog("Console: no control port (socket failed)"); lsock=-1; return; }
	setsockopt(lsock,SOL_SOCKET,SO_REUSEADDR,&one,sizeof(one));
	memset(&a,0,sizeof(a));
	a.sin_family=AF_INET; a.sin_port=htons(CONSOLE_PORT); a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);	// this computer only
	if (bind(lsock,(struct sockaddr*)&a,sizeof(a))<0 || listen(lsock,4)<0) {
		xlog("Console: control port %d not available",CONSOLE_PORT);
		close(lsock); lsock=-1; return;
	}
	fcntl(lsock,F_SETFL,O_NONBLOCK);
	xlog("Console: control port 127.0.0.1:%d open (MyV2 Editor)",CONSOLE_PORT);
}

static void net_send_all(int fd,char *b,int len)
{
	int w,tries=0;
	while (len>0 && tries<200) {
		w=send(fd,b,len,MSG_NOSIGNAL);
		if (w>0) { b+=w; len-=w; continue; }
		if (w<0 && (errno==EAGAIN || errno==EWOULDBLOCK)) { usleep(1000); tries++; continue; }
		break;
	}
}

static void net_poll(void)
{
	int r,c;
	char *nl;

	if (lsock==-2) { con_started=time(NULL); net_open(); }
	if (lsock<0) return;
	if (csock<0) {
		c=accept(lsock,NULL,NULL);
		if (c<0) return;
		fcntl(c,F_SETFL,O_NONBLOCK);
		csock=c; clen=0;
	}
	r=recv(csock,cbuf+clen,sizeof(cbuf)-1-clen,0);
	if (r==0 || (r<0 && errno!=EAGAIN && errno!=EWOULDBLOCK)) { close(csock); csock=-1; return; }
	if (r<0) return;
	clen+=r; cbuf[clen]=0;
	while ((nl=strchr(cbuf,'\n'))) {
		*nl=0;
		if (nl>cbuf && nl[-1]=='\r') nl[-1]=0;
		con_to=csock; net_out_len=0;
		con_cmd(cbuf);
		out(".\n");			// end of the answer
		net_send_all(csock,net_out,net_out_len);
		con_to=-1;
		r=strlen(nl+1); memmove(cbuf,nl+1,r+1); clen=r;
	}
	if (clen>=(int)sizeof(cbuf)-1) clen=0;
}

/* called once per pass of the main loop */
void console_poll(void)
{
	fd_set fds;
	struct timeval tv;
	int r,n;
	char *nl;

	net_poll();
	if (con_off) return;
	FD_ZERO(&fds); FD_SET(0,&fds);
	tv.tv_sec=0; tv.tv_usec=0;
	if (select(1,&fds,NULL,NULL,&tv)<=0 || !FD_ISSET(0,&fds)) return;
	r=read(0,con_buf+con_len,sizeof(con_buf)-1-con_len);
	if (r<=0) { con_off=1; xlog("Console: no terminal input, console off"); return; }
	con_len+=r; con_buf[con_len]=0;
	while ((nl=strchr(con_buf,'\n'))) {
		*nl=0;
		if (nl>con_buf && nl[-1]=='\r') nl[-1]=0;
		con_cmd(con_buf);
		n=strlen(nl+1);
		memmove(con_buf,nl+1,n+1);
		con_len=n;
	}
	if (con_len>=(int)sizeof(con_buf)-1) con_len=0;	// an endless line: drop it
}
