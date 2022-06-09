from jose.utils import base64url_encode, base64url_decode, base64

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

def varintenc(num):
    output = bytearray()
    while True:
        byte = num & 0x7f
        num >>= 7
        if num:
            output.append(byte | 0x80)
        else:
            output.append(byte)
            return output

def varintdec(stream):
    result = 0
    bits = 0
    while True:
        byte = stream.read(1)[0]
        result |= (byte & 0x7f) << bits
        if byte & 0x80:
            bits += 7
        else:
            return result

def zigzagenc(num):
    num <<= 1
    return ~num if num < 0 else num

def zigzagdec(zz):
    if zz & 1:
        zz = ~zz
    return zz >> 1
