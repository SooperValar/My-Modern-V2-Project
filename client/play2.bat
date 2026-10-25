@echo off
rem A second client at the same time (testing): its own login/options file merc2.dat
cd /d "%~dp0"
start "" merc.exe -h 127.0.0.1 -p 5555 -m -o merc2.dat
