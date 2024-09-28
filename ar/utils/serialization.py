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

def erlintenc(integer, bits):
    integer = int(integer)
    return integer.to_bytes(bits // 8, 'big')

def erlintdec(stream, bits):
    int_size = bits // 8
    int_raw = stream.read(int_size)
    if len(int_raw) != int_size:
        raise ArweaveException('stream terminated early')
    return int.from_bytes(int_raw, 'big')

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
    if integer is None:
        return bytes(bits // 8)
    elif integer < 256 and bits == 8:
        return bytes([1,integer])
    else:
        integer = int(integer)
        size_bits = integer.bit_length()
        if size_bits == 0:
            size_bits = 8
        else:
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
    if size == 0:
        return None
    int_raw = stream.read(size)
    if len(int_raw) != size:
        raise ArweaveException('stream terminated early')
    return int.from_bytes(int_raw, 'big')

class AutoRaw:
    def __getattr(self, attr):
        return super().__getattribute__(attr)
    def __hasattr(self, attr):
        try:
            self.__getattr(attr)
            return True
        except AttributeError:
            return False
    def __hasprop(self, attr):
        try:
            clsattr = getattr(type(self), attr)
            return type(clsattr) is property
        except AttributeError:
            return False
    def __getattr__(self, attr):
        if not self.__hasattr(attr):
            if attr.endswith('_raw'):
                str_attr = attr[:-4]
                if not self.__hasprop(str_attr):
                    try:
                        str_val = self.__getattr(str_attr)
                    except:
                        pass
                    else:
                        if type(str_val) in [list, tuple]:
                            return [b64dec(item) for item in str_val]
                        else:
                            return b64dec(str_val)
            else:
                raw_attr = attr + '_raw'
                if not self.__hasprop(raw_attr):
                    try:
                        raw_val = self.__getattr(raw_attr)
                    except:
                        pass
                    else:
                        if type(raw_val) in [list, tuple]:
                            return [b64enc(item) for item in raw_val]
                        else:
                            return b64enc(raw_val)
        return super().__getattribute__(attr)
    def __setattr__(self, attr, val):
        if not self.__hasattr(attr):
            if attr.endswith('_raw'):
                str_attr = attr[:-4]
                if not self.__hasprop(str_attr) and self.__hasattr(str_attr):
                    return super().__setattr__(str_attr, b64enc(val))
            else:
                raw_attr = attr + '_raw'
                if not self.__hasprop(raw_attr) and self.__hasattr(raw_attr):
                    return super().__setattr__(raw_attr, b64dec(val))
        return super().__setattr__(attr, val)
