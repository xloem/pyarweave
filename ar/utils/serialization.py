from jose.utils import base64url_encode, base64url_decode, base64
from .. import ArweaveException

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

def arbinenc(data, bits):
    size_raw = len(data).to_bytes(bits // 8, 'big')
    return size_raw + data

def arbindec(stream, bits):
    size_size = bits // 8
    size_raw = stream.read(size_size)
    if len(size_raw) != size_size:
        raise ArweaveException('stream terminated early')
    size = int.from_bytes(size_raw, 'big')
    data = stream.read(size)
    if len(data) != size:
        raise ArweaveException('stream terminated early')
    return data

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
    size_size = bits // 8
    size_raw = stream.read(size_size)
    if len(size_raw) != size_size:
        raise ArweaveException('stream terminated early')
    size = int.from_bytes(size_raw, 'big')
    int_raw = stream.read(size)
    if len(int_raw) != size:
        raise ArweaveException('stream terminated early')
    return int.from_bytes(int_raw, 'big')
