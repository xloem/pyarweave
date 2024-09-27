import io

from .utils import arbinenc, arbindec, b64enc, b64dec
from .utils.merkle import Node as MerkleNode
from . import utils

class Chunk:
    def __init__(self, data = None, data_path = None, tx_path = None, packing = 'unpacked'):
        self.data = data
        self.data_path = data_path
        self.tx_path = tx_path
        self.packing = packing

    @property
    def start_offset(self):
        return self.data_path[-1].min_byte_range

    @property
    def end_offset(self):
        return self.data_path[-1].max_byte_range

    @property
    def tx_start_offset(self):
        return self.tx_path[-1].min_byte_range

    @property
    def tx_end_offset(self):
        return self.tx_path[-1].max_byte_range

    @property
    def data_hash_raw(self):
        '''sha256 of the chunk'''
        return self.data_path[-1].data_hash

    @property
    def data_hash(self):
        return b64enc(self.data_path[-1].data_hash)

    @property
    def data_root_raw(self):
        return self.data_path[0].id_raw

    @property
    def data_root(self):
        return b64enc(self.data_path[0].id_raw)

    @property
    def tx_root_raw(self):
        return self.tx_path[0].id_raw

    @property
    def tx_root(self):
        return b64enc(self.tx_path[0].id_raw)

    def __len__(self):
        tail = self.data_path[-1]
        return tail.max_byte_range - tail.min_byte_range

    def validate(self, data_root, tx_root):
        assert utils.merkle.validate_path(self.data_path[0].id_raw, self.start_offset, self.start_offset, self.end_offset, self.data_path[0].tobytes())
        if self.end_offset > self.start_offset:
            assert utils.merkle.validate_path(self.data_path[0].id_raw, self.end_offset-1, self.start_offset, self.end_offset, self.data_path[0].tobytes())
        assert utils.merkle.validate_path(self.tx_path[0].id_raw, self.tx_start_offset, self.tx_start_offset, self.tx_end_offset, self.tx_path[0].tobytes())
        if self.tx_end_offset > self.tx_start_offset:
            assert utils.merkle.validate_path(self.tx_path[0].id_raw, self.tx_end_offset-1, self.tx_start_offset, self.tx_end_offset, self.tx_path[0].tobytes())
        assert self.data_path[0].id_raw == self.tx_path[-1].data_hash
        if data_root is not None:
            assert data_root == self.data_root
        if tx_root is not None:
            assert tx_root == self.tx_root
        assert utils.merkle.hash_raw(self.data) == self.data_hash_raw

    def tojson(self):
        return {
            'chunk': b64enc(self.data),
            'data_path': b64enc(self.data_path[0].tobytes()),
            'packing': self.packing,
            'tx_path': b64enc(self.tx_path[0].tobytes())
        }

    def tobytes(self):
        return b''.join((
            arbinenc(self.data, 24),
            arbinenc(self.tx_path[0].tobytes(), 24),
            arbinenc(self.data_path[0].tobytes(), 24),
            arbinenc(self.packing.encode(), 8)
        ))
    
    @classmethod
    def fromjson(cls, json_obj):
        data = b64dec(json_obj['chunk'])
        return cls(
            data = data,
            data_path = MerkleNode.frombytes(b64dec(json_obj['data_path']), max_byte_range=len(data)),
            packing = json_obj['packing'],
            tx_path = MerkleNode.frombytes(b64dec(json_obj['tx_path']))
        )

    @classmethod
    def frombytes(cls, bytes):
        return cls.fromstream(io.BytesIO(bytes))

    @classmethod
    def fromstream(cls, stream):
        data = arbindec(stream, 24)
        tx_path_bin = arbindec(stream, 24)
        data_path_bin = arbindec(stream, 24)
        packing_bin = arbindec(stream, 8)
        assert len(tx_path_bin) # have not diagnosed why this raises sometimes
        return cls(
            data = data,
            tx_path = MerkleNode.frombytes(tx_path_bin),
            data_path = MerkleNode.frombytes(data_path_bin, max_byte_range=len(data)),
            packing = packing_bin.decode()
        )


if __name__ == '__main__':
    import ar
    for gw_url in ar.PUBLIC_GATEWAYS:
        gw = ar.Peer(gw_url)
        for peer_url in [*[origin['endpoint'] for origin in gw.health()['origins']], *gw.peers()]:
            try:
                peer = ar.Peer(peer_url)
                peer.info()
                break
            except:
                peer = None
                print('failed to connect to', peer_url)
        if peer:
            break
    else:
        raise RuntimeError('no peer')
    print('connected to', peer.api_url)
    chunk_bounds = peer.data_sync_record()[-1]
    chunkjson = peer.chunk(chunk_bounds[0])
    chunkbytes = peer.chunk2(chunk_bounds[0])
    chunkfromjson = Chunk.fromjson(chunkjson)
    chunkfrombytes = Chunk.frombytes(chunkbytes)
    assert chunkfromjson.tobytes() == chunkbytes
    assert chunkfrombytes.tojson() == chunkjson
    chunkfromjson.validate(None,None)
    chunkfrombytes.validate(None,None)
    print('chunk range:', chunkfrombytes.start_offset, chunkfrombytes.end_offset)
