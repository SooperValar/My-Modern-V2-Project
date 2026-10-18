/*
 * pngdec.c - minimal PNG reader for the Astonia v2 client port.
 *
 * Replaces the old Borland-built libpng. Supports what the client's sprite
 * loader accepts: 8 bit-per-channel RGB and RGBA images, interlaced or not.
 * (Gray and palette images are expanded to RGB/RGBA for robustness.)
 *
 * Reads from the FILE's current position until IEND, so it works both on
 * single gfx\NNNNN.png files and inside pnglib.dat.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "zlib.h"
#include "pngdec.h"

static unsigned int be32(const unsigned char *p)
{
	return ((unsigned)p[0]<<24)|((unsigned)p[1]<<16)|((unsigned)p[2]<<8)|p[3];
}

static int paeth(int a,int b,int c)
{
	int p=a+b-c,pa=abs(p-a),pb=abs(p-b),pc=abs(p-c);

	if (pa<=pb && pa<=pc) return a;
	if (pb<=pc) return b;
	return c;
}

/* unfilter one (sub)image in place; returns 0 on error */
static int unfilter(unsigned char *data,int w,int h,int bpp)
{
	int x,y,stride=w*bpp,f;
	unsigned char *row,*prev=NULL,*src=data,*dst=data;

	for (y=0; y<h; y++) {
		f=*src++;
		row=dst;
		memmove(row,src,stride);	/* strip filter byte (dst trails src) */
		src+=stride;

		for (x=0; x<stride; x++) {
			int a=x>=bpp ? row[x-bpp] : 0;
			int b=prev ? prev[x] : 0;
			int c=(prev && x>=bpp) ? prev[x-bpp] : 0;

			switch (f) {
				case 0: break;
				case 1: row[x]=(unsigned char)(row[x]+a); break;
				case 2: row[x]=(unsigned char)(row[x]+b); break;
				case 3: row[x]=(unsigned char)(row[x]+((a+b)>>1)); break;
				case 4: row[x]=(unsigned char)(row[x]+paeth(a,b,c)); break;
				default: return 0;
			}
		}
		prev=row;
		dst+=stride;
	}
	return 1;
}

unsigned char *png_decode(FILE *fp,int *xs,int *ys,int *channels)
{
	static const unsigned char sig[8]={137,80,78,71,13,10,26,10};
	unsigned char hdr[8],crc[4],ihdr[13];
	unsigned char *idat=NULL,*raw=NULL,*img=NULL,*out=NULL;
	unsigned char pal[256*3],trns[256];
	size_t idatlen=0,idatcap=0,rawlen,need;
	int w=0,h=0,depth=0,ctype=0,interlace=0,bpp=0,palcnt=0,trnscnt=0,got_ihdr=0,outch;
	unsigned int len;
	z_stream zs;
	int r;

	memset(trns,255,sizeof(trns));

	if (fread(hdr,1,8,fp)!=8 || memcmp(hdr,sig,8)) return NULL;

	for (;;) {
		if (fread(hdr,1,8,fp)!=8) goto fail;
		len=be32(hdr);
		if (len>0x7fffffff) goto fail;

		if (!memcmp(hdr+4,"IHDR",4)) {
			if (len!=13 || fread(ihdr,1,13,fp)!=13) goto fail;
			w=(int)be32(ihdr);
			h=(int)be32(ihdr+4);
			depth=ihdr[8];
			ctype=ihdr[9];
			interlace=ihdr[12];
			got_ihdr=1;
		} else if (!memcmp(hdr+4,"PLTE",4)) {
			if (len>768 || fread(pal,1,len,fp)!=len) goto fail;
			palcnt=len/3;
		} else if (!memcmp(hdr+4,"tRNS",4) && ctype==3) {
			if (len>256 || fread(trns,1,len,fp)!=len) goto fail;
			trnscnt=len;
		} else if (!memcmp(hdr+4,"IDAT",4)) {
			if (idatlen+len>idatcap) {
				unsigned char *p;
				idatcap=(idatlen+len)*2;
				p=realloc(idat,idatcap);
				if (!p) goto fail;
				idat=p;
			}
			if (fread(idat+idatlen,1,len,fp)!=len) goto fail;
			idatlen+=len;
		} else if (!memcmp(hdr+4,"IEND",4)) {
			fread(crc,1,4,fp);
			break;
		} else {
			if (fseek(fp,len,SEEK_CUR)) goto fail;
		}
		if (fread(crc,1,4,fp)!=4) goto fail;
	}

	if (!got_ihdr || w<=0 || h<=0 || w>16384 || h>16384) goto fail;
	if (depth!=8) goto fail;	/* client only ever accepted 8 bit */

	switch (ctype) {
		case 0: bpp=1; break;	/* gray */
		case 2: bpp=3; break;	/* rgb */
		case 3: bpp=1; break;	/* palette */
		case 4: bpp=2; break;	/* gray+alpha */
		case 6: bpp=4; break;	/* rgba */
		default: goto fail;
	}

	/* decompressed size (with filter bytes) */
	if (!interlace) rawlen=(size_t)h*(w*bpp+1);
	else {
		static const int xo[7]={0,4,0,2,0,1,0},yo[7]={0,0,4,0,2,0,1},xs_[7]={8,8,4,4,2,2,1},ys_[7]={8,8,8,4,4,2,2};
		int p,pw,ph;
		rawlen=0;
		for (p=0; p<7; p++) {
			pw=(w-xo[p]+xs_[p]-1)/xs_[p];
			ph=(h-yo[p]+ys_[p]-1)/ys_[p];
			if (pw>0 && ph>0) rawlen+=(size_t)ph*(pw*bpp+1);
		}
	}

	raw=malloc(rawlen);
	if (!raw) goto fail;

	memset(&zs,0,sizeof(zs));
	if (inflateInit(&zs)!=Z_OK) goto fail;
	zs.next_in=idat;
	zs.avail_in=(unsigned)idatlen;
	zs.next_out=raw;
	zs.avail_out=(unsigned)rawlen;
	r=inflate(&zs,Z_FINISH);
	need=rawlen-zs.avail_out;
	inflateEnd(&zs);
	if (r<0 || need!=rawlen) goto fail;

	free(idat); idat=NULL;

	img=malloc((size_t)w*h*bpp);
	if (!img) goto fail;

	if (!interlace) {
		if (!unfilter(raw,w,h,bpp)) goto fail;
		memcpy(img,raw,(size_t)w*h*bpp);
	} else {
		static const int xo[7]={0,4,0,2,0,1,0},yo[7]={0,0,4,0,2,0,1},xs_[7]={8,8,4,4,2,2,1},ys_[7]={8,8,8,4,4,2,2};
		int p,pw,ph,x,y;
		unsigned char *src=raw;

		for (p=0; p<7; p++) {
			pw=(w-xo[p]+xs_[p]-1)/xs_[p];
			ph=(h-yo[p]+ys_[p]-1)/ys_[p];
			if (pw<=0 || ph<=0) continue;
			if (!unfilter(src,pw,ph,bpp)) goto fail;
			for (y=0; y<ph; y++)
				for (x=0; x<pw; x++)
					memcpy(img+((size_t)(yo[p]+y*ys_[p])*w+xo[p]+x*xs_[p])*bpp,src+((size_t)y*pw+x)*bpp,bpp);
			src+=(size_t)ph*(pw*bpp+1);
		}
	}

	free(raw); raw=NULL;

	/* expand to RGB / RGBA */
	if (ctype==2 || ctype==6) {
		out=img;
		outch=bpp;
	} else {
		int i,n=w*h,alpha=(ctype==4 || (ctype==3 && trnscnt));
		outch=alpha ? 4 : 3;
		out=malloc((size_t)n*outch);
		if (!out) goto fail;
		for (i=0; i<n; i++) {
			unsigned char *d=out+(size_t)i*outch;
			if (ctype==0) { d[0]=d[1]=d[2]=img[i]; }
			else if (ctype==4) { d[0]=d[1]=d[2]=img[i*2]; d[3]=img[i*2+1]; }
			else {
				int idx=img[i];
				if (idx>=palcnt) idx=0;
				d[0]=pal[idx*3]; d[1]=pal[idx*3+1]; d[2]=pal[idx*3+2];
				if (alpha) d[3]=trns[idx];
			}
		}
		free(img);
		img=NULL;
	}

	*xs=w;
	*ys=h;
	*channels=outch;
	return out;

fail:
	free(idat);
	free(raw);
	free(img);
	return NULL;
}
