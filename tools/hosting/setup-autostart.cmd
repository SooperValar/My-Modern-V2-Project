@echo off
rem MyV2: makes Windows start the game server and the MyV2 Editor when you log on.
rem Right-click this file and pick "Run as administrator" (once).
schtasks /Create /F /TN "MyV2 Server" /SC ONLOGON /RL LIMITED /DELAY 0001:00 /TR "wscript.exe \"%~dp0myv2-autostart.vbs\""
if errorlevel 1 (echo. & echo Could not create the task: right-click this file and pick "Run as administrator". & pause & exit /b 1)
echo.
echo Done: "MyV2 Server" starts the game and the editor one minute after you log on.
echo To start it right now without logging off:  schtasks /Run /TN "MyV2 Server"
pause
