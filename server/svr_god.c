/*************************************************************************

This file is part of 'Mercenaries of Astonia v2'
Copyright (c) 1997-2001 Daniel Brockhaus (joker@astonia.com)
All rights reserved.

**************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <time.h>
#include <fcntl.h>
#include <unistd.h>

#include "server.h"
#include "driver.h"

static char *mkp(void)
{
        static char buf[40];
        static char *syl1[]={
                "thi","ar","an","un","iss","ish","urs","ur",
                "ent","esh","ash","jey","jay",
                "dur","lon","lan","len","lun",
                "so","lur","gar","cry","au","dau","dei",
                "zir","zil","sol","luc","ni","bus",
                "mid","err","doo","do","al","ea","jac","ta",
                "bi","vae","rif","tol","nim","ru","li",
                "fro","sam","beut","bil","ga",
                "nee","ara","rho","dan","va","lan",
                "cec","cic","cac","cuc","ix","vea","cya",
                "hie","bo","ni","do","sar","phe","ho",
                "cos","sin","tan","mul","har","gur","tar",
                "a","e","i","o","u","je","ho","if",
                "jai","coy","ya","pa","pul","pil",
                "rez","rel","rar","dom","rom","tom",
                "ar","ur","ir","er","yr","li","la","lu","lo"
                };
        static char *syl2[]={
                "tar","tur","kar","kur","kan","tan","gar","gur","run"};
        static char *syl3[]={
                "a","e","i","o","u"};

        int n;

        buf[0]=0;

        n=random()%(sizeof(syl1)/sizeof(char *));
        strcat(buf,syl1[n]);
        buf[0]=toupper(buf[0]);

        n=random()%(sizeof(syl2)/sizeof(char *));
        strcat(buf,syl2[n]);

        if (random()%2) return buf;

        n=random()%(sizeof(syl3)/sizeof(char *));
        strcat(buf,syl3[n]);

        return buf;
}

#define MAXFREEITEM	32
static int free_item_list[MAXFREEITEM];

void god_init_freelist(void)
{
	int n,m;

        bzero(free_item_list,sizeof(free_item_list));
	
	for (m=0,n=1; n<MAXITEM; n++) {
		if (it[n].used==USE_EMPTY) {
			free_item_list[m++]=n;
			if (m>=MAXFREEITEM) break;
		}
	}
}

int get_free_item(void)
{
	int n,in,m;
	
        for (n=0; n<MAXFREEITEM; n++)
		if ((in=free_item_list[n]) && it[in].used==USE_EMPTY) break;
	if (n<MAXFREEITEM) { free_item_list[n]=0; return in; }
	
	for (m=in=0, n=1; n<MAXITEM; n++) {
		if (it[n].used==USE_EMPTY) {
			in=free_item_list[m++]=n;
			if (m>=MAXFREEITEM) break;
		}
	}
	
	return in;
}

int god_create_item(int temp)
{
        int n,m;
        unsigned long long prof;

        if (!IS_SANEITEMPLATE(temp)) return 0;

        prof=prof_start();

        if (it_temp[temp].used == USE_EMPTY) {
                xlog("god_create_item(): unused template.");
                prof_stop(23,prof);
                return 0;
        }

	n=get_free_item();
        if (!n) {
                xlog("god_create_item (svr_god.c): MAXITEM reached");
                prof_stop(23,prof);
                return 0;
        }

        if (it_temp[temp].flags&IF_UNIQUE) {
                for (m=1; m<MAXITEM; m++)
                        if (it[m].used!=USE_EMPTY && it[m].temp==temp) break;

                if (m<MAXITEM) {
                	prof_stop(23,prof);
                        return 0;
                }
        }

        it[n]=it_temp[temp];
        it[n].temp=temp;

	prof_stop(23,prof);

        return n;
}

int god_create_char(int temp,int withitems)
{
        int n,m,tmp,flag=0;

        for (n=1; n<MAXCHARS; n++)
                if (ch[n].used==USE_EMPTY) break;

        if (n==MAXCHARS) {
                xlog("god_create_char (svr_god.c): MAXCHARS reached!");
                return 0;
        }

        ch[n]=ch_temp[temp];
        ch[n].pass1=RANDOM(0x3fffffff);
        ch[n].pass2=RANDOM(0x3fffffff);
        ch[n].temp=temp;

        while (1) {
                strcpy(ch[n].name,mkp());
                for (m=1; m<MAXCHARS; m++) {
                        if (m==n) continue;
                        if (!strcmp(ch[n].name,ch[m].name)) break;
                }
                if (m==MAXCHARS) break;
        }
        strcpy(ch[n].reference,ch[n].name);

        sprintf(ch[n].description,"%s is a %s%s%s%s%s. %s%s%s looks somewhat nondescript.",
                ch[n].name,
                (ch[n].kindred&KIN_TEMPLAR) ? "Templar" : "",
                (ch[n].kindred&KIN_HARAKIM) ? "Harakim" : "",
                (ch[n].kindred&KIN_MERCENARY) ? "Mercenary" : "",
                (ch[n].kindred&KIN_SEYAN_DU) ? "Seyan'Du" : "",
                !(ch[n].kindred&(KIN_TEMPLAR|KIN_HARAKIM|KIN_MERCENARY|KIN_SEYAN_DU)) ? "Monster" : "",
                (ch[n].kindred&KIN_MALE) ? "He" : "",
                (ch[n].kindred&KIN_FEMALE) ? "She" : "",
                (ch[n].kindred&KIN_MONSTER) ? "It" : "");

        for (m=0; m<100; m++) ch[n].data[m]=0;
        ch[n].attack_cn=0;
        ch[n].skill_nr=0;
        ch[n].goto_x=0;
        ch[n].use_nr=0;
        ch[n].misc_action=0;
        ch[n].stunned=0;
        ch[n].retry=0;
        ch[n].dir=DX_DOWN;

        for (m=0; m<40; m++) {
                if ((tmp=ch[n].item[m])!=0) {
                        if (withitems) {
                                tmp=god_create_item(tmp);
                                if (!tmp) flag=1;
                                it[tmp].carried=n;
                        } else tmp=0;
                        ch[n].item[m]=tmp;
                }
        }

        for (m=0; m<20; m++) {
                if ((tmp=ch[n].worn[m])!=0) {
                        if (withitems) {
                                tmp=god_create_item(tmp);
                                if (!tmp) flag=1;
                                it[tmp].carried=n;
                        } else tmp=0;
                        ch[n].worn[m]=tmp;
                }
        }

        for (m=0; m<20; m++)
                if (ch[n].spell[m]!=0) ch[n].spell[m]=0;

        if ((tmp=ch[n].citem)!=0) {
                if (withitems) {
                        tmp=god_create_item(tmp);
                        if (!tmp) flag=1;
                        it[tmp].carried=n;
                } else tmp=0;
                ch[n].citem=tmp;
        }

        if (flag) {
                god_destroy_items(n);
                ch[n].used=USE_EMPTY;
                return 0;
        }

        ch[n].a_end=1000000;
        ch[n].a_hp=1000000;
        ch[n].a_mana=1000000;

        do_update_char(n);

        return n;
}

int god_change_pass(int cn,int co,char *pass)
{
	int hash,n;

        if (co<1 || co>=MAXCHARS) {
                do_char_log(cn,0,"Character out of bounds.\n");
                return 0;
        }
	if (!pass || !*pass) {
		if (cn!=co) do_char_log(cn,1,"Removed %s's password.\n",ch[co].name);
		else do_char_log(cn,1,"Removed password.\n");
		chlog(cn,"Removed password");
		ch[co].flags&=~CF_PASSWD;
		bzero(ch[co].passwd,sizeof(ch[co].passwd));
		return 1;
	}
        memcpy(ch[co].passwd,pass,15); ch[co].passwd[15]=0;

	if (cn!=co) do_char_log(cn,1,"Set %s's password to \"%s\".\n",ch[co].name,ch[co].passwd);
	else do_char_log(cn,1,"Set your password to \"%s\".\n",ch[co].passwd);

	for (n=hash=0; n<15 && ch[co].passwd[n]; n++) {
		hash^=(ch[co].passwd[n]<<(n*2));
	}

	chlog(cn,"Set %s's (%d) password to hash %u",ch[co].name,co,hash);
	
	ch[co].flags|=CF_PASSWD;

        return 1;
}

int god_drop_item(int nr,int x,int y)
{
        int m;

        if (!SANEXY(x,y)) return 0;
        m = XY2M(x,y);
        if (map[m].ch || map[m].to_ch || map[m].it || (map[m].flags&(MF_MOVEBLOCK|MF_DEATHTRAP)) || map[m].fsprite) return 0;

        map[m].it=nr;

        it[nr].x=(short)x;
        it[nr].y=(short)y;
        it[nr].carried=0;

        if (it[nr].active) {
                if (it[nr].light[1])
                        do_add_light(x,y,it[nr].light[1]);
        } else {
                if (it[nr].light[0])
                        do_add_light(x,y,it[nr].light[0]);
        }

        return 1;
}

int god_remove_item(int cn,int nr)
{
        int in;

        in=ch[cn].worn[nr];
        if (!in) return 0;

        it[in].x=0;
        it[in].y=0;
        it[in].carried=0;

        ch[cn].worn[nr]=0;

        do_update_char(cn);

        return in;
}

int god_drop_item_fuzzy(int nr,int x,int y)
{
        if (god_drop_item(nr,x,y)) return 1;

        if (can_go(x,y,x+1,y) && god_drop_item(nr,x+1,y)) return 1;
        if (can_go(x,y,x-1,y) && god_drop_item(nr,x-1,y)) return 1;
        if (can_go(x,y,x,y+1) && god_drop_item(nr,x,y+1)) return 1;
        if (can_go(x,y,x,y-1) && god_drop_item(nr,x,y-1)) return 1;

        if (can_go(x,y,x+1,y+1) && god_drop_item(nr,x+1,y+1)) return 1;
        if (can_go(x,y,x+1,y-1) && god_drop_item(nr,x+1,y-1)) return 1;
        if (can_go(x,y,x-1,y+1) && god_drop_item(nr,x-1,y+1)) return 1;
        if (can_go(x,y,x-1,y-1) && god_drop_item(nr,x-1,y-1)) return 1;

        if (can_go(x,y,x+2,y-2) && god_drop_item(nr,x+2,y-2)) return 1;
        if (can_go(x,y,x+2,y-1) && god_drop_item(nr,x+2,y-1)) return 1;
        if (can_go(x,y,x+2,y+0) && god_drop_item(nr,x+2,y+0)) return 1;
        if (can_go(x,y,x+2,y+1) && god_drop_item(nr,x+2,y+1)) return 1;
        if (can_go(x,y,x+2,y+2) && god_drop_item(nr,x+2,y+2)) return 1;
        if (can_go(x,y,x-2,y-2) && god_drop_item(nr,x-2,y-2)) return 1;
        if (can_go(x,y,x-2,y-1) && god_drop_item(nr,x-2,y-1)) return 1;
        if (can_go(x,y,x-2,y+0) && god_drop_item(nr,x-2,y+0)) return 1;
        if (can_go(x,y,x-2,y+1) && god_drop_item(nr,x-2,y+1)) return 1;
        if (can_go(x,y,x-2,y+2) && god_drop_item(nr,x-2,y+2)) return 1;
        if (can_go(x,y,x-1,y+2) && god_drop_item(nr,x-1,y+2)) return 1;
        if (can_go(x,y,x+0,y+2) && god_drop_item(nr,x+0,y+2)) return 1;
        if (can_go(x,y,x+1,y+2) && god_drop_item(nr,x+1,y+2)) return 1;
        if (can_go(x,y,x-1,y-2) && god_drop_item(nr,x-1,y-2)) return 1;
        if (can_go(x,y,x+0,y-2) && god_drop_item(nr,x+0,y-2)) return 1;
        if (can_go(x,y,x+1,y-2) && god_drop_item(nr,x+1,y-2)) return 1;

        return 0;
}

int god_drop_char(int cn,int x,int y)
{
        int m,in;

        if (x<1 || x>MAPX-2 || y<1 || y>MAPY-2) return 0;

        m=x+y*MAPX;
        if (map[m].ch || map[m].to_ch || ((in=map[m].it)!=0 && (it[in].flags&IF_MOVEBLOCK)) || (map[m].flags&MF_MOVEBLOCK) ||
           (map[m].flags&MF_TAVERN) || (map[m].flags&MF_DEATHTRAP)) return 0;

        ch[cn].x=(unsigned short)x;
        ch[cn].y=(unsigned short)y;
        ch[cn].tox=(unsigned short)x;
        ch[cn].toy=(unsigned short)y;

        plr_map_set(cn);

        return 1;
}

int god_drop_char_fuzzy(int nr,int x,int y)
{
        if (god_drop_char(nr,x,y)) return 1;

        if (can_go(x,y,x+1,y) && god_drop_char(nr,x+1,y)) return 1;
        if (can_go(x,y,x-1,y) && god_drop_char(nr,x-1,y)) return 1;
        if (can_go(x,y,x,y+1) && god_drop_char(nr,x,y+1)) return 1;
        if (can_go(x,y,x,y-1) && god_drop_char(nr,x,y-1)) return 1;

        if (can_go(x,y,x+1,y+1) && god_drop_char(nr,x+1,y+1)) return 1;
        if (can_go(x,y,x+1,y-1) && god_drop_char(nr,x+1,y-1)) return 1;
        if (can_go(x,y,x-1,y+1) && god_drop_char(nr,x-1,y+1)) return 1;
        if (can_go(x,y,x-1,y-1) && god_drop_char(nr,x-1,y-1)) return 1;

        if (can_go(x,y,x+2,y-2) && god_drop_char(nr,x+2,y-2)) return 1;
        if (can_go(x,y,x+2,y-1) && god_drop_char(nr,x+2,y-1)) return 1;
        if (can_go(x,y,x+2,y+0) && god_drop_char(nr,x+2,y+0)) return 1;
        if (can_go(x,y,x+2,y+1) && god_drop_char(nr,x+2,y+1)) return 1;
        if (can_go(x,y,x+2,y+2) && god_drop_char(nr,x+2,y+2)) return 1;
        if (can_go(x,y,x-2,y-2) && god_drop_char(nr,x-2,y-2)) return 1;
        if (can_go(x,y,x-2,y-1) && god_drop_char(nr,x-2,y-1)) return 1;
        if (can_go(x,y,x-2,y+0) && god_drop_char(nr,x-2,y+0)) return 1;
        if (can_go(x,y,x-2,y+1) && god_drop_char(nr,x-2,y+1)) return 1;
        if (can_go(x,y,x-2,y+2) && god_drop_char(nr,x-2,y+2)) return 1;
        if (can_go(x,y,x-1,y+2) && god_drop_char(nr,x-1,y+2)) return 1;
        if (can_go(x,y,x+0,y+2) && god_drop_char(nr,x+0,y+2)) return 1;
        if (can_go(x,y,x+1,y+2) && god_drop_char(nr,x+1,y+2)) return 1;
        if (can_go(x,y,x-1,y-2) && god_drop_char(nr,x-1,y-2)) return 1;
        if (can_go(x,y,x+0,y-2) && god_drop_char(nr,x+0,y-2)) return 1;
        if (can_go(x,y,x+1,y-2) && god_drop_char(nr,x+1,y-2)) return 1;

        return 0;
}

int god_drop_char_fuzzy_large(int nr,int x,int y,int xs,int ys)
{
        if (can_go(xs,ys,x,y) && god_drop_char(nr,x,y)) return 1;

        if (can_go(xs,ys,x+1,y) && god_drop_char(nr,x+1,y)) return 1;
        if (can_go(xs,ys,x-1,y) && god_drop_char(nr,x-1,y)) return 1;
        if (can_go(xs,ys,x,y+1) && god_drop_char(nr,x,y+1)) return 1;
        if (can_go(xs,ys,x,y-1) && god_drop_char(nr,x,y-1)) return 1;

        if (can_go(xs,ys,x+1,y+1) && god_drop_char(nr,x+1,y+1)) return 1;
        if (can_go(xs,ys,x+1,y-1) && god_drop_char(nr,x+1,y-1)) return 1;
        if (can_go(xs,ys,x-1,y+1) && god_drop_char(nr,x-1,y+1)) return 1;
        if (can_go(xs,ys,x-1,y-1) && god_drop_char(nr,x-1,y-1)) return 1;

        if (can_go(xs,ys,x+2,y-2) && god_drop_char(nr,x+2,y-2)) return 1;
        if (can_go(xs,ys,x+2,y-1) && god_drop_char(nr,x+2,y-1)) return 1;
        if (can_go(xs,ys,x+2,y+0) && god_drop_char(nr,x+2,y+0)) return 1;
        if (can_go(xs,ys,x+2,y+1) && god_drop_char(nr,x+2,y+1)) return 1;
        if (can_go(xs,ys,x+2,y+2) && god_drop_char(nr,x+2,y+2)) return 1;
        if (can_go(xs,ys,x-2,y-2) && god_drop_char(nr,x-2,y-2)) return 1;
        if (can_go(xs,ys,x-2,y-1) && god_drop_char(nr,x-2,y-1)) return 1;
        if (can_go(xs,ys,x-2,y+0) && god_drop_char(nr,x-2,y+0)) return 1;
        if (can_go(xs,ys,x-2,y+1) && god_drop_char(nr,x-2,y+1)) return 1;
        if (can_go(xs,ys,x-2,y+2) && god_drop_char(nr,x-2,y+2)) return 1;
        if (can_go(xs,ys,x-1,y+2) && god_drop_char(nr,x-1,y+2)) return 1;
        if (can_go(xs,ys,x+0,y+2) && god_drop_char(nr,x+0,y+2)) return 1;
        if (can_go(xs,ys,x+1,y+2) && god_drop_char(nr,x+1,y+2)) return 1;
        if (can_go(xs,ys,x-1,y-2) && god_drop_char(nr,x-1,y-2)) return 1;
        if (can_go(xs,ys,x+0,y-2) && god_drop_char(nr,x+0,y-2)) return 1;
        if (can_go(xs,ys,x+1,y-2) && god_drop_char(nr,x+1,y-2)) return 1;

        return 0;
}

int god_give_char(int in,int cn)
{
        int n;

        if (!IS_SANEITEM(in) || !IS_LIVINGCHAR(cn)) return 0;
        for (n=0; n<40; n++)
                if (!ch[cn].item[n]) break;
        if (n==40) return 0;

        ch[cn].item[n]=in;

        it[in].x=0;
        it[in].y=0;
        it[in].carried=cn;

	do_update_char(cn);

        return 1;
}

int god_take_from_char(int in,int cn)
{
        int n;

        if (ch[cn].citem==in) ch[cn].citem=0;
        else {
                for (n=0; n<40; n++)
                        if (ch[cn].item[n]==in) break;
                if (n<40) ch[cn].item[n]=0;
                else {
                        for (n=0; n<20; n++)
                                if (ch[cn].worn[n]==in) break;
                        if (n==20) return 0;
                        ch[cn].worn[n]=0;
                }
        }

        it[in].x=0;
        it[in].y=0;
        it[in].carried=0;

	do_update_char(cn);

        return 1;
}

int god_transfer_char(int cn,int x,int y)
{
        if (!IS_SANECHAR(cn) || !SANEXY(x,y)) return 0;

        ch[cn].status=0;
        ch[cn].attack_cn=0;
        ch[cn].skill_nr=0;
        ch[cn].goto_x=0;

        plr_map_remove(cn);

        if (god_drop_char_fuzzy_large(cn,x,y,x,y)) return 1;
        if (god_drop_char_fuzzy_large(cn,x+3,y,x,y)) return 1;
        if (god_drop_char_fuzzy_large(cn,x-3,y,x,y)) return 1;
        if (god_drop_char_fuzzy_large(cn,x,y+3,x,y)) return 1;
        if (god_drop_char_fuzzy_large(cn,x,y-3,x,y)) return 1;

        plr_map_set(cn);

        return 0;
}

/* CS, 991128: GOTO n|e|s|w <nnn> */
void god_goto(int cn,int co,char *cx, char *cy)
{
        int xo,yo;

        xo=ch[co].x; yo=ch[co].y;

        if (!*cy) { // GOTO to a character
                int who = dbatoi(cx);
                if (!IS_SANECHAR(who) || ((ch[who].flags&CF_GOD) && !(ch[cn].flags&CF_GOD))) {
                        do_char_log(cn,0,"Bad character: %s!\n", cx);
                        return;
                } else if (god_transfer_char(co,ch[who].x,ch[who].y)) {
                        chlog(cn, "IMP: transferred %s to %s (%s).", ch[co].name,ch[who].name, get_area_m(ch[who].x,ch[who].y,0));
                        if (!(ch[co].flags&CF_INVISIBLE)) {
                                fx_add_effect(12,0,xo,yo,0);
                                fx_add_effect(12,0,ch[co].x,ch[co].y,0);
                        }
                        return;
                }
        } else { // x,y coordinates
                int x, y;

                x = ch[co].x;
                y = ch[co].y;
                if      (!strcasecmp(cx,"n")) x -= atoi(cy);
                else if (!strcasecmp(cx,"e")) y += atoi(cy);
                else if (!strcasecmp(cx,"s")) x += atoi(cy);
                else if (!strcasecmp(cx,"w")) y -= atoi(cy);
                else {
                        x = atoi(cx);
                        y = atoi(cy);
                }
                if (!SANEXY(x,y)) {
                        do_char_log(cn,0,"Bad coordinates(%d %d)\n", x, y);
                        return;
                }
                if (god_transfer_char(co,x,y)) {
                        chlog(cn, "IMP: transferred %s to %d,%d (%s).",ch[co].name,x,y,get_area_m(x,y,0));
                        if (!(ch[co].flags&CF_INVISIBLE)) {
                                fx_add_effect(12,0,xo,yo,0);
                                fx_add_effect(12,0,ch[co].x,ch[co].y,0);
                        }
                        return;
                }
        }
        do_char_log(cn,0,"GOTO failed. Dykstra was right (Elrac will explain this comment if you ask nicely).\n");
        return;
}

void god_info(int cn,int co)
{
        int t;
        /* CS, 991128: Support for different levels of #INFO */
        char cnum_str[20], pos_str[30], temp_str[20], need_str[20];
        int pos_x, pos_y;
        int pts;

        if (!IS_SANECHAR(co)) {
                do_char_log(cn,0,"There's no such character.\n");
                return;
        }

        if (IS_SANENPC(co) && !(IS_GOD(cn)|IS_IMP(cn)|IS_USURP(cn))) {
                do_char_log(cn,0,"Access denied.\n");
                return;
        }

        if ((ch[co].flags&CF_GOD) && !(ch[cn].flags&CF_GOD)) {
                do_char_log(cn,0,"Access denied.\n");
                return;
        }

        char_info(cn,co);
        /* CS, 991127: No position for invis Imps, no char num to staff */
        if (IS_IMP(cn)||IS_USURP(cn)) sprintf(cnum_str, " (%d)", co); else cnum_str[0] = '\0';
        pos_x = ch[co].x; pos_y = ch[co].y;
        if (!IS_IMP(cn) && !IS_USURP(cn) && ((ch[co].flags&(CF_INVISIBLE|CF_NOWHO)) && invis_level(co) > invis_level(cn))) pos_x = pos_y = 0;
        if (pos_x != 0 || pos_y != 0) sprintf(pos_str, " Pos=%d,%d.", pos_x, pos_y); else pos_str[0] = '\0';
        /* CS, 991127: Display exp/exp to next level or template number */
        pts = ch[co].points_tot;
        strcpy(need_str, int2str(points_tolevel(pts)));
        if (IS_PLAYER(co)) {
                do_char_log(cn,2,"%s %s%s%s Pts/need=%s/%s.\n",
                            who_rank_name[points2rank(pts)],
                            ch[co].name,
                            cnum_str,pos_str,
                            int2str(pts), need_str);
        } else {
                if (IS_IMP(cn) || IS_USURP(cn)) sprintf(temp_str, " Temp=%d", ch[co].temp); else temp_str[0] = '\0';
                do_char_log(cn,2,"%s %s%s%s%s.\n",
                            who_rank_name[points2rank(pts)],
                            ch[co].name,
                            cnum_str,pos_str,temp_str);
        }
        do_char_log(cn,2,"HP=%d/%d, End=%d/%d, Mana=%d/%d.\n",
                    ch[co].a_hp/1000, ch[co].hp[5],
                    ch[co].a_end/1000,ch[co].end[5],
                    ch[co].a_mana/1000,ch[co].mana[5]);
        do_char_log(cn,2,"Speed=%d. Gold=%d.%02dG (%d.%02dG).\n",
                    ch[co].speed,
                    ch[co].gold/100,ch[co].gold%100,
                    ch[co].data[13]/100,ch[co].data[13]%100);
        if (IS_PLAYER(co) && IS_PURPLE(co) && ch[co].data[CHD_ATTACKTIME]) {
                if (IS_IMP(cn) && IS_SANEPLAYER(ch[co].data[CHD_ATTACKVICT])) {
                        do_char_log(cn,0,"Last PvP attack: %s, against %s.\n",
                                    ago_string(globs->ticker - ch[co].data[CHD_ATTACKTIME]),
                                    ch[ch[co].data[CHD_ATTACKVICT]].name);
                } else {
                        do_char_log(cn,0,"Last PvP attack: %s.\n",
                                    ago_string(globs->ticker - ch[co].data[CHD_ATTACKTIME]));
                }
        }
        if (IS_IMP(cn) || IS_USURP(cn)) {
                if (IS_PLAYER(co)) {
                        do_char_log(cn,3,"Killed %d NPCs below rank, %d NPCs at rank, %d NPCs above rank.\n",
                                ch[co].data[23],ch[co].data[24],ch[co].data[25]);
                        do_char_log(cn,3,"Killed %d players outside arena, killed %d shopkeepers.\n",
                                ch[co].data[29],ch[co].data[40]);
                        do_char_log(cn,3,"BS: Killed %d NPCs below rank, %d NPCs at rank, %d NPCs above rank, %d candles returned.\n",
                                ch[co].data[26],ch[co].data[27],ch[co].data[28],ch[co].data[43]);
                }
                do_char_log(cn,3,"Armor=%d, Weapon=%d. Alignment=%d.\n",ch[co].armor,ch[co].weapon,ch[co].alignment);
                do_char_log(cn,3,"Group=%d (%d), Single Awake=%d, Spells=%d.\n",ch[co].data[42],group_active(co),ch[co].data[92],ch[co].data[96]);
                do_char_log(cn,3,"Luck=%d, Gethit_Dam=%d.\n",ch[co].luck,ch[co].gethit_dam);
		do_char_log(cn,3,"Current Online Time: %dd %dh %dm %ds, Total Online Time: %dd %dh %dm %ds.\n",
			ch[co].current_online_time/(TICKS*60*60*24),
			ch[co].current_online_time/(TICKS*60*60)%24,
			ch[co].current_online_time/(TICKS*60)%60,
			ch[co].current_online_time/(TICKS)%60,
			ch[co].total_online_time/(TICKS*60*60*24),
			ch[co].total_online_time/(TICKS*60*60)%24,
			ch[co].total_online_time/(TICKS*60)%60,
			ch[co].total_online_time/(TICKS)%60);
			
                if (IS_SANENPC(co) && ch[co].data[64]) {
                        t=ch[co].data[64]-globs->ticker;
                        t/=TICKS;
                        do_char_log(cn,3,"Will self destruct in %dm %ds.\n",t/60,t%60);
                }
        }
        return;
}

void god_iinfo(int cn,int in)
{
        if (!IS_SANEITEM(in)) {
                do_char_log(cn,0,"Argument out of bounds.\n");
                return;
        }
        if (!IS_USEDITEM(in)) {
                do_char_log(cn,0,"There's no such item.\n");
                return;
        }

        item_info(cn,in,0);
        do_char_log(cn,1,"Owner: %s (%d), Position %d,%d.\n",
                ch[it[in].carried].name,it[in].carried,it[in].x,it[in].y);
        return;
}

void god_tinfo(int cn,int temp)
{
        int in;

        if (!IS_SANEITEMPLATE(temp) || !it_temp[temp].used) {
                do_char_log(cn,0,"There's no such item.\n");
                return;
        }

        for (in=1; in<MAXITEM; in++) {
                if (it[in].used==USE_EMPTY) continue;
                if (it[in].temp==temp) break;
        }

        if (in==MAXITEM) {
                do_char_log(cn,1,"No %s is in the game.\n",it_temp[temp].name);
                return;
        }

        item_info(cn,in,0);
        do_char_log(cn,1,"Owner: %s (%d), Position %d,%d (%d).\n",
                ch[it[in].carried].name,it[in].carried,it[in].x,it[in].y,in);
}

void god_unique(int cn)
{
        static int unique[60]={
                280,281,282,283,284,285,286,287,288,289,290,291,292,525,526,
                527,528,529,530,531,532,533,534,535,536,537,538,539,540,541,
                542,543,544,545,546,547,548,549,550,551,552,553,554,555,556,
                572,573,574,575,576,577,578,579,580,581,582,583,584,585,586};
        int owner[60];
        int n,in;

        for (n=0; n<60; n++) owner[n]=0;

        for (in=1; in<MAXITEM; in++) {
                if (it[in].used==USE_EMPTY) continue;
                for (n=0; n<60; n++) {
                        if (it[in].temp==unique[n]) owner[n]=it[in].carried;
                }
        }

        for (n=0; n<60; n++) {
                do_char_log(cn,2,"%-25.25s: %.10s (%d)\n",
                        it_temp[unique[n]].name,ch[owner[n]].name,owner[n]);
        }
}

char *int2str(int val)
{
        static char buf[256];

        if (val<99*1000) sprintf(buf,"%d",val);
        else if (val<99*1000*1000) sprintf(buf,"%dK",val/1000);
        else sprintf(buf,"%dM",val/1000000);

        return buf;
}

void god_who(int cn)
{
        int n, players, font,showarea;

        players = 0;
        do_char_log(cn,3,"-----------------------------------------------\n");
        for (n=1; n<MAXCHARS; n++) {
                if (!IS_ACTIVECHAR(n)) {
                        continue;
                } else if (!IS_PLAYER(n)) {
                        if (!IS_USURP(n)) continue;
                        if (! (IS_GOD(cn)||IS_IMP(cn)) ) continue;
                        font = 3; // Usurped mobs are blue for imps
                } else if (IS_INVISIBLE(n)) {
                        if (invis_level(cn)<invis_level(n)) continue;
                        font = 0; // Invisible chars are red for highers
                } else if (ch[n].flags&CF_NOWHO) {
                        if (!(ch[cn].flags&(CF_IMP|CF_GOD))) continue;
                        // only imps below this point
                        font = 3; // NOWHO'd chars are blue for imps
                } else if (IS_STAFF(n) || IS_GOD(n)) {
                        // staff and gods are green for everyone
                        font = 2;
                } else {
                        font = 1; // all others yellow
                }
                players++;

                showarea=1;
                if ((ch[n].flags&CF_GOD) && !(ch[cn].flags&CF_GOD)) showarea=0;
                if ((ch[n].kindred&KIN_PURPLE) && !(ch[cn].flags&(CF_GOD|CF_IMP|CF_USURP))) showarea=0;

                do_char_log(cn,font,"%4d: %-10.10s%c%c%c %-8.8s %.18s\n",
                                n,ch[n].name,
                                IS_PURPLE(n) ? '*' : ' ',
                                (ch[n].flags&CF_POH) ? '+' : ' ',
                                (ch[n].flags&CF_POH_LEADER) ? '+' : ' ',
                                int2str(ch[n].points_tot),
                                !showarea ? "--------" : get_area(n,0));
        }
        /* list player's GC and thralls, if any */
        for (n=1; n<MAXCHARS; n++) {
                if ((ch[n].flags&(CF_PLAYER))) continue;
                if (ch[n].data[63] != cn) continue;
                do_char_log(cn,3,"%.5s %-10.10s%c%c%c %.23s\n",
                        who_rank_name[points2rank(ch[n].points_tot)],
                        ch[n].name,
                        IS_PURPLE(n) ? '*' : ' ',
                        (ch[n].flags&CF_POH) ? '+' : ' ',
                        (ch[n].flags&CF_POH_LEADER) ? '+' : ' ',
                        get_area(n,0));
        }
        do_char_log(cn,3,"-----------------------------------------------\n");
        do_char_log(cn,1,"%3d player%s online.\n",
                    players, (players > 1) ? "s" : "");
}

void god_implist(int cn)
{
        int n,players,showarea;

        players = 0;
        do_char_log(cn,3,"-----------------------------------------------\n");
        for (n=1; n<MAXCHARS; n++) {
		if (!IS_USEDCHAR(n)) continue;
                if (!IS_PLAYER(n)) continue;
                if (!IS_IMP(n)) continue;
                players++;

                showarea=1;
                if ((ch[n].flags&CF_GOD) && !(ch[cn].flags&CF_GOD)) showarea=0;
                if ((ch[n].kindred&KIN_PURPLE) && !(ch[cn].flags&(CF_GOD|CF_IMP|CF_USURP))) showarea=0;

                do_char_log(cn,1,"%4d: %-10.10s%c%c%c %-8.8s %.18s\n",
                                n,ch[n].name,
                                IS_PURPLE(n) ? '*' : ' ',
                                (ch[n].flags&CF_POH) ? '+' : ' ',
                                (ch[n].flags&CF_POH_LEADER) ? '+' : ' ',
                                int2str(ch[n].points_tot),
                                !showarea ? "--------" : get_area(n,0));
        }
        do_char_log(cn,3,"-----------------------------------------------\n");
        do_char_log(cn,1,"%3d imp%s.\n",
                    players, (players > 1) ? "s" : "");
}

void user_who(int cn)
{
        int n, players, gc, font,showarea;

        do_char_log(cn,1,"-----------------------------------------------\n");
        players = 0;
        /* list players */
        for (n=1; n<MAXCHARS; n++) {
                if (!(ch[n].flags&(CF_PLAYER))) continue;
                if (ch[n].used!=USE_ACTIVE || (ch[n].flags&(CF_INVISIBLE|CF_NOWHO))) continue;
                players++;
                /* color staff and gods green */
                font = (IS_STAFF(n) || IS_GOD(n)) ? 2 : 1;

                showarea=1;
                if ((ch[n].flags&CF_GOD) && !(ch[cn].flags&CF_GOD)) showarea=0;
                if ((ch[n].kindred&KIN_PURPLE) && !(ch[cn].flags&(CF_GOD|CF_IMP|CF_USURP))) showarea=0;

                do_char_log(cn,font,"%.5s %-10.10s%c%c%c %.23s\n",
                        who_rank_name[points2rank(ch[n].points_tot)],
                        ch[n].name,
                        IS_PURPLE(n) ? '*' : ' ',
                        (ch[n].flags&CF_POH) ? '+' : ' ',
                        (ch[n].flags&CF_POH_LEADER) ? '+' : ' ',
                        !showarea ? "--------" : get_area(n,0));
        }
        if ((gc=ch[cn].data[CHD_COMPANION]) && IS_SANECHAR(gc)) {
                do_char_log(cn,3,"%4d: %-10.10s@ %-8.8s %.20s\n",
                                gc,ch[gc].name,
                                int2str(ch[gc].points_tot),
                        get_area(gc,0));
        }
        do_char_log(cn,1,"-----------------------------------------------\n");
        do_char_log(cn,1,"%3d player%s online.\n",
                    players, (players > 1) ? "s" : "");
}

void god_top(int cn)
{
        do_char_log(cn,1,"Only partially implemented.\n");

        do_char_log(cn,1,"Today is the %d%s%s%s%s day of the Year %d. It is %d:%02d Astonian Standard Time.\n",
                globs->mdday,
                (globs->mdday==1 ? "st" : ""),
                (globs->mdday==2 ? "nd" : ""),
                (globs->mdday==3 ? "rd" : ""),
                (globs->mdday>3 ? "th" : ""),
                globs->mdyear,globs->mdtime/3600,(globs->mdtime/60)%60);

        if ((globs->mdday%28)+1==1) do_char_log(cn,1,"New Moon tonight!\n");
        else if ((globs->mdday%28)+1<14) do_char_log(cn,1,"The Moon is growing.\n");
        else if ((globs->mdday%28)+1==15) do_char_log(cn,1,"Full Moon tonight!\n");
        else do_char_log(cn,1,"The moon is dwindling.\n");
}

void god_create(int cn,int x)
{
        int in;

        if (x == 0) {
                do_char_log(cn,0,"No such item.\n");
                return;
        } else if (!IS_SANEITEM(x)) {
                do_char_log(cn,0,"Bad item number: %d.\n", x);
                return;
        }
        if (!(it_temp[x].flags&IF_TAKE)) {
                do_char_log(cn,0,"item is not take-able.\n");
                return;
        }
        in=god_create_item(x);
        if (in==0) {
                do_char_log(cn,0,"god_create_item() failed.\n");
                return;
        }
        if (!god_give_char(in,cn)) {
                do_char_log(cn,0,"Your inventory is full!\n");
                return;
        }
        do_char_log(cn,1,"created one %s.\n", it[in].name);
        chlog(cn, "IMP: created one %s.", it[in].name);
        return;
}

int find_next_char(int startcn, char *spec1, char *spec2)
{
        int n;
        int rank;

        if (isdigit(*spec2)) {
                rank = atoi(spec2);
        } else {
                rank = -1;
        }
        for (n=startcn+1; n<MAXCHARS; n++) {
                if (!IS_USEDCHAR(n)) continue;
                if (!strstr(ch[n].name, spec1)) continue;
                if (rank == -1) {
                        if (strstr(ch[n].name, spec2)) return n;
                } else {
                        if (points2rank(ch[n].points_tot) == rank) return n;
                }
        }
        return 0;
}

int invis(int looker,int target)
{
	if (!(ch[target].flags&CF_INVISIBLE)) return 0;
	if (invis_level(looker)>=invis_level(target)) return 0;
	
	return 1;
}


void god_summon(int cn, char *spec1, char *spec2, char *spec3)
{
        int co;
        int x, y,xo,yo;
        int which = 1, count = 0;

        if (!*spec1) {          // no arguments
                do_char_log(cn, 0, "summon whom?\n");
                return;
        }
        if (!*spec2) {  // only one arg
                co = dbatoi(spec1);
                if (!IS_SANEUSEDCHAR(co) || invis(cn,co)) {     // bad character number
			do_char_log(cn,0,"No such character.\n");
			return;
                }
                if (ch[co].flags & CF_BODY) {   // dead character
                        do_char_log(cn,0,"Character recently deceased; try %d.\n",
                                    ch[co].data[CHD_CORPSEOWNER]);
			return;
                }
                if (co == cn) {                 // self
                        do_char_log(cn,0,"You can't summon yourself!\n");
                        return;
                }
        } else {                // at least 2 args
                co = 0;
                if (isdigit(*spec2)) {
                        if (atoi(spec2) < 0 || atoi(spec2) >= RANKS) {
                                do_char_log(cn, 0, "No such rank: %s\n", spec2);
                                return;
                        }
                } else {
                        titlecase_str(spec2);
                }
                titlecase_str(spec1);
                if (*spec3) {   // 3 args
                        which = max(atoi(spec3),1);
                }
                while (count < which) {
                        co = find_next_char(co, spec1, spec2);
                        if (co == 0) break;
                        if (co == cn) continue;                 // ignore self
                        if (ch[co].flags & CF_BODY) continue;   // ignore bodies
                        if (IS_PLAYER(co) && !IS_ACTIVECHAR(co)) continue; // ignore sleeping players
			if (invis(cn,co)) continue;	// ignore whom we cant see
                        count++;
                }
                if (co == 0) {
                        if (!isdigit(*spec2)) {
                                if (count == 0) {
                                do_char_log(cn, 0, "Couldn't find a %s %s.\n", spec1, spec2);
                        } else {
                                        do_char_log(cn, 0, "Only found %d %s %s.\n", count, spec1, spec2);
                                }
                        } else {
                                if (count == 0) {
                                do_char_log(cn, 0, "Couldn't find a %s %s.\n", spec1, rank_name[atoi(spec2)]);
                                } else {
                                        do_char_log(cn, 0, "Only found %d %s %s.\n", count, spec1, rank_name[atoi(spec2)]);
                                }
                        }
                        return;
                }
        }

        x = ch[cn].x;
        y = ch[cn].y;
        /* try to transfer char to in front of summoner */
        switch (ch[cn].dir) {
                case DX_RIGHT:          x++; break;
                case DX_RIGHTUP:        x++; y--; break;
                case DX_UP:             y--; break;
                case DX_LEFTUP:         x--; y--; break;
                case DX_LEFT:           x--; break;
                case DX_LEFTDOWN:       x--; y++; break;
                case DX_DOWN:           y++; break;
                case DX_RIGHTDOWN:      y++; x++; break;
        }

        xo=ch[co].x;
        yo=ch[co].y;

        if (!god_transfer_char(co, x, y))  {
                do_char_log(cn,0,"god_transfer_char() failed.\n");

                fx_add_effect(12,0,xo,yo,0);
                fx_add_effect(12,0,ch[co].x,ch[co].y,0);

                return;
        }
        do_char_log(cn,1,"%s was summoned.\n", ch[co].name);
        chlog(cn,"IMP: summoned %s.", ch[co].name);
        return;
}

/*   creates a mirror-enemy in front of the target (*spec1) with the skills of target
     with a skillbonus of (*spec2) , no equipment, same spells active              */

void god_mirror(int cn,char *spec1, char *spec2)
{
    int cc,co,i,bonus=0;

        co  = dbatoi(spec1);
	if (!*spec1) {        			// no arguments
                do_char_log(cn, 0, "create mirror-enemy of whom?\n");
                return;
        }
        if (!*spec2) {          		// only one arg
		bonus=0;
                if (!IS_SANEUSEDCHAR(co)) {     // bad character number
            	    do_char_log(cn,0,"No such character.\n");
            	    return;
                }
                if (ch[co].flags & CF_BODY) {   // dead character
                    do_char_log(cn,0,"Character recently deceased. \n");
            	    return;
                }
    		if (!IS_PLAYER(co)) {		// only mirror players (should we allow usurps?)
            	    do_char_log(cn, 0, "%s is not a player, and you can't mirror monsters!\n",
                    ch[co].name);
            	    return;
    		}
                if (co == cn) {                 // self
                    do_char_log(cn,0,"You want an enemy? Here it is...!\n");
		}
	}
	else 	if (isdigit(*spec2))	bonus=atoi(spec2);;;	// 2 arguments

//	cc=pop_create_char(968,0);
        if (!(cc = god_create_char(968, 0))) {
                do_char_log(cn,0,"god_create_char() failed.\n");
                return;
	}	
	
	
				strcpy(ch[cc].name,      ch[co].name);
				ch[cc].sprite		=ch[co].sprite;
	for (i=0;i<5;i++)	ch[cc].attrib[i][0]	=ch[co].attrib[i][0];
				ch[cc].hp[0]		=ch[co].hp[0];
				ch[cc].end[0]		=ch[co].end[0];
				ch[cc].mana[0]		=ch[co].mana[0];
	for (i=1;i<35;i++)	ch[cc].skill[i][0]	=ch[co].skill[i][0];

	if 	(ch[co].kindred&(KIN_TEMPLAR | KIN_ARCHTEMPLAR | KIN_SEYAN_DU))  	// TH -> hand2hand (str,str,agi)
		    ch[co].skill[0][0] =ch[co].skill[6][0] + bonus + (ch[co].attrib[4][0]-ch[co].attrib[0][0])/5;
	else if (ch[co].kindred&(KIN_HARAKIM | KIN_ARCHHARAKIM )) 			// Dag-> hand2hand (wil,agi,int)
		    ch[co].skill[0][0] =ch[co].skill[2][0] + bonus + (ch[co].attrib[2][0]-ch[co].attrib[4][0])/5;
	else if (ch[co].kindred&(KIN_MERCENARY | KIN_SORCERER | KIN_WARRIOR )) 		// Swo-> hand2hand (wil,agi,str)
		    ch[co].skill[0][0] =ch[co].skill[3][0] + bonus ;
		
	ch[co].weapon=ch[cn].weapon;
	ch[co].armor =ch[cn].armor;
	do_update_char(cc);
	
    god_drop_char_fuzzy(cc,ch[cn].x,ch[cn].y);   // to be replaced later by: _fuzzy(cc,ch[co].x,ch[co].y);
//        if (!god_transfer_char(cc, ch[cn].x, ch[cn].y))  {
//                do_char_log(cn,0,"god_transfer_char() failed.\n");
//                return;
//        }


    npc_add_enemy(cc,co,1)    ;
    do_char_log(cn,0,"Mirror of %s active (bonus: %s) \n",spec1,spec2);
    chlog(cn,"IMP: created mirror against %s.", ch[co].name);
    return;
}	


int god_thrall(int cn, char *spec1, char *spec2)
{
        int co,ct,x,y,n,in;

        if (!*spec1) {          // no arguments
                do_char_log(cn, 0, "enthrall whom?\n");
                return 0;
        }
        if (!*spec2) {          // only one arg
                co = dbatoi(spec1);
                if (!IS_SANEUSEDCHAR(co)) {     // bad character number
                do_char_log(cn,0,"No such character.\n");
                return 0;
                }
                if (ch[co].flags & CF_BODY) {   // dead character
                        do_char_log(cn,0,"Character recently deceased; try %d.\n",
                                    ch[co].data[CHD_CORPSEOWNER]);
                return 0;
                }
                if (co == cn) {                 // self
                        do_char_log(cn,0,"You can't enthrall yourself!\n");
                        return 0;
                }
        } else {                // at least 2 args
                co = 0;
                if (isdigit(*spec2)) {
                        if (atoi(spec2) < 0 || atoi(spec2) >= RANKS) {
                                do_char_log(cn, 0, "No such rank: %s\n", spec2);
                                return 0;
                        }
                } else {
                        titlecase_str(spec2);
                }
                titlecase_str(spec1);
                while (1) {
                        co = find_next_char(co, spec1, spec2);
                        if (co == 0) break;
                        if (co == cn) continue;                 // ignore self
                        if (ch[co].flags & CF_BODY) continue;   // ignore bodies
                        break;
                }
                if (co == 0) {
                        if (!isdigit(*spec2)) {
                                do_char_log(cn, 0, "Couldn't find a %s %s.\n", spec1, spec2);
                        } else {
                                do_char_log(cn, 0, "Couldn't find a %s %s.\n", spec1, rank_name[atoi(spec2)]);
                        }
                        return 0;
                }
        }

        if (IS_PLAYER(co)) {
                do_char_log(cn, 0, "%s is a player, and you can't enthrall players!\n",
                            ch[co].name);
                return 0;
        }

	if (IS_COMPANION(co)) {
		do_char_log(cn, 0, "%s is a companion/thrall, and you can't enthrall them!\n",
                            ch[co].name);
                return 0;
	}

        x = ch[cn].x;
        y = ch[cn].y;
        /* try to transfer char to in front of summoner */
        switch (ch[cn].dir) {
                case DX_RIGHT:          x++; break;
                case DX_RIGHTUP:        x++; y--; break;
                case DX_UP:             y--; break;
                case DX_LEFTUP:         x--; y--; break;
                case DX_LEFT:           x--; break;
                case DX_LEFTDOWN:       x--; y++; break;
                case DX_DOWN:           y++; break;
                case DX_RIGHTDOWN:      y++; x++; break;
        }

        if (!(ct = god_create_char(ch[co].temp, 1))) {
                do_char_log(cn,0,"god_create_char() failed.\n");
                return 0;
        }

        strcpy(ch[ct].name,ch[co].name);
        strcpy(ch[ct].reference,ch[co].reference);
        strcpy(ch[ct].description,ch[co].description);

        /* tricky: make thrall act like a ghost companion */
        ch[ct].temp = CT_COMPANION;
        ch[ct].data[64] = globs->ticker + 7 * 24 * 3600 * TICKS; // die in one week if not otherwise
        ch[ct].data[42]=65536+cn;                       // set group
        ch[ct].data[59]=65536+cn;                       // protect all other members of this group

        /* make thrall harmless */
        ch[ct].data[24] = 0;    // do not interfere in fights
        ch[ct].data[36] = 0;    // no walking around
        ch[ct].data[43] = 0;    // don't attack anyone
        ch[ct].data[80] = 0;    // no enemies
        ch[ct].data[63] = cn;   // obey and protect enthraller

        ch[ct].flags|=CF_SHUTUP|CF_THRALL;

	for (n=0; n<20; n++) {
		if ((in=ch[ct].worn[n]) && (it[in].flags&IF_LABYDESTROY)) {
			it[in].used=0;
			ch[ct].worn[n]=0;
		}
	}

	for (n=0; n<40; n++) {
		if ((in=ch[ct].item[n]) && (it[in].flags&IF_LABYDESTROY)) {
			it[in].used=0;
			ch[ct].item[n]=0;
		}
	}

	if ((in=ch[ct].citem) && (it[in].flags&IF_LABYDESTROY)) {
		it[in].used=0;
		ch[ct].citem=0;
	}

        if (!god_drop_char_fuzzy(ct, x, y))  {
                do_char_log(cn,0,"god_drop_char_fuzzy() called from god_thrall() failed.\n");
                god_destroy_items(ct);
                ch[ct].used=USE_EMPTY;
                return 0;
        }
        do_char_log(cn,1,"%s was enthralled.\n", ch[co].name);
        chlog(cn,"IMP: enthralled %s.", ch[co].name);
        return ct;
}


void god_tavern(int cn)
{
        // DB: tavern does nothing to NPCs... But better be safe than sorry ;-)
        if (IS_USURP(cn)) {
                do_char_log(cn,0,"Not with NPCs!\n");
                return;
        }
        if (IS_BUILDING(cn)) {
                god_build(cn,0);
        }
        ch[cn].tavern_x=ch[cn].x;
        ch[cn].tavern_y=ch[cn].y;
        chlog(cn,"Entered tavern");
        plr_logout(cn,ch[cn].player,LO_TAVERN);
}

int god_build_start(int cn)
{
        int co, n, in;

        if ((co=ch[cn].data[CHD_COMPANION])) {
                do_char_log(cn, 0, "Get rid of %s first.\n",
                            ch[co].name);
                return 0;
        }
        /* Create char to hold inventory */
        co = god_create_char(1, 0);
        if (!co) {
                do_char_log(cn, 0, "Could not create item holder for you.\n");
                return 0;
        }
        ch[cn].data[CHD_COMPANION] = co;

        /* Transfer inventory */
        for (n=0; n<40; n++) {
                in = ch[cn].item[n];
                if (in) {
                        ch[co].item[n] = in;
                        ch[cn].item[n] = 0;
                        it[in].carried = co;
                }
        }
        ch[co].citem = ch[cn].citem;
        ch[cn].citem = 0;

        sprintf(ch[co].name,"%s's holder",ch[cn].name);
        god_drop_char(co,10,10);

        /* Set build mode flag */
        ch[cn].flags |= CF_BUILDMODE;
	do_update_char(cn);

        return 1;
}

void god_build_stop(int cn)
{
        int co, n, in;

        /* Empty builder's inventory */
        for (n=0; n<40; n++)
                ch[cn].item[n]=0;
        ch[cn].citem=0;

        /* Reset build mode */
        ch[cn].flags&=~(CF_BUILDMODE);
        ch[cn].misc_action=DR_IDLE;
        do_char_log(cn, 3, "Now out of build mode.\n");

        /* Retrieve inventory from item holder */
        co = ch[cn].data[CHD_COMPANION];
        if (!co) {
                do_char_log(cn, 0, "Could not find your item holder!\n");
                return;
        }

        /* Transfer inventory */
        for (n=0; n<40; n++) {
                in = ch[co].item[n];
                if (in) {
                        ch[cn].item[n] = in;
                        ch[co].item[n] = 0;
                        it[in].carried = cn;
                }
        }
        ch[cn].citem = ch[co].citem;
        ch[co].citem = 0;

        /* Destroy item holder */
        plr_map_remove(co);
        ch[co].used = USE_EMPTY;
        ch[cn].data[CHD_COMPANION] = 0;

	do_update_char(cn);
}

/* the original hand-made build sets (kept as data for the build pages) */
static void build_set(unsigned int *BI,int x)
{
        int n,m;

                m=0;
        switch (x) {
        case 0:
                        BI[m++]=0x40000000|MF_MOVEBLOCK;
                        BI[m++]=0x40000000|MF_SIGHTBLOCK;
                        BI[m++]=0x40000000|MF_INDOORS;
                        BI[m++]=0x40000000|MF_ARENA;
                        BI[m++]=0x40000000|MF_NOMONST;
                        BI[m++]=0x40000000|MF_BANK;
                        BI[m++]=0x40000000|MF_TAVERN;
                        BI[m++]=0x40000000|MF_NOMAGIC;
                        BI[m++]=0x40000000|MF_DEATHTRAP;
                        BI[m++]=0x40000000|MF_UWATER;
                        BI[m++]=0x40000000|MF_NOLAG;
                        BI[m++]=0x40000000|MF_NOFIGHT;
                        BI[m++]=0x40000000|MF_NOEXPIRE;

                        BI[m++]=0x20000000|SPR_TUNDRA_GROUND;
                        BI[m++]=0x20000000|SPR_DESERT_GROUND;
                        BI[m++]=0x20000000|SPR_GROUND1;
                        BI[m++]=0x20000000|SPR_WOOD_GROUND;
                        BI[m++]=0x20000000|SPR_TAVERN_GROUND;
                        BI[m++]=0x20000000|SPR_STONE_GROUND1;
                        BI[m++]=0x20000000|SPR_STONE_GROUND2;
                        BI[m++]=0x20000000|1100;
                        BI[m++]=0x20000000|1099;
                        BI[m++]=0x20000000|1109;
                        BI[m++]=0x20000000|1118;
                        BI[m++]=0x20000000|1141;
                        BI[m++]=0x20000000|1158;
                        BI[m++]=0x20000000|1145;
                        BI[m++]=0x20000000|1014;
                        BI[m++]=0x20000000|1003;
                        BI[m++]=0x20000000|1005;
                        BI[m++]=0x20000000|1006;
                        BI[m++]=0x20000000|1007;
                        BI[m++]=0x20000000|402;
                        BI[m++]=0x20000000|500;
                        BI[m++]=0x20000000|558;
                        BI[m++]=0x20000000|596;
                break;
        case 1:
                        BI[m++]=0x20000000|520;
                        BI[m++]=0x20000000|521;
                        BI[m++]=0x20000000|522;
                        BI[m++]=0x20000000|523;
                        BI[m++]=0x20000000|524;
                        BI[m++]=0x20000000|525;
                        BI[m++]=0x20000000|526;
                        BI[m++]=0x20000000|527;
                        BI[m++]=0x20000000|528;
                        BI[m++]=0x20000000|529;
                        BI[m++]=0x20000000|530;
                        BI[m++]=0x20000000|531;
                        BI[m++]=0x20000000|532;
                        BI[m++]=0x20000000|533;
                        BI[m++]=0x20000000|534;
                        BI[m++]=0x20000000|535;
                        BI[m++]=0x20000000|536;
                        BI[m++]=0x20000000|537;
                        BI[m++]=0x20000000|538;
                        BI[m++]=0x20000000|539;
                        BI[m++]=0x20000000|540;
                        BI[m++]=0x20000000|541;
                break;
        case 2:
                        BI[m++]=0x20000000|542;
                        BI[m++]=0x20000000|543;
                        BI[m++]=0x20000000|544;
                        BI[m++]=0x20000000|545;
                        BI[m++]=0x20000000|546;
                        BI[m++]=0x20000000|547;
                        BI[m++]=0x20000000|548;
                        BI[m++]=0x20000000|549;
                        BI[m++]=0x20000000|550;
                        BI[m++]=0x20000000|551;
                        BI[m++]=0x20000000|552;
                        BI[m++]=0x20000000|553;
                        BI[m++]=0x20000000|554;
                break;
        case 3:
                        BI[m++]=0x20000000|130;
                        BI[m++]=0x20000000|131;
                        BI[m++]=0x20000000|132;
                        BI[m++]=0x20000000|133;
                        BI[m++]=0x20000000|134;
                        BI[m++]=0x20000000|135;
                        BI[m++]=0x20000000|136;
                        BI[m++]=0x20000000|137;
                        BI[m++]=0x20000000|138;
                        BI[m++]=0x20000000|139;
                        BI[m++]=0x20000000|140;
                        BI[m++]=0x20000000|141;
                        BI[m++]=0x20000000|142;
                        BI[m++]=0x20000000|143;
                        BI[m++]=0x20000000|144;
                        BI[m++]=0x20000000|145;
                break;
        case 4:
                        BI[m++]=0x20000000|170;
                        BI[m++]=0x20000000|171;
                        BI[m++]=0x20000000|172;
                        BI[m++]=0x20000000|173;
                        BI[m++]=0x20000000|174;
                        BI[m++]=0x20000000|175;
                break;
        case 331:
                        BI[m++]=0x40000000|MF_INDOORS;
                        BI[m++]=0x20000000|116;
                        BI[m++]=0x20000000|117;
                        BI[m++]=0x20000000|118;

                        BI[m++]=0x20000000|704;
                        /*BI[m++]=0x20000000|705;
                        BI[m++]=0x20000000|706;
                        BI[m++]=0x20000000|707;
                        BI[m++]=0x20000000|708;
                        BI[m++]=0x20000000|709;
                        BI[m++]=0x20000000|710;
                        BI[m++]=0x20000000|711;
                        BI[m++]=0x20000000|712;
                        BI[m++]=0x20000000|713;
                        BI[m++]=0x20000000|714;
                        BI[m++]=0x20000000|715;
                        BI[m++]=0x20000000|716;
                        BI[m++]=0x20000000|717;
                        BI[m++]=0x20000000|718;
                        BI[m++]=0x20000000|719;
                        BI[m++]=0x20000000|720;
                        BI[m++]=0x20000000|721;
                        BI[m++]=0x20000000|722;
                        BI[m++]=0x20000000|723;
                        BI[m++]=0x20000000|724;
                        BI[m++]=0x20000000|725;
                        BI[m++]=0x20000000|726;
                        BI[m++]=0x20000000|727;
                        BI[m++]=0x20000000|728;*/
                break;
        case 700:       // black stronghold
                BI[m++]=0x40000000|MF_INDOORS;
                BI[m++]=0x20000000|950;
                BI[m++]=0x20000000|959;
                BI[m++]=0x20000000|16652;
                BI[m++]=0x20000000|16653;
                BI[m++]=0x20000000|16654;
                BI[m++]=0x20000000|16655;
                break;
        case 701:
                for (n=0; n<40; n++)
                        BI[m++]=0x20000000|(n+16430);
                break;
        case 702:
                for (n=40; n<78; n++)
                        BI[m++]=0x20000000|(n+16430);
                break;
        case 703:
                for (n=16584; n<16599; n++)
                        BI[m++]=0x20000000|n;
                break;
        case 704:
                for (n=985; n<989; n++)
                        BI[m++]=0x20000000|n;
                break;
        case 705:
                BI[m++]=0x20000000|1118;
                BI[m++]=0x20000000|989;
                for (n=16634; n<16642; n++)
                        BI[m++]=0x20000000|n;
                break;
        case 819:
                BI[m++]=0x40000000|MF_INDOORS;
                BI[m++]=0x20000000|16728;
                break;
        case 900:       // graveyard quest
                BI[m++]=0x20000000|16933; // lost souls tile
                BI[m++]=0x20000000|16934; // grave
                BI[m++]=0x20000000|16937; // grave, other dir
                break;
        case 1000:
                        BI[m++]=0x40000000|MF_INDOORS;
                        BI[m++]=0x20000000|1014;
                        BI[m++]=0x20000000|704;
                        //BI[m++]=150;
                        //BI[m++]=171;
                        //BI[m++]=152;
                        //BI[m++]=153;
                        //BI[m++]=154;
                        //BI[m++]=155;
                        //BI[m++]=156;
                        //BI[m++]=157;
                        //BI[m++]=520;
                        //BI[m++]=521;
                        //BI[m++]=504;
                        //BI[m++]=505;
                        //BI[m++]=506;
                        //BI[m++]=507;
                        BI[m++]=508;
                        BI[m++]=509;
                        BI[m++]=510;
                        BI[m++]=511;
                        BI[m++]=512;
                        BI[m++]=513;
                        BI[m++]=514;
                        BI[m++]=515;
                        BI[m++]=516;
                        BI[m++]=517;
                        BI[m++]=518;
                        BI[m++]=519;
                        BI[m++]=522;
                break;
        case 1001:
                        BI[m++]=0x40000000|MF_INDOORS;
                        BI[m++]=0x20000000|1118;
                        BI[m++]=16;
                        BI[m++]=17;
                        BI[m++]=45;
                        BI[m++]=47;
                        BI[m++]=19;
                        BI[m++]=20;
                        BI[m++]=48;
                        BI[m++]=49;
                        BI[m++]=606;
                        BI[m++]=607;
                        BI[m++]=608;
                        BI[m++]=609;
                        BI[m++]=611;
                break;
        case 1002:   // ice penta
                        BI[m++]=0x40000000|MF_INDOORS;
                        BI[m++]=0x20000000|16670;
                        BI[m++]=800;
                        BI[m++]=801;
                        BI[m++]=802;
                        BI[m++]=803;
                        BI[m++]=804;
                        BI[m++]=805;
                        BI[m++]=806;
                        BI[m++]=807;
                        BI[m++]=808;
                        BI[m++]=809;
                        BI[m++]=810;
                        BI[m++]=811;
                        BI[m++]=812;
			break;
	case	1003:	BI[m++]=0x20000000|16980;
			break;
	case 	1140:	BI[m++]=0x20000000|17064;
			BI[m++]=0x20000000|17065;
			BI[m++]=0x20000000|17066;
			BI[m++]=0x20000000|17067;
			break;
                }

}

/* ---- build pages --------------------------------------------------------
 * #build             start building (page 0) / show where you are
 * #build <page>      go to that page
 * #build next|prev   next / previous page
 * #build end         stop building
 * Page 0 holds the zone flags, then come the floor pages, then the object
 * pages (every placeable template, look-alikes skipped). All lists are
 * collected once from the original build sets and the item templates.
 */
int god_build_start(int cn);
void god_build_stop(int cn);
static unsigned int *bp_flag=NULL,*bp_floor=NULL,*bp_obj=NULL;
static int bp_nflag=0,bp_nfloor=0,bp_nobj=0;

static int bp_has(unsigned int *list,int n,unsigned int v)
{
	int k;
	for (k=0; k<n; k++) if (list[k]==v) return 1;
	return 0;
}

static void bp_collect(void)
{
	static int sets[]={0,1,2,3,4,331,700,701,702,703,704,705,819,900,1000,1001,1002,1003,1140};
	unsigned int tmp[40],v;
	int s,k,n,t,dup;

	if (bp_flag) return;
	bp_flag=calloc(64,sizeof(unsigned int));
	bp_floor=calloc(1024,sizeof(unsigned int));
	bp_obj=calloc(MAXTITEM,sizeof(unsigned int));
	if (!bp_flag || !bp_floor || !bp_obj) return;

	// flags and floors from the hand-made sets, in their order
	for (s=0; s<(int)(sizeof(sets)/sizeof(int)); s++) {
		memset(tmp,0,sizeof(tmp));
		build_set(tmp,sets[s]);
		for (k=0; k<40; k++) {
			v=tmp[k];
			if (!v) continue;
			if (v&0x40000000) { if (bp_nflag<64 && !bp_has(bp_flag,bp_nflag,v)) bp_flag[bp_nflag++]=v; }
			else if (v&0x20000000) { if (bp_nfloor<1024 && !bp_has(bp_floor,bp_nfloor,v)) bp_floor[bp_nfloor++]=v; }
			else if (v<MAXTITEM && !bp_has(bp_obj,bp_nobj,v)) bp_obj[bp_nobj++]=v;
		}
	}
	// then every other placeable template, look-alikes skipped
	for (n=1; n<MAXTITEM; n++) {
		if (it_temp[n].used==USE_EMPTY) continue;
		if (it_temp[n].flags&IF_TAKE) continue;
		if (it_temp[n].driver==25 && it_temp[n].data[3]==0) continue;
		if (it_temp[n].driver==22) continue;
		for (dup=0,k=0; k<bp_nobj; k++) {
			t=bp_obj[k];
			if (t==n || (it_temp[t].sprite[0]==it_temp[n].sprite[0] && !strcmp(it_temp[t].name,it_temp[n].name))) { dup=1; break; }
		}
		if (!dup) bp_obj[bp_nobj++]=n;
	}
}

static int bp_floorpages(void) { return (bp_nfloor+39)/40; }
static int bp_pages(void) { return 1+bp_floorpages()+(bp_nobj+39)/40; }

void god_build_equip(int cn, int x)
{
	int m,k,fp,op,pages;

	bp_collect();
	if (!bp_flag) return;
	pages=bp_pages();
	if (x<0) x=0;
	if (x>=pages) x=pages-1;

	for (m=0; m<40; m++) ch[cn].item[m]=0;
	fp=bp_floorpages();
	m=0;
	if (x==0) {
		for (k=0; k<bp_nflag && m<40; k++) ch[cn].item[m++]=bp_flag[k];
		do_char_log(cn,3,"Build page 0 of %d: zones and flags. Drop one on a tile to switch it on or off.\n",pages-1);
	} else if (x<=fp) {
		for (k=(x-1)*40; k<bp_nfloor && m<40; k++) ch[cn].item[m++]=bp_floor[k];
		do_char_log(cn,3,"Build page %d of %d: floors (%d of %d).\n",x,pages-1,x,fp);
	} else {
		op=x-fp;
		for (k=(op-1)*40; k<bp_nobj && m<40; k++) ch[cn].item[m++]=bp_obj[k];
		do_char_log(cn,3,"Build page %d of %d: objects (%d of %d).\n",x,pages-1,op,pages-1-fp);
	}
	ch[cn].data[CHD_BUILDPAGE]=x;
	chlog(cn,"Now on build page %d",x);
	do_update_char(cn);
}

// the #build command
void god_build_cmd(int cn,char *arg)
{
	int page;

	if (!IS_BUILDING(cn)) {
		if (!strcasecmp(arg,"end")) { do_char_log(cn,0,"You are not building.\n"); return; }
		page=isdigit(*arg) ? atoi(arg) : 0;
		if (god_build_start(cn)) {
			int fp,pages;
			bp_collect();
			fp=bp_floorpages(); pages=bp_pages();
			do_char_log(cn,3," \n");
			do_char_log(cn,3,"Build mode. Your backpack is put away until you stop.\n");
			do_char_log(cn,3,"  Page 0          zones and flags\n");
			do_char_log(cn,3,"  Pages 1-%-2d      floors\n",fp);
			do_char_log(cn,3,"  Pages %d-%-2d     objects\n",fp+1,pages-1);
			do_char_log(cn,3," \n");
			do_char_log(cn,3,"#build              show which page you're on\n");
			do_char_log(cn,3,"#build <page>       go to that page\n");
			do_char_log(cn,3,"#build next | prev  next / previous page\n");
			do_char_log(cn,3,"#build end          stop, get your backpack back\n");
			do_char_log(cn,3,"#undo               undo your last placement or area\n");
			do_char_log(cn,3,"#tile               what is on the tile under the mouse\n");
			do_char_log(cn,3,"#light              recompute lighting everywhere\n");
			do_char_log(cn,3," \n");
			do_char_log(cn,3,"Shift+click a piece: place one at a time. Right-click a piece: area mode, click two corners to fill.\n");
			do_char_log(cn,3," \n");
			god_build_equip(cn,page);
		}
		return;
	}
	if (!strcasecmp(arg,"end") || !strcasecmp(arg,"stop")) { god_build_stop(cn); return; }
	if (!strcasecmp(arg,"next")) { god_build_equip(cn,ch[cn].data[CHD_BUILDPAGE]+1); return; }
	if (!strcasecmp(arg,"prev")) { god_build_equip(cn,ch[cn].data[CHD_BUILDPAGE]-1); return; }
	if (isdigit(*arg)) { god_build_equip(cn,atoi(arg)); return; }
	bp_collect();
	do_char_log(cn,3,"You are on build page %d of %d. #build <page>, #build next, #build prev, #build end to stop. #undo, #tile.\n",ch[cn].data[CHD_BUILDPAGE],bp_pages()-1);
}

void god_build(int cn,int x)
{

        if (!IS_BUILDING(cn)) {
                // build from non-build mode: start
                if (god_build_start(cn)) god_build_equip(cn,x);
        } else if (!x) {
                // build 0 from build mode: stop
                god_build_stop(cn);
        } else {
                // switch to mode x
                god_build_equip(cn, x);
        }
}

void god_raise_char(int cn,int co,int v)
{
        if (co == 0) {
                do_char_log(cn,0,"No such character.\n");
                return;
        } else if (!IS_SANECHAR(co)) {
                do_char_log(cn,0,"Bad character number: %d\n", co);
                return;
        } else if (v < 0) {
                do_char_log(cn,0,"Raising by a negative amount??\n");
                return;
        }
        ch[co].points+=v;
        ch[co].points_tot+=v;

        do_char_log(cn,1,"Raised %s by %d.\n",ch[co].name,v);
        chlog(cn, "IMP: Raised %s by %d.",ch[co].name,v);
        do_char_log(co,0,"You have been rewarded by the gods. You received %d experience points.\n",v);

        do_check_new_level(co);
}

void god_lower_char(int cn,int co,int v)
{
        if (co == 0) {
                do_char_log(cn,0,"No such character.\n");
                return;
        } else if (!IS_SANECHAR(co)) {
                do_char_log(cn,0,"Bad character number: %d\n", co);
                return;
        } else if (v < 0) {
                do_char_log(cn,0,"Lowering by a negative amount??\n");
        }
        ch[co].points_tot-=v;
	ch[co].points-=v;

        do_char_log(cn,1,"Lowered %s by %d.\n",ch[co].name,v);
        chlog(cn, "IMP: Lowered %s by %d.",ch[co].name,v);
        do_char_log(co,0,"You have been punished by the gods. You lost %d experience points.\n",v);
}

/* CS, 991127: Now takes either <silver> or <gold> <silver> */
void god_gold_char(int cn,int co,int v,char *silver)
{
        if (co == 0) {
                do_char_log(cn,0,"No such character.\n");
                return;
        } else if (!IS_SANECHAR(co)) {
                do_char_log(cn,0,"Bad character number: %d\n", co);
                return;
        } else if (v < 0) {
                do_char_log(cn,0,"Handing out negative gold?\n");
                return;
        } else if (*silver && (atoi(silver) < 0)) {
                do_char_log(cn,0,"Handing out negative silver?\n");
                return;
        }
        if (*silver) v = v * 100 + atoi(silver);
        ch[co].gold += v;

        do_char_log(cn,1,"Added %dG %dS to %s.\n",v/100,v%100,ch[co].name);
        chlog(cn, "IMP: Added %dG %dS to %s.",v/100,v%100,ch[co].name);
        do_char_log(co,0,"You have been rewarded by the gods. You received %dG %dS.\n",v/100,v%100);

	do_update_char(co);
}

void god_erase(int cn,int co,int erase_player)
{
        if (co == 0) {
                do_char_log(cn,0,"No such character.\n");
                return;
        } else if (!IS_SANECHAR(co)) {
                do_char_log(cn,0,"Bad character number: %d\n", co);
                return;
        } else if (!IS_USEDCHAR(co)) {
                do_char_log(cn,0,"Character %d is unused anyway.\n", co);
                return;
        }

        if ((ch[co].flags&(CF_PLAYER|CF_USURP)) && !erase_player) {
                do_char_log(cn, 0, "%-.20s is a player or QM; use #PERASE if you insist.\n", ch[co].name);
                return;
        }
        if (erase_player && !(ch[co].flags&(CF_PLAYER|CF_USURP))) {
                do_char_log(cn, 0, "%-.20s is not a player; use #ERASE for NPCs.\n", ch[co].name);
                return;
        }
        if (erase_player) {
                if (ch[co].player) plr_logout(co,ch[co].player,LO_SHUTDOWN);
                ch[co].used=USE_EMPTY;
                chlog(cn, "IMP: Erased player %d (%-.20s).", co, ch[co].name);
                do_char_log(cn,1,"Player %d (%-.20s) is no more.\n", co, ch[co].name);
        } else {
                do_char_killed(0,co);
                chlog(cn, "IMP: Erased NPC %d (%-.20s).", co, ch[co].name);
                do_char_log(cn,1,"NPC %d (%-.20s) is no more.\n", co, ch[co].name);
        }
}

void god_kick(int cn,int co)
{
        if (co == 0) {
                do_char_log(cn,0,"No such character.\n");
                return;
        } else if (!IS_SANECHAR(co)) {
                do_char_log(cn,0,"Bad character number: %d\n", co);
                return;
        } else if (!IS_USEDCHAR(co) || !IS_PLAYER(co)) {
                do_char_log(cn,0,"Character %d is not a player!\n", co);
                return;
        }
                plr_logout(co,ch[co].player,LO_IDLE);
        do_char_log(cn,1,"Kicked %s.\n", ch[co].name);
                chlog(cn,"IMP: kicked %s (%d)",ch[co].name,co);
                ch[co].flags|=CF_KICKED;
}

void god_skill(int cn,int co,int n,int val)
{
        if (n == -1) { // bad skill number
                return;
        } else if (co == 0) {
                do_char_log(cn,0,"No such character.\n");
                return;
        } else if (!IS_SANECHAR(co)) {
                do_char_log(cn,0,"Bad character number: %d\n", co);
                return;
        } else if (!IS_USEDCHAR(co)) {
                do_char_log(cn,0,"Character %d is not in the game!\n", co);
                return;
        } else if (!SANESKILL(n)) {
                do_char_log(cn,0,"Skill number %d out of range.\n", n);
                return;
        } else if (val<0 || val>199) {
                do_char_log(cn,0,"Skill amount %d out of range.\n", val);
                return;
        }
        ch[co].skill[n][0]=val;
        do_update_char(co);

        do_char_log(cn,1,"Set %s of %s to %d.\n",skilltab[n].name,ch[co].name,val);
        chlog(cn,"IMP: Set %s of %s to %d.",skilltab[n].name,ch[co].name,val);
}

void god_donate_item(int in,int place)
{
        static int don_x[]={497,560}; // Temple of Skua
        static int don_y[]={512,542}; // Temple of the Purple One
        int x,y;

        if (!IS_SANEUSEDITEM(in)) {
                xlog("Attempt to god_donate_item %d", in);
                return;
        }
        if (place<1 || place>2) place=RANDOM(2)+1;

        x=don_x[place-1];
        y=don_y[place-1];

        if (!god_drop_item_fuzzy(in,x,y)) it[in].used=USE_EMPTY;
}

void god_set_flag(int cn,int co,unsigned long long flag)
{
	char *ptr="unknown";

	if (!co || !IS_SANECHAR(co)) {
		do_char_log(cn,0,"Character %d does not exist, dude!\n",co);
		return;
	}

	ch[co].flags^=flag;

	switch (flag) {
		case    CF_IMMORTAL:    ptr="immortal"; break;
		case    CF_GOD:         ptr="god"; break;
		case    CF_CREATOR:     ptr="creator"; break;
		case    CF_BUILDMODE:   ptr="buildmode"; break;
		case    CF_RESPAWN:     ptr="respawn"; break;
		case    CF_PLAYER:      ptr="player"; break;
		case    CF_CCP:         ptr="ccp"; break;
		case    CF_NEWUSER:     ptr="newuser"; break;
		case    CF_NOTELL:      ptr="notell"; break;
		case    CF_NOSHOUT:     ptr="noshout"; break;
		case    CF_MERCHANT:    ptr="merchant"; break;
		case    CF_STAFF:       ptr="staff"; break;
		case    CF_NOHPREG:     ptr="nohpreg"; break;
		case    CF_NOENDREG:    ptr="noendreg"; break;
		case    CF_NOMANAREG:   ptr="nomanareg"; break;
		case    CF_INVISIBLE:   ptr="invisible"; fx_add_effect(12,0,ch[co].x,ch[co].y,0); break;
		case    CF_INFRARED:    ptr="infrared"; break;
		case    CF_BODY:        ptr="body"; break;
		case    CF_UNDEAD:      ptr="undead"; break;
		case    CF_NOMAGIC:     ptr="nomagic"; break;
		case    CF_STONED:      ptr="stoned"; break;
		case    CF_USURP:       ptr="usurp"; break;
		case    CF_IMP:         ptr="imp"; break;
		case    CF_SHUTUP:      ptr="shutup"; break;
		case    CF_NODESC:      ptr="nodesc"; break;
		case    CF_PROF:        ptr="prof"; break;
		case    CF_NOLIST:      ptr="nolist"; break;
		case    CF_NOWHO:       ptr="nowho"; break;
		case    CF_SAFE:        ptr="safe"; break;
		case    CF_POH:         ptr="purple of honor"; break;
		case    CF_POH_LEADER:  ptr="poh leader"; break;
		case 	CF_GOLDEN:	ptr="golden list"; break;
		case 	CF_BLACK: 	ptr="black list"; break;
		case 	CF_GREATERGOD:	ptr="greater god"; break;
		case 	CF_GREATERINV:	ptr="greater inv";
					if (ch[cn].flags&CF_GREATERINV) {
						ch[cn].flags|=CF_INVISIBLE;
						ptr="greater inv & invisible";
					}
					break;

		default:                ptr="unknown"; break;
	}

	chlog(cn,"IMP: set %s (%llX) on %s (%d) to %s",ptr,flag,ch[co].name,co,(ch[co].flags&flag) ? "on" : "off");
	do_char_log(cn,3,"Set %s on %s to %s.\n",ptr,ch[co].name,(ch[co].flags&flag) ? "on" : "off");

	if (flag==CF_STAFF) {
		if (ch[co].kindred&KIN_PURPLE) {
			ch[co].temple_x=ch[co].tavern_x=558;
			ch[co].temple_y=ch[co].tavern_y=542;
		} else if (ch[co].flags&CF_STAFF) {
			ch[co].temple_x=ch[co].tavern_x=813;
			ch[co].temple_y=ch[co].tavern_y=165;
		} else {
			ch[co].temple_x=ch[co].tavern_x=512;
			ch[co].temple_y=ch[co].tavern_y=512;
		}
	}
}

void god_set_gflag(int cn,int flag)
{
        char *ptr="unknown";

        globs->flags^=flag;

        switch(flag) {
                case    GF_LOOTING:     ptr="looting"; break;
		case    GF_MAYHEM:      ptr="mayhem"; break;
		case    GF_CAP:      	ptr="cap"; break;
		case    GF_SPEEDY:      ptr="speedy"; break;

                default:                ptr="unknown"; break;
        }

        chlog(cn,"IMP: set %s (%X) to %s",ptr,flag,(globs->flags&flag) ? "on" : "off");
        do_char_log(cn,3,"Set %s to %s.\n",ptr,(globs->flags&flag) ? "on" : "off");
}

/* toggle purple (PK) status */
void god_set_purple(int cn,int co)
{
        if (co == 0) {
                do_char_log(cn,0,"No such character.\n");
                return;
        } else if (!IS_SANECHAR(co)) {
                do_char_log(cn,0,"Bad character number: %d\n", co);
                return;
        }
        ch[co].kindred^=KIN_PURPLE;
        do_char_log(cn,1,"%s purple: %s.\n",ch[co].name,(IS_PURPLE(co)) ? "on" : "off");
        chlog(cn, "IMP: Set purple status of %s to %s.", ch[co].name,(IS_PURPLE(co)) ? "on" : "off");
        /* CS, 000209: Reset last kill time and victim */
        if (!IS_PURPLE(co)) {
                ch[co].data[CHD_ATTACKTIME] = 0;
                ch[co].data[CHD_ATTACKVICT] = 0;
                ch[co].temple_x=512;
        	ch[co].temple_y=512;
        } else {
        	ch[co].temple_x=558;
                ch[co].temple_y=542;
        }
}

void god_destroy_items(int cn)
{
        int n,in;

        for (n=0; n<40; n++) {
                if ((in=ch[cn].item[n])!=0) {
                        ch[cn].item[n]=0;
                        if (in>0 && in<MAXITEM) it[in].used=USE_EMPTY;
                }
        }
        for (n=0; n<20; n++) {
                if ((in=ch[cn].worn[n])!=0) {
                        ch[cn].worn[n]=0;
                        if (in>0 && in<MAXITEM) it[in].used=USE_EMPTY;
                }
                if ((in=ch[cn].spell[n])!=0) {
                        ch[cn].spell[n]=0;
                        if (in>0 && in<MAXITEM) it[in].used=USE_EMPTY;
                }
        }
        if ((in=ch[cn].citem)!=0) {
                ch[cn].citem=0;
                if (in>0 && in<MAXITEM) it[in].used=USE_EMPTY;
        }
        if (ch[cn].flags&CF_PLAYER) {
                for (n=0; n<62; n++) {
                        if ((in=ch[cn].depot[n])!=0) {
                                ch[cn].depot[n]=0;
                                if (in>0 && in<MAXITEM) it[in].used=USE_EMPTY;
                        }
                }
        }
	do_update_char(cn);
}

void god_racechange(int co,int temp)
{
        int n;
        struct character old;

        if (!IS_SANEUSEDCHAR(co) || !IS_PLAYER(co)) return;

        god_destroy_items(co);

        old=ch[co];

        ch[co]=ch_temp[temp];

        ch[co].temp=temp;
        ch[co].pass1=old.pass1;
        ch[co].pass2=old.pass2;
        ch[co].gold=old.gold;

        strcpy(ch[co].name,old.name);
        strcpy(ch[co].reference,old.name);
        strcpy(ch[co].description,old.description);

        ch[co].dir=old.dir;

        ch[co].temple_x=ch[co].tavern_x=HOME_MERCENARY_X;
        ch[co].temple_y=ch[co].tavern_y=HOME_MERCENARY_Y;

        ch[co].creation_date=old.creation_date;
        ch[co].login_date=old.login_date;
        ch[co].flags=old.flags;
        if (old.kindred&KIN_PURPLE) {
        	ch[co].kindred|=KIN_PURPLE;
        	ch[co].temple_x=558;
        	ch[co].temple_y=542;
        }
        ch[co].total_online_time=old.total_online_time;
        ch[co].current_online_time=old.current_online_time;
        ch[co].comp_volume=old.comp_volume;
        ch[co].raw_volume=old.raw_volume;
        ch[co].idle=old.idle;

        ch[co].a_end=1000000;
        ch[co].a_hp=1000000;
        ch[co].a_mana=1000000;

        ch[co].x=old.x;
        ch[co].y=old.y;
        ch[co].tox=old.tox;
        ch[co].toy=old.toy;
        ch[co].frx=old.frx;
        ch[co].fry=old.fry;

        ch[co].mode=old.mode;
        ch[co].used=USE_ACTIVE;
        ch[co].player=old.player;
        ch[co].alignment=0;
        ch[co].luck=old.luck;
        ch[co].light=old.light;
        ch[co].status=old.status;
        ch[co].status2=old.status2;

        for (n=0; n<40; n++)
                ch[co].item[n]=0;

        for (n=0; n<20; n++)
                ch[co].worn[n]=0;

        for (n=0; n<20; n++)
                ch[co].spell[n]=0;

        for (n=0; n<100; n++)
                ch[co].data[n]=old.data[n];

        ch[co].data[18]=0;      // pentagram experience
        ch[co].data[20]=0;      // highest gorge solved
        ch[co].data[21]=0;      // seyan'du sword bits
        ch[co].data[22]=0;      // arena monster reset
        ch[co].data[45]=0;      // current rank

        for (n=0; n<62; n++)
                ch[co].depot[n]=old.depot[n];

        do_update_char(co);
}

int god_save(int cn,int co)
{
        int handle;
        char buf[80];

        if (co == 0) {
                do_char_log(cn,0,"No such character.\n");
                return 0;
        } else if (!IS_SANECHAR(co)) {
                do_char_log(cn,0,"Bad character number: %d\n", co);
                return 0;
        } else if (!IS_PLAYER(co)) {
                do_char_log(cn,0,"Character %d is not a player.\n", co);
                return 0;
        }

        sprintf(buf,".save/%s.moa",ch[co].name);
        handle=open(buf,O_WRONLY|O_TRUNC|O_CREAT,0600);
        if (handle==-1) {
                do_char_log(cn,0,"Could not open file.\n");
                perror(buf);
                return 0;
        }
        write(handle,&co,4);
        write(handle,&ch[co].pass1,4);
        write(handle,&ch[co].pass2,4);
        write(handle,ch[co].name,40);
        write(handle,&ch[co].temp,4);
        close(handle);
        do_char_log(cn,1,"Saved as %s.moa.\n",ch[co].name);
        chlog(cn,"IMP: Saved %s.", ch[co].name);

        return 1;
}

void god_mail_pass(int cn,int co)
{
        char buf[256];

        if (!god_save(cn,co)) return;

        sprintf(buf,"uuencode %s.moa </home/merc/.save/%s.moa | mail -s \"%s savefile\" %s",
                ch[co].name,
                ch[co].name,
                ch[co].name,
                "admin@astonia.com");

        system(buf);
}

void god_slap(int cn,int co)
{
        // DB: why else ... else .. else ?
        if (co == 0) {
                do_char_log(cn,0,"No such character.\n");
                return;
        } else if (!IS_SANECHAR(co)) {
                do_char_log(cn,0,"Bad character number: %d\n", co);
                return;
        } else if (!IS_USEDCHAR(co)) {
                do_char_log(cn,0,"Character %d is not active.\n", co);
                return;
        } else if (!IS_ACTIVECHAR(co) || IS_GOD(co)) {
                do_char_log(cn,0,"%s is not available to feel your punishment.\n", ch[co].name);
                return;
        }

        if (ch[co].a_hp>10000) ch[co].a_hp-=5000;
        if (ch[co].a_end>10000) ch[co].a_end-=5000;
        if (ch[co].a_mana>10000) ch[co].a_mana-=5000;

        if (cn) do_char_log(cn,1,"Slapped %s.\n",ch[co].reference);
        do_char_log(co,0,"A god reaches down and slaps you in the face.\n");
        do_area_log(cn,co,ch[co].x,ch[co].y,1,"A god reaches down and slaps %s in the face.\n",ch[co].reference);
        chlog(cn,"IMP: slapped %s (%d)",ch[co].name,co);
}

void god_spritechange(int cn,int co,int sprite)
{
        if (co == 0) {
                do_char_log(cn,0,"No such character.\n");
                return;
        } else if (!IS_SANECHAR(co)) {
                do_char_log(cn,0,"Bad character number: %d\n", co);
                return;
        } else if (!IS_USEDCHAR(co)) {
                do_char_log(cn,0,"Character %d is not active.\n", co);
                return;
        } else if (sprite>31 || sprite<0) {
                do_char_log(cn,0,"Sprite base out of bounds.\n");
                return;
        } else if ((ch[co].flags&CF_PLAYER) && !(ch[cn].flags&CF_GOD)) {
		do_char_log(cn,0,"Sorry, you cannot change a player's sprite.\n");
		return;
	}

	chlog(cn,"IMP: changed sprite of %s (%d) from %d to %d",ch[co].name,co,(ch[co].sprite-2000)/1024,sprite);
        do_char_log(cn,0,"%s former sprite base was %d.\n",ch[co].name,(ch[co].sprite-2000)/1024);
        ch[co].sprite=sprite*1024+2000;
}

void god_luck(int cn,int co,int val)
{
        if (co == 0) {
                do_char_log(cn,0,"No such character.\n");
                return;
        } else if (!IS_SANECHAR(co)) {
                do_char_log(cn,0,"Bad character number: %d\n", co);
                return;
        } else if (!IS_PLAYER(co)) {
                do_char_log(cn,0,"Character %d is not a player.\n", co);
                return;
        }
        ch[co].luck=val;

        do_char_log(cn,2,"Set %s luck to %d.\n",ch[co].name,val);
        chlog(cn, "IMP: Set %s luck to %d.",ch[co].name,val);

}

void god_reset_description(int cn,int co)
{
        char old_desc[LENDESC];

        if (co == 0) {
                do_char_log(cn,0,"No such character.\n");
                return;
        } else if (!IS_SANECHAR(co)) {
                do_char_log(cn,0,"Bad character number: %d\n", co);
                return;
        } else if (!IS_PLAYER(co) && !IS_USURP(co)) {
                do_char_log(cn,0,"Character %d is not a player.\n", co);
                return;
        }

        if (ch[co].flags & CF_NODESC) { // is currently hindered from describing self
                ch[co].flags&=~CF_NODESC;
                do_char_log(cn,2,"%s is again able to change his/her description.\n", ch[co].name);
                do_char_log(co,0,"The gods have restored your ability to describe yourself.\n");
                chlog(cn,"IMP: reset NODESC flag on %s", ch[co].name);
        } else {
                strncpy(old_desc, ch[co].description, LENDESC);
                sprintf(ch[co].description,"%s chose an indecent description and it was removed by the gods.",ch[co].name);
                ch[co].flags|=CF_NODESC;
                do_char_log(cn,2,"Reset description of %s (%d).\n", ch[co].name,co);
                do_char_log(co,0,"A god has removed your inappropriate description.\n");
                chlog(cn,"IMP: reset description of %s (%d)",ch[co].name,co);
                chlog(co,"previous description: %-.*s", LENDESC, old_desc);
        }
}

void god_set_name(int cn,int co,char *name)
{
        if (co == 0) {
                do_char_log(cn,0,"No such character.\n");
                return;
        } else if (!IS_SANECHAR(co)) {
                do_char_log(cn,0,"Bad character number: %d\n", co);
                return;
        } else if (!IS_GOD(cn) && ch[co].data[63]!=cn) {
                do_char_log(cn,0,"Character %d isn't one of your thralls.\n", co);
                return;
        }

        if (!name || strlen(name)<3 || strlen(name)>35) {
                do_char_log(cn,0,"Name too short or long.\n");
                return;
        }
        //titlecase_str(name);

	chlog(cn,"IMP: changed name %s (%d) to %s",ch[co].name,co,name);

        strcpy(ch[co].name,name);
        strcpy(ch[co].reference,name);
        do_char_log(cn,1,"Done.\n");

	do_update_char(co);
}

void god_usurp(int cn,int co)
{
        int nr;

        if (co == 0) {
                do_char_log(cn,0,"No such character.\n");
                return;
        } else if (!IS_SANECHAR(co)) {
                do_char_log(cn,0,"Bad character number: %d\n", co);
                return;
        } else if (!IS_USEDCHAR(co) || !IS_SANENPC(co)) {
                do_char_log(cn,0,"Character %d is not an NPC.\n", co);
                return;
        }

        chlog(cn,"IMP: Usurping %s (%d, t=%d)",ch[co].name,co,ch[co].temp);

        ch[co].flags|=CF_USURP;
        nr=ch[cn].player;

        ch[co].player=nr;
        player[nr].usnr=co;

        if (ch[cn].flags&CF_USURP) {
                ch[co].data[97]=ch[cn].data[97];
                ch[cn].data[97]=0;
        } else {
                ch[co].data[97]=cn;
                ch[cn].flags|=CF_CCP;
        }

        if (ch[cn].flags&(CF_PLAYER)) {
                ch[cn].tavern_x=ch[cn].x;
                ch[cn].tavern_y=ch[cn].y;
                god_transfer_char(cn, 10, 10);
                if (!ch[cn].data[CHD_AFK]) do_afk(cn, NULL);
        }
        plr_logout(cn,nr,LO_USURP);

	do_update_char(co);
}

void god_exit_usurp(int cn)
{
        int co,nr;

        ch[cn].flags&=~(CF_USURP|CF_STAFF|CF_IMMORTAL|CF_GOD|CF_CREATOR);
        co=ch[cn].data[97];
        ch[co].flags&=~CF_CCP;

        nr=ch[cn].player;

        ch[co].player=nr;
        player[nr].usnr=co;
        god_transfer_char(co, 512, 512); // simulate recall
        do_afk(co, NULL);

	do_update_char(cn);
}

void god_grolm(int cn)
{
        int co;

        co=pop_create_char(386,1);
        if (co) {
                chlog(cn,"IMP: is now playing %s (%d)",ch[co].name,co);
                god_usurp(cn,co);
        }
}

void god_grolm_info(int cn)
{
        static char *states[3]={"at_home","moving_out","moving_in"};
        int co;

        for (co=1; co<MAXCHARS; co++)
                if (ch[co].temp==498) break;

        if (co==MAXCHARS || ch[co].used!=USE_ACTIVE || (ch[co].flags&CF_BODY)) {
                do_char_log(cn,1,"Grolmy is dead.\n");
                return;
        }

        do_char_log(cn,2,"Current state=%s, runs=%d, timer=%2.2fm, id=%d.\n",
                (ch[co].data[22]>=0 || ch[co].data[22]<=2) ? states[ch[co].data[22]] : "unknown",
                ch[co].data[40],
                (double)(globs->ticker-ch[co].data[23])/(TICKS*60.0),
                co);
}

void god_grolm_start(int cn)
{
        int co;

        for (co=1; co<MAXCHARS; co++)
                if (ch[co].temp==498) break;

        if (co==MAXCHARS || ch[co].used!=USE_ACTIVE || (ch[co].flags&CF_BODY)) {
                do_char_log(cn,1,"Grolmy is dead.\n");
                return;
        }

        if (ch[co].data[22]!=0) {
                do_char_log(cn,1,"Grolmy is already moving.\n");
                return;
        }

        ch[co].data[22]=1;
}

void god_gargoyle(int cn)
{
        int co;

        co=pop_create_char(495,1);
        if (co) {
                chlog(cn,"is now playing %s (%d)",ch[co].name,co);
                god_usurp(cn,co);
        }
}

void god_minor_racechange(int cn,int t) // note: cannot deal with values which are already higher than the new max!
{
        int n;

        if (!IS_SANECHAR(cn) || !IS_SANECTEMPLATE(t)) return;

        chlog(cn,"Changed into %s",ch_temp[t].name);

        ch[cn].hp[1]=ch_temp[t].hp[1];
        ch[cn].hp[2]=ch_temp[t].hp[2];
        ch[cn].hp[3]=ch_temp[t].hp[3];

        ch[cn].end[1]=ch_temp[t].end[1];
        ch[cn].end[2]=ch_temp[t].end[2];
        ch[cn].end[3]=ch_temp[t].end[3];

        ch[cn].mana[1]=ch_temp[t].mana[1];
        ch[cn].mana[2]=ch_temp[t].mana[2];
        ch[cn].mana[3]=ch_temp[t].mana[3];


        if (ch[cn].kindred&KIN_PURPLE) ch[cn].kindred=ch_temp[t].kindred|KIN_PURPLE;
        else ch[cn].kindred=ch_temp[t].kindred;

        ch[cn].temp=t;
        ch[cn].sprite=ch_temp[t].sprite+LOOKTIER_STEP*char_looktier(cn);	// prestige look of the new class
        ch[cn].weapon_bonus=ch_temp[t].weapon_bonus;
        ch[cn].armor_bonus=ch_temp[t].armor_bonus;
        ch[cn].gethit_bonus=ch_temp[t].gethit_bonus;

        // character flags??

        for (n=0; n<5; n++) {
                ch[cn].attrib[n][1]=ch_temp[t].attrib[n][1];
                ch[cn].attrib[n][2]=ch_temp[t].attrib[n][2];
                ch[cn].attrib[n][3]=ch_temp[t].attrib[n][3];
        }

        for (n=0; n<50; n++) {
                if (ch[cn].skill[n][0]==0 && ch_temp[t].skill[n][0]) {
                        ch[cn].skill[n][0]=ch_temp[t].skill[n][0];
                        xlog("added %s to %s",skilltab[n].name,ch[cn].name);
                }
                ch[cn].skill[n][1]=ch_temp[t].skill[n][1];
                ch[cn].skill[n][2]=ch_temp[t].skill[n][2];
                ch[cn].skill[n][3]=ch_temp[t].skill[n][3];
        }

        ch[cn].data[45]=0;	// reset level
        do_check_new_level(cn);
}

void god_force(int cn, char *whom, char *text)
{
        int co;

        if (cn <= 0) return;

        if (!*whom) {
                do_char_log(cn, 0, "#FORCE whom?\n");
                return;
        }
        co = dbatoi_self(cn, whom);
        if (co <= 0) {
                do_char_log(cn, 0, "No such character.\n");
                return;
        }
        if (!IS_USEDCHAR(co)) {
                do_char_log(cn, 0, "Character is not active.\n");
                return;
        }
        if (IS_PLAYER(co) && !IS_GOD(cn)) {
                do_char_log(cn, 0, "Not allowed to #FORCE players.\n");
                return;
        }
        if (!text || !*text) {
                do_char_log(cn, 0, "#FORCE %s to what?\n", ch[co].name);
                return;
        }
        chlog(cn, "IMP: Forced %s (%d) to \"%s\"", ch[co].name, co, text);
        do_say(co, text);
        do_char_log(cn, 2, "%s was forced.\n", ch[co].name);
}

/* CS, 991205: #ENEMY <NPC> <char> */
void do_enemy(int cn, char *npc, char *victim)
{
        int co, cv;

        if (!*npc) {
                do_char_log(cn, 0, "Make whom the enemy of whom?\n");
                return;
        }
        co = dbatoi(npc);
        if (co == 0) {
                do_char_log(cn, 0, "No such character: '%s'.\n", npc);
                return;
        }
        if (!IS_USEDCHAR(co)) {
                do_char_log(cn, 0, "That character is currently not in use.\n");
                return;
        }
        if (IS_PLAYER(co)) {
                do_char_log(cn, 0, "#ENEMY only works on NPCs; %s is a player.\n", ch[co].name);
                return;
        }
        if (!*victim) {
                npc_list_enemies(co, cn);
                return;
        }
        cv = dbatoi(victim);
        if (cv == 0) {
                do_char_log(cn, 0, "No such character: '%s'.\n", victim);
                return;
        }
        if (!IS_USEDCHAR(cv)) {
                do_char_log(cn, 0, "That character is currently not in use.\n");
                return;
        }
        if (npc_is_enemy(co,cv)) {
                if (!npc_remove_enemy(co,cv)) {
                        do_char_log(cn, 0, "Can't remove %s from %s's enemy list!\n", ch[cv].name, ch[co].name);
                        xlog("#ENEMY failed to remove %s from %s's enemy list.", ch[cv].name, ch[co].name);
                } else {
                        do_char_log(cn, 0, "Removed %s from %s's enemy list.\n", ch[cv].name, ch[co].name);
                        chlog(cn, "IMP: Removed %s from %s's enemy list.\n", ch[cv].name, ch[co].name);
                }
                return;
        }
        if (ch[co].data[CHD_GROUP] == ch[cv].data[CHD_GROUP]) {
                do_char_log(cn, 0, "%s refuses to fight %s.\n", ch[co].name, ch[cv].name);
                return;
        }
        if (!npc_add_enemy(co,cv,1)) {
                do_char_log(cn, 0, "%s can't handle any more enemies.\n", ch[co].name);
                return;
        }
        if (ch[cn].text[1][0]) do_sayx(co,ch[co].text[1],ch[cv].name);
        chlog(cn,"IMP: Made %s an enemy of %s", ch[cv].name, ch[co].name);
        chlog(co,"Added %s to kill list (#ENEMY by %s)",ch[cv].name,ch[cn].name);
        do_char_log(cn, 2, "%s is now an enemy of %s.\n", ch[cv].name, ch[co].name);
}


#define MAXBAN  250

struct ban
{
        char creator[80];
        char victim[80];

        unsigned int addr;
};

struct ban ban[MAXBAN];
int maxban=0;

int god_read_banlist(void)
{
	int handle;

	handle=open("banlist.dat",O_RDONLY);
	if (handle==-1) return 0;

	read(handle,&maxban,sizeof(maxban));
	read(handle,ban,sizeof(ban));

	close(handle);

	return 1;
}

int god_write_banlist(void)
{
	int handle;

	handle=open("banlist.dat",O_WRONLY|O_CREAT|O_TRUNC,0600);
	if (handle==-1) return 0;

	write(handle,&maxban,sizeof(maxban));
	write(handle,ban,sizeof(ban));

	close(handle);

	return 1;
}

int god_is_banned(int addr)
{
        int n;

        for (n=0; n<maxban; n++)
                if ((ban[n].addr&0x00ffffff)==(addr&0x00ffffff)) return 1;

        return 0;
}

int god_add_single_ban(int cn,int co,unsigned int addr)
{
	int n;

	for (n=0; n<maxban; n++) {
			if ((ban[n].addr&0x00ffffff)==(addr&0x00ffffff)) {
					do_char_log(cn,2,"%s is already banned\n",ch[co].name);
					return 1;
			}
        }
        for (n=0; n<maxban; n++) {
			if (!ban[n].addr) break;
        }
        if (n+1==MAXBAN) {
                do_char_log(cn,2,"Sorry, ban list is full.\n");
                return 1;
        }
        strcpy(ban[n].creator,ch[cn].name);
        strcpy(ban[n].victim,ch[co].name);
        ban[n].addr=addr;
        if (n==maxban) maxban=n+1;

	do_char_log(cn,2,"Banned %s (%d.%d.%d.%d)\n",ch[co].name,addr&255,(addr>>8)&255,(addr>>16)&255,addr>>24);

	return 1;
}

void god_add_ban(int cn,int co)
{
        int n;

	for (n=80; n<90; n++)
		if (ch[co].data[n]) if (!god_add_single_ban(cn,co,ch[co].data[n])) break;

	chlog(cn,"IMP: banned %s (%d)",ch[co].name,co);

	god_write_banlist();
}

void god_del_ban(int cn,int nr)
{
        if (nr>maxban || !ban[nr].addr) {
                do_char_log(cn,2,"Number out of bounds.\n");
                return;
        }
        ban[nr].addr=0;
        do_char_log(cn,2,"Done.\n");

	god_write_banlist();
}

void god_list_ban(int cn)
{
        int n;

        for (n=0; n<maxban; n++) {
                if (!ban[n].addr) continue;
                do_char_log(cn,2,"%03d: %-10.10s %d.%d.%d.%d (%s)\n",
                        n,ban[n].victim,
                        ban[n].addr&255,(ban[n].addr>>8)&255,(ban[n].addr>>16)&255,ban[n].addr>>24,
                        ban[n].creator);
        }
}

static char **badname=NULL;
static int cursize=0,maxsize=0;

void god_init_badnames(void)
{
        char buf[80],*dst,*src;
        FILE *fp;

        fp=fopen("badnames.txt","r");
        if (!fp) return;

	if (badname) {
		free(badname); badname=NULL;
		cursize=maxsize=0;
	}

        while (fgets(buf,79,fp)) {
                buf[79]=0; // fgets is silly.

                dst=src=buf;

                while (*src) {
                        if (isspace(*src)) { src++; continue; }
                        if (*src=='\r' || *src=='\n') break;
                        *dst++=*src++;
                }
                *dst=0;

                if (strlen(buf)<3) continue;

                if (cursize>=maxsize) {
                        maxsize+=256;
                        badname=realloc(badname,maxsize*sizeof(char**));
                }
                badname[cursize++]=strdup(buf);
        }

        fclose(fp);
}

int god_is_badname(char *name)
{
        int n;

        if (strlen(name)>15) return 1;

        for (n=0; n<cursize; n++) {
                if (strstr(name,badname[n])) return 1;
        }
        return 0;
}

void god_shutup(int cn,int co)
{
	god_set_flag(cn,co,CF_SHUTUP);
	if (ch[cn].flags&(CF_IMP|CF_GOD)) return;
	
	do_imp_log(2,"%s set %s %s shutup (just for info).\n",
		ch[cn].name,ch[co].name,
		(ch[co].flags&CF_SHUTUP) ? "on" : "off");
}

// #shrines <player>: mark all shrines of Kwai as visited and bring the
// player's Seyan'Du sword to its maximum weapon value (15+20*4=95).
void god_shrines(int cn,int co)
{
	int n,in,found=0,bits=SEYAN_SHRINES;

	if (co==0) { do_char_log(cn,0,"No such character.\n"); return; }
	if (!IS_SANECHAR(co) || !IS_USEDCHAR(co)) { do_char_log(cn,0,"Bad character.\n"); return; }
	if (!(ch[co].kindred&KIN_SEYAN_DU)) {
		do_char_log(cn,0,"%s is not a Seyan'Du.\n",ch[co].name);
		return;
	}

	ch[co].data[21]|=SEYAN_SHRINEBITS;	// one bit per shrine

	for (n=1; n<MAXITEM; n++) {
		if (it[n].used!=USE_ACTIVE) continue;
		if (it[n].driver!=40) continue;
		if (it[n].data[0]!=co) continue;

		it[n].weapon[0]=15+bits*4;
		it[n].temp=0;
		it[n].flags|=IF_UPDATE;
		sprintf(it[n].description,"A huge, two-handed sword, engraved with runes and magic symbols. It bears the name %s.",ch[co].name);
		found++;
	}

	if (!found) {	// no sword yet: hand out a new one, no luck cost
		in=god_create_item(682);
		if (!in) { do_char_log(cn,0,"Could not create the sword.\n"); return; }
		it[in].data[0]=co;
		it[in].weapon[0]=15+bits*4;
		it[in].temp=0;
		it[in].flags|=IF_UPDATE;
		sprintf(it[in].description,"A huge, two-handed sword, engraved with runes and magic symbols. It bears the name %s.",ch[co].name);
		if (!god_give_char(in,co)) {
			it[in].used=USE_EMPTY;
			do_char_log(cn,0,"%s's inventory is full.\n",ch[co].name);
			return;
		}
		do_char_log(co,0,"Kwai, the great goddess of war, grants you a new blade.\n");
	}

	do_update_char(co);

	do_char_log(co,1,"You have visited %d of the %d shrines of Kwai.\n",SEYAN_SHRINES,SEYAN_SHRINES);
	if (cn!=co) do_char_log(cn,1,"%s has now visited all %d shrines, sword at %d.\n",ch[co].name,SEYAN_SHRINES,15+bits*4);
	chlog(cn,"IMP: #shrines for %s (%d)",ch[co].name,co);
}

/* ---- prestige and its looks ------------------------------------------------
 * ch.data[CHD_PRESTIGE] counts how often a character has prestiged (gone from
 * an arch class back to the start of its class line; the rules for that are
 * still to be decided). The look follows from it: prestige 1+ Arch-Templars
 * and Arch-Harakim wear a recoloured set (blue / red cape), Seyan'Du amber, installed right
 * after the class's own 448 sprites (Seyan'Du: amber) (tools/sprites/install_variant.py), so
 * the sprite is the template's + 448. Other classes keep their normal look.
 */
int char_looktier(int cn)
{
	if (ch[cn].data[CHD_PRESTIGE]>=1 && (ch[cn].kindred&(KIN_ARCHTEMPLAR|KIN_ARCHHARAKIM|KIN_SEYAN_DU))) return 1;
	return 0;
}

void char_apply_look(int cn)
{
	int t=ch[cn].temp;

	if (t<1 || t>=MAXTCHARS || !ch_temp[t].sprite) return;
	ch[cn].sprite=ch_temp[t].sprite+LOOKTIER_STEP*char_looktier(cn);
}

void god_prestige(int cn,int co,char *arg)
{
	int p;

	if (co==0 || !IS_SANECHAR(co) || !IS_USEDCHAR(co)) { do_char_log(cn,0,"No such character.\n"); return; }
	if (!arg || !*arg) {
		do_char_log(cn,1,"%s is prestige %d. #prestige <player> <n> sets it (0 = none).\n",ch[co].name,ch[co].data[CHD_PRESTIGE]);
		return;
	}
	p=atoi(arg);
	if (p<0 || p>99) { do_char_log(cn,0,"Prestige goes from 0 to 99.\n"); return; }
	ch[co].data[CHD_PRESTIGE]=p;
	char_apply_look(co);
	do_update_char(co);
	chlog(cn,"IMP: set prestige of %s (%d) to %d",ch[co].name,co,p);
	do_char_log(cn,1,"%s is now prestige %d (sprite %d).\n",ch[co].name,p,ch[co].sprite);
	if (co!=cn) do_char_log(co,2,"You are now prestige %d.\n",p);
}
