from jose import jwk
from Crypto.Util.number import bytes_to_long
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pss

class Rsa4096Pss: # arweave-style
    signatureType = 1
    ownerLength = 512
    signatureLength = 512

    @staticmethod
    def sign(jwkjson, databytes):
        jwkobj = jwk.construct(jwkjson, algorithm=jwk.ALGORITHMS.RS256)
        key = RSA.importKey(jwkobj.to_pem())
        hash = SHA256.new(databytes)
        return pss.new(key, salt_bytes=478).sign(hash)

    @staticmethod
    def verify(ownerbytes, databytes, signaturebytes):
        key = RSA.construct((bytes_to_long(ownerbytes), 65537))
        hash = SHA256.new(databytes)
        try:
            pss.new(key, salt_bytes=478).verify(hash, signaturebytes)
            return True
        except (ValueError, TypeError):
            return False

class Curve25519:
    signatureType = 2
    ownerLength = 32
    signatureLength = 64

class Secp256k1: # ethereum-style
    signatureType = 3
    ownerLength = 65
    signatureLength = 65

class solana:
    signatureType = 4
    ownerLength = 32
    signatureLength = 64

configs = {
    keycfg.signatureType: keycfg
    for keycfg in (Rsa4096Pss, Curve25519, Secp256k1, solana)
}

DEFAULT_CONFIG = configs[1]
