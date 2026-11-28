/* help.c -- MyV2 (Nov 27, Cody): pages for the Godot client's Help window.
 *
 * The client asks for a page (CL_CMD_HELP: short page at byte 1, int arg at byte 3); the server answers with SV_HELP packets of 64 bytes:
 *   [0] SV_HELP  [1] page  [2] kind  [3..4] row  [5] column  [6] font  [7] part  [8..63] 56 characters of text
 * kind 0 starts the page (row = the arg asked for), 1 a column heading (font 1 = right-aligned), 2 a table cell,
 * 3 a line of text under the table, 255 ends the page (row = the number of table rows). A longer text comes in parts
 * 0, 1, 2... of the same row / column, which the client joins.
 * Pages reuse the chat commands: while a page is built (help_capture_cn) do_char_log() turns their lines into the
 * page's text lines, and help_line() / #quest's list (help_rows) give table rows instead of chat lines.
 * Pages: 1 commands (#help), 2 quests (arg 1: all), 3 one quest in detail (arg: its number, +0x8000: of "all"),
 * 4 areas (#areas), 5 kill quests (#kills), 6 ranks (#ranks, then #rank under the table), 7 who is online (#who),
 * 8 armor (#armor and #moddedarmor), 9 weapons (every weapon type), 10 rings, 11 belts, 12 special items (#specialw and
 * #specialarmor). */

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

static void help_heading(int col,int right,const char *title)
{
	hp_send(1,0,col,right,title);
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
			help_heading(0,0,"Command"); help_heading(1,0,"What it does");
			do_help(cn,NULL);
			break;
		case HELP_QUESTS:
			help_rows=1;
			help_heading(0,1,"#"); help_heading(1,0,"Giver"); help_heading(2,0,"Where"); help_heading(3,0,"Reward"); help_heading(4,1,"Exp");
			do_quest(cn,(arg&1) ? "all" : NULL,NULL);
			break;
		case HELP_QUEST:
			help_rows=0;
			sprintf(num,"%d",arg&0x7fff);
			do_quest(cn,num,(arg&0x8000) ? "all" : NULL);
			break;
		case HELP_AREAS:
			help_rows=1;
			help_heading(0,0,"Area"); help_heading(1,0,"Progress");
			do_areas(cn);
			break;
		case HELP_KILLS:
			help_rows=1;
			help_heading(0,1,"#"); help_heading(1,0,"Task"); help_heading(2,0,"Giver"); help_heading(3,0,"Where");
			help_heading(4,0,"Reward"); help_heading(5,0,"Status");
			do_kills(cn);
			break;
		case HELP_RANKS:
			help_rows=1;
			help_heading(0,1,"#"); help_heading(1,0,"Rank"); help_heading(2,1,"Starts at");
			do_ranks(cn);
			help_rows=0;
			do_rank(cn);
			break;
		case HELP_WHO:
			help_rows=1;
			help_heading(0,0,"Rank"); help_heading(1,0,"Name"); help_heading(2,0,"Group"); help_heading(3,0,"Where");
			user_who(cn);
			break;
		case HELP_ARMOR:
			help_rows=1;
			help_heading(0,0,"Armor"); help_heading(1,1,"Needs AGL"); help_heading(2,1,"Needs STR"); help_heading(3,1,"AV per piece"); help_heading(4,1,"Full set");
			do_info_armor(cn);
			do_info_moddedarmor(cn);
			break;
		case HELP_WEAPONS:
			help_rows=1;
			help_heading(0,0,"Weapon"); help_heading(1,1,"Needs AGL"); help_heading(2,1,"Needs STR"); help_heading(3,1,"Needs skill"); help_heading(4,1,"WV");
			help_weapons(cn);
			break;
		case HELP_RINGS:
			help_rows=1;
			help_heading(0,0,"Ring"); help_heading(1,0,"Rank"); help_heading(2,0,"Silver"); help_heading(3,0,"Golden");
			do_info_rings(cn);
			break;
		case HELP_BELTS:
			help_rows=1;
			help_heading(0,0,"Belt"); help_heading(1,0,"Needs");
			help_heading(2,1,"BR"); help_heading(3,1,"WI"); help_heading(4,1,"IN"); help_heading(5,1,"AG"); help_heading(6,1,"ST");
			help_heading(7,1,"HP"); help_heading(8,1,"EN"); help_heading(9,1,"MA"); help_heading(10,0,"Skills");
			do_info_belt(cn);
			break;
		case HELP_SPECIAL:
			help_rows=1;
			help_heading(0,0,"Item"); help_heading(1,0,"Type"); help_heading(2,0,"Needs"); help_heading(3,1,"WV / AV"); help_heading(4,0,"Gives");
			do_info_specialw(cn);
			do_info_specialarmor(cn);
			break;
	}
	help_capture_cn=0; help_rows=0;
	hp_send(255,hp_row,0,0,NULL);
}
