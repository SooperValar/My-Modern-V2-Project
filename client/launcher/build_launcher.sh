#!/bin/bash
# cross-build the launcher with clang-cl + lld-link against the MSVC/Windows SDK (like the client)
set -e
S=/home/claude/sdk
cd "$(dirname "$0")"
mkdir -p obj
/home/claude/cl.sh /nologo /c /O2 /W3 /MT /D_CRT_SECURE_NO_WARNINGS -Wno-unused-parameter /Foobj/launcher.obj launcher.c
llvm-rc /nologo /I $S/inc/um /I $S/inc/shared /I $S/inc/ucrt /I $S/inc/msvc /C 1252 /FO obj/launcher.res launcher.rc
lld-link /nologo /subsystem:windows /machine:x86 /dynamicbase /nxcompat /libpath:$S/lib obj/launcher.obj obj/launcher.res \
   user32.lib gdi32.lib kernel32.lib /out:Launcher.exe
ls -la Launcher.exe
