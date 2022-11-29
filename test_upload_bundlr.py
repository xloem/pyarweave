#!/usr/bin/env python3

import datetime
from ar import Peer, Wallet, DataItem
from bundlr import Node

print('Generating a wallet ...')
wallet = Wallet.generate()

print('Uploading "Hello, world." ...')
di = DataItem(data = b'Hello, world.')
di.sign(wallet.rsa)

node = Node()
result = node.send_tx(di.tobytes())
txid = result['id']

peer = Peer()

# bundlr used to return an expected block height but now seems to return some timestamp  2022-11
# communicate with bundlr for details on their api.
#current_block = peer.current_block()
#eta = current_block['timestamp'] + (result['block'] - current_block['height']) * 60 * 2
eta = int(result['timestamp']/1000)

eta = datetime.datetime.fromtimestamp(eta)

print(f'{peer.api_url}/{result["id"]} timestamp={eta.isoformat()}')
