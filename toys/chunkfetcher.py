import ar

import bisect, random, threading, time

class ChunkRecordPeer:
    # the arweave data sync record is returned high-first
    def __init__(self, peer, min=None, max=None):
        self.peer = peer
        self._min = min
        self._max = max
        self._lock = threading.Lock()
        self._timestamp = 0
    def _fetch_1_dsr(self, offset):
        # bisect works more simply on things that are storted left-to-right and do not contain tuples
        return [
            [low+1, high]
            for high, low
            in self.peer.data_sync_record(offset, None, 'etf')
        ][::-1]
    def _update_dsr(self, now):
        # looks like peers might randomly filter this content
        # to make it more robust, dropped intervals could be checked via a request
        # of course, strange results may return from load-balancing proxies
            # maybe it would make more sense to just query chunks from peers in random order or such
        with self._lock:
            start = self._min
            full_dsr = self._fetch_1_dsr(start)
            while full_dsr[-1][1] < self._max:
                #import pdb; pdb.set_trace()
                assert sorted(full_dsr) == full_dsr
                more_dsr = self._fetch_1_dsr(random.randint(full_dsr[-2][0], full_dsr[-1][1]))
                assert sorted(more_dsr) == more_dsr
                full_dsr.extend([
                    interval
                    for interval in more_dsr
                    if interval[0] > full_dsr[-1][0]
                ])
            self._max = full_dsr[-1][1]
            self._ordered_data_sync_record = full_dsr
        self._timestamp = now
    def has_chunk(self, offset):
        if None in [self._min, self._max] or offset < self._min or offset > self._max:
            with self._lock:
                if self._min is None or offset < self._min:
                    self._min = offset
                    if self._max is None or offset > self._max:
                        self._max = offset
                    self._timestamp = 0
                elif self._max is None or offset > self._max:
                    self._max = offset
                    self._timestamp = 0
        dsr = self.ordered_data_sync_record
        idx = bisect.bisect(dsr, [offset, self._max+1])
        if idx == 0:
            return False
        return offset <= dsr[idx-1][1]
    @property
    def min(self):
        return self._min
    @property
    def max(self):
        return self._max
    @property
    def ordered_data_sync_record(self):
        if not self._lock.locked():
            now = time.time()
            if now - self._timestamp > 30:
                self._update_dsr(now) # ideally done in bg when min/max unchanged
        return self._ordered_data_sync_record

class ChunkFetcher:
    def __init__(self, peers, min_offset=None, max_offset=None):
        if type(peers) is int:
            peers = ar.PUBLIC_GATEWAYS[:peers]
        self.peers = [
            ChunkRecordPeer(
                ar.Peer(peer)
                    if type(peer) is str
                    else peer,
                min = min_offset,
                max = max_offset,
            )
            for peer in peers
        ]
        #self._peer_lock = threading.Lock()
        #self._peer_idx = 0
    def iter_peers(self):
        peers = list(self.peers)
        random.shuffle(peers)
        return peers
        #with self._peer_lock:
        #    idx0 = self._peer_idx
        #    self._peer_idx = idx0 + 1
        #for idx1 in range(len(self.peers)):
        #    idx = (idx0 + idx1) % len(self.peers)
        #    yield self.peers[idx]
    def pick_peer(self):
        return random.choice(self.peers)
        #for peer in self.iter_peers():
        #    return peer
    def chunk2(self, offset):
        while True:
            for peer in self.iter_peers():
                if peer.has_chunk(offset):
                    return peer.peer.chunk2(offset)
            for ct in range(8):
                for peer in self.iter_peers():
                    try:
                        result = peer.peer.chunk2(offset)
                        peer._update_dsr(time.time())
                        return result
                    except:
                        pass
            else:
                raise ValueError('no peers in this set advertise having this chunk')
