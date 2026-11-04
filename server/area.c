/*************************************************************************

This file is part of 'Mercenaries of Astonia v2'
Copyright (c) 1997-2001 Daniel Brockhaus (joker@astonia.com)
All rights reserved.

**************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <string.h>

#include "server.h"

struct area {
        int x1,y1;
        int x2,y2;
        char *name;
        int flag;       // 0=in, 1=the, 2=on, 3=at
};

static struct area builtin_area[]={
        {481,407,       633,596,        "Aston",                        0},
        {497,205,       537,233,        "Lizard Temple",                1},
        {480,234,       634,405,        "Strange Forest",               1},
        {840,0,         1024,157,       "Underground I",                0},
        {491,504,       520,520,        "Temple of Skua",               1},
        {520,524,       529,534,        "Leather Armor Shop",           1},
        {539,525,       548,532,        "Jamil's House",                0},
        {545,536,       564,548,        "Temple of the Purple One",     1},
        {499,539,       528,550,        "Thieves House I",              1},
        { 20, 20,        49, 69,        "Thieves Basement",              1},
        {499,525,       514,538,        "Thieves House II",             1},
        {532,399,       536,568,        "Temple Street",                2},     // the whole stretch, town gate to the Gorn Clan Hall
        {537,551,       578,555,        "Rose Street",                  2},
        {538,559,       575,588,        "Cursed Tomb",                  1},
        {574,496,       578,550,        "Castle Way",                   2},
        {588,530,       623,554,        "Haunted Castle",               1},
        {562,525,       570,531,        "Inga's House",                 0},
        {582,519,       587,524,        "Jefferson's House",            0},
        {582,510,       591,514,        "Steel Armor Shop",             1},
        {554,509,       570,520,        "Joe's House",                  0},
        {582,498,       588,505,        "Bronze Armor Shop",            1},
        {569,468,       582,487,        "Damor's Magic Shop",           0},
        {558,481,       567,487,        "Brunhild's Shop",              0},
        {555,499,       563,504,        "Sirjan's House",               0},
        {540,498,       550,504,        "Crystal Armor Shop",           1},     // Geoffrey; was labelled Cloth Armor Shop
        {540,507,       550,517,        "Cloth Armor Shop",             1},     // Ruth, across from the Temple of Skua
        {540,479,       553,487,        "Weapon Shop",                  1},
        {507,482,       514,487,        "Tavern of the Blue Ogre",      1},
        {515,436,       522,444,        "Bank",                         1},
        {493,479,       503,486,        "Bank",                         1},     // across from the Temple of Skua
        {484,442,       488,490,        "Arena Street",                 2},
        {489,442,       508,446,        "Arena Street",                 2},
        {540,442,       546,451,        "Cirrus' House",                0},
        {621,440,       627,446,        "Gunther's House",              0},
        {621,481,       628,487,        "Robin's House",                0},
        {607,423,       613,431,        "Syleia's House",               0},     // just south of the Dungeon of Doors
        {483,497,       490,501,        "Gina's Shop",                  0},     // by Merchant's Way, right outside the mines
        {539,411,       546,417,        "Garna's Shop",                 0},
        {539,424,       547,431,        "Manfred's House",              0},
        {548,411,       557,422,        "Barracks",                     1},
        {550,424,       557,431,        "Leopold's House",              0},
        {521,450,       528,459,        "Serena's House",               0},
        {540,456,       564,474,        "Magic Maze",                   1},
        {520,464,       529,472,        "Steven's House",               0},     // the house only, not the arena north of it
        {519,477,       527,484,        "Golden Armor Shop",            1},
        {537,434,       616,438,        "New Street",                   2},
        {559,442,       565,448,        "Gordon's House",               0},
        {571,442,       577,448,        "Nasir's House",                0},
        {582,442,       610,462,        "Templar Outlaws",              3},
        {614,434,       618,495,        "South End",                    2},
        {590,467,       610,488,        "Skeleton Lord",                3},
        {537,491,       613,495,        "Merchant's Way",               2},
        {464,491,       531,495,        "Merchant's Way",               2},     // north of Temple Street, up to the mines
        {593,498,       601,505,        "Ingrid's House",               0},
        {501,400,       526,432,        "Abandoned Kwai Clan Hall",     1},
        {500,558,       525,590,        "Abandoned Gorn Clan Hall",     1},
        {493,448,       519,476,        "Arena",                        1},
        {411,331,       478,394,        "Black Stronghold",             1},
        {561,410,       604,430,        "Dungeon of Doors",             1},

        {125,57,        197,131,        "Random Dungeon",               1},

        {411,460,       479,529,        "Mine, 1st Level",              1},
        {771, 20,       839, 89,        "Mine, 2nd Level",              1},
        {700, 20,       768, 89,        "Mine, 3rd Level",              1},

        { 52, 52,       105,104,        "Labyrinth, Grolm Gorge",       1},
        { 58,158,       154,212,        "Labyrinth, Lizard Gorge",      1},
        { 30,236,       151,307,        "Labyrinth, Spellcaster Gorge", 1},
        { 25,330,       110,375,        "Labyrinth, Knight Gorge",      1},
        { 16,385,       119,455,        "Labyrinth, Undead Gorge",      1},
        { 16,459,        56,487,        "Labyrinth, Undead Gorge",      1},
        { 16,489,        81,529,        "Labyrinth, Light&Dark Gorge",  1},
        { 16,529,        81,591,        "Labyrinth, Water Gorge",       1},

        { 16,593,        37,602,        "Labyrinth, Final Entry",       1},
        { 16,602,        48,608,        "Labyrinth, Final Preparations",1},
        { 38,593,        48,602,        "Labyrinth, Final Test",        1},
        { 49,593,        80,608,        "Labyrinth, Final Reward",      1},
        { 15,611,       126,703,        "Labyrinth, Forest Gorge",      1},
        {112,703,       126,708,        "Labyrinth, Forest Gorge",      1},
        { 15,704,        66,724,        "Labyrinth, Riddle Gorge",      1},
        { 15,724,        48,804,        "Labyrinth, Riddle Gorge",      1},
        { 15,804,        37,812,        "Labyrinth, Riddle Gorge",      1},
        {180,900,       299,999,        "Labyrinth, Sunken Dark",       1},
        {181,936,       202,962,        "Entry Hall",                   1},
        {203,924,       238,969,        "Atrium",                       1},
        {239,924,       274,969,        "Library",                      1},
        {275,901,       298,998,        "Crypt",                        1},
        {203,970,       274,998,        "Cistern",                      1},
        {181,963,       202,998,        "Vault",                        1},
        { 49,779,       118,894,        "Labyrinth, Seasons Gorge",     1},
        { 49,779,        57,786,        "Hourglass Chamber",            1},
        { 50,787,       117,804,        "Summer",                       0},
        { 89,805,       117,847,        "Summer",                       0},
        { 50,805,        88,848,        "Spring",                       0},
        { 51,826,        59,834,        "Inn",                          1},
        { 89,848,       117,887,        "Fall",                         0},
        {103,888,       112,894,        "Fall",                         0},
        { 50,849,        88,887,        "Winter",                       0},
        { 76,842,        82,847,        "Shrine of Change",             1},
        {212, 50,       305,104,        "Spider Underground",           1},
        {210,120,       270,162,        "Ghost Underground",            1},
        {210,300,       410,600,        "Pentagram Quest",              1},
        {368,246,       408,299,        "Ice Pentagram Quest",          1},
        {330,264,       367,299,        "Ice Pentagram Quest",          1},
        {265,225,       367,263,        "Underwater Pentagram Quest",   1},
        {265,264,       329,293,        "Underwater Pentagram Quest",   1},
        {265,294,       320,300,        "Underwater Pentagram Quest",   1},

        {822,176,      1020,333,        "Underground II",               1},

        {776,793,       821,824,        "Elysium",                      1},

        {367,227,       410,244,        "Gargoyle's Nest",              1},
        {410,227,       480,329,        "Gargoyle's Nest",              1},
        {  1,  1,        20, 20,        "Aston",                        0},

	{622,466,       629,477,        "Astonian Inn",                 1},
	{630,466,       633,481,        "Astonian Inn",                 1},
	{ 61,122,        65,131,        "Astonian Inn",                 1},
	{ 53,118,        60,124,        "Astonian Inn",                 1},
	{ 36,106,        52,141,        "Astonian Inn",                 1},
	{ 29,137,        38,144,        "Astonian Inn",                 1},

	{578,566,       633,596,        "Memorial Park",                1},

	{820,158,       851,161,        "Staffers Corner",              1},
	{807,151,       819,168,        "Staffers Corner",              1},
	{793,146,       805,156,        "Staffers Corner",              1},
	{799,158,       805,168,        "Staffers Corner",              1},
	{794,163,       798,165,        "Staffers Corner",              1},

	{632,240,       647,257,        "Tower I",                  1},
	{822,337,       837,352,        "Tower II",                  1},
	{824,360,       839,373,        "Tower III",                  1},
	{823,380,       838,395,        "Tower IV",                  1},
	{822,401,       837,416,        "Tower V",                  1},
	{822,420,       838,435,        "Tower VI",                  1},
	{844,337,       860,350,        "Tower VII",                  1},
	{844,354,       860,368,        "Tower VIII",                  1},
	{845,374,       861,389,        "Tower IX",                  1},
	{844,395,       860,411,        "Tower X",                  1},
	{844,415,       860,430,        "Tower XI",                  1},
	{867,337,       885,356,        "Tower XII",                  1},
	{865,361,       882,376,        "Tower XIII",                  1},
	{865,380,       883,396,        "Tower XIV",                  1},
	{870,400,       886,424,        "Tower XV",                  1},
	{865,416,       869,424,        "Tower XV",                  1},
	{892,337,       916,359,        "Tower XVI",                  1},
	{892,360,       908,378,        "Tower XVI",                  1},
	{892,386,       911,406,        "Tower XVII",                  1},
	{890,410,       909,429,        "Tower XVIII",                  1},
	{921,337,       940,356,        "Tower XIX",                  1},
	
	{926,360,       940,378,        "Tower XX",                  1},
	{924,379,       942,404,        "Tower XX",                  1},
	{921,405,       945,415,        "Tower XX",                  1},	

	{411,436,       476,456,        "Pentagram Quest",              1},
	{597,600,       619,619,        "Aston Hall",              	0},

	{529,198,	537,204,        "Lizard Temple Shrine",         1},
	{321,294,	327,300,        "Ice Pents Shrine",         	1},
	{529,198,	537,204,        "Lizard Temple Shrine",         1},
        {577,597,	596,628,	"Aston Hall",			1},
	{597,620,	619,628,	"Aston Hall",			1},
	{620,597,	633,628,	"Aston Hall",			1},
	{597,597,	619,599,	"Aston Hall",			1},
	{836,151,	846,154,	"Underground I",		1},
	{479,360,	479,363,        "Black Stronghold",             1},
	{634,466,	639,477,	"Astonian Inn",			1},
	{532,406,	536,406,        "Aston",             		0},
        {469,457,	473,459,	"Pentagram Quest",		1}

};

/* Zones. A zone is one name made of one or more boxes: every box with the same name is part of
 * the same zone (so odd shapes are several boxes), and the zone is listed once. The zones come from
 * .dat/zones.dat ("x1 y1 x2 y2 flag name", one box per line, # for comments; written by the MyV2
 * Editor) when it exists; else from the table above. "zonereload" on the console reads it again. */

#define ZONE_FILE DATDIR"/zones.dat"
#define MAXZONEBOX 2000

static struct area *area=builtin_area;
static int area_cnt=sizeof(builtin_area)/sizeof(builtin_area[0]);
static int zones_loaded=0;
static struct area zbox[MAXZONEBOX];
static char *zname=NULL;		// the names of zbox[], one block

// read zones.dat; returns the number of boxes, 0 = no file (the built-in table is used), -1 = error (kept as it was)
int zone_load(void)
{
	FILE *f;
	char line[256],*p,*pool;
	int cnt=0,x1,y1,x2,y2,fl,k,len=0,bad=0;
	static struct area tmp[MAXZONEBOX];

	zones_loaded=1;
	if (!(f=fopen(ZONE_FILE,"r"))) { area=builtin_area; area_cnt=sizeof(builtin_area)/sizeof(builtin_area[0]); return 0; }
	if (!(pool=malloc(MAXZONEBOX*48))) { fclose(f); return -1; }
	while (fgets(line,sizeof(line),f)) {
		for (p=line; *p==' ' || *p=='\t'; p++) ;
		if (*p=='#' || *p=='\n' || *p=='\r' || !*p) continue;
		if (sscanf(p,"%d %d %d %d %d %n",&x1,&y1,&x2,&y2,&fl,&k)<5 || cnt>=MAXZONEBOX) { bad++; continue; }
		p+=k;
		k=strcspn(p,"\r\n"); while (k>0 && (p[k-1]==' ' || p[k-1]=='\t')) k--;
		if (x2>=MAPX) x2=MAPX-1;
		if (y2>=MAPY) y2=MAPY-1;
		if (k<1 || k>45 || x1>x2 || y1>y2 || x1<0 || y1<0 || fl<0 || fl>3) { bad++; continue; }
		memcpy(pool+len,p,k); pool[len+k]=0;
		tmp[cnt].x1=x1; tmp[cnt].y1=y1; tmp[cnt].x2=x2; tmp[cnt].y2=y2; tmp[cnt].flag=fl;
		tmp[cnt].name=(char*)(long)len;
		len+=k+1; cnt++;
	}
	fclose(f);
	if (cnt<1) { free(pool); return -1; }
	for (k=0; k<cnt; k++) { zbox[k]=tmp[k]; zbox[k].name=pool+(long)tmp[k].name; }
	if (zname) free(zname);
	zname=pool; area=zbox; area_cnt=cnt;
	if (bad) xlog("zones.dat: %d line(s) not understood",bad);
	return cnt;
}

int zone_count(void)
{
	int n,m,cnt=0;
	if (!zones_loaded) zone_load();
	for (n=0; n<area_cnt; n++) {
		for (m=0; m<n; m++) if (!strcmp(area[m].name,area[n].name)) break;
		if (m==n) cnt++;
	}
	return cnt;
}

int zone_boxes(void)
{
	if (!zones_loaded) zone_load();
	return area_cnt;
}

static int in_box(int n,int x,int y)
{
	return x>=area[n].x1 && y>=area[n].y1 && x<=area[n].x2 && y<=area[n].y2;
}

// box n contains x,y and is the first box of its zone that does (so a zone is listed once)
static int first_hit(int n,int x,int y)
{
	int m;
	if (!in_box(n,x,y)) return 0;
	for (m=0; m<n; m++) if (in_box(m,x,y) && !strcmp(area[m].name,area[n].name)) return 0;
	return 1;
}

static void area_text(char *buf,int x,int y,int verbose,int cap)
{
	int n,flag=0;

	buf[0]=0;
	if (!zones_loaded) zone_load();
	for (n=0; n<area_cnt; n++) {
		if (!first_hit(n,x,y)) continue;
		if (strlen(buf)+strlen(area[n].name)+12>500) break;
		if (verbose) {		// "In Aston, in the Bank", "on Temple Street", "at Skeleton Lord"
			static char *pre[4]={"in ","in the ","on ","at "};
			char *w=pre[area[n].flag&3];
			if (flag) strcat(buf,", ");
			strcat(buf,w);
			if (!flag && cap) buf[0]=toupper(buf[0]);
			flag=1;
			strcat(buf,area[n].name);
		} else {
			if (!flag) flag=1;
			else strcat(buf,", ");
			strcat(buf,area[n].name);
		}
	}
}

// return a description of the area character cn is in
char *get_area(int cn,int verbose)
{
	static char buf[512];

	buf[0]=0;
	if (cn<1 || cn>=MAXCHARS) return buf;
	area_text(buf,ch[cn].x,ch[cn].y,verbose,1);
	return buf;
}

/* where someone lives, as players would say it: "Aston, New Street". The building they stand in
 * (the smallest zone around them, all its boxes), the street its front door opens onto (doors are
 * items with driver 2 on the edge of the building's boxes; else the street closest to the building),
 * with the town around it. Outside town: the area's own name. Streets are the zones with flag 2.
 * Used by #quest. */
static int area_gap(int x1,int y1,int x2,int y2,int n)	// rectangle to box n, in tiles (0 = touching)
{
	int dx=0,dy=0;
	if (area[n].x1>x2) dx=area[n].x1-x2; else if (x1>area[n].x2) dx=x1-area[n].x2;
	if (area[n].y1>y2) dy=area[n].y1-y2; else if (y1>area[n].y2) dy=y1-area[n].y2;
	return dx>dy ? dx : dy;
}

static int zone_size(int h)	// tiles in all the boxes of h's zone (overlaps counted twice; only used to compare)
{
	int n,size=0;
	for (n=0; n<area_cnt; n++) if (!strcmp(area[n].name,area[h].name)) size+=(area[n].x2-area[n].x1+1)*(area[n].y2-area[n].y1+1);
	return size;
}

char *get_area_street(int x,int y)
{
	static char buf[200];
	int n,b,h=-1,hs=0,town=-1,best=-1,bd=99,d,xx,yy,in,size;

	buf[0]=0;
	if (!zones_loaded) zone_load();
	for (n=0; n<area_cnt; n++) {
		if (!in_box(n,x,y)) continue;
		if (town<0) town=n;
		size=zone_size(n);
		if (h<0 || size<hs) { h=n; hs=size; }
	}
	if (h<0) return buf;
	if (area[h].flag==2) best=h;			// standing on a street
	else if (hs<=2500) {				// a building: the street in front of its doors
		for (b=0; b<area_cnt; b++) {
			if (strcmp(area[b].name,area[h].name)) continue;
			for (yy=area[b].y1-1; yy<=area[b].y2+1; yy++) for (xx=area[b].x1-1; xx<=area[b].x2+1; xx++) {
				if (xx<1 || yy<1 || xx>=MAPX || yy>=MAPY) continue;
				in=map[xx+yy*MAPX].it;
				if (in<=0 || in>=MAXITEM || it[in].used==USE_EMPTY || (it[in].driver!=2 && it[in].driver!=20)) continue;
				for (n=0; n<area_cnt; n++) if (area[n].flag==2 && (d=area_gap(xx,yy,xx,yy,n))<bd && d<=12) { bd=d; best=n; }
			}
		}
		if (best<0) for (b=0; b<area_cnt; b++) {
			if (strcmp(area[b].name,area[h].name)) continue;
			for (n=0; n<area_cnt; n++) if (area[n].flag==2 && (d=area_gap(area[b].x1,area[b].y1,area[b].x2,area[b].y2,n))<bd && d<=6) { bd=d; best=n; }
		}
	} else {					// out in the open: a street close by
		for (n=0; n<area_cnt; n++) if (area[n].flag==2 && (d=area_gap(x,y,x,y,n))<bd && d<=6) { bd=d; best=n; }
	}
	if (best>=0) {
		if (town>=0 && strcmp(area[town].name,area[best].name) && strcmp(area[town].name,area[h].name)) snprintf(buf,sizeof(buf),"%s, %s",area[town].name,area[best].name);
		else snprintf(buf,sizeof(buf),"%s",area[best].name);
	} else snprintf(buf,sizeof(buf),"%s",area[h].name);
	return buf;
}

//return the area description for x,y
char *get_area_m(int x,int y,int verbose)
{
	static char buf[512];

	area_text(buf,x,y,verbose,0);
	return buf;
}
