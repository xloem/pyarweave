#!/usr/bin/env python3

import datetime
from ar import Peer, Wallet, Transaction
from bundlr import Node, DataItem
from jose.utils import base64url_decode

print('Generating a wallet ...')
wallet = Wallet.generate()

print('Uploading "Hello, world." ...')
di = DataItem(owner = base64url_decode(wallet.jwk_data['n'].encode()), data=b'Hello, world.')
di.sign(wallet.jwk_data)

node = Node()
peer = Peer()
result = node.send_tx(di.tobytes())

txid = result['id']
current_block = peer.current_block()
eta = current_block['timestamp'] + (result['block'] - current_block['height']) * 60 * 2
eta = datetime.datetime.fromtimestamp(eta)

print(f'https://arweave.net/{result["id"]} should be mined by {eta.isoformat()} block {result["block"]} or so, at the very latest.')
