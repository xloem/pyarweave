from ar import ArweaveNetworkException
from ar.peer import HTTPClient

DEFAULT_API_URL = 'https://node2.bundlr.network'
DEFAULT_CHAIN = 'arweave'

class Node(HTTPClient):
    def __init__(self, api_url = DEFAULT_API_URL, timeout = None, retries = 5, outgoing_connections = 100, requests_per_period = 10000, period_sec = 60):
        super().__init__(api_url, timeout, retries, outgoing_connections = outgoing_connections, requests_per_period = requests_per_period, period_sec = period_sec)

    def account_withdrawals_address(self, address, currency = DEFAULT_CHAIN):
        '''Gets the nonce used for withdrawal request validation from the bundler'''
        response = self._get('account', 'withdrawals', currency, '?address=' + address)
        return response.text

    def account_balance(self, address, currency = DEFAULT_CHAIN):
        '''
        Gets the balance on the current bundler for the specified user

        {
            "balance": "<balance>"
        }
        '''
        response = self._get_json('account', 'balance', currency, '?address=' + address)
        return response

    def info(self):
        '''
        {
            "version": "<x.y.z>",
            "addresses": {
                "<currency>": "<bundler address>",
            },
            "gateway": "<arweave api host>",
        }
        '''
        response = self._get_json('info')
        return response

    def price(self, bytes, currency = DEFAULT_CHAIN):
        '''Calculates the price for [bytes] bytes paid for with [currency] for the loaded bundlr node.'''
        response = self._get('price', currency, str(bytes))
        return int(response.text)
        
    def send_tx(self, transaction_bytes, currency = DEFAULT_CHAIN):
        '''
        Uploads a given transaction to the bundler

        {
            "id": "<arweave txid for data>",
            "public": "<public key>",
            "signature": "<signature>",
            "block": "<cutoff height by which tx must be mined in arweave>"
        }
        402: Not enough funds to send data
        201: It looks like this can mean that a transaction is already received
        '''
        response = self._post(transaction_bytes, 'tx', currency)
        try:
            return response.json()
        except Exception as exc:
            raise ArweaveNetworkException(response.text, response.status_code, exc, response)

    def send_chunks(self, databytes, txid, offset, currency = DEFAULT_CHAIN):
        response = self._post(databytes, 'chunks', currency, txid, offset)
        return response.text # unsure

    def chunks(self, txid, size, currency = DEFAULT_CHAIN):
        response = self._get_json('chunks', currency, txid, size)
        return response

    def send_chunks_finished(self, txid, currency = DEFAULT_CHAIN):
        response = self._post(None, 'chunks', currency, txid, '-1')
        return response.text

    def data(self, txid):
        response = self._get('tx', tx_id, 'data')
        return response.content
