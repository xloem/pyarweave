#!/usr/bin/env python3

import datetime, os
from ar import Peer, Wallet, DataItem, ArweaveNetworkException
from bundlr import Node
import requests

if os.path.exists('testwallet.json'):
    wallet = Wallet('testwallet.json')
else:
    print('Generating a wallet ...')
    wallet = Wallet.generate(jwk_file='testwallet.json')

print('Uploading ...')
node = Node()
peer = Peer()

def see(osize):
    di = DataItem(data = (b'Hello, world.' * int(osize//len('hello  world ')+1))[:osize])
    di.sign(wallet.rsa)
    b = di.tobytes()
    size = len(b)
    try:
        result = node.send_tx(b)
        txid = result['id']
        print(size, ':', txid)
        return [osize, size, True]
    except ArweaveNetworkException as e:
        print(size, ':', e)
        return [osize, size, False]
i = [see(0),see(200000)]
assert i[0][-1]
assert not i[1][-1]
while i[0][1]+1<i[1][1]:
    size = int((i[0][0] + i[1][0]) / 2)
    status = see(size)
    i[0 if status[-1] else 1] = status
assert see(i[0][0])
print(i[0])
