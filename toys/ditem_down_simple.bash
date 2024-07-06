#!/usr/bin/env bash

GW=https://arweave.net/
#GW=https://permagate.io/
#GW=https://darksunrayz.store/
DATA=$(mktemp)
cat > "$DATA"
head -n1 < "$DATA" | jq -r .name 1>&2
SIZE=$(head -n1 < "$DATA" | jq -r .size)
DEPTH=$(head -n1 < "$DATA" | jq -r '.depth // 1')
for ((d=DEPTH; d>0; d--))
do
    mv "$DATA" "$DATA".old
        #parallel -k -j128 -N24 wget -qO - | 
    jq -r "\"$GW\" + .id" < "$DATA".old |
        parallel -k -j32 -N24 wget -qO - | 
        if ((d>1))
        then
            pv -trb --line-mode --name "depth=$d" > "$DATA"
        else
            pv -pteab --name "depth=$d" -s "$SIZE"
        fi
    rm "$DATA".old
done
