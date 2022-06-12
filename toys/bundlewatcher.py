import time

from ar import Peer, ArweaveNetworkException, ArweaveException, ANS104BundleHeader, Bundle, DataItem
from bundlr import Node

class BundleWatcher:
    def __init__(self, peer = Peer(), height = None):
        self.peer = peer
        self.height = height
    def run(self):
        mark = time.time()
        if self.height is None:
            self.height = self.peer.height()
        missing_txs = set()
        old_pending_txs = set()
        old_block_txs = set(self.peer.block_height(self.height)['txs'])
        while True:
            new_pending_txs = set(self.peer.tx_pending())
            new_height = self.peer.height()
            new_block_txs = set()
            for new_height in range(self.height + 1, new_height + 1):
                self.height = new_height
                new_block_txs.update(set(self.peer.block_height(self.height)['txs']))
            else:
                new_block_txs = old_block_txs
                
            for txid in new_block_txs.difference(old_block_txs).union(new_pending_txs).difference(old_pending_txs).union(missing_txs):
                #txid = 'vPwbFzEYlE8Bti7phVRt0ZMPtNG65FfBYM8RwHdS6tY'
                tags = self.peer.unconfirmed_tx(txid)['tags']
                print(txid, tags)
                if any((tag['name'].startswith(b'Bundle') for tag in tags)):
                    try:
                        stream = self.peer.stream(txid)
                    except ArweaveException as exc:
                        #print(exc)
                        missing_txs.add(txid)
                        continue
                    missing_txs.discard(txid)
                    with stream:
                        #header = ANS104Header.from_tags_stream(tags, stream)
                        #header.data = lambda: Bundle.from_tags_stream(tags, stream)# get individual item
                        #yield from Bundle.from_tags_stream(tags, stream).dataitems
                        try:
                            yield from DataItem.all_from_tags_stream(tags, stream)
                        except ArweaveNetworkException as exc:
                            missing_txs.add(Txid)
                            continue
                    #headers = 
                    #print(txid)
            old_block_txs = new_block_txs
            old_pending_txs = new_pending_txs
            now = time.time()
            period = 30
            if mark + period > now:
                time.sleep(mark + period - now)
                mark += period
            else:
                mark = now

for item in BundleWatcher().run():
    print('bundled', item.header.id, item.header.tags)
