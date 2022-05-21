class Rsa4096Pss: # arweave-style
    signatureType = 1
    ownerLength = 512
    signatureLength = 512

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

configs = [None, Rsa4096Pss, Curve25519, Secp256k1, solana]

DEFAULT_CONFIG = configs[1]
