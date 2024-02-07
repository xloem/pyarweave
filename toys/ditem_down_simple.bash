#!/usr/bin/env bash

GW=https://arweave.net/
DATA=$(mktemp)
cat > "$DATA"
SIZE=$(head -n1 < "$DATA" | jq -r .size)
DEPTH=$(head -n1 < "$DATA" | jq -r '.depth // 1')
for ((d=DEPTH; d>0; d--))
do
    mv "$DATA" "$DATA".old
    jq -r "\"$GW\" + .id" < "$DATA".old | parallel -k -j128 -N16 curl -sL | pv -pteab --name "depth=$d" -s "$SIZE" > "$DATA"
    rm "$DATA".old
done
cat "$DATA"
rm "$DATA"
