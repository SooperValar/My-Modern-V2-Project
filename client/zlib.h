/*
 * Minimal zlib-compatible inflate for the Astonia v2 client.
 *
 * Replaces the old Borland-built zlib.LIB. Only the parts of the zlib API the
 * client actually uses are provided: z_stream, inflateInit(), inflate() and
 * inflateEnd(). Decompression is streaming: the 32K history window is kept
 * between calls, so the server's continuous deflate stream (one sync-flushed
 * chunk per tick) decodes exactly like it did with real zlib.
 */
#ifndef MOA_ZLIB_H
#define MOA_ZLIB_H

#define Z_OK            0
#define Z_STREAM_END    1
#define Z_STREAM_ERROR (-2)
#define Z_DATA_ERROR   (-3)
#define Z_MEM_ERROR    (-4)
#define Z_BUF_ERROR    (-5)

#define Z_NO_FLUSH      0
#define Z_SYNC_FLUSH    2
#define Z_FINISH        4

#define Z_NULL          0

typedef struct z_stream_s {
	unsigned char *next_in;
	unsigned int avail_in;
	unsigned long total_in;

	unsigned char *next_out;
	unsigned int avail_out;
	unsigned long total_out;

	char *msg;
	void *state;

	void *zalloc;
	void *zfree;
	void *opaque;
} z_stream;

int inflateInit(z_stream *strm);
int inflateInit_raw(z_stream *strm);	/* raw deflate, no zlib header */
int inflate(z_stream *strm,int flush);
int inflateEnd(z_stream *strm);

#endif
