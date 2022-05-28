from .peer import Peer
from . import logger

import bisect

class UnboundedStateVector:
    # range: (first, last, state)
    key_low = staticmethod(lambda entry: entry[0])
    key_high = staticmethod(lambda entry: entry[1])
    def __init__(self, other = None):
        self.shadow = other
        self.ranges = []
    def get_idx_around(self, offset):
        right_idx = bisect.bisect_right(self.ranges, offset, key=self.key)
        if right_idx == 0:
            # all entries are after offset
            return None
        elif right_idx == len(self.ranges):
            # all entries are prior to offset
            return None
        else:
            left_idx = right_idx - 1
            return left_idx
    def set_range(self, low, high, state = True):
        # bisect_left  : [keyidx - 1] <  val <= [keyidx]
        #                    [keyidx] >= val >  [keyidx - 1]
        # bisect_right : [keyidx - 1] <= val <  [keyidx]
        #                    [keyidx] >  val >= [keyidx - 1]

        # select highest left_idx such that left_idx low < low
        left_idx = bisect.bisect_left(self.ranges, low, key=self.key_low) - 1
        left_add = ()
        if left_idx < 0:
            replace_low = 0
        else:
            left_low, left_high, left_state = self.ranges[left_idx]
            if left_high >= low:
                replace_low = left_idx
                if left_state == state:
                    low = left_low
                else:
                    # break left apart
                    left_add = ((left_low, low - 1, left_state),)
            else:
                replace_low = left_idx + 1

        # select lowest right_idx such that right_idx high > high
        right_idx = bisect.bisect_right(self.ranges, high, key=self.key_high)
        right_add = ()
        if right_idx == len(self.ranges):
            replace_high = right_idx
        else:
            right_low, right_high, right_state = self.ranges[right_idx]
            if right_low <= high:
                replace_high = right_idx + 1
                if right_state == state:
                    high = right_high
                else:
                    # break right apart
                    right_add = ((high + 1, right_high, right_state),)
            else:
                replace_high = right_idx

        mid_add = ((low, high, state),)

        self.ranges[replace_low:replace_high] = left_add + mid_add + right_add

def test_usv_set_range():
    usv = UnboundedStateVector()
    usv.set_range( 0,10,True)
    usv.set_range(20,30,False)
    usv.set_range(40,50,True)
    usv.set_range(60,70,False)
    usv.set_range(80,90,True)
    assert usv.ranges == [
        ( 0,10,True),
        (20,30,False),
        (40,50,True),
        (60,70,False),
        (80,90,True),
    ]
    usv.set_range(5,25,None)
    assert usv.ranges == [
        ( 0, 4,True),
        ( 5,25,None),
        (26,30,False),
        (40,50,True),
        (60,70,False),
        (80,90,True),
    ]
    usv.set_range(30,40,None)
    assert usv.ranges == [
        ( 0, 4,True),
        ( 5,25,None),
        (26,29,False),
        (30,40,None),
        (41,50,True),
        (60,70,False),
        (80,90,True),
    ]
    usv.set_range(14,31,True)
    assert usv.ranges == [
        ( 0, 4,True),
        ( 5,13,None),
        (14,31,True),
        (32,40,None),
        (41,50,True),
        (60,70,False),
        (80,90,True),
    ]
    usv.set_range(32,40,False)
    assert usv.ranges == [
        ( 0, 4,True),
        ( 5,13,None),
        (14,31,True),
        (32,40,False),
        (41,50,True),
        (60,70,False),
        (80,90,True),
    ]
    usv.set_range(45,75,True)
    assert usv.ranges == [
        ( 0, 4,True),
        ( 5,13,None),
        (14,31,True),
        (32,40,False),
        (41,75,True),
        (80,90,True),
    ]
    usv.set_range(-1,6,None)
    assert usv.ranges == [
        (-1,13,None),
        (14,31,True),
        (32,40,False),
        (41,75,True),
        (80,90,True)
    ]
    usv.set_range(38,91,False)
    assert usv.ranges == [
        (-1,13,None),
        (14,31,True),
        (32,91,False),
    ]

def make_bit_range(low, high):
    '''Returns an integer with bits low through high set, inclusively.'''
    # fill a bit vector of the right length
    set_bits = (1 << ((high+1) - low)) - 1
    # shift it into the right place
    set_bits <<= low
    return set_bits

class ContentTrackedPeer(Peer):
    def __init__(self, *params, **kwparams):
        super().__init__(*params, **kwparams)
        self.chunks_looked = 0
        self.chunks_held = 0

    def has_range(self, first, last):
        chunk_code = make_bit_range(first, last)

        # loop until we have looked at all the requested chunks
        while chunk_code & ~self.chunks_looked:

            # find needed offsets by masked with unlooked
            mask = chunk_code & ~self.chunks_looked
            # pick out lowest bit by and'ing with twos complement
            mask &= -mask
            # convert from bit code to smallest new offset
            start_offset = mask.bit_length() - 1

            records = self.data_sync_record(start = start_offset)
            expected_offset = start_offset

            for high_offset, low_offset in records[::-1]:
                if expected_offset < low_offset:
                    # set the skipped range as missing
                    self.chunks_looked |= make_bit_range(expected_offset, low_offset - 1)

                # set the found range as held
                set_bits = make_bit_range(low_offset, high_offset)
                self.chunks_looked |= set_bits
                self.chunks_held |= set_bits

                # look for the next skipped range
                expected_offset = high_offset + 1

        return chunk_code | ~self.chunks_held == 0

def wrap_txid(callable):
    def wrapped(self, txid, *params, **kwparams):
        peer = self.tx_peer(txid)
        return callable(peer, txid, *params, **kwparams)
    wrapped.__name__ = callable.__name__
    return wrapped
def wrap_offset(callable):
    def wrapped(self, offset, *params, **kwparams):
        peer = self.chunk_peer(offset)
        return callable(peer, offset, *params, **kwparams)
    wrapped.__name__ = callable.__name__
    return wrapped

class MultiPeer:
    def __init__(self, initial_peers = None):
        if initial_peers is None:
            initial_peers = [origin['endpoint'].split('://',1)[1] for origin in Peer().health()['origins']]
        self.peer_queue = set(initial_peers)
        self.peers = []
        self.chunks_indexed = 0
    def chunk_peer(self, offset, size=1):
        first = offset
        last = first + size - 1
        for idx, peer in enumerate(self.peers):
            if peer.has_range(first, last):
                self.peers = [peer] + self.peers[:idx] + self.peers[idx+1:]
                logger.info(f'I have a peer with this content. Returning {peer.api_url}.')
                return peer
        while True:
            if not len(self.peer_queue):
                peer_queue.update(self.peers[0].peers())
            peer = ContentTrackedPeer('http://' + self.peer_queue.pop())
            if peer.has_range(first, last):
                try:
                    peer.chunk2((first+last)//2)
                except:
                    pass
                else:
                    self.peers[:0] = peer
                    logger.info(f'I found that {peer.api_url} has this content. Added to peer list and returning.')
                    return peer
            else:
                logger_info(f'I checked {peer.api_url} but they did not have the content. Moving on ...')
    def tx_peer(self, txid):
        txoffset = self.tx_offset(txid)
        last = txoffset['offset']
        size = txoffset['size']
        first = last - size + 1
        return self.chunk_peer(first, size)

    def peers(self):
        return [peer.api_url.split('://',1)[1] for peer in self.peers[:16]]

    tx = wrap_txid(Peer.tx)
    tx2 = wrap_txid(Peer.tx2)
    tx_data_html = wrap_txid(Peer.tx_data_html)
    chunk = wrap_offset(Peer.chunk)
    chunk2 = wrap_offset(Peer.chunk2)
    chunk_size = wrap_offset(Peer.chunk_size)
    tx_offset = wrap_txid(Peer.tx_offset)
    tx_field = wrap_txid(Peer.tx_field)
    data = wrap_txid(Peer.data)
    stream = wrap_txid(Peer.stream)
    peer_stream = wrap_txid(Peer.peer_stream)

    
    def __getattr__(self, attr):
        if not len(self.peers):
            peer = self.chunk_peer(1)
        else:
            peer = self.peers[0]
        return getattr(peer, attr)

if __name__ == '__main__':
    test_usv_set_range()
    import ar.multipeer
    peer = ar.multipeer.MultiPeer()
    peer.chunk2(12168648941376)
