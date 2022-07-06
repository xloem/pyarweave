import io
import threading
import time

import erlang
import json
import requests

from . import DEFAULT_API_URL, DEFAULT_REQUESTS_PER_MINUTE_LIMIT, logger, ArweaveException, ArweaveNetworkException
from .stream import PeerStream, GatewayStream
from .utils import b64dec, arbindec

def binary_to_term(b):
    # arweave.live seems to replace nonascii chars with this sequence :/
    # occasionally things will work if it's turned back into the etf byte
    if b[:3] == b'\xef\xbf\xbd':
        b = b.replace(b'\xef\xbf\xbd', b'\x83')
    return erlang.binary_to_term(b)

class HTTPClient:
    def __init__(self, api_url, timeout = None, retries = 10, outgoing_connections = 256, requests_per_period = DEFAULT_REQUESTS_PER_MINUTE_LIMIT, period_sec = 60, extra_headers = {}):
        self.api_url = api_url
        self.session = requests.Session()
        self.max_outgoing_connections = outgoing_connections
        self.outgoing_connection_semaphore = threading.BoundedSemaphore(outgoing_connections)
        self.rate_limit_lock = threading.Lock()
        self.requests_per_period = requests_per_period
        self.ratelimited_requests = 0
        self.period_sec = period_sec
        #self.incoming_port = incoming_port
        self.req_history = []
        self.extra_headers = extra_headers
        max_retries = requests.adapters.Retry(total=retries, backoff_factor=0.1, status_forcelist=[500,502,503,504]) # from so
        adapter = requests.adapters.HTTPAdapter(
            pool_connections = outgoing_connections,
            pool_maxsize = outgoing_connections,
            max_retries = max_retries,
            pool_block = True
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.timeout = timeout
    def __del__(self):
        self.session.close()

    def ratelimited(self):
        if self.requests_per_period is None:
            return False
        with self.rate_limit_lock:
            now = time.time()
            queued_requests = 0
            for idx, then in enumerate(self.req_history):
                if then + self.period_sec >= now:
                    queued_requests_idx = idx
                    queued_requests = len(self.req_history) - queued_requests_idx
                    break
            return queued_requests + self.ratelimited_requests >= self.requests_per_period

    def ratelimit_suggested(self):
        if self.requests_per_period is None:
            return False
        if len(self.req_history) == 0:
            return False
        return (time.time() - self.req_history[-1] < self.requests_per_period / period_sec) or self.ratelimited

    def _ratelimit_prologue(self):
        if self.requests_per_period is None:
            return
        with self.rate_limit_lock:
            now = time.time()
            queued_requests = 0
            #if len(self.req_history) >= 3600:
            #    import pdb; pdb.set_trace()
            for idx, then in enumerate(self.req_history):
                if then + self.period_sec >= now:
                    queued_requests_idx = idx
                    queued_requests = len(self.req_history) - queued_requests_idx
                    break
            if queued_requests + self.ratelimited_requests < self.requests_per_period:
                #if len(self.req_history) >= self.requests_per_period:
                #    import pdb; pdb.set_trace()
                self.req_history.append(now)
                return
        #print(f'{self.api_url}: too many requests in prologue')
        self.on_too_many_requests()
        with self.rate_limit_lock:
            now = time.time()
            if len(self.req_history) >= self.requests_per_period:
                duration = self.req_history[-self.requests_per_period+1] + self.period_sec - now
                if duration > 0:
                    if duration > 0.5:
                        # quick workaround to let this display later during lock contention
                        time.sleep(0.5)
                        duration -= 0.5
                    logger.info(f'Sleeping for {int(duration*100)/100}s to respect ratelimit of {self.requests_per_period}req/{self.period_sec}s ...')
                    time.sleep(duration)
                    #import pdb; pdb.set_trace()
                    logger.info(f'Done sleeping for {int(duration*100)/100}s to respect ratelimit of {self.requests_per_period}req/{self.period_sec}s .')
        return self._ratelimit_prologue()

    def _ratelimit_epilogue(self, success = True):
        if self.requests_per_period is None:
            return
        if success:
            with self.rate_limit_lock:
                self.ratelimited_requests = 0
                now = time.time()
                for req_idx, req_time in enumerate(self.req_history):
                    if req_time + self.period_sec > now:
                        self.req_history = self.req_history[req_idx:]
                        break
        else:
            with self.rate_limit_lock:
                self.ratelimited_requests += 1
                now = time.time()
                #import pdb; pdb.set_trace()
                if len(self.req_history):
                    self.period_sec = max(self.period_sec, now - self.req_history[0])
                if len(self.req_history) - self.ratelimited_requests <= self.requests_per_period:
                    self.requests_per_period = max(1, len(self.req_history) - self.ratelimited_requests)
                logger.info(f'Rate limit hit. Dropped rate to {self.requests_per_period}/{self.period_sec}s.')
            self.on_too_many_requests()

    # _get and _post should just call a _request function to share code
    def _request(self, *params, **request_kwparams):
        if len(params) and params[-1][0] == '?':
            url = self.api_url + '/' + '/'.join(params[:-1]) + params[1]
        else:
            url = self.api_url + '/' + '/'.join(params)

        headers = {**self.extra_headers, **request_kwparams.get('headers', {})}
        request_kwparams['headers'] = headers

        while True:
            self._ratelimit_prologue()
            response = None
            try:
                if not self.outgoing_connection_semaphore.acquire(blocking=False):
                    self.on_too_many_connections()
                    logger.info(f'Waiting for connection count limit semaphore to drain...')
                    self.outgoing_connection_semaphore.acquire()
                try:
                    response = self.session.request(**{'url': url, 'timeout': self.timeout, **request_kwparams})
                finally:
                    self.outgoing_connection_semaphore.release()

                if response.status_code == 400:
                    try:
                        msg = response.json()['error']
                    except:
                        msg = response.text
                    raise ArweaveException(msg)

                response.raise_for_status()
                if int(response.headers.get('content-length', 1)) == 0:
                    raise ArweaveException(f'Empty response from {url}')
                self._ratelimit_epilogue(True)
                return response
            except requests.exceptions.RequestException as exc:
                text = '' if response is None else response.text
                status_code = 0 if response is None else response.status_code
                if status_code == 429:
                    # too many requests
                    self._ratelimit_epilogue(False)
                    self.on_too_many_requests()
                    continue
                logger.error('{}\n{}\n\n{}'.format(exc, text, request_kwparams))
                if status_code == 520:
                    # cloudfront broke
                    self._ratelimit_epilogue(True)
                    continue
                elif status_code == 502:
                    # cloudflare broke
                    self._ratelimit_epilogue(True)
                    continue
                self.on_network_exception(text, status_code, exc, response)
                raise ArweaveNetworkException(text, status_code, exc, response)
            except:
                self._ratelimit_epilogue(True)
                raise

    def _get(self, *params, **request_kwparams):
        return self._request(*params, **{'method': 'GET', **request_kwparams})

    def _post(self, data, *params, headers = {}, **request_kwparams):
        headers = {**headers}

        if type(data) is dict:
            headers.setdefault('Content-Type', 'application/json')
            data_key = 'json'
        else:
            if isinstance(data, (bytes, bytearray)):
                headers.setdefault('Content-Type', 'application/octet-stream')
            else:
                headers.setdefault('Content-Type', 'text/plain')
            data_key = 'data'

        return self._request(*params, **{'method': 'POST', 'headers': headers, **{data_key: data}, **request_kwparams})

    def on_network_exception(self, text, code, exception, response):
        raise ArweaveNetworkException(text, code, exception, response)

    def on_too_many_connections(self):
        pass

    def on_too_many_requests(self):
        return self.on_too_many_connections()

class Peer(HTTPClient):
    # peer api [incomplete]:
    # - https://docs.arweave.org/developers/server/http-api
    # - https://github.com/ArweaveTeam/arweave/blob/master/apps/arweave/src/ar_http_iface_middleware.erl#L132
    # - https://github.com/ArweaveTeam/arweave/blob/master/apps/arweave/src/ar_http_iface_client.erl
    def __init__(self, api_url = DEFAULT_API_URL, timeout = None, retries = 5, outgoing_connections = DEFAULT_REQUESTS_PER_MINUTE_LIMIT, requests_per_period = DEFAULT_REQUESTS_PER_MINUTE_LIMIT, period_sec = 60, incoming_port = None):
        super().__init__(
            api_url, timeout, retries, outgoing_connections, requests_per_period, period_sec,
            extra_headers = {'X-P2p-Port':str(incoming_port)} if incoming_port is not None else {}
        )

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

    def probe(self):
        features = []
        systems = []
        status = {}
        exclude = set()

        def load_balancing_proxy():
            sync_record_1 = self.data_sync_record(0,1)[-1]
            sync_record_2 = self.data_sync_record(0,2)[-1]
            if sync_record_1 == sync_record_2:
                raise ArweaveNetworkException()

        def partial_data():
            for height in range(self.height(), 0, -1):
                tx = self.block_height(height)['txs'][0]
                try:
                    stream = self.gateway_stream(tx, range = (0,4))
                    data = stream.read(8)
                    if len(data) == 8:
                        partial_data = False
                    else:
                        stream = self.gateway_stream(tx)
                        data = stream.read(8)
                        if len(data) == 8:
                            partial_data = True
                        else:
                            continue
                    break
                except ArweaveException as exc:
                    print(tx, exc)
                    continue
            if not partial_data:
                raise ArweaveNetworkException()

        def peers():
            health = status.get('health')
            if health is not None and 'origins' in health:
                status['peers'] = [origin['endpoint'].split('://',1)[1] for origin in health['origins']]
                raise ArweaveNetworkException()
            else:
                return self.peers()

        probes = dict(
            arql = dict(
                params = [dict(op='equals',expr1='',expr2='')],
            ),
            graphql = dict(
                params = ['query{transaction(id:""){id}}']
            ),
            load_balancing_proxy = dict(
                probe = load_balancing_proxy,
                exclude = ['info', 'sync_buckets']
            ),
            partial_data = dict(
                probe = partial_data,
            ),
            cache_jobs = dict(
                system = 'arseeding',
            ),
            health = dict(
                system = 'arweave-gateway',
            ),
            info = dict(
                system = 'arweave-erlang'
            ),
            peers = dict(
                probe = peers,
                system = 'arweave-erlang'
            ),
            sync_buckets = dict(
                system = 'arweave-erlang'
            )
        )

        for probe, options in probes.items():
            if probe in exclude:
                continue
            logger.info(f'{probe} ...')
            try:
                params = options.get('params',[])
                func = options.get('probe')
                if func is None:
                    func = getattr(self, probe)
                reply = func(*options.get('params',[]))
                logger.info(f'{self.api_url} has {probe}')
                if len(params) == 0 and reply is not None:
                    status[options.get('status',probe)] = reply
                exclude.update(options.get('exclude',[]))
                features.append(options.get('feature',probe))
                system = options.get('system')
                if system is not None and system not in systems:
                    systems.append(system)
            except ArweaveNetworkException:
                logger.info(f'{self.api_url} does not have {probe}')
                continue
 
        return {
            'guess': systems,
            'features': features,
            'status': status
        }

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
        response = self._get('tx2', txid)#, stream = True)
        #with response_stream_to_file_object(response) as stream:
        #    size = int.from_bytes(stream.read(3), 'big')
        #    format = stream.read(1)[0]
        #    txid_raw = stream.read(32)
        #    last_tx = arbindec(stream, 
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
        return binary_to_term(response.content)

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
        intervals = binary_to_term(response.content)
                
        intervals = [
            (int.from_bytes(left.value, 'big'), int.from_bytes(right.value, 'big'))
            for left, right in intervals
        ]
        return intervals

    def chunk(self, offset, packing = 'unpacked', bucket_based_offset = False):
        '''
        Returns the data chunk containing 1-based offset,
        using json, base64 encoded network transmission.

        {packing} := { 'unpacked' | 'spora_2_5' | 'spora_2_6_<address>' | 'any' }

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
        return response.json()

    def chunk2(self, offset, packing = 'unpacked', bucket_based_offset = False):
        '''
        Returns the data chunk containing 1-based offset,
        using a raw binary format for the fields.

        {packing} := { 'unpacked' | 'spora_2_5' | 'spora_2_6_<address>' | 'any' }
        '''

        headers = {
            'x-packing': packing
        }
        if bucket_based_offset:
            headers['x-bucket-based-offset'] = '1'

        response = self._get('chunk2', str(offset), headers=headers)
        return response.content

    def chunk_size(self, offset, packing = 'unpacked', bucket_based_offset = False):
        '''Returns the size of the data chunk containing 1-based offset.'''

        headers = {
            'x-packing': packing,
            'Range': 'bytes=0-2',
        }
        if bucket_based_offset:
            headers['x-bucket-based-offset'] = '1'

        response = self._get('chunk2', str(offset), headers=headers, stream = True)
        with response_stream_to_file_object(response) as stream:
            return int.from_bytes(stream.read(3), 'big')

    def tx_offset(self, hash):
        '''
        Get the absolute end offset and size of the transaction

        The client may use this information to collect transaction chunks. Add 1 to
        the end offset and substract the size to get the start offset, then fetch a
        chunk via chunk(<start offset>). Add its size to the start offset and fetch
        the next chunk - if there are more chunks, continue to do the same.

        {
            "offset": <offset of last byte of tx data>,
            "size": <total size of tx data>
        }
        '''
        response = self._get('tx', hash, 'offset')
        result = response.json()
        result['offset'] = int(result['offset'])
        result['size'] = int(result['size'])
        return result

    def send_chunk(self, json_data):
        # NOTE: this can take two headers
        # arweave-data-root: 43 encoded bytes
        # arweave-data-size: integer
        # i'm guessing these are used to quickly discard data that does not match the server
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
        response = self._post(
            json_data,
            'chunk',
            headers={
                'arweave-data-root': json_data['data_root'],
                'arweave-data-size': str(json_data['data_size'])
            }
        )
        return response.text # OK

    def block_announcement(self, block_announcement):
        '''
        Accept an announcement of a block. Returns optional missing transactions and chunk.
        412: no previous block
        208: already processing the block
        '''
        response = self._post(block_announcement, 'block_announcement')
        return response.json()

    def send_block(self, block, arweave_recall_byte : int = None):
        '''Accept a JSON-encoded block with Base64Url encoded fields.'''
        headers = {}
        if arweave_recall_byte is not None:
            headers['arweave-recall-byte'] = str(arweave_recall_byte)
        response = self._post(block, 'block', headers=headers)
        return response.text # OK

    def send_block2(self, block, arweave_recall_byte : int = None):
        '''Accept a binary-encoded block.'''
        headers = {}
        if arweave_recall_byte is not None:
            headers['arweave-recall-byte'] = str(arweave_recall_byte)
        response = self._post(block, 'block2', headers=headers)
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
        Deprecated: To make a node learn your IP, you can make any request to it. The port is inferred from the X-P2p-Port header.
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
        if earliest_tx is not None:
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

        field :: nonce | previous_block | timestamp | last_retarget | diff | height | hash |
        indep_hash | txs | hash_list | wallet_list | reward_addr | tags | reward_pool

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
        '''
        Return the JSON-encoded block or field of a block with the given height.

        field :: nonce | previous_block | timestamp | last_retarget | diff | height | hash |
        indep_hash | txs | hash_list | wallet_list | reward_addr | tags | reward_pool
        '''
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
        '''A convenience method that hands off to block_height or block_hash.'''
        if type(height_or_hash) is int:
            return self.block_height(height_or_hash)
        elif not height_or_hash :
            return self.block_current()
        else:
            return self.block_hash(height_or_hash)

    def block2(self, height_or_hash):
        '''A convenience method that hands off to block2_height or block2_hash.'''
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
                try:
                    return response.json()
                except json.decoder.JSONDecodeError:
                    return response.text

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

    def stream(self, txid, range = None):
        try:
            return self.peer_stream(txid, range=range)
        except Exception:
            if reupload(self, txid):
                return self.gateway_stream(txid, range=range)
            else:
                raise

    def gateway_stream(self, txid, ext ='', range = None):
        if range is not None:
            return GatewayStream.from_txid(self, txid, range[0], range[1] - range[0])
        else:
            return GatewayStream.from_txid(self, txid)

    def peer_stream(self, txid, range = None):
        if range is not None:
            return io.BufferedReader(PeerStream.from_txid(self, txid, range[0], range[1]-range[0]), 0x40000)
        else:
            return io.BufferedReader(PeerStream.from_txid(self, txid), 0x40000)

    # below are used with https://github.com/ar-io/arweave-gateway

    def graphql(self, query):
        response = self._post({
            'operationName': None,
            'query': query,
            'variables': {}
        }, 'graphql')
        return response.json()

    def health(self):
        '''
        Returns information on the connected peers and database.
        
        {
            "region": "<AWS_REGION>",
            "origins": [
                {
                    "endpoint": "<api_url>",
                    "status": <http status code>, 
                    "info": peer.info()
                }
            ],
            "database": {
                "block": { "id", "height", "mined_at", "previous_block", "txs", "extended" }
            }
        }
        '''
        response = self._get('health')
        return response.json()
        

    # below are used with https://github.com/everFinance/arseeding

    def send_job_broadcast(self, txid):
        '''Register a tx to be broadcast to all nodes.'''
        response = self._get('job', 'broadcast', txid, method='POST')
        return response.text

    def send_job_sync(self, txid):
        response = self._get('job', 'sync', txid, method='POST')
        return response.text

    def job_kill(self, txid, type):
        '''Close a running job.'''
        response = self._get('job', 'kill', txid, type, method='POST')
        return response.text

    def job_kill_broadcast(self, txid):
        '''Close a broadcast job.'''
        return self.job_kill(txid, 'broadcast')

    def job_kill_sync(self, txid):
        '''Close a sync job.'''
        return self.job_kill(txid, 'sync')

    def job(self, txid, type):
        '''Get the status of a job.'''
        response = self._get('job', txid, type)
        return response.json()

    def job_broadcast(self, txid):
        '''Get the status of a broadcast job.

        {
            "arid": "<txid>",
            "jobType": "broadcast",
            "countSuccessed": <nodes successfully broadcast>,
            "countFailed": <nodes failed to broadcast>,
            "totalNodes": <total number of nodes>,
            "close": <whether task is closed>
        }
        '''
        return self.job(txid, 'broadcast')

    def job_sync(self, txid):
        '''Get the status of a sync job.
        '''
        return self.job(txid, 'sync')

    def cache_jobs(self):
        response = self._get('cache', 'jobs')
        return response.json()

from ar.utils.merkle import compute_root_hash, generate_transaction_chunks
from ar.utils import b64enc
def reupload(peer, tx):
    stream = peer.gateway_stream(tx)

    chunks = generate_transaction_chunks(stream)
    stream = peer.gateway_stream(tx)
    if chunks['data_root'] != peer.tx_data_root(tx):
        logger.error(f'{peer.api_url}: Data for {tx} mismatches generated root.')
        return False
    logger.warning(f'uhh trying to reupload {tx}')
    offset = 0
    for proof, chunk in zip(chunks['proofs'], chunks['chunks']):
        chunk_size = chunk.data_size
        chunk = {
            'data_root': chunks['data_root'],
            'data_size': str(chunks['chunks'][-1].max_byte_range),
            'data_path': b64enc(proof.proof),
            'offset': str(proof.offset),
            'chunk': b64enc(stream.read(chunk_size))
        }
        peer.send_chunk(chunk)
        offset+=chunk_size
    return True
