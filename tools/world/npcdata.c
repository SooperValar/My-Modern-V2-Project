/* npcdata <.dat folder> <spec>: lines "chd <temp> <i> <value>" set data[i], "cht <temp> <i> <text>" set text[i], of the template and its living NPCs. */
#include <stdio.h>
#include <string.h>
#include "gendefs.h"
#include "data.h"
static struct character c;
int main(int a,char**v){char fn[512],l[200];FILE*s=fopen(v[2],"r");int t,i,val;
 while(fgets(l,200,s)){ char txt[200]=""; int ist=0; if(sscanf(l,"cht %d %d %199[^\n]",&t,&i,txt)==3) ist=1; else if(sscanf(l,"chd %d %d %d",&t,&i,&val)!=3) continue;
  for(int k=0;k<2;k++){ sprintf(fn,"%s/%s",v[1],k?"char.dat":"tchar.dat"); FILE*f=fopen(fn,"r+b"); long n=0;
   while(fread(&c,sizeof(c),1,f)==1){ if(c.used&&(k==0?n==t:c.temp==t)&&!(c.flags&CF_PLAYER)){ int old=0; if(ist){ strncpy(c.text[i],txt,sizeof(c.text[i])-1); c.text[i][sizeof(c.text[i])-1]=0; } else { old=c.data[i]; c.data[i]=val; } fseek(f,n*sizeof(c),SEEK_SET); fwrite(&c,sizeof(c),1,f); fseek(f,(n+1)*sizeof(c),SEEK_SET); if(ist) printf("%s %s (t%d) text[%d] = %s\n",k?"char":"template",c.name,t,i,txt); else printf("%s %s (t%d) data[%d] %d -> %d\n",k?"char":"template",c.name,t,i,old,val);} n++; } fclose(f);} }}
