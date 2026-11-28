/* help.c -- MyV2 (Nov 27, Cody): pages for the Godot client's Help window.
 *
 * The client asks for a page (CL_CMD_HELP: short page at byte 1, int arg at byte 3); the server answers with SV_HELP packets of 64 bytes:
 *   [0] SV_HELP  [1] page  [2] kind  [3..4] row  [5] column  [6] font  [7] part  [8..63] 56 characters of text
 * kind 0 starts the page (row = the arg asked for), 1 a column heading (font 1 = right-aligned, row = its width in
 * tenths), 2 a table cell, 4 a sub-tab (row = the arg that shows it, in the order they come),
 * 3 a line of text under the table, 255 ends the page (row = the number of table rows). A longer text comes in parts
 * 0, 1, 2... of the same row / column, which the client joins.
 * Pages reuse the chat commands: while a page is built (help_capture_cn) do_char_log() turns their lines into the
 * page's text lines, and help_line() / #quest's list (help_rows) give table rows instead of chat lines.
 * Pages: 1 commands (#help), 2 quests (arg 1: all), 3 one quest in detail (arg: its number, +0x8000: of "all"),
 * 4 areas (#areas), 5 kill quests (#kills), 6 ranks (#ranks, then #rank under the table), 7 who is online (#who),
 * 8 armor (#armor and #moddedarmor: tiered armor), 9 weapons (arg: 0 daggers, 1 swords, 2 two-handed swords, 3 axes,
 * 4 greataxes, 5 staffs; each with its special weapons), 10 rings (arg: 0 attribute rings as a grid by stone, 1 skill
 * rings, 2 other rings), 11 belts, 12 special items (#specialw and #specialarmor). Pages with sub-tabs send them.
 * Column widths and sub-tabs come from here, so a new layout or a new sub-tab needs no new client. */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "server.h"

int help_capture_cn=0;		// the character whose do_char_log() lines go into the page being built
int help_rows=0;		// the page is a table: help_line() and #quest's list give rows

static int hp_nr,hp_page,hp_row,hp_line;

static void hp_send(int kind,int row,int col,int font,const char *text)
{
	unsigned char buf[64];
	int len=text ? (int)strlen(text) : 0,off=0,part=0,k;

	do {
		memset(buf,0,sizeof(buf));
		buf[0]=SV_HELP; buf[1]=hp_page; buf[2]=kind;
		*(unsigned short*)(buf+3)=row;
		buf[5]=col; buf[6]=font; buf[7]=part;
		k=len-off; if (k>56) k=56;
		if (k>0) memcpy(buf+8,text+off,k);
		xsend(hp_nr,buf,64);
		off+=56; part++;
	} while (off<len);
}

/* a column heading; width: the column's share of the table in tenths (the client's stretch ratio) */
void help_heading(int col,int right,int width,const char *title)
{
	hp_send(1,width,col,right,title);
}

/* a sub-tab the page offers: asking for the page with arg shows it (Weapons: a weapon type, Rings: a kind of ring) */
void help_subtab(int arg,const char *name)
{
	hp_send(4,arg,0,0,name);
}

/* a table row of n cells */
void help_cells(int font,int n,const char **cells)
{
	int k;
	for (k=0; k<n; k++) hp_send(2,hp_row,k,font,cells[k] ? cells[k] : "");
	hp_row++;
}

/* a line a chat command printed while its page is built: a text line under the table; in a table, a short line
 * ending in ':' ("Staff Commands:") is a section row instead, and empty lines are left out */
void help_capture_line(int font,const char *text)
{
	char buf[1024];
	int len;

	strncpy(buf,text,sizeof(buf)-1); buf[sizeof(buf)-1]=0;
	len=strlen(buf);
	while (len>0 && (buf[len-1]=='\n' || buf[len-1]==' ')) buf[--len]=0;
	if (help_rows) {
		const char *cells[2];
		if (!len || strspn(buf,"-")==(size_t)len) return;
		if (len<40 && buf[len-1]==':') { cells[0]=buf; cells[1]=""; help_cells(font,2,cells); return; }
	}
	hp_send(3,hp_line++,0,font,buf);
}

void plr_cmd_help(int nr)
{
	int cn,page,arg;
	char num[16];

	cn=player[nr].usnr;
	if (cn<1 || cn>=MAXCHARS) return;
	page=*(unsigned short*)(player[nr].inbuf+1);		// the client's ShortAndInt packet: short page, int arg
	arg=*(unsigned int*)(player[nr].inbuf+3)&0xffff;

	hp_nr=nr; hp_page=page; hp_row=0; hp_line=0;
	hp_send(0,arg,0,0,NULL);
	help_capture_cn=cn;
	switch (page) {
		case HELP_COMMANDS:
			help_rows=1;
			help_heading(0,0,14,"Command"); help_heading(1,0,26,"What it does");
			do_help(cn,NULL);
			break;
		case HELP_QUESTS:
			help_rows=1;
			help_heading(0,1,3,"#"); help_heading(1,0,13,"Giver"); help_heading(2,0,15,"Where"); help_heading(3,0,16,"Reward"); help_heading(4,1,6,"Exp");
			do_quest(cn,(arg&1) ? "all" : NULL,NULL);
			break;
		case HELP_QUEST:
			help_rows=0;
			sprintf(num,"%d",arg&0x7fff);
			do_quest(cn,num,(arg&0x8000) ? "all" : NULL);
			break;
		case HELP_AREAS:
			help_rows=1;
			help_heading(0,0,16,"Area"); help_heading(1,0,24,"Progress");
			do_areas(cn);
			break;
		case HELP_KILLS:
			help_rows=1;
			help_heading(0,1,3,"#"); help_heading(1,0,19,"Task"); help_heading(2,0,10,"Giver"); help_heading(3,0,11,"Where");
			help_heading(4,0,13,"Reward"); help_heading(5,0,11,"Status");
			do_kills(cn);
			break;
		case HELP_RANKS:
			help_rows=1;
			help_heading(0,1,3,"#"); help_heading(1,0,22,"Rank"); help_heading(2,1,15,"Starts at");
			do_ranks(cn);
			help_rows=0;
			do_rank(cn);
			break;
		case HELP_WHO:
			help_rows=1;
			help_heading(0,0,6,"Rank"); help_heading(1,0,12,"Name"); help_heading(2,0,12,"Group"); help_heading(3,0,24,"Where");
			user_who(cn);
			break;
		case HELP_ARMOR:
			help_rows=1;
			help_heading(0,0,14,"Armor"); help_heading(1,1,10,"Needs AGL"); help_heading(2,1,10,"Needs STR"); help_heading(3,1,10,"AV per piece"); help_heading(4,1,10,"Full set");
			do_info_armor(cn);
			do_info_moddedarmor(cn);
			break;
		case HELP_WEAPONS:
			help_rows=1;
			help_heading(0,0,20,"Weapon"); help_heading(1,1,8,"Needs AGL"); help_heading(2,1,8,"Needs STR"); help_heading(3,1,8,"Needs skill"); help_heading(4,1,6,"WV"); help_heading(5,0,30,"Also");
			help_weapons(cn,arg);
			break;
		case HELP_RINGS:
			help_rows=1;
			help_rings(cn,arg);
			break;
		case HELP_BELTS:
			help_rows=1;
			help_heading(0,0,14,"Belt"); help_heading(1,0,8,"Needs");
			help_heading(2,1,4,"BR"); help_heading(3,1,4,"WI"); help_heading(4,1,4,"IN"); help_heading(5,1,4,"AG"); help_heading(6,1,4,"ST");
			help_heading(7,1,4,"HP"); help_heading(8,1,4,"EN"); help_heading(9,1,4,"MA"); help_heading(10,0,22,"Skills");
			do_info_belt(cn);
			break;
		case HELP_SPECIAL:
			help_rows=1;
			help_heading(0,0,16,"Item"); help_heading(1,0,6,"Type"); help_heading(2,0,22,"Needs"); help_heading(3,1,6,"WV / AV"); help_heading(4,0,26,"Gives");
			do_info_specialw(cn);
			do_info_specialarmor(cn);
			break;
	}
	help_capture_cn=0; help_rows=0;
	hp_send(255,hp_row,0,0,NULL);
}
