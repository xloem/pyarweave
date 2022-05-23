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
current_block = peer.current_block()
eta = current_block['timestamp'] + (result['block'] - current_block['height']) * 60 * 2
eta = datetime.datetime.fromtimestamp(eta)

print(f'{peer.api_url}/{result["id"]} should be mined by {eta.isoformat()} block {result["block"]} or so, at the very latest.')
