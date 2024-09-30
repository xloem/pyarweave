import ar

import tqdm

from dataclasses import dataclass
import io, os, threading

from chunkfetcher import ChunkFetcher

_INDEP_HASH = 0
_PREV_BLOCK = 1
#_TX_ROOT = 2
_FLAG_BLOCK = b'B'
_FLAG_HDR = b'h'
_FLAG_EOF = b''

@dataclass
class Transaction:
    @dataclass
    class Block:
        id: str
        timestamp: int
        height: int
        previous: str
    @dataclass
    class MetaData:
        size: int
        type: str # this is just the content-type tag content
    @dataclass
    class Owner:
        address: str
        key: str
    @dataclass
    class Tag:
        name: str
        value: str
    @dataclass
    class Bundle:
        id: str
    id: str
    anchor: str
    signature: str
    recipient: str
    owner: Owner
    fee: int
    quantity: int
    data: MetaData
    tags: [Tag]
    block: Block
    bundledIn: Bundle

class BundleWatcher2MB:
    def __init__(self, peers = 1, cache_file = '.testarblkhdrcache.bin'):
        if type(peers) is int:
            peers = ar.PUBLIC_GATEWAYS[:peers]
        self.peers = [
                ar.Peer(peer)
                if type(peer) is str
                else peer
            for peer in peers
        ]
        self.chunkfetcher = ChunkFetcher(self.peers)
        self._cache_fn = cache_file
        self._lock_blks = threading.RLock()
        self._lock_file = threading.RLock()
        try:
            self._minheight, self._blocks = self._read()
            self._maxheight = self._minheight + len(self._blocks) - 1
            self._fsck(self._minheight, self._maxheight, self._blocks, deep=True)
        except FileNotFoundError:
            self._blocks = [
                ar.Block.frombytes(
                    self._peer().block2_height(
                        self._peer().info()['height']
                    )
                )
            ]
            self._minheight = self._maxheight = self._blocks[0].height
            self._fsck(self._minheight, self._maxheight, self._blocks)
            self._write()
    def iter_txs(self, height, step=1):
        while True:
            self._fsck(self._minheight, self._maxheight, self._blocks, self._blocks)
            self._ensure_range(height, height)
            self._fsck(self._minheight, self._maxheight, self._blocks, self._blocks)
            blk = self._blk(height)
            self._fsck(self._minheight, self._maxheight, self._blocks, self._blocks)
            response_block = Transaction.Block(
                id = blk.indep_hash,
                timestamp = blk.timestamp,
                height = blk.height,
                previous = blk.previous_block,
            )
            for txid in blk.txs[::step]:
                self._fsck(self._minheight, self._maxheight, self._blocks, self._blocks)
                tx = self._fetch_txid(txid)
                self._fsck(self._minheight, self._maxheight, self._blocks, self._blocks)
                response_data_type = [
                    tag['value']
                    for tag in tx.tags
                    if tag['name'].lower() == b'content-type'
                ]
                response_data_type = response_data_type[0].decode() if len(response_data_type) else None
                response_tx = Transaction(
                    id = txid,
                    anchor = tx.last_tx,
                    signature = tx.signature,
                    recipient = tx.target,
                    owner = Transaction.Owner(
                        address = ar.utils.owner_to_address(tx.owner),
                        key = tx.owner,
                    ),
                    fee = tx.reward,
                    quantity = tx.quantity,
                    data = Transaction.MetaData(
                        size = tx.data_size,
                        type = response_data_type,
                    ),
                    tags = [
                        Transaction.Tag(
                            name = tag['name'].decode(),
                            value = tag['value'].decode()
                        ) for tag in tx.tags
                    ],
                    block = response_block,
                    bundledIn = None,
                )
                if step > 0:
                    yield response_tx
                if any([tag['name'].startswith(b'Bundle') for tag in tx.tags]):
                    self._fsck(self._minheight, self._maxheight, self._blocks, self._blocks)
                    tx_offset = self._peer().tx_offset(txid)
                    self._fsck(self._minheight, self._maxheight, self._blocks, self._blocks)
                    stream = io.BufferedReader(
                        ar.stream.PeerStream.from_tx_offset(
                            self.chunkfetcher, tx_offset,
                            tx_root=blk.tx_root_raw, data_root=tx.data_root
                        ),
                        0x40000
                    )
                    with stream:
                        for di_hdr, stream_again, data_offset, data_len in ar.ANS104DataItemHeader.all_from_tags_stream(tx.tags, stream, step=step):
                            if di_hdr.id != di_hdr.nominal_id:
                                continue
                            assert stream_again is stream
                            response_data_type = [
                                tag['value']
                                for tag in di_hdr.tags
                                if tag['name'].lower() == b'content-type'
                            ]
                            response_data_type = (
                                response_data_type[0].decode()
                                if len(response_data_type)
                                else None
                            )
                            self._fsck(self._minheight, self._maxheight, self._blocks, self._blocks)
                            yield Transaction(
                                id = di_hdr.nominal_id,
                                anchor = di_hdr.anchor,
                                signature = di_hdr.signature,
                                recipient = di_hdr.target,
                                owner = Transaction.Owner(
                                    address = ar.utils.b64enc(ar.utils.raw_owner_to_raw_address(di_hdr.raw_owner)),
                                    key = di_hdr.owner,
                                ),
                                fee = 0,
                                quantity = 0,
                                data = Transaction.MetaData(
                                    size = data_len,
                                    type = response_data_type,
                                ),
                                tags = [
                                    Transaction.Tag(
                                        name = tag['name'].decode(),
                                        value = tag['value'].decode(),
                                    ) for tag in di_hdr.tags
                                ],
                                block = response_block,
                                bundledIn = txid,
                            )
                            self._fsck(self._minheight, self._maxheight, self._blocks, self._blocks)
                if step < 0:
                    yield response_tx
                self._fsck(self._minheight, self._maxheight, self._blocks, self._blocks)
            height += step
            self._fsck(self._minheight, self._maxheight, self._blocks, self._blocks)

    def _ensure_range(self, minheight, maxheight):
        with self._lock_blks:
            self._fsck(self._minheight, self._maxheight, self._blocks, self._blocks)
            if minheight < self._minheight:
                headblks = [
                    self._fetch_height(_height)
                    for _height in range(minheight, self._minheight)
                ]
            else:
                minheight = self._minheight
                headblks = []
            if maxheight > self._maxheight:
                tailblks = [
                    self._fetch_height(_height)
                    for _height in range(self._maxheight, maxheight)
                ]
            else:
                maxheight = self._maxheight
                tailblks = []
            blks = headblks + self._blocks + tailblks
            self._fsck(minheight, maxheight, blks, self._blocks, deep=False)
            self._blocks = blks
            self._minheight = minheight
            self._maxheight = maxheight
    def _hdr(self, height):
        blk = self._blocks[height - self._minheight]
        if type(blk) is ar.Block:
            blk = self._blk2hdr(blk, check=False)
        return blk
    def _blk(self, height):
        self._fsck(self._minheight, self._maxheight, self._blocks, self._blocks)
        blk = self._blocks[height - self._minheight]
        if type(blk) is not ar.Block:
            realblk = self._fetch_hash(blk[_INDEP_HASH])
            assert self._blk2hdr(realblk, check=True) == blk
            blk = realblk
            self._blocks[height - self._minheight] = blk
            self._fsck(self._minheight, self._maxheight, self._blocks, self._blocks)
        return blk
    def _fetch_hash(self, raw_indep_hash):
        blkbin = self._peer().block2_hash(b64enc(raw_indep_hash))
        return ar.Block.frombytes(blkbin)
    def _fetch_height(self, height):
        blkbin = self._peer().block2_height(height)
        return ar.Block.frombytes(blkbin)
    def _fetch_txid(self, txid):
        txbin = self._peer().tx2(txid)
        return ar.Transaction.frombytes(txbin)
    def _hdr_fromblk(self, blk, check=True):
        if check:
            assert blk.raw_indep_hash == blk.compute_indep_hash_raw()
        return [blk.indep_hash_raw, blk.previous_block_raw]#, blk.tx_root_raw]
    def _hdr_fromstream(self, fh):
        return [fh.read(48),fh.read(48)]#,fh.read(32)]
    def _hdr_tostream(self, hdr, fh):
        return fh.write(b''.join(hdr))
    def _read(self):
        with self._lock_blks, self._lock_file:
            blks = []
            with open(self._cache_fn, 'rb') as fh:
                while True:
                    flag = fh.read(1)
                    if flag == _FLAG_EOF:
                        break
                    elif flag == _FLAG_BLOCK:
                        blk = ar.Block.fromstream(fh)
                        minheight = blk.height - len(blks)
                    elif flag == _FLAG_HDR:
                        blk = self._hdr_fromstream(fh)
                    blks.append(blk)
            self._blocks = blks
        return minheight, blks
    def _write(self):
        with self._lock_file:
            with self._lock_blks:
                curblks = self._blocks
                minheight = self._minheight
                maxheight = self._maxheight
                self._fsck(minheight, maxheight, curblks)
                try:
                    oldminheight, oldblks = self._read()
                except FileNotFoundError:
                    oldblks = []
                self._fsck(minheight, maxheight, curblks, oldblks)
            del oldblks
            with open(self._cache_fn+'.new', 'wb') as fh:
                for blk in curblks:
                    if type(blk) is ar.Block:
                        fh.write(_FLAG_BLOCK)
                        fh.write(blk.tobytes())
                    else:
                        fh.write(_FLAG_HDR)
                        _hdr_tostream(blk, fh)
            os.rename(self._cache_fn+'.new', self._cache_fn)
    def _fsck(self, minheight, maxheight, blks, oldblks=[], deep=False):
        assert len(blks) >= len(oldblks)
        blkct = 0
        for idx in tqdm.tqdm(
            range(len(blks)),
            'fscking blk ids',
            unit='blk',
            leave=False
        ):
            blk = blks[idx]
            if type(blk) is ar.Block:
                blkct += 1
                assert blk.indep_hash_raw == blk.compute_indep_hash_raw()
                indephash = blk.indep_hash_raw
                prevblock = blk.previous_block_raw
                assert minheight == blk.height - idx
                assert maxheight == blk.height - idx + len(blks) - 1
            else:
                indephash = blk[_INDEP_HASH]
                prevblock = blk[_PREV_BLOCK]
                if deep:
                    blk = ar.Block.frombytes(self._peer().block2_hash(indephash))
                    assert blk.indep_hash_raw == blk.compute_indep_hash_raw()
                    assert blk.indep_hash_raw == indephash
                    assert blk.previous_block_raw == prevblock
            if idx > 0:
                assert prevblock == previndephash
            previndephash = indephash
        assert blkct > 0
        return True
    def _peer(self):
        return self.chunkfetcher.pick_peer().peer

if __name__ == '__main__':
    import dataclasses
    def dc_to_dict(dc):
        return {
            name:
                dc_to_dict(value)
                if dataclasses.is_dataclass(value)
                else value
            for name, value
            in dataclasses.asdict(dc).items()
        }
    bw = BundleWatcher2MB(16)
    for response in bw.iter_txs(bw._maxheight, -1):
        print(dc_to_dict(response))
        bw._fsck(bw._minheight, bw._maxheight, bw._blocks, bw._blocks)
        bw._write()
