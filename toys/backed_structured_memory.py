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

import numpy as _np
class MemoryBackedNumpy:
    def __init__(self, region, shape, dtype=numpy.float32):
        self.region = region
        self.np = _np.ndarray(shape, dtype, region.view)
    def _reseat(self, region):
        self.region = region
        self.np = _np.ndarray(self.np.shape, self.np.dtype, region.view)
    def resize(self, new_shape):
        new_size = self.itemsize
        for dim in new_shape:
            new_size *= dim
        shared_slice = (
            slice(None,min(new_shape[dim],self.np.shape[dim]))
            for dim in range(min(len(new_shape),len(self.np.shape)))
        )
        if new_size < len(self.region.view):
            new_np = _np.ndarray(new_shape, self.np.dtype, self.region.view)
            new_np[shared_slice] = self.np[shared_slice]
            self.region.resize(new_size)
        elif new_size > len(self.region.view):
            self.region.resize(new_size)
            new_np = _np.ndarray(new_shape, self.np.dtype, self.region.view)
            new_np[shared_slice] = self.np[shared_slice]
        self.np = new_np

import collections.abc
class MemoryBackedFixedArrayList(collections.abc.MutableSequence):
    def __init__(self, region, fixedsize, dtype='B'):
        self.region = region
        self.dtype = dtype
        self.fixedsize = fixedsize
        self._list = []
    def resize_fixed(self, new_fixedsize):
        if new_fixedsize < self.fixedsize:
            offset = 0
            for row in self._list:
                next_offset = offset + new_fixedsize
                self._view[offset : next_offset] = row[:new_fixedsize]
                offset = next_offset
            self.fixedsize = new_fixedsize
            self.region.resize(offset)
        elif new_fixedsize > self.fixedsize:
            offset = len(self.view)
            old_fixedsize = self.fixedsize
            self.fixedsize = new_fixedsize
            self.region.resize(new_fixedsize * len(self._list))
            for new_row in self._list[::-1]:
                prev_offset = offset - old_fixedsize
                new_row[:] = self._view[offset : prev_offset]
    def _reseat(self, region):
        self._view = region.view.cast(self.dtype)
        size = len(self._view)
        assert size % self.fixedsize == 0
        self._list[:] = [
            self._view[idx : idx + self.fixedsize]
            for idx in range(0, size, self.fixedsize)
        ]
        self._len = size // self.fixedsize
    def __getitem__(self, idx):
        return self._list[idx]
        #return self.view[idx * self.fixedsize]
    def __len__(self):
        return len(self._list)
    def __setitem__(self, idx, row):
        self._list[idx][:] = row
    def __delitem__(self, idx):
        #if type(idx) is not slice:
        #    idx = slice(idx)
        # slices aren't hard just take a little time
        self.view[idx * self.fixedsize:] = self.view[(idx+1) * self.fixedsize:]
        self.region.resize((len(self) - 1) * self.fixedsize)
    def insert(idx, row):
        self.region.resize((len(self) + 1) * self.fixedsize)
        self.view[(idx+1) * self.fixedsize:] = self.view[idx * self.fixedsize:]
        self._list[idx][:] = row
    def clear(self):
        self.region.resize(0)
    def extend(self, rows):
        self.region.resize(len(self._view) + self.fixedsize * len(rows))
        for idx in range(len(rows)):
            self._list[-len(rows)+idx][:] = rows[idx]

#class MemoryBackedFixedArrayDict:
#    HASH_BYTES = 8
#    HASH_BITS = HASH_BYTES * 8
#    #EMPTY = 0
#    #EMPTY_SUBSTITUTE = ((1<<HASHBITS)-1)^EMPTY
#
#    # proposal for empty hash structure
#    # up link and down link, first 32 bits have 31 bits being one, second 32 bits have the other
#    # 1 bit on each side is either is-empty flag or the there-is-no-up-or-down-link flag
#    # this extra bit can be extracted in a bytewise manner or a bitwise manner
#    # if the values are stored little-endian, then the highest bit is the 0x80 bit of the rightmost byte
#    LINK_BITS = 32
#    LINK_FLAG_BYTE = 3
#    LINK_FLAG_BYTE_BIT = 0x80
#
#    _LINK_BYTES = 4
#    _FLAG_BIT = LINK_BYTES * 8
#    _LINK_BITS = _FLAG_BIT - 1
#    _LINK_MAX = (1 << _LINK_BITS) - 1
#    _FLAG_MASK = 1 << (_FLAG_BIT - 1)
#
#    _D_OFF = 0
#    _U_OFF = _LINK_BYTES
#    _D_END = _D_OFF + _LINK_BYTES
#    _U_END = _U_OFF + _LINK_BYTES
#    _D_SHIFT = 1 << (_D_OFF * 8)
#    _U_SHIFT = 1 << (_U_OFF * 8)
#    _D_MASK = _LINK_MAX
#    _U_MASK = _LINK_MAX << _U_SHIFT
#    _E_MASK = _FLAG_MASK
#    _C_MASK = _FLAG_MASK << _U_SHIFT
#    _F_MASK = _E_MASK | _C_MASK
#
#    def __init__(self, region, fixedsize, dtype='B'):
#        # this implementation is a little simple due to cognitive struggles during design
#        # key hash collisions are not detected
#        self._list = MemoryBackedFixedArrayList(region, fixedsize, 'B')
#        self._dtype = dtype
#        #self._hashsize = self.HASHBITS // 8 // self._list.view.itemsize
#        self._count = 0
#        for idx in range(len(self._list._list)):
#            entry, full, short = self._entry_hash(idx)
#            if full != self.EMPTY:
#                self._count += 1
#    def _reseat(sef, region):
#        self._list.reseat(region)
#        self._hashed_entries = [
#            [row[:self.HASHBYTES], 
#            for row in self._list._list
#        ]
#        self._entries = [
#            row[self.HASHBYTES:].cast(self._dtype)
#            for row in self._list._list
#        ]
#    def _key_hash(self, key, size=None):
#        if size is None:
#            size = len(self._list._list)
#        full = hash(key)
#        if full == self.EMPTY:
#            full = self.EMPTY_SUBSTITUTE
#        short = full % size
#        return [full, short]
#    def _entry_hash(self, idx, size=None):
#        if size is None:
#            size = len(self._list._list)
#        hash, entry = [self._hashes[idx], self._entries[idx]]
#        full = int.from_bytes(hash, 'little')
#        
#        short = full % size
#        return [hash, entry, full, short]
#
#    # i left off adding links to empty fields
#    # that could provide for near-constant lookup time
#    # without adding more metadata space.
#    # empty rows use their hash to link to adjacent filled rows,
#    # then a binary search would be used if a hash lookup misses.
#
#    def _set_cleared(self):
#        # - when structure is entirely empty, if sized, rows must all effectively have unique constant value
#        cleared_hash = (self._EMPTY_FLAG | self._CLEAR_FLAG).tobytes(self.HASHBYTES,'little')
#        for hash in self._hashes:
#            hash[:] = cleared_hash
#    #def _set(self, entry, mask, val):
#    #
#    def _fill_entry(self, idx, hash, entry):
#        # - when an item is added to or removed from the structure, rows surrounding it must be filled
#        #l = self._list._list
#        size = len(self._hashes)
#        cur = int.from_bytes(self._hashes[idx], 'little')
#        assert cur & self._F_MASK == self._E_MASK
#        assert hash & self._F_MASK == 0
#        d_link = idx - ((cur & self._D_MASK) >> self._D_SHIFT)
#        u_link = idx + ((cur & self._U_MASK) >> self._U_SHIFT)
#        for d_idx in range(d_link + 1, idx):
#            # change the up link to idx
#            # this could be faster with identical absolute indices assigned to a strided memoryview,
#            #  in which case high bits could be asserted to match
#            # if the assert were hit the data could be rebalanced and/or resized
#            d_u_link = idx - d_idx
#            assert d_u_link <= self._LINK_MAX
#            self._hashes[d_idx%size][self._U_OFF:self._U_END] = d_u_link.to_bytes(self._LINK_BYTES, 'little')
#        for u_idx in range(idx + 1, u_link):
#            # change the down link to idx
#            u_d_link = u_idx - idx
#            assert u_d_link < self._LINK_MAX
#            self._hashes[u_idx%size][self._D_OFF:self._D_END] = u_d_link.to_bytes(self._LINK_BYTES, 'little')
#        self._hashes[idx][:] = hash.to_bytes(self._HASH_BYTES, 'little')
#        if entry is not None:
#            self._entries[idx][:] = entry
#    def _find(self, key):
#            # - to find an item, o(1) hash indexing is used as a hint for o(log(n)) bisection
#        size = len(self._list._list)
#        size2 = size // 2
#        assert size2 * 2 == size
#        k_hash, k_hint = self._key_hash(key, size)
#        # ok so this may not work but one idea is to pass a custom key operator to bisect.bisect.
#        # the key operator says what to compare.
#        # so a question is, what should entries in the middle be compared as?
#            # i guess the entry that is farther from where the needles goes. this leaves most things nearest to their guess.
#                # let's create a list of idcs for now :s
#        idcs = list(range(size))
#        def key(idx):
#            if idx is None:
#                return k_hash
#            hash = int.from_bytes(self._hashes[idx], 'little')
#            if hash & self._E_MASK:
#                if not hash & self._C_MASK:
#                    # return the one of ulink and dlink that are farther from hint
#                    # the ulink and link are relative offsets, making an extra lookup, but this is the fallback operation anyway
#                    u_idx = (idx + ((hash & self._U_MASK) >> self._U_SHIFT)) % size
#                    d_idx = (idx - ((hash & self._D_MASK) >> self._D_SHIFT)) % size
#
#                    # modular distance ?
#                        # ok so 1. at size//2 it starts decreasing.
#                        # you can also subtract the two mod the value
#                        # 2. if the absolute difference is greater than size//2, then the corret value is size - it.
#                                # it sounds like we could do abs(size//2 - abs(x - y)).
#                                # and i think the abs's combine into abs(size//2 + x - y) :) but i think i am wrong
#                                    # size//2 - abs(x-y) doesn't work for x-y==size//2
#                                # got it backwards
#                                # abs(5 - abs(x - y)) + 5 maybe?
#                                # it's size//2 - abs(size//2 - abs(x - y))
#                        # found on s.o. fabs(5.5-((b-(a-5.5))%12.0))
#                        # so one number has the half subtracted, then it is diffed with the other, then modded ,
#                        # then diffed with the half, then abs'd
#                            # it works for me(mod 10 works) great
#                    # modular distance(x,y,size) = abs((((x-size//2)-y)%size)-size//2)
#                    # simplifies to abs(((x-y-size//2)%size)-size//2)
#                    u_dist = abs(((u_idx - hint - size2)%size)-size2)
#                    d_dist = abs(((d_idx - hint - size2)%size)-size2)
#
#                    # this should return the average maybe
#                    # it's so hard to thinkwork on this rn. i think we will leave it not implemented for now.
#
#                    if u_dist > d_dist:
#                        return int.from_bytes(self._hashes[u_idx], 'little')
#                    elif u_dist < d_dist:
#                        return int.from_bytes(self._hashes[d_idx], 'little')
#                    else:
#                        return (int.from_bytes(self._hashes[u_idx], 'little') +
#                                int.from_bytes(self._hashes[d_idx], 'little')) / 2
#                    # so it looks like, if a list of idcs weren't used, the links could simply refer directly to their dest keys
#                    # but then you'd only get 32-bit keys, which is likely fine
#                    # could also use a list of hashes instead but that would be unnecessarily o(n)
#        idx = bisect.bisect_left(idcs, None, key=key)
#        e_hash, e_entry, e_full, e_short = self._entry_hash(idx, size)
#        if e_full == k_full: # found
#        else: # not found
#            assert e_hash & self._F_MASK # i guess if this is not set then the size could be grown or things could be shifted over
#            # there might be less frequent congestion if the key function were changed to balance the available data better
#        assert e_full == k_full or 
#        return [e_full == k_full, idx, e_hash, e_entry, k_
#        return [True, offset, entry, k_full, k_short, e_full, e_short]
#        return [k_hash, idx]
#
##    def _find(self, key):
##            # so, a reasonable solution here could be to use sorted list bisection with the short hash as the hint.
##            # the concern is that there are empty regions to consider when bisecting.
##            # when these are encountered, they would be filled.
##                # it would be a new bisection algorithm than the one in the library i suppose, unless sparse lists are implemented or this is changed to operate densely
##            # there are a handful of approaches that haven't been explored.
##                # idea: keep the list sorted.
##                # if the list were packed to the front, then normal bisection could be used, but insertion time would grow.
##                    # bisection starts at the hint. if val > hint, it then jumps right. if val < hint, it jumps left.
##                    # it jumps by half the maximum unexplored range each time.
##                    # it finishes with log(n) lookups using random access.
##                # ok so maybe when comparing entries we could guess with their short hash?
##                # doesn't seem to quite work, unevenly weighted data would/could skew things
##                        # it would need to backtrack if it doesn't find evidence it made a correct guess :/
##                                # when storing an item, you could store links to it in empty neighbors
##            # ok so the list would default as empty entries
##            # when one item is filled, all entries would be both empty and link to it (space for this is reasonable)
##            # when two items are filled, it would look for high/low in the ilnks, and change them in that range to point to it.
##            # then bisection can perform two lookups to always quickly find where something goes.
##            # the issue is that storing the high/low entries would require twice the shorthash size in each.
##            # they could be stored relative whih would shrink it by some small bounded value on average, rarely more
##                            # the issue is that it needs a minimum fixedsize to store the links in.
##                            # an alternative is to pack the dict like the list.
##            # there are a number of solutions that have been studied and researched for decades. they are all data structure algorithms.
##            # the current situation of o(n) time for failed lookup is unideal.
##                    # ok i found sufficient space for solutions
##                    # because the empty hash is a 1-bit emptiness indication stored in a 64-bit space,
##                    # that leaves 31 and 32 bits for relative offsets. i.e. 2 billion empties in either dir.
##                        # we got confused cause this wasn't thought of until a different solution was considered
##                        # than written above, unsure what to pursue or consider
##            # ok let's try it.
##            # conditions:
##            # - when structure is entirely empty, if sized, rows must all effectively have unique constant value
##            # - when an item is added to or removed from the structure, rows surrounding it must be filled
##            # - to find an item, o(1) hash indexing is used as a hint for o(log(n)) bisection
##            
##        size = len(self._list._list)
##        k_full, k_short = self._key_hash(key, size)
##        first_empty = [False, None, None, k_full, k_short, None, None]
##        for offset in range(size):
##            offset = (k_short+offset) % size
##            entry, e_full, e_short = self._entry_hash(offset, size)
##            if e_full == k_full:
##                assert e_short == k_short
##                return [True, offset, entry, k_full, k_short, e_full, e_short]
##            elif e_full == self.EMPTY and first_empty[-1] is None:
##                first_empty = [False, offset, entry, k_full, k_short, e_full, e_short]
##        else:
##            return first_empty
##    def __getitem__(self, key):
##        found, idx, entry, k_full, k_short, e_full, e_short = self._find(key)
##        if not found:
##            raise KeyError(key)
##        return entry[self._hashsize:]
##    def __setitem__(self, key, value):
##        found, idx, entry, k_full, k_short, e_full, e_short = self._find(key)
##        if idx is not None:
##            entry[self._hashsize:] = value
##            entry[:self._hashsize] = k_full
##        else:
##            size_new = size * 2
##            empty_row = self.EMPTY.to_bytes(
##                self._list.fixedsize*self._list.view.itemsize,
##                'little'
##            )
##            self._list.extend([empty_row] * size_old)
##            assert len(self._list._list) == size_new
##            for idx in range(size_new):
##                entry, e_full, e_short_old = self._entry_hash(idx, size)
##                e_short_new = e_full % size_new
##                if e_short_new != e_short_old:
##                    assert empty_row == self._list._list[e_short_new]
##                    self._list._list[e_short_new][:] = self._list._list[idx]
##                    self._list._list[idx][:] = empty_row
##            self[key] = value
##    def __delitem__(self, key, value):
##        found, idx, entry, k_full, k_short, e_full, e_short = self._find(key)
##        if not found:
##            raise KeyError(key)
##        entry[:self._hashsize] = self.EMPTY.to_bytes(self.HASHBITS//8,'little')
##    def values(self):
##        size = len(self._list._list)
##        for idx in range(size):
##            entry, full, short = self._entry_hash(idx, size)
##            if full != self.EMPTY:
##                yield[entry[self._hashsize:]]
##        
##    
##class MemoryBackedFixedArrayDict:
##    def __init__(self, region, fixedsize, dtype='B'):
##        self.region = region
##        self.dtype = dtype
##        self.fixedsize = fixedsize
##        self._reseat(self, region)
##    def _reseat(self, region):
##        # there are two different size concepts here
##        # but the idea was to make the bucket count equal to the content length
##        # so the total size is (fixedsize * count) + (indexsize * count)
##        # total = fixed * ct + idx * ct
##        # total - idx * ct = fixed * ct
##        # well we have two knowns, total and fixed
##        # then we need to know indexsize to find ct
##            # ok but if the hashsize is a function of ct it's different
##            # to store n unique values we use log2(n) bits
##            # so hashbytes = log2(ct)/8
##                # so there's a log2(ct)/8 element in indexsize
##                # total = ct * (fixed + log2(ct)*y + z)
##                # we end up solving for m = ct * n + ct log(ct) * o or such, with ct unknown
##                    # involves lambert W function
##                    # but given our hashlengths are some pretty special cases we could do it by iterative trial
##                    # and it would converge very quickly
##
##        per_elem_bytes = self.fixedsize * itemsize + per_element_index_bytes
##        total_bytes = len(region.view)
##        # total = (fixedsize + indexsize) * ct
##        assert total_bytes % per_elem_bytes == 0
##        itemct = len(region.view) // (self.fixedsize + indexsize)
##        
##        # ok we need a layout.
##        # - one region can be entries, or the entries can be spaced
##        # - we'll want one list that is as long as the number of hashes
##        # - so basically we have the idea of as many items as there are hashes
##        # - the items could simply be sorted based on their hash, and indexed by hash
##        # - however, there may be duplicate hashes for a single item
##        # - we could increase the size when there's a duplicate :/ or parametrically change the hash function by the difference of hashes
##        # - if the content size is smaller than the capacity, might then want to store the actual size.
##        # - this could also be counted based on null entries, on load
##        # - all indexing information could possibly be removed if items were checked for matching hash and iterated
##            # - it leaves a concern of wrong hash following; it makes duplicate items steal hashes of other entries
##                # so if you find an item, you check if the hash matches, and iterate forward until it does.
##                # the max duplicate count seems pretty important then
##                    # yeah i'm not sure
##                    # but maybe we'll just do that approach since it seems like a success to!
##        # ok so that would simplify a dict, to a view on an array that hashes and truncates the index.
##        # but when the array grows it then needs to reorder everything to meet the new hash bits
##        # or at least when it grows uhh beyond a two power ??
##        # there is a little unresolved concept.    
##            # we'll reorder it when it grows and take the hash mod the length.
##
##        # ok i ran into an issue that i don't have an actual way to compare keys unless the keys are
##        # stored, or at least their full hashes stored.
##        # additionally if keys aren't stored then there's no .items()
##        # but if keys are stored then they are limited to array content (which could be expanded to struct content)
##        # seems fun to not store keys, just their hashes, which i guess would have some kind of fixed length
##        
##        # if we resize by two powers, does that do anything interesting with the modulo operator?
##            # exactly half on average of the items shift by exactly half the length when growing.
##        # that's still a move of half the items separately, at least it's only half
##        # one could possible copy them all and clear the unused ones
