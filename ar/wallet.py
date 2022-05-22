import json
from jose import jwk
from jose.utils import base64url_decode
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS
from Crypto.Hash import SHA256
from .utils import (
    winston_to_ar,
    owner_to_address,
)
from . import DEFAULT_API_URL
from .peer import Peer


class Wallet(object):
    HASH = 'sha256'

    def __init__(self, jwk_file='jwk_file.json', jwk_data=None):
        if jwk_data is not None:
            self.jwk_data = jwk_data
        else:
            with open(jwk_file, 'r') as j_file:
                self.jwk_data = json.loads(j_file.read())

        self.jwk_data['p2s'] = ''
        self.jwk = jwk.construct(self.jwk_data, algorithm=jwk.ALGORITHMS.RS256)
        self.rsa = RSA.importKey(self.jwk.to_pem())

        self.owner = self.jwk_data.get('n')
        self.address = owner_to_address(self.owner)

        self.peer = Peer(DEFAULT_API_URL)

    @classmethod
    def generate(cls, bits = 4096, jwk_file = None):
        key = RSA.generate(4096)
        jwk_data = jwk.RSAKey(key.export_key(), jwk.ALGORITHMS.RS256).to_dict()
        if jwk_file is not None:
            with open(jwk_file, 'xt') as jwk_fh:
                json.dump(jwk_data, fh)
        return cls(jwk_file = jwk_file, jwk_data = jwk_data)

    @classmethod
    def from_data(cls, jwk_data):
        return cls(jwk_data = jwk_data)

    @property
    def api_url(self):
        return self.peer.api_url
    @api_url.setter
    def set_api_url(self, api_url):
        self.peer.api_url = api_url

    @property
    def balance(self):
        balance = self.peer.wallet_balance(self.address)
        return winston_to_ar(balance)

    @property
    def raw_owner(self):
        return base64url_decode(self.jwk_data['n'].encode())

    def sign(self, message):
        h = SHA256.new(message)
        signed_data = PKCS1_PSS.new(self.rsa).sign(h)
        return signed_data

    def verify(self):
        pass

    def get_last_transaction_id(self):
        self.last_tx = self.peer.tx_anchor()
        return self.last_tx
