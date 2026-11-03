#!/bin/sh
exec clang --driver-mode=cl --target=i686-pc-windows-msvc -fms-compatibility-version=19.50 /imsvc /home/claude/sdk/inc/msvc /imsvc /home/claude/sdk/inc/ucrt /imsvc /home/claude/sdk/inc/um /imsvc /home/claude/sdk/inc/shared "$@"
