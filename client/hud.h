/*
 * hud.h - layout of the new (v2) HUD, in HUD units.
 *
 * The HUD canvas is the window size divided by HUD_SCALE. Everything here
 * is in canvas units; the presenter scales the canvas up by HUD_SCALE.
 * engine.c draws the panels, inter.c handles the mouse on them - both use
 * these numbers, so they always agree.
 */
#ifndef HUD_H
#define HUD_H

#define HUD_SCALE_X100	150	// 1.5x

#define HUD_ROW		14	// row height of the stats panels

// stats panel columns (x relative to the panel)
#define HC_NAME		2
#define HC_BASE		106	// blue base value
#define HC_TOT		138	// modified value
#define HC_PLUS		170
#define HC_MINUS	184
#define HC_COST		198
#define HC_END		252
#define HC_SCR		14	// width of the skill scroll column

// stats panel blocks
#define HS_X		0
#define HS_Y		0
#define HS_H1		(8*HUD_ROW+2)			// attributes + hp/end/mana
#define HS_Y2		(HS_Y+HS_H1-2)			// skills block
#define HS_H2		(10*HUD_ROW+2)
#define HS_Y3		(HS_Y2+HS_H2-2)			// update row
#define HS_H3		(HUD_ROW+2)
#define HS_Y4		(HS_Y3+HS_H3+4)			// current/max block
#define HS_W4		(104+2*40)
#define HS_H4		(3*HUD_ROW+2)

// backpack, 4 x 5 slots
#define HB_SLOT		35
#define HB_COLS		4
#define HB_ROWS		5
#define HB_X		(HS_X+HC_END+HC_SCR-2)
#define HB_Y		0
#define HB_W		(HB_COLS*HB_SLOT+16)
#define HB_H		(HB_ROWS*HB_SLOT+4)
#define HB_VISIBLE	(HB_COLS*HB_ROWS)
#define HB_MAXPOS	(40-HB_VISIBLE)

// gold buttons, equipment and character panel: taken from the old HUD
#define HG_LX		219	// gold buttons (legacy rect)
#define HG_LY		176
#define HG_LW		83
#define HG_LH		84
#define HG_X		HB_X
#define HG_Y		(HB_Y+HB_H-2)

#define HE_LX		300	// equipment
#define HE_LY		0
#define HE_LW		74
#define HE_LH		212
#define HE_X		(HB_X+HB_W-2)
#define HE_Y		0

#define HL_LX		372	// character / look panel
#define HL_LY		0
#define HL_LW		128
#define HL_LH		204
#define HL_X		(HE_X+HE_LW-2)
#define HL_Y		0

// chat, top right
#define HCH_COLS	64	// characters per line
#define HCH_LINES	25
#define HCH_W		(HCH_COLS*6+8)
#define HCH_H		(4+HCH_LINES*10+18)

// weapon/armor/exp/load panel under the chat
#define HQ_W		200

// buttons, bottom right: skill buttons over mode buttons
#define HK_BW		64
#define HK_W		(4*HK_BW+2)
#define HK_BH		(3*15+4)
#define HK_GAP		6

// minimap, bottom left
#define HM_SIZE		196
#define HM_ZOOM		2
#define HM_TILES	((HM_SIZE-6)/HM_ZOOM)

// compass (legacy rect), bottom center
#define HCP_LX		277
#define HCP_LY		566
#define HCP_LW		53
#define HCP_LH		30

// shop window (legacy rect), centered
#define HSH_LX		218
#define HSH_LY		255
#define HSH_LW		300
#define HSH_LH		318

extern int hud_cw,hud_ch;	// canvas size (dd.c)

#define HCH_X		(hud_cw-HCH_W)
#define HCH_Y		0
#define HQ_X		(hud_cw-HQ_W)
#define HQ_Y		(HCH_H-2)
#define HK_X		(hud_cw-HK_W)
#define HK_Y2		(hud_ch-HK_BH)			// mode buttons
#define HK_Y1		(HK_Y2-HK_GAP-HK_BH)		// skill buttons
#define HM_X		0
#define HM_Y		(hud_ch-HM_SIZE)
#define HCP_X		(hud_cw/2-HCP_LW/2)
#define HCP_Y		(hud_ch-HCP_LH-2)
#define HSH_X		(hud_cw/2-HSH_LW/2)
#define HSH_Y		(hud_ch/2-HSH_LH/2)

// the server sends tiles 2..TILEX-3 only; the ring outside is never filled
#define VIEW_CUT	2
#define IN_VIEW(x,y)	((x)>=VIEW_CUT && (y)>=VIEW_CUT && (x)<TILEX-VIEW_CUT && (y)<TILEY-VIEW_CUT)

extern int walkmark_x[4],walkmark_y[4];	// auto-walk markers, world coordinates

static int in_rect(int x,int y,int rx,int ry,int rw,int rh) { return x>=rx && y>=ry && x<rx+rw && y<ry+rh; }


// clean theme (hud_theme 2): panel fills and border lines drawn by the
// presenter at full window resolution (canvas units, see dd.c)
#define HUD_RGB_PANEL	0x1F1F22	// deep grey
#define HUD_RGB_LINE	0x7E6F48	// tan
#define VOP_FILL	0
#define VOP_HLINE	1	// a band of h canvas rows starting at y, drawn as one crisp line
#define VOP_VLINE	2	// a band of w canvas columns starting at x
struct hud_vop { short x,y,w,h; unsigned char type; unsigned int rgb; };
int dd_hud_vops(struct hud_vop **p);
int dd_hud_vhit(int x,int y);
extern int hud_theme;

#endif
