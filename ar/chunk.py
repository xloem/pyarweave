import io

from .utils import arbinenc, arbindec, b64enc, b64dec
from .utils.merkle import Node as MerkleNode

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
        return self.data_path[-1].data_hash

    def __len__(self):
        tail = self.data_path[-1]
        return tail.max_byte_range - tail.min_byte_range

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
        return cls(
            data = data,
            tx_path = MerkleNode.frombytes(arbindec(stream, 24)),
            data_path = MerkleNode.frombytes(arbindec(stream, 24), max_byte_range=len(data)),
            packing = arbindec(stream, 8).decode()
        )


if __name__ == '__main__':
    import ar
    peer = ar.Peer(ar.Peer().health()['origins'][-1]['endpoint'])
    chunk_bounds = peer.data_sync_record()[-1]
    chunkjson = peer.chunk(chunk_bounds[0])
    chunkbytes = peer.chunk2(chunk_bounds[0])
    chunkfromjson = Chunk.fromjson(chunkjson)
    chunkfrombytes = Chunk.frombytes(chunkbytes)
    assert chunkfromjson.tobytes() == chunkbytes
    assert chunkfrombytes.tojson() == chunkjson
    print('chunk range:', chunkfrombytes.first_offset, chunkfrombytes.last_offset)
