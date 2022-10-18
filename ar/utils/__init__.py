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

import decimal, math
import hashlib
import struct
from Crypto.Signature import PKCS1_PSS
from Crypto.Hash import SHA256
from jose import jwk

from .serialization import *

# all this tags stuff could be a Tags class

def create_tag(name, value, v2):
    b64name = utf8enc_if_not_bytes(name)
    b64value = utf8enc_if_not_bytes(value)
    if not v2:
        b64name = b64enc(b64name)
        b64value = b64enc(b64value)

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

def change_tag(tags, name, value, condense_to_one=False):
    name = utf8enc_if_not_bytes(name)
    newvalue = utf8enc_if_not_bytes(value)
    to_change = None
    to_remove = []
    for idx, tag in enumerate(tags):
        if tag['name'] == name:
            if to_change is not None:
                if condense_to_one:
                    to_remove.append(idx)
                else:
                    raise Exception('more than one tag with name')
            to_change = tag
    if to_change is not None:
        to_change['value'] = newvalue
        for idx in to_remove[::-1]:
            tags.pop(idx)
    else:
        tags.append(create_tag(name, newvalue, True))
    return tags

def ensure_tag(tags, name, value):
    name = utf8enc_if_not_bytes(name)
    value = utf8enc_if_not_bytes(value)
    for tag in tags:
        if tag['name'] == name and tag['value'] == value:
            return tags
    tags.append(dict(name=name, value=value))
    return tags

def get_tags(tags, name):
    name = utf8enc_if_not_bytes(name)
    return [tag['value'] for tag in tags if tag['name'] == name]

def owner_to_address(owner):
    result = b64enc(hashlib.sha256(b64dec(utf8enc_if_not_bytes(owner))).digest())

    return result


def winston_to_ar(winston) -> float:
    return decimal.Decimal(winston) / 1000000000000

  
def ar_to_winston(ar_amount: str) -> str:
    return str(math.ceil(decimal.Decimal(ar_amount) * 10**12))


def concat_buffers(buffers):
    return b''.join(buffers)
