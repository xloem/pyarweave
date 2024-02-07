#!/usr/bin/env bash

GW=https://arweave.net/
DATA=$(mktemp)
cat > "$DATA"
SIZE=$(head -n1 < "$DATA" | jq -r .size)
DEPTH=$(head -n1 < "$DATA" | jq -r .depth)
for ((d=DEPTH; d>0; d--))
do
    mv "$DATA" "$DATA".old
    jq -r "\"$GW\" + .id" < "$DATA".old | parallel -k -j0 curl -sL | pv --name "depth=$d" -s "$SIZE" > "$DATA"
    rm "$DATA".old
done
cat "$DATA"
rm "$DATA"
