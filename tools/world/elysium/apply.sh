#!/bin/bash
# Elysium: build the spec from the sheet and apply it to the server .dat (server stopped!)
set -e
P="$HOME/mnt/Client/Claude outputs/My-Modern-V2-Project/tools/world/elysium"
W=$HOME/mnt/Server/.dat; L=$HOME/l11/ely_live
rm -rf $L && mkdir -p $L/.dat && cp $W/*.dat $L/.dat/
$HOME/tq/ely $L/.dat 771 829 788 826 > $HOME/l11/ely.tsv 2>/dev/null
python3 "$P/elysium_build.py" "$P/elysium_layout.xlsx" $HOME/l11/ely.tsv $HOME/l11/elysium.spec
$HOME/tq/build_lab $L/.dat $HOME/l11/elysium.spec > $L/build.log; tail -1 $L/build.log; grep -c "moved from" $L/build.log
cp $HOME/bt/server $L/server; cd $L
timeout 170 ./server light > light.log 2>&1; tail -c 60 light.log; echo
cp $L/.dat/*.dat $W/ && for f in $L/.dat/*.dat; do cmp $f $W/$(basename $f); done && echo copied back
