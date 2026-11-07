/*
 * Mercenaries of Asgard v2 launcher (MyV2): keeps the player's client up to date, then starts the game.
 *
 * It reads manifest.txt from the update site (the client-dist branch of the project on GitHub,
 * over HTTPS), compares each listed file's SHA-256 with the player's copy, downloads what is
 * missing or different, checks it, and puts it in place. Then it starts merc.exe and closes.
 * If the update site can't be reached, it just starts the game.
 *
 * manifest.txt, one entry per line:
 *     version <text>                      shown to the player
 *     file <sha256> <size> <path>         kept up to date (path relative to the game folder, '/' separators)
 *     base <size> <path>                  must exist, never downloaded (the big original graphics from the zip)
 *     # comment
 *
 * It never touches the player's own files (merc.dat, client.ini, *.moa, client.log) and refuses
 * paths that leave the game folder. It updates itself too: a new Launcher.exe is downloaded as
 * Launcher.new.exe, the running one is renamed Launcher.old.exe (Windows allows renaming a
 * running program), the new one takes its place and is started again.
 *
 * client.ini [update] base=<url> points it somewhere else (for testing); off=1 turns updating off.
 *
 * Built with the client's toolchain: clang-cl + lld-link (see tools/release/build_launcher.sh).
 * WinHTTP is loaded at run time (winhttp.dll ships with every Windows), SHA-256 is done here.
 */
#include <windows.h>
#include <winhttp.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define UPDATE_BASE	"https://raw.githubusercontent.com/SooperValar/My-Modern-V2-Project/client-dist/"
#define GAME_EXE	"merc.exe"
#define SELF_EXE	"Launcher.exe"
#define TITLE		"Mercenaries of Asgard v2"

/* ------------------------------------------------------------------ SHA-256 */
typedef struct { unsigned int s[8]; unsigned long long n; unsigned char b[64]; int bl; } SHA;
static const unsigned int K[64]={
0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,
0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,
0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,
0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
#define ROR(x,n) (((x)>>(n))|((x)<<(32-(n))))
static void sha_block(SHA *c,const unsigned char *p)
{
	unsigned int w[64],a,b,d,e,f,g,h,cc,t1,t2; int i;
	for (i=0; i<16; i++) w[i]=(p[i*4]<<24)|(p[i*4+1]<<16)|(p[i*4+2]<<8)|p[i*4+3];
	for (i=16; i<64; i++) w[i]=w[i-16]+(ROR(w[i-15],7)^ROR(w[i-15],18)^(w[i-15]>>3))+w[i-7]+(ROR(w[i-2],17)^ROR(w[i-2],19)^(w[i-2]>>10));
	a=c->s[0]; b=c->s[1]; cc=c->s[2]; d=c->s[3]; e=c->s[4]; f=c->s[5]; g=c->s[6]; h=c->s[7];
	for (i=0; i<64; i++) {
		t1=h+(ROR(e,6)^ROR(e,11)^ROR(e,25))+((e&f)^(~e&g))+K[i]+w[i];
		t2=(ROR(a,2)^ROR(a,13)^ROR(a,22))+((a&b)^(a&cc)^(b&cc));
		h=g; g=f; f=e; e=d+t1; d=cc; cc=b; b=a; a=t1+t2;
	}
	c->s[0]+=a; c->s[1]+=b; c->s[2]+=cc; c->s[3]+=d; c->s[4]+=e; c->s[5]+=f; c->s[6]+=g; c->s[7]+=h;
}
static void sha_init(SHA *c)
{
	static const unsigned int I[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
	memcpy(c->s,I,sizeof(I)); c->n=0; c->bl=0;
}
static void sha_add(SHA *c,const void *data,size_t len)
{
	const unsigned char *p=data;
	c->n+=len;
	while (len) {
		int k=64-c->bl; if ((size_t)k>len) k=(int)len;
		memcpy(c->b+c->bl,p,k); c->bl+=k; p+=k; len-=k;
		if (c->bl==64) { sha_block(c,c->b); c->bl=0; }
	}
}
static void sha_hex(SHA *c,char *out)
{
	unsigned long long bits=c->n*8; unsigned char pad=0x80,z=0,L[8]; int i;
	sha_add(c,&pad,1);
	while (c->bl!=56) sha_add(c,&z,1);
	for (i=0; i<8; i++) L[i]=(unsigned char)(bits>>(56-8*i));
	sha_add(c,L,8);
	for (i=0; i<8; i++) sprintf(out+i*8,"%08x",c->s[i]);
}
static int file_sha(const char *path,char *hex,long long *size)	/* 1 = read */
{
	HANDLE f=CreateFileA(path,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,NULL,OPEN_EXISTING,0,NULL);
	static unsigned char buf[65536]; DWORD got; SHA c; long long n=0;
	if (f==INVALID_HANDLE_VALUE) return 0;
	sha_init(&c);
	while (ReadFile(f,buf,sizeof(buf),&got,NULL) && got) { sha_add(&c,buf,got); n+=got; }
	CloseHandle(f); sha_hex(&c,hex); if (size) *size=n; return 1;
}

/* ------------------------------------------------------------------ WinHTTP, loaded at run time */
typedef HINTERNET (WINAPI *pOpen)(LPCWSTR,DWORD,LPCWSTR,LPCWSTR,DWORD);
typedef HINTERNET (WINAPI *pConnect)(HINTERNET,LPCWSTR,INTERNET_PORT,DWORD);
typedef HINTERNET (WINAPI *pOpenRequest)(HINTERNET,LPCWSTR,LPCWSTR,LPCWSTR,LPCWSTR,LPCWSTR*,DWORD);
typedef BOOL (WINAPI *pSend)(HINTERNET,LPCWSTR,DWORD,LPVOID,DWORD,DWORD,DWORD_PTR);
typedef BOOL (WINAPI *pReceive)(HINTERNET,LPVOID);
typedef BOOL (WINAPI *pQueryHeaders)(HINTERNET,DWORD,LPCWSTR,LPVOID,LPDWORD,LPDWORD);
typedef BOOL (WINAPI *pRead)(HINTERNET,LPVOID,DWORD,LPDWORD);
typedef BOOL (WINAPI *pClose)(HINTERNET);
typedef BOOL (WINAPI *pSetTimeouts)(HINTERNET,int,int,int,int);
static pOpen hOpen; static pConnect hConnect; static pOpenRequest hOpenRequest; static pSend hSend; static pReceive hReceive;
static pQueryHeaders hQuery; static pRead hRead; static pClose hClose; static pSetTimeouts hTimeouts;
static HINTERNET session;

static int net_init(void)
{
	HMODULE m=LoadLibraryA("winhttp.dll");
	if (!m) return 0;
	hOpen=(pOpen)GetProcAddress(m,"WinHttpOpen"); hConnect=(pConnect)GetProcAddress(m,"WinHttpConnect");
	hOpenRequest=(pOpenRequest)GetProcAddress(m,"WinHttpOpenRequest"); hSend=(pSend)GetProcAddress(m,"WinHttpSendRequest");
	hReceive=(pReceive)GetProcAddress(m,"WinHttpReceiveResponse"); hQuery=(pQueryHeaders)GetProcAddress(m,"WinHttpQueryHeaders");
	hRead=(pRead)GetProcAddress(m,"WinHttpReadData"); hClose=(pClose)GetProcAddress(m,"WinHttpCloseHandle");
	hTimeouts=(pSetTimeouts)GetProcAddress(m,"WinHttpSetTimeouts");
	if (!hOpen || !hConnect || !hOpenRequest || !hSend || !hReceive || !hQuery || !hRead || !hClose) return 0;
	session=hOpen(L"MyV2AstoniaLauncher/1.0",WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,WINHTTP_NO_PROXY_NAME,WINHTTP_NO_PROXY_BYPASS,0);
	if (session && hTimeouts) hTimeouts(session,10000,10000,15000,30000);
	return session!=NULL;
}

/* GET url; the body goes to the file 'out' (if given) or into *mem (malloc'd, 0-terminated). 0 = ok */
typedef void (*progress_fn)(long long got);
static int http_get(const char *url,const char *out,char **mem,long long *len,progress_fn prog)
{
	wchar_t wurl[1024],host[256],path[1024]; URL_COMPONENTS u; HINTERNET c=NULL,r=NULL;
	DWORD status=0,sl=sizeof(status),got; static char buf[65536]; long long total=0; HANDLE f=INVALID_HANDLE_VALUE;
	char *m=NULL; size_t mcap=0; int ret=1, secure;
	MultiByteToWideChar(CP_UTF8,0,url,-1,wurl,1024);
	memset(&u,0,sizeof(u)); u.dwStructSize=sizeof(u);
	u.lpszHostName=host; u.dwHostNameLength=256; u.lpszUrlPath=path; u.dwUrlPathLength=1024;
	{	/* WinHttpCrackUrl, also loaded at run time */
		typedef BOOL (WINAPI *pCrack)(LPCWSTR,DWORD,DWORD,LPURL_COMPONENTS);
		pCrack crack=(pCrack)GetProcAddress(GetModuleHandleA("winhttp.dll"),"WinHttpCrackUrl");
		if (!crack || !crack(wurl,0,0,&u)) return 1;
	}
	secure=(u.nScheme==INTERNET_SCHEME_HTTPS);
	if (!(c=hConnect(session,host,u.nPort,0))) goto done;
	if (!(r=hOpenRequest(c,L"GET",path,NULL,WINHTTP_NO_REFERER,WINHTTP_DEFAULT_ACCEPT_TYPES,secure ? WINHTTP_FLAG_SECURE : 0))) goto done;
	if (!hSend(r,WINHTTP_NO_ADDITIONAL_HEADERS,0,WINHTTP_NO_REQUEST_DATA,0,0,0) || !hReceive(r,NULL)) goto done;
	if (!hQuery(r,WINHTTP_QUERY_STATUS_CODE|WINHTTP_QUERY_FLAG_NUMBER,WINHTTP_HEADER_NAME_BY_INDEX,&status,&sl,WINHTTP_NO_HEADER_INDEX) || status!=200) { ret=2; goto done; }
	if (out && (f=CreateFileA(out,GENERIC_WRITE,0,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL))==INVALID_HANDLE_VALUE) { ret=3; goto done; }
	for (;;) {
		if (!hRead(r,buf,sizeof(buf),&got)) goto done;
		if (!got) break;
		if (out) { DWORD w; if (!WriteFile(f,buf,got,&w,NULL) || w!=got) { ret=3; goto done; } }
		else {
			if (total+got+1>(long long)mcap) { mcap=(size_t)(total+got+1)*2; m=realloc(m,mcap); if (!m) goto done; }
			memcpy(m+total,buf,got);
		}
		total+=got; if (prog) prog(total);
	}
	if (!out) { if (!m) m=malloc(1); m[total]=0; *mem=m; m=NULL; }
	if (len) *len=total;
	ret=0;
done:
	if (f!=INVALID_HANDLE_VALUE) CloseHandle(f);
	if (m) free(m);
	if (r) hClose(r);
	if (c) hClose(c);
	return ret;
}

/* ------------------------------------------------------------------ the window */
static HWND win,lbl;
static int pct=-1;
static char status_text[256];
static volatile int done_flag=0;
static char gamedir[MAX_PATH];

static void set_status(const char *fmt,...)
{
	va_list a; va_start(a,fmt); vsnprintf(status_text,sizeof(status_text),fmt,a); va_end(a);
	PostMessageA(win,WM_APP,0,0);
}
static void set_pct(int p) { pct=p; PostMessageA(win,WM_APP,0,0); }

static LRESULT CALLBACK wndproc(HWND h,UINT m,WPARAM w,LPARAM l)
{
	switch (m) {
	case WM_APP:
		SetWindowTextA(lbl,status_text); InvalidateRect(h,NULL,FALSE); return 0;
	case WM_PAINT: {
		PAINTSTRUCT ps; HDC dc=BeginPaint(h,&ps); RECT r={20,62,400,80}; HBRUSH bg=CreateSolidBrush(RGB(40,40,46)),fg=CreateSolidBrush(RGB(214,164,67));
		FillRect(dc,&r,bg);
		if (pct>=0) { RECT q=r; q.right=r.left+(r.right-r.left)*(pct>100 ? 100 : pct)/100; FillRect(dc,&q,fg); }
		DeleteObject(bg); DeleteObject(fg); EndPaint(h,&ps); return 0; }
	case WM_CTLCOLORSTATIC:
		SetBkColor((HDC)w,RGB(28,28,32)); SetTextColor((HDC)w,RGB(235,225,205));
		{ static HBRUSH b=NULL; if (!b) b=CreateSolidBrush(RGB(28,28,32)); return (LRESULT)b; }
	case WM_CLOSE:
		if (!done_flag) { done_flag=2; }
		DestroyWindow(h); return 0;
	case WM_DESTROY:
		PostQuitMessage(0); return 0;
	}
	return DefWindowProcA(h,m,w,l);
}

/* ------------------------------------------------------------------ the update */
struct entry { char kind; char sha[65]; long long size; char path[MAX_PATH]; };
static struct entry *ent; static int nent;
static char version[64];
static long long dl_total,dl_done;

static void prog(long long got) { if (dl_total>0) set_pct((int)((dl_done+got)*100/dl_total)); }

static int safe_path(const char *p)	/* stays in the game folder, and isn't one of the player's own files */
{
	const char *b;
	if (!*p || p[0]=='/' || p[0]=='\\' || strchr(p,':') || strstr(p,"..")) return 0;
	b=strrchr(p,'/'); b=b ? b+1 : p;
	if (!_stricmp(b,"merc.dat") || !_stricmp(b,"client.ini") || !_stricmp(b,"client.log") || !_stricmp(b,"launcher.log")) return 0;
	if (strlen(b)>4 && !_stricmp(b+strlen(b)-4,".moa")) return 0;
	return 1;
}

static void local_path(const char *rel,char *out)
{
	char *p;
	snprintf(out,MAX_PATH,"%s%s",gamedir,rel);
	for (p=out; *p; p++) if (*p=='/') *p='\\';
}

static void make_dirs(const char *full)
{
	char t[MAX_PATH],*p; strncpy(t,full,MAX_PATH-1); t[MAX_PATH-1]=0;
	for (p=t+strlen(gamedir); *p; p++) if (*p=='\\') { *p=0; CreateDirectoryA(t,NULL); *p='\\'; }
}

static FILE *logf;
static void lg(const char *fmt,...)
{
	va_list a; if (!logf) return;
	va_start(a,fmt); vfprintf(logf,fmt,a); va_end(a); fputc('\n',logf); fflush(logf);
}

static int parse_manifest(char *txt)
{
	char *line,*next; int cap=0;
	for (line=txt; line && *line; line=next) {
		struct entry e; char kind[8]; long long sz;
		next=strchr(line,'\n'); if (next) *next++=0;
		if (line[0]=='#' || !line[0] || line[0]=='\r') continue;
		if (!strncmp(line,"version ",8)) { strncpy(version,line+8,63); version[63]=0; { char *c=strchr(version,'\r'); if (c) *c=0; } continue; }
		memset(&e,0,sizeof(e));
		if (sscanf(line,"%7s",kind)!=1) continue;
		if (!strcmp(kind,"file")) { if (sscanf(line,"file %64s %lld %259[^\r\n]",e.sha,&sz,e.path)!=3) continue; e.kind='f'; }
		else if (!strcmp(kind,"base")) { if (sscanf(line,"base %lld %259[^\r\n]",&sz,e.path)!=2) continue; e.kind='b'; }
		else continue;
		e.size=sz;
		if (!safe_path(e.path)) { lg("refused path %s",e.path); continue; }
		if (nent>=cap) { cap=cap ? cap*2 : 1024; ent=realloc(ent,cap*sizeof(*ent)); }
		ent[nent++]=e;
	}
	return nent;
}

/* download one file to <path>.part, check it, put it in place. 0 = ok */
static int fetch(const char *base,struct entry *e)
{
	char url[1024],full[MAX_PATH],part[MAX_PATH+8],hex[65]; long long n;
	local_path(e->path,full); snprintf(part,sizeof(part),"%s.part",full);
	make_dirs(full);
	snprintf(url,sizeof(url),"%s%s",base,e->path);
	if (http_get(url,part,NULL,&n,prog)) { DeleteFileA(part); lg("download failed: %s",e->path); return 1; }
	if (!file_sha(part,hex,NULL) || strcmp(hex,e->sha)) { DeleteFileA(part); lg("checksum mismatch: %s",e->path); return 2; }
	if (!MoveFileExA(part,full,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)) { DeleteFileA(part); lg("can't replace %s (%lu)",e->path,GetLastError()); return 3; }
	dl_done+=e->size; set_pct((int)(dl_done*100/(dl_total ? dl_total : 1)));
	return 0;
}

static int self_update;	/* 1: a new launcher was put in place; start it and quit */

static DWORD WINAPI worker(LPVOID arg)
{
	char ini[MAX_PATH],base[512],*man=NULL,full[MAX_PATH],hex[65]; long long sz; int i,need=0,fail=0,busy=0;
	(void)arg;
	snprintf(ini,sizeof(ini),"%sclient.ini",gamedir);
	GetPrivateProfileStringA("update","base",UPDATE_BASE,base,sizeof(base),ini);
	if (base[0] && base[strlen(base)-1]!='/') strcat(base,"/");
	if (GetPrivateProfileIntA("update","off",0,ini)) { set_status("Updates are turned off (client.ini). Starting the game..."); Sleep(600); goto start; }

	set_status("Checking for updates...");
	if (!net_init()) { set_status("Can't check for updates on this PC. Starting the game..."); Sleep(1500); goto start; }
	{ char url[600]; snprintf(url,sizeof(url),"%smanifest.txt",base);
	  if (http_get(url,NULL,&man,NULL,NULL) || !parse_manifest(man)) {
		lg("manifest not reachable: %s",url);
		set_status("The update site can't be reached right now. Starting the game..."); Sleep(1800); goto start; } }
	lg("manifest %s: %d entries",version,nent);

	/* what is missing or different */
	for (i=0; i<nent; i++) {
		struct entry *e=&ent[i];
		local_path(e->path,full);
		if (e->kind=='b') { if (GetFileAttributesA(full)==INVALID_FILE_ATTRIBUTES) { lg("missing base file %s",e->path); e->kind='M'; } continue; }
		if (i%50==0) set_status("Checking your game files... %d of %d",i,nent);
		if (!file_sha(full,hex,&sz) || sz!=e->size || strcmp(hex,e->sha)) { e->kind='D'; dl_total+=e->size; need++; }
	}
	for (i=0; i<nent; i++) if (ent[i].kind=='M') {
		set_status("Your game folder is missing %s. Please download the game again.",ent[i].path);
		MessageBoxA(win,"Some of the game's own files are missing from this folder.\n\nPlease download the game again and unzip the whole folder.",TITLE,MB_ICONWARNING);
		goto start;
	}

	/* a new launcher first: put it in place and start it */
	for (i=0; i<nent; i++) if (ent[i].kind=='D' && !_stricmp(ent[i].path,SELF_EXE)) {
		char me[MAX_PATH],old[MAX_PATH],nw[MAX_PATH];
		struct entry e=ent[i];
		set_status("Updating the launcher...");
		snprintf(me,sizeof(me),"%s%s",gamedir,SELF_EXE); snprintf(old,sizeof(old),"%sLauncher.old.exe",gamedir);
		snprintf(nw,sizeof(nw),"%sLauncher.new.exe",gamedir);
		strcpy(e.path,"Launcher.new.exe");
		{	/* fetch() checks the checksum against the manifest's Launcher.exe entry */
			char url[1024],part[MAX_PATH+8]; long long n;
			snprintf(url,sizeof(url),"%s%s",base,SELF_EXE); snprintf(part,sizeof(part),"%s.part",nw);
			if (http_get(url,part,NULL,&n,NULL) || !file_sha(part,hex,NULL) || strcmp(hex,ent[i].sha)) { DeleteFileA(part); lg("launcher download failed"); break; }
			DeleteFileA(old);
			if (!MoveFileExA(me,old,MOVEFILE_REPLACE_EXISTING) || !MoveFileExA(part,me,MOVEFILE_REPLACE_EXISTING)) { lg("can't swap the launcher (%lu)",GetLastError()); MoveFileExA(old,me,0); break; }
		}
		lg("launcher updated");
		self_update=1; done_flag=1; PostMessageA(win,WM_CLOSE,0,0); return 0;
	}

	if (need) {
		for (i=0; i<nent && !fail; i++) if (ent[i].kind=='D') {
			int r;
			set_status("Downloading update %s: %s",version,ent[i].path);
			r=fetch(base,&ent[i]);
			if (r==3) busy=1;
			if (r) fail++;
		}
		if (busy) {
			MessageBoxA(win,"The update can't replace the game's files while the game is running.\n\nClose the game and start the launcher again.",TITLE,MB_ICONINFORMATION);
			done_flag=2; PostMessageA(win,WM_CLOSE,0,0); return 0;
		}
		if (fail) { set_status("The update didn't finish. Starting the game anyway; it tries again next time."); Sleep(2000); goto start; }
		set_status("Updated to %s. Starting the game...",version);
	} else set_status("Your game is up to date (%s). Starting the game...",version);
	set_pct(100); Sleep(700);
start:
	done_flag=1; PostMessageA(win,WM_CLOSE,0,0);
	return 0;
}

static void run(const char *exe,const char *args)
{
	char cmd[MAX_PATH*2]; STARTUPINFOA si; PROCESS_INFORMATION pi;
	memset(&si,0,sizeof(si)); si.cb=sizeof(si);
	snprintf(cmd,sizeof(cmd),"\"%s%s\" %s",gamedir,exe,args ? args : "");
	if (CreateProcessA(NULL,cmd,NULL,NULL,FALSE,0,NULL,gamedir,&si,&pi)) { CloseHandle(pi.hProcess); CloseHandle(pi.hThread); }
	else MessageBoxA(NULL,"Can't start the game (merc.exe is missing from this folder?).",TITLE,MB_ICONERROR);
}

int WINAPI WinMain(HINSTANCE inst,HINSTANCE prev,LPSTR cmdline,int show)
{
	WNDCLASSA wc; MSG msg; char *p,logp[MAX_PATH],old[MAX_PATH];
	(void)prev; (void)show;
	GetModuleFileNameA(NULL,gamedir,MAX_PATH);
	p=strrchr(gamedir,'\\'); if (p) p[1]=0; else strcpy(gamedir,".\\");
	snprintf(old,sizeof(old),"%sLauncher.old.exe",gamedir); DeleteFileA(old);	/* left over from a self-update */
	snprintf(logp,sizeof(logp),"%slauncher.log",gamedir); logf=fopen(logp,"w");

	memset(&wc,0,sizeof(wc));
	wc.lpfnWndProc=wndproc; wc.hInstance=inst; wc.lpszClassName="MyV2Launcher";
	wc.hbrBackground=CreateSolidBrush(RGB(28,28,32)); wc.hCursor=LoadCursor(NULL,IDC_ARROW);
	wc.hIcon=LoadIconA(inst,"ICON_1");
	RegisterClassA(&wc);
	{
		RECT r={0,0,420,100}; int sw=GetSystemMetrics(SM_CXSCREEN),sh=GetSystemMetrics(SM_CYSCREEN);
		AdjustWindowRect(&r,WS_CAPTION|WS_SYSMENU,FALSE);
		win=CreateWindowA("MyV2Launcher",TITLE,WS_CAPTION|WS_SYSMENU|WS_MINIMIZEBOX,(sw-(r.right-r.left))/2,(sh-(r.bottom-r.top))/2,
				  r.right-r.left,r.bottom-r.top,NULL,NULL,inst,NULL);
	}
	lbl=CreateWindowA("STATIC","Starting...",WS_CHILD|WS_VISIBLE|SS_LEFTNOWORDWRAP,20,22,380,32,win,NULL,inst,NULL);
	SendMessageA(lbl,WM_SETFONT,(WPARAM)GetStockObject(DEFAULT_GUI_FONT),TRUE);
	ShowWindow(win,SW_SHOW); UpdateWindow(win);
	CreateThread(NULL,0,worker,NULL,0,NULL);
	while (GetMessageA(&msg,NULL,0,0)>0) { TranslateMessage(&msg); DispatchMessageA(&msg); }
	if (logf) fclose(logf);
	if (self_update) run(SELF_EXE,"");
	else if (done_flag==1) run(GAME_EXE,cmdline);
	return 0;
}
