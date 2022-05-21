import io
import struct
import fastavro
from Crypto.Random import get_random_bytes
from . import keys
from . import tags
from ar.utils.deep_hash import deep_hash

# this is analogous to ar.Transaction and the two should likely be normalised to have similar interfaces.

# this could read straight from a file and not need to allocate as much memory

class DataItem:
    def __init__(self, sig_config = keys.Rsa4096Pss, signature = None, owner = None, target = None, anchor = None, tags = {}, data = None):
        self.sig_config = sig_config
        self.signature = signature
        self.owner = owner
        self.target = target
        self.anchor = anchor
        self.tags = tags
        self.data = data

    def tobytes(self):
        outfp = io.BytesIO()

        outfp.write(bytes((self.sig_config.signatureType, 0)))

        if self.signature is None:
            self.signature = bytes(self.sig_config.signatureLength)
        assert len(self.signature) == self.sig_config.signatureLength
        outfp.write(self.signature)

        if self.owner is None:
            self.owner = get_random_bytes(self.sig_config.ownerLength)
        assert len(self.owner) == self.sig_config.ownerLength
        outfp.write(self.owner)
        
        if self.target is not None:
            assert len(self.target) == 32
            outfp.write(b'\x01')
            outfp.write(self.target)
        else:
            outfp.write(b'\x00')

        if self.anchor is not None:
            assert len(self.anchor) == 32
            outfp.write(b'\x01')
            outfp.write(self.anchor)
        else:
            outfp.write(b'\x00')

        if len(self.tags):
            _tags = tags.serialize_buffer(self.tags)
            outfp.write(struct.pack('<QQ', len(self.tags), len(_tags)))
            outfp.write(_tags)
        else:
            outfp.write(bytes(16)) # 0, 0

        if self.data is None:
            self.data = b''

        return outfp.getvalue() + self.data

    def get_signature_data(self):
        return deep_hash([
            b'dataitem',
            b'1',
            str(self.sig_config.signatureType).encode(),
            self.owner,
            self.target if self.target is not None else b'',
            self.anchor if self.anchor is not None else b'',
            tags.serialize_buffer(self.tags) if len(self.tags) else b'',
            self.data
        ])
