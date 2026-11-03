#!/bin/bash
# cross-build with clang-cl + lld-link against the real MSVC/Windows SDK
set -e
S=/home/claude/sdk
cd /home/claude/port/src
mkdir -p obj
SRC="main.c dd.c engine.c inter.c socket.c sound.c options.c conv.c inflate.c pngdec.c crash.c"
fail=0
for f in $SRC; do
  /home/claude/cl.sh /nologo /c /O2 /W3 /MT /D_CRT_SECURE_NO_WARNINGS /D_CRT_NONSTDC_NO_WARNINGS /D_WINSOCK_DEPRECATED_NO_WARNINGS \
     -Wno-unused-variable -Wno-unused-but-set-variable -Wno-microsoft-anon-tag \
     /Foobj/${f%.c}.obj $f || fail=1
done
[ $fail = 0 ] || exit 1
llvm-rc /nologo /I $S/inc/um /I $S/inc/shared /I $S/inc/ucrt /I $S/inc/msvc /C 1252 /FO obj/client.res client.rc
lld-link /nologo /subsystem:windows /machine:x86 /largeaddressaware /dynamicbase /nxcompat /libpath:$S/lib \
   obj/*.obj obj/client.res user32.lib gdi32.lib kernel32.lib advapi32.lib shell32.lib comdlg32.lib winmm.lib wsock32.lib dsound.lib \
   /out:merc.exe
ls -la merc.exe
