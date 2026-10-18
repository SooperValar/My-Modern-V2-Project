/*
 * crash.c - diagnostics for the ported client.
 *
 * The original client just vanished when something went wrong. This writes
 * client.log next to merc.exe and, on a crash, records the exception code and
 * the faulting address (relative to merc.exe) and tells the user.
 */
#include <windows.h>
#include <stdio.h>
#include <stdarg.h>
#include <time.h>
#include <string.h>
#include <stdlib.h>
#include <signal.h>

static char log_path[MAX_PATH];

void dbg_log(const char *format,...)
{
	FILE *fp;
	va_list args;
	time_t t;
	char tbuf[32];

	if (!log_path[0]) return;

	fp=fopen(log_path,"a");
	if (!fp) return;

	t=time(NULL);
	strftime(tbuf,sizeof(tbuf),"%Y-%m-%d %H:%M:%S",localtime(&t));
	fprintf(fp,"[%s] ",tbuf);

	va_start(args,format);
	vfprintf(fp,format,args);
	va_end(args);

	fputc('\n',fp);
	fclose(fp);
}

static LONG WINAPI crash_handler(EXCEPTION_POINTERS *ep)
{
	char buf[512],mod[MAX_PATH]="?";
	DWORD code=ep->ExceptionRecord->ExceptionCode;
	void *addr=ep->ExceptionRecord->ExceptionAddress;
	HMODULE hm=NULL;
	unsigned long off=0;

	if (GetModuleHandleEx(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCSTR)addr,&hm)) {
		GetModuleFileName(hm,mod,MAX_PATH);
		off=(unsigned long)((char*)addr-(char*)hm);
	}

	dbg_log("CRASH: exception 0x%08lX at %p (%s+0x%lX)",code,addr,mod,off);
	if (code==EXCEPTION_ACCESS_VIOLATION && ep->ExceptionRecord->NumberParameters>=2)
		dbg_log("       %s address %p",ep->ExceptionRecord->ExceptionInformation[0] ? "writing" : "reading",
			(void*)ep->ExceptionRecord->ExceptionInformation[1]);

	sprintf(buf,"The client crashed.\n\nException 0x%08lX at %s+0x%lX\n\nDetails were written to client.log.",
		code,strrchr(mod,'\\') ? strrchr(mod,'\\')+1 : mod,off);
	MessageBox(NULL,buf,"Client crash",MB_OK|MB_ICONSTOP|MB_TOPMOST);

	return EXCEPTION_EXECUTE_HANDLER;
}

// PORT: the Microsoft CRT terminates the process instantly (no exception,
// no message) when a CRT function gets an invalid argument, e.g. close(-1).
// The Borland CRT the game was written for just returned an error. Restore
// that behaviour, but log it.
static void __cdecl invalid_param(const wchar_t *expr,const wchar_t *func,const wchar_t *file,unsigned int line,uintptr_t res)
{
	static int cnt=0;
	(void)expr; (void)func; (void)file; (void)line; (void)res;
	if (cnt++<20) dbg_log("CRT invalid parameter (ignored, #%d)",cnt);
}

static void on_abort(int sig)
{
	(void)sig;
	dbg_log("CRASH: abort() called");
	MessageBox(NULL,"The client aborted. Details were written to client.log.","Client crash",MB_OK|MB_ICONSTOP|MB_TOPMOST);
	_exit(3);
}

static void __cdecl purecall(void)
{
	dbg_log("CRASH: pure virtual call");
	_exit(3);
}

void crash_init(void)
{
	char *p;

	GetModuleFileName(NULL,log_path,MAX_PATH);
	p=strrchr(log_path,'\\');
	if (p) strcpy(p+1,"client.log");
	else strcpy(log_path,"client.log");

	SetUnhandledExceptionFilter(crash_handler);
	_set_invalid_parameter_handler(invalid_param);
	_set_purecall_handler(purecall);
	signal(SIGABRT,on_abort);
	_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);

	dbg_log("---- client start ----");
}
