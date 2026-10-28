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
 * is closed (server started in the background) the console just switches off.
 * Everything done here is logged with "CONSOLE:".
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdarg.h>
#include <unistd.h>
#include <sys/select.h>
#include "server.h"

extern volatile int quit;
static int con_off=0;
static char con_buf[1024];
static int con_len=0;

static void out(char *format,...)
{
	va_list args;
	va_start(args,format);
	vprintf(format,args);
	va_end(args);
	fflush(stdout);
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

static void con_cmd(char *line)
{
	char copy[1024],*w[4],*p;
	int n,co,v;

	strncpy(copy,line,sizeof(copy)-1); copy[sizeof(copy)-1]=0;
	for (n=0; n<4; n++) w[n]="";
	for (n=0,p=strtok(copy," \t"); n<4 && p; n++,p=strtok(NULL," \t")) w[n]=p;
	if (!*w[0]) return;
	for (p=w[0]; *p; p++) *p=tolower(*p);

	if (!strcmp(w[0],"help") || !strcmp(w[0],"?")) {
		out("  Console commands:\n"
		    "  who                           players online\n"
		    "  raise <player> <exp>          give experience\n"
		    "  lower <player> <exp>          take experience away\n"
		    "  gold <player> <gold> [silver] give money\n"
		    "  announce <text>               message to everyone online\n"
		    "  tell <player> <text>          message to one player\n"
		    "  kick <player>                 log a player out\n"
		    "  shutdown                      save and stop the server\n");
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

/* called once per pass of the main loop */
void console_poll(void)
{
	fd_set fds;
	struct timeval tv;
	int r,n;
	char *nl;

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
