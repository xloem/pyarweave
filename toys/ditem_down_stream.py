import io, ar
import yarl39
import json, tqdm
import bisect, itertools, threading, queue
import lru_idx_data_cache

class LoadBalancer:
    def __init__(self, servers):
        self._servers = servers
        self._uses = [[0,idx] for idx in range(len(servers))]
        self._lock = threading.Lock()
    @property
    def servers(self):
        return list(self._servers)
    def use(self):
        return self.Selection(self)
    class Selection:
        def __init__(self, balancer):
            self.balancer = balancer
        def __enter__(self):
            with self.balancer._lock:
                self.balancer._uses.sort()
                self._selection = self.balancer._uses[0]
                self._selection[0] += 1
            return self.balancer._servers[self._selection[1]]
        def __exit__(self, *params):
            with self.balancer._lock:
                self._selection[0] -= 1
        @staticmethod
        def _sort_key(entry):
            return entry[0]

class DownStream(io.RawIOBase):
    @classmethod
    def from_file(cls, good_gws, jsonfn, cachesize=1024*1024*1024, bundlrs=[]):
        with open(jsonfn, 'rb') as jsonfh:
            return cls(good_gws, jsonfh, cachesize=cachesize, bundlrs=bundlrs).expand()
    def expand(self):
        stream = self
        with tqdm.tqdm(desc=self.name, total=self.depth, unit='depth', leave=False) as pbar:
            pbar.update()
            while stream.depth > 1:
                with stream:
                    stream = type(self)(stream.gws.servers, stream, cachesize=self._cache.capacity, bundlrs=self._bundlrs)
                pbar.update()
        return stream
    def __init__(self, good_gws, jsonfh, cachesize=1024*1024*1024, bundlrs=[]):
        self.gws = LoadBalancer(good_gws)
        self._bundlrs = bundlrs
        self._pump = yarl39.SyncThreadPump(
            self._data2,
            size_per_period=None,
            period_secs=1,
        )
        self._ids = []
        self._offsets = []
        for line in jsonfh.readlines():
            line = line.strip()
            if len(line):
                jsondoc = json.loads(line)
                self._ids.append(jsondoc['id'])
                self._offsets.append(jsondoc['off'])
        self._cache = lru_idx_data_cache.Cache(cachesize, len(self._ids))
        self.offset = 0
        self.depth = jsondoc.get('depth',1)
        if self.depth == 1:
            assert jsondoc['size'] == self._offsets[-1] + self._length(self._ids[-1])
            self.size = jsondoc['size']
        else:
            self.size = self._offsets[-1] + self._length(self._ids[-1])
        self._offsets.append(self.size)
        self.name = jsondoc['name']
    def tell(self):
        return self.offset
    def readable(self):
        return True
    def seekable(self):
        return True
    def seek(self, offset, whence = io.SEEK_SET):
        if whence == io.SEEK_CUR:
            offset += self.offset
        elif whence == io.SEEK_END:
            offset += self.size
        self.offset = max(0, min(self.size, offset))
        return self.offset
    def readinto(self, b):
        offset = self.offset
        #print('readinto @', offset,' -> ', len(b))
        if self.size is not None and offset >= self.size:
            return 0
        b_offset = 0
        _offsets = self._offsets
        #unk_idx_min, unk_idx_max = self._unk_offset_range
        idx0 = bisect.bisect_right(_offsets, offset) - 1
        idx1 = min(bisect.bisect_left(_offsets, offset + len(b), idx0), self._cache.max_idx)
        #if offset <= _offsets[unk_offset_min-1]:
        #if True:
        #    idx0 = bisect.bisect_right(_offsets[:unk_idx_min], offset) - 1
        #    idx1 = min(bisect.bisect_left(_offsets[:unk_idx_min], offset + len(b), idx0), len(self._cache))
        #elif offset >= _offsets[unk_offset_max

        #to_add = []
        # fetch
        #fetched_entries = 
        for idx in range(idx0, idx1):#min(idx1,len(self._cache)-1)):
            if self._cache.access(idx, lock=1) is None:
                size = self._offsets[idx+1] - self._offsets[idx]
                self._cache.add(idx, size, self._pump.immed_fut(size, idx), lock=2)
                #to_add.append([idx, size, self._pump.immed_fut(size, idx)])
            #else:
            #    to_add.append([idx, size, None])
        # prefetch
        prefetch_tail = min(idx1+(idx1-idx0)*2+1,self._cache.max_idx)
        for idx in range(idx1, prefetch_tail):
            if self._cache.peek(idx, lock=1) is None:
                size = self._offsets[idx+1] - self._offsets[idx]
                self._cache.add(idx, size, self._pump.feed(size, idx), lock=2)
                #to_add.append([idx, size, self._pump.feed(size, idx)])
            #else:
            #    to_add.append([idx, size, None])
        #self._cache.add_many(*to_add)

        # drain background output queue since it isn't used and grows
        [self._pump.queue_bg_out.get() for _ in range(self._pump.fetch_count())]

        have_data = False
        for idx in range(idx0, idx1):
            data = self._cache.peek(idx)
            self._cache.unlock(idx, 1)
            if type(data) is not bytes:
                if have_data and not data.done():
                    for idx in range(idx+1, idx1):
                        self._cache.unlock(idx, 1)
                    break
                data = data.result()
                self._cache.replace(idx, data)
                self._cache.unlock(idx, 1)
            if idx == idx0:
                data = data[offset - self._offsets[idx]:]
            elif self.size is None and idx + 1 == self._cache.max_idx:
                self.size = self._offsets[idx] + len(data)
            size = min(len(data), len(b) - b_offset)
            b[b_offset:b_offset+size] = data[:size]
            have_data = True
            offset += size
            b_offset += size
        for idx in range(idx1, prefetch_tail):
            self._cache.unlock(idx, 1)
        if self.offset < self._pbar.n + self.size // 16:
            # i guess ideally this might track coverage of the file :s
            self._pbar.update(offset - self._pbar.n)
        self.offset = offset
        #print(self._cache.used, self._cache.capacity, len(self._cache.expiry))
        #print(idx0, idx1, '->', b_offset)
        return b_offset
    def __enter__(self):
        self._pump.__enter__()
        self._pbar = tqdm.tqdm(desc='opening ' + self.name,total=self.size,unit='B',unit_scale=True,leave=False) 
        self._pbar.__enter__()
        return self
    def __exit__(self, *params):
        self._pbar.__exit__(*params)
        return self._pump.__exit__(*params)

    def _length(self, txid):
        try:
            with (
                self.gws.use() as gw,
                gw._request(txid, method='HEAD') as response
            ):
                return int(response.headers['Content-Length'])
        except ar.ArweaveNetworkException as exc:
            # this is in the graphql too i think
            if exc.args[1] == 404 and len(self._bundlrs):
                for bundlr in self._bundlrs:
                    try:
                        return int(bundlr._request('tx', txid, 'data', method='HEAD').headers['Content-Length'])
                    except Exception as exc2:
                        bundlr_exception = exc2 # just in case debugging and helpful to use variable name
            raise
    def _data(self, txid):
        # might be faster to push raw headers to raw sockets here or use libcurl
        try:
            with (
                self.gws.use() as gw,
                gw._request(txid, method='GET') as response
            ):
                return response.content
        except ar.ArweaveNetworkException as exc:
            if exc.args[1] == 404 and len(self._bundlrs):
                for bundlr in self._bundlrs:
                    try:
                        return bundlr.data(txid)
                    except Exception as exc2:
                        bundlr_exception = exc2 # just in case debugging and helpful to use variable name
            raise
    def _data2(self, idx):
        data = self._data(self._ids[idx])
        #self._cache[idx] = data
        #idx_1 = idx+1
        #if idx_1 == self._unk_offset_range[0]:
        #    self._offsets[idx_1] = self._offsets[idx] + len(data)
        #    if idx_1 == self._unk_offset_range[1]:
        #        self._unk_offset_range = [None,None]
        #    else:
        #        self._unk_offset_range[0] += 1
        #elif idx == self._unk_offset_range[1]:
        #    if idx_1 == len(self._offsets): 
        #        self._offsets[idx] = self.size - len(data)
        #    else:
        #        self._offsets[idx] = self._offsets[idx_1] - len(data)
        #    if idx == self._unk_offset_range[0]:
        #        self._unk_offset_range = [None,None]
        #    else:
        #        self._unk_offset_range[1] -= 1
        #elif self._unk_offset_range != [None,None]:
        #    import pdb; pdb.set_trace()
        return data
    def readline(self):
        offset = self.offset
        idx = -1
        line = newdata = b''
        while idx == -1:
            line += newdata
            newdata = self.read(102400)
            if not newdata:
                return line
            idx = newdata.find(b'\n')
        line += newdata[:idx+1]
        self.offset = offset + len(line)
        return line

def main():
    import argparse, sys, os
    parser = argparse.ArgumentParser(description='put description here')
    parser.add_argument(
        'json',
        type=argparse.FileType('rb', bufsize=0),
        help='The jsonl file to download from',
    )
    DEFAULT_GWS = ','.join([
        ar.gateways.GOOD[idx]
        for idx in range(32)
    ])
    parser.add_argument(
        '--gateways', '-gws',
        type=str,
        help='Comma-separated list of gateways to use, or an integer count. default: "' + DEFAULT_GWS + '"',
        default=DEFAULT_GWS
    )
    args = parser.parse_args()

    if args.gateways.isdecimal():
        num_gws = int(args.gateways)
        ar.gateways.update_best(num_gws)
        ar.gateways.fetch_and_update_new()
        args.gateways = ','.join([
            ar.gateways.GOOD[idx]
            for idx in range(num_gws)
        ])
    gws = args.gateways.split(',')
    conns_per_gw = ar.Peer().max_outgoing_connections // len(gws)

    with DownStream([ar.Peer(gw, outgoing_connections=conns_per_gw, requests_per_period = None) for gw in gws], args.json, cachesize=102400*3).expand() as stream:
        #print(stream.name, file=sys.stderr)
        with tqdm.tqdm(desc=stream.name, total=stream.size, unit='B', unit_scale=True, smoothing=0) as pbar:
            while True:
                data = stream.read(1024*1024)
                pbar.update(len(data))
                if not data:
                    break
                sys.stdout.buffer.write(data)

if __name__ == '__main__':
    main()
