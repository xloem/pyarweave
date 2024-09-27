import hashlib, io, ar
from ar import logger

class PeerStream(io.RawIOBase):
    @classmethod
    def from_txid(cls, peer, txid, offset = 0, length = None, tx_root = None, data_root = None):
        try:
            tx_offset = peer.tx_offset(txid)
            if tx_root is None:
                tx_status = peer.tx_status(txid)
                block = ar.Block.frombytes(peer.block2_hash(tx_status['block_indep_hash']))

                tx_root = block.tx_root
            if data_root is None:
                tx = ar.Transaction.frombytes(peer.tx2(txid))
                assert tx.verify()
                data_root = tx.data_root
        except ar.ArweaveNetworkException as exc:
            raise # likely exc is 404 and the tx is unconfirmed. a gateway stream would work, or waiting.
        return cls.from_tx_offset(peer, tx_offset, offset, length, tx_root, data_root)
    @classmethod
    def from_tx_offset(cls, peer, tx_offset, offset = 0, length = None, tx_root = None, data_root = None):
        assert tx_root is not None
        assert data_root is not None
        stream_last = tx_offset['offset']
        stream_size = tx_offset['size']
        stream_first = stream_last - stream_size + 1
        return cls(peer, stream_first, offset, stream_size if length is None else min(offset + length, stream_size), tx_root, data_root)

    def __init__(self, peer, tx_start_offset, start_offset, end_offset, tx_root, data_root):
        self.peer = peer
        assert end_offset >= start_offset
        self.start = start_offset
        self.tx_start = tx_start_offset
        self.end = end_offset
        self.offset = self.start
        self.tx_root_raw = ar.utils.b64dec(tx_root)
        self.data_root_raw = ar.utils.b64dec(data_root)
        self.chunk = None
    def tell(self):
        return self.offset - self.start
    def readable(self):
        return True
    def seekable(self):
        return True
    def seek(self, offset, whence = io.SEEK_SET):
        if whence == io.SEEK_SET:
            offset += self.start
        elif whence == io.SEEK_CUR:
            offset += self.offset
        elif whence == io.SEEK_END:
            offset += self.end
        
        self.offset = max(self.start, min(self.end, offset))
        return self.offset - self.start

    def readinto(self, b):
        if self.offset >= self.end:
            return 0

        if (
                self.chunk is None or
                self.chunk.start_offset > self.offset or
                self.chunk.end_offset <= self.offset
        ):
            self.chunk = ar.Chunk.frombytes(self.peer.chunk2(self.offset + self.tx_start), self.tx_root_raw, self.data_root_raw)
            assert self.chunk.start_offset <= self.offset
            assert self.chunk.end_offset > self.offset

        bytecount = min(len(b), self.chunk.end_offset - self.offset, self.end - self.offset)
        logger.debug(f'reading {bytecount} bytes from chunk [{self.chunk.start_offset + self.tx_start},{self.chunk.end_offset + self.tx_start})')
        assert bytecount > 0
        suboffset = self.offset - self.chunk.start_offset
        b[ : bytecount] = self.chunk.data[suboffset : suboffset + bytecount]
        self.seek(bytecount, io.SEEK_CUR)

        return bytecount

class GatewayStream:
    @classmethod
    def from_txid(cls, peer, txid, offset = 0, length = None):
        if offset != 0 or length is not None:
            if length is None:
                end = ''
            else:
                end = offset + length
            headers = {'Range':f'bytes={offset}-{end}'}
        else:
            headers = {}
        response = peer._get('raw', txid, headers = headers, stream = True)
        return cls(response)

    def __init__(self, response):
        self.response = response

    def read(self, *params):
        return self.response.raw.read(*params)

    def close(self):
        self.response.close()

    def __getattr__(self, attr):
        return getattr(self.response.raw, attr)

    def __enter__(self):
        self.response.__enter__()
        return self

    def __exit__(self, *params):
        return self.response.__exit__(*params)

    def __del__(self):
        self.close()

#class GatewayBackedPeerStream(io.RawIOBase):
#    '''
#    Data from a tx is only available once that data is mined,
#    but gateways have some way of serving data early.
#    '''
#    '''
#    If the tx data is available, degrades into a PeerStream.
#    Otherwise, reuploads the data while using the gateway as a back.
#    '''
#    def __init__(self, gateway, txid, offset=0, length=None):
#        
