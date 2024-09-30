import time

from ar import Peer, ArweaveNetworkException, ArweaveException, ANS104BundleHeader, ANS104DataItemHeader, Bundle, DataItem
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
                tx = self.peer.unconfirmed_tx(txid)
                tags = tx['tags']
                #print(txid, tags)
                if any((tag['name'].startswith(b'Bundle') for tag in tags)):
                    #print(txid, tags)
                    try:
                        stream = self.peer.stream(txid,reupload=False)
                    except ArweaveException as exc:
                        print(exc)
                        missing_txs.add(txid)
                        continue
                    except Exception as exc:
                        print(exc)
                        raise
                    missing_txs.discard(txid)
                    with stream:
                        #header = ANS104BundleHeader.from_tags_stream(tags, stream)
                        #header.data = lambda: Bundle.from_tags_stream(tags, stream)# get individual item
                        #yield from Bundle.from_tags_stream(tags, stream).dataitems
                        try:
                            for ditem_data in ANS104DataItemHeader.all_from_tags_stream(tags, stream):
                                yield tx, *ditem_data
                        #    yield from ANS104DataItemHeader.all_from_tags_stream(tags, stream)
                        #    yield from DataItem.all_from_tags_stream(tags, stream)
                        except ArweaveNetworkException as exc:
                            print('pending tx cause of', exc)
                            missing_txs.add(txid)
                            continue
                    #headers = 
                    #print(txid)
            old_block_txs = new_block_txs
            old_pending_txs = new_pending_txs
            now = time.time()
            period = 30
            if mark + period > now:
                print('sleeping for', mark + period - now, 'seconds')
                time.sleep(mark + period - now)
                mark += period
            else:
                mark = now

for bundle, ditem, stream, offset, length in BundleWatcher().run():
    print('bundled', ditem.id, ditem.tags)
