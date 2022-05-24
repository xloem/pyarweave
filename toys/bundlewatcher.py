import time

from ar import Peer, ArweaveException, ANS104BundleHeader, Bundle, DataItem
from bundlr import Node

class BundleWatcher:
    def __init__(self, peer = Peer()):
        self.peer = peer
    def run(self):
        mark = time.time()
        height = self.peer.height()
        old_pending_txs = set()
        old_block_txs = set(self.peer.block_height(height)['txs'])
        while True:
            new_pending_txs = set(self.peer.tx_pending())
            new_height = self.peer.height()
            new_block_txs = set()
            for new_height in range(height + 1, new_height + 1):
                height = new_height
                new_block_txs.update(set(self.peer.block_height(height)))
            else:
                new_block_txs = old_block_txs
                
            for txid in new_block_txs.difference(old_block_txs).union(new_pending_txs).difference(old_pending_txs):
                #txid = 'vPwbFzEYlE8Bti7phVRt0ZMPtNG65FfBYM8RwHdS6tY'
                tags = self.peer.unconfirmed_tx(txid)['tags']
                print(txid, tags)
                if any((tag['name'].startswith(b'Bundle') for tag in tags)):
                    try:
                        stream = self.peer.stream(txid)
                    except ArweaveException:
                        new_pending_txs.discard(txid)
                        new_block_txs.discard(txid)
                        continue
                    with stream:
                        #header = ANS104Header.from_tags_stream(tags, stream)
                        #header.data = lambda: Bundle.from_tags_stream(tags, stream)# get individual item
                        #yield from Bundle.from_tags_stream(tags, stream).dataitems
                        yield from DataItem.all_from_tags_stream(tags, stream)
                    #headers = 
                    #print(txid)
            old_block_txs = new_block_txs
            old_pending_txs = new_pending_txs
            now = time.time()
            if mark + 30 > now:
                time.sleep(now - mark + 30)
                mark += 30
            else:
                mark = now

for item in BundleWatcher().run():
    print(item.header.id, item.header.tags)
