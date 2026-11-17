#!/bin/bash
# Put area build scripts live (Claude's device shell). Usage:
#   tools/world/deploy.sh [--code] <script.py> [<script.py> ...]
# 1. stops the game ONLY if nobody is online (stop-send: the live world comes to Server/.dat), 2. runs each script on
# Server/.dat, 3. recomputes the lights on a copy (~/ctest/server light; build ~/ctest first, see HANDOFF "Test server"),
# 4. --code: "get" (the changed source goes to Ubuntu and is rebuilt), 5. update-world (starts the game), 6. reload-editor,
# 7. shows spawn failures ("Could not drop char N": a blocked or tavern tile) from the log since the start.
set -o pipefail
S="$HOME/mnt/MyV2/Server"; C="$S/control"; ID="dep$$"; CODE=0
[ "$1" = "--code" ] && { CODE=1; shift; }
req(){ echo "{\"id\":\"$ID-$1\",\"action\":\"$2\"}" > "$C/requests/$ID-$1.json"; for i in $(seq 1 60); do [ -f "$C/responses/$ID-$1.json" ] && return 0; sleep 3; done; echo "no answer to $2"; return 1; }
[ -x "$HOME/ctest/server" ] || { echo "build ~/ctest/server first (HANDOFF: Test server)"; exit 1; }
grep -q '"online": 0' "$C/status.json" || { echo "SOMEONE IS ONLINE: not stopping. Ask Cody."; exit 2; }
req stop stop-send || exit 1; grep -q '"ok": true' "$C/responses/$ID-stop.json" || { cat "$C/responses/$ID-stop.json"; exit 1; }
for f in "$@"; do echo "== $f"; python3 "$f" "$S/.dat" 2>&1 | tail -${TAIL:-12} || { echo "SCRIPT FAILED: the game is stopped, Server/.dat may be half changed. Fix, or send update-world after restoring .dat/mapedit-backups."; exit 3; }; done
rm -rf "$HOME/ctest/.dat"; mkdir "$HOME/ctest/.dat"; for f in "$S"/.dat/*; do [ -f "$f" ] && cp "$f" "$HOME/ctest/.dat/"; done
(cd "$HOME/ctest" && ./server light > light.txt 2>&1) && cp "$HOME/ctest/.dat/map.dat" "$S/.dat/map.dat" && echo "lights recomputed"
[ $CODE = 1 ] && { req get get; python3 -c "import json,sys; r=json.load(open('$C/responses/$ID-get.json')); print('code:', r.get('ok'), [l for l in r.get('log',[]) if ' error ' in l][:5])"; }
req uw update-world; grep -o "the server is up" "$C/responses/$ID-uw.json" || cat "$C/responses/$ID-uw.json"
sleep 12; req re reload-editor; req log log
python3 - "$C/responses/$ID-log.json" <<'PY'
import json,sys
L=json.load(open(sys.argv[1])).get('log') or []; i=[k for k,l in enumerate(L) if 'Entering game loop' in l]
print('spawn failures since the start:', [l for l in L[i[-1]:] if 'drop' in l] if i else 'start not in the log tail')
PY
