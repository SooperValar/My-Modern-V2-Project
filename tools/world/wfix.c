/* copy weapon value and attribute requirements from a template to its items:
 * wfix <.dat> <temp> <old template wv> [write]  - wv changes by (new - old), so enhanced pieces keep their bonus */
#include <stdio.h>
#include <stdlib.h>
#include "gendefs.h"
#include "data.h"
static struct item T[MAXTITEM];
int main(int a,char**v){char p[300];sprintf(p,"%s/titem.dat",v[1]);FILE*f=fopen(p,"rb");fread(T,sizeof(struct item),MAXTITEM,f);fclose(f);
int t=atoi(v[2]),ow=atoi(v[3]),n=0;sprintf(p,"%s/item.dat",v[1]);f=fopen(p,a>4?"r+b":"rb");static struct item I;
for(long i=0;i<MAXITEM;i++){fseek(f,i*sizeof I,SEEK_SET);if(fread(&I,sizeof I,1,f)!=1)break;if(!I.used||I.temp!=t)continue;
int nw=I.weapon[0]+T[t].weapon[0]-ow;printf("item %ld %s wv %d -> %d, agi %d->%d str %d->%d\n",i,I.name,I.weapon[0],nw,I.attrib[3][2],T[t].attrib[3][2],I.attrib[4][2],T[t].attrib[4][2]);n++;
if(a>4){I.weapon[0]=nw;I.weapon[1]=I.weapon[1]?I.weapon[1]+T[t].weapon[0]-ow:0;I.attrib[3][2]=T[t].attrib[3][2];I.attrib[4][2]=T[t].attrib[4][2];fseek(f,i*sizeof I,SEEK_SET);fwrite(&I,sizeof I,1,f);}}
printf("%d item(s)\n",n);}
