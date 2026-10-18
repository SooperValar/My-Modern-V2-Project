#ifndef MOA_PNGDEC_H
#define MOA_PNGDEC_H
#include <stdio.h>

/* Decode a PNG starting at fp's current position.
   Returns malloc'd pixel data (w*h*channels bytes, channels is 3 or 4) or NULL. */
unsigned char *png_decode(FILE *fp,int *xs,int *ys,int *channels);

#endif
