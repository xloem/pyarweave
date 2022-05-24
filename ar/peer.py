import erlang
import requests
import json

from . import DEFAULT_API_URL, logger, ArweaveException
from .utils import response_stream_to_file_object, b64dec, be_u256dec

class HTTPClient:
    def __init__(self, api_url, timeout = None, retries = 5):
        self.api_url = api_url
        self.session = requests.Session()
        max_retries = requests.adapters.Retry(total=retries, backoff_factor=0.1, status_forcelist=[500,502,503,504]) # from so
        self.session.mount('http://', requests.adapters.HTTPAdapter(max_retries=max_retries))
        self.session.mount('https://', requests.adapters.HTTPAdapter(max_retries=max_retries))
        self.timeout = timeout

    def _get(self, *params, **request_kwparams):
        if len(params) and params[-1][0] == '?':
            url = self.api_url + '/' + '/'.join(params[:-1]) + params[1]
        else:
            url = self.api_url + '/' + '/'.join(params)

        response = self.session.request(**{'method': 'GET', 'url': url, 'timeout': self.timeout, **request_kwparams})

        if response.status_code >= 200 and response.status_code < 300 and int(response.headers.get('content-length', 1)) > 0:
            return response
        else:
            logger.error(response.text)
            raise ArweaveException(response.text)

    def _post(self, data, *params, headers = {}, **request_kwparams):
        if len(params) and params[-1][0] == '?':
            url = self.api_url + '/' + '/'.join(params[:-1]) + params[1]
        else:
            url = self.api_url + '/' + '/'.join(params)

        headers = {**headers}

        if type(data) is dict:
            if type(data) is dict:
                headers.setdefault('Content-Type', 'application/json')
            response = self.session.request(**{'method': 'POST', 'url': url, 'json': data, 'headers': headers, 'timeout': self.timeout, **request_kwparams})
        else:
            if isinstance(data, (bytes, bytearray)):
                headers.setdefault('Content-Type', 'application/octet-stream')
            else:
                headers.setdefault('Content-Type', 'text/plain')
            response = self.session.request(**{'method': 'POST', 'url': url, 'data': data, 'headers': headers, 'timeout': self.timeout, **request_kwparams})

        # logger.debug('{}\n\n{}'.format(response.text, data))

        if response.status_code >= 200 and response.status_code < 300:
            # logger.debug('RESPONSE 200: {}'.format(response.text))
            return response
        else:
            # logger.error('{}\n\n{}'.format(response.text, data))
            raise ArweaveException(response.text, data, url)

class Peer(HTTPClient):
    # peer api [incomplete]:
    # - https://docs.arweave.org/developers/server/http-api
    # - https://github.com/ArweaveTeam/arweave/blob/master/apps/arweave/src/ar_http_iface_middleware.erl#L132
    # - https://github.com/ArweaveTeam/arweave/blob/master/apps/arweave/src/ar_http_iface_client.erl
    def __init__(self, api_url = DEFAULT_API_URL, timeout = None, retries = 5):
        super().__init__(api_url, timeout, retries)

    def info(self):
        '''
        Get the current network information including
        height, current block, and other properties.

        {
          "network": "arweave.N.1",
          "version": 5,
          "release": 43,
          "height": 551511,
          "current": "XIDpYbc3b5iuiqclSl_Hrx263Sd4zzmrNja1cvFlqNWUGuyymhhGZYI4WMsID1K3",
          "blocks": 97375,
          "peers": 64,
          "queue_length": 0,
          "node_state_latency": 18
        }
        '''
        response = self._get('info')
        return response.json()

    def time(self):
        '''Return the current universal time in seconds.'''
        response = self._get('time')
        return int(response.text)

    def tx_pending(self):
        '''Return all mempool transactions.'''
        response = self._get('tx/pending')
        return response.json()

    def queue(self):
        '''Return outgoing transaction priority queue.'''
        response = self._get('queue')
        return response.json()

    def tx_status(self, hash):
        '''
        Return additional information about the transaction with the given identifier (hash).

        {
            "block_height": "<Height>,
            "block_indep_hash": "<BH>",
            "number_of_confirmations": "<NumberOfConfirmations>",
        }
        '''
        response = self._get('tx', txid, 'status')
        return response.json()

    def tx(self, txid):
        '''Return a JSON-encoded transaction.'''
        response = self._get('tx', txid)
        tx = response.json()
        for tag in tx['tags']:
            for key in tag:
                tag[key] = b64dec(tag[key].encode())
        return tx

    def tx2(self, txid):
        '''Return a binary-encoded transaction.'''
        response = self._get('tx2', txid)
        return response.content

    def unconfirmed_tx(self, txid):
        '''Return a possibly unconfirmed JSON-encoded transaction.'''
        response = self._get('unconfirmed_tx', txid)
        tx = response.json()
        for tag in tx['tags']:
            for key in tag:
                tag[key] = b64dec(tag[key].encode())
        return tx

    def unconfirmed_tx2(self, txid):
        '''Return a possibly unconfirmed binary-encoded transaction.'''
        response = self._get('unconfirmed_tx2', txid)
        return response.content

    def arql(self, logical_expression):
        '''
        Return the transaction IDs of all txs where the tags match the given set
        of key value pairs, any logical expression valid in ar_parser.
        
        Logical Expression:
        {
            op:     { and | or | equals }
            expr1:  { string | logical expression }
            expr2:  { string | logical expression }
        }
    
        Example:
        {
            "op": "and",
            ": {
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
        }
        '''
        response = self._post(logical_expression, 'arql')
        return response.json()

    def graphql(self, query):
        response = self._post({
            'operationName': None,
            'query': query,
            'variables': {}
        }, 'graphql')
        return response.json()

    def tx_data_html(self, txid):
        '''
        Return the data field of the transaction specified via the transaction ID (hash)
        served as HTML.
        '''
        response = self._get('tx', txid, 'data.html')
        return response.content

    def sync_buckets(self):
        '''
        Return a compact but imprecise representation of the synced data -
        a bucket size and a map where every key is the sequence number of the bucket,
        every value - the percentage of data synced in the reported bucket.
        '''
        response = self._get('sync_buckets')
        return erlang.binary_to_term(response.content)

    def data_sync_record(self, start = None, limit = None, format = 'etf'):
        '''
        Return a high-to-low list of intervals of synced data ranges.

        start: pick intervals with higher bound >= start
        limit: the number of intervals to pick
        format: 'json' or 'etf', serialize in JSON or Erlang Term Format
        '''
        if format == 'json':
            headers = {'content-type':'application/json'}
        else:
            headers = {}
        if start is None and limit is None:
            response = self._get('data_sync_record', headers=headers)
        else:
            if start is None:
                start = -1
            if limit is None:
                limit = -1
            response = self._get('data_sync_record', str(start), str(limit), headers=headers)
        if format == 'json':
            try:
                intervals = response.json()
                intervals = [
                    (int(key), int(value))
                    for interval in intervals
                    for key, value in interval.items()
                ]
                return intervals
            except json.decoder.JSONDecodeError:
                # some proxies, such as arweave.net 2022-05, ignore the header and return etf
                pass
        intervals = erlang.binary_to_term(response.content)
        intervals = [
            (be_u256dec(left.value), be_u256dec(right.value))
            for left, right in intervals
        ]
        return intervals

    def chunk(self, offset, packing = 'unpacked', bucket_based_offset = False):
        '''

        {packing} := { 'unpacked' | 'spora_2_5' | 'any' }

        {
            "tx_path",
            "packing",
            "data_path",
            "chunk"
        }
        '''

        headers = {
            'x-packing': packing
        }
        if bucket_based_offset:
            headers['x-bucket-based-offset'] = '1'

        response = self._get('chunk', str(offset), headers=headers)
        result = response.json()
        for key in ('tx_path', 'data_path', 'chunk'):
            result[key] = b64dec(result[key])
        return result

    def chunk2(self, offset, packing = 'unpacked', bucket_based_offset = False):
        '''

        {packing} := { 'unpacked' | 'spora_2_5' | 'any' }

        Returns: b[
            chunk_size      3 bytes, big-endian
            chunk           chunk_size bytes

            txpath_size     3 bytes, big-endian
            txpath          txpath_size bytes

            datapath_size   3 bytes, big-endian
            datapath        datapath_size bytes

            packing2_size   1 byte
            packing2        packing2_size bytes
        ]
        '''

        headers = {
            'x-packing': packing
        }
        if bucket_based_offset:
            headers['x-bucket-based-offset'] = '1'

        response = self._get('chunk2', str(offset), headers=headers)
        return response.content

    def tx_offset(self, hash):
        '''
        Get the absolute end offset and size of the transaction

        The client may use this information to collect transaction chunks. Start with
        the end offset and fetch a chunk via chunk(<offset>). Subtract its size
        from the transaction size - if there are more chunks to fetch, subtract the
        size of the chunk from the offset and fetch the next chunk.

        {
            "offset": <Offset>,
            "size": <Size>
        }
        '''
        response = self._get('tx', hash, 'offset')
        result = response.json()
        result['offset'] = int(result['offset'])
        result['size'] = int(result['size'])
        return result

    def send_chunk(self, json_data):
        '''
        Upload Data Chunks

        json_data:
        {
          "data_root": "<Base64URL encoded data merkle root>",
          "data_size": "a number, the size of transaction in bytes",
          "data_path": "<Base64URL encoded inclusion proof>",
          "chunk": "<Base64URL encoded data chunk>",
          "offset": "<a number from [start_offset, start_offset + chunk size), relative to other chunks>"
        }
        '''
        response = self._post(json_data, 'chunk')
        return response.json()

    def block_announcement(self, block_announcement):
        '''
        Accept an announcement of a block. Returns optional missing transactions and chunk.
        412: no previous block
        208: already processing the block
        '''
        response = self._post(block_announcement, 'block_announcement')
        return response.json()

    def send_block(self, block):
        '''Accept a JSON-encoded block with Base64Url encoded fields.'''
        response = self._post(block, 'block')
        return response.text # OK

    def send_block2(self, block):
        '''Accept a binary-encoded block.'''
        response = self._post(block, 'block2')
        return response.text # OK

    def wallet(self, secret):
        '''
        Generate a wallet and receive a secret key identifying it.
        Requires internal_api_secret startup option to be set.
        WARNING: only use it if you really really know what you are doing.

        {
            "wallet_address": <Address>,
            "wallet_access_code": <WalletAccessCode>
        }
        '''
        response = self._post(secret, 'wallet')
        return response.json()

    def send_tx(self, json_data):
        '''
        Submit a new transaction to the network.

        The object should have the attributes described in:
        https://docs.arweave.org/developers/server/http-api#transaction-format
        '''
        response = self._post(json_data, 'tx')
        return response.text # OK

    def send_tx2(self, binary_data):
        '''Submit a new binary-encoded transaction to the network.'''
        response = self._post(binary_data, 'tx2')
        return response.text # OK

    def unsigned_tx(self, secret):
        '''
        Sign and send a tx to the network.

        Fetches the wallet by the provided key generated via wallet().
        Requires internal_api_secret startup option to be set.
        WARNING: only use it if you really really know what you are doing.
        '''
        response = self._post(secret, 'unsigned_tx')
        return response.json()

    def peers(self):
        '''
        Get the list of peers from the node.

        Nodes can only respond with peers they currently know about, so
        this will not be an exhaustive or complete list of nodes on the network.
        '''
        response = self._get('peers')
        return response.json()

    def price(self, bytes=0, target_address=None):
        '''Return the estimated transaction fee not including a new wallet fee.

        This endpoint is used to calculate the minimum fee (reward) for a transaction
        of a specific size, and possibly to a specific address.This endpoint should
        always be used to calculate transaction fees as closely to the submission time
        as possible. Pricing is dynamic and determined by the network, so it's not
        always possible to accurately calculate prices offline or ahead of
        time.Transactions with a fee that's too low will simply be rejected.

        bytes:
            The number of bytes to go into the transaction data field.
            If sending AR to another wallet with no data attached, then 0 should be used.

        target:
            The target wallet address if sending AR to another wallet.
        '''
        if target_address is not None:
            response = self._get('price', str(bytes), target_address)
        else:
            response = self._get('price', str(bytes))
        return response.text

    def hash_list(self, from_height = None, to_height = None, as_hash_list = True):
        '''
        Return the current JSON-encoded hash list held by the node.
        Deprecated for block_index().
        '''
        kwparams = {}
        if as_hash_list:
            kwparams['headers'] = {'x-block-format': '2'}
        if from_height is not None or to_height is not None:
            response = self._get('hash_list', str(from_height), str(to_height), **kwparams)
        else:
            response = self._get('hash_list', **kwparams)
        return response.json()

    def block_index(self, from_height = None, to_height = None, as_hash_list = False):
        '''Return the current JSON-encoded hash list held by the node.'''
        kwparams = {}
        if as_hash_list:
            kwparams['headers'] = {'x-block-format': '2'}
        if from_height is not None or to_height is not None:
            response = self._get('block_index', str(from_height), str(to_height), **kwparams)
        else:
            response = self._get('block_index', **kwparams)
        return response.json()
    
    def block_index2(self):
        '''Return the current binary-encoded block index held by the node.'''
        response = self._get('block_index2')
        return response.content

    def recent_hash_list(self):
        response = self._get('recent_hash_list')
        return response.json()

    def recent_hash_list_diff(self, hash_list_binary):
        '''
        Accept the list of independent block hashes ordered from oldest to newest
        and return the deviation of our hash list from the given one.
        Peers may use this endpoint to make sure they did not miss blocks or learn
        about the missed blocks and their transactions so that they can catch up quickly.
        '''
        response = self._post(hash_list_binary, 'recent_hash_list_diff', method='GET')
        return response.json()

    def wallet_list(self, encoded_root_hash = None, encoded_cursor = None, wallet_list_chunk_size = None):
        '''
        Return the current wallet list held by the node, or optionally a bunch of wallets,
        up to wallet_list_chunk_size, from the tree with the given root hash, optionally
        starting with the provided cursor, taken the wallet addresses are picked in the
        ascending alphabetical order.
        '''
        if wallet_list_chunk_size is not None:
            wallet_list_chunk_size = f'?{wallet_list_chunk_size}'
        else:
            wallet_list_chunk_size = ''
        if encoded_cursor is not None:
            response = self._get('wallet_list', encoded_root_hash, encoded_cursor, wallet_list_chunk_size)
        if encoded_root_hash is not None:
            response = self._get('wallet_list', encoded_root_hash, wallet_list_chunk_size)
        else:
            response = self._get('wallet_list')
        return response.json()

    def wallet_list_balance(self, encoded_root_hash, encoded_addr):
        '''Return the balance of the given address from the wallet tree with the given root hash.'''
        response = self._get('wallet_list', encoded_root_hash, encoded_addr, 'balance')
        return int(response.text)

    def send_peers(self):
        '''
        Share your IP with another peer.
        Deprecated: To make a node learn your IP, you can make any request to it.
        '''
        response = self._post(None, 'peers')
        return response.text # OK

    def wallet_balance(self, wallet_address):
        '''
        Return the balance of the wallet specified via wallet_address.
        Unknown wallet addresses will simply return 0.
        '''
        response = self._get('wallet', wallet_address, 'balance')
        return int(response.text)

    def wallet_last_tx(self, wallet_address):
        '''
        Return the last outgoing transaction ID (hash) for the wallet
        specified via wallet_address.
        '''
        response = self._get('wallet', wallet_address, 'last_tx')
        return response.text

    def tx_anchor(self):
        '''Return a block anchor to use for building transactions.'''
        response = self._get('tx_anchor')
        return response.text

    def wallet_txs(self, wallet_address, earliest_tx = None):
        '''
        Return transaction identifiers (hashes), optionally starting from the earliest_tx,
        for the wallet specified via wallet_address.
        '''
        if earlieset_tx is not None:
            response = self._get('wallet', wallet_address, 'txs', earliest_tx)
        else:
            response = self._get('wallet', wallet_address, 'txs')
        return response.json()

    def wallet_deposits(self, wallet_address, earliest_deposit = None):
        '''
        Return identifiers (hashes) of transfer transactions depositing to the given
        wallet_address, optionally starting from the earliest_deposit.
        '''
        if earliest_deposit is not None:
            response = self._get('wallet', wallet_address, 'deposits', earliest_deposit)
        else:
            response = self._get('wallet', wallet_address, 'deposits')
        return response.json()

    def block_hash(self, hash, field = None):
        '''
        Return the JSON-encoded block or field of a block with the given hash.

        {
            "nonce",
            "previous_block",
            "timestamp",
            "last_retarget",
            "diff",
            "height",
            "hash","indep_hash","txs":[],
            "tx_root",
            "tx_tree":[],
            "wallet_list","reward_addr",
            "tags":[],
            "reward_pool",
            "weave_size",
            "block_size",
            "cumulative_diff",
            "hash_list_merkle",
            "poa": {
                "option",
                "tx_path",
                "data_path",
                "chunk"
            }
        }
        '''
        if field is not None:
            response = self._get('block/hash', hash, field)
        else:
            response = self._get('block/hash', hash)
        return response.json()

    def block_height(self, height, field = None):
        '''Return the JSON-encoded block or field of a block with the given height.'''
        if field is not None:
            response = self._get('block/height', str(height), field)
        else:
            response = self._get('block/height', str(height))
        return response.json()

    def block2_hash(self, hash, encoded_transaction_indices = None):
        '''
        Return the binary-encoded block with the given hash.

        Optionally accept up to 125 bytes of encoded transaction indices where
        the Nth bit being 1 asks to include the Nth transaction in the
        alphabetical order (not just its identifier) in the response. The node
        only includes transactions in the response when the corresponding
        indices are present in the request and those transactions are found in
        the block cache - the motivation is to keep the endpoint lightweight.
        '''
        if encoded_transaction_indices is not None:
            response = self._post(encoded_transaction_indices, 'block2/hash', hash, method = 'GET')
        else:
            response = self._get('block2/hash', hash)
        return response.content

    def block2_height(self, height, encoded_transaction_indices = None):
        '''
        Return the binary-encoded block with the given height.

        Optionally accept up to 125 bytes of encoded transaction indices where
        the Nth bit being 1 asks to include the Nth transaction in the
        alphabetical order (not just its identifier) in the response. The node
        only includes transactions in the response when the corresponding
        indices are present in the request and those transactions are found in
        the block cache - the motivation is to keep the endpoint lightweight.
        '''
        if encoded_transaction_indices is not None:
            response = self._post(encoded_transaction_indices, 'block2/height', str(height), method = 'GET')
        else:
            response = self._get('block2/height', str(height))
        return response.content

    def block_current(self):
        '''Return the current block.'''
        response = self._get('block/current')
        return response.json()

    def current_block(self):
        '''Deprecated for block_current() 12/07/2018'''
        response = self._get('current_block')
        return response.json()

    def block(self, height_or_hash):
        if type(height_or_hash) is int:
            return self.block_height(height_or_hash)
        elif not height_or_hash :
            return self.block_current()
        else:
            return self.block_hash(height_or_hash)

    def block2(self, height_or_hash):
        if type(height_or_hash) is int:
            return self.block2_height(height_or_hash)
        else:
            return self.block2_hash(height_or_hash)

    def tx_field(self, hash, field):
        '''
        Return a given field of the transaction specified by the transaction ID (hash).
        
        {field} := { 
            'id' | 'last_tx' | 'owner' | 'tags' | 'target' | 'quantity' |
            'data_root' | 'data_size' | 'data' | 'reward' | 'signature'
        }
        '''
        if field == 'data':
            response = self._get('tx', hash, 'data.')
            return response.content
        else:
            response = self._get('tx', hash, field)
            if field == 'tags':
                tags = response.json()
                for tag in tags:
                    for key in tag:
                        tag[key] = b64dec(tag[key].encode())
                return tags
            else:
                return response.json()

    def tx_id(self, hash):
        '''Return transaction id.'''
        return self.tx_field(hash, 'id')

    def tx_last_tx(self, hash):
        '''Return transaction last_tx.'''
        return self.tx_field(hash, 'last_tx')

    def tx_owner(self, hash):
        '''Return transaction owner.'''
        return self.tx_field(hash, 'owner')

    def tx_tags(self, hash):
        '''Return transaction tags.'''
        return self.tx_field(hash, 'tags')

    def tx_target(self, hash):
        '''Return transaction target.'''
        return self.tx_field(hash, 'target')

    def tx_quantity(self, hash):
        '''Return transaction quantity.'''
        return self.tx_field(hash, 'quantity')

    def tx_data_root(self, hash):
        '''Return transaction data root.'''
        return self.tx_field(hash, 'data_root')

    def tx_data_size(self, hash):
        '''Return transaction data size.'''
        return self.tx_field(hash, 'data_size')

    def tx_data(self, hash):
        '''
        Return transaction data.

        The endpoint serves data regardless of how it was uploaded.
        '''
        return self.tx_field(hash, 'data')

    def tx_signature(self, hash):
        '''Return transaction signature.'''
        return self.tx_field(hash, 'signature')

    def tx_reward(self, hash):
        '''Return transaction reward.'''
        return self.tx_field(hash, 'reward')

    def height(self):
        '''Return the current block hieght.'''
        response = self._get('height')
        return int(response.text)

    def data(self, txid, ext = '', range = None):
        '''
        Get the decoded data from a transaction.

        This is roughly just an alias for tx_data_html.

        The transaction is pending: Pending
        The provided transaction ID is not valid or the field name is not valid: Invalid hash.
        A transaction with the given ID could not be found: Not Found.
        '''
        if range is not None:
            headers = {'Range':f'bytes={range[0]}-{range[1]}'}
        else:
            headers = {}
        response = self._get(txid + ext, headers = headers)

        return response.content

    def stream(self, txid, ext = '', range = None):
        if range is not None:
            headers = {'Range':f'bytes={range[0]}-{range[1]}'}
        else:
            headers = {}
        response = self._get(txid + ext, headers = headers, stream = True)
        return response_stream_to_file_object(response)
