#include <windows.h>
#include "common.h"
#include "inter.h"
#include "hud.h"

extern int init_done;
extern unsigned int inv_pos,skill_pos;
extern unsigned int look_nr,look_type;
extern unsigned char inv_block[];
extern int tile_x,tile_y,tile_type;

extern int xoff,yoff;
extern int stat_raised[];
extern int stat_points_used;
extern int noshop;
extern int do_alpha;

void dd_invalidate_alpha(void);

int hightlight=0;
int hightlight_sub=0;
int cursor_type=CT_NONE;
int selected_char=0;
int last_skill=-1;

int xmove=0;

void cmd(int cmd,int x,int y);
void cmd3(int cmd,int x,int y,int z);

int mouse_x=0,mouse_y=0;

int trans_button(int x,int y)
{
	int n;
	int tx,ty;

	if (x>290 && y>1 && x<300 && y<34) return 12;
	if (x>290 && y>141 && x<300 && y<174) return 13;

	if (x>206 && y>113 && x<218 && y<148) return 14;
	if (x>206 && y>218 && x<218 && y<252) return 15;

	tx=x-604;
	ty=y-552;
	for (n=0; n<4; n++) {
		if (tx>=0 && tx<=41 && ty>=0 && ty<=14) {
			hightlight=HL_BUTTONBOX;
			hightlight_sub=n;
			cursor_type=CT_NONE;
			return n;
		}
		tx-=49;
	}

	tx=x-604;
	ty=y-568;
	for (n=0; n<4; n++) {
		if (tx>=0 && tx<=41 && ty>=0 && ty<=14) {
			hightlight=HL_BUTTONBOX;
			hightlight_sub=n+4;
			cursor_type=CT_NONE;
			return n+4;
		}
		tx-=49;
	}

	tx=x-604;
	ty=y-584;
	for (n=0; n<4; n++) {
		if (tx>=0 && tx<=41 && ty>=0 && ty<=14) {
			hightlight=HL_BUTTONBOX;
			hightlight_sub=n+8;
			cursor_type=CT_NONE;
			return n+8;
		}
		tx-=49;
	}

  tx=x-604;
	ty=y-504;
	for (n=0; n<4; n++) {
		if (tx>=0 && tx<=41 && ty>=0 && ty<=14) {
			hightlight=HL_BUTTONBOX;
			hightlight_sub=n;
			cursor_type=CT_NONE;
			return n+16;
		}
		tx-=49;
	}

	tx=x-604;
	ty=y-519;
	for (n=0; n<4; n++) {
		if (tx>=0 && tx<=41 && ty>=0 && ty<=14) {
			hightlight=HL_BUTTONBOX;
			hightlight_sub=n+4;
			cursor_type=CT_NONE;
			return n+20;
		}
		tx-=49;
	}

	tx=x-604;
	ty=y-534;
	for (n=0; n<4; n++) {
		if (tx>=0 && tx<=41 && ty>=0 && ty<=14) {
			hightlight=HL_BUTTONBOX;
			hightlight_sub=n+8;
			cursor_type=CT_NONE;
			return n+24;
		}
		tx-=49;
	}

	return -1;
}

void button_command(int nr)
{
  int sk;

	switch(nr) {
		case	0:	cmd(CL_CMD_MODE,2,0); break;
		case	1:	cmd(CL_CMD_MODE,1,0); break;
		case	2: 	cmd(CL_CMD_MODE,0,0); break;
		case	3: 	pdata.show_proz=1-pdata.show_proz; break;
		case	4:	do_alpha=1-do_alpha; dd_invalidate_alpha(); break;
		case	5: 	pdata.hide=1-pdata.hide; break;
		case	6: 	pdata.show_names=1-pdata.show_names; break;
		case	7: 	break;
		case	11: 	xmove=0; cmd_exit(); break; // exit

		case  12: if (inv_pos>1) inv_pos-=2; break;
		case  13: if (inv_pos<30) inv_pos+=2; break;

		case  14: if (skill_pos>1) skill_pos-=2; break;
		case  15: if (skill_pos<40) skill_pos+=2; break;

     case  16:
     case  17:
     case  18:
     case  19:
     case  20:
     case  21:
     case  22:
     case  23:
     case  24:
     case  25:
     case  26:
     case  27: if ((sk=pdata.xbutton[nr-16].skill_nr)!=-1) {
                    cmd3(CL_CMD_SKILL,sk,selected_char,1); //pdata.xbutton[nr-16].skill_strength);
               } else xlog(1,"This button is unassigned. Right click on a skill/spell, then right click on the button to assign it.");
               break;

		default: break;
	}
}

void button_help(int nr)
{
	switch(nr) {
		case	0:	xlog(1,"F1/FAST: Makes you move faster, but takes a lot more endurance. You will also be seen more easily."); break;
		case	1:	xlog(1,"F2/NORMAL: Move at normal speed. Takes no endurance when not fighting."); break;
		case	2: xlog(1,"F3/SLOW: Makes you move slower. You regain endurance while not fighting. Decreases chances of being seen."); break;
		case	3: xlog(1,"F4/HEALTH: Toggle whether the current health of all characters is displayed."); break;
		case	4:	break;
		case	5: xlog(1,"F6/HIDE: Toggle whether walls and other high objects are displayed."); break;
		case	6: xlog(1,"F7/NAMES: Toggle whether the name of all characters is displayed."); break;
		case	7: break;
		case	11: xlog(1,"F12/EXIT: Leave the game. Will cost you 50%% health and 10%% gold."); break; // exit

		case  12: xlog(1,"Scroll inventory contents up."); break;
		case  13: xlog(1,"Scroll inventory contents down"); break;

		case  14: xlog(1,"Scroll skill list up"); break;
		case  15: xlog(1,"Scroll skill list down"); break;

     case  16:
     case  17:
     case  18:
     case  19:
     case  20:
     case  21:
     case  22:
     case  23:
     case  24:
     case  25:
     case  26:
     case  27: if (last_skill!=-1) {
                  if (skilltab[last_skill].nr==pdata.xbutton[nr-16].skill_nr) {
                    pdata.xbutton[nr-16].skill_nr=-1;
                    strcpy(pdata.xbutton[nr-16].name,"-");
                    xlog(1,"Shift-F%d, now unassigned.",nr-15);
                  } else {
                    pdata.xbutton[nr-16].skill_nr=skilltab[last_skill].nr;
//                    pdata.xbutton[nr-16].skill_strength=1;

                    /*if (skilltab[last_skill].sortkey=='R') {
                         xlog(1,"Shift-F%d, now %s at level %d.",nr-15,skilltab[last_skill].name,skilltab[last_skill].attrib[0]);
                         pdata.xbutton[nr-16].skill_strength=skilltab[last_skill].attrib[0];
                         sprintf(pdata.xbutton[nr-16].name,"%-.5s %d",skilltab[last_skill].name,skilltab[last_skill].attrib[0]);
                    } else {*/
                         xlog(1,"Shift-F%d, now %s.",nr-15,skilltab[last_skill].name);
                         strncpy(pdata.xbutton[nr-16].name,skilltab[last_skill].name,7);
                         pdata.xbutton[nr-16].name[7]=0;
//                    }
                  }
               } else {
                 xlog(1,"Right click on a skill/spell first to assign it to a button.");
               }
               break;

		default: break;
	}
}

void reset_block(void)
{
	int n;

	if (pl.citem) {
		if (pl.citem_p&PL_HEAD) inv_block[WN_HEAD]=0;
		else inv_block[WN_HEAD]=1;
		if (pl.citem_p&PL_NECK) inv_block[WN_NECK]=0;
		else inv_block[WN_NECK]=1;
		if (pl.citem_p&PL_BODY) inv_block[WN_BODY]=0;
		else inv_block[WN_BODY]=1;
		if (pl.citem_p&PL_ARMS) inv_block[WN_ARMS]=0;
		else inv_block[WN_ARMS]=1;
		if (pl.citem_p&PL_BELT) inv_block[WN_BELT]=0;
		else inv_block[WN_BELT]=1;
		if (pl.citem_p&PL_LEGS) inv_block[WN_LEGS]=0;
		else inv_block[WN_LEGS]=1;
		if (pl.citem_p&PL_FEET) inv_block[WN_FEET]=0;
		else inv_block[WN_FEET]=1;
		if (pl.citem_p&PL_WEAPON) inv_block[WN_RHAND]=0;
		else inv_block[WN_RHAND]=1;
		if (pl.citem_p&PL_SHIELD) inv_block[WN_LHAND]=0;
		else inv_block[WN_LHAND]=1;
		if (pl.citem_p&PL_CLOAK) inv_block[WN_CLOAK]=0;
		else inv_block[WN_CLOAK]=1;
     if (pl.citem_p&PL_RING) inv_block[WN_LRING]=inv_block[WN_RRING]=0;
		else inv_block[WN_LRING]=inv_block[WN_RRING]=1;
	} else {
		for (n=0; n<20; n++) inv_block[n]=0;
	}
   if (pl.worn_p[WN_RHAND]&PL_TWOHAND) inv_block[WN_LHAND]=1;
}

int mouse_inventory(int x,int y,int mode)
{
	int nr,keys;
	int tx,ty;

	keys=0;
	if (GetAsyncKeyState(VK_SHIFT)&0x8000) keys|=1;
	if (GetAsyncKeyState(VK_CONTROL)&0x8000) keys|=2;

	// money
	if (y>176 && y<203) {
		if (x>219 && x<246) {
			if (mode==MS_LB_UP) cmd3(CL_CMD_INV,2,1,selected_char);
			if (mode==MS_RB_UP) xlog(1,"1 silver coin.");
			hightlight=HL_MONEY;
			hightlight_sub=1;
			cursor_type=CT_TAKE;
			return 1;
		}
		if (x>247 && x<274) {
			if (mode==MS_LB_UP) cmd3(CL_CMD_INV,2,10,selected_char);
			if (mode==MS_RB_UP) xlog(1,"10 silver coins.");
			hightlight=HL_MONEY;
			hightlight_sub=2;
			cursor_type=CT_TAKE;
			return 1;
		}
		if (x>275 && x<301) {
			if (mode==MS_LB_UP) cmd3(CL_CMD_INV,2,100,selected_char);
			if (mode==MS_RB_UP) xlog(1,"1 gold coin.");
			hightlight=HL_MONEY;
			hightlight_sub=3;
			cursor_type=CT_TAKE;
			return 1;
		}
  }
  if (y>205 && y<231) {
		if (x>219 && x<246) {
			if (mode==MS_LB_UP) cmd3(CL_CMD_INV,2,1000,selected_char);
			if (mode==MS_RB_UP) xlog(1,"10 gold coins.");
			hightlight=HL_MONEY;
			hightlight_sub=4;
			cursor_type=CT_TAKE;
			return 1;
		}
		if (x>247 && x<274) {
			if (mode==MS_LB_UP) cmd3(CL_CMD_INV,2,10000,selected_char);
			if (mode==MS_RB_UP) xlog(1,"100 gold coins.");
			hightlight=HL_MONEY;
			hightlight_sub=5;
			cursor_type=CT_TAKE;
			return 1;
		}
		if (x>275 && x<301) {
			if (mode==MS_LB_UP) cmd3(CL_CMD_INV,2,100000,selected_char);
			if (mode==MS_RB_UP) xlog(1,"1,000 gold coins.");
			hightlight=HL_MONEY;
			hightlight_sub=1;
			cursor_type=CT_TAKE;
			return 1;
		}
  }
 	if (y>232 && y<259 && x>219 && x<246) {
		if (mode==MS_LB_UP) cmd3(CL_CMD_INV,2,1000000,selected_char);
		if (mode==MS_RB_UP) xlog(1,"10,000 gold coins.");
		hightlight=HL_MONEY;
		hightlight_sub=2;
		cursor_type=CT_TAKE;
		return 1;
	}

	// backpack
	if (x>219 && x<288 && y>1 && y<175) {
		tx=(x-219)/35;
		ty=(y-1)/35;

		nr=tx+ty*2;
		if (keys==1) {
			if (mode==MS_LB_UP) cmd3(CL_CMD_INV,0,nr+inv_pos,selected_char);
			else if (mode==MS_RB_UP) cmd3(CL_CMD_INV_LOOK,nr+inv_pos,0,selected_char);
			if (pl.item[nr+inv_pos]) {
				if (pl.citem) cursor_type=CT_SWAP;
				else cursor_type=CT_TAKE;
			} else {
				if (pl.citem) cursor_type=CT_DROP;
				else cursor_type=CT_NONE;
			}
		}
		else if (keys==0) {
			if (mode==MS_LB_UP) cmd3(CL_CMD_INV,6,nr+inv_pos,selected_char);
			else if (mode==MS_RB_UP) cmd3(CL_CMD_INV_LOOK,nr+inv_pos,0,selected_char);
			if (pl.item[nr+inv_pos]) cursor_type=CT_USE;
			else cursor_type=CT_NONE;
		} else cursor_type=CT_NONE;
		hightlight=HL_BACKPACK;
		hightlight_sub=nr+inv_pos;
		return 1;
	}

	// worn
	if (x>302 && x<371 && y>1 && y<175+35) {
		tx=(x-302)/35;
		ty=(y-1)/35;

		if (tx==0 && ty==2) {		// neck
			if (keys==1) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,1,1,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,1,selected_char);
				if (pl.worn[1]) {
					if (pl.citem) cursor_type=CT_SWAP;
					else cursor_type=CT_TAKE;
				} else {
					if (pl.citem) cursor_type=CT_DROP;
					else cursor_type=CT_NONE;
				}
			} else if (keys==0) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,5,1,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,1,selected_char);
				if (pl.worn[1]) cursor_type=CT_USE;
				else cursor_type=CT_NONE;
			} else cursor_type=CT_NONE;
			hightlight=HL_EQUIPMENT;
			hightlight_sub=1;
			return 1;
		}
		if (tx==0 && ty==0) {	// head
			if (keys==1) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,1,0,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,0,selected_char);
				if (pl.worn[0]) {
					if (pl.citem) cursor_type=CT_SWAP;
					else cursor_type=CT_TAKE;
				} else {
					if (pl.citem) cursor_type=CT_DROP;
					else cursor_type=CT_NONE;
				}
			} else if (keys==0) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,5,0,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,0,selected_char);
				if (pl.worn[0]) cursor_type=CT_USE;
				else cursor_type=CT_NONE;
			} else cursor_type=CT_NONE;
			hightlight=HL_EQUIPMENT;
			hightlight_sub=0;
			return 1;
		}
		if (tx==1 && ty==1) {	// arms
			if (keys==1) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,1,3,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,3,selected_char);
				if (pl.worn[3]) {
					if (pl.citem) cursor_type=CT_SWAP;
					else cursor_type=CT_TAKE;
				} else {
					if (pl.citem) cursor_type=CT_DROP;
					else cursor_type=CT_NONE;
				}
			} else if (keys==0) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,5,3,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,3,selected_char);
				if (pl.worn[3]) cursor_type=CT_USE;
				else cursor_type=CT_NONE;
			} else cursor_type=CT_NONE;
			hightlight=HL_EQUIPMENT;
			hightlight_sub=3;
			return 1;
		}
		if (tx==1 && ty==3) {	// lhand
			if (keys==1) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,1,7,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,7,selected_char);
				if (pl.worn[7]) {
					if (pl.citem) cursor_type=CT_SWAP;
					else cursor_type=CT_TAKE;
				} else {
					if (pl.citem) cursor_type=CT_DROP;
					else cursor_type=CT_NONE;
				}
			} else if (keys==0) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,5,7,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,7,selected_char);
				if (pl.worn[7]) cursor_type=CT_USE;
				else cursor_type=CT_NONE;
			} else cursor_type=CT_NONE;
			hightlight=HL_EQUIPMENT;
			hightlight_sub=7;
			return 1;
		}
		if (tx==0 && ty==4) {	// lring
			if (keys==1) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,1,11,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,11,selected_char);
				if (pl.worn[11]) {
					if (pl.citem) cursor_type=CT_SWAP;
					else cursor_type=CT_TAKE;
				} else {
					if (pl.citem) cursor_type=CT_DROP;
					else cursor_type=CT_NONE;
				}
			} else if (keys==0) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,5,11,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,11,selected_char);
				if (pl.worn[11]) cursor_type=CT_USE;
				else cursor_type=CT_NONE;
			} else cursor_type=CT_NONE;
			hightlight=HL_EQUIPMENT;
			hightlight_sub=11;
			return 1;
		}
		if (tx==1 && ty==4) {	// rring
			if (keys==1) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,1,10,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,10,selected_char);
				if (pl.worn[10]) {
					if (pl.citem) cursor_type=CT_SWAP;
					else cursor_type=CT_TAKE;
				} else {
					if (pl.citem) cursor_type=CT_DROP;
					else cursor_type=CT_NONE;
				}
			} else if (keys==0) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,5,10,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,10,selected_char);
				if (pl.worn[11]) cursor_type=CT_USE;
				else cursor_type=CT_NONE;
			} else cursor_type=CT_NONE;
			hightlight=HL_EQUIPMENT;
			hightlight_sub=10;
			return 1;
		}
     if (tx==0 && ty==5) {	// legs
			if (keys==1) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,1,5,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,5,selected_char);
				if (pl.worn[5]) {
					if (pl.citem) cursor_type=CT_SWAP;
					else cursor_type=CT_TAKE;
				} else {
					if (pl.citem) cursor_type=CT_DROP;
					else cursor_type=CT_NONE;
				}
			} else if (keys==0) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,5,5,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,5,selected_char);
				if (pl.worn[5]) cursor_type=CT_USE;
				else cursor_type=CT_NONE;
			} else cursor_type=CT_NONE;
			hightlight=HL_EQUIPMENT;
			hightlight_sub=5;
			return 1;
		}
		if (tx==1 && ty==5) {	// feet
			if (keys==1) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,1,6,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,6,selected_char);
				if (pl.worn[6]) {
					if (pl.citem) cursor_type=CT_SWAP;
					else cursor_type=CT_TAKE;
				} else {
					if (pl.citem) cursor_type=CT_DROP;
					else cursor_type=CT_NONE;
				}
			} else if (keys==0) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,5,6,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,6,selected_char);
				if (pl.worn[6]) cursor_type=CT_USE;
				else cursor_type=CT_NONE;
			} else cursor_type=CT_NONE;
			hightlight=HL_EQUIPMENT;
			hightlight_sub=6;
			return 1;
		}
		if (tx==1 && ty==0) {	// cloak
			if (keys==1) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,1,9,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,9,selected_char);
				if (pl.worn[9]) {
					if (pl.citem) cursor_type=CT_SWAP;
					else cursor_type=CT_TAKE;
				} else {
					if (pl.citem) cursor_type=CT_DROP;
					else cursor_type=CT_NONE;
				}
			} else if (keys==0) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,5,9,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,9,selected_char);
				if (pl.worn[9]) cursor_type=CT_USE;
				else cursor_type=CT_NONE;
			} else cursor_type=CT_NONE;
			hightlight=HL_EQUIPMENT;
			hightlight_sub=9;
			return 1;
		}
		if (tx==0 && ty==3) {	// rhand
			if (keys==1) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,1,8,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,8,selected_char);
				if (pl.worn[8]) {
					if (pl.citem) cursor_type=CT_SWAP;
					else cursor_type=CT_TAKE;
				} else {
					if (pl.citem) cursor_type=CT_DROP;
					else cursor_type=CT_NONE;
				}
			} else if (keys==0) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,5,8,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,8,selected_char);
				if (pl.worn[8]) cursor_type=CT_USE;
				else cursor_type=CT_NONE;
			} else cursor_type=CT_NONE;
			hightlight=HL_EQUIPMENT;
			hightlight_sub=8;
			return 1;
		}
		if (tx==1 && ty==2) {	// belt
			if (keys==1) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,1,4,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,4,selected_char);
				if (pl.worn[4]) {
					if (pl.citem) cursor_type=CT_SWAP;
					else cursor_type=CT_TAKE;
				} else {
					if (pl.citem) cursor_type=CT_DROP;
					else cursor_type=CT_NONE;
				}
			} else if (keys==0) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,5,4,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,4,selected_char);
				if (pl.worn[4]) cursor_type=CT_USE;
				else cursor_type=CT_NONE;
			} else cursor_type=CT_NONE;
			hightlight=HL_EQUIPMENT;
			hightlight_sub=4;
			return 1;
		}
		if (tx==0 && ty==1) {	// body
			if (keys==1) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,1,2,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,2,selected_char);
				if (pl.worn[2]) {
					if (pl.citem) cursor_type=CT_SWAP;
					else cursor_type=CT_TAKE;
				} else {
					if (pl.citem) cursor_type=CT_DROP;
					else cursor_type=CT_NONE;
				}
			} else if (keys==0) {
				if (mode==MS_LB_UP) cmd3(CL_CMD_INV,5,2,selected_char);
				else if (mode==MS_RB_UP) cmd3(CL_CMD_INV,7,2,selected_char);
				if (pl.worn[2]) cursor_type=CT_USE;
				else cursor_type=CT_NONE;
			} else cursor_type=CT_NONE;
			hightlight=HL_EQUIPMENT;
			hightlight_sub=2;
			return 1;
		}
	}

	return 0;
}

int mouse_buttonbox(int x,int y,int state)
{
	int nr;

	nr=trans_button(x,y);
	if (nr==-1) return 0;

	if (state==MS_LB_UP) button_command(nr);
  if (state==MS_RB_UP) button_help(nr);

	return 1;
}

int _mouse_statbox(int x,int y,int state)
{
	int n,m;

	// update:
	if (x>109 && y>254 && x<158 && y<266) {
		hightlight=HL_STATBOX;
		hightlight_sub=0;
		if (state==MS_RB_UP) xlog(1,"Make the changes permanent");
		if (state!=MS_LB_UP) return 1;

		stat_points_used=0;

		for (n=0; n<108; n++) {
			if (stat_raised[n]) {
				if (n>7) {
					m=skilltab[n-8].nr+8;
				} else m=n;
				cmd(CL_CMD_STAT,m,stat_raised[n]);
			}
			stat_raised[n]=0;
		}
		return 1;
	}

	if (x<133) return 0;
	if (x>157) return 0;
	if (y<2) return 0;
	if (y>251) return 0;

	n=(y-2)/14;

	hightlight=HL_STATBOX;
	hightlight_sub=n;

	if (x<145) { // raise
		if (state==MS_RB_UP) {
			if (n<5) xlog(1,"Raise %s.",at_name[n]);
			else if (n==5) xlog(1,"Raise Hitpoints.");
			else if (n==6) xlog(1,"Raise Endurance.");
			else if (n==7) xlog(1,"Raise Mana.");
			else xlog(1,"Raise %s.",skilltab[n-8+skill_pos].name);
			return 1;
		}
		if (state!=MS_LB_UP) return 1;

		if (n<5) {
			if (attrib_needed(n,pl.attrib[n][0]+stat_raised[n])>pl.points-stat_points_used) return 1;
			stat_points_used+=attrib_needed(n,pl.attrib[n][0]+stat_raised[n]);
			stat_raised[n]++;
			return 1;
		} else if (n==5) {
			if (hp_needed(pl.hp[0]+stat_raised[n])>pl.points-stat_points_used) return 1;
			stat_points_used+=hp_needed(pl.hp[0]+stat_raised[n]);
			stat_raised[n]++;
			return 1;
		} else if (n==6) {
			if (end_needed(pl.end[0]+stat_raised[n])>pl.points-stat_points_used) return 1;
			stat_points_used+=end_needed(pl.end[0]+stat_raised[n]);
			stat_raised[n]++;
			return 1;
		} else if (n==7) {
			if (mana_needed(pl.mana[0]+stat_raised[n])>pl.points-stat_points_used) return 1;
			stat_points_used+=mana_needed(pl.mana[0]+stat_raised[n]);
			stat_raised[n]++;
			return 1;
		} else {
			m=skilltab[n-8+skill_pos].nr;
			if (skill_needed(m,pl.skill[m][0]+stat_raised[n+skill_pos])>pl.points-stat_points_used) return 1;
			stat_points_used+=skill_needed(m,pl.skill[m][0]+stat_raised[n+skill_pos]);
			stat_raised[n+skill_pos]++;
			return 1;
		}
	} else { // lower
		if (state==MS_RB_UP) {
			if (n<5) xlog(1,"Lower %s.",at_name[n]);
			else if (n==5) xlog(1,"Lower Hitpoints.");
			else if (n==6) xlog(1,"Lower Endurance.");
			else if (n==7) xlog(1,"Lower Mana.");
			else xlog(1,"Lower %s.",skilltab[n-8+skill_pos].name);
			return 1;
		}
		if (state!=MS_LB_UP) return 1;

		if (n<5) {
			if (!stat_raised[n]) return 1;
			stat_raised[n]--;
			stat_points_used-=attrib_needed(n,pl.attrib[n][0]+stat_raised[n]);
			return 1;
		} else if (n==5) {
			if (!stat_raised[n]) return 1;
			stat_raised[n]--;
			stat_points_used-=hp_needed(pl.hp[0]+stat_raised[n]);
			return 1;
		} else if (n==6) {
			if (!stat_raised[n]) return 1;
			stat_raised[n]--;
			stat_points_used-=end_needed(pl.end[0]+stat_raised[n]);
			return 1;
		} else if (n==7) {
			if (!stat_raised[n]) return 1;
			stat_raised[n]--;
			stat_points_used-=mana_needed(pl.mana[0]+stat_raised[n]);
			return 1;
		} else {
			if (!stat_raised[n+skill_pos]) return 1;
			m=skilltab[n-8+skill_pos].nr;
			stat_raised[n+skill_pos]--;
			stat_points_used-=skill_needed(m,pl.skill[m][0]+stat_raised[n+skill_pos]);
			return 1;
		}
	}
}

int mouse_statbox(int x,int y,int state)
{
    int n,m,keys,ret;

    keys=0;
	  if (GetAsyncKeyState(VK_SHIFT)&0x8000) keys|=1;
	  if (GetAsyncKeyState(VK_CONTROL)&0x8000) keys|=2;

    if (state==MS_LB_UP) {
       if (keys&2) m=90;
       else if (keys&1) m=10;
       else m=1;
    } else m=1;

    for (n=0; n<m; n++) ret=_mouse_statbox(x,y,state);

    return ret;
}

int mouse_statbox2(int x,int y,int state)
{
	int n;
    extern struct skilltab _skilltab[];

	if (x<2) return 0;
	if (x>108) return 0;
	if (y<114) return 0;
	if (y>251) return 0;

	n=(y-114)/14;

	hightlight=HL_STATBOX2;
	hightlight_sub=n;

	if (state==MS_RB_UP) {
		if (pl.skill[skilltab[n+skill_pos].nr][0]) {
        xlog(1,skilltab[n+skill_pos].desc);
        last_skill=n+skill_pos;
        /*if (skilltab[n+skill_pos].sortkey=='R') {
                skilltab[n+skill_pos].attrib[0]++;
                if (skilltab[n+skill_pos].attrib[0]>9) skilltab[n+skill_pos].attrib[0]=1;
                nr=skilltab[n+skill_pos].nr;
                sprintf(skilltab[n+skill_pos].name,"%s %d",_skilltab[nr].name,skilltab[n+skill_pos].attrib[0]);
                xlog(1,"Spell Level %d set.",skilltab[n+skill_pos].attrib[0]);
        }*/
     }
	} else if (state==MS_LB_UP) {
		cmd3(CL_CMD_SKILL,skilltab[n+skill_pos].nr,selected_char,skilltab[n+skill_pos].attrib[0]);
	}
	return 1;
}

void cmd(int cmd,int x,int y)
{
	unsigned char buf[16];

	play_sound("sfx\\click.wav",-1000,0);

	buf[0]=(char)cmd;
	*(unsigned short*)(buf+1)=(short)x;
	*(unsigned long*)(buf+3)=(long)y;
	xsend(buf);
}

void cmds(int cmd,int x,int y)
{
	unsigned char buf[16];

	buf[0]=(char)cmd;
	*(unsigned short*)(buf+1)=(short)x;
	*(unsigned long*)(buf+3)=(long)y;
	xsend(buf);
}

void cmd3(int cmd,int x,int y,int z)
{
	unsigned char buf[16];

	play_sound("sfx\\click.wav",-1000,0);

	buf[0]=(char)cmd;
	*(unsigned long*)(buf+1)=x;
	*(unsigned long*)(buf+5)=y;
	*(unsigned long*)(buf+9)=z;
	xsend(buf);
}

void cmd1(int cmd,int x)
{
	unsigned char buf[16];

	play_sound("sfx\\click.wav",-1000,0);

	buf[0]=(char)cmd;
	*(unsigned int*)(buf+1)=x;
	xsend(buf);
}

void cmd1s(int cmd,int x)
{
	unsigned char buf[16];

	buf[0]=(char)cmd;
	*(unsigned int*)(buf+1)=x;
	xsend(buf);
}

void mouse_mapbox(int x,int y,int state)
{
	int mx,my,m,keys;

	x+=176-16;
	y+=8;

	mx=2*y+x-(YPOS*2)-XPOS+((TILEX-34)/2*32);
	my=x-2*y+(YPOS*2)-XPOS+((TILEX-34)/2*32);;

	// auto-walk markers (x,y here are world coordinates, before the shift above)
	{
		int k,wx=x-(176-16),wy=y-8;
		for (k=0; k<4; k++) {
			if (abs(wx-walkmark_x[k])<16 && abs(wy-walkmark_y[k])<9) {
				if (state==MS_LB_UP) xmove=k+1;	// 1=N 2=W 3=S 4=E, as before
				return;
			}
		}
	}

	// the whole view is clickable
        if (mx<2*32 || mx>=(TILEX-2)*32 || my<2*32 || my>=(TILEY-2)*32) return;

	mx=mx/32;
	my=my/32;

        tile_x=-1; tile_y=-1; tile_type=-1;
	if (mx<2 || mx>TILEX-3) return;
	if (my<2 || my>TILEY-3) return;

	m=mx+my*TILEX;

//	xlog("light=%d",map[m].light);
//  xlog("ch_sprite=%d, nr=%d, id=%d",map[m].ch_sprite,map[m].ch_nr,map[m].ch_id);

	if (pl.citem==46) { // build
		if (state==MS_RB_UP) { xmove=0; cmd(CL_CMD_DROP,map[m].x,map[m].y); }
		if (state==MS_LB_UP) { xmove=0; cmd(CL_CMD_PICKUP,map[m].x,map[m].y); }
		tile_type=0; tile_x=mx; tile_y=my;
		hightlight=HL_MAP;
		return;
	}

	keys=0;
	if (GetAsyncKeyState(VK_SHIFT)&0x8000) keys|=1;
	if (GetAsyncKeyState(VK_CONTROL)&0x8000) keys|=2;
	if (GetAsyncKeyState(VK_MENU)&0x8000) keys|=4;

	if (keys==0) {
		tile_x=mx; tile_y=my;
		tile_type=0;

		if (state==MS_RB_UP) { xmove=0; cmd(CL_CMD_TURN,map[m].x,map[m].y); }
		if (state==MS_LB_UP) { xmove=0; cmd(CL_CMD_MOVE,map[m].x,map[m].y); }
		hightlight=HL_MAP;
		cursor_type=CT_WALK;
		return;
	}

	if (keys==1) {
		if (pl.citem) { hightlight=HL_MAP; cursor_type=CT_DROP; }
		else if (map[m].flags&ISITEM) ;
		else if (map[m+1-TILEX].flags&ISITEM) { mx++; my--; }
		else if (map[m+2-2*TILEX].flags&ISITEM) { mx+=2; my-=2; }
		else if (map[m+1].flags&ISITEM) { mx++; }
		else if (map[m+TILEX].flags&ISITEM) { my++; }
		else if (map[m-1].flags&ISITEM) { mx--; }
		else if (map[m-TILEX].flags&ISITEM) { my--; }
		else if (map[m+1+TILEX].flags&ISITEM) { mx++; my++; }
		else if (map[m-1+TILEX].flags&ISITEM) { mx--; my++; }
		else if (map[m-1-TILEX].flags&ISITEM) { mx--; my--; }
		else if (map[m+2].flags&ISITEM) { mx+=2; }
		else if (map[m+2*TILEX].flags&ISITEM) { my+=2; }
		else if (map[m-2].flags&ISITEM) { mx-=2; }
		else if (map[m-2*TILEX].flags&ISITEM) { my-=2; }
		else if (map[m+1+2*TILEX].flags&ISITEM) { mx++; my+=2; }
		else if (map[m-1+2*TILEX].flags&ISITEM) { mx--; my+=2; }
		else if (map[m+1-2*TILEX].flags&ISITEM) { mx++; my-=2; }
		else if (map[m-1-2*TILEX].flags&ISITEM) { mx--; my-=2; }
		else if (map[m+2+1*TILEX].flags&ISITEM) { mx+=2; my++; }
		else if (map[m-2+1*TILEX].flags&ISITEM) { mx-=2; my++; }
		else if (map[m+2-1*TILEX].flags&ISITEM) { mx+=2; my--; }
		else if (map[m-2-1*TILEX].flags&ISITEM) { mx-=2; my--; }
		else if (map[m+2+2*TILEX].flags&ISITEM) { mx+=2; my+=2; }
		else if (map[m-2+2*TILEX].flags&ISITEM) { mx-=2; my+=2; }
		else if (map[m-2-2*TILEX].flags&ISITEM) { mx-=2; my-=2; }

		m=mx+my*TILEX;
		tile_x=mx; tile_y=my;

		if (pl.citem && map[m].flags&ISITEM) { if (map[m].flags&ISUSABLE) cursor_type=CT_USE; else cursor_type=CT_NONE; }
		else if (map[m].flags&ISITEM) { hightlight=HL_MAP; if (map[m].flags&ISUSABLE) cursor_type=CT_USE; else cursor_type=CT_TAKE; }

		if (pl.citem && !(map[m].flags&ISITEM)) {
			if (state==MS_LB_UP) { xmove=0; cmd(CL_CMD_DROP,map[m].x,map[m].y); }
			tile_type=0;
		}
		if ((map[m].flags&ISITEM)) {
			if (state==MS_LB_UP) {
				if (map[m].flags&ISUSABLE) { xmove=0; cmd(CL_CMD_USE,map[m].x,map[m].y); noshop=0; }
				else { xmove=0; cmd(CL_CMD_PICKUP,map[m].x,map[m].y); }
			}
			if (state==MS_RB_UP) { xmove=0; cmd(CL_CMD_LOOK_ITEM,map[m].x,map[m].y); }
			tile_type=1;
		}
		return;
	}

	if (keys==2) {
		if (map[m].flags&ISCHAR) hightlight=HL_MAP;
		else if (map[m+1-TILEX].flags&ISCHAR) { mx++; my--; hightlight=HL_MAP; }
		else if (map[m+2-2*TILEX].flags&ISCHAR) { mx+=2; my-=2; hightlight=HL_MAP; }
		else if (map[m+1].flags&ISCHAR) { mx++; hightlight=HL_MAP; }
		else if (map[m+TILEX].flags&ISCHAR) { my++; hightlight=HL_MAP; }
		else if (map[m-1].flags&ISCHAR) { mx--; hightlight=HL_MAP; }
		else if (map[m-TILEX].flags&ISCHAR) { my--; hightlight=HL_MAP; }
		else if (map[m+1+TILEX].flags&ISCHAR) { mx++; my++; hightlight=HL_MAP; }
		else if (map[m-1+TILEX].flags&ISCHAR) { mx--; my++; hightlight=HL_MAP; }
		else if (map[m-1-TILEX].flags&ISCHAR) { mx--; my--; hightlight=HL_MAP; }
		else if (map[m+2].flags&ISCHAR) { mx+=2; hightlight=HL_MAP; }
		else if (map[m+2*TILEX].flags&ISCHAR) { my+=2; hightlight=HL_MAP; }
		else if (map[m-2].flags&ISCHAR) { mx-=2; hightlight=HL_MAP; }
		else if (map[m-2*TILEX].flags&ISCHAR) { my-=2; hightlight=HL_MAP; }
		else if (map[m+1+2*TILEX].flags&ISCHAR) { mx++; my+=2; hightlight=HL_MAP; }
		else if (map[m-1+2*TILEX].flags&ISCHAR) { mx--; my+=2; hightlight=HL_MAP; }
		else if (map[m+1-2*TILEX].flags&ISCHAR) { mx++; my-=2; hightlight=HL_MAP; }
		else if (map[m-1-2*TILEX].flags&ISCHAR) { mx--; my-=2; hightlight=HL_MAP; }
		else if (map[m+2+1*TILEX].flags&ISCHAR) { mx+=2; my++; hightlight=HL_MAP; }
		else if (map[m-2+1*TILEX].flags&ISCHAR) { mx-=2; my++; hightlight=HL_MAP; }
		else if (map[m+2-1*TILEX].flags&ISCHAR) { mx+=2; my--; hightlight=HL_MAP; }
		else if (map[m-2-1*TILEX].flags&ISCHAR) { mx-=2; my--; hightlight=HL_MAP; }
		else if (map[m+2+2*TILEX].flags&ISCHAR) { mx+=2; my+=2; hightlight=HL_MAP; }
		else if (map[m-2+2*TILEX].flags&ISCHAR) { mx-=2; my+=2; hightlight=HL_MAP; }
		else if (map[m-2-2*TILEX].flags&ISCHAR) { mx-=2; my-=2; hightlight=HL_MAP; }

		m=mx+my*TILEX;
		tile_x=mx; tile_y=my;

      if (map[m].flags&ISCHAR) {
			if (pl.citem) cursor_type=CT_GIVE;
			else cursor_type=CT_HIT;
		}

		if (map[m].flags&ISCHAR) {
			if (pl.citem && state==MS_LB_UP) { xmove=0; cmd1(CL_CMD_GIVE,map[m].ch_nr); }
			else if (state==MS_LB_UP) { xmove=0; cmd1(CL_CMD_ATTACK,map[m].ch_nr); }
			else if (state==MS_RB_UP) { xmove=0; cmd1(CL_CMD_LOOK,map[m].ch_nr); noshop=0; }
			tile_type=2;
		}
	}

	if (keys==4) {
		if (map[m].flags&ISCHAR) hightlight=HL_MAP;
		else if (map[m+1-TILEX].flags&ISCHAR) { mx++; my--; hightlight=HL_MAP; }
		else if (map[m+2-2*TILEX].flags&ISCHAR) { mx+=2; my-=2; hightlight=HL_MAP; }
		else if (map[m+1].flags&ISCHAR) { mx++; hightlight=HL_MAP; }
		else if (map[m+TILEX].flags&ISCHAR) { my++; hightlight=HL_MAP; }
		else if (map[m-1].flags&ISCHAR) { mx--; hightlight=HL_MAP; }
		else if (map[m-TILEX].flags&ISCHAR) { my--; hightlight=HL_MAP; }
		else if (map[m+1+TILEX].flags&ISCHAR) { mx++; my++; hightlight=HL_MAP; }
		else if (map[m-1+TILEX].flags&ISCHAR) { mx--; my++; hightlight=HL_MAP; }
		else if (map[m-1-TILEX].flags&ISCHAR) { mx--; my--; hightlight=HL_MAP; }
		else if (map[m+2].flags&ISCHAR) { mx+=2; hightlight=HL_MAP; }
		else if (map[m+2*TILEX].flags&ISCHAR) { my+=2; hightlight=HL_MAP; }
		else if (map[m-2].flags&ISCHAR) { mx-=2; hightlight=HL_MAP; }
		else if (map[m-2*TILEX].flags&ISCHAR) { my-=2; hightlight=HL_MAP; }
		else if (map[m+1+2*TILEX].flags&ISCHAR) { mx++; my+=2; hightlight=HL_MAP; }
		else if (map[m-1+2*TILEX].flags&ISCHAR) { mx--; my+=2; hightlight=HL_MAP; }
		else if (map[m+1-2*TILEX].flags&ISCHAR) { mx++; my-=2; hightlight=HL_MAP; }
		else if (map[m-1-2*TILEX].flags&ISCHAR) { mx--; my-=2; hightlight=HL_MAP; }
		else if (map[m+2+1*TILEX].flags&ISCHAR) { mx+=2; my++; hightlight=HL_MAP; }
		else if (map[m-2+1*TILEX].flags&ISCHAR) { mx-=2; my++; hightlight=HL_MAP; }
		else if (map[m+2-1*TILEX].flags&ISCHAR) { mx+=2; my--; hightlight=HL_MAP; }
		else if (map[m-2-1*TILEX].flags&ISCHAR) { mx-=2; my--; hightlight=HL_MAP; }
		else if (map[m+2+2*TILEX].flags&ISCHAR) { mx+=2; my+=2; hightlight=HL_MAP; }
		else if (map[m-2+2*TILEX].flags&ISCHAR) { mx-=2; my+=2; hightlight=HL_MAP; }
		else if (map[m-2-2*TILEX].flags&ISCHAR) { mx-=2; my-=2; hightlight=HL_MAP; }

		m=mx+my*TILEX;
		tile_x=mx; tile_y=my;

		if (map[m].flags&ISCHAR) {
			cursor_type=CT_SEL;
			if (state==MS_LB_UP) { xmove=0; if (selected_char==map[m].ch_nr) selected_char=0; else selected_char=map[m].ch_nr; }
			else if (state==MS_RB_UP) { xmove=0; cmd1(CL_CMD_LOOK,map[m].ch_nr); noshop=0; }
			tile_type=2;
		} else if (state==MS_LB_UP) selected_char=0;
	}
}

int mouse_shop(int x,int y,int mode)
{
	int nr;
	int tx,ty;

	if (!show_shop) return 0;

	if (x>499 && x<516 && y>260 && y<274) {
		if (mode==MS_LB_UP) { show_shop=0; noshop=QSIZE*36; }
		return 1;
	}

	if (x>220 && x<500 && y>261 && y<485+32+35) {
		tx=(x-220)/35;
		ty=(y-261)/35;

		nr=tx+ty*8;
		if (mode==MS_LB_UP) cmd(CL_CMD_SHOP,shop.nr,nr);
     if (mode==MS_RB_UP) cmd(CL_CMD_SHOP,shop.nr,nr+62);

		if (shop.item[nr]) { cursor_type=CT_TAKE; }
		else if (pl.citem) { cursor_type=CT_DROP; }
		hightlight=HL_SHOP;
		hightlight_sub=nr;
		return 1;
	}
	return 0;
}


/* ===================================================================
   v2 HUD mouse handling (canvas coordinates, layout from hud.h).
   Where a panel works like the old one, the position is translated to the
   old 800x600 coordinates and the original handler does the work.
   =================================================================== */

int mouse_cx=0,mouse_cy=0;	// mouse on the HUD canvas

static void hud_button(int nr,int state)
{
	hightlight=HL_BUTTONBOX;
	hightlight_sub=nr;
	cursor_type=CT_NONE;
	if (state==MS_LB_UP) button_command(nr);
	if (state==MS_RB_UP) button_help(nr);
}

static void hud_backpack(int nr,int mode)
{
	int keys=0;

	if (GetAsyncKeyState(VK_SHIFT)&0x8000) keys|=1;
	if (GetAsyncKeyState(VK_CONTROL)&0x8000) keys|=2;

	nr+=inv_pos;
	if (keys==1) {
		if (mode==MS_LB_UP) cmd3(CL_CMD_INV,0,nr,selected_char);
		else if (mode==MS_RB_UP) cmd3(CL_CMD_INV_LOOK,nr,0,selected_char);
		if (pl.item[nr]) cursor_type=pl.citem ? CT_SWAP : CT_TAKE;
		else cursor_type=pl.citem ? CT_DROP : CT_NONE;
	} else if (keys==0) {
		if (mode==MS_LB_UP) cmd3(CL_CMD_INV,6,nr,selected_char);
		else if (mode==MS_RB_UP) cmd3(CL_CMD_INV_LOOK,nr,0,selected_char);
		cursor_type=pl.item[nr] ? CT_USE : CT_NONE;
	} else cursor_type=CT_NONE;
	hightlight=HL_BACKPACK;
	hightlight_sub=nr;
}

// returns 1 if (x,y) is on a panel (even if nothing happens there)
int hud_mouse(int x,int y,int state)
{
	int n,c,r,lrow;

	// shop window (on top of everything)
	if (show_shop && in_rect(x,y,HSH_X,HSH_Y,HSH_LW,HSH_LH)) {
		mouse_shop(x-HSH_X+HSH_LX,y-HSH_Y+HSH_LY,state);
		return 1;
	}

	// gold buttons, equipment, character panel: old handlers
	if (in_rect(x,y,HG_X,HG_Y,HG_LW,HG_LH)) { mouse_inventory(x-HG_X+HG_LX,y-HG_Y+HG_LY,state); return 1; }
	if (in_rect(x,y,HE_X,HE_Y,HE_LW,HE_LH)) { mouse_inventory(x-HE_X+HE_LX,y-HE_Y+HE_LY,state); return 1; }
	if (in_rect(x,y,HL_X,HL_Y,HL_LW,HL_LH)) { mouse_inventory(x-HL_X+HL_LX,y-HL_Y+HL_LY,state); return 1; }

	// backpack 4x5 + scroll column
	if (in_rect(x,y,HB_X,HB_Y,HB_W,HB_H)) {
		if (x>=HB_X+HB_COLS*HB_SLOT) {
			if (state==MS_LB_UP) {
				if (y<HB_Y+HB_H/2) inv_pos=(inv_pos>=HB_COLS) ? inv_pos-HB_COLS : 0;
				else inv_pos=(inv_pos+HB_COLS<=HB_MAXPOS) ? inv_pos+HB_COLS : HB_MAXPOS;
			}
			return 1;
		}
		c=(x-HB_X-1)/HB_SLOT; r=(y-HB_Y-1)/HB_SLOT;
		if (c<0) c=0;
		if (c>=HB_COLS) c=HB_COLS-1;
		if (r<0) r=0;
		if (r>=HB_ROWS) r=HB_ROWS-1;
		hud_backpack(c+r*HB_COLS,state);
		return 1;
	}

	// stats: attributes/hp/end/mana (rows 0-7) and skills (rows 8-17)
	lrow=-1;
	if (in_rect(x,y,HS_X,HS_YH,HC_END,HS_HH-2)) return 1;	// header row
	if (in_rect(x,y,HS_X,HS_Y,HC_END,HS_H1)) lrow=(y-HS_Y)/HUD_ROW;
	else if (in_rect(x,y,HS_X,HS_Y2,HC_END+HC_SCR,HS_H2)) {
		if (x>=HS_X+HC_END-2) {		// skill scroll column
			if (y<HS_Y2+HS_H2/2) hud_button(14,state);
			else hud_button(15,state);
			return 1;
		}
		n=(y-HS_Y2)/HUD_ROW;
		if (n>9) n=9;
		if (x<HS_X+HC_BASE-2) {		// skill name: right click = description/assign, left click = use
			mouse_statbox2(50,114+n*14+7,state);
			return 1;
		}
		lrow=8+n;
	}
	if (lrow>=0) {
		if (lrow>17) lrow=17;
		if (x>=HS_X+HC_PLUS-2 && x<HS_X+HC_MINUS-2) mouse_statbox(139,2+lrow*14+7,state);		// raise
		else if (x>=HS_X+HC_MINUS-2 && x<HS_X+HC_COST-2) mouse_statbox(151,2+lrow*14+7,state);	// lower
		return 1;
	}

	// update
	if (in_rect(x,y,HS_X+HC_TOT-2,HS_Y3,HC_END-HC_TOT+2,HS_H3)) { mouse_statbox(130,260,state); return 1; }
	if (in_rect(x,y,HS_X,HS_Y4,HS_W4,HS_H4)) return 1;

	// skill buttons / mode buttons
	if (in_rect(x,y,HK_X,HK_Y1,HK_W,HK_BH) || in_rect(x,y,HK_X,HK_Y2,HK_W,HK_BH)) {
		int y0=in_rect(x,y,HK_X,HK_Y1,HK_W,HK_BH) ? HK_Y1 : HK_Y2;
		c=(x-HK_X)/HK_BW; r=(y-y0-2)/15;
		if (c<0) c=0;
		if (c>3) c=3;
		if (r<0) r=0;
		if (r>2) r=2;
		if (y0==HK_Y1) hud_button(16+r*4+c,state);
		else hud_button(r*4+c,state);
		return 1;
	}

	// compass: click an arm to walk far in that direction
	if (in_rect(x,y,HCP_X,HCP_Y,HCP_LW,HCP_LH)) {
		if (state==MS_LB_UP) {
			int left=(x<HCP_X+HCP_LW/2),top=(y<HCP_Y+HCP_LH/2);
			if (left && top) xmove=1;		// N
			else if (!left && top) xmove=4;		// E
			else if (left) xmove=2;			// W
			else xmove=3;				// S
		}
		return 1;
	}

	// chat, weapon/armor/exp, minimap: nothing to click
	if (in_rect(x,y,HCH_X,HCH_Y,HCH_W,HCH_H)) return 1;
	if (in_rect(x,y,HQ_X,HQ_Y,HQ_W,4*HUD_ROW+2)) return 1;
	if (in_rect(x,y,HM_X,HM_Y,HM_SIZE,HM_SIZE)) return 1;

	return 0;
}

// called by the window code: on_hud says whether the mouse is over a HUD
// pixel; cx,cy = canvas position, gx,gy = world (1280x960) position
void mouse2(int on_hud,int cx,int cy,int gx,int gy,int state)
{
	if (!init_done) return;

	hightlight=0;
	cursor_type=CT_NONE;

	mouse_cx=cx; mouse_cy=cy;
	mouse_x=gx; mouse_y=gy;

	if (on_hud && hud_mouse(cx,cy,state)) return;
	mouse_mapbox(gx,gy,state);
}

// mouse wheel over the HUD: lines>0 = wheel up
void hud_wheel(int x,int y,int lines)
{
	extern int logstart,logtimer;

	if (in_rect(x,y,HCH_X,HCH_Y,HCH_W,HCH_H)) {
		logstart+=lines*3;
		if (logstart>HCH_LINES*10-HCH_LINES) logstart=HCH_LINES*10-HCH_LINES;
		if (logstart<0) logstart=0;
		logtimer=TICKS*30;
	} else if (in_rect(x,y,HS_X,HS_Y2,HC_END+HC_SCR,HS_H2)) {
		int pos=(int)skill_pos-lines*2;
		if (pos<0) pos=0;
		if (pos>40) pos=40;
		skill_pos=pos;
	} else if (in_rect(x,y,HB_X,HB_Y,HB_W,HB_H)) {
		int pos=(int)inv_pos-lines*HB_COLS;
		if (pos<0) pos=0;
		if (pos>HB_MAXPOS) pos=HB_MAXPOS;
		inv_pos=pos;
	}
}
