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
static RECT dst_rect={0,0,MODEX,MODEY};	// where the game image is drawn in the client area
static WINDOWPLACEMENT win_place={sizeof(WINDOWPLACEMENT)};
static int win_shown=0;
static int smooth_scale=1;

static void calc_dst_rect(void)
{
	RECT cr;
	int cw,ch,dw,dh,scale;

	GetClientRect(desk_hwnd,&cr);
	cw=cr.right-cr.left;
	ch=cr.bottom-cr.top;
	if (cw<1 || ch<1) { SetRect(&dst_rect,0,0,MODEX,MODEY); return; }

	// keep the 4:3 aspect ratio, prefer pixel-exact integer scaling
	scale=min(cw/MODEX,ch/MODEY);
	if (scale>=1 && (cw-scale*MODEX<MODEX/4 || ch-scale*MODEY<MODEY/4)) {
		dw=scale*MODEX;
		dh=scale*MODEY;
	} else if (cw*MODEY>ch*MODEX) {
		dh=ch;
		dw=ch*MODEX/MODEY;
	} else {
		dw=cw;
		dh=cw*MODEY/MODEX;
	}
	dst_rect.left=(cw-dw)/2;
	dst_rect.top=(ch-dh)/2;
	dst_rect.right=dst_rect.left+dw;
	dst_rect.bottom=dst_rect.top+dh;
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
	HBRUSH black;

	if (!desk_hwnd || !win_shown) return;

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

	dc=GetDC(desk_hwnd);
	if (!dc) return;

	dw=dst_rect.right-dst_rect.left;
	dh=dst_rect.bottom-dst_rect.top;

	// black borders around the image
	GetClientRect(desk_hwnd,&cr);
	black=GetStockObject(BLACK_BRUSH);
	if (dst_rect.left>0) { RECT r={0,0,dst_rect.left,cr.bottom}; FillRect(dc,&r,black); }
	if (dst_rect.right<cr.right) { RECT r={dst_rect.right,0,cr.right,cr.bottom}; FillRect(dc,&r,black); }
	if (dst_rect.top>0) { RECT r={dst_rect.left,0,dst_rect.right,dst_rect.top}; FillRect(dc,&r,black); }
	if (dst_rect.bottom<cr.bottom) { RECT r={dst_rect.left,dst_rect.bottom,dst_rect.right,cr.bottom}; FillRect(dc,&r,black); }

	if (smooth_scale && (dw%w || dh%h)) {
		SetStretchBltMode(dc,HALFTONE);
		SetBrushOrgEx(dc,0,0,NULL);
	} else SetStretchBltMode(dc,COLORONCOLOR);

	StretchDIBits(dc,dst_rect.left,dst_rect.top,dw,dh,0,0,w,h,bits,(BITMAPINFO*)&bmi,DIB_RGB_COLORS,SRCCOPY);

	ReleaseDC(desk_hwnd,dc);
}

// translate window client coordinates into 800x600 game coordinates
static void map_mouse(LPARAM lParam,int *x,int *y)
{
	int cx=GET_X_LPARAM(lParam),cy=GET_Y_LPARAM(lParam);
	int dw=dst_rect.right-dst_rect.left,dh=dst_rect.bottom-dst_rect.top;

	if (dw<1 || dh<1) { *x=cx; *y=cy; return; }

	*x=(cx-dst_rect.left)*MODEX/dw;
	*y=(cy-dst_rect.top)*MODEY/dh;

	if (*x<0) *x=0;
	if (*x>MODEX-1) *x=MODEX-1;
	if (*y<0) *y=0;
	if (*y>MODEY-1) *y=MODEY-1;
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
}

static void save_display_settings(void)
{
	WritePrivateProfileString("display","fullscreen",fullscreen ? "1" : "0",ini_file);
	WritePrivateProfileString("display","smooth",smooth_scale ? "1" : "0",ini_file);
}

// called by dd_init(): size and show the game window
int win_show(void)
{
	RECT wa,r;
	int scale,want_fs=fullscreen;

	SystemParametersInfo(SPI_GETWORKAREA,0,&wa,0);

	// largest integer scale that fits on the desktop
	for (scale=4; scale>1; scale--) {
		SetRect(&r,0,0,MODEX*scale,MODEY*scale);
		AdjustWindowRect(&r,WS_OVERLAPPEDWINDOW,FALSE);
		if (r.right-r.left<=wa.right-wa.left && r.bottom-r.top<=wa.bottom-wa.top) break;
	}
	SetRect(&r,0,0,MODEX*scale,MODEY*scale);
	AdjustWindowRect(&r,WS_OVERLAPPEDWINDOW,FALSE);

	fullscreen=0;
	SetWindowPos(desk_hwnd,NULL,
		     wa.left+((wa.right-wa.left)-(r.right-r.left))/2,
		     wa.top+((wa.bottom-wa.top)-(r.bottom-r.top))/2,
		     r.right-r.left,r.bottom-r.top,SWP_NOZORDER);
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
				RECT r={0,0,MODEX/2,MODEY/2};
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
			quit=1;
			PostQuitMessage(0);
			break;

		case WM_MOUSEMOVE:
			map_mouse(lParam,&mx,&my);
			mouse(mx,my,MS_MOVE);
			break;

		case WM_LBUTTONDOWN:
			SetCapture(hWnd);
			map_mouse(lParam,&mx,&my);
			mouse(mx,my,MS_LB_DOWN);
			break;

		case WM_LBUTTONUP:
			ReleaseCapture();
			map_mouse(lParam,&mx,&my);
			mouse(mx,my,MS_LB_UP);
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
				map_mouse(MAKELPARAM(pt.x,pt.y),&gx,&gy);

				wheel_acc+=GET_WHEEL_DELTA_WPARAM(wParam);
				lines=wheel_acc/WHEEL_DELTA;	// notches, + = wheel up
				wheel_acc%=WHEEL_DELTA;		// keep remainder (smooth-scrolling wheels/touchpads)
				if (!lines) break;

				if (gx>=CHAT_X1 && gy<=CHAT_Y2) {		// chat
					logstart+=lines*CHAT_WHEEL_LINES;
					if (logstart>CHAT_MAXSCROLL) logstart=CHAT_MAXSCROLL;
					if (logstart<0) logstart=0;
					logtimer=TICKS*30;	// return to the newest lines after 30s, like PgUp/PgDn
				} else if (gx<SKILL_X2 && gy>=SKILL_Y1 && gy<=SKILL_Y2) {	// skill list
					int pos=(int)skill_pos-lines*2;		// 2 entries per notch, like the arrows
					if (pos<0) pos=0;
					if (pos>40) pos=40;
					skill_pos=pos;
				} else if (gx>=INV_X1 && gx<INV_X2 && gy<=INV_Y2) {	// backpack
					int pos=(int)inv_pos-lines*2;		// one row per notch, like the arrows
					if (pos<0) pos=0;
					if (pos>30) pos=30;
					inv_pos=pos;
				}
			}
			break;

		case WM_RBUTTONDOWN:
			map_mouse(lParam,&mx,&my);
			mouse(mx,my,MS_RB_DOWN);
			break;

		case WM_RBUTTONUP:
			map_mouse(lParam,&mx,&my);
			mouse(mx,my,MS_RB_UP);
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
				     CW_USEDEFAULT,CW_USEDEFAULT,MODEX,MODEY,
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

	if ((tmp=dd_init(hwnd,MODEX,MODEY))!=0) {

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
