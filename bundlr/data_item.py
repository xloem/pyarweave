import io
import struct
import fastavro
from Crypto.Random import get_random_bytes
from Crypto.Hash import SHA256
from . import keys
from . import tags
from ar.utils.deep_hash import deep_hash

# this is analogous to ar.Transaction and the two should likely be normalised to have similar interfaces.

# this could read straight from a file and not need to allocate as much memory

# NOTE: these seem very similar to ans104 bundle dataitems, but i'm not sure whether they're precisely the same

class DataItem:
    MIN_BINARY_SIZE = 80
    def __init__(self, sig_config = keys.Rsa4096Pss, signature = None, owner = None, target = None, anchor = None, tags = [], data = None):
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

        if self.tags is not None and len(self.tags):
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

    def sign(self, jwkjson):
        self.signature = self.sig_config.sign(jwkjson, self.get_signature_data())

    def verify(self):
        if len(self.tags) > 128:
            return False
        if self.anchor is not None and len(self.anchor) > 32:
            return False
        for tag in self.tags:
            if len(tag.keys()) > 2 or 'name' not in tag or 'value' not in tag:
                return False
            for key, value in tag.items():
                if not isinstance(value, (bytes, bytearray)):
                    value = str(value).encode()
                    tag[key] = value
                if len(value) == 0:
                    return False
            if len(tag['name']) > 1024:
                return False
            if len(tag['value']) > 3072:
                return False
        return self.sig_config.verify(self.owner, self.get_signature_data(), self.signature)

    @property
    def id(self):
        return SHA256.new(self.signature).digest()

    @classmethod
    def frombytes(cls, bytes):
        if len(bytes) < DataItem.MIN_BINARY_SIZE:
            raise Exception('Length shorter than minimum size')

        infp = io.BytesIO(bytes)
        
        rawsigtype = infp.read(2)
        sigtype = rawsigtype[0] + rawsigtype[1] * 256
        sig_config = keys.configs.get(sigtype)
        if sig_config is None:
            raise Exception(f'Unknown signature type: {sigtype}')

        signature = infp.read(sig_config.signatureLength)

        owner = infp.read(sig_config.ownerLength)

        target_flag = infp.read(1)[0]
        if target_flag not in b'\x00\x01':
            raise Exception(f'Unknown target flag value: {targetFlag}')

        target = infp.read(32) if target_flag else None

        anchor_flag = infp.read(1)[0]
        if anchor_flag not in b'\x00\x01':
            raise Exception(f'Unknown anchor flag value: {anchorFlag}')

        anchor = infp.read(32) if anchor_flag else None

        tag_count, tags_bytelength = struct.unpack('<QQ', infp.read(16))

        if tags_bytelength != 0:
            deserialized_tags = tags.deserialize_buffer(infp.read(tags_bytelength))
            if len(deserialized_tags) != tag_count:
                raise Exception('Incorrect tag count')
        else:
            deserialized_tags = None
            
        data_offset = infp.tell()

        return cls(sig_config = sig_config, signature = signature, owner = owner, target = target, anchor = anchor, tags = deserialized_tags, data = bytes[data_offset:])
