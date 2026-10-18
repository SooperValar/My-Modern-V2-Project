/*
 * makegod - give a player character god rights (like the original Ishtar).
 *
 * Build:  gcc -o makegod makegod.c
 * Usage:  ./makegod              list all player characters
 *         ./makegod <name>       make <name> a god
 *         ./makegod -r <name>    remove god rights again
 *
 * Stop the server before using it.
 */
#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>
#include <sys/mman.h>

#include "gendefs.h"
#include "data.h"

#define CHARSIZE (sizeof(struct character)*MAXCHARS)

#define GODFLAGS (CF_GOD|CF_CREATOR|CF_STAFF|CF_IMP|CF_GREATERGOD|CF_SAFE)

int main(int argc,char *args[])
{
	struct character *ch;
	int handle,cn,remove=0;
	char *name=NULL;

	if (argc==3 && !strcmp(args[1],"-r")) { remove=1; name=args[2]; }
	else if (argc==2) name=args[1];
	else if (argc!=1) { fprintf(stderr,"Usage: %s [-r] [name]\n",args[0]); return 1; }

	handle=open(DATDIR"/char.dat",O_RDWR);
	if (handle==-1) { fprintf(stderr,"cannot open "DATDIR"/char.dat - run this in the server folder.\n"); return 1; }
	ch=mmap(NULL,CHARSIZE,PROT_READ|PROT_WRITE,MAP_SHARED,handle,0);
	close(handle);
	if (ch==(void*)-1) { fprintf(stderr,"cannot mmap char.dat\n"); return 1; }

	if (!name) {
		printf("Player characters:\n");
		for (cn=1; cn<MAXCHARS; cn++)
			if (ch[cn].used && (ch[cn].flags&CF_PLAYER))
				printf("  %-20s %s\n",ch[cn].name,(ch[cn].flags&CF_GOD) ? "(god)" : "");
		munmap(ch,CHARSIZE);
		return 0;
	}

	for (cn=1; cn<MAXCHARS; cn++) {
		if (!ch[cn].used) continue;
		if (!(ch[cn].flags&CF_PLAYER)) continue;
		if (strcasecmp(ch[cn].name,name)==0) break;
	}
	if (cn==MAXCHARS) { printf("Could not find player %s. Run without a name to list players.\n",name); munmap(ch,CHARSIZE); return 2; }

	if (remove) ch[cn].flags&=~GODFLAGS;
	else ch[cn].flags|=GODFLAGS;
	ch[cn].flags|=CF_SAVEME;

	printf("%s (%d) is %s a god.\n",ch[cn].name,cn,remove ? "no longer" : "now");

	munmap(ch,CHARSIZE);
	return 0;
}
