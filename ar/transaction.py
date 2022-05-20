import json
import os
import io
import hashlib
from jose import jwk
from jose.utils import base64url_encode
from .utils import (
    winston_to_ar,
    ar_to_winston,
    create_tag,
    encode_tag,
    decode_tag,
    base64url_decode
)
from .peer import Peer
from .utils.deep_hash import deep_hash
from .utils.merkle import compute_root_hash, generate_transaction_chunks
from . import logger

class Transaction(object):
    def __init__(self, wallet, **kwargs):
        self.jwk_data = wallet.jwk_data
        self.jwk = jwk.construct(self.jwk_data, algorithm='RS256')
        self.wallet = wallet

        self.id = kwargs.get('id', '')
        self.last_tx = wallet.get_last_transaction_id()
        self.owner = self.jwk_data.get('n')
        self.tags = []
        self.format = kwargs.get('format', 2)

        self.peer = Peer()
        self.chunks = None

        data = kwargs.get('data', '')
        self.data_size = len(data)

        if type(data) is bytes:
            self.data = base64url_encode(data)
        else:
            self.data = base64url_encode(data.encode('utf-8'))

        if self.data is None:
            self.data = ''

        self.file_handler = kwargs.get('file_handler', None)
        if self.file_handler:
            self.uses_uploader = True
            self.data_size = os.stat(kwargs['file_path']).st_size
        else:
            self.uses_uploader = False

        if kwargs.get('transaction'):
            self.from_serialized_transaction(kwargs.get('transaction'))
        else:
            self.data_root = ''

            self.data_tree = []

            self.target = kwargs.get('target', '')
            self.to = kwargs.get('to', '')

            if self.target == '' and self.to != '':
                self.target = self.to

            self.quantity = kwargs.get('quantity', '0')
            if float(self.quantity) > 0:
                if self.target == '':
                    raise ArweaveException(
                        'Unable to send {} AR without specifying a target address'.format(self.quantity))

                # convert to winston
                self.quantity = ar_to_winston(float(self.quantity))

            reward = kwargs.get('reward', None)
            if reward is not None:
                self.reward = reward

            self.signature = ''
            self.status = None
    @property
    def api_url(self):
        return self.peer.api_url
    @api_url.setter
    def set_api_url(self, api_url):
        self.peer.api_url = api_url

    def from_serialized_transaction(self, transaction_json):
        if type(transaction_json) == str:
            transaction_json = json.loads(transaction_json)
        if type(transaction_json) == dict:
            self.load(transaction_json)
        else:
            raise ArweaveException(
                'Please supply a string or dict containing json to initialize a serialized transaction')

    def get_reward(self, data_size, target_address=None):
        reward = self.peer.price(data_size, target_address)
        return winston_to_ar(reward)

    def add_tag(self, name, value):
        tag = create_tag(name, value, self.format == 2)
        self.tags.append(tag)

    def encode_tags(self):
        tags = []
        for tag in self.tags:
            tags.append(encode_tag(tag))

        self.tags = tags

    def sign(self):
        data_to_sign = self.get_signature_data()

        raw_signature = self.wallet.sign(data_to_sign)

        self.signature = base64url_encode(raw_signature)

        self.id = base64url_encode(hashlib.sha256(raw_signature).digest())

        if type(self.id) == bytes:
            self.id = self.id.decode()

    def get_signature_data(self):
        self.reward = str(self.get_reward(self.data_size, target_address=self.target if len(self.target) > 0 else None))

        if int(self.data_size) > 0 and self.data_root == '' and not self.uses_uploader:
            if type(self.data) == str:
                root_hash = compute_root_hash(io.BytesIO(base64url_decode(self.data.encode('utf-8'))))

            if type(self.data) == bytes:
                root_hash = compute_root_hash(io.BytesIO(base64url_decode(self.data)))

            self.data_root = base64url_encode(root_hash)

        if self.format == 1:
            tag_str = ''

            for tag in self.tags:
                name, value = decode_tag(tag)
                tag_str += '{}{}'.format(name.decode(), value.decode())

            owner = base64url_decode(self.jwk_data['n'].encode())
            target = base64url_decode(self.target)
            data = base64url_decode(self.data)
            quantity = self.quantity.encode()
            reward = self.reward.encode()
            last_tx = base64url_decode(self.last_tx.encode())

            signature_data = owner + target + data + quantity + reward + last_tx + tag_str.encode()

        if self.format == 2:
            if self.uses_uploader:
                self.prepare_chunks()

            tag_list = [[tag['name'].encode(), tag['value'].encode()] for tag in self.tags]

            signature_data_list = [
                '2'.encode(),
                base64url_decode(self.jwk_data['n'].encode()),
                base64url_decode(self.target.encode()),
                str(self.quantity).encode(),
                self.reward.encode(),
                base64url_decode(self.last_tx.encode()),
                tag_list,
                str(self.data_size).encode(),
                base64url_decode(self.data_root)]

            signature_data = deep_hash(signature_data_list)

        return signature_data

    def send(self):
        try:
            self.peer.send_tx(self.json_data)
        except ArweaveException:
            pass

        return self.last_tx

    def to_dict(self):

        if self.data is None:
            self.data = ''

        data = {
            'data': self.data.decode() if type(self.data) == bytes else self.data,
            'id': self.id.decode() if type(self.id) == bytes else self.id,
            'last_tx': self.last_tx,
            'owner': self.owner,
            'quantity': self.quantity,
            'reward': self.reward,
            'signature': self.signature.decode(),
            'tags': self.tags,
            'target': self.target
        }

        if self.format == 2:
            self.encode_tags()
            data['tags'] = self.tags
            data['format'] = 2
            if len(self.data_root) > 0:
                data['data_root'] = self.data_root.decode()
            else:
                data['data_root'] = ''
            data['data_size'] = str(self.data_size)
            data['data_tree'] = []

        return data

    @property
    def json_data(self):
        data = self.to_dict()

        json_str = json.dumps(data)

        logger.debug(json_str)

        return json_str.replace(' ', '')

    def get_status(self):
        try:
            self.status = self.peer.tx_status(self.id)
        except ArweaveException:
            self.status = 'PENDING'
        return self.status

    def get_transaction(self):
        try:
            self.load(self.peer.tx(self.id))
        except ArweaveException as exception:
            pass

    def get_price(self):
        try:
            price = self.peer.price(self.data_size)
            return winston_to_ar(price)
        except ArweaveException as exception:
            pass

    def get_data(self):
        self.data = self.peer.data(self.id)
        return self.data

    def load(self, json_data):
        self.data = json_data.get('data', '')
        self.last_tx = json_data.get('last_tx', '')
        self.owner = json_data.get('owner', '')
        self.quantity = json_data.get('quantity', '')
        self.reward = json_data.get('reward', '')
        self.signature = json_data.get('signature', '')
        self.tags = [decode_tag(tag) for tag in json_data.get('tags', [])]
        self.target = json_data.get('target', '')
        self.data_size = json_data.get('data_size', '0')
        self.data_root = json_data.get('data_root', '')
        self.data_tree = json_data.get('data_tree', [])

        logger.debug(json_data)

    def prepare_chunks(self):
        if not self.chunks:
            self.chunks = generate_transaction_chunks(self.file_handler)
            self.data_root = base64url_encode(self.chunks.get('data_root'))

        if not self.chunks:
            self.chunks = {
                'chunks': [],
                'data_root': b'',
                'proof': []
            }

            self.data_root = ''

    def get_chunk(self, idx):
        if self.chunks is None:
            raise ArweaveException('Chunks have not been prepared')

        proof = self.chunks.get('proofs')[idx]
        chunk = self.chunks.get('chunks')[idx]

        self.file_handler.seek(chunk.min_byte_range)

        chunk_data = self.file_handler.read(chunk.data_size)

        return {
            'data_root': self.data_root.decode(),
            'data_size': str(self.data_size),
            'data_path': base64url_encode(proof.proof),
            'offset': str(proof.offset),
            'chunk': base64url_encode(chunk_data)
        }
