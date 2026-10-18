@echo off
rem ------------------------------------------------------------------
rem  Build the ported Astonia v2 client (merc.exe) with Visual Studio.
rem  Just double-click this file, or run it from a command prompt.
rem  Needs Visual Studio with the "Desktop development with C++" workload.
rem ------------------------------------------------------------------
setlocal
cd /d "%~dp0"

if defined VSCMD_VER goto havevs
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" (
  echo Could not find vswhere.exe - is Visual Studio installed?
  goto fail
)
for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSDIR=%%i"
if not defined VSDIR (
  echo Visual Studio C++ tools not found.
  goto fail
)
call "%VSDIR%\VC\Auxiliary\Build\vcvarsall.bat" x86 >nul || goto fail
:havevs

if not exist obj mkdir obj

set CFLAGS=/nologo /c /O2 /W3 /MT /D_CRT_SECURE_NO_WARNINGS /D_CRT_NONSTDC_NO_WARNINGS /D_WINSOCK_DEPRECATED_NO_WARNINGS /wd4244 /wd4018 /wd4996
set SRC=main.c dd.c engine.c inter.c socket.c sound.c options.c conv.c inflate.c pngdec.c crash.c

cl %CFLAGS% /Foobj\ %SRC% || goto fail
rc /nologo /c 1252 /fo obj\client.res client.rc || goto fail
link /nologo /subsystem:windows /machine:x86 /largeaddressaware /dynamicbase /nxcompat ^
  obj\*.obj obj\client.res ^
  user32.lib gdi32.lib kernel32.lib advapi32.lib shell32.lib comdlg32.lib winmm.lib wsock32.lib dsound.lib ^
  /out:merc.exe || goto fail

echo.
echo Build OK: merc.exe
goto end

:fail
echo.
echo BUILD FAILED
:end
if "%1"=="" pause
endlocal
