#!/bin/bash
# claude-sync.sh - keep the Ubuntu server (live) and the Windows Server folder
# (the copy Claude can edit) in step. Run it from the Ubuntu server folder.
#
#   ./claude-sync.sh send        Ubuntu -> Windows: source files, and the world
#                                data too if the server is stopped
#   ./claude-sync.sh get         Windows -> Ubuntu: source files Claude changed,
#                                then rebuilds the server
#   ./claude-sync.sh get-world   Windows -> Ubuntu: the world data (.dat files).
#                                Server must be stopped. Makes a backup first.
#
# Every 'get' backs up what it replaces into ~/claude-backups/<date-time>/.

WIN=/mnt/c/Users/Cody/Desktop/MyV2/Server
LIVE="$(cd "$(dirname "$0")" && pwd)"
BK="$HOME/claude-backups/$(date +%Y%m%d-%H%M%S)"
cd "$LIVE" || exit 1

running() { pgrep -x server >/dev/null; }

case "$1" in
send)
	# -u: never overwrite a file Claude changed on the Windows side and you have not "get" yet
	cp -pu *.c *.h Makefile "$WIN"/ && echo "Source sent to Windows (files changed there by Claude are kept)."
	if running; then
		echo "Server is running: world data NOT sent (stop the server and run 'send' again if Claude needs it)."
	else
		mkdir -p "$WIN/.dat" && cp -p .dat/*.dat "$WIN/.dat/" && echo "World data sent to Windows."
	fi
	;;
get)
	n=0
	for f in "$WIN"/*.c "$WIN"/*.h "$WIN"/Makefile; do
		b=$(basename "$f")
		if [ ! -f "$b" ] || ! cmp -s "$f" "$b"; then
			mkdir -p "$BK"; [ -f "$b" ] && cp -p "$b" "$BK/"
			cp -p "$f" "$b"; echo "  updated $b"; n=$((n+1))
		fi
	done
	echo "$n source file(s) updated."
	[ $n -gt 0 ] && echo "Backup: $BK" && make server && echo "Rebuilt. Restart the server to use it."
	;;
get-world)
	if running; then echo "Stop the server first."; exit 1; fi
	mkdir -p "$BK/.dat" && cp -p .dat/*.dat "$BK/.dat/" || exit 1
	cp -p "$WIN"/.dat/*.dat .dat/ && echo "World data updated. Backup: $BK/.dat"
	;;
*)
	sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
	;;
esac
