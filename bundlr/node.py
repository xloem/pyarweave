from ar.peer import HTTPClient

DEFAULT_API_URL = 'https://node2.bundlr.network'
DEFAULT_CHAIN = 'arweave'

class Node(HTTPClient):
    def __init__(self, api_url = DEFAULT_API_URL, timeout = None, retries = 5):
        super().__init__(api_url, timeout, retries)

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
        response = self._get('account', 'balance', currency, '?address=' + address)
        return response.json()

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
        response = self._get('info')
        return response.json()

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
        '''
        response = self._post(transaction_bytes, 'tx', currency)
        return response.json()

    def send_chunks(self, databytes, txid, offset, currency = DEFAULT_CHAIN):
        response = self._post(databytes, 'chunks', currency, txid, offset)
        return response.text # unsure

    def chunks(self, txid, size, currency = DEFAULT_CHAIN):
        response = self._get('chunks', currency, txid, size)
        return response.json()

    def send_chunks_finished(self, txid, currency = DEFAULT_CHAIN):
        response = self._post(None, 'chunks', currency, txid, '-1')
        return response.text

    def data(self, txid):
        response = self._get('tx', tx_id, 'data')
        return response.content
