import array,mmap,struct

UINT = { 8:'B',16:'H',32:'L',64:'Q' }
SINT = { 8:'b',16:'h',32:'l',64:'q' }

class Memory:
    def __init__(self, fn):
        self.fh = open(fn, 'r+b')
        self._create_mm()
        self.regions = [
            self.Region(
                self,
                idx,
                self.view[self.hdr[1][idx]:self.hdr[1][idx+1]]
            )
            for idx in range(0,self.hdr[0][0])
        ]
    @classmethod
    def create(cls, fn, *buffersizes):
        hdr = array.array(UINT[64], [len(buffersizes),0]+buffersizes)
        for idx in range(1,len(buffersizes)+1):
            hdr[idx+1] += hdr[idx]
        hdr[0] = len(buffersizes)
        with open(fn, 'wb') as fh:
            hdr.tofile(fh)
            fh.truncate(fh.tell() + sum(buffersizes))
        return cls(fn)
    def resize_region(self, region_idx, new_size):
        region = self.regions[region_idx]
        size_diff = new_size - len(region.view)
        if size_diff > 0:
            # copy data forward
            self.fh.truncate(self.hdr[1][-1] + new_size - len(region.view))
            self._create_mm()
            for idx in range(region_idx):
                self.regions[idx]._reseat(self.view[self.hdr[1][idx]:self.hdr[1][idx+1]])
            for idx in range(len(self.regions)-1, region_idx, -1):
                off1 = self.hdr[1][idx]
                off2 = self.hdr[1][idx+1]
                self.hdr[1][idx+1] += size_diff
                self.view[off1+size_diff:off2+size_diff] = self.view[off1:off2]
                self.regions[idx]._reseat(self.view[off1+size_diff:off2+size_diff])
            self.hdr[1][region_idx+1] += size_diff
            regions[region_idx]._reseat(self.view[self.hdr[1][region_idx]:self.hdr[1][region_idx+1]])
        elif size_diff < 0:
            # move data backward
            region._reseat(region.view[:new_size])
            for idx in range(region_idx+1, len(self.regions)):
                off1 = self.hdr[1][idx]
                off2 = self.hdr[1][idx]
                self.hdr[1][idx] += size_diff
                self.view[off1+size_diff:off2+size_diff] = self.view[off1:off2]
                self.regions[idx]._reseat(self.view[off1+size_diff:off2+size_diff])
            self.hdr[1][len(self.regions)] += size_diff
            self.fh.truncate(self.hdr[1][len(self.regions)]
    class Region:
        def __init__(self, memory, idx, view):
            self.outer = memory
            self.idx = idx
            self.view = view
            self.composers = []
        def add_composer(self, composer):
            self.composers.append(composer)
        def resize(self, new_size):
            self.outer.resize_region(idx, new_size)
        def _reseat(self, view):
            self.view = view
            for composer in self.composers:
                composer._reseat(self)
    def _create_mm(self):
        self.mm = mmap.mmap(self.fh)
        self.view = memoryview(mm)
        view32 = self.view.cast(UINT[32])
        self.hdr = [view32[:1], view32[1:view32[0]+2]]

class MemoryBackedArray:
    def __init__(self, region, dtype):
        self.dtype = dtype
        self._reseat(region)
    def _reseat(self, region):
        self.region = region
        self.view = region.view.cast(self.dtype)
    def resize(self, new_size):
        self.region.resize(new_size * self.view.itemsize)
    def __len__(self):
        return len(self.view)
    def __iter__(self):
        return iter(self.view)
    def __getitem__(self,idx):
        return self.view[idx]
    def __setitem__(self,idx,val):
        self.view[idx]=val

class MemoryBackedDeque(MemoryBackedArray):
    def __init__(self, region, dtype=UINT[32]):
        super().__init__(region, dtype)
        self._hi = 0
        self._lo = 0
    def append(self, val):
        newhi = (self._hi + 1) % len(self.view)
        if newhi == self._lo:
            self._grow()
            newhi = (self._hi + 1) % len(self.view)
        self.view[newhi] = val
    def appendleft(self, val):
        newlo = (self._lo - 1) % len(self.view)
        if newlo == self._hi:
            self._gro()
            newlo = (self._lo - 1) % len(self.view)
        self.view[newlo] = val
    def pop(self):
        if self._lo == self._hi:
            raise IndexError('pop from an empty deque')
        val = self.view[self._hi]
        self._hi = (self._hi - 1) % len(self.view)
        return val
    def popleft(self):
        if self._lo == self._hi:
            raise IndexError('pop from an empty deque')
        val = self.view[self._lo]
        self._lo = (self._lo + 1) % len(self.view)
        return val
    def _grow(self):
        oldsize = len(self.view)
        newsize = oldsize * 2
        growth = newsize - oldsize
        super().resize(newsize)
        if self._hi < self._lo:
            self.view[self._lo+growth:] = self.view[self._lo:oldsize]
            self._lo += growth

import numpy
class MemoryBackedNumpy:
    def __init__(self, region, shape, dtype=numpy.float32):
        self._numpy = numpy.ndarray(shape, dtype, region.view)
        self.region = region
    def _reseat(self, region):
        self.region = region
        self._numpy = numpy.ndarray(self._numpy.shape, self._numpy.dtype, region.view)
    def resize(self, new_shape):
        new_size = self.itemsize
        min_shape = list(new_shape)
        for dim in new_shape:
            new_size *= dim
            min_shape = self.
        self.region.resize(new_size)
        old_numpy = self._numpy
        self._numpy = numpy.ndarray(new_shape, self._numpy.dtype, self.region.view)
        
class MemoryBackedListOfArray:
    def __init__(self, region, dtype, itemsize):
        self.region = region
        self.dtype = dtype
        self.itemsize = itemsize
        self._reseat(region)
    def _reseat(self, region):
        self.view = region.view.cast(self.array_dtype)
