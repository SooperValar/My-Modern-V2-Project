' MyV2: start the game server and the MyV2 Editor in Ubuntu, without a window.
' Run by the scheduled task MyV2 Server when Cody logs on to Windows.
Set sh = CreateObject("WScript.Shell")
sh.Run "wsl.exe -- bash /mnt/c/Users/Cody/Desktop/MyV2/Server/myv2-start.sh", 0, False
