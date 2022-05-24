import io
import struct

import fastavro
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes

from .utils import b64dec, b64enc, b64dec_if_not_bytes, b64enc_if_not_str, le_u256enc, le_u256dec, encode_tag, decode_tag, normalize_tag
from .utils.deep_hash import deep_hash
from .utils.ans104_signers import DEFAULT as DEFAULT_SIGNER, BY_TYPE as SIGNERS_BY_TYPE

ANS104_TAGS_SCHEMA = {
  "type": "array",
  "items": {
    "type": "record",
    "name": "Tag",
    "fields": [
      { "name": "name", "type": "bytes" },
      { "name": "value", "type": "bytes" }
    ]
  }  
}

ANS104_TAGS_SCHEMA_fastavro = fastavro.parse_schema(ANS104_TAGS_SCHEMA)

class ANS104BundleHeader:
    def __init__(self, length_by_id = {}):
        self.length_by_id = length_by_id

    def get_count(self):
        return len(self.length_by_id)

    def get_length(self, id):
        id = b64enc_if_not_str(id)
        return self.length_by_id(id)

    def get_offset(self, id):
        return self.get_range(id)[0]

    def get_range(self, id):
        total = self.get_len_bytes()
        id = b64enc_if_not_str(id)
        for other_id, length in self.length_by_id.items():
            if other_id == id:
                return total, total + length
            total += length

    def get_len_bytes(self):
        return 32 + len(self.length_by_id) * 64

    def tobytes(self):
        return le_u256enc(len(self)) + b''.join((
            le_u256enc(length) + b64dec(id)
            for id, length in self.length_by_id.items()
        ))

    @classmethod
    def from_tags_stream(cls, tags, stream):
        fmt = tags[b'Bundle-Format']
        if fmt == b'json':
            return cls.fromjson(json.load(stream))
        elif fmt == b'binary':
            return cls.fromstream(stream)

    @classmethod
    def fromjson(cls, json):
        dataitems = (DataItem.fromjson(item) for item in json['items'])
        return cls({
            dataitem.id: dataitem.get_len_bytes()
            for dataitem in dataitems
        })

    @classmethod
    def frombytes(cls, data):
        stream = io.BytesIO(data)
        return self.fromstream(stream)

    @classmethod
    def fromstream(cls, stream):
        entryct = le_u256dec(stream.read(32))

        length_id_pairs = (
            (le_u256dec(stream.read(32)), b64enc(stream.read(32)))
            for idx in range(entryct)
        )

        return cls({
            id: length
            for length, id in length_id_pairs
        })

class ANS104DataItemHeader:
    def __init__(self, tags = [], owner=None, target=None, anchor=None, signature=None, signer=DEFAULT_SIGNER):
        if isinstance(tags, (bytes, bytearray)):
            self.raw_tags = tags
        else:
            self.tags = tags
        self.raw_owner = b64dec_if_not_bytes(owner)
        self.raw_signature = b64dec_if_not_bytes(signature)
        self.target = b64enc_if_not_str(target) if target else None
        if anchor is None:
            anchor = get_random_bytes(32)
        self.anchor = b64enc_if_not_str(anchor) if anchor else None
        self.signer = signer

    @property
    def signature_type(self):
        return self.signer.type

    @property
    def raw_signature_type(self):
        return struct.pack('<H', self.signature_type)

    @property
    def signature(self):
        if len(self.raw_signature):
            return b64enc(self.raw_signature)
        else:
            return None

    @signature.setter
    def set_signature(self, signature):
        self.raw_signature = b64dec(signature)

    @property
    def owner(self):
        return b64enc(self.raw_owner)

    @property
    def raw_public_key(self):
        return self.raw_owner

    @property
    def public_key(Self):
        return self.owner

    @property
    def raw_target(self):
        if self.target is not None:
            return b64dec(self.target)
        else:
            return b''

    @property
    def raw_anchor(self):
        if self.anchor is not None:
            return b64dec(self.anchor)
        else:
            return b''

    @property
    def raw_nonce(self):
        return self.raw_anchor
    
    @property
    def nonce(self):
        return self.anchor

    @property
    def raw_id(self):
        return SHA256.new(self.raw_signature).digest()

    @property
    def id(self):
        return b64enc(self.raw_id)

    @property
    def tags(self):
        stream = io.BytesIO(self.raw_tags)
        return fastavro.schemaless_reader(stream, ANS104_TAGS_SCHEMA_fastavro)

    @tags.setter
    def tags(self, tags):
        stream = io.BytesIO()
        fastavro.schemaless_writer(stream, ANS104_TAGS_SCHEMA_fastavro, [
            normalize_tag(tag) for tag in tags
        ])
        self.raw_tags = stream.getvalue()
        

    def tojson(self):
        return {
            'owner': self.owner,
            'target': self.target if self.target is not None else '',
            'nonce': self.anchor if self.anchor is not None else '',
            'tags': [
                encode_tag(tag)
                for tag in self.tags
            ] if self.tags is not None else [],
            'signature': self.signature,
            'id': self.id,
        }

    def get_len_bytes(self):
        total = 2 + self.signer.signature_length + self.signer.owner_length + 2
        if self.target is not None:
            total += 32
        if self.anchor is not None:
            total += 32
        total += 16 + len(self.raw_tags)
        return total

    def tobytes(self):
        raw = io.BytesIO()
        if self.target is not None:
            target_struct = '?32s'
            target_values = (True, self.raw_target)
        else:
            target_struct = '?'
            target_values = (False,)
        if self.anchor is not None:
            anchor_struct = '?32s'
            anchor_values = (True, self.raw_anchor)
        else:
            anchor_struct = '?'
            anchor_values = (False,)
        raw_tags = self.raw_tags
        return struct.pack(
            (
                '<H' + # signature type
                self.signer.signature_structpack + # signature
                self.signer.owner_structpack + # public key
                target_struct + # optional receiving address
                anchor_struct + # antireplay nonce
                'QQ' # tags count, tags bytelength
            ),
            self.signer.type,
            self.raw_signature,
            self.raw_owner,
            *target_values,
            *anchor_values,
            len(self.tags), len(raw_tags)
        ) + raw_tags

    @classmethod
    def fromjson(cls, json):
        signer = DEFAULT_SIGNER
        return cls(
            tags = [
                decode_tag(tag)
                for tag in json['tags']
            ],
            owner = b64dec(json['owner']),
            target = json['target'],
            anchor = json['nonce'],
            signature = json['signature'],
            signer = signer
        )

    @classmethod
    def frombytes(cls, data):
        if len(data) < 80:
            raise Exception('length shorter than 80 bytes')
        stream = io.BytesIO(data)
        return cls.fromstream(stream)

    @classmethod
    def fromstream(cls, stream):
        offset = 0
        start_tell = stream.tell()

        signature_type, = struct.unpack('<H', stream.read(2)) # signature type
        signer = SIGNERS_BY_TYPE.get(signature_type)
        offset += 2

        if signer is None:
            raise Exception(f'unknown signature type: {signature_type}')
        raw_signature, raw_owner = struct.unpack(
            signer.signature_structpack + # signature
            signer.owner_structpack, # public key
            stream.read(signer.signature_length + signer.owner_length)
        )
        offset += signer.signature_length + signer.owner_length

        target_flag = stream.read(1)[0]
        if target_flag not in b'\x00\x01':
            raise Exception(f'unknown target flag value: {target_flag}')
        offset += 1

        if target_flag:
            target = stream.read(32)
            offset += 32
        else:
            target = None

        anchor_flag = stream.read(1)[0]
        if anchor_flag not in b'\x00\x01':
            raise Exception(f'unknown anchor flag value: {anchor_flag}')
        offset += 1

        if anchor_flag:
            anchor = stream.read(32)
            offset += 32
        else:
            anchor = b''

        tags_len, raw_tags_len = struct.unpack('<QQ', stream.read(16))
        offset += 16

        if raw_tags_len > 0:
            raw_tags = stream.read(raw_tags_len)
            raw_tags_stream = io.BytesIO(raw_tags)
            tags = fastavro.schemaless_reader(raw_tags_stream, ANS104_TAGS_SCHEMA_fastavro)
            offset += raw_tags_len
            if raw_tags_stream.tell() != raw_tags_len or len(tags) != tags_len:
                raise Exception(f'incorrect tags length')
        else:
            tags = b''

        assert stream.tell() == offset + start_tell

        result = cls(
            tags = raw_tags,
            owner = raw_owner,
            target = target,
            anchor = anchor,
            signature = raw_signature,
            signer = signer
        )
    
        assert offset - raw_tags_len == result.get_len_bytes() - len(result.raw_tags)
        assert offset == result.get_len_bytes()
        return result

class DataItem:
    def __init__(self, header = None, data = b'', version = 2):
        self.data = data
        if header is None:
            header = ANS104DataItemHeader()
        self.header = header
        self.version = version

    def get_raw_signature_data(self):
        items = [
            b'dataitem',
            b'1'
        ]
        if int(self.version) >= 2:
            items.append(str(self.header.signature_type).encode())
        items.extend((
            self.header.raw_owner,
            self.header.raw_target,
            self.header.raw_anchor,
        ))
        if int(self.version) >= 2:
            items.append(self.header.raw_tags)
        else:
            items.append([
                [tag['name'], tag['value']]
                for tag in self.header.tags
            ])
        items.append(self.data)
        return deep_hash(items)

    def sign(self, private_key):
        self.header.raw_owner = self.header.signer.raw_owner(private_key)
        self.header.raw_signature = self.header.signer.sign(private_key, self.get_raw_signature_data())
        return self.header.id

    def verify(self):
        if len(self.header.tags) > 128:
            return False
        if len(self.header.raw_anchor) > 32:
            return False
        for tag in self.header.tags:
            if len(tag.keys()) > 2 or 'name' not in tag or 'value' not in tag:
                return False
            for key, value in tag.items():
                if len(value) == 0:
                    return False
        if len(tag['name']) > 1024:
            return False
        if len(tag['value']) > 3072:
            return False
        public_key = self.header.signer.public_key(self.header.raw_owner)
        return self.header.signer.verify(public_key, self.get_raw_signature_data(), self.header.raw_signature)

    def tojson(self):
        result = self.header.tojson()
        result['data'] = b64enc(self.data)
        return result

    def get_len_bytes(self):
        return self.header.get_len_bytes() + len(self.data)

    def tobytes(self):
        return self.header.tobytes() + self.data

    @classmethod
    def all_from_tags_stream(cls, tags, stream):
        fmt = None
        for tag in tags:
            if tag['name'] == b'Bundle-Format':
                fmt = tag['value']
        print(fmt)
        if fmt == b'json':
            yield from Bundle.fromjson(json.load(stream)).dataitems
        elif fmt == b'binary':
            header = ANS104BundleHeader.fromstream(stream)
            offset = header.get_len_bytes()
            for length in header.length_by_id.values():
                dataitem = cls.fromstream(stream, length=length)
                offset += length
                yield dataitem

    @classmethod
    def fromjson(cls, json):
        return cls(header = ANS104DataItemHeader.fromjson(json), data = b64dec(json['data']), version = 1)

    @classmethod
    def frombytes(cls, data, length = None):
        stream = io.BytesIO(data)
        return cls.fromstream(stream, length = length)

    @classmethod
    def fromstream(cls, stream, length = None):
        header = ANS104DataItemHeader.fromstream(stream)
        if length is None:
            data = stream.read()
        else:
            data = stream.read(length - header.get_len_bytes())
        return cls(header = header, data = data, version = 2)

class Bundle:
    def __init__(self, dataitems, version = 2):
        self.dataitems = dataitems

    def sign(self, private_key):
        for dataitem in self.dataitems:
            dataitem.sign(private_key)

    def verify(self):
        return all(dataitem.verify() for dataitem in self.dataitems)

    @property
    def header(self):
        return ANS104BundleHeader({
            item.id: item.get_len_bytes()
            for item in self.dataitems
        })

    def tojson(self):
        return {
            'items': [
                dataitem.tojson()
                for dataitem in self.dataitems
            ]
        }

    def tobytes(self):
        return self.header + b''.join(item.tobytes() for item in self.dataitems)
    
    @classmethod
    def fromjson(cls, json):
        dataitems = [DataItem.fromjson(item) for item in json['items']]
        return cls(dataitems, version = 1)

    @classmethod
    def frombytes(cls, bytes):
        stream = io.BytesIO(bytes)
        return self.fromstream(stream)

    @classmethod
    def fromstream(cls, stream):
        header = ANS104BundleHeader.fromstream(stream)
        dataitems = [DataItem.fromstream(stream, length) for id, length in header.length_by_id.items()]
        return cls(dataitems, version = 2)
