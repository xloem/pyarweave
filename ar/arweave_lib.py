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

import json
import logging
import hashlib
from jose import jwk
from jose.backends.cryptography_backend import CryptographyRSAKey
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_PSS
from Crypto.Hash import SHA256
from .utils import (
    winston_to_ar,
    owner_to_address,
)
from .peer import Peer

from . import DEFAULT_API_URL, logger

TRANSACTION_DATA_LIMIT_IN_BYTES = 2000000



class Wallet(object):
    HASH = 'sha256'

    def _set_jwk_params(self):
        self.jwk_data['p2s'] = ''
        self.jwk = jwk.construct(self.jwk_data, algorithm=jwk.ALGORITHMS.RS256)
        self.rsa = RSA.importKey(self.jwk.to_pem())

        self.owner = self.jwk_data.get('n')
        self.address = owner_to_address(self.owner)

        self.peer = Peer(DEFAULT_API_URL)
    @property
    def api_url(self):
        return self.peer.api_url
    @api_url.setter
    def set_api_url(self, api_url):
        self.peer.api_url = api_url

    def __init__(self, jwk_file='jwk_file.json'):
        with open(jwk_file, 'r') as j_file:
            self.jwk_data = json.loads(j_file.read())
        self._set_jwk_params()

    @classmethod
    def from_data(cls, jwk_data):
        wallet = cls.__new__(cls)
        wallet.jwk_data = jwk_data
        wallet._set_jwk_params()
        return wallet

    @property
    def balance(self):
        balance = self.peer.wallet_balance(self.address)
        return winston_to_ar(balance)

    def sign(self, message):
        h = SHA256.new(message)
        signed_data = PKCS1_PSS.new(self.rsa).sign(h)
        return signed_data

    def verify(self):
        pass

    def get_last_transaction_id(self):
        self.last_tx = self.peer.tx_anchor()
        return self.last_tx



def arql(wallet, query):
    """
    Creat your query like so:
    query = {
        "op": "and",
          "expr1": {
            "op": "equals",
            "expr1": "from",
            "expr2": "hnRI7JoN2vpv__w90o4MC_ybE9fse6SUemwQeY8hFxM"
          },
          "expr2": {
            "op": "or",
            "expr1": {
              "op": "equals",
              "expr1": "type",
              "expr2": "post"
            },
            "expr2": {
              "op": "equals",
              "expr1": "type",
              "expr2": "comment"
            }
          }
    :param wallet:
    :param query:
    :return list of Transaction instances:
    """

    return Peer(DEFAULT_API_URL).arql(query)


def arql_with_transaction_data(wallet, query):
    """
    Creat your query like so:
    query = {
        "op": "and",
          "expr1": {
            "op": "equals",
            "expr1": "from",
            "expr2": "hnRI7JoN2vpv__w90o4MC_ybE9fse6SUemwQeY8hFxM"
          },
          "expr2": {
            "op": "or",
            "expr1": {
              "op": "equals",
              "expr1": "type",
              "expr2": "post"
            },
            "expr2": {
              "op": "equals",
              "expr1": "type",
              "expr2": "comment"
            }
          }
    :param wallet:
    :param query:
    :return list of Transaction instances:
    """

    transaction_ids = arql(wallet, query)
    if transaction_ids:
        transactions = []
        for transaction_id in transaction_ids:
            tx = Transaction(wallet, id=transaction_id)
            tx.get_transaction()
            tx.get_data()

            transactions.append(tx)

    return None
