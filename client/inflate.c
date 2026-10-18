/*
 * inflate.c - small, self-contained zlib/deflate decompressor.
 *
 * Written for the Astonia v2 client port as a drop-in replacement for the
 * subset of zlib the client uses. Huffman decoding follows the canonical
 * approach described in RFC 1951 (same scheme as Mark Adler's "puff").
 *
 * Streaming model: all input handed to inflate() is buffered internally.
 * Blocks are decoded one at a time; if a block is cut off by the end of the
 * available input, it is decoded again from its start on the next call once
 * more data has arrived. The last 32K of output are kept as the history
 * window for back-references across calls.
 */
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include "zlib.h"

#define MAXBITS   15
#define MAXLCODES 286
#define MAXDCODES 30
#define FIXLCODES 288
#define WSIZE     32768

#define NEED_INPUT 1
#define BAD_DATA   2

struct huffman {
	short count[MAXBITS+1];
	short symbol[FIXLCODES];
};

struct inf_state {
	int raw;		/* 1: no zlib header */
	int need_header;
	int done;		/* final block decoded */

	unsigned char *in;	/* buffered compressed input */
	size_t inlen,incap;
	size_t bitpos;		/* bit offset of the next undecoded block */

	unsigned char hist[WSIZE];
	size_t histlen;

	unsigned char *pend;	/* decoded data not yet handed out */
	size_t pendlen,pendpos,pendcap;

	unsigned char *blk;	/* scratch for the block being decoded */
	size_t blklen,blkcap;

	/* bit reader */
	size_t incnt;
	unsigned long bitbuf;
	int bitcnt;
	jmp_buf env;
};

static int grow(unsigned char **buf,size_t *cap,size_t need)
{
	size_t ncap;
	unsigned char *p;

	if (need<=*cap) return 1;
	ncap=*cap ? *cap : 4096;
	while (ncap<need) ncap*=2;
	p=realloc(*buf,ncap);
	if (!p) return 0;
	*buf=p;
	*cap=ncap;
	return 1;
}

static int bits(struct inf_state *s,int need)
{
	unsigned long val=s->bitbuf;

	while (s->bitcnt<need) {
		if (s->incnt>=s->inlen) longjmp(s->env,NEED_INPUT);
		val|=(unsigned long)s->in[s->incnt++]<<s->bitcnt;
		s->bitcnt+=8;
	}
	s->bitbuf=val>>need;
	s->bitcnt-=need;

	return (int)(val&((1UL<<need)-1));
}

static void put(struct inf_state *s,unsigned char c)
{
	if (s->blklen>=s->blkcap) {
		if (!grow(&s->blk,&s->blkcap,s->blklen+1)) longjmp(s->env,BAD_DATA);
	}
	s->blk[s->blklen++]=c;
}

static int decode(struct inf_state *s,const struct huffman *h)
{
	int len,code=0,first=0,count,index=0;

	for (len=1; len<=MAXBITS; len++) {
		code|=bits(s,1);
		count=h->count[len];
		if (code-count<first) return h->symbol[index+(code-first)];
		index+=count;
		first+=count;
		first<<=1;
		code<<=1;
	}
	return -10;
}

static int construct(struct huffman *h,const short *length,int n)
{
	int symbol,len,left;
	short offs[MAXBITS+1];

	for (len=0; len<=MAXBITS; len++) h->count[len]=0;
	for (symbol=0; symbol<n; symbol++) h->count[length[symbol]]++;
	if (h->count[0]==n) return 0;

	left=1;
	for (len=1; len<=MAXBITS; len++) {
		left<<=1;
		left-=h->count[len];
		if (left<0) return left;
	}

	offs[1]=0;
	for (len=1; len<MAXBITS; len++) offs[len+1]=offs[len]+h->count[len];
	for (symbol=0; symbol<n; symbol++)
		if (length[symbol]!=0) h->symbol[offs[length[symbol]]++]=(short)symbol;

	return left;
}

static const short lbase[29]={3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258};
static const short lext[29]={0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0};
static const short dbase[30]={1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577};
static const short dext[30]={0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13};

static int codes(struct inf_state *s,const struct huffman *lencode,const struct huffman *distcode)
{
	int symbol,len;
	size_t dist,n;

	for (;;) {
		symbol=decode(s,lencode);
		if (symbol<0) return -1;
		if (symbol<256) { put(s,(unsigned char)symbol); continue; }
		if (symbol==256) return 0;

		symbol-=257;
		if (symbol>=29) return -1;
		len=lbase[symbol]+bits(s,lext[symbol]);

		symbol=decode(s,distcode);
		if (symbol<0 || symbol>=30) return -1;
		dist=dbase[symbol]+bits(s,dext[symbol]);

		if (dist>s->blklen+s->histlen) return -1;	/* reaches before start of stream */

		while (len--) {
			if (dist<=s->blklen) n=s->blk[s->blklen-dist];
			else n=s->hist[s->histlen-(dist-s->blklen)];
			put(s,(unsigned char)n);
		}
	}
}

static struct huffman fixed_len,fixed_dist;
static int fixed_done=0;

static void build_fixed(void)
{
	short lengths[FIXLCODES];
	int symbol;

	for (symbol=0; symbol<144; symbol++) lengths[symbol]=8;
	for (; symbol<256; symbol++) lengths[symbol]=9;
	for (; symbol<280; symbol++) lengths[symbol]=7;
	for (; symbol<FIXLCODES; symbol++) lengths[symbol]=8;
	construct(&fixed_len,lengths,FIXLCODES);

	for (symbol=0; symbol<MAXDCODES; symbol++) lengths[symbol]=5;
	construct(&fixed_dist,lengths,MAXDCODES);

	fixed_done=1;
}

static int dynamic(struct inf_state *s)
{
	int nlen,ndist,ncode,index,err,symbol,len;
	short lengths[MAXLCODES+MAXDCODES];
	struct huffman lencode,distcode;
	static const short order[19]={16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15};

	nlen=bits(s,5)+257;
	ndist=bits(s,5)+1;
	ncode=bits(s,4)+4;
	if (nlen>MAXLCODES || ndist>MAXDCODES) return -1;

	for (index=0; index<ncode; index++) lengths[order[index]]=(short)bits(s,3);
	for (; index<19; index++) lengths[order[index]]=0;

	err=construct(&lencode,lengths,19);
	if (err!=0) return -1;

	index=0;
	while (index<nlen+ndist) {
		symbol=decode(s,&lencode);
		if (symbol<0) return -1;
		if (symbol<16) lengths[index++]=(short)symbol;
		else {
			len=0;
			if (symbol==16) {
				if (index==0) return -1;
				len=lengths[index-1];
				symbol=3+bits(s,2);
			} else if (symbol==17) symbol=3+bits(s,3);
			else symbol=11+bits(s,7);
			if (index+symbol>nlen+ndist) return -1;
			while (symbol--) lengths[index++]=(short)len;
		}
	}

	if (lengths[256]==0) return -1;

	err=construct(&lencode,lengths,nlen);
	if (err<0 || (err>0 && nlen-lencode.count[0]!=1)) return -1;

	err=construct(&distcode,lengths+nlen,ndist);
	if (err<0 || (err>0 && ndist-distcode.count[0]!=1)) return -1;

	return codes(s,&lencode,&distcode);
}

static int stored(struct inf_state *s)
{
	unsigned len;

	s->bitbuf=0;
	s->bitcnt=0;

	if (s->incnt+4>s->inlen) longjmp(s->env,NEED_INPUT);
	len=s->in[s->incnt]|(s->in[s->incnt+1]<<8);
	if (s->in[s->incnt+2]!=(~len&0xff) || s->in[s->incnt+3]!=((~len>>8)&0xff)) return -1;
	s->incnt+=4;

	if (s->incnt+len>s->inlen) longjmp(s->env,NEED_INPUT);
	if (!grow(&s->blk,&s->blkcap,s->blklen+len)) return -1;
	memcpy(s->blk+s->blklen,s->in+s->incnt,len);
	s->blklen+=len;
	s->incnt+=len;

	return 0;
}

/* returns 0 = block done, NEED_INPUT, BAD_DATA */
static int one_block(struct inf_state *s)
{
	volatile int last=0;
	int type,err,r;
	size_t keep;

	s->incnt=s->bitpos>>3;
	s->bitbuf=0;
	s->bitcnt=0;
	s->blklen=0;

	r=setjmp(s->env);
	if (r) return r;

	if (s->bitpos&7) bits(s,(int)(s->bitpos&7));

	last=bits(s,1);
	type=bits(s,2);

	if (type==0) err=stored(s);
	else if (type==1) err=codes(s,&fixed_len,&fixed_dist);
	else if (type==2) err=dynamic(s);
	else err=-1;

	if (err) return BAD_DATA;

	/* block complete: commit */
	s->bitpos=s->incnt*8-s->bitcnt;

	if (!grow(&s->pend,&s->pendcap,s->pendlen+s->blklen)) return BAD_DATA;
	memcpy(s->pend+s->pendlen,s->blk,s->blklen);
	s->pendlen+=s->blklen;

	if (s->blklen>=WSIZE) {
		memcpy(s->hist,s->blk+s->blklen-WSIZE,WSIZE);
		s->histlen=WSIZE;
	} else {
		if (s->histlen+s->blklen>WSIZE) {
			keep=WSIZE-s->blklen;
			memmove(s->hist,s->hist+s->histlen-keep,keep);
			s->histlen=keep;
		}
		memcpy(s->hist+s->histlen,s->blk,s->blklen);
		s->histlen+=s->blklen;
	}

	if (last) s->done=1;

	return 0;
}

static int init_common(z_stream *strm,int raw)
{
	struct inf_state *s;

	if (!fixed_done) build_fixed();

	s=calloc(1,sizeof(struct inf_state));
	if (!s) return Z_MEM_ERROR;
	s->raw=raw;
	s->need_header=!raw;

	strm->state=s;
	strm->total_in=strm->total_out=0;
	strm->msg=NULL;

	return Z_OK;
}

int inflateInit(z_stream *strm) { return init_common(strm,0); }
int inflateInit_raw(z_stream *strm) { return init_common(strm,1); }

int inflate(z_stream *strm,int flush)
{
	struct inf_state *s=strm->state;
	size_t n,drop;
	int r,progress=0;

	(void)flush;

	if (!s) return Z_STREAM_ERROR;

	/* buffer all new input */
	if (strm->avail_in) {
		if (!grow(&s->in,&s->incap,s->inlen+strm->avail_in)) return Z_MEM_ERROR;
		memcpy(s->in+s->inlen,strm->next_in,strm->avail_in);
		s->inlen+=strm->avail_in;
		strm->next_in+=strm->avail_in;
		strm->total_in+=strm->avail_in;
		strm->avail_in=0;
		progress=1;
	}

	if (s->need_header) {
		if (s->inlen<2) return Z_OK;
		if ((s->in[0]&0x0f)!=8 || ((s->in[0]<<8)+s->in[1])%31 || (s->in[1]&0x20)) {
			strm->msg="invalid zlib header";
			return Z_DATA_ERROR;
		}
		s->bitpos=16;
		s->need_header=0;
	}

	while (!s->done) {
		r=one_block(s);
		if (r==NEED_INPUT) break;
		if (r==BAD_DATA) {
			strm->msg="invalid deflate data";
			return Z_DATA_ERROR;
		}
	}

	/* drop fully consumed input bytes */
	drop=s->bitpos>>3;
	if (drop) {
		memmove(s->in,s->in+drop,s->inlen-drop);
		s->inlen-=drop;
		s->bitpos-=drop*8;
	}

	/* hand out decoded data */
	n=s->pendlen-s->pendpos;
	if (n>strm->avail_out) n=strm->avail_out;
	if (n) {
		memcpy(strm->next_out,s->pend+s->pendpos,n);
		strm->next_out+=n;
		strm->avail_out-=(unsigned)n;
		strm->total_out+=(unsigned long)n;
		s->pendpos+=n;
		progress=1;
	}
	if (s->pendpos==s->pendlen) s->pendpos=s->pendlen=0;

	if (s->done && s->pendlen==0) return Z_STREAM_END;
	if (!progress) return Z_BUF_ERROR;

	return Z_OK;
}

int inflateEnd(z_stream *strm)
{
	struct inf_state *s=strm->state;

	if (!s) return Z_STREAM_ERROR;
	free(s->in);
	free(s->pend);
	free(s->blk);
	free(s);
	strm->state=NULL;

	return Z_OK;
}
