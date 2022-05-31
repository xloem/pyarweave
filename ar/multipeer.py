from .peer import Peer
from . import logger

import bisect

class IntervalVector:
    # range: (first, last, state)
    key_low = staticmethod(lambda entry: entry[0])
    key_high = staticmethod(lambda entry: entry[1])
    def __init__(self, ranges = [], low = -float('inf'), high = float('inf')):
        self.low = low
        self.high = high
        self.ranges = ranges
    #def get_idx_around(self, offset):
    #    right_idx = bisect.bisect_right(self.ranges, offset, key=self.key)
    #    if right_idx == 0:
    #        # all entries are after offset
    #        return None
    #    elif right_idx == len(self.ranges):
    #        # all entries are prior to offset
    #        return None
    #    else:
    #        left_idx = right_idx - 1
    #        return left_idx
    def __eq__(self, other):
        if type(other) is self.__class__:
            return self.low == other.low and self.high == other.high and self.ranges == other.ranges
        else:
            return self.ranges == [(
                (self.low, self.high, other)
            )]
    # UNLIKE USUAL PYTHON THESE ARE INCLUSIVE OF THE UPPER BOUND
    def __getitem__(self, idx):
        if type(idx) is slice:
            low = idx.start if idx.start is not None else self.low
            high = idx.stop if idx.stop is not None else self.high
            return self.range(low, high)
        else:
            part = self.range(idx, idx)
            return part.ranges[0][-1]
    def __setitem__(self, idx, state):
        if type(idx) is slice:
            low = idx.start if idx.start is not None else self.low
            high = idx.stop if idx.stop is not None else self.high
            self.set_range(low, high, state)
        else:
            self.set_range(idx, idx, state)
    def __contains__(self, state):
        return any((state == interval[-1] for interval in self.ranges))
    # bisect_left  : [keyidx - 1] <  val <= [keyidx]
    #                    [keyidx] >= val >  [keyidx - 1]
    # bisect_right : [keyidx - 1] <= val <  [keyidx]
    #                    [keyidx] >  val >= [keyidx - 1]
    def lowest_gap(self, low = None, high = None, lo_bound=0, hi_bound=None):
        '''returns the lowest non-accounted-for offset'''
        # we are looking for gap
        # so we'll be starting with the first overlap
        # and walking right
        # that's how to find first gap in nonoverlapping intervals, unless there is index
        # let's copy range code for consistency, since so confusedish

        low = self.low if low is None else low
        high = self.high if high is None else high

        # lowest interval_such that high >= low 
        idx = bisect.bisect_left(self.ranges, low, key=self.key_high, lo=lo_bound, hi=hi_bound)
        while idx < len(self.ranges) and low <= high:
            idx_low, idx_high, _ = self.ranges[idx]
            if idx_low > low:
                return low
            low = idx_high + 1
            idx += 1
        if low <= high:
            return low
        else:
            return None
    def highest_gap(self, low = None, high = None, lo_bound=0, hi_bound=None):
        '''returns the highest non-accounted-for offset'''
        low = self.low if low is None else low
        high = self.high if high is None else high

        # highest interval_such that low <= high
        idx = bisect.bisect_right(self.ranges, high, key=self.key_low, lo=max(lo_bound, first), hi=hi_bound) - 1
        while idx >= 0 and high >= low:
            idx_low, idx_high, _ = self.ranges[idx]
            if idx_high < high:
                return high
            high = idx_low - 1
            idx -= 1
        if high >= low:
            return high
        else:
            return None
        
    def range(self, low, high, lo_bound=0, hi_bound=None):
        # lowest interval_high >= low 
        first = bisect.bisect_left(self.ranges, low, key=self.key_high, lo=lo_bound, hi=hi_bound)
        # highest interval_low <= high
        last = bisect.bisect_right(self.ranges, high, key=self.key_low, lo=max(lo_bound, first), hi=hi_bound) - 1

        portion = self.ranges[first:last+1]
        if len(portion):
            first_low, first_high, first_state = portion[0]
            if first_low < low:
                portion[0] = (low, first_high, first_state)
            last_low, last_high, last_state = portion[-1]
            if last_high > high:
                portion[-1] = (last_low, high, last_state)
        return self.__class__(portion, low=low, high=high)

    def set_range(self, low, high, state = True, lo_bound=0, hi_bound=None):
        # this could probably be simplified by copying range()'s approach

        # select highest left_idx such that left_idx low < low
        left_idx = bisect.bisect_left(self.ranges, low, key=self.key_low, lo=lo_bound, hi=hi_bound) - 1
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
        right_idx = bisect.bisect_right(self.ranges, high, key=self.key_high, lo=max(lo_bound,left_idx), hi=hi_bound)
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

def test_usv_range():
    usv = IntervalVector()
    usv.set_range( 0,10,True)
    usv.set_range(20,30,False)
    usv.set_range(40,50,True)
    usv.set_range(60,70,False)
    usv.set_range(80,90,True)
    assert usv.range(5,45) == IntervalVector([
        ( 5,10,True),
        (20,30,False),
        (40,45,True)
    ], 5, 45)
    assert usv.range(41,49) == IntervalVector([
        (41,49,True)
    ], 41, 49)
    assert usv.range(-5,5) == IntervalVector([
        ( 0, 5,True)
    ], -5, 5)
    assert usv.range(65,95) == IntervalVector([
        (65,70,False),
        (80,90,True),
    ], 65, 95)
    assert usv.range(35,55) == IntervalVector([
        (40,50,True),
    ], 35, 55)

def test_usv_set_range():
    usv = IntervalVector()
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

class ContentTrackedPeer(Peer):
    def __init__(self, *params, **kwparams):
        super().__init__(*params, **kwparams)
        self.chunks = IntervalVector()
        #self.chunks_held = IntervalVector()

    def has_range(self, first, last):
        lowest_gap = self.chunks.lowest_gap(low=first, high=last)
        while lowest_gap is not None:
            records = self.data_sync_record(start = lowest_gap, limit=1000)
            if not len(records):
                self.chunks[lowest_gap:last] = False
                break
            expected_offset = lowest_gap
            for high_offset, low_offset in records[::-1]:
                if expected_offset < low_offset:
                #    # set the skipped range as missing
                #    self.chunks_looked |= make_bit_range(expected_offset, low_offset - 1)
                    self.chunks[expected_offset : low_offset - 1] = False

                # set the found range as held
                self.chunks[low_offset : high_offset] = True
        #        set_bits = make_bit_range(low_offset, high_offset)
        #        self.chunks_looked |= set_bits
        #        self.chunks_held |= set_bits

                # look for the next skipped range
                expected_offset = high_offset + 1
            lowest_gap = self.chunks.lowest_gap(low=expected_offset, high=last)
        return self.chunks[first:last] == True

        #return chunk_code | ~self.chunks_held == 0
        #chunk_code = make_bit_range(first, last)
        #chunk_interval = IntervalVector([(first, last, True)])

        ## loop until we have looked at all the requested chunks
        #while chunk_code & ~self.chunks_looked:

        #    # find needed offsets by masked with unlooked
        #    mask = chunk_code & ~self.chunks_looked
        #    # pick out lowest bit by and'ing with twos complement
        #    mask &= -mask
        #    # convert from bit code to smallest new offset
        #    start_offset = mask.bit_length() - 1

        #    records = self.data_sync_record(start = start_offset)
        #    expected_offset = start_offset

        #    for high_offset, low_offset in records[::-1]:
        #        if expected_offset < low_offset:
        #            # set the skipped range as missing
        #            self.chunks_looked |= make_bit_range(expected_offset, low_offset - 1)

        #        # set the found range as held
        #        set_bits = make_bit_range(low_offset, high_offset)
        #        self.chunks_looked |= set_bits
        #        self.chunks_held |= set_bits

        #        # look for the next skipped range
        #        expected_offset = high_offset + 1

        #return chunk_code | ~self.chunks_held == 0

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
            initial_peers = []
            self.protected_peers = set(origin['endpoint'].split('://',1)[1] for origin in Peer().health()['origins'])
            initial_peers = set(self.protected_peers)
        else:
            self.protected_peers = set()
        self.backup_peer_queue = set()
        self.peer_queue = set(initial_peers)
        self.peers = []
    def chunk_peer(self, offset, size=1):
        first = offset
        last = first + size - 1
        for idx, peer in enumerate(self.peers):
            if peer.has_range(first, last):
                self.peers = [peer] + self.peers[:idx] + self.peers[idx+1:]
                logger.info(f'I have a peer with this content. Returning {peer.api_url}.')
                return peer
        uninteresting_peers = set()
        # there may be a better way to do this to ensure that all peers are enumerated.
        while True:
            if not len(self.peer_queue):
                if not len(self.peers):
                    self.peer_queue = self.backup_peer_queue.difference(uninteresting_peers)
                    self.backup_peer_queue = set()
                else:
                    self.peer_queue.update(set(self.peers[0].peers()).difference(uninteresting_peers))
            if not len(self.peer_queue):
                self.backup_peer_queue = uninteresting_peers
                return None
            peer_addr = self.peer_queue.pop()
            peer = ContentTrackedPeer('http://' + peer_addr, timeout = 1, retries = 0)
            try:
                has_content = peer.has_range(first, last)
                if has_content:
                    if peer_addr in self.protected_peers:
                        logger.info(f'I found that {peer.api_url} has this content but the peer is protected. Moving on ...')
                        self.backup_peer_queue.add(peer_addr)
                        self.peer_queue.update(set(peer.peers()).difference(uninteresting_peers))
                        continue
                    peer.chunk2((first+last)//2)
                    self.peers[:0] = [peer]
                    logger.info(f'I found that {peer.api_url} has this content. Added to peer list and returning.')
                    return peer
                logger.info(f'I checked {peer.api_url} but they did not have the content. Moving on ... {len(self.peer_queue)}')
                if peer_addr not in self.protected_peers:
                    uninteresting_peers.add(peer_addr)
                if not len(self.peers):
                    try:
                        more_peers = set(peer.peers()).difference(uninteresting_peers)
                        self.backup_peer_queue.update(more_peers)
                    except:
                        pass
            except Exception as exc:
                logger.info(f'{peer.api_url} raised {exc}. Moving on ...')
    def tx_peer(self, txid):
        if not len(self.peers):
            #peer = Peer().current_block()['height']#self.chunk_peer(1)
            txoffset = Peer().tx_offset(txid)
        else:
            #peer = self.peers[0]
            txoffset = self.peers[0].tx_offset(txid)
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
    import logging
    logging.basicConfig(level=logging.INFO)
    test_usv_range()
    test_usv_set_range()
    import ar.multipeer
    peer = ar.multipeer.MultiPeer()
    peer.tx_peer('9yMhEpVzxdR606es3G6fjZITK488x8Hr7Qb3pJ1GIaM')
    peer.chunk2(12168648941376)