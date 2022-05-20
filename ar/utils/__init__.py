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
from Crypto.Signature import PKCS1_PSS
from Crypto.Hash import SHA256
from jose import jwk
from jose.utils import base64url_encode, base64url_decode, base64


def create_tag(name, value, v2):
    if v2:
        b64name = name
        b64value = value
    else:
        b64name = base64url_encode(name.encode('ascii')).decode()
        b64value = base64url_encode(value.encode('ascii')).decode()

    return {'name': b64name, 'value': b64value}


def encode_tag(tag):
    b64name = base64url_encode(tag['name'].encode('ascii')).decode()
    b64value = base64url_encode(tag['value'].encode('ascii')).decode()

    return {'name': b64name, 'value': b64value}


def decode_tag(tag):
    name = base64url_decode(tag['name'].encode())
    value = base64url_decode(tag['value'].encode())

    return {'name': name, 'value': value}


def owner_to_address(owner):
    result = base64url_encode(hashlib.sha256(base64url_decode(owner.encode('ascii'))).digest()).decode()

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
