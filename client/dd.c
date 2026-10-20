#include <stdio.h>
#include <malloc.h>
#include <fcntl.h>
#include <io.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>
#include <windowsx.h>
#include <process.h>
#include <time.h>
#include <math.h>
#include "dd.h"
#include "common.h"
#include "inter.h"
#include "pngdec.h"
#include "hud.h"

int tricky_flag=0;

int maxmem=16*1024*1024,maxvid=2*1024*1024;
int usedmem=0,usedvid=0;
char *DDERR;
extern int do_alpha;
extern int do_shadow;

int blockcnt=0,blocktot=0,blockgc=0;
int alphapix=0,fullpix=0;

unsigned short *dd_load_png(FILE *fp,int *xs,int *ys,unsigned char **alpha_ptr,int *alphacnt_ptr);
void display_alpha(unsigned char *alpha,int alphacnt,int xf,int yf,int effect);
FILE *load_pnglib(int nr);

// PORT: the original used HeapCreate() with a fixed maximum size of 20MB,
// while the sprite cache limit was derived from the total physical RAM.
// On any machine with more than a few hundred MB of RAM this ran the heap
// dry (HEAP_GENERATE_EXCEPTIONS -> instant crash) or, with >2GB RAM, made
// maxmem negative so free_2nd_cache() spun forever (black screen).
void init_xalloc(void)
{
}

void *xmalloc(int size)
{
	char *ptr;

	ptr=malloc(size);
	if (!ptr) return NULL;

	blockcnt++; blocktot++;
	usedmem+=(int)_msize(ptr)+16;

	return ptr;
}

void xfree(void *ptr)
{
	if (!ptr) return;

	blockcnt--;
	usedmem-=(int)_msize(ptr)+16;

	free(ptr);
}

void *xcalloc(int size1,int size2)
{
	unsigned char *ptr;

	ptr=calloc(size1,size2);
	if (!ptr) return NULL;

	blockcnt++; blocktot++;
	usedmem+=(int)_msize(ptr)+16;

	return ptr;
}

extern HWND desk_hwnd;

#define TILE 32
unsigned short background=0;
int invisible=0;

void one(void);
void two(void);
void three(void);
void four(void);
void five(void);

int MAXX,MAXY;
int MAXX1,MAXY1;
int RED,GREEN,BLUE;
int RGBM=-1;

// PORT: DirectDraw surfaces replaced by plain memory buffers (RGB565).
// sur2 is the back buffer everything is drawn into, sur1 holds the last
// presented frame (used for screenshots), suro is the sprite tile cache.
typedef struct dd_surface {
	unsigned short *bits;
	int w,h,pitch;	// pitch in pixels
} DDSURF;

typedef DDSURF *LPDIRECTDRAWSURFACE;

static DDSURF s1,s2,so,shud;
LPDIRECTDRAWSURFACE sur1=&s1,sur2=&s2,suro=&so;

// BIGVIEW: s2 is the big screen (SCREEN_W x SCREEN_H) the world is drawn on,
// shud is an 800x600 surface the original HUD code draws on. dd_target()
// switches sur2/MAXX/MAXY/MODEX/MODEY between them, so all the old drawing
// functions work unchanged on either.
int cur_w=SCREEN_W,cur_h=SCREEN_H;
int map_clip_top=0;		// world drawing clip (was 200: under the top HUD)
static int hud_active=0;

void win_present(unsigned short *bits,int w,int h);
int win_show(void);

void *load_file(char *file);
void dd_invalidate_cache(void);
void *dd_get_ptr(LPDIRECTDRAWSURFACE sur);
int dd_release_ptr(LPDIRECTDRAWSURFACE sur);
void dd_flip(void);

int MAXCACHE;
int MAXXOVER;

int cachex,cachey;

DWORD total,left;

#define CACHE_W		1024	// sprite cache: 32 x 128 tiles of 32x32 pixels
#define CACHE_H		4096

static int alloc_surface(DDSURF *sur,int w,int h)
{
	sur->bits=calloc((size_t)w*h,sizeof(unsigned short));
	if (!sur->bits) return 0;
	sur->w=w;
	sur->h=h;
	sur->pitch=w;
	return 1;
}

void dd_clear(void)
{
	memset(sur1->bits,0,(size_t)sur1->pitch*sur1->h*2);
	memset(sur2->bits,0,(size_t)sur2->pitch*sur2->h*2);
	memset(suro->bits,0,(size_t)suro->pitch*suro->h*2);
}

int usedvidmem=1;

int dd_init(HWND hwnd,int x,int y)
{
	(void)hwnd;

	DDERR="OK";

	x=SCREEN_W; y=SCREEN_H;

	MAXX=MAXX1=x;
	MAXY=MAXY1=y;
	cur_w=x; cur_h=y;

	// we always work in RGB565 internally, the presenter converts as needed
	RED=0xF800;
	GREEN=0x07E0;
	BLUE=0x001F;
	RGBM=0;

	if (!alloc_surface(sur1,x,y) || !alloc_surface(sur2,x,y) || !alloc_surface(&shud,LEGACY_W,LEGACY_H+8)) {
		DDERR="OUTOFMEMORY (frame buffer)";
		return -1;
	}
	if (!alloc_surface(suro,CACHE_W,CACHE_H)) {
		DDERR="OUTOFMEMORY (sprite cache)";
		return -9;
	}

	MAXXOVER=suro->pitch;
	cachex=MAXXOVER/TILE;
	cachey=suro->h/TILE;

	MAXCACHE=min(65535,cachex*cachey);

	dd_clear();

	if (!win_show()) {
		DDERR="could not show game window";
		return -2;
	}

	return 0;
}

void dd_deinit(void)
{
	// nothing to restore any more - no display mode change happens
}



static int locks=0;

void *dd_get_ptr(LPDIRECTDRAWSURFACE sur)
{
	if (!sur || !sur->bits) return NULL;
	locks++;
	return sur->bits;
}

int dd_release_ptr(LPDIRECTDRAWSURFACE sur)
{
	(void)sur;
	locks--;
	return 0;
}

void *_dd_get_ptr(LPDIRECTDRAWSURFACE sur)
{
	if (!sur) return NULL;
	return sur->bits;
}

int _dd_release_ptr(LPDIRECTDRAWSURFACE sur)
{
	(void)sur;
	return 0;
}

void islocked(void)
{
	unsigned short *ptr;
	int n;

	if (!locks)	return;

	ptr=_dd_get_ptr(sur1);
	if (!ptr) return;

	for (n=0; n<10; n++) {
		ptr[n]=0xF800;
		ptr[n+MODEX]=0xF800;
		ptr[n+MODEX*2]=0xF800;
	}
	_dd_release_ptr(sur1);
}

void dd_showbar(int xf,int yf,int xs,int ys,unsigned short col)
{
	unsigned short *ptr;
	int x,y,off;
	int xt,yt,r,g,b;

	ptr=dd_get_ptr(sur2);
	if (ptr==NULL) return;

	xt=xf+xs;
	yt=yf+ys;

	for (y=yf; y<yt; y++) {
		for (x=xf,off=y*MAXX+xf; x<xt; x++,off++) {
			switch (RGBM) {
				case 0:	  // 565
					r=((ptr[off]&0xF800)>>11)+((col&0xF800)>>11);
					g=((ptr[off]&0x07E0)>>5)+((col&0x07E0)>>5);
					b=((ptr[off]&0x001F))+((col&0x001F));

					r/=3;
					g/=3;
					b/=3;

					ptr[off]=(unsigned short)((r<<11)+(g<<5)+b);
					break;
				case 1:	 // 555
					r=((ptr[off]&0x7C00)>>10)+((col&0x7C00)>>10);
					g=((ptr[off]&0x03E0)>>5)+((col&0x03E0)>>5);
					b=((ptr[off]&0x001F))+((col&0x001F));

					r/=3;
					g/=3;
					b/=3;

					ptr[off]=(unsigned short)((r<<10)+(g<<5)+b);
					break;
				case 2:	 // 555
					b=((ptr[off]&0x7C00)>>10)+((col&0x7C00)>>10);
					g=((ptr[off]&0x03E0)>>5)+((col&0x03E0)>>5);
					r=((ptr[off]&0x001F))+((col&0x001F));

					r/=3;
					g/=3;
					b/=3;

					ptr[off]=(unsigned short)((b<<10)+(g<<5)+r);
					break;
			}
		}
	}

	dd_release_ptr(sur2);
}

// QoL: copy a block of rows (x1..x2-1, h lines) of the back buffer from ysrc
// to ydst. Used to grow HUD panels by repeating one of their rows.
void dd_copy_rows(int x1,int x2,int ysrc,int ydst,int h)
{
	unsigned short tmp[4096];
	int y,w;

	if (x1<0) x1=0;
	if (x2>MAXX) x2=MAXX;
	if (x2-x1>4096) x2=x1+4096;
	w=x2-x1;
	if (w<=0) return;

	for (y=0; y<h; y++) {
		if (ysrc+y<0 || ysrc+y>=MAXY || ydst+y<0 || ydst+y>=MAXY) continue;
		memcpy(tmp,sur2->bits+(ysrc+y)*sur2->pitch+x1,w*2);
		memcpy(sur2->bits+(ydst+y)*sur2->pitch+x1,tmp,w*2);
	}
}

void dd_showbox(int xf,int yf,int xs,int ys,unsigned short col)
{
	unsigned short *ptr;
	int x,y,off;
	int xt,yt;

	ptr=dd_get_ptr(sur2);
	if (ptr==NULL) return;

	xt=xf+xs;
	yt=yf+ys;

	for (y=yf; y<=yt; y++) {
		for (x=xf,off=y*MAXX+xf; x<=xt; x++,off++) {
			if (x!=xf && x!=xt && y!=yf && y!=yt) continue;
			ptr[off]=col;
		}
	}

	dd_release_ptr(sur2);
}

int dd_set_background(int color)
{
	background=(unsigned short)color;
	return 0;
}

// copy tile nr from the sprite cache to x,y at surface sur (with color key)
int dd_copytile(int nr,int x,int y,LPDIRECTDRAWSURFACE sur,int mapcheck)
{
	int xs=0,ys=0,xe=0,ye=0,w,h,sx,sy,i;
	unsigned short *from,*to,key=background;

	if (!mapcheck) {
		if (x<-31 || y<-31 || x>=MODEX || y>=MODEY)	return 0;

		if (x<0) { xs=-x; x=0; }
		if (y<0) { ys=-y; y=0; }

		if (x+32>=MODEX) xe=x-MODEX+32;
		if (y+32>=MODEY) ye=y-MODEY+32;
	} else {
		if (x<-31 || y<map_clip_top-30 || x>=MODEX || y>=MODEY)	return 0;

		if (x<0) { xs=-x; x=0; }
		if (y<map_clip_top) { ys=-y+map_clip_top; y=map_clip_top; }

		if (x+32>=MODEX) xe=x-MODEX+32;
		if (y+32>=MODEY) ye=y-MODEY+32;
	}

	w=TILE-xs-xe;
	h=TILE-ys-ye;
	if (w<=0 || h<=0) return 0;

	sx=(nr%cachex)*TILE+xs;
	sy=(nr/cachex)*TILE+ys;

	from=suro->bits+sx+sy*suro->pitch;
	to=sur->bits+x+y*sur->pitch;

	while (h--) {
		for (i=0; i<w; i++)
			if (from[i]!=key) to[i]=from[i];
		from+=suro->pitch;
		to+=sur->pitch;
	}

	return 0;
}

void dd_alphaeffect_magic_1(int nr,int str,int xpos,int ypos,int xoff,int yoff)
{
	int rx,ry;
	unsigned short *dst,d;
	int x,y,dstx,dsty,e;
	int r,g,b,r1,g1,b1,e2;

	rx=(xpos/2)+(ypos/2)-(2*16)+32+XPOS-((TILEX-34)/2*32);
	if (xpos<0 && (xpos&1))	rx--;
	if (ypos<0 && (ypos&1))	rx--;
	ry=(xpos/4)-(ypos/4)+YPOS-2*32;
	if (xpos<0 && (xpos&3))	ry--;
	if (ypos<0 && (ypos&3))	ry++;

	rx+=xoff;
	ry+=yoff;

	dst=dd_get_ptr(sur2);

	dstx=rx;
	dsty=ry;

	for (y=0; y<64; y++) {
		if (dsty+y<map_clip_top || dsty+y>=MODEY) continue;
		for (x=0; x<64; x++) {
			if (dstx+x<0 || dstx+x>=MODEX) continue;

			d=dst[(dstx+x)+(dsty+y)*MODEX];

			r1=(d&0x7C00)>>10;
			g1=(d&0x03E0)>>5;
			b1=(d&0x001F);

			e=32;
			if (x<32) e-=32-x;
			if (x>31) e-=x-31;
			if (y<16) e-=16-y;
			if (y>55) e-=(y-55)*2;
			if (e<0) e=0;
			e/=max(1,str);

			e2=0;
			if (nr&1) e2+=e;
			if (nr&2) e2+=e;
			if (nr&4) e2+=e;

			r=r1-e2/2; if (r<0)	r=0;
			g=g1-e2/2; if (g<0)	g=0;
			b=b1-e2/2; if (b<0)	b=0;

			if (nr&1) {
				r=r+e;
				if (r>31) r=31;
			}
			if (nr&2) {
				g=g+e;
				if (g>31) g=31;
			}
			if (nr&4) {
				b=b+e;
				if (b>31) b=31;
			}
			dst[(dstx+x)+(dsty+y)*MODEX]=(unsigned short)((r<<10)+(g<<5)+b);
		}
	}

	dd_release_ptr(sur2);

}

void dd_alphaeffect_magic_0(int nr,int str,int xpos,int ypos,int xoff,int yoff)
{
	int rx,ry;
	unsigned short *dst,d;
	int x,y,dstx,dsty,e;
	int r,g,b,r1,g1,b1,e2;

	rx=(xpos/2)+(ypos/2)-(2*16)+32+XPOS-((TILEX-34)/2*32);
	if (xpos<0 && (xpos&1))	rx--;
	if (ypos<0 && (ypos&1))	rx--;
	ry=(xpos/4)-(ypos/4)+YPOS-2*32;
	if (xpos<0 && (xpos&3))	ry--;
	if (ypos<0 && (ypos&3))	ry++;

	rx+=xoff;
	ry+=yoff;

	dst=dd_get_ptr(sur2);

	dstx=rx;
	dsty=ry;

	for (y=0; y<64; y++) {
		if (dsty+y<map_clip_top || dsty+y>=MODEY) continue;
		for (x=0; x<64; x++) {
			if (dstx+x<0 || dstx+x>=MODEX) continue;

			d=dst[(dstx+x)+(dsty+y)*MAXX];

			r1=(d&0xF800)>>11;
			g1=(d&0x07E0)>>5;
			b1=(d&0x001F);

			e=32;
			if (x<32) e-=32-x;
			if (x>31) e-=x-31;
			if (y<16) e-=16-y;
			if (y>55) e-=(y-55)*2;
			if (e<0) e=0;
			e/=max(1,str);

			e2=0;
			if (nr&1) e2+=e;
			if (nr&2) e2+=e;
			if (nr&4) e2+=e;

			r=r1-e2/2; if (r<0)	r=0;
			g=g1-e2; if (g<0) g=0;
			b=b1-e2/2; if (b<0)	b=0;

			if (nr&1) {
				r=r+e;
				if (r>31) r=31;
			}
			if (nr&2) {
				g=g+e*2;
				if (g>63) g=63;
			}
			if (nr&4) {
				b=b+e;
				if (b>31) b=31;
			}
			dst[(dstx+x)+(dsty+y)*MAXX]=(unsigned short)((r<<11)+(g<<5)+b);
		}
	}

	dd_release_ptr(sur2);
}

void dd_alphaeffect_magic(int nr,int str,int xpos,int ypos,int xoff,int yoff)
{
	if (RGBM==1) dd_alphaeffect_magic_1(nr,str,xpos,ypos,xoff,yoff);
	else dd_alphaeffect_magic_0(nr,str,xpos,ypos,xoff,yoff);	
}

void dd_flip(void)
{
	// keep a copy of what is on screen (for screenshots), then present
	memcpy(sur1->bits,sur2->bits,(size_t)sur2->pitch*sur2->h*2);
	win_present(sur2->bits,sur2->pitch,sur2->h);
}

/* -------------
   Helper routines for dd_load_bitmap
   ------------- */

static void*__mem=NULL;
static int __msize=0;

void *load_file(char *file)
{
	int handle;
	int size;
	unsigned char *ptr;

	if (locks) xlog(0,"trying to read while locked");

	handle=open(file,O_RDONLY|O_BINARY);
	if (handle==-1) {
		return NULL;
	} // xlog(0,"File not found: %s",strerror(errno));
	size=lseek(handle,0L,SEEK_END);
	lseek(handle,0L,SEEK_SET);
	if (size>__msize) {
		if (__mem) xfree(__mem);
		__msize=max(2*1024*2024,size);
		__mem=xmalloc(__msize);
	}
	ptr=__mem;
	if (!ptr) {
		xlog(0,"memory low"); return NULL;
	}
	read(handle,ptr,size);
	close(handle);

	return ptr;
}

static void unload_file(void *ptr)
{
	//xfree(ptr);
	;
}

/* Load a bitmap and return it's contents */

// PORT: decodes the BMP ourselves instead of letting GDI convert it to the
// (16 bit) screen format through a DirectDraw surface DC.
void *dd_load_bitmap(char *name,int *xs,int *ys,LPDIRECTDRAWSURFACE sur)
{
	unsigned char *ptr,*bits,*row;
	BITMAPFILEHEADER *file_hdr;
	BITMAPINFOHEADER *bih;
	RGBQUAD *pal;
	unsigned short *target;
	int w,h,x,y,bpp,stride,topdown,r,g,b,idx;
	unsigned int v,rm=0,gm=0,bm=0;

	(void)sur;

	ptr=load_file(name);
	if (ptr==NULL) return NULL;

	file_hdr=(void*)ptr;
	if (file_hdr->bfType!=0x4D42) return NULL;	// "BM"

	bih=(void*)(ptr+sizeof(BITMAPFILEHEADER));
	bits=ptr+file_hdr->bfOffBits;
	pal=(RGBQUAD*)((unsigned char*)bih+bih->biSize);

	w=bih->biWidth;
	h=bih->biHeight;
	topdown=h<0;
	if (topdown) h=-h;
	bpp=bih->biBitCount;

	if (w<=0 || h<=0 || w>4096 || h>4096) return NULL;
	if (bih->biCompression!=BI_RGB && !(bih->biCompression==BI_BITFIELDS && (bpp==16 || bpp==32))) {
		xlog(0,"%s: compressed bitmaps are not supported",name);
		return NULL;
	}
	if (bpp!=8 && bpp!=16 && bpp!=24 && bpp!=32) {
		xlog(0,"%s: %d bit bitmaps are not supported",name,bpp);
		return NULL;
	}

	if (bpp==16) {
		if (bih->biCompression==BI_BITFIELDS) {
			unsigned int *m=(unsigned int*)pal;
			rm=m[0]; gm=m[1]; bm=m[2];
		} else { rm=0x7C00; gm=0x03E0; bm=0x001F; }
	}

	stride=((w*bpp+31)/32)*4;

	target=xmalloc(w*h*2);
	if (!target) return NULL;

	for (y=0; y<h; y++) {
		row=bits+(size_t)(topdown ? y : h-1-y)*stride;
		for (x=0; x<w; x++) {
			switch (bpp) {
				case 8:
					idx=row[x];
					r=pal[idx].rgbRed; g=pal[idx].rgbGreen; b=pal[idx].rgbBlue;
					break;
				case 16:
					v=row[x*2]|(row[x*2+1]<<8);
					if (rm==0xF800) { r=(v>>8)&0xF8; g=(v>>3)&0xFC; b=(v<<3)&0xF8; }
					else { r=(v>>7)&0xF8; g=(v>>2)&0xF8; b=(v<<3)&0xF8; }
					break;
				case 24:
					b=row[x*3]; g=row[x*3+1]; r=row[x*3+2];
					break;
				default:
					b=row[x*4]; g=row[x*4+1]; r=row[x*4+2];
					break;
			}
			target[x+y*w]=(unsigned short)(((r>>3)<<11)|((g>>2)<<5)|(b>>3));
		}
	}

	*xs=w;
	*ys=h;

	return target;
}

/* ------------------
     sprite manager
   ------------------*/

// note:
// tiles in the upper left corner of the cache area will be destroyed by loading a new
// sprite

#define MAXEFFECT	1024

#define current_tick GetTickCount()


struct sprtab {
	unsigned short *image;			// null means not loaded	
	unsigned char *alpha;			// null means no alpha information present
	unsigned short *cache;
	unsigned char xs;			// in tiles
	unsigned char ys;			// in tiles
	unsigned short alphacnt;
	unsigned int ticker;
	unsigned short avgcol;
};

struct cachetab {
	unsigned int sprite;
	unsigned int ticker;
	unsigned int effect;
	unsigned int visible;
};

static struct sprtab *sprtab=NULL;
static struct cachetab *cachetab=NULL;

int dd_cache_hit=0,dd_cache_miss=0;

void free_2nd_cache(void)
{
	int n,m,old=0,tmp,t;

	int freed,panic=0;

	t=GetTickCount();

	while (usedmem+256*1024>maxmem && panic++<64) {
		freed=0;
		for (n=0; n<MAXSPRITE; n++) {
			if (!sprtab[n].image) continue;
			if (!sprtab[n].ticker) continue;
			tmp=t-sprtab[n].ticker;
			if (tmp>old) old=tmp;
		}
		old-=old/3;
		for (n=0; n<MAXSPRITE; n++) {
			if (!sprtab[n].image) continue;
			if (!sprtab[n].ticker) continue;
			tmp=t-sprtab[n].ticker;

			if (tmp>old) {
				for (m=0; m<MAXEFFECT*sprtab[n].xs*sprtab[n].ys; m++) {
					tmp=sprtab[n].cache[m];
					if (cachetab[tmp].sprite) {
						usedvid--;
						cachetab[tmp].sprite=0;
						cachetab[tmp].ticker=0;
						cachetab[tmp].effect=0;
						cachetab[tmp].visible=0;
					}
				}
				xfree(sprtab[n].cache); blockgc++;
				xfree(sprtab[n].image); blockgc++;

				if (sprtab[n].alpha) { free(sprtab[n].alpha); }

				sprtab[n].image=NULL;
				sprtab[n].alpha=NULL;
				sprtab[n].alphacnt=0;
				sprtab[n].ticker=0;
				sprtab[n].avgcol=0;
				freed++;
			}

		}
		if (!freed) break;
	}
}

unsigned short avgcolor(unsigned short *ptr,int xs,int ys)
{
	int size=xs*ys,n;
	int r=0,g=0,b=0,c=0;

	for (n=0; n<size; n++) {
		switch (RGBM) {
			case 0:
				if (ptr[n]!=0xf81f) {
					r+=((ptr[n]&0xF800)>>11);
					g+=((ptr[n]&0x07E0)>>5);
					b+=((ptr[n]&0x001F));
					c++;
				}
				break;
			case 1:
				if (ptr[n]!=0x7c1f) {
					r+=((ptr[n]&0x7C00)>>10);
					g+=((ptr[n]&0x03E0)>>5);
					b+=((ptr[n]&0x001F));
					c++;
				}
				break;
			case 2:
				if (ptr[n]!=0xf81f) {
					b+=((ptr[n]&0x7C00)>>10);
					g+=((ptr[n]&0x03E0)>>5);
					r+=((ptr[n]&0x001F));
					c++;
				}
				break;
		}
	}
	if (c) {
		r/=c;
		g/=c;
		b/=c;
	}

	switch (RGBM) {
		case 0: return(unsigned short)((r<<11)+(g<<5)+b);
		case 1: return(unsigned short)((r<<10)+(g<<5)+b);
		case 2: return(unsigned short)((b<<11)+(g<<5)+r);
		default: return 42;
	}
}

int get_avgcol(int nr)
{
	return sprtab[nr].avgcol;
}

void *conv_load(int nr,int *xs,int *ys);

extern char path[];

// HUD colour theme. 0 = original red marble / gold, 1 = deep grey / tan,
// 2 = clean: flat grey panels and crisp tan lines drawn at full resolution.
// Applied to the HUD picture (sprite 1) when it is loaded, so every piece of
// the HUD that comes from it (panels, borders, legacy panels) follows.
int hud_theme=2;

static void hud_theme_apply(unsigned short *p,int xs,int ys)
{
	int x,y,r,g,b,L,gv,s;
	unsigned short v;

	for (y=0; y<ys; y++) for (x=0; x<xs; x++) {
		v=p[x+y*xs];
		if (v==0xF81F) continue;
		r=((v>>11)&31)*255/31; g=((v>>5)&63)*255/63; b=(v&31)*255/31;
		if (b>r) continue;				// blue background: keep
		L=(30*r+59*g+11*b)/100;
		if (r*10>g*16+40) {				// dark red marble -> deep grey
			gv=28+((L-14)*22)/100;
			if (gv<18) gv=18;
			if (gv>40) gv=40;
			// neutral grey in RGB565: green gets exactly twice the red/blue level
			p[x+y*xs]=(unsigned short)(((gv>>3)<<11)|(((gv>>3)*2)<<5)|((gv*107/100)>>3));
			continue;
		} else if (r+g>8) {				// gold -> tan, same brightness
			// keep the coin icons in the gold buttons (legacy 217..303, 176..261)
			if (x>=217 && x<304 && y>=176 && y<262 &&
			    x!=218 && x!=219 && x!=246 && x!=247 && x!=274 && x!=275 && x!=301 && x!=302 &&
			    y!=176 && y!=177 && y!=203 && y!=204 && y!=231 && y!=232 && y!=258 && y!=259 && y!=260) continue;
			s=L*1000/911;
			r=s; g=s*92/100; b=s*62/100;
			if (r>255) r=255;
			if (g>255) g=255;
			if (b>255) b=255;
		} else continue;
		p[x+y*xs]=(unsigned short)(((r>>3)<<11)|((g>>2)<<5)|(b>>3));
	}
}

void dd_load_sprite(int nr)
{
	int xs,ys,alphacnt=0;
	unsigned short *optr=NULL;
	unsigned char *alpha=NULL;
	char buf[300];
	FILE *fp;

	if (usedmem>maxmem) free_2nd_cache();

	if (!optr) {	// try to load from single png file
		sprintf(buf,"%sgfx\\%05d.png",path,nr);
		fp=fopen(buf,"rb");
		if (fp) {
			optr=dd_load_png(fp,&xs,&ys,&alpha,&alphacnt);
			fclose(fp);
		}
	}	
        if (!optr) {	// try to load from pnglib
		fp=load_pnglib(nr);
		if (fp) optr=dd_load_png(fp,&xs,&ys,&alpha,&alphacnt);
	} 
        if (!optr) {	// try to load from single bmp file
	    sprintf(buf,"%sgfx\\%05d.bmp",path,nr);
	    optr=dd_load_bitmap(buf,&xs,&ys,suro);
	}
	if (!optr) {	// try to load from bmplib
		optr=conv_load(nr,&xs,&ys);
	}
	if (!optr) {	// not found!
		sprintf(buf,"Sprite %d is missing",nr);
		xlog(0,buf);
		return;
	}

	sprtab[nr].image=optr;
	sprtab[nr].alpha=alpha;
	sprtab[nr].alphacnt=(unsigned short)alphacnt;
	sprtab[nr].xs=(unsigned char)(xs/TILE);
	sprtab[nr].ys=(unsigned char)(ys/TILE);
	if (nr==1 && hud_theme>=1) hud_theme_apply(optr,xs,ys);
	sprtab[nr].avgcol=avgcolor(optr,xs,ys);

	sprtab[nr].cache=xcalloc(MAXEFFECT*sizeof(short),sprtab[nr].xs*sprtab[nr].ys);
}

void dd_invalidate_cache(void)
{
	int n;

	for (n=0; n<MAXCACHE; n++) {
		cachetab[n].ticker=0;
		cachetab[n].sprite=0;
		cachetab[n].effect=0;
		cachetab[n].visible=0;
	}
	usedvid=0;
}

void dd_init_sprites(void)
{
	MEMORYSTATUSEX ms;

	// PORT: GlobalMemoryStatus() overflows on machines with >2GB (returns
	// -1 / 2GB), which made maxmem garbage. Use a sane fixed budget for the
	// decoded sprite cache instead, capped by what is actually available.
	ms.dwLength=sizeof(ms);
	maxmem=256*1024*1024;
	if (GlobalMemoryStatusEx(&ms) && ms.ullAvailPhys/4<(DWORDLONG)maxmem) maxmem=(int)(ms.ullAvailPhys/4);
	if (maxmem<32*1024*1024) maxmem=32*1024*1024;
	maxvid=MAXCACHE;

	if (!sprtab) sprtab=xcalloc(MAXSPRITE,sizeof(struct sprtab));
	if (!cachetab) cachetab=xcalloc(MAXCACHE,sizeof(struct cachetab));

	dd_set_background(RED+BLUE);
}

#define LEFFECT	(gamma-4880)   //120

int gamma=5000;

unsigned short do_effect(unsigned short val,int effect,int seed1,int seed2,int sprite)
{
	int r,g,b,invis=0,tmp,grey=0,infra=0,water=0,red=0,green=0;

	if (effect&16) { effect-=16; red=1; }//red border
	if (effect&32) { effect-=32; green=1; }//green border
	if (effect&64) { effect-=64; invis=1; } //blackened out
	if (effect&128) { effect-=128; grey=1; } //grey scale
	if (effect&256) { effect-=256; infra=1; } //grey scale
	if (effect&512) { effect-=512; water=1; } //grey scale

	switch (RGBM) {
		case 0:
			if (val!=0xf81f) {
				r=(val&0xf800)>>11;
				g=(val&0x07e0)>>5;
				b=(val&0x001f);

				/* !!!!!!!!  color channel stuff
				if (sprite>2000+30*1024) {
					int r2=0,g2=0,b2=0;

					r2+=r*300/256;
					g2+=r*300/256;
					b2+=r*300/256; 

					r2+=g*120/512;	// 224
					g2+=g*50/512;	// 167
					b2+=g*20/512;	// 144

					r2+=b*256/256;
					g2+=b*  0/256;
					b2+=b*  0/256;

                                        r=r2;
					g=g2*2;
					b=b2;

					if (r>31) r=31;
					if (g>63) g=63;
					if (b>31) b=31;

				} !!!!!! */

				if (effect) {
					r=(r*LEFFECT)/(effect*effect+LEFFECT);
					g=(g*LEFFECT)/(effect*effect+LEFFECT);
					b=(b*LEFFECT)/(effect*effect+LEFFECT);
				}

                                if (grey) {
					tmp=(r+(g/2)+b)/6;
					r=tmp;
					b=tmp;
					g=tmp*2;
				}

				if (infra) {
					tmp=(r+(g/2)+b)/3;
					r=tmp;
					b=0;
					g=0;
				}

				if (water) {
					tmp=(r+(g/2)+b)/2;
					if (tmp>31)	tmp=31;
					r=(r+tmp)/3;
					b=(b+tmp); if (b>31) b=31;
					g=((g+tmp)/3)*2;
				}

				if (gamma!=5000) {
					r=r*gamma/5000; if (r>31) r=31;
					g=g*gamma/5000; if (g>63) g=63;
					b=b*gamma/5000; if (b>31) b=31;
				}

				//if (red) { r+=15; if (r>31) r=31; }

				if (red) { 
					r*=2; if (r>31) r=31;
					g*=2; if (g>63) g=63;
					b*=2; if (b>31) b=31;					
				}

				if (green) { g+=31; if (g>63) g=63; }

				if (invis) {
					r=g=b=0;
				}

                                return(unsigned short)((r<<11)+(g<<5)+b);
			} else return val;

		case 1:
			if (val!=0x7C1F) {
				r=(val&0x7C00)>>10;
				g=(val&0x03E0)>>5;
				b=(val&0x001F);

				if (effect) {
					r=(r*LEFFECT)/(effect*effect+LEFFECT);
					g=(g*LEFFECT)/(effect*effect+LEFFECT);
					b=(b*LEFFECT)/(effect*effect+LEFFECT);
				}

				if (grey) {
					tmp=(r+g+b)/6;
					r=tmp;
					b=tmp;
					g=tmp;
				}

				if (infra) {
					tmp=(r+g+b)/3;
					r=tmp;
					b=0;
					g=0;
				}

				if (water) {
					tmp=(r+g+b)/2;
					if (tmp>31)	tmp=31;
					r=(r+tmp)/3;
					b=(b+tmp); if (b>31) b=31;
					g=(g+tmp)/3;
				}

				if (gamma!=5000) {
					r=r*gamma/5000; if (r>31) r=31;
					g=g*gamma/5000; if (g>31) g=31;
					b=b*gamma/5000; if (b>31) b=31;
				}

				if (red) { r+=15; if (r>31) r=31; }
				if (green) { g+=15; if (g>31) g=31; }

				if (invis) {
					r=g=b=0;
				}

				return(unsigned short)((r<<10)+(g<<5)+b);
			} else return val;

		case 2:
			if (val!=0xf81f) {
				b=(val&0xf800)>>11;
				g=(val&0x07e0)>>5;
				r=(val&0x001f);

				if (effect) {
					r=(r*LEFFECT)/(effect*effect+LEFFECT);
					g=(g*LEFFECT)/(effect*effect+LEFFECT);
					b=(b*LEFFECT)/(effect*effect+LEFFECT);
				}

				if (invis) {
					r=g=b=0;
				}

				if (grey) {
					tmp=(r+(g/2)+b)/6;
					r=tmp;
					b=tmp;
					g=tmp*2;
				}

				if (infra) {
					tmp=(r+(g/2)+b)/3;
					r=tmp;
					b=0;
					g=0;
				}

				if (water) {
					tmp=(r+g+b)/2;
					if (tmp>31)	tmp=31;
					r=(r+tmp)/3;
					b=(b+tmp); if (b>31) b=31;
					g=(g+tmp)/3;
				}

				if (gamma!=5000) {
					r=r*gamma/5000; if (r>31) r=31;
					g=g*gamma/5000; if (g>63) g=63;
					b=b*gamma/5000; if (b>31) b=31;
				}

				return(unsigned short)((b<<11)+(g<<5)+r);
			} else return val;

		default:    return val;
	}
}

int tile2cache(int tile,int sprite,int xpos,int ypos,int xs,int effect)
{
	int cx,cy,sx,sy,x,y,visible=0;
	unsigned short *screen,*image;
	extern int ticker;

	screen=dd_get_ptr(suro);
	if (!screen) return 0;

	image=sprtab[sprite].image;

	cx=(tile%cachex)*TILE;
	cy=(tile/cachex)*TILE;

	sx=xpos*32;
	sy=ypos*32;

	screen+=cx+cy*MAXXOVER;
	image+=sx+sy*xs*32;

	for (y=0; y<32; y++) {
		for (x=0; x<32; x++) {
			if ((*screen=do_effect(*image,effect,x,y,sprite))!=background)	visible=1;
			image++; screen++;
		}
		screen+=MAXXOVER-32;
		image+=(xs-1)*32;
	}


	dd_release_ptr(suro);

	return visible;
}

int gettile(unsigned int sprite,unsigned int effect,int x,int y,int xs)
{
	int n,old=0;
	unsigned int nr,oldrec=0;

	nr=(sprite<<16)+x+y*xs;

	n=sprtab[sprite].cache[(x+y*xs)*MAXEFFECT+effect];
	if (cachetab[n].sprite==nr && cachetab[n].effect==effect) {
		cachetab[n].ticker=0;
		dd_cache_hit++;
		if (!cachetab[n].visible) {
			invisible++; return -1;
		}
		return n;
	}

	for (n=0; n<MAXCACHE; n++) {
		if (cachetab[n].sprite==0) {
			oldrec=0x7fffffff; old=n;
		}
		if (cachetab[n].ticker>oldrec) {
			oldrec=cachetab[n].ticker; old=n;
		}
		cachetab[n].ticker++;
	}
	dd_cache_miss++;

	if (oldrec==0x7fffffff)	usedvid++;

	cachetab[old].visible=tile2cache(old,sprite,x,y,xs,effect);
	cachetab[old].sprite=nr;
	cachetab[old].ticker=(rand()%1024)+24;
	cachetab[old].effect=effect;
	sprtab[sprite].cache[(x+y*xs)*MAXEFFECT+effect]=(short)old;

	if (!cachetab[old].visible) {
		invisible++; return -1;
	}

	return old;
}

void copysprite(int nr,int effect,int xpos,int ypos,int xoff,int yoff)
{
	unsigned int x,y,xs,ys,n,rx,ry;

	if (nr==0) return;

        // image loaded?
	if (!sprtab[nr].image) dd_load_sprite(nr);
	if (!sprtab[nr].image) return;

	xs=sprtab[nr].xs;
	ys=sprtab[nr].ys;
	sprtab[nr].ticker=current_tick;

	rx=(xpos/2)+(ypos/2)-(xs*16)+32+XPOS-((TILEX-34)/2*32);
	if (xpos<0 && (xpos&1))	rx--;
	if (ypos<0 && (ypos&1))	rx--;
	ry=(xpos/4)-(ypos/4)+YPOS-ys*32;
	if (xpos<0 && (xpos&3))	ry--;
	if (ypos<0 && (ypos&3))	ry++;

	rx+=xoff;
	ry+=yoff;

	for (y=0; y<ys; y++) {
		for (x=0; x<xs; x++) {
			n=gettile(nr,effect,x,y,xs);
			if (n==-1) continue;
			dd_copytile(n,rx+x*32,ry+y*32,sur2,1);
		}
	}
	if (sprtab[nr].alpha) display_alpha(sprtab[nr].alpha,sprtab[nr].alphacnt,rx,ry,effect);
}

void copyspritex(int nr,int xpos,int ypos,int effect)
{
	unsigned int x,y,xs,ys,n;

	if (nr==0) return;

	// image loaded?
	if (!sprtab[nr].image) dd_load_sprite(nr);
	if (!sprtab[nr].image) return;

	xs=sprtab[nr].xs;
	ys=sprtab[nr].ys;
	sprtab[nr].ticker=current_tick;

	for (y=0; y<ys; y++) {
		for (x=0; x<xs; x++) {
			n=gettile(nr,effect,x,y,xs);
			if (n==-1) continue;
			dd_copytile(n,xpos+x*32,ypos+y*32,sur2,0);
		}
	}
	if (sprtab[nr].alpha) display_alpha(sprtab[nr].alpha,sprtab[nr].alphacnt,xpos,ypos,effect);
}

// draw a sprite shrunk to fit a box of box x box pixels (for big pieces in
// the backpack, e.g. walls and trees in build mode); small sprites as usual
void copyspritex_fit(int nr,int xpos,int ypos,int box,int effect)
{
	int w,h,dw,dh,x,y,sx,sy,ox,oy;
	unsigned short *dst,v;

	if (nr==0) return;
	if (!sprtab[nr].image) dd_load_sprite(nr);
	if (!sprtab[nr].image) return;
	if (sprtab[nr].xs<=1 && sprtab[nr].ys<=1) { copyspritex(nr,xpos,ypos,effect); return; }

	w=sprtab[nr].xs*32; h=sprtab[nr].ys*32;
	sprtab[nr].ticker=current_tick;
	if (w>=h) { dw=box; dh=h*box/w; } else { dh=box; dw=w*box/h; }
	if (dw<1 || dh<1) return;
	ox=xpos+(box-dw)/2; oy=ypos+(box-dh);		// centred, standing on the bottom of the box

	dst=dd_get_ptr(sur2);
	if (!dst) return;
	for (y=0; y<dh; y++) {
		if (oy+y<0 || oy+y>=MAXY) continue;
		sy=y*h/dh;
		for (x=0; x<dw; x++) {
			if (ox+x<0 || ox+x>=MAXX) continue;
			sx=x*w/dw;
			v=sprtab[nr].image[sx+sy*w];
			if (v==0xF81F) continue;
			if (effect&16) v=(unsigned short)(((v>>1)&0x7BEF)+0x39E7);	// highlighted
			dst[(ox+x)+(oy+y)*MAXX]=v;
		}
	}
	dd_release_ptr(sur2);
}

void dd_savescreen(void)
{
	static int lasttime=0;
	HGLOBAL mem;
	BITMAPINFOHEADER *bih;
	unsigned char *dst;
	unsigned short v;
	int x,y,stride;

	if (time(NULL)-lasttime<10) {
		xlog(0,"One moment please, I'm counting my bits!");
		return;
	}

	lasttime=(int)time(NULL);

	stride=((sur1->w*3)+3)&~3;
	mem=GlobalAlloc(GMEM_MOVEABLE,sizeof(BITMAPINFOHEADER)+stride*sur1->h);
	if (!mem) return;
	bih=GlobalLock(mem);
	memset(bih,0,sizeof(*bih));
	bih->biSize=sizeof(*bih);
	bih->biWidth=sur1->w;
	bih->biHeight=sur1->h;
	bih->biPlanes=1;
	bih->biBitCount=24;
	bih->biCompression=BI_RGB;
	dst=(unsigned char*)(bih+1);

	for (y=0; y<sur1->h; y++) {
		unsigned char *row=dst+(size_t)(sur1->h-1-y)*stride;
		for (x=0; x<sur1->w; x++) {
			v=sur1->bits[x+y*sur1->pitch];
			row[x*3+0]=(unsigned char)((v&0x001F)<<3);
			row[x*3+1]=(unsigned char)((v&0x07E0)>>3);
			row[x*3+2]=(unsigned char)((v&0xF800)>>8);
		}
	}
	GlobalUnlock(mem);

	if (!OpenClipboard(desk_hwnd)) { GlobalFree(mem); return; }
	EmptyClipboard();
	if (!SetClipboardData(CF_DIB,mem)) GlobalFree(mem);
	CloseClipboard();

	xlog(2,"Placed screenshot in clipboard.");
}

void dd_gputc(int xpos,int ypos,int font,int c)
{
	unsigned short *fptr,*tptr;
	int x,y,off,nr;

	if (c>127) return;
	c-=32;

	if (font<0 || font>3) return;
	nr=700+font;

	// image loaded?
	if (!sprtab[nr].image) dd_load_sprite(nr);
	if (!sprtab[nr].image) return;

	if (c<0 || xpos<0 || ypos<0 || xpos+6>MAXX || ypos+9>MAXY) return;

	off=c*6;
	tptr=dd_get_ptr(sur2);
	if (!tptr) return;
	tptr+=xpos+ypos*MAXX;
	fptr=sprtab[nr].image+off+576;
	sprtab[nr].ticker=current_tick;

	for (y=0; y<9; y++) {
		for (x=0; x<6; x++,tptr++,fptr++) {
			if (*fptr!=background)
				*tptr=*fptr;
		}
		tptr+=MAXX-6;
		fptr+=576-6;
	}

	dd_release_ptr(sur2);

	return;
}

void dd_gputtext(int xpos,int ypos,int font,char *text,int xoff,int yoff)
{
	int rx,ry,len;

	len=strlen(text);

	rx=(xpos/2)+(ypos/2)+32-((len*5)/2)+XPOS-((TILEX-34)/2*32);
	if (xpos<0 && (xpos&1))	rx--;
	if (ypos<0 && (ypos&1))	rx--;
	ry=(xpos/4)-(ypos/4)+YPOS-64;
	if (xpos<0 && (xpos&3))	ry--;
	if (ypos<0 && (ypos&3))	ry++;

	rx+=xoff;
	ry+=yoff;

	while (*text) {
		if (rx<0 || rx>MODEX-7 || ry<0 || ry>MODEY-10) return;
		dd_gputc(rx,ry,font,*text);
		text++; rx+=6;
	}
}

/* ---- smooth HUD font ------------------------------------------------------
 * With hud_font=1, text drawn on the HUD canvas is not drawn with the old
 * 6x9 bitmap font: it is remembered here and drawn by the presenter with a
 * real font at full window resolution, one character per 6-unit cell so all
 * the layout stays as it was. hud_font=0 keeps the old font.
 */
int hud_font=1;

#define MAXHTEXT	4096
#define HTEXTPOOL	(256*1024)
static struct htext htexts[MAXHTEXT];
static int nhtext=0,htextpos=0;
static char htextpool[HTEXTPOOL];

static void htext_add(int x,int y,int font,const char *text,int len)
{
	if (nhtext>=MAXHTEXT || htextpos+len+1>HTEXTPOOL || len<=0) return;
	htexts[nhtext].x=x; htexts[nhtext].y=y; htexts[nhtext].font=font;
	htexts[nhtext].len=len; htexts[nhtext].off=htextpos;
	memcpy(htextpool+htextpos,text,len); htextpool[htextpos+len]=0;
	htextpos+=len+1;
	nhtext++;
}

int dd_hud_texts(struct htext **p,char **pool)
{
	*p=htexts; *pool=htextpool;
	return nhtext;
}

// the colour of bitmap font f, so the smooth font uses the same colours
unsigned int dd_font_rgb(int f)
{
	static unsigned int rgb[4]={0,0,0,0};
	int nr=700+f,n,r,g,b,cnt=0;
	unsigned short v;
	unsigned int sr=0,sg=0,sb=0;

	if (f<0 || f>3) f=1;
	if (rgb[f]) return rgb[f];
	if (!sprtab[nr].image) dd_load_sprite(nr);
	if (!sprtab[nr].image) return 0xFFFFFF;
	for (n=0; n<576*9 && cnt<2000; n++) {	// average of the glyph pixels
		v=sprtab[nr].image[576+n%576+(n/576)*576];
		if (v==background) continue;
		if (RGBM==0) { r=(v>>11)<<3; g=((v>>5)&63)<<2; b=(v&31)<<3; }
		else { r=((v>>10)&31)<<3; g=((v>>5)&31)<<3; b=(v&31)<<3; }
		if (r+g+b<120) continue;	// skip dark outline pixels
		sr+=r; sg+=g; sb+=b; cnt++;
	}
	if (!cnt) return 0xFFFFFF;
	rgb[f]=((sr/cnt)<<16)|((sg/cnt)<<8)|(sb/cnt)|0x01000000;
	return rgb[f];
}

void dd_putc(int xpos,int ypos,char font,int c)
{
	unsigned short *fptr,*tptr;
	int x,y,off,nr;

	if (c>127) return;
	c-=32;

	if (font<0 || font>3) return;

	if (hud_active==2 && hud_font) {
		char ch=(char)(c+32);
		if (c>0 && xpos>=0 && ypos>=0 && xpos+6<=MAXX && ypos+9<=MAXY) htext_add(xpos,ypos,font,&ch,1);
		return;
	}

	nr=700+font;

	// image loaded?
	if (!sprtab[nr].image) dd_load_sprite(nr);
	if (!sprtab[nr].image) return;

	if (c<0 || xpos<0 || ypos<0 || xpos+6>MAXX || ypos+9>MAXY) return;

	off=c*6;
	tptr=dd_get_ptr(sur2);
	if (!tptr) return;
	tptr+=xpos+ypos*MAXX;
	fptr=sprtab[nr].image+off+576;
	sprtab[nr].ticker=current_tick;

	for (y=0; y<9; y++) {
		for (x=0; x<6; x++,tptr++,fptr++) {
			if (*fptr!=background)
				*tptr=*fptr;
		}
		tptr+=MAXX-6;
		fptr+=576-6;
	}

	dd_release_ptr(sur2);

	return;
}

void dd_puttext(int x,int y,int font,char *text)
{
	if (hud_active==2 && hud_font && font>=0 && font<=3) {
		if (x>=0 && y>=0 && y+9<=MAXY) htext_add(x,y,font,text,(int)strlen(text));
		return;
	}
	while (*text) {
		dd_putc(x,y,(char)font,*text);
		text++; x+=6;
	}
}

void dd_xputtext(int x,int y,int font,char *format,...)
{
	va_list args;
	char buf[1024];

	va_start(args,format);
	vsprintf(buf,format,args);
	dd_puttext(x,y,font,buf);
	va_end(args);
}

int dd_isvisible(void)
{
	// no lost surfaces any more; just skip drawing while minimized
	return !IsIconic(desk_hwnd);
}

void dd_show_map(unsigned short *src,int xo,int yo)
{
	unsigned short *dst;
	int x,y,d,s;

	dst=dd_get_ptr(sur2);
	if (!dst) return;

	for (y=0; y<128; y++) {
		d=(y+471)*MAXX+3;
		s=(y+yo)*1024+xo;
		for (x=0; x<128; x++) {
			dst[d++]=src[s++];
		}
	}
	dd_release_ptr(sur2);
}

void do_rgb8_effect(int *r1,int *g1,int *b1,int effect)
{
    int r,g,b,invis=0,tmp,grey=0,infra=0,water=0,red=0,green=0;

    if (effect&16) { effect-=16; red=1; } //red border
    if (effect&32) { effect-=32; green=1; } //green border
    if (effect&64) { effect-=64; invis=1; } //blackened out
    if (effect&128) { effect-=128; grey=1; } //grey scale
    if (effect&256) { effect-=256; infra=1; } //infrared
    if (effect&512) { effect-=512; water=1; } //under water
		
    r=*r1;
    g=*g1;
    b=*b1;

    if (effect) {
	    r=(r*LEFFECT)/(effect*effect+LEFFECT);
	    g=(g*LEFFECT)/(effect*effect+LEFFECT);
	    b=(b*LEFFECT)/(effect*effect+LEFFECT);
    }

    if (grey) {
	    tmp=(r+g+b)/6;
	    r=tmp;
	    b=tmp;
	    g=tmp;
    }

    if (infra) {
	    tmp=(r+g+b)/3;
	    r=tmp;
	    b=0;
	    g=0;
    }

    if (water) {
	    tmp=(r+g+b)/2;
	    if (tmp>31)	tmp=31;
	    r=(r+tmp)/3;
	    b=(b+tmp); if (b>31) b=31;
	    g=(g+tmp)/3;
    }

    if (gamma!=5000) {
	    r=r*gamma/5000; if (r>255) r=255;
	    g=g*gamma/5000; if (g>255) g=255;
	    b=b*gamma/5000; if (b>255) b=255;
    }

    //if (red) { r+=128; if (r>255) r=255; }
    if (red) { 
	    r*=2; if (r>255) r=255; 
	    g*=2; if (g>255) g=255; 
	    b*=2; if (b>255) b=255; 
	}
    if (green) { g+=128; if (g>255) g=255; }

    if (invis) {
	    r=g=b=0;
    }

    *r1=r;
    *g1=g;
    *b1=b;
}


void display_alpha(unsigned char *alpha,int alphacnt,int xf,int yf,int effect)
{
    unsigned short *dst,val;
    int x,y,r1,g1,b1,r2,b2,g2,a1,a2,r,g,b,n,pos;

    dst=dd_get_ptr(sur2);
    if (!dst) return;

    for (n=0; n<alphacnt; n+=6) {	
	x=alpha[n+0];
	y=alpha[n+1];
        r1=alpha[n+2];
	g1=alpha[n+3];
	b1=alpha[n+4];
	a1=alpha[n+5];
	a2=256-a1;

	do_rgb8_effect(&r1,&g1,&b1,effect);

	if (x+xf<0 || x+xf>=MAXX || y+yf<0 || y+yf>=MAXY) continue;
	pos=x+xf+y*MAXX+yf*MAXX;
	val=dst[pos];

	if (RGBM==0) {
	    r2=(val&RED)>>8; 
	    g2=(val&GREEN)>>3;
	    b2=(val&BLUE)<<3;
	} else {
	    r2=(val&RED)>>7;
	    g2=(val&GREEN)>>2;
	    b2=(val&BLUE)<<3;
	}	

	r=(r1*a1+r2*a2)/256;
	g=(g1*a1+g2*a2)/256;
	b=(b1*a1+b2*a2)/256;

        if (RGBM==0) dst[pos]=(unsigned short)(((r<<8)&RED)+((g<<3)&GREEN)+((b>>3)&BLUE));
	else dst[pos]=(unsigned short)(((r<<7)&RED)+((g<<2)&GREEN)+((b>>3)&BLUE));
	
    }

    dd_release_ptr(sur2);
}

// displays a png in RGBA 8 bit format (memory blocks, not the silly rows-concept)
void display_png(unsigned char *png,int xf,int yf,int xs,int ys)
{
    unsigned short *dst;
    int x,y,r1,g1,b1,r2,b2,g2,a1,a2,r,g,b;

    dst=dd_get_ptr(sur2);
    if (!dst) return;

    for (y=0; y<ys; y++) {
	if (y+yf<0 || y+yf>=MAXY) continue;
	for (x=0; x<xs; x++) {
	    if (x+xf<0 || x+xf>=MAXX) continue;
	    r1=png[x*4+y*xs*4+0];
	    g1=png[x*4+y*xs*4+1];
	    b1=png[x*4+y*xs*4+2];
	    a1=png[x*4+y*xs*4+3];
	    a2=256-a1;

            if (RGBM==0) {
		r2=(dst[x+xf+y*MAXX+yf*MAXX]&RED)>>8;
		g2=(dst[x+xf+y*MAXX+yf*MAXX]&GREEN)>>3;
		b2=(dst[x+xf+y*MAXX+yf*MAXX]&BLUE)<<3;
	    } else {
		r2=(dst[x+xf+y*MAXX+yf*MAXX]&RED)>>7;
		g2=(dst[x+xf+y*MAXX+yf*MAXX]&GREEN)>>2;
		b2=(dst[x+xf+y*MAXX+yf*MAXX]&BLUE)<<3;
	    }	

	    r=(r1*a1+r2*a2)/256;
	    g=(g1*a1+g2*a2)/256;
	    b=(b1*a1+b2*a2)/256;

            if (RGBM==0) dst[x+xf+y*MAXX+yf*MAXX]=(unsigned short)(((r<<8)&RED)+((g<<3)&GREEN)+((b>>3)&BLUE));
	    else dst[x+xf+y*MAXX+yf*MAXX]=(unsigned short)(((r<<7)&RED)+((g<<2)&GREEN)+((b>>3)&BLUE));
	}
    }

    dd_release_ptr(sur2);
}

// reads a PNG file and transforms the data into a 16 bit RGB data (returned as ptr to memory block)
// the alpha information is stored in alpha_ptr & alphacnt_ptr in the format x,y,r,g,b,a for all
// pixels actually having alpha information.
// pixel with alpha!=255 (i.e. partially or fully transparent pixels) are marked as the transparent
// color in the 16 bit RGB data to allow blitting them with FastBLT.
// the alpha information may be used, but doesnt need to - it just looks better...
unsigned short *dd_load_png(FILE *fp,int *xs,int *ys,unsigned char **alpha_ptr,int *alphacnt_ptr)
{
    int x,y,n,m,alphacnt=0,alphamax=0,noalpha=0,mul=4,r,g,b,a;
    unsigned char *pix,*p,*alpha=NULL;
    unsigned short *bmp;

    pix=png_decode(fp,&x,&y,&mul);
    if (!pix) { xlog(0,"png decode failed"); return 0; }
    if (mul==3) noalpha=1;

    bmp=xmalloc(x*y*2);
    if (!bmp) { free(pix); return 0; }

    for (n=0; n<y; n++) {
	for (m=0; m<x; m++) {
	    p=pix+((size_t)n*x+m)*mul;
	    if (noalpha) {
		if (p[0]>250 && p[1]<5 && p[2]>250) a=0;
		else a=255;
	    } else a=p[3];

	    // this gets the rgb info from the png and scales the colors to their original value. 3dsmax will mix the image
	    // color and the background color AND supply alpha information, which is just plain wrong...
	    if (a) {
		    r=min(255,p[0]*255/a);
		    g=min(255,p[1]*255/a);
		    b=min(255,p[2]*255/a);
	    } else {
		    r=p[0];
		    g=p[1];
		    b=p[2];
	    }

	    if ((do_alpha==0 && a<64) ||
		(do_alpha==1 && a<192) ||
		(do_alpha==2 && a<255))	bmp[m+n*x]=(unsigned short)(RED|BLUE);
	    else if (RGBM==0) bmp[m+n*x]=(unsigned short)(((r<<8)&RED)+((g<<3)&GREEN)+((b>>3)&BLUE));
	    else bmp[m+n*x]=(unsigned short)(((r<<7)&RED)+((g<<2)&GREEN)+((b>>3)&BLUE));

	    if (!noalpha && ((do_alpha==1 && a>63 && a<192) || (do_alpha==2 && a!=0 && a!=255))) {
		if (alphacnt>=alphamax-8) {
		    alphamax+=32;
		    p=realloc(alpha,alphamax);
		    if (!p) break;
		    alpha=p;
		}
		*(unsigned char*)(alpha+alphacnt)=(unsigned char)m; alphacnt+=1;
		*(unsigned char*)(alpha+alphacnt)=(unsigned char)n; alphacnt+=1;
		*(unsigned char*)(alpha+alphacnt)=r; alphacnt+=1;
		*(unsigned char*)(alpha+alphacnt)=g; alphacnt+=1;
		*(unsigned char*)(alpha+alphacnt)=b; alphacnt+=1;
		*(unsigned char*)(alpha+alphacnt)=a; alphacnt+=1;

		alphapix++;
	    } else fullpix++;
	}
    }

    if (alpha && alphacnt) { p=realloc(alpha,alphacnt); if (p) alpha=p; }

    free(pix);

    *alpha_ptr=alpha;
    *alphacnt_ptr=alphacnt;
    *xs=x;
    *ys=y;

    return bmp;
}

void dd_invalidate_alpha(void)
{
    int n,tmp,m;

    for (n=0; n<MAXSPRITE; n++) {
	if (!sprtab[n].image) continue;

	for (m=0; m<MAXEFFECT*sprtab[n].xs*sprtab[n].ys; m++) {
            tmp=sprtab[n].cache[m];
		if (cachetab[tmp].sprite) {
			usedvid--;
			cachetab[tmp].sprite=0;
			cachetab[tmp].ticker=0;
			cachetab[tmp].effect=0;
			cachetab[tmp].visible=0;
		}
	}
	xfree(sprtab[n].cache); blockgc++;
	xfree(sprtab[n].image); blockgc++;

	if (sprtab[n].alpha) { free(sprtab[n].alpha); }

	sprtab[n].image=NULL;
	sprtab[n].alpha=NULL;
	sprtab[n].alphacnt=0;
	sprtab[n].ticker=0;
	sprtab[n].avgcol=0;
    }
}

static unsigned char *shadowmap;

/* low hitpoints: a soft red glow on the ground under our character, slowly
 * pulsing, a little stronger the lower the hitpoints are. */
void dd_lowhp_glow(int xpos,int ypos,int xoff,int yoff,int pct,int limit)
{
	int rx,ry,cx,cy,x,y,r,g,b,a,amax;
	unsigned short *dst,v;
	double d,ph;
	const int RX=30,RY=15;

	rx=(xpos/2)+(ypos/2)-16+32+XPOS-((TILEX-34)/2*32);
	if (xpos<0 && (xpos&1)) rx--;
	if (ypos<0 && (ypos&1)) rx--;
	ry=(xpos/4)-(ypos/4)+YPOS-32;
	if (xpos<0 && (xpos&3)) ry--;
	if (ypos<0 && (ypos&3)) ry++;
	cx=rx+xoff+16;
	cy=ry+yoff+32-8;	// middle of the floor diamond

	// strength: 35..90 (of 256) depending on how low, pulsing over ~1.6 seconds
	amax=35+55*(limit-pct)/max(1,limit);
	ph=0.65+0.35*sin(GetTickCount()/1600.0*6.2832);
	amax=(int)(amax*ph);

	dst=dd_get_ptr(sur2);
	if (!dst) return;
	for (y=cy-RY; y<=cy+RY; y++) {
		if (y<0 || y>=MAXY) continue;
		for (x=cx-RX; x<=cx+RX; x++) {
			if (x<0 || x>=MAXX) continue;
			d=((double)(x-cx)*(x-cx))/(RX*RX)+((double)(y-cy)*(y-cy))/(RY*RY);
			if (d>=1.0) continue;
			a=(int)(amax*(1.0-d)*(1.0-d));
			if (a<=0) continue;
			v=dst[x+y*MAXX];
			if (RGBM==0) { r=v>>11; g=(v>>5)&63; b=v&31; }
			else { r=(v>>10)&31; g=((v>>5)&31)<<1; b=v&31; }
			r+=((31-r)*a)>>8;
			g-=(g*a)>>9;
			b-=(b*a)>>9;
			if (RGBM==0) dst[x+y*MAXX]=(unsigned short)((r<<11)|(g<<5)|b);
			else dst[x+y*MAXX]=(unsigned short)((r<<10)|((g>>1)<<5)|b);
		}
	}
	dd_release_ptr(sur2);
}

void dd_shadow_clear(void)
{
	if (!shadowmap) shadowmap=calloc(SCREEN_W,SCREEN_H);
	else memset(shadowmap,0,MAXX*MAXY);
}

void dd_shadow(int nr,int xpos,int ypos,int xoff,int yoff)
{
	unsigned int x,y,xs,ys,rx,ry,m,p,v,ok=0,disp,swap=0,n;
	unsigned short *dst,*src;

	if (nr==0) return;

	if (nr>=2000 && nr<16336) { ok=1; disp=14; }
	if (nr>17360) { ok=1; disp=14; }

	if (!ok) return;

        // image loaded?
	if (!sprtab[nr].image) dd_load_sprite(nr);
	if (!sprtab[nr].image) return;

	xs=sprtab[nr].xs;
	ys=sprtab[nr].ys;
	sprtab[nr].ticker=current_tick;

	rx=(xpos/2)+(ypos/2)-(xs*16)+32+XPOS-((TILEX-34)/2*32);
	if (xpos<0 && (xpos&1))	rx--;
	if (ypos<0 && (ypos&1))	rx--;
	ry=(xpos/4)-(ypos/4)+YPOS-ys*32;
	if (xpos<0 && (xpos&3))	ry--;
	if (ypos<0 && (ypos&3))	ry++;

	rx+=xoff;
	ry+=yoff;

	ry+=ys*32-disp;

	dst=dd_get_ptr(sur2);
	if (!dst) return;

	src=sprtab[nr].image;

	for (y=ry+ys*8,m=0; y>ry; y--,m+=xs*96) {
                for (x=rx; x<rx+xs*32; x++,m++) {
                        if (src[m]!=(RED|BLUE)) {
                                
				if (swap==1) p=x+y*MAXX+(int)((x-rx)*0.885)*MAXX;
				else if (swap==2) p=x+y*MAXX-(int)((x-rx)*0.885)*MAXX;
                                else p=x+y*MAXX;

				if (p>=(unsigned)(MAXX*MAXY)) continue;
				if (shadowmap[p]) continue;

				v=dst[p];
				v>>=1;
				if (RGBM==0) v&=(0x7800|0x03E0|0x000F); else v&=(0x3C00|0x01E0|0x000F);
				dst[p]=v;

				shadowmap[p]=1;
			}
		}
	}

	if (sprtab[nr].alpha) {	
		for (n=0; n<(unsigned)sprtab[nr].alphacnt; n+=6) {	
			
			x=sprtab[nr].alpha[n+0]+rx;
			y=ry+ys*8-(sprtab[nr].alpha[n+1]/4);

			if (swap==1) p=x+y*MAXX+(int)((x-rx)*0.885)*MAXX;
			else if (swap==2) p=x+y*MAXX-(int)((x-rx)*0.885)*MAXX;
			else p=x+y*MAXX;
	
			if (p>=(unsigned)(MAXX*MAXY)) continue;
			if (shadowmap[p]) continue;
	
			v=dst[p];
			v>>=1;
			if (RGBM==0) v&=(0x7800|0x03E0|0x000F); else v&=(0x3C00|0x01E0|0x000F);
                        dst[p]=v;
	
			shadowmap[p]=1;
		}
	}
        
	dd_release_ptr(sur2);
}

/*
	switch(nr) {
		case 106:	disp=12; ok=1; break;		// big pillar

		case 460:
		case 461:
		case 462:
		case 463:
		case 464:       disp=12; ok=1; break;		// big candle on

		case 594:
		case 595:	disp=12; ok=1; break;		// big street lamp

		case 792:	disp=12; ok=1; break;		// shrine

		case 946:	disp=12; ok=1; break;		// thick pillar

		case 968:	disp=8; ok=1; swap=2; break;	// iron bars
		case 976:	disp=22; ok=1; swap=1; break;	// iron bars
		case 978:	disp=22; ok=1; swap=1; break;	// iron bars with door

		case 997:	disp=30; ok=1; swap=1; break;	// iron door open
		case 998:	disp=8; ok=1; swap=2; break;	// iron door closed

		case 1102:	
		case 1104:
		case 1106:
		case 1108:	disp=11; ok=1; break;		// golden candle on

		case 1026:	
		case 1028:
		case 1030:
		case 1032:	disp=11; ok=1; break;		// blue candle on

		case 1112:	disp=10; ok=1; break;		// tree
		case 1114:	disp=10; ok=1; break;		// tree

		case 1154:      disp=8; ok=1; break;		// red flower
		case 1155:	disp=8; ok=1; break;		// small green plant
		case 1184:	disp=8; ok=1; break;		// red flower

		case 1160:	disp=12; ok=1; break;		// marble pillar

		case 1162:      disp=11; ok=1; break;		// golden candle off

		case 1166:      disp=11; ok=1; break;		// blue candle off

		case 1186:	disp=24; ok=1; swap=1; break;	// street sign
		case 1190:	disp=24; ok=1; swap=1; break;	// street sign
		case 1194:	disp=0; ok=1; swap=2; break;	// street sign
		case 1196:	disp=0; ok=1; swap=2; break;	// street sign

		case 1234:
		case 1235:	disp=8; ok=1; break;		// purple flower
		case 1236:	disp=8; ok=1; break;		// small green plant
		case 1238:	disp=12; ok=1; break;		// tree
		case 1240:	disp=12; ok=1; break;		// tree

		case 1625:	disp=12; ok=1; break;		// titan helmet

		case 16510:					// fire in pot
		case 16511:					// fire in pot
		case 16512:					// fire in pot
		case 16513:					// fire in pot
		case 16514:	disp=8; ok=1; break;		// fire in pot
				
		case 16969:	disp=8; ok=1; break;		// trashcan
		

				
	}
*/


/* ===================================================================
   BIGVIEW: HUD composition for the 1280x960 screen
   ===================================================================

   The original HUD is one 800x608 sprite (nr 1): panels, a blue background
   and a diamond-shaped transparent hole (color key) the world shows through.
   Here it is taken apart once:
     hudmask: 0 = hole, 1 = blue background, 2 = panel pixel
     hudreg : which screen corner a panel pixel is pinned to
   Every frame the old HUD code draws into the 800x600 shud surface, then
   dd_hud_compose() copies the panel pixels (with whatever text/items were
   drawn on them) to their new place on the big screen. Anything drawn over
   the hole/background (e.g. the shop window) is copied centered.
*/

#define HUDW	800
#define HUDH	608

#define REG_NONE	0
#define REG_TOP		1	// top block, split between A (left) and B (right)
#define REG_C		3	// minimap, bottom left
#define REG_D		4	// compass, bottom center
#define REG_E		5	// buttons, bottom right

#define SPLIT_X		497	// chat panel's left border (columns 497/498 belong to both halves)

static unsigned char *hudmask=NULL,*hudreg=NULL;
static unsigned short *hudimg=NULL;
static unsigned short *hudbase=NULL;	// the HUD as drawn this frame, before any text/items (brightness applied)

static int is_bgcol(unsigned short v)
{
	return v!=0xF81F && (v>>11)==0 && ((v>>5)&63)<=10;
}

/* ---- clean HUD (hud_theme 2) ----------------------------------------------
 * Panels are not drawn from the old texture any more. The canvas only gets the
 * content (text, items, labels); panel fills and border lines go into a small
 * list of "vector" operations that the presenter draws at full window
 * resolution in 24 bit colour: fills under the canvas, lines on top.
 * For the panels copied from the old HUD picture, the picture is classified
 * once: panel area (becomes a fill), border lines (become crisp lines) and
 * everything else (labels, icons: copied as before).
 */
#define HC_NONE	0
#define HC_FILL	1
#define HC_KEEP	2
#define HC_LINE	3

static unsigned char *hudcls=NULL;
struct lseg { short a,b0,b1,t; };	// a = first row (h) / column (v) of the band, b0..b1 = extent, t = band thickness
static struct lseg *hseg=NULL,*vseg=NULL;
static int nhseg=0,nvseg=0;
struct frect { short x,y,w,h; };
static struct frect *frects=NULL;
static int nfrect=0;

static void rgb8(unsigned short v,int *r,int *g,int *b)
{
	*r=((v>>11)&31)*255/31; *g=((v>>5)&63)*255/63; *b=(v&31)*255/31;
}

static unsigned char *warmmap=NULL;

static int is_warm(int x,int y)
{
	if (x<0 || y<0 || x>=HUDW || y>=HUDH) return 0;
	return warmmap[x+y*HUDW];
}

static int frac_warm_row(int y,int x0,int x1)
{
	int x,n=0;
	for (x=x0; x<x1; x++) n+=is_warm(x,y);
	return n*100/(x1-x0);
}

static int frac_warm_col(int x,int y0,int y1)
{
	int y,n=0;
	for (y=y0; y<y1; y++) n+=is_warm(x,y);
	return n*100/(y1-y0);
}

static void hud_classify(void)
{
	int x,y,p,x0,x1,y0,y1,last,r,g,b,L,k;
	unsigned char *line;

	hudcls=calloc(HUDW*HUDH,1);
	line=calloc(HUDW*HUDH,1);
	warmmap=calloc(HUDW*HUDH,1);
	hseg=malloc(sizeof(struct lseg)*4096); vseg=malloc(sizeof(struct lseg)*4096);
	frects=malloc(sizeof(struct frect)*8192);
	if (!hudcls || !line || !warmmap || !hseg || !vseg || !frects) { free(line); free(hudcls); hudcls=NULL; return; }

	for (p=0; p<HUDW*HUDH; p++) {
		if (hudmask[p]!=2) continue;
		rgb8(hudimg[p],&r,&g,&b);
		warmmap[p]=(r>b+6 && r+g>40);
	}

	// border lines: long thin runs of gold (gaps of up to 2 pixels allowed)
	for (y=0; y<HUDH; y++) {
		for (x=0; x<HUDW; ) {
			if (!is_warm(x,y)) { x++; continue; }
			x0=x; last=x;
			while (x<HUDW && (is_warm(x,y) || x-last<=2)) { if (is_warm(x,y)) last=x; x++; }
			x1=last+1; x=x1;
			if (x1-x0<12) continue;
			if (frac_warm_row(y-2,x0,x1)<30 && frac_warm_row(y+2,x0,x1)<30)
				for (k=x0; k<x1; k++) line[k+y*HUDW]|=1;
		}
	}
	for (x=0; x<HUDW; x++) {
		for (y=0; y<HUDH; ) {
			if (!is_warm(x,y)) { y++; continue; }
			y0=y; last=y;
			while (y<HUDH && (is_warm(x,y) || y-last<=2)) { if (is_warm(x,y)) last=y; y++; }
			y1=last+1; y=y1;
			if (y1-y0<12) continue;
			if (frac_warm_col(x-2,y0,y1)<30 && frac_warm_col(x+2,y0,y1)<30)
				for (k=y0; k<y1; k++) line[x+k*HUDW]|=2;
		}
	}

	// classes
	for (p=0; p<HUDW*HUDH; p++) {
		if (hudmask[p]!=2) continue;
		if (line[p]) { hudcls[p]=HC_LINE; continue; }
		rgb8(hudimg[p],&r,&g,&b);
		L=(30*r+59*g+11*b)/100;
		if (abs(r-g)<=10 && b>=r-4 && b<=r+16 && L<60) hudcls[p]=HC_FILL;	// grey panel texture
		else hudcls[p]=HC_KEEP;							// labels, icons
		if (hudcls[p]==HC_KEEP && p%HUDW>=300 && p%HUDW<374 && p/HUDW<212) hudcls[p]=HC_FILL;	// equipment labels: drawn as text
	}

	// line segments: one per band of adjacent line rows / columns
	for (y=0; y<HUDH; y++) {
		for (x=0; x<HUDW; ) {
			if (!(line[x+y*HUDW]&1) || (y>0 && (line[x+(y-1)*HUDW]&1))) { x++; continue; }
			x0=x;
			while (x<HUDW && (line[x+y*HUDW]&1) && !(y>0 && (line[x+(y-1)*HUDW]&1))) x++;
			for (k=1; y+k<HUDH && (line[x0+(y+k)*HUDW]&1); k++) ;
			if (nhseg<4096) { hseg[nhseg].a=y; hseg[nhseg].b0=x0; hseg[nhseg].b1=x; hseg[nhseg].t=k; nhseg++; }
		}
	}
	for (x=0; x<HUDW; x++) {
		for (y=0; y<HUDH; ) {
			if (!(line[x+y*HUDW]&2) || (x>0 && (line[x-1+y*HUDW]&2))) { y++; continue; }
			y0=y;
			while (y<HUDH && (line[x+y*HUDW]&2) && !(x>0 && (line[x-1+y*HUDW]&2))) y++;
			for (k=1; x+k<HUDW && (line[x+k+y0*HUDW]&2); k++) ;
			if (nvseg<4096) { vseg[nvseg].a=x; vseg[nvseg].b0=y0; vseg[nvseg].b1=y; vseg[nvseg].t=k; nvseg++; }
		}
	}

	// panel area as rectangles: row runs, merged downwards while the span is the same
	for (y=0; y<HUDH; y++) {
		for (x=0; x<HUDW; ) {
			if (hudmask[x+y*HUDW]!=2) { x++; continue; }
			x0=x;
			while (x<HUDW && hudmask[x+y*HUDW]==2) x++;
			for (k=nfrect-1; k>=0; k--) {
				if (frects[k].y+frects[k].h<y) { k=-1; break; }
				if (frects[k].y+frects[k].h==y && frects[k].x==x0 && frects[k].w==x-x0) break;
			}
			if (k>=0) frects[k].h++;
			else if (nfrect<8192) { frects[nfrect].x=x0; frects[nfrect].y=y; frects[nfrect].w=x-x0; frects[nfrect].h=1; nfrect++; }
		}
	}
	free(line);
}

/* exact border lines of the three old-HUD panels used every frame (legacy
   coordinates; type 1 = horizontal: a=row, b0..b1 = columns; type 2 = vertical).
   The detected lines are good enough for the rarely seen shop window, but
   these panels get the precise grid. */
static const short fixed_lines[][5]={
	// gold buttons (219,176 83x84)
	{1,176,218,303,2},{1,203,218,303,2},{1,231,218,303,2},{1,258,218,248,2},
	{2,218,176,260,2},{2,246,176,260,2},{2,274,176,233,2},{2,301,176,233,2},
	// equipment (300,0 74x212): 2 x 6 slots of 35
	{1,0,301,373,2},{1,35,301,373,2},{1,70,301,373,2},{1,105,301,373,2},{1,140,301,373,2},{1,175,301,373,2},{1,210,301,373,2},
	{2,301,0,212,2},{2,336,0,212,2},{2,371,0,212,2},
	// character / look panel (372,0 128x204)
	{1,0,371,499,2},{1,126,371,499,1},{1,133,371,499,1},{1,140,371,499,2},{1,147,371,499,1},{1,166,371,499,1},{1,185,371,499,2},{1,199,371,499,2},
	{2,497,0,201,2},{2,410,185,201,1},
};
#define NFIXED	((int)(sizeof(fixed_lines)/sizeof(fixed_lines[0])))
#define IN_FIXED(x,y)	(((x)>=217 && (x)<304 && (y)>=176 && (y)<262) || ((x)>=300 && (x)<500 && (y)<214))

/* the vector list, rebuilt every frame together with the canvas */
#define MAXVOP	8192
static struct hud_vop vops[MAXVOP];
static int nvop=0;

static void vadd(int type,int x,int y,int w,int h,unsigned int rgb)
{
	if (nvop>=MAXVOP || w<=0 || h<=0) return;
	vops[nvop].type=type; vops[nvop].x=x; vops[nvop].y=y; vops[nvop].w=w; vops[nvop].h=h; vops[nvop].rgb=rgb;
	nvop++;
}

int dd_hud_vops(struct hud_vop **p)
{
	*p=vops;
	return nvop;
}

void dd_hud_vfill(int x,int y,int w,int h,unsigned int rgb)
{
	vadd(VOP_FILL,x,y,w,h,rgb);
}

void dd_hud_vtri(int x,int y,int w,int h,int down)
{
	vadd(down ? VOP_TRIDOWN : VOP_TRIUP,x,y,w,h,HUD_RGB_LINE);
}

// is canvas point x,y on a panel fill?
// take the lines and arrows of other panels out of a rectangle (a tooltip
// drawn on top of them); lines crossing it are split around it
void dd_hud_vclip(int rx,int ry,int rw,int rh)
{
	int n,cnt=nvop;
	struct hud_vop v;

	for (n=0; n<nhtext; n++) {	// text of other panels under it
		int i;
		if (htexts[n].y+9<=ry || htexts[n].y>=ry+rh) continue;
		for (i=0; i<htexts[n].len; i++)
			if (htexts[n].x+i*6+6>rx && htexts[n].x+i*6<rx+rw) htextpool[htexts[n].off+i]=' ';
	}
	for (n=0; n<cnt; n++) {
		v=vops[n];
		if (v.type==VOP_FILL) continue;
		if (v.x>=rx+rw || v.y>=ry+rh || v.x+v.w<=rx || v.y+v.h<=ry) continue;	// outside
		vops[n].type=255;	// remove (no type draws it), then add the pieces outside
		if (v.type==VOP_HLINE) {
			if (v.x<rx) vadd(VOP_HLINE,v.x,v.y,rx-v.x,v.h,v.rgb);
			if (v.x+v.w>rx+rw) vadd(VOP_HLINE,rx+rw,v.y,v.x+v.w-(rx+rw),v.h,v.rgb);
		} else if (v.type==VOP_VLINE) {
			if (v.y<ry) vadd(VOP_VLINE,v.x,v.y,v.w,ry-v.y,v.rgb);
			if (v.y+v.h>ry+rh) vadd(VOP_VLINE,v.x,ry+rh,v.w,v.y+v.h-(ry+rh),v.rgb);
		}
	}
}

int dd_hud_vhit(int x,int y)
{
	int n;
	for (n=0; n<nvop; n++)
		if (vops[n].type==VOP_FILL && x>=vops[n].x && y>=vops[n].y && x<vops[n].x+vops[n].w && y<vops[n].y+vops[n].h) return 1;
	return 0;
}

static int hud_prepare(void)
{
	int x,y,p,q,head,tail,nx,ny,k;
	int *queue;
	static const int dx[4]={1,-1,0,0},dy[4]={0,0,1,-1};

	if (hudmask) return 1;

	if (!sprtab[1].image) dd_load_sprite(1);
	if (!sprtab[1].image || sprtab[1].xs*TILE!=HUDW || sprtab[1].ys*TILE<HUDH-8) return 0;
	// own copy: the sprite cache may free sprite images at any time
	hudimg=malloc(HUDW*HUDH*sizeof(unsigned short));
	if (!hudimg) return 0;
	memcpy(hudimg,sprtab[1].image,HUDW*HUDH*sizeof(unsigned short));

	hudmask=calloc(HUDW*HUDH,1);
	hudreg=calloc(HUDW*HUDH,1);
	queue=malloc(HUDW*HUDH*sizeof(int));
	if (!hudmask || !hudreg || !queue) { free(queue); return 0; }

	// panel by default, hole where the sprite is transparent
	for (p=0; p<HUDW*HUDH; p++) hudmask[p]=(hudimg[p]==0xF81F) ? 0 : 2;

	// background = blue pixels connected to the hole
	head=tail=0;
	for (y=0; y<HUDH; y++) for (x=0; x<HUDW; x++) {
		p=x+y*HUDW;
		if (hudmask[p]!=2 || !is_bgcol(hudimg[p])) continue;
		for (k=0; k<4; k++) {
			nx=x+dx[k]; ny=y+dy[k];
			if (nx<0 || ny<0 || nx>=HUDW || ny>=HUDH) continue;
			if (hudmask[nx+ny*HUDW]==0) { hudmask[p]=1; queue[tail++]=p; break; }
		}
	}
	while (head<tail) {
		p=queue[head++]; x=p%HUDW; y=p/HUDW;
		for (k=0; k<4; k++) {
			nx=x+dx[k]; ny=y+dy[k];
			if (nx<0 || ny<0 || nx>=HUDW || ny>=HUDH) continue;
			q=nx+ny*HUDW;
			if (hudmask[q]==2 && is_bgcol(hudimg[q])) { hudmask[q]=1; queue[tail++]=q; }
		}
	}

	// the top block: panel pixels connected to the top left corner
	head=tail=0;
	if (hudmask[5+5*HUDW]==2) { hudreg[5+5*HUDW]=REG_TOP; queue[tail++]=5+5*HUDW; }
	while (head<tail) {
		p=queue[head++]; x=p%HUDW; y=p/HUDW;
		for (k=0; k<4; k++) {
			nx=x+dx[k]; ny=y+dy[k];
			if (nx<0 || ny<0 || nx>=HUDW || ny>=HUDH) continue;
			q=nx+ny*HUDW;
			if (hudmask[q]==2 && !hudreg[q]) { hudreg[q]=REG_TOP; queue[tail++]=q; }
		}
	}
	free(queue);

	// the other panels by area; the small diamond markers stay REG_NONE
	for (y=0; y<HUDH; y++) for (x=0; x<HUDW; x++) {
		p=x+y*HUDW;
		if (hudmask[p]!=2 || hudreg[p]) continue;
		if (x<200 && y>=440) hudreg[p]=REG_C;
		else if (x>=260 && x<345 && y>=550) hudreg[p]=REG_D;
		else if (x>=600 && y>=490) hudreg[p]=REG_E;
	}
	if (hud_theme==2) hud_classify();

	return 1;
}

// screen offset of each HUD part (legacy -> big screen)
#define OFF_RX	(SCREEN_W-LEGACY_W)
#define OFF_BY	(SCREEN_H-LEGACY_H)
#define OFF_CX	((SCREEN_W-LEGACY_W)/2)
#define OFF_CY	((SCREEN_H-LEGACY_H)/2)

#define LOOK_BOTTOM	201	// look panel's bottom border; below it columns 497/498 are only the chat's edge

static int part_of(int reg,int x,int y,int which)
{
	// which: 1=A (top left) 2=B (top right) 3=C 4=D 5=E
	switch (which) {
		case 1: return reg==REG_TOP && (x<SPLIT_X || (x<=SPLIT_X+1 && y<=LOOK_BOTTOM));
		case 2: return reg==REG_TOP && x>=SPLIT_X;
		default: return reg==which;
	}
}

static void part_off(int which,int *ox,int *oy)
{
	switch (which) {
		case 1: *ox=0; *oy=0; break;
		case 2: *ox=OFF_RX; *oy=0; break;
		case 3: *ox=0; *oy=OFF_BY; break;
		case 4: *ox=OFF_CX; *oy=OFF_BY; break;
		case 5: *ox=OFF_RX; *oy=OFF_BY; break;
		default: *ox=OFF_CX; *oy=OFF_CY; break;	// overlays drawn over the hole
	}
}

/* -------------------------------------------------------------------
   HUD canvas (v2): the new HUD is drawn in "HUD units" on a canvas the size
   of the window divided by the HUD scale (1.5). The presenter scales it up
   and lays it over the world. Color key = transparent.
   ------------------------------------------------------------------- */
static DDSURF shc;
int hud_cw=0,hud_ch=0;

int dd_hud_canvas(int w,int h)
{
	if (w<200) w=200;
	if (h<150) h=150;
	if (shc.bits && shc.w==w && shc.h==h) return 1;
	free(shc.bits);
	shc.bits=NULL;
	if (!alloc_surface(&shc,w,h)) return 0;
	hud_cw=w; hud_ch=h;
	return 1;
}

unsigned short *dd_hud_canvas_bits(int *w,int *h,int *pitch)
{
	*w=shc.w; *h=shc.h; *pitch=shc.pitch;
	return shc.bits;
}

// switch drawing between the big screen (0), the legacy HUD surface (1)
// and the HUD canvas (2)
void dd_target(int hud)
{
	hud_active=hud;
	if (hud==2) {
		sur2=&shc;
		MAXX=shc.pitch; MAXY=shc.h;
		cur_w=shc.w; cur_h=shc.h;
	} else if (hud) {
		sur2=&shud;
		MAXX=LEGACY_W; MAXY=LEGACY_H;
		cur_w=LEGACY_W; cur_h=LEGACY_H;
	} else {
		sur2=&s2;
		MAXX=SCREEN_W; MAXY=SCREEN_H;
		cur_w=SCREEN_W; cur_h=SCREEN_H;
	}
}

// start a HUD frame: clear the legacy surface to the color key
void dd_hud_begin(void)
{
	int n;
	unsigned short *p=shud.bits;

	dd_target(1);
	for (n=0; n<shud.pitch*shud.h; n++) p[n]=0xF81F;
}

// call right after the HUD picture itself has been drawn: remembers it, so
// anything drawn afterwards over the background/hole can be told apart
void dd_hud_snapshot(void)
{
	int y;

	if (!hudbase) hudbase=malloc(LEGACY_W*LEGACY_H*sizeof(unsigned short));
	if (!hudbase) return;
	for (y=0; y<LEGACY_H; y++) memcpy(hudbase+y*LEGACY_W,shud.bits+y*shud.pitch,LEGACY_W*sizeof(unsigned short));
}

// copy the HUD to the big screen
void dd_hud_compose(void)
{
	int x,y,p,w,ox,oy,sx,sy;
	unsigned short v,*src=shud.bits,*dst=s2.bits;

	if (!hud_prepare()) return;

	for (y=0; y<LEGACY_H; y++) {
		for (x=0; x<LEGACY_W; x++) {
			p=x+y*HUDW;
			v=src[x+y*shud.pitch];
			if (v==0xF81F) continue;

			if (hudmask[p]==2) {
				for (w=1; w<=5; w++) {
					if (!part_of(hudreg[p],x,y,w)) continue;
					part_off(w,&ox,&oy);
					sx=x+ox; sy=y+oy;
					if (sx>=0 && sy>=0 && sx<SCREEN_W && sy<SCREEN_H) dst[sx+sy*s2.pitch]=v;
				}
			} else if (hudbase && v!=hudbase[x+y*LEGACY_W]) {	// something drawn over the hole/background
				sx=x+OFF_CX; sy=y+OFF_CY;
				if (sx>=0 && sy>=0 && sx<SCREEN_W && sy<SCREEN_H) dst[sx+sy*s2.pitch]=v;
			}
		}
	}
}

// translate a big screen position to legacy HUD coordinates.
// returns 1 if the position is on a HUD panel (or an overlay like the shop
// when overlay!=0), 0 if it is on the world.
int hud_from_screen(int sx,int sy,int *lx,int *ly,int overlay)
{
	int w,ox,oy,x,y,p;

	if (!hud_prepare()) { *lx=sx; *ly=sy; return 0; }

	for (w=1; w<=5; w++) {
		part_off(w,&ox,&oy);
		x=sx-ox; y=sy-oy;
		if (x<0 || y<0 || x>=LEGACY_W || y>=LEGACY_H) continue;
		p=x+y*HUDW;
		if (hudmask[p]==2 && part_of(hudreg[p],x,y,w)) { *lx=x; *ly=y; return 1; }
	}
	if (overlay) {
		x=sx-OFF_CX; y=sy-OFF_CY;
		if (x>=0 && y>=0 && x<LEGACY_W && y<LEGACY_H) {
			p=x+y*HUDW;
			if (hudmask[p]!=2 && hudbase && shud.bits[x+y*shud.pitch]!=0xF81F && shud.bits[x+y*shud.pitch]!=hudbase[x+y*LEGACY_W]) {
				*lx=x; *ly=y; return 1;
			}
		}
	}
	*lx=sx; *ly=sy;
	return 0;
}

// fill the big screen with the HUD's blue background texture (mirrored tiles)
void dd_fill_background(void)
{
	int x,y,tx,ty;
	unsigned short *dst=s2.bits,*src;
	const int PX=132,PY=504,PS=80;	// an 80x80 patch of pure background
	int stride;

	if (!hud_prepare()) { memset(dst,0,(size_t)s2.pitch*s2.h*2); return; }

	// use last frame's HUD (brightness applied) if we have it
	if (hudbase) { src=hudbase; stride=LEGACY_W; }
	else { src=hudimg; stride=HUDW; }

	for (y=0; y<SCREEN_H; y++) {
		ty=y%(PS*2); if (ty>=PS) ty=PS*2-1-ty;
		for (x=0; x<SCREEN_W; x++) {
			tx=x%(PS*2); if (tx>=PS) tx=PS*2-1-tx;
			dst[x+y*s2.pitch]=src[(PX+tx)+(PY+ty)*stride];
		}
	}
}

// fixed view edge: everything outside the diamond (center cx,cy, half sizes
// hw,hh) is covered with the background again. Like the hole in the old HUD
// picture, this keeps the edge still while the world scrolls under it.
void dd_mask_view(int cx,int cy,int hw,int hh)
{
	int x,y,ty,tx,w,x0,x1;
	unsigned short *dst=s2.bits,*src;
	const int PX=132,PY=504,PS=80;
	int stride;

	if (!hud_prepare()) return;
	if (hudbase) { src=hudbase; stride=LEGACY_W; }
	else { src=hudimg; stride=HUDW; }

	for (y=0; y<SCREEN_H; y++) {
		ty=y%(PS*2); if (ty>=PS) ty=PS*2-1-ty;
		w=hw-(abs(y-cy)*hw)/hh;		// half width of the diamond on this row
		if (w<0) { x0=x1=SCREEN_W; }	// whole row outside
		else { x0=cx-w; x1=cx+w; }
		for (x=0; x<SCREEN_W; x++) {
			if (x>=x0 && x<x1) { x=x1-1; continue; }
			tx=x%(PS*2); if (tx>=PS) tx=PS*2-1-tx;
			dst[x+y*s2.pitch]=src[(PX+tx)+(PY+ty)*stride];
		}
	}
}

// draw one of the HUD's small diamond markers centered at sx,sy (big screen)
void dd_draw_marker(int cx,int cy)
{
	const int MX=150,MY=308,MW=29,MH=14;	// marker graphic in the HUD sprite
	int x,y,sx,sy,p;

	if (!hud_prepare()) return;

	for (y=0; y<MH; y++) for (x=0; x<MW; x++) {
		p=(MX+x)+(MY+y)*HUDW;
		if (hudmask[p]!=2 || hudreg[p]!=REG_NONE) continue;
		sx=cx-MW/2+x; sy=cy-MH/2+y;
		if (sx>=0 && sy>=0 && sx<SCREEN_W && sy<SCREEN_H) s2.bits[sx+sy*s2.pitch]=hudimg[p];
	}
}


/* ---- HUD canvas drawing helpers (all in HUD units, on the canvas) ---- */

void dd_canvas_clear(void)
{
	int n;
	nvop=0;
	nhtext=0; htextpos=0;
	for (n=0; n<shc.pitch*shc.h; n++) shc.bits[n]=0xF81F;
}

static void cput(int x,int y,unsigned short v)
{
	if (x<0 || y<0 || x>=shc.w || y>=shc.h || v==0xF81F) return;
	shc.bits[x+y*shc.pitch]=v;
}

// red panel texture (taken from the inside of the original chat panel)
void dd_hud_red(int x0,int y0,int w,int h)
{
	int x,y;
	if (hud_theme==2) { vadd(VOP_FILL,x0,y0,w,h,HUD_RGB_PANEL); return; }
	if (!hud_prepare()) return;
	for (y=0; y<h; y++) for (x=0; x<w; x++)
		cput(x0+x,y0+y,hudimg[(520+(x%260))+(12+(y%200))*HUDW]);
}

// 2 pixel gold border lines, pattern taken from the original borders
void dd_hud_hline(int x0,int y,int w)
{
	int i;
	if (hud_theme==2) { vadd(VOP_HLINE,x0,y,w,2,HUD_RGB_LINE); return; }
	if (!hud_prepare()) return;
	for (i=0; i<w; i++) {
		cput(x0+i,y,hudimg[(640+(i%150))+239*HUDW]);
		cput(x0+i,y+1,hudimg[(640+(i%150))+240*HUDW]);
	}
}

void dd_hud_vline(int x,int y0,int h)
{
	int i;
	if (hud_theme==2) { vadd(VOP_VLINE,x,y0,2,h,HUD_RGB_LINE); return; }
	if (!hud_prepare()) return;
	for (i=0; i<h; i++) {
		cput(x,y0+i,hudimg[497+(10+(i%180))*HUDW]);
		cput(x+1,y0+i,hudimg[498+(10+(i%180))*HUDW]);
	}
}

void dd_hud_panel(int x,int y,int w,int h)
{
	dd_hud_red(x,y,w,h);
	dd_hud_hline(x,y,w);
	dd_hud_hline(x,y+h-2,w);
	dd_hud_vline(x,y,h);
	dd_hud_vline(x+w-2,y,h);
}

void dd_hud_fill(int x0,int y0,int w,int h,unsigned short col)
{
	int x,y;
	for (y=0; y<h; y++) for (x=0; x<w; x++) cput(x0+x,y0+y,col);
}

// copy a piece of the legacy 800x600 HUD (as drawn this frame) onto the
// canvas: its panel pixels plus anything drawn over hole/background there
void dd_hud_from_legacy(int lx,int ly,int w,int h,int cx,int cy)
{
	int x,y,p;
	unsigned short v;

	if (!hud_prepare()) return;
	if (hud_theme==2 && hudcls) {
		int n,a0,a1,b0,b1,dx=cx-lx,dy=cy-ly;
		// panel fills, clipped to the piece; the three panels with fixed
		// lines are clipped to their frame, so no fill sticks out past it
		int fx0=lx,fy0=ly,fx1=lx+w,fy1=ly+h;
		if (lx==219 && ly==176) { fx0=219; fy0=176; fx1=303; fy1=260; }	// gold buttons
		else if (lx==300 && ly==0) { fx0=301; fy0=0; fx1=373; fy1=212; }	// equipment
		else if (lx==372 && ly==0) { fx0=372; fy0=0; fx1=499; fy1=201; }	// character / look panel
		for (n=0; n<nfrect; n++) {
			a0=max(frects[n].x,fx0); a1=min(frects[n].x+frects[n].w,fx1);
			b0=max(frects[n].y,fy0); b1=min(frects[n].y+frects[n].h,fy1);
			if (a0<a1 && b0<b1) vadd(VOP_FILL,a0+dx,b0+dy,a1-a0,b1-b0,HUD_RGB_PANEL);
		}
		for (n=0; n<nhseg; n++) {
			if (hseg[n].a<ly || hseg[n].a>=ly+h || IN_FIXED(hseg[n].b0,hseg[n].a)) continue;
			a0=max(hseg[n].b0,lx); a1=min(hseg[n].b1,lx+w);
			if (a0<a1) vadd(VOP_HLINE,a0+dx,hseg[n].a+dy,a1-a0,hseg[n].t,HUD_RGB_LINE);
		}
		for (n=0; n<nvseg; n++) {
			if (vseg[n].a<lx || vseg[n].a>=lx+w || IN_FIXED(vseg[n].a,vseg[n].b0)) continue;
			b0=max(vseg[n].b0,ly); b1=min(vseg[n].b1,ly+h);
			if (b0<b1) vadd(VOP_VLINE,vseg[n].a+dx,b0+dy,vseg[n].t,b1-b0,HUD_RGB_LINE);
		}
		for (n=0; n<NFIXED; n++) {
			const short *f=fixed_lines[n];
			if (f[0]==1) {
				if (f[1]<ly || f[1]>=ly+h) continue;
				a0=max(f[2],lx-1); a1=min(f[3],lx+w);	// may start on the neighbour's border line
				if (a0<a1) vadd(VOP_HLINE,a0+dx,f[1]+dy,a1-a0,f[4],HUD_RGB_LINE);
			} else {
				if (f[1]<lx || f[1]>=lx+w) continue;
				b0=max(f[2],ly); b1=min(f[3],ly+h);
				if (b0<b1) vadd(VOP_VLINE,f[1]+dx,b0+dy,f[4],b1-b0,HUD_RGB_LINE);
			}
		}
	}
	for (y=0; y<h; y++) {
		if (ly+y<0 || ly+y>=LEGACY_H) continue;
		for (x=0; x<w; x++) {
			if (lx+x<0 || lx+x>=LEGACY_W) continue;
			p=(lx+x)+(ly+y)*HUDW;
			v=shud.bits[(lx+x)+(ly+y)*shud.pitch];
			if (v==0xF81F) continue;
			if (hudbase && v!=hudbase[(lx+x)+(ly+y)*LEGACY_W]) {	// drawn this frame
				if (hud_theme==2 && lx==300 && x<3) continue;		// old backpack scroll bar reaches in here
				cput(cx+x,cy+y,v);
			}
			else if (hud_theme==2 && hudcls) { if (hudcls[p]==HC_KEEP) cput(cx+x,cy+y,v); }
			else if (hudmask[p]==2) cput(cx+x,cy+y,v);
		}
	}
}

// minimap: (2*n x 2*n tiles) from the 1024x1024 map memory, zoom pixels per tile
void dd_hud_minimap(unsigned short *src,int xo,int yo,int x0,int y0,int n,int zoom)
{
	int x,y,zx,zy;
	unsigned short v;

	for (y=0; y<n; y++) for (x=0; x<n; x++) {
		v=src[(y+yo)*1024+x+xo];
		for (zy=0; zy<zoom; zy++) for (zx=0; zx<zoom; zx++) cput(x0+x*zoom+zx,y0+y*zoom+zy,v ? v : 0x0001);
	}
}
