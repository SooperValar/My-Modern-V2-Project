@echo off
rem Build Launcher.exe on Windows with Visual Studio (like client\build.bat). Double-click it.
setlocal
cd /d "%~dp0"
if defined VSCMD_VER goto havevs
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" ( echo Could not find vswhere.exe - is Visual Studio installed? & goto fail )
for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do set "VSDIR=%%i"
if not defined VSDIR ( echo Visual Studio C++ tools not found. & goto fail )
call "%VSDIR%\VC\Auxiliary\Build\vcvarsall.bat" x86 >nul || goto fail
:havevs
if not exist obj mkdir obj
cl /nologo /c /O2 /W3 /MT /D_CRT_SECURE_NO_WARNINGS /Foobj\launcher.obj launcher.c || goto fail
rc /nologo /c 1252 /fo obj\launcher.res launcher.rc || goto fail
link /nologo /subsystem:windows /machine:x86 /dynamicbase /nxcompat obj\launcher.obj obj\launcher.res user32.lib gdi32.lib kernel32.lib /out:Launcher.exe || goto fail
echo Build OK: Launcher.exe
goto end
:fail
echo BUILD FAILED
:end
pause
