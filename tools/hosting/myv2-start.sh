#!/bin/bash
# MyV2: start the MyV2 Editor (and through it the game server) in Ubuntu; run by Windows at log-on
# (scheduled task "MyV2 Server", myv2-autostart.vbs). The editor stays in the foreground so Windows keeps
# Ubuntu running; it also makes the automatic backups. Its output goes to ~/editor.log.
cd ~ || exit 1
if pgrep -f "Server/mapedit.py" >/dev/null; then
    echo "$(date '+%F %T') editor already running" >> ~/editor.log
    # keep this window's Ubuntu session alive as long as the running editor
    while pgrep -f "Server/mapedit.py" >/dev/null; do sleep 60; done
    exit 0
fi
echo "$(date '+%F %T') starting the editor (and the server)" >> ~/editor.log
exec python3 /mnt/c/Users/Cody/Desktop/MyV2/Server/mapedit.py --start-server >> ~/editor.log 2>&1
