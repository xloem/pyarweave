import time

import json

from ar import Peer, ArweaveNetworkException, ArweaveException, ANS104BundleHeader, Bundle, DataItem
from bundlr import Node
from ar.utils import tags_to_dict

def getwinsz():
    import sys, struct, fcntl, termios
    
    s = struct.pack('HHHH', 0, 0, 0, 0)
    t = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, s)
    height_chars, width_chars, width_px, height_px = struct.unpack('HHHH', t)
    return width_chars, height_chars

class BundleWatcher:
    def __init__(self, peer = Peer(timeout=1), height = None):
        self.peer = peer
        self.height = height
        self.known = {}
        print(end='\x1b[H\x1b[J') # clear screen
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
                tags = tags_to_dict(tags)
                app = None
                def tags2app(tags):
                    for applabel in (form for label in 'Application App-Name App User-Agent Type Content-Type'.split(' ') for form in (label, label.lower())):
                        applabel = applabel.encode()
                        if applabel in tags:
                            return tags.pop(applabel).decode() + '-' + str(len(tags))
                app = tags2app(tags)
                if app == 'application/json-0' or (app is None and len(tags) == 0):
                    try:
                        bin = self.peer.data(txid)
                    except:
                        #missing_txs.add(txid)
                        continue
                    try:
                        txt = bin.decode()
                        try:
                            j = json.loads(txt)
                            app2 = tags2app(j.items())
                            if app2 is not None:
                                app = app2
                        except:
                            pass
                        if app is None:
                            app = txt
                    except:
                        app = 'application/octet-stream-' + str(len(tags))
                if app is None:
                    app = ';'.join(f'{key.decode()}:{value.decode()}' for key, value in tags.items())
                if app not in self.known:
                    self.known[app] = (1, txid, tags)
                else:
                    self.known[app] = (self.known[app][0] + 1, txid, tags)
                print(end='\x1b[H') # cursor to top left of screen
                items = list(self.known.items())
                items.sort(key=lambda item: item[1][0], reverse=True)
                width, height = getwinsz()
                for app, (count, txid, tags) in items[:height]:
                    line = f'{count} {app.rsplit("-",1)[0][:32]} {txid} {tags}'[:width]
                    print(line, end='\x1b[K\n') # clear rest of line
                print(flush=True, end='\x1b[J') # clear rest of screen
                #print(txid, tags)
                #if any((tag['name'].startswith(b'Bundle') for tag in tags)):
                #    try:
                #        stream = self.peer.stream(txid)
                #    except ArweaveException as exc:
                #        #print(exc)
                #        missing_txs.add(txid)
                #        continue
                #    missing_txs.discard(txid)
                #    with stream:
                #        #header = ANS104Header.from_tags_stream(tags, stream)
                #        #header.data = lambda: Bundle.from_tags_stream(tags, stream)# get individual item
                #        #yield from Bundle.from_tags_stream(tags, stream).dataitems
                #        try:
                #            yield from DataItem.all_from_tags_stream(tags, stream)
                #        except ArweaveNetworkException as exc:
                #            missing_txs.add(Txid)
                #            continue
                #    #headers = 
                #    #print(txid)
            old_block_txs = new_block_txs
            old_pending_txs = new_pending_txs
            now = time.time()
            period = 5
            if mark + period > now:
                time.sleep(mark + period - now)
                mark += period
            else:
                mark = now

for item in BundleWatcher().run():
    print('bundled', item.header.id, item.header.tags)
