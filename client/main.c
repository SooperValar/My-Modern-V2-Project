#include <stdio.h>
#include <malloc.h>
#include <fcntl.h>
#include <io.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <windows.h>
#include <windowsx.h>
#include <mmsystem.h>
#include <process.h>
#include <signal.h>
#include "dd.h"
#include "common.h"
#include "inter.h"
#include "hud.h"

extern int RED,GREEN,BLUE,RGBM,MAXXOVER;
extern char *DDERR;
extern int dd_cache_hit,dd_cache_miss,MAXCACHE,invisible,cachex,cachey,MAXXOVER;
extern int pskip,pidle;
extern int maxmem,usedmem,maxvid,usedvid;
extern int noshop;
void dd_invalidate_cache(void);
void conv_init(void);
int init_pnglib(void);

extern int cursor_type;
HCURSOR cursor[10];

void cmd(int cmd,int x,int y);

int quit=0;
char host_addr[84]={MHOST};
int host_port=5555;

extern char path[];
extern int tricky_flag;

HWND desk_hwnd;
HINSTANCE hinst;

int init_sound(HWND hwnd);
void engine(void);

#define MWORD 2048

char input[128];
int in_len=0;
int cur_pos=0;
int hist_nr=0;
int view_pos=0;
int tabmode=0;
int tabstart=0;
int logstart=0;
int logtimer=0;

// chat window area in game coordinates (see engine.c, log is drawn at x=500)
#define CHAT_X1			496
#define CHAT_Y2			240
#define CHAT_WHEEL_LINES	3
#define CHAT_MAXSCROLL		(22*10-22)	// XLL-LL in engine.c

// skill list (left) and backpack, incl. their scroll bars (see inter.c trans_button)
#define SKILL_X2		218
#define SKILL_Y1		113
#define SKILL_Y2		252
#define INV_X1			218
#define INV_X2			300
#define INV_Y2			174

extern unsigned int inv_pos,skill_pos;
int do_alpha=2;
int do_shadow=1;

void dd_invalidate_alpha(void);

char history[20][128];
int hist_len[20]={0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};
char words[MWORD][40];

#define xisalpha(a) (((a)=='#') || (isalpha(a)))

void complete_word(void)
{
	int n=0,z,pos;
	char buf[40];

	if (cur_pos<1) return;

	for (z=cur_pos-1; z>=0; z--) if (!xisalpha(input[z])) {
			z++; break;
		}
	if (z<0) z=0;
	while (z<cur_pos && n<39) buf[n++]=input[z++];
	buf[n]=0;

	if (n<1) return;

	for (z=tabstart; z<MWORD; z++) {
		if (!strncmp(buf,words[z],n) && strlen(words[z])>(unsigned)n) {
			pos=cur_pos;
			while (pos<115 && words[z][n]) input[pos++]=words[z][n++];
			if (pos<115) input[pos++]=' ';
			in_len=pos;
			tabmode=1;
			tabstart=z+1;
			return;
		}
	}
	tabmode=0;
	tabstart=0;
	in_len=cur_pos;
}

void add_word(char *buf)
{
	int n;

	for (n=0; n<MWORD-1; n++)
		if (!strcmp(words[n],buf)) break;

	memmove(words[1],words[0],n*40);
	memcpy(words[0],buf,40);
}

void add_words(void)
{
	char buf[40];
	int z1=0,z2;

	while (input[z1]) {
		z2=0;
		while (xisalpha(input[z1]) && z2<39) {
			buf[z2++]=input[z1++];
		}
		buf[z2]=0;
		add_word(buf);
		while (input[z1] && !xisalpha(input[z1])) z1++;
	}
}

HBRUSH dlg_back;
int dlg_col,dlg_fcol;

extern int blockcnt,blocktot,blockgc;
int mx=0,my=0;
extern int tile_x,tile_y;

void say(char *input)
{
	int n;
	char buf[16];
	buf[0]=CL_CMD_INPUT1;
	for (n=0; n<15; n++)
		buf[n+1]=input[n];
	xsend(buf);

	buf[0]=CL_CMD_INPUT2;
	for (n=0; n<15; n++)
		buf[n+1]=input[n+15];
	xsend(buf);

	buf[0]=CL_CMD_INPUT3;
	for (n=0; n<15; n++)
		buf[n+1]=input[n+30];
	xsend(buf);

	buf[0]=CL_CMD_INPUT4;
	for (n=0; n<15; n++)
		buf[n+1]=input[n+45];
	xsend(buf);

	buf[0]=CL_CMD_INPUT5;
	for (n=0; n<15; n++)
		buf[n+1]=input[n+60];
	xsend(buf);

	buf[0]=CL_CMD_INPUT6;
	for (n=0; n<15; n++)
		buf[n+1]=input[n+75];
	xsend(buf);

	buf[0]=CL_CMD_INPUT7;
	for (n=0; n<15; n++)
		buf[n+1]=input[n+90];
	xsend(buf);

	buf[0]=CL_CMD_INPUT8;
	for (n=0; n<15; n++)
		buf[n+1]=input[n+105];
	xsend(buf);
}

int do_ticker=1;
extern int gamma;
extern int usedvidmem;

extern int alphapix,fullpix;


// ---------------------------------------------------------------------------
// PORT: windowed / borderless-fullscreen presenter.
//
// The original switched the monitor into an exclusive 800x600 16 bit
// DirectDraw mode. Modern Windows and GPUs handle that badly (black screen,
// crash right after login). Now the game renders into a memory buffer and we
// scale it into a normal window with GDI. Alt+Enter toggles fullscreen,
// which is a borderless window covering the monitor (no mode change).
// ---------------------------------------------------------------------------

int fullscreen=0;
static RECT dst_rect={0,0,SCREEN_W,SCREEN_H};	// where the game image is drawn in the client area
static WINDOWPLACEMENT win_place={sizeof(WINDOWPLACEMENT)};
static int win_shown=0;
static int smooth_scale=1;

int dd_hud_canvas(int w,int h);
unsigned short *dd_hud_canvas_bits(int *w,int *h,int *pitch);
void mouse2(int on_hud,int cx,int cy,int gx,int gy,int state);
void hud_wheel(int x,int y,int lines);

static int client_w=0,client_h=0;

// world zoom: show a centered part of the 1280x960 world, scaled up.
// client.ini [display] zoom=115 means 115%.
static int world_zoom=115;
extern int hud_theme;	// dd.c
static int crop_x=0,crop_y=0,crop_w=SCREEN_W,crop_h=SCREEN_H;

static void calc_crop(void)
{
	int cy;

	if (world_zoom<100) world_zoom=100;
	if (world_zoom>200) world_zoom=200;
	crop_w=SCREEN_W*100/world_zoom;
	crop_h=SCREEN_H*100/world_zoom;
	crop_x=(SCREEN_W-crop_w)/2;
	cy=460;				// shows the world lower in the window (the top HUD is taller)
	crop_y=cy-crop_h/2;
	if (crop_y<0) crop_y=0;
	if (crop_y+crop_h>SCREEN_H) crop_y=SCREEN_H-crop_h;
}

static void calc_dst_rect(void)
{
	RECT cr;
	int cw,ch,dw,dh;

	GetClientRect(desk_hwnd,&cr);
	cw=cr.right-cr.left;
	ch=cr.bottom-cr.top;
	if (cw<1 || ch<1) { SetRect(&dst_rect,0,0,SCREEN_W,SCREEN_H); return; }
	client_w=cw; client_h=ch;

	calc_crop();

	// world: as large as possible, 4:3
	if (cw*SCREEN_H>ch*SCREEN_W) {
		dh=ch;
		dw=ch*SCREEN_W/SCREEN_H;
	} else {
		dw=cw;
		dh=cw*SCREEN_H/SCREEN_W;
	}
	dst_rect.left=(cw-dw)/2;
	dst_rect.top=(ch-dh)/2;
	dst_rect.right=dst_rect.left+dw;
	dst_rect.bottom=dst_rect.top+dh;

	// HUD canvas covers the whole window at 1/1.5 size
	dd_hud_canvas((cw*100+HUD_SCALE_X100-1)/HUD_SCALE_X100,(ch*100+HUD_SCALE_X100-1)/HUD_SCALE_X100);
}

// back buffer the frame is assembled in (32 bit, window size)
static HDC bb_dc=NULL;
static HBITMAP bb_bmp=NULL,bb_old=NULL;
static unsigned int *bb_bits=NULL;
static int bb_w=0,bb_h=0;

// per column/row: first canvas pixel and its weight (0..256) for the 1.5x filter
static int *sx_i=NULL,*sx_w=NULL,*sy_i=NULL,*sy_w=NULL;

static int backbuffer(HDC dc,int w,int h)
{
	BITMAPINFO bi;
	int n;
	double a,e,f;

	if (bb_dc && bb_w==w && bb_h==h) return 1;

	if (bb_dc) { SelectObject(bb_dc,bb_old); DeleteObject(bb_bmp); DeleteDC(bb_dc); bb_dc=NULL; }

	memset(&bi,0,sizeof(bi));
	bi.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);
	bi.bmiHeader.biWidth=w;
	bi.bmiHeader.biHeight=-h;
	bi.bmiHeader.biPlanes=1;
	bi.bmiHeader.biBitCount=32;
	bi.bmiHeader.biCompression=BI_RGB;

	bb_dc=CreateCompatibleDC(dc);
	if (!bb_dc) return 0;
	bb_bmp=CreateDIBSection(dc,&bi,DIB_RGB_COLORS,(void**)&bb_bits,NULL,0);
	if (!bb_bmp) { DeleteDC(bb_dc); bb_dc=NULL; return 0; }
	bb_old=SelectObject(bb_dc,bb_bmp);
	bb_w=w; bb_h=h;

	// area filter tables: output pixel X covers canvas [X/s,(X+1)/s), s=1.5
	free(sx_i); free(sx_w); free(sy_i); free(sy_w);
	sx_i=malloc(w*sizeof(int)); sx_w=malloc(w*sizeof(int));
	sy_i=malloc(h*sizeof(int)); sy_w=malloc(h*sizeof(int));
	f=100.0/HUD_SCALE_X100;
	for (n=0; n<w; n++) {
		a=n*f; e=(n+1)*f;
		sx_i[n]=(int)a;
		sx_w[n]=(e<=sx_i[n]+1) ? 256 : (int)(256*((sx_i[n]+1)-a)/(e-a));
	}
	for (n=0; n<h; n++) {
		a=n*f; e=(n+1)*f;
		sy_i[n]=(int)a;
		sy_w[n]=(e<=sy_i[n]+1) ? 256 : (int)(256*((sy_i[n]+1)-a)/(e-a));
	}
	return 1;
}

// clean theme: panel fills / border lines at full resolution (canvas units -> window pixels)
#define CW2W(c)	((c)*HUD_SCALE_X100/100)

static void fill_rect(int x0,int y0,int x1,int y1,unsigned int rgb)
{
	int x,y;
	unsigned int *d;
	if (x0<0) x0=0;
	if (y0<0) y0=0;
	if (x1>bb_w) x1=bb_w;
	if (y1>bb_h) y1=bb_h;
	for (y=y0; y<y1; y++) { d=bb_bits+y*bb_w; for (x=x0; x<x1; x++) d[x]=rgb; }
}

static void draw_vops(int lines)
{
	struct hud_vop *v;
	int n,cnt,a,b;

	cnt=dd_hud_vops(&v);
	for (n=0; n<cnt; n++,v++) {
		if (!lines && v->type==VOP_FILL)
			fill_rect(CW2W(v->x),CW2W(v->y),CW2W(v->x+v->w),CW2W(v->y+v->h),v->rgb);
		else if (lines && v->type==VOP_HLINE) {
			a=CW2W(v->y); b=CW2W(v->y+v->h); a=(a+b-1)/2;
			fill_rect(CW2W(v->x),a,CW2W(v->x+v->w),a+1,v->rgb);
		} else if (lines && v->type==VOP_VLINE) {
			a=CW2W(v->x); b=CW2W(v->x+v->w); a=(a+b-1)/2;
			fill_rect(a,CW2W(v->y),a+1,CW2W(v->y+v->h),v->rgb);
		} else if (lines && (v->type==VOP_TRIUP || v->type==VOP_TRIDOWN)) {
			int x0=CW2W(v->x),x1=CW2W(v->x+v->w),y0=CW2W(v->y),y1=CW2W(v->y+v->h),r,hw,c2,k;
			c2=x0+x1;	// twice the centre
			for (r=y0; r<y1; r++) {
				k=(v->type==VOP_TRIUP) ? r-y0+1 : y1-r;		// rows from the tip
				hw=k*(x1-x0)/(y1-y0);				// full width at this row
				if (hw<1) hw=1;
				fill_rect((c2-hw)/2,r,(c2+hw+1)/2,r+1,v->rgb);
			}
		}
	}
}

// lay the HUD canvas (565, color key = transparent) over the back buffer
static void blend_hud(void)
{
	unsigned short *src,*r0,*r1,v;
	int sw,sh,sp,X,Y,x0,x1,y1,wx,wy,w[4],k,a;
	unsigned int *d,c,acc_r,acc_g,acc_b;
	unsigned short smp[4];

	src=dd_hud_canvas_bits(&sw,&sh,&sp);
	if (!src || !sx_i) return;

	for (Y=0; Y<bb_h; Y++) {
		if (sy_i[Y]>=sh) break;
		r0=src+sy_i[Y]*sp;
		y1=sy_i[Y]+1; if (y1>=sh) y1=sh-1;
		r1=src+y1*sp;
		wy=sy_w[Y];
		d=bb_bits+Y*bb_w;
		for (X=0; X<bb_w; X++) {
			x0=sx_i[X]; if (x0>=sw) break;
			x1=x0+1; if (x1>=sw) x1=sw-1;
			smp[0]=r0[x0]; smp[1]=r0[x1]; smp[2]=r1[x0]; smp[3]=r1[x1];
			if (smp[0]==0xF81F && smp[1]==0xF81F && smp[2]==0xF81F && smp[3]==0xF81F) continue;
			wx=sx_w[X];
			w[0]=wx*wy; w[1]=(256-wx)*wy; w[2]=wx*(256-wy); w[3]=(256-wx)*(256-wy);
			acc_r=acc_g=acc_b=0; a=0;
			for (k=0; k<4; k++) {
				if (!w[k] || (v=smp[k])==0xF81F) continue;
				acc_r+=((v>>11)<<3)*w[k];
				acc_g+=(((v>>5)&63)<<2)*w[k];
				acc_b+=((v&31)<<3)*w[k];
				a+=w[k];
			}
			if (!a) continue;
			c=d[X];
			acc_r+=((c>>16)&255)*(65536-a);
			acc_g+=((c>>8)&255)*(65536-a);
			acc_b+=(c&255)*(65536-a);
			d[X]=((acc_r>>16)<<16)|((acc_g>>16)<<8)|(acc_b>>16);
		}
	}
}

void win_present(unsigned short *bits,int w,int h)
{
	struct {
		BITMAPINFOHEADER h;
		DWORD masks[3];
	} bmi;
	HDC dc;
	RECT cr;
	int dw,dh;

	if (!desk_hwnd || !win_shown) return;

	GetClientRect(desk_hwnd,&cr);
	if (cr.right<1 || cr.bottom<1) return;

	dc=GetDC(desk_hwnd);
	if (!dc) return;
	if (!backbuffer(dc,cr.right,cr.bottom)) { ReleaseDC(desk_hwnd,dc); return; }

	memset(&bmi,0,sizeof(bmi));
	bmi.h.biSize=sizeof(BITMAPINFOHEADER);
	bmi.h.biWidth=w;
	bmi.h.biHeight=-h;	// top-down
	bmi.h.biPlanes=1;
	bmi.h.biBitCount=16;
	bmi.h.biCompression=BI_BITFIELDS;
	bmi.masks[0]=0xF800;
	bmi.masks[1]=0x07E0;
	bmi.masks[2]=0x001F;

	dw=dst_rect.right-dst_rect.left;
	dh=dst_rect.bottom-dst_rect.top;

	// world
	PatBlt(bb_dc,0,0,bb_w,bb_h,BLACKNESS);
	if (smooth_scale && (dw%crop_w || dh%crop_h)) {
		SetStretchBltMode(bb_dc,HALFTONE);
		SetBrushOrgEx(bb_dc,0,0,NULL);
	} else SetStretchBltMode(bb_dc,COLORONCOLOR);
	bmi.h.biHeight=-crop_h;		// rows from crop_y on; row stride stays w
	StretchDIBits(bb_dc,dst_rect.left,dst_rect.top,dw,dh,crop_x,0,crop_w,crop_h,bits+crop_y*w,(BITMAPINFO*)&bmi,DIB_RGB_COLORS,SRCCOPY);
	GdiFlush();

	// HUD on top: panel fills, canvas content, border lines
	draw_vops(0);
	blend_hud();
	draw_vops(1);

	BitBlt(dc,0,0,bb_w,bb_h,bb_dc,0,0,SRCCOPY);
	ReleaseDC(desk_hwnd,dc);
}

// translate window client coordinates into world (1280x960) coordinates
static void map_mouse(LPARAM lParam,int *x,int *y)
{
	int cx=GET_X_LPARAM(lParam),cy=GET_Y_LPARAM(lParam);
	int dw=dst_rect.right-dst_rect.left,dh=dst_rect.bottom-dst_rect.top;

	if (dw<1 || dh<1) { *x=cx; *y=cy; return; }

	*x=crop_x+(cx-dst_rect.left)*crop_w/dw;
	*y=crop_y+(cy-dst_rect.top)*crop_h/dh;

	if (*x<0) *x=0;
	if (*x>SCREEN_W-1) *x=SCREEN_W-1;
	if (*y<0) *y=0;
	if (*y>SCREEN_H-1) *y=SCREEN_H-1;
}

// is there HUD under this window position? (canvas coordinates returned)
static int hud_at(int wx,int wy,int *cx,int *cy)
{
	unsigned short *src;
	int sw,sh,sp;

	*cx=wx*100/HUD_SCALE_X100;
	*cy=wy*100/HUD_SCALE_X100;
	src=dd_hud_canvas_bits(&sw,&sh,&sp);
	if (!src || *cx<0 || *cy<0 || *cx>=sw || *cy>=sh) return 0;
	return src[*cx+*cy*sp]!=0xF81F || dd_hud_vhit(*cx,*cy);
}

static int last_wx=-1,last_wy=-1;

static void on_mouse(LPARAM lParam,int state)
{
	int cx,cy,on;

	last_wx=GET_X_LPARAM(lParam);
	last_wy=GET_Y_LPARAM(lParam);
	map_mouse(lParam,&mx,&my);
	on=hud_at(last_wx,last_wy,&cx,&cy);
	mouse2(on,cx,cy,mx,my,state);
}

// re-evaluate the hover state every frame (the HUD changes under the mouse)
void mouse_rehover(void)
{
	int cx,cy,on;

	if (last_wx<0) return;
	on=hud_at(last_wx,last_wy,&cx,&cy);
	mouse2(on,cx,cy,mx,my,0);
}

static void set_fullscreen(int on)
{
	MONITORINFO mi={sizeof(mi)};
	DWORD style=GetWindowLong(desk_hwnd,GWL_STYLE);

	if (on) {
		GetWindowPlacement(desk_hwnd,&win_place);
		GetMonitorInfo(MonitorFromWindow(desk_hwnd,MONITOR_DEFAULTTOPRIMARY),&mi);
		SetWindowLong(desk_hwnd,GWL_STYLE,(style&~WS_OVERLAPPEDWINDOW)|WS_POPUP);
		SetWindowPos(desk_hwnd,HWND_TOP,mi.rcMonitor.left,mi.rcMonitor.top,
			     mi.rcMonitor.right-mi.rcMonitor.left,mi.rcMonitor.bottom-mi.rcMonitor.top,
			     SWP_NOOWNERZORDER|SWP_FRAMECHANGED|SWP_SHOWWINDOW);
	} else {
		SetWindowLong(desk_hwnd,GWL_STYLE,(style&~WS_POPUP)|WS_OVERLAPPEDWINDOW);
		SetWindowPlacement(desk_hwnd,&win_place);
		SetWindowPos(desk_hwnd,NULL,0,0,0,0,SWP_NOMOVE|SWP_NOSIZE|SWP_NOZORDER|SWP_NOOWNERZORDER|SWP_FRAMECHANGED|SWP_SHOWWINDOW);
	}
	fullscreen=on;
	calc_dst_rect();
	InvalidateRect(desk_hwnd,NULL,TRUE);
}

static char ini_file[MAX_PATH];

static void load_display_settings(void)
{
	char *p;

	GetModuleFileName(NULL,ini_file,MAX_PATH);
	p=strrchr(ini_file,'\\');
	if (p) strcpy(p+1,"client.ini");
	else strcpy(ini_file,"client.ini");

	if (fullscreen==-1) fullscreen=0;	// -w on command line
	else if (!fullscreen) fullscreen=GetPrivateProfileInt("display","fullscreen",0,ini_file);
	smooth_scale=GetPrivateProfileInt("display","smooth",1,ini_file);
	world_zoom=GetPrivateProfileInt("display","zoom",115,ini_file);
	{ extern int lowhp_pct; lowhp_pct=GetPrivateProfileInt("display","lowhp",25,ini_file); if (lowhp_pct<0 || lowhp_pct>90) lowhp_pct=25; }
	hud_theme=GetPrivateProfileInt("display","hud_theme",2,ini_file);
}

static void save_display_settings(void)
{
	WINDOWPLACEMENT wp={sizeof(wp)};
	char buf[32];

	// window position: from before fullscreen if we are fullscreen now
	if (fullscreen) wp=win_place;
	else GetWindowPlacement(desk_hwnd,&wp);
	if (win_shown && wp.rcNormalPosition.right>wp.rcNormalPosition.left) {
		sprintf(buf,"%ld",wp.rcNormalPosition.left); WritePrivateProfileString("window_v2","left",buf,ini_file);
		sprintf(buf,"%ld",wp.rcNormalPosition.top); WritePrivateProfileString("window_v2","top",buf,ini_file);
		sprintf(buf,"%ld",wp.rcNormalPosition.right); WritePrivateProfileString("window_v2","right",buf,ini_file);
		sprintf(buf,"%ld",wp.rcNormalPosition.bottom); WritePrivateProfileString("window_v2","bottom",buf,ini_file);
		WritePrivateProfileString("window_v2","maximized",wp.showCmd==SW_SHOWMAXIMIZED ? "1" : "0",ini_file);
	}

	WritePrivateProfileString("display","fullscreen",fullscreen ? "1" : "0",ini_file);
	WritePrivateProfileString("display","smooth",smooth_scale ? "1" : "0",ini_file);
	sprintf(buf,"%d",world_zoom); WritePrivateProfileString("display","zoom",buf,ini_file);
	sprintf(buf,"%d",hud_theme); WritePrivateProfileString("display","hud_theme",buf,ini_file);
}

// called by dd_init(): size and show the game window
int win_show(void)
{
	RECT wa,r;
	int scale,want_fs=fullscreen;

	SystemParametersInfo(SPI_GETWORKAREA,0,&wa,0);

	// as large as fits on the desktop (4:3), a little margin around it
	{
		RECT fr={0,0,400,300};
		int fw,fh,ch,cw;
		AdjustWindowRect(&fr,WS_OVERLAPPEDWINDOW,FALSE);
		fw=(fr.right-fr.left)-400; fh=(fr.bottom-fr.top)-300;
		ch=((wa.bottom-wa.top)-fh)*96/100;
		cw=ch*4/3;
		if (cw>((wa.right-wa.left)-fw)*96/100) { cw=((wa.right-wa.left)-fw)*96/100; ch=cw*3/4; }
		SetRect(&r,0,0,cw,ch);
	}
	(void)scale;
	AdjustWindowRect(&r,WS_OVERLAPPEDWINDOW,FALSE);

	fullscreen=0;
	SetWindowPos(desk_hwnd,NULL,
		     wa.left+((wa.right-wa.left)-(r.right-r.left))/2,
		     wa.top+((wa.bottom-wa.top)-(r.bottom-r.top))/2,
		     r.right-r.left,r.bottom-r.top,SWP_NOZORDER);
	{	// QoL: restore the last window position and size
		RECT sr;
		int max;
		sr.left=GetPrivateProfileInt("window_v2","left",-32000,ini_file);
		sr.top=GetPrivateProfileInt("window_v2","top",-32000,ini_file);
		sr.right=GetPrivateProfileInt("window_v2","right",-32000,ini_file);
		sr.bottom=GetPrivateProfileInt("window_v2","bottom",-32000,ini_file);
		max=GetPrivateProfileInt("window_v2","maximized",0,ini_file);
		if (sr.left!=-32000 && sr.right-sr.left>=200 && sr.bottom-sr.top>=150 && MonitorFromRect(&sr,MONITOR_DEFAULTTONULL)) {
			WINDOWPLACEMENT wp={sizeof(wp)};
			wp.showCmd=max ? SW_SHOWMAXIMIZED : SW_SHOWNORMAL;
			wp.rcNormalPosition=sr;
			SetWindowPlacement(desk_hwnd,&wp);
		}
	}
	ShowWindow(desk_hwnd,SW_SHOW);
	win_shown=1;
	calc_dst_rect();

	if (want_fs) set_fullscreen(1);

	SetForegroundWindow(desk_hwnd);
	SetFocus(desk_hwnd);

	return 1;
}

// set the game's mouse cursor, but only while the mouse is over the game area
void set_game_cursor(HCURSOR c)
{
	POINT pt;
	RECT cr;

	if (!c) c=LoadCursor(NULL,IDC_ARROW);
	if (GetForegroundWindow()!=desk_hwnd) return;
	GetCursorPos(&pt);
	ScreenToClient(desk_hwnd,&pt);
	GetClientRect(desk_hwnd,&cr);
	if (PtInRect(&cr,pt)) SetCursor(c);
}

void cmd_exit(void);

LRESULT CALLBACK MainWndProc(HWND hWnd, UINT message,WPARAM wParam, LPARAM lParam)
{
	PAINTSTRUCT ps;
	int keys;
	extern int ser_ver,xmove,init_done;

	keys=0;
	if (GetAsyncKeyState(VK_SHIFT)&0x8000) keys|=1;
	if (GetAsyncKeyState(VK_CONTROL)&0x8000) keys|=2;

	switch (message) {
		case    WM_SYSKEYDOWN:
			if (wParam==VK_RETURN) {	// Alt+Enter: toggle fullscreen
				if (!(lParam&(1<<30))) { set_fullscreen(!fullscreen); save_display_settings(); }
				break;
			}
			if (wParam==VK_F4 && (GetKeyState(VK_MENU)&0x8000)) { cmd_exit(); break; }
			/* fall through: F10 arrives as a system key */
		case WM_KEYDOWN:
			// Ctrl+1..9, 0, -, = : skill buttons 1-12 (left to right, top to bottom)
			if ((keys&2) && !(keys&1)) {
				int b=-1;
				if (wParam>='1' && wParam<='9') b=(int)wParam-'1';
				else if (wParam=='0') b=9;
				else if (wParam==VK_OEM_MINUS) b=10;
				else if (wParam==VK_OEM_PLUS) b=11;
				if (b>=0) { if (!(lParam&(1<<30))) button_command(16+b); break; }
			}
			switch ((int)wParam) {
				case    27:         cmd(CL_CMD_RESET,0,0); show_shop=0; noshop=QSIZE*12; xmove=0; break;	//ESC
				case    'p':            if (keys) button_command(16);
					else cmd(CL_CMD_MODE,2,0); break;		//F1
				case    'q':            if (keys) button_command(17);
					else cmd(CL_CMD_MODE,1,0); break;		//F2
				case    'r':            if (keys) button_command(18);
					else cmd(CL_CMD_MODE,0,0); break;		//F3
				case    's':            if (keys) button_command(19);
					else pdata.show_proz=1-pdata.show_proz; break;	//F4
				case    't':            if (keys) button_command(20);			//F5
					else do_alpha++; if (do_alpha==3) do_alpha=0; dd_invalidate_alpha(); break;
				case    'u':            if (keys) button_command(21);
					else pdata.hide=1-pdata.hide; break;		//F6
				case    'v':            if (keys) button_command(22);
					else pdata.show_names=1-pdata.show_names; break;//F7
				case    'w':            if (keys) button_command(23);break;			   //F8
				case    'x':            if (keys) button_command(24);
					else dd_savescreen(); break;						   //F9
				case  'y':        if (keys)	button_command(25);
					else {
						gamma+=250;
						if (gamma>6000)	gamma=5000;
						xlog(2,"Set gamma correction to %1.2f",gamma/5000.0);
						dd_invalidate_cache();
					}
					break;		// F10
				case    'z':        if (keys) button_command(26);
					else {
						xlog(2," ");											//F11
						xlog(2,"Client Version %d.%02d.%02d",VERSION>>16,(VERSION>>8)&255,VERSION&255);
						xlog(2,"Server Version %d.%02d.%02d",ser_ver>>16,(ser_ver>>8)&255,ser_ver&255);
						xlog(2,"MAXX=%d, MAXY=%d, MAXXO=%d",MAXX,MAXY,MAXXOVER);
						xlog(2,"R=%04X, G=%04X, B=%04X",RED,GREEN,BLUE);
						xlog(2,"RGBM=%d",RGBM);
						xlog(2,"MAXCACHE=%d",MAXCACHE);
						xlog(2,"Hit=%d, Miss=%d, Invis=%d",dd_cache_hit,dd_cache_miss,invisible);
						xlog(2,"Ratio=%.2f%%",100.0/(dd_cache_hit+dd_cache_miss)*dd_cache_hit);
						xlog(2,"Skip=%d%% Idle=%d%%",pskip,pidle);
						xlog(2,"MaxMem=%dK, UsedMem=%dK",maxmem>>10,usedmem>>10);
						xlog(2,"MemBlocks=%d (T=%d,GC=%d)",blockcnt,blocktot,blockgc);
						xlog(2,"MaxVid=%dK, UsedVid=%dK",(maxvid*32*32*2)>>10,(usedvid*32*32*2)>>10);
						xlog(2,"cachex=%d, cachey=%d, MAXXOVER=%d",cachex,cachey,MAXXOVER);
						xlog(2,"usedvidmemflag=%d",usedvidmem);
						xlog(2,"alphapix=%d, fullpix=%d, ratio=%.2f",alphapix,fullpix,100.0/(alphapix+fullpix+1)*alphapix);

//                                do_ticker=1-do_ticker;
					}
					break;

				case    '{':            if (keys) button_command(27);
					else cmd_exit();
					break;		   //F12


					// text editor
				case  9:          complete_word();
					break;

				case    8:              if (cur_pos && in_len) { //BACKSPACE
						if (tabmode) {
							in_len=cur_pos; tabmode=0; tabstart=0;
						}
						if (cur_pos>in_len)	cur_pos=in_len;
						memmove(input+cur_pos-1,input+cur_pos,120-cur_pos);
						in_len--;
						cur_pos--;
					}
					break;
				case 46:             if (in_len) { // DEL
						if (tabmode) {
							in_len=cur_pos; tabmode=0; tabstart=0;
						} else {
							memmove(input+cur_pos,input+cur_pos+1,120-cur_pos);
							in_len--;
						}
					}
					break;
				case 33:          if (logstart<22*8) {
						logstart+=11; logtimer=TICKS*30;
					}
					break;
				case 34:          if (logstart>0) {
						logstart-=11; logtimer=TICKS*30;
					}
					break;
				case 36:          cur_pos=0; tabmode=0; tabstart=0; break; // HOME
				case 35:          cur_pos=in_len; tabmode=0; tabstart=0; break;	// END
				case 37:          if (cur_pos) cur_pos--;
					tabmode=0; tabstart=0;
					break;
				case 39:          if (cur_pos<115) cur_pos++;
					tabmode=0; tabstart=0;
					break;
				case 38:          if (hist_nr<19) {
						memcpy(history[hist_nr],input,128);
						hist_len[hist_nr]=in_len;
						hist_nr++;

						memcpy(input,history[hist_nr],128);
						in_len=cur_pos=hist_len[hist_nr];

						tabmode=0; tabstart=0;
					}
					break;
				case 40:          if (hist_nr>0) {
						memcpy(history[hist_nr],input,128);
						hist_len[hist_nr]=in_len;

						hist_nr--;

						memcpy(input,history[hist_nr],128);
						in_len=cur_pos=hist_len[hist_nr];

						tabmode=0; tabstart=0;
					}
					break;
/*           default:          xlog(3,"key=%d",(int)wParam);
							 break;*/

			}
			break;

		case WM_CHAR:
			switch ((int)wParam) {
				case    13:            if (in_len==0) break;

					if (tabmode) {
						tabmode=0; tabstart=0;
						in_len--;
					}

					memmove(history[2],history[1],18*128);
					memmove(&hist_len[2],&hist_len[1],sizeof(int)*18);

					memcpy(history[1],input,128);
					hist_len[1]=in_len;

					input[in_len]=0;
					in_len=0;
					cur_pos=0;
					view_pos=0;
					hist_nr=0;

					add_words();

					// #tile / /tile with no coordinates: use the map tile under the mouse
					if ((!_stricmp(input,"/tile") || !_stricmp(input,"#tile")) && tile_x>=0 && tile_y>=0 && map) {
						int tm=tile_x+tile_y*TILEX;
						sprintf(input+5," %d %d",map[tm].x,map[tm].y);
					}

					say(input);

					break;

				default:                if ((int)wParam>31 && (int)wParam<128 && in_len<115) {
						if (tabmode) {
							if (!isalnum((char)wParam))	in_len--;
							cur_pos=in_len;
							tabmode=0;
							tabstart=0;
						}
						if (cur_pos>in_len)	cur_pos=in_len;
						memmove(input+cur_pos+1,input+cur_pos,120-cur_pos);
						input[cur_pos]=(char)wParam;
						in_len++;
						cur_pos++;
					}
					break;
			}
			break;

		case WM_PAINT:
			BeginPaint(hWnd,&ps);
			EndPaint(hWnd,&ps);
			break;

		case WM_ERASEBKGND:
			return 1;

		// keep Alt / F10 from putting the window into menu mode, and
		// Alt+Enter from beeping
		case WM_SYSKEYUP:
			if (wParam==VK_MENU || wParam==VK_F10) break;
			return DefWindowProc(hWnd,message,wParam,lParam);
		case WM_SYSCHAR:
			if (wParam==VK_RETURN) break;
			return DefWindowProc(hWnd,message,wParam,lParam);

		case WM_SIZE:
			calc_dst_rect();
			InvalidateRect(hWnd,NULL,FALSE);
			break;

		case WM_GETMINMAXINFO:
			{
				RECT r={0,0,LEGACY_W/2,LEGACY_H/2};
				AdjustWindowRect(&r,WS_OVERLAPPEDWINDOW,FALSE);
				((MINMAXINFO*)lParam)->ptMinTrackSize.x=r.right-r.left;
				((MINMAXINFO*)lParam)->ptMinTrackSize.y=r.bottom-r.top;
			}
			break;

		case WM_SETCURSOR:
			if (LOWORD(lParam)==HTCLIENT) {
				extern int cursor_type;
				SetCursor(cursor[cursor_type] ? cursor[cursor_type] : LoadCursor(NULL,IDC_ARROW));
				return TRUE;
			}
			return DefWindowProc(hWnd,message,wParam,lParam);

		case WM_CLOSE:		// window close button: same as the in-game exit (F12)
			if (init_done) cmd_exit();
			else quit=1;
			break;

		case WM_DESTROY:
			save_display_settings();
			quit=1;
			PostQuitMessage(0);
			break;

		case WM_MOUSEMOVE:
			on_mouse(lParam,MS_MOVE);
			break;

		case WM_LBUTTONDOWN:
			SetCapture(hWnd);
			on_mouse(lParam,MS_LB_DOWN);
			break;

		case WM_LBUTTONUP:
			ReleaseCapture();
			on_mouse(lParam,MS_LB_UP);
			break;

		case WM_MOUSEWHEEL:	// QoL: mouse wheel scrolls the chat while hovering over it
			{
				static int wheel_acc=0;
				POINT pt;
				int gx,gy,lines;

				// WM_MOUSEWHEEL has screen coordinates
				pt.x=GET_X_LPARAM(lParam);
				pt.y=GET_Y_LPARAM(lParam);
				ScreenToClient(hWnd,&pt);

				wheel_acc+=GET_WHEEL_DELTA_WPARAM(wParam);
				lines=wheel_acc/WHEEL_DELTA;	// notches, + = wheel up
				wheel_acc%=WHEEL_DELTA;		// keep remainder (smooth-scrolling wheels/touchpads)
				if (!lines) break;

				if (hud_at(pt.x,pt.y,&gx,&gy)) hud_wheel(gx,gy,lines);
			}
			break;

		case WM_RBUTTONDOWN:
			on_mouse(lParam,MS_RB_DOWN);
			break;

		case WM_RBUTTONUP:
			on_mouse(lParam,MS_RB_UP);
			break;

		default:
			return(DefWindowProc(hWnd, message, wParam, lParam));
	}
	return 0;
}


HWND InitWindow(HINSTANCE hInstance,int nCmdShow)
{
	WNDCLASS wc;
	HWND hWnd;
	char buf[256];
	int n;

	(void)nCmdShow;
	hinst=hInstance;

	for (n=1; n<10; n++)
		cursor[n]=LoadCursor(hInstance,MAKEINTRESOURCE(n));

	wc.style=CS_HREDRAW|CS_VREDRAW;
	wc.lpfnWndProc=MainWndProc;
	wc.cbClsExtra=0;
	wc.cbWndExtra=0;
	wc.hInstance=hInstance;
	wc.hIcon=LoadIcon(hInstance,MAKEINTRESOURCE(1));
	wc.hCursor=NULL;
	wc.hbrBackground=GetStockObject(BLACK_BRUSH);
	wc.lpszMenuName=NULL;
	wc.lpszClassName="DDCWin";

	RegisterClass(&wc);

	sprintf(buf,MNAME" v%d.%02d.%02d",
			VERSION>>16,(VERSION>>8)&255,VERSION&255);

	// created hidden; dd_init() -> win_show() sizes and shows it after login
	desk_hwnd=hWnd=CreateWindowEx(0,"DDCWin",buf,WS_OVERLAPPEDWINDOW,
				     CW_USEDEFAULT,CW_USEDEFAULT,LEGACY_W,LEGACY_H,
				     NULL,NULL,hInstance,NULL);

	return hWnd;
}

int parse_cmd(char *s)
{
	int n;

	while (isspace(*s))	s++;
	while (*s) {
		if (*s=='-') {
			s++;
			if (tolower(*s)=='t') {
				s++;
				tricky_flag=1;
			} else if (tolower(*s)=='d') {
				s++;
				while (isspace(*s)) s++;
				n=0; while (n<150 && *s && !isspace(*s)) path[n++]=*s++;
				if (n && path[n-1]!='\\') path[n++]='\\';
				path[n]=0;
			} else if (tolower(*s)=='h') {	// PORT: -h <server address>
				s++;
				while (isspace(*s)) s++;
				n=0; while (n<80 && *s && !isspace(*s)) host_addr[n++]=*s++;
				host_addr[n]=0;
			} else if (tolower(*s)=='f') {	// PORT: -f start in fullscreen
				s++;
				fullscreen=1;
			} else if (tolower(*s)=='w') {	// PORT: -w start windowed
				s++;
				fullscreen=-1;
			} else if (tolower(*s)=='p') {
				s++;
				while (isspace(*s)) s++;
				host_port=atoi(s);
				while (*s && !isspace(*s)) s++;
			} else return -1;
		} else return -2;
		while (isspace(*s))	s++;
	}
	return 1;
}

void log_system_data(void)
{
	char buf[256];
	unsigned int langid,lcid;
	DWORD size=80;
	char systemdir[256],windir[256],cdir[256],user[256],computer[256];

	langid=GetSystemDefaultLangID();
	lcid=GetSystemDefaultLCID();

	GetSystemDirectory(systemdir,80);
        GetWindowsDirectory(windir,80);
	GetCurrentDirectory(80,cdir);
	GetUserName((void*)user,&size); size=80;
	GetComputerName((void*)computer,&size);

	sprintf(buf,"|langid=%u, lcid=%u",langid,lcid); say(buf);
	sprintf(buf,"|systemdir=\"%s\"",systemdir); say(buf);
	sprintf(buf,"|windowsdir=\"%s\"",windir); say(buf);
	sprintf(buf,"|currentdir=\"%s\"",cdir); say(buf);
	sprintf(buf,"|username=\"%s\"",user); say(buf);
	sprintf(buf,"|computername=\"%s\"",computer); say(buf);
}

void crash_init(void);

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance,
				   LPSTR lpCmdLine, int nCmdShow)
{
	HWND hwnd;
	char buf[2048];
	int tmp;
	HANDLE mutex;
	HMODULE user32;

	(void)hPrevInstance;

	crash_init();

	// PORT: render at full resolution on high-DPI displays instead of
	// letting Windows blur-scale the whole window
	user32=GetModuleHandle("user32.dll");
	if (user32) {
		BOOL (WINAPI *dpiaware)(void)=(void*)GetProcAddress(user32,"SetProcessDPIAware");
		if (dpiaware) dpiaware();
	}

	// PORT: 1ms timer resolution so Sleep(1) in the frame limiter is accurate
	timeBeginPeriod(1);

	srand((unsigned)GetTickCount());

	if (parse_cmd(lpCmdLine)<0) {
		MessageBox(0,"Usage: merc.exe [-h server] [-p port] [-d datadir] [-f|-w] [-t]","Command line",MB_OK|MB_ICONINFORMATION);
	}
	load_display_settings();

	mutex=CreateMutex(NULL,0,"MOAB");
	if (mutex==NULL || (GetLastError()==ERROR_ALREADY_EXISTS && strcmp(host_addr,"192.168.42.1"))) {
		MessageBox(0,"Another instance of "MNAME" is already running.","Error",MB_OK|MB_ICONSTOP);
		return 0;
	}

	dlg_col=GetSysColor(COLOR_BTNFACE);
	dlg_back=CreateSolidBrush(dlg_col);
	dlg_fcol=GetSysColor(COLOR_WINDOWTEXT);

	hwnd=InitWindow(hInstance,nCmdShow);

	load_options();
	init_engine();
	options();
	if (quit) exit(0);

	init_sound(hwnd);

	if ((tmp=dd_init(hwnd,SCREEN_W,SCREEN_H))!=0) {

		sprintf(buf,"|DDERROR=%d",-tmp);
		say(buf);
		Sleep(1000);

		sprintf(buf,
				"Graphics init failed with code %d.\n"
				"Error=%s\n"
				"Client Version %d.%02d.%02d\n",
				-tmp,DDERR,VERSION>>16,(VERSION>>8)&255,VERSION&255);
		MessageBox(hwnd,buf,"Graphics init failed.",MB_ICONSTOP|MB_OK);
		exit(1);
	}
        sprintf(buf,"|R=%04X, G=%04X, B=%04X, RGBM=%d",RED,GREEN,BLUE,RGBM);
	say(buf);

        init_xalloc();
	conv_init();
	init_pnglib();
	dd_init_sprites();	

	log_system_data();

	engine();

	dd_deinit();

	save_options();
	save_display_settings();

	timeEndPeriod(1);

	return 0;
}
