import collections

class Cache:
    '''
    Maintains a list of data indexed by integers and bounded in total size.
    Data is removed in an LRU manner by storing indices in an expiry deque.
    '''
    def __init__(self, cache_size, max_idx):
        self.capacity = cache_size
        self.cache = [None] * max_idx
        self.max_idx = max_idx
        self.expiry = collections.deque()
        self._expiry_offset = 0
        self._locked_count = 0
        self.used = 0
    def add(self, idx, size, data, lock=0):
        '''Provide data for an index in the cache.'''
        assert self.cache[idx] is None
        self.ensure(size)
        expiry_idx = len(self.expiry) + self._expiry_offset
        self.expiry.append(idx)
        self.cache[idx] = [data, size, expiry_idx, lock]
        if lock:
            self._locked_count += 1
        self.used += size
        self.fsck()
    #def add_many(self, *idx_size_datas):
    #    total_size = sum([size for idx, size, data, *locked in idx_size_datas])
    #    self.ensure(total_size)
    #    for idx, size, data, locked in idx_size_datas:
    #        assert self.cache[idx] is None
    #        expiry_idx = len(self.expiry) + self._expiry_offset
    #        self.expiry.append(idx)
    #        self.cache[idx] = [data, size, expiry_idx]
    #        self.used += size
    #    self.fsck()
    def ensure(self, size):
        self.fsck()
        while self.used + size > self.capacity and len(self.expiry) > self._locked_count:
            expired = self.expiry[0]
            self._expiry_offset += 1
            if expired is not None:
                data = self.cache[expired]
                if data[3]:
                    self.expiry.rotate(-1)
                    data[2] = len(self.expiry) + self._expiry_offset - 1
                    continue
                self.used -= self.cache[expired][1]
                self.cache[expired] = None
            self.expiry.popleft()
        self.fsck()
    def replace(self, idx, value):
        assert self.cache[idx] is not None
        self.cache[idx][0] = value
    def lock(self, idx, count=1):
        '''
        Locked data will not be evicted from the cache,
        even if the cache is past capacity.
        '''
        locked = self.cache[idx][3]
        if locked == 0:
            self._locked_count += 1
        locked += count
        self.cache[idx][3] = locked
    def unlock(self, idx, count=1):
        locked = self.cache[idx][3]
        assert locked
        locked -= count
        assert locked >= 0
        self.cache[idx][3] = locked
        if locked == 0:
            self._locked_count -= 1
    def peek(self, idx, lock=False):
        data = self.cache[idx]
        if data is None:
            return None
        else:
            if lock:
                self.lock(idx, lock)
            return data[0]
    def access(self, idx, lock=False):
        '''Retrieve data at an index in the cache.'''
        self.fsck()
        data = self.cache[idx]
        if data is not None:
            data_, size, expiry_idx, locked = data
            expiry_idx -= self._expiry_offset
            self.expiry[expiry_idx] = None
            expiry_idx = len(self.expiry) + self._expiry_offset
            data[2] = expiry_idx
            self.expiry.append(idx)
            if lock:
                self.lock(idx, lock)
            data = data_
        self.fsck()
        return data
    def fsck(self):
        ct = 0
        size = 0
        for idx in range(len(self.cache)):
            data = self.cache[idx]
            if data is not None:
                data, data_size, expiry_idx, lock = data
                assert self.expiry[expiry_idx - self._expiry_offset] == idx
                ct += 1
                size += data_size
        assert ct == len(self.expiry) - sum([item is None for item in self.expiry])
        assert size == self.used
        return True

def test():
    cache = Cache(12, 4)
    cache.add(0, b'hello')
    cache.add(1, b'world')
    assert cache._expiry_offset == 0
    cache.add(2, b'it is I') # b'hello' should be kicked out
    assert cache._expiry_offset == 1
    assert list(cache.expiry) == [1,2]
    assert cache.access(1) == b'world' # b'world' should be moved to head
    assert list(cache.expiry) == [None,2,1]
    assert cache._expiry_offset == 1
    cache.add(0, b'hello') # b'it is I' should be kicked out
    assert list(cache.expiry) == [1,0]
    assert cache._expiry_offset == 3

if __name__ == '__main__':
    test()
