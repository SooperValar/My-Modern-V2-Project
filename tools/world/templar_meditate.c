/* one-off: give the Templar and Arch-Templar player templates Meditate fixed at 1 */
#include <stdio.h>
#include "gendefs.h"
#include "data.h"
int main(int c,char**v){
 FILE*f=fopen(v[1],"r+b"); static struct character ch; int ids[]={3,77,544,549},k;
 if(!f){perror(v[1]);return 1;}
 for(k=0;k<4;k++){ fseek(f,(long)ids[k]*sizeof(ch),0); fread(&ch,sizeof(ch),1,f);
  if(!(ch.kindred&(KIN_TEMPLAR|KIN_ARCHTEMPLAR))){printf("%d is not a Templar template (%s), skipped\n",ids[k],ch.name);continue;}
  ch.skill[SK_MEDIT][0]=1; ch.skill[SK_MEDIT][1]=0; ch.skill[SK_MEDIT][2]=1; ch.skill[SK_MEDIT][3]=9;
  fseek(f,(long)ids[k]*sizeof(ch),0); fwrite(&ch,sizeof(ch),1,f);
  printf("%d %s: Meditate 1/1\n",ids[k],ch.name);}
 fclose(f); return 0;}
