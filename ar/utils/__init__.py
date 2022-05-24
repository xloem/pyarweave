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
    size_raw = erlintenc(len(data), bits)
    return size_raw + data

def arbindec(stream, bits):
    size = erlintdec(stream, bits)
    return stream.read(size)

def arintenc(integer, bits):
    int_raw = erlintenc(integer)
    size_raw = erlintenc(len(int_raw), bits)
    return size_raw + int_raw

def arintdec(stream, bits):
    size = erlintdec(stream, bits)
    return erlintdec(stream, size * 8)

def erlintenc(integer, bits = None):
    if integer < 0:
        raise NotImplementedError('negative integers not implemented yet')
    if bits is None:
        if integer == 0:
            bits = 8
        else:
            bits = integer.bit_length()
            bits -= bits % -8 # round up to 8 bits
    else:
        if integer >= (1 << bits):
            raise OverflowError(integer, bits)
    size = bits // 8
    aligned_size = size - size % -8 # round up to 8 bytes
    result = bytearray(aligned_size)
    for qword in range(aligned_size-8,-8,-8):
        struct.pack_into('>Q', result, qword, integer & 0xffffffffffffffff)
        integer >>= 64
    return result[-size:]

def erlintdec(stream, bits):
    integer = 0
    size = bits // 8
    data = stream.read(size)
    aligned_size = size - size % -8 # round up to 8 bytes
    data = data.rjust(aligned_size, b'\0')
    for qword in range(0, size, 8):
        integer = (integer << 64) | struct.unpack_from('>Q', data, qword)[0]
    return integer


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

def be_u256dec(data):
    qword4, qword3, qword2, qword1 = struct.unpack('>4Q', data)
    return qword1 | (qword2 << 64) | (qword3 << 128) | (qword4 << 192)

def be_u256enc(valu):
    return struct.pack(
        '>4Q',
        (value >> 192) & 0xffffffffffffffff,
        (value >> 128) & 0xffffffffffffffff,
        (value >> 64) & 0xffffffffffffffff,
        value & 0xffffffffffffffff
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
