import json, requests

from . import DEFAULT_API_URL, logger, ArweaveTransactionException

class Peer(object):
    # peer api [incomplete]:
    # - https://docs.arweave.org/developers/server/http-api
    # - https://github.com/ArweaveTeam/arweave/blob/master/apps/arweave/src/ar_http_iface_middleware.erl#L132
    # - https://github.com/ArweaveTeam/arweave/blob/master/apps/arweave/src/ar_http_iface_client.erl

    def __init__(self, api_url = DEFAULT_API_URL):
        self.api_url = api_url
        self.session = requests.Session()


    def info(self):
        """Return network information from a given node."""
        response = self._get("{}/info")
        return json.loads(response.text)

    def time(self):
        """Return the current universal time in seconds."""
        response = self._get("{}/time")
        return int(response.text)

    def tx_pending(self):
        """Return all mempool transactions."""
        response = self._get("{}/tx/pending")
        return json.loads(response.text)

    def queue(self):
        """Return outgoing transaction priority queue."""
        response = self._get("{}/queue")
        return json.loads(response.text)

    def tx_status(self, hash):
        """
        Return additional information about the transaction with the given identifier (hash).

        {
            "block_height": "<Height>,
            "block_indep_hash": "<BH>",
            "number_of_confirmations": "<NumberOfConfirmations>",
        }
        """
        response = self._get("{}/tx/{}/status", txid)
        return json.loads(response.text)

    def tx(self, txid):
        """Return a JSON-encoded transaction."""
        tx_response = self._get("{}/tx/{}", txid)
        return json.loads(tx_response.text)

    def tx2(self, txid):
        """Return a binary-encoded transaction."""
        tx_response = self._get("{}/tx2/{}", txid)
        return tx_response.content

    def unconfirmed_tx(self, txid):
        """Return a possibly unconfirmed JSON-encoded transaction."""
        tx_response = self._get("{}/unconfirmed_tx/{}", txid)
        return json.loads(tx_response.text)

    def unconfirmed_tx2(self, txid):
        """Return a possibly unconfirmed binary-encoded transaction."""
        tx_response = self._get("{}/unconfirmed_tx2/{}", txid)
        return tx_response.content

    def arql(self, logical_expression):
        """
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
        """
        response = self._post(expr, "{}/arql")
        return json.loads(response.text)

    def tx_data_html(self, txid):
        """
        Return the data field of the transaction specified via the transaction ID (hash)
        served as HTML.
        """
        response = self._get("{}/tx/{}/data.html")
        return response.content

    def sync_buckets(self):
        response = self._get("{}/sync_buckets")
        return response.content

    def data_sync_record(self, encoded_start = None, encoded_limit = None):
        if encoded_start is None and encoded_limit is None:
            response = self._get("{}/data_sync_record")
        else:
            response = self._get("{}/data_sync_record", encoded_start, encoded_limit)
        return response.content

    def chunk(self, offset):
        response = self._get("{}/chunk/{}", offset)
        return json.loads(response.text)

    def chunk2(self, offset):
        response = self._get("{}/chunk2/{}", offset)
        return response.content

    def tx_offset(self, hash):
        """
        Return transaction offset and size.

        {
            "offset": "<Offset>",
            "size": "<Size>"
        }
        """
        response = self._get("{}/tx/{}/offset", hash)
        return json.loads(response.text)

    def send_chunk(self, json_data):
        """
        Upload Data Chunks

        json_data:
        {
          "data_root": "<Base64URL encoded data merkle root>",
          "data_size": "a number, the size of transaction in bytes",
          "data_path": "<Base64URL encoded inclusion proof>",
          "chunk": "<Base64URL encoded data chunk>",
          "offset": "<a number from [start_offset, start_offset + chunk size), relative to other chunks>"
        }
        """
        response = self._post(json_data, "{}/chunk")
        return json.loads(response.text)

    def block_announcement(self, block_announcement):
        """
        Accept an announcement of a block. Returns optional missing transactions and chunk.
        412: no previous block
        208: already processing the block
        """
        response = self._post(block_announcement, "{}/block_announcement")
        return json.loads(response.text)

    def block(self, block):
        """Accept a JSON-encoded block with Base64Url encoded fields."""
        response = self._put(block, "{}/block")
        return response.text # OK

    def block2(self, block):
        """Accept a binary-encoded block."""
        response = self._put(block, "{}/block2")
        return response.text # OK

    def wallet(self, secret):
        """
        Generate a wallet and receive a secret key identifying it.
        Requires internal_api_secret startup option to be set.
        WARNING: only use it if you really really know what you are doing.

        {
            "wallet_address": <Address>,
            "wallet_access_code": <WalletAccessCode>
        }
        """
        response = self._post(secret, "{}/wallet")
        return json.loads(response.text)

    def send_tx(self, json_data):
        """Accept a new JSON-encoded transaction."""
        response = self._post(json_data, "{}/tx")
        return response.text # OK

    def send_tx2(self, binary_data):
        """Accept a new binary-encoded transaction."""
        response = self._post(binary_data, "{}/tx2")
        return response.text # OK

    def unsigned_tx(self, secret):
        """
        Sign and send a tx to the network.
        Fetches the wallet by the provided key generated via wallet().
        Requires internal_api_secret startup option to be set.
        WARNING: only use it if you really really know what you are doing.
        """
        response = self._post(secret, "{}/unsigned_tx")
        return json.loads(response.text)

    def peers(self):
        """Return the list of peers held by the node."""
        response = self._get("{}/peers")
        return json.loads(response.text)

    def price(self, data_size=0, target_address=None):
        """Return the estimated transaction fee not including a new wallet fee."""
        if target_address is not None:
            response = self._get("{}/price/{}/{}", data_size, target_address)
        else:
            response = self._get("{}/price/{}", data_size)
        return response.text

    def hash_list(self, from_height = None, to_height = None, as_hash_list = True):
        """
        Return the current JSON-encoded hash list held by the node.
        Deprecated for block_index().
        """
        kwparams = {}
        if as_hash_list:
            kwparams['headers'] = {'x-block-format': '2'}
        if from_height is not None or to_height is not None:
            response = self._get("{}/hash_list/{}/{}", from_height, to_height, **kwparams)
        else:
            response = self._get("{}/hash_list", **kwparams)
        return json.loads(response.text)

    def block_index(self, from_height = None, to_height = None, as_hash_list = False):
        """Return the current JSON-encoded hash list held by the node."""
        kwparams = {}
        if as_hash_list:
            kwparams['headers'] = {'x-block-format': '2'}
        if from_height is not None or to_height is not None:
            response = self._get("{}/block_index/{}/{}", from_height, to_height, **kwparams)
        else:
            response = self._get("{}/block_index", **kwparams)
        return json.loads(response.text)
    
    def block_index2(self):
        """Return the current binary-encoded block index held by the node."""
        response = self._get("{}/block_index2")
        return response.content

    def recent_hash_list(self):
        response = self._get("{}/recent_hash_list")
        return json.loads(response.content)

    def recent_hash_list_diff(self, hash_list_binary):
        """
        Accept the list of independent block hashes ordered from oldest to newest
        and return the deviation of our hash list from the given one.
        Peers may use this endpoint to make sure they did not miss blocks or learn
        about the missed blocks and their transactions so that they can catch up quickly.
        """
        response = self._post(hash_list_binary, "{}/recent_hash_list_diff", method='GET')
        return json.loads(response.text)

    def wallet_list(self, encoded_root_hash = None, encoded_cursor = None, wallet_list_chunk_size = None):
        """
        Return the current wallet list held by the node, or optionally a bunch of wallets,
        up to wallet_list_chunk_size, from the tree with the given root hash, optionally
        starting with the provided cursor, taken the wallet addresses are picked in the
        ascending alphabetical order.
        """
        if wallet_list_chunk_size is not None:
            wallet_list_chunk_size = f'?{wallet_list_chunk_size}'
        else:
            wallet_list_chunk_size = ''
        if encoded_cursor is not None:
            response = self._get("{}/wallet_list/{}/{}{}", encoded_root_hash, encoded_cursor, wallet_list_chunk_size)
        if encoded_root_hash is not None:
            response = self._get("{}/wallet_list/{}{}", encoded_root_hash, wallet_list_chunk_size)
        else:
            response = self._get("{}/wallet_list")
        return json.loads(response.text)

    def wallet_list_balance(self, encoded_root_hash, encoded_addr):
        """Return the balance of the given address from the wallet tree with the given root hash."""
        response = self._get("{}/wallet_list/{}/{}/balance", encoded_root_hash, encoded_addr)
        return int(response.text)

    def send_peers(self):
        """
        Share your IP with another peer.
        Deprecated: To make a node learn your IP, you can make any request to it.
        """
        response = self._post(None, "{}/peers")
        return response.text # OK

    def wallet_balance(self, wallet_address):
        """Return the balance of the wallet specified via wallet_address."""
        response = self._get("{}/wallet/{}/balance", wallet_address)
        return int(response.text)

    def wallet_last_tx(self, wallet_address):
        """
        Return the last transaction ID (hash) for the wallet specified via wallet_address.
        GET request to endpoint /wallet/{wallet_address}/last_tx.
        """
        response = self._get("{}/wallet/{}/last_tx", wallet_address)
        return response.text

    def tx_anchor(self):
        """Return a block anchor to use for building transactions."""
        last_tx_response = self._get("{}/tx_anchor")
        return last_tx_response.text

    def wallet_txs(self, wallet_address, earliest_tx = None):
        """
        Return transaction identifiers (hashes), optionally starting from the earliest_tx,
        for the wallet specified via wallet_address.
        """
        if earlieset_tx is not None:
            response = self._get("{}/wallet/{}/txs/{}", wallet_address, earliest_tx)
        else:
            response = self._get("{}/wallet/{}/txs", wallet_address)
        return json.loads(response.text)

    def wallet_deposits(self, wallet_address, earliest_deposit = None):
        """
        Return identifiers (hashes) of transfer transactions depositing to the given
        wallet_address, optionally starting from the earliest_deposit.
        """
        if earliest_deposit is not None:
            response = self._get("{}/wallet/{}/deposits/{}", wallet_address, earliest_deposit)
        else:
            response = self._get("{}/wallet/{}/deposits", wallet_address)
        return json.loads(response.text)

    def block_hash(self, hash, field = None):
        """Return the JSON-encoded block or field of a block with the given hash."""
        if field is not None:
            response = self._get("{}/block/hash/{}/{}", hash, field)
        else:
            response = self._get("{}/block/hash/{}", hash)
        return json.loads(response.text)

    def block_height(self, height, field = None):
        """Return the JSON-encoded block or field of a block with the given height."""
        if field is not None:
            response = self._get("{}/block/height/{}/{}", height, field)
        else:
            response = self._get("{}/block/height/{}", height)
        return json.loads(response.text)

    def block2_hash(self, hash, encoded_transaction_indices = None):
        """
        Return the binary-encoded block with the given hash.

        Optionally accept up to 125 bytes of encoded transaction indices where
        the Nth bit being 1 asks to include the Nth transaction in the
        alphabetical order (not just its identifier) in the response. The node
        only includes transactions in the response when the corresponding
        indices are present in the request and those transactions are found in
        the block cache - the motivation is to keep the endpoint lightweight.
        """
        if encoded_transaction_indices is not None:
            response = self._post(encoded_transaction_indices, "{}/block2/hash/{}", hash, method = 'GET')
        else:
            response = self._get(encoded_transaction_indices, "{}/block2/hash/{}", hash)
        return response.content

    def block2_height(self, height, encoded_transaction_indices = None):
        """
        Return the binary-encoded block with the given height.

        Optionally accept up to 125 bytes of encoded transaction indices where
        the Nth bit being 1 asks to include the Nth transaction in the
        alphabetical order (not just its identifier) in the response. The node
        only includes transactions in the response when the corresponding
        indices are present in the request and those transactions are found in
        the block cache - the motivation is to keep the endpoint lightweight.
        """
        if encoded_transaction_indices is not None:
            response = self._post(encoded_transaction_indices, "{}/block2/height/{}", height, method = 'GET')
        else:
            response = self._get(encoded_transaction_indices, "{}/block2/height/{}", height)
        return response.content

    def block_current(self):
        """Return the current block."""
        response = self._get("{}/block/current")
        return json.loads(response.text)

    def current_block(self):
        """Deprecated for block_current() 12/07/2018"""
        response = self._get("{}/current_block")
        return json.loads(response.text)

    def tx_field(self, hash, field):
        """
        Return a given field of the transaction specified by the transaction ID (hash).
        
        {field} := { "id" | "last_tx" | "owner" | "tags" | "target" | "quantity" | "data" | "signature" | "reward" }
        """
        response = self._get("{}/tx/{}/{}", hash, field)
        return json.loads(response.text)

    def tx_id(self, hash):
        """Return transaction id."""
        return self.tx_field(hash, 'id')

    def tx_last_tx(self, hash):
        """Return transaction last_tx."""
        return self.tx_field(hash, 'last_tx')

    def tx_owner(self, hash):
        """Return transaction owner."""
        return self.tx_field(hash, 'owner')

    def tx_tags(self, hash):
        """Return transaction tags."""
        return self.tx_field(hash, 'tags')

    def tx_target(self, hash):
        """Return transaction target."""
        return self.tx_field(hash, 'target')

    def tx_quantity(self, hash):
        """Return transaction quantity."""
        return self.tx_field(hash, 'quantity')

    def tx_data(self, hash):
        """Return transaction data."""
        return self.tx_field(hash, 'data')

    def tx_signature(self, hash):
        """Return transaction signature."""
        return self.tx_field(hash, 'signature')

    def tx_reward(self, hash):
        """Return transaction reward."""
        return self.tx_field(hash, 'reward')

    def height(self):
        """Return the current block hieght."""
        response = self._get("{}/height")
        return int(response.text)

    def data(self, txid, ext = ""):
        """
        Get the decoded data from a transaction.

        TODO: content type may impact something here. in erlang it looks like this forwards to {}/tx/data .

        The transaction is pending: Pending
        The provided transaction ID is not valid or the field name is not valid: Invalid hash.
        A transaction with the given ID could not be found: Not Found.
        """
        response = self._get("{}/{}{}/", txid, ext)
        return response.content


    def _get(self, format = "{}", *params, **request_kwparams):
        url = format.format(self.api_url, *params)

        request = requests.Request(**{"method": "GET", "url": url, **request_kwparams})
        response = self.session.send(request.prepare())

        if response.status_code == 200:
            return response
        else:
            logger.error(response.text)
            raise ArweaveTransactionException(response.text)

    def _post(self, data, format = "{}", *params, **request_kwparams):
        url = format.format(self.api_url, *params)

        headers = {'Content-Type': 'application/json', 'Accept': 'text/plain'}

        request = requests.Request(**{"method": "POST", "url": url, "data": data, "headers": headers, **request_kwparams})
        response = self.session.send(request.prepare())

        logger.debug("{}\n\n{}".format(response.text, self.json_data))

        if response.status_code == 200:
            logger.debug("RESPONSE 200: {}".format(response.text))
            return response
        else:
            logger.error("{}\n\n{}".format(response.text, json_data))
            raise ArweaveTransactionException(response.text, json_data)
