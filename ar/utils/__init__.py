# This file is part of PyArweave.
# 
# PyArweave is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 2 of the License, or (at your option) any later
# version.
# 
# PyArweave is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along with
# PyArweave. If not, see <https://www.gnu.org/licenses/>.

import hashlib
import struct
from Crypto.Signature import PKCS1_PSS
from Crypto.Hash import SHA256
from jose import jwk
from jose.utils import base64url_encode, base64url_decode, base64

def arbinenc(data, bits):
    size_raw = len(data).to_bytes(bits // 8, 'big')
    return size_raw + data

def arbindec(stream, bits):
    size = int.from_bytes(stream.read(bits // 8), 'big')
    return stream.read(size)

def arintenc(integer, bits):
    if integer < 256:
        return bytes((1,integer))
    else:
        integer = int(integer)
        size_bits = integer.bit_length()
        size_bits -= size_bits % -8 # round up to 8 bits
        int_raw = integer.to_bytes(size_bits // 8, 'big')
        size_raw = len(int_raw).to_bytes(bits // 8, 'big')
        return size_raw + int_raw

def arintdec(stream, bits):
    size = int.from_bytes(stream.read(bits // 8), 'big')
    return int.from_bytes(stream.read(size), 'big')


def b64dec(data):
    return base64url_decode(utf8enc_if_not_bytes(data))

def b64enc(data):
    return base64url_encode(data).decode()

def b64enc_if_not_str(data):
    if data is None:
        return None
    elif type(data) is str:
        return data
    else:
        return base64url_encode(data).decode()

def b64dec_if_not_bytes(data):
    if data is None:
        return b''
    elif isinstance(data, (bytes, bytearray)):
        return data
    else:
        return base64url_decode(data.encode())

def utf8enc_if_not_bytes(data):
    if data is None:
        return b''
    elif isinstance(data, (bytes, bytearray)):
        return data
    else:
        return data.encode()

def utf8dec_if_bytes(data):
    if data is None:
        return None
    elif isinstance(data, (bytes, bytearray)):
        return data.decode()
    else:
        return data

def le_u256dec(data):
    qword1, qword2, qword3, qword4 = struct.unpack('<4Q', data)
    return qword1 | (qword2 << 64) | (qword3 << 128) | (qword4 << 192)

def le_u256enc(valu):
    return struct.pack(
        '<4Q',
        value & 0xffffffffffffffff,
        (value >> 64) & 0xffffffffffffffff,
        (value >> 128) & 0xffffffffffffffff,
        (value >> 192) & 0xffffffffffffffff
    )

def create_tag(name, value, v2):
    b64name = utf8enc_if_not_bytes(name)
    b64value = utf8enc_if_not_bytes(value)
    if not v2:
        b64name = b64enc(b64name)
        b64value = b64enc(b64name)

    return {'name': b64name, 'value': b64value}

def normalize_tag(tag):
    name = utf8enc_if_not_bytes(tag['name'])
    value = utf8enc_if_not_bytes(tag['value'])

    return {'name': name, 'value': value}


def encode_tag(tag):
    b64name = b64enc(utf8enc_if_not_bytes(tag['name']))
    b64value = b64enc(utf8enc_if_not_bytes(tag['value']))

    return {'name': b64name, 'value': b64value}


def decode_tag(tag):
    name = b64dec(tag['name'])
    value = b64dec(tag['value'])

    return {'name': name, 'value': value}

def tags_to_dict(tags):
    return {
        tag['name']: tag['value']
        for tag in tags
    }

def dict_to_tags(tags_dict):
    return [
        create_tag(key, value)
        for key, value in tags_dict.items()
    ]

def owner_to_address(owner):
    result = b64enc(hashlib.sha256(b64dec(utf8enc_if_not_bytes(owner))).digest())

    return result


def winston_to_ar(winston) -> float:
    return float(winston) / 1000000000000

  
def ar_to_winston(ar_amount: str) -> str:
    return str(int(float(ar_amount) * 10**12))


def concat_buffers(buffers):
    total_length = 0

    for buffer in buffers:
        total_length += len(buffer)

    offset = 0

    temp = b'\x00' * total_length
    temp = bytearray(temp)
    for buffer in buffers:
        for i in range(len(buffer)):
            temp[i + offset] = buffer[i]

        offset += len(buffer)

    return bytes(temp)

from .. import logger
class response_stream_to_file_object:
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

import bisect, io
class ChunkStream(io.RawIOBase):

    # This could be much improved by calculating based on the 256KiB portions that
    # started after the 2.5 fork. To implement, see for example:
    # https://github.com/ArweaveTeam/arweave/blob/master/apps/arweave/src/ar_data_sync.erl#L118

    @classmethod
    def from_txid(cls, peer, txid):
        tx_offset = peer.tx_offset(txid)

        stream_last = tx_offset['offset']
        stream_size = tx_offset['size']
        stream_first = stream_last - stream_size + 1

        logger.info(f'Requesting bounds of first chunk of {txid} ...')
        first_size = peer.chunk_size(stream_first)
        offset_pairs = [
            (stream_first, stream_first + first_size - 1),
        ]

        if stream_first + first_size - 1 < stream_last:
            logger.info(f'Requesting bounds of last chunk of {txid} ...')
            offset_pairs.append(
                (stream_last - peer.chunk_size(stream_last) + 1, stream_last),
            )

        logger.info(f'{txid} measured.')

        return cls(peer, offset_pairs, stream_first, stream_last)

    def __init__(self, peer, first_last_chunk_offset_pairs, stream_first_offset, stream_last_offset = float('inf')):
        # instead of first/last chunk pairs, this could use pairs of absolute and suboffset  . if the suboffset is negative, it would be from the end. then fewer requests are needed.
        self.peer = peer
        self.chunks = [*first_last_chunk_offset_pairs]
        for first, last in self.chunks:
            assert first <= last
        self.chunks.sort(key = lambda interval: interval[0])
        assert stream_first_offset <= stream_last_offset
        self.stream_first = stream_first_offset
        self.stream_last = stream_last_offset
        self.chunk = None
        self.chunk_first, self.chunk_last = self.chunks[0]
        self.offset = self.chunk_first
        self.seek(0, io.SEEK_SET)
    def tell(self):
        return self.offset - self.stream_first
    def chunk_relative_tell(self):
        return self.offset - self.chunk_first
    def chunk_start_tell(self):
        return self.chunk_first
    def absolute_tell(self):
        return self.offset
    def readable(self):
        return True
    def seekable(self):
        return True
    def seek(self, offset, whence = io.SEEK_SET):
        if whence == io.SEEK_SET:
            offset += self.stream_first
        elif whence == io.SEEK_CUR:
            offset += self.offset
        elif whence == io.SEEK_END:
            offset += self.stream_last + 1

        if offset >= self.chunk_first and offset <= self.chunk_last:
            self.offset = offset
            return

        def walk_left(nearest_idx):
            chunk_first, chunk_last = self.chunks[nearest_idx]
            additional = []
            while chunk_first > offset:
                chunk_last = chunk_first - 1 # needed so chunk_size gets the _earlier_ chunk
                logger.info(f'Requesting bounds of chunk before {chunk_first - self.stream_first} to find {offset - self.stream_first}...')
                chunk_first = chunk_last - self.peer.chunk_size(chunk_last) + 1
                additional.append((chunk_first, chunk_last))
            self.chunks[nearest_idx : nearest_idx] = additional
            return chunk_first, chunk_last

        def walk_right(nearest_idx):
            chunk_first, chunk_last = self.chunks[nearest_idx]
            additional = []
            while chunk_last < offset:
                chunk_first = chunk_last + 1 # needed so chunk_size gets the _next_ chunk
                logger.info(f'Requesting bounds of chunk after {chunk_last - self.stream_first} to find {offset - self.stream_first}...')
                chunk_last = chunk_first + self.peer.chunk_size(chunk_first) - 1
                nearest_idx += 1
                additional.append((chunk_first, chunk_last))
            self.chunks[nearest_idx + 1 : nearest_idx + 1] = additional[::-1]
            return chunk_first, chunk_last

        import pdb; pdb.set_trace()
        right_idx = bisect.bisect_right(self.chunks, offset, key=lambda interval: interval[1])
        left_idx = right_idx - 1
        if right_idx == 0:
            # all intervals are after offset
            chunk_first, chunk_last = walk_left(right_idx)
        elif right_idx == len(self.chunks):
            # all intervals are prior to offset
            chunk_first, chunk_last = walk_right(left_idx)

        elif self.chunks[right_idx][0] - offset < offset - self.chunks[left_idx][1]:
            # the interval on the right is closer
            chunk_first, chunk_last = walk_left(right_idx)
        else:
            # the interval on the left is closer
            chunk_first, chunk_last = walk_right(left_idx)

        assert chunk_first <= offset and chunk_last >= offset

        self.chunk = None
        self.chunk_first = chunk_first
        self.chunk_last = chunk_last
        self.offset = offset

    def readinto(self, b):
        if self.chunk is None:
            result = self.peer.chunk2(self.chunk_first)
            self.chunk = result['chunk']
            assert len(self.chunk) - 1 == self.chunk_last - self.chunk_first 

        bytecount = min(len(b), self.chunk_last + 1 - self.offset)

        suboffset = self.offset - self.chunk_first
        b[ : bytecount] = self.chunk[suboffset : suboffset + bytecount]

        self.seek(bytecount, io.SEEK_CUR)

        return bytecount
