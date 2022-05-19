import json, requests

from . import DEFAULT_API_URL, logger, ArweaveTransactionException

class Peer(object):
    # peer api [incomplete]:
    # - https://docs.arweave.org/developers/server/http-api
    # - https://github.com/ArweaveTeam/arweave/blob/master/apps/arweave/src/ar_http_iface_middleware.erl#L132
    # - https://github.com/ArweaveTeam/arweave/blob/master/apps/arweave/src/ar_http_iface_client.erl

    def __init__(self, api_url = DEFAULT_API_URL):
        self.api_url = api_url

    def _get(self, format, *params):
        url = format.format(self.api_url, *params)

        response = requests.get(url)

        if response.status_code == 200:
            return response
        else:
            logger.error(response.text)
            raise ArweaveTransactionException(response.text)

    def _post(self, json_data, format, *params):
        url = format.format(self.api_url, *params)

        headers = {'Content-Type': 'application/json', 'Accept': 'text/plain'}

        response = requests.post(url, data=json_data, headers=headers)

        logger.debug("{}\n\n{}".format(response.text, self.json_data))

        if response.status_code == 200:
            logger.debug("RESPONSE 200: {}".format(response.text))
            return response
        else:
            logger.error("{}\n\n{}".format(response.text, json_data))
            raise ArweaveTransactionException(response.text, json_data)
        

    def tx(self, txid):
        """Get Transaction by ID"""
        tx_response = self._get("{}/tx/{}", txid)
        return tx_response.text

    def tx_status(self, txid):
        """Get Transaction Status"""
        response = self._get("{}/tx/{}/status", txid)
        return json.loads(response.text)

    def tx_field(self, txid, field):
        """Get Transaction Field"""
        response = self._get("{}/tx/{}/{}", txid, field)
        return json.loads(response.text)

    def data(self, txid):
        """
        Get the decoded data from a transaction.

        The content type is not preserved.

        The transaction is pending: Pending
        The provided transaction ID is not valid or the field name is not valid: Invalid hash.
        A transaction with the given ID could not be found: Not Found.
        """
        response = self._get("{}/{}/", txid)
        return response.content

    def price(self, data_size=0, target_address=None):
        """Get Transaction Price"""
        if target_address:
            response = self._get("{}/price/{}/{}", data_size, target_address)
        else:
            response = self._get("{}/price/{}", data_size)
        return response.text

    def send(self, json_data):
        """Submit a Transaction"""
        response = self._post(json_data)
        return response.text

    def wallet_balance(self, address):
        """Get a Wallet Balance"""
        response = self._get("{}/wallet/{}/balance", address)
        return response.text

    def tx_anchor(self):
        # TODO: the docs say this should be https://arweave.net/wallet/{address}/last_tx
        """Get Last Transaction ID"""
        last_tx_response = self._get("{}/tx_anchor")
        return last_tx_response.text

    def block_hash(self, block_hash):
        """Get Block by ID"""
        response = self._get("{}/block/hash/{}", block_hash)
        return json.loads(response.text)

    def info(self):
        """Network Info"""
        response = self._get("{}/info")
        return json.loads(response.text)

    def peers(self):
        """Peer list"""
        response = self._get("{}/peers")
        return json.loads(response.text)

    def chunk(self, json_data):
        """
        Upload Data Chunks

        {
          "data_root": "<Base64URL encoded data merkle root>",
          "data_size": "a number, the size of transaction in bytes",
          "data_path": "<Base64URL encoded inclusion proof>",
          "chunk": "<Base64URL encoded data chunk>",
          "offset": "<a number from [start_offset, start_offset + chunk size), relative to other chunks>"
        }
        """
        response = self._post(json_data, "{}/chunk")

    def tx_data(self, txid):
        """Get Transaction Data"""
        response = self._get("{}/tx/{}/data", txid)
        return response.content

    def tx_offset(self, txid):
        """Get Transaction Offset and Size"""
        response = self._get("{}/tx/{}/offset", txid)
        return response.text
