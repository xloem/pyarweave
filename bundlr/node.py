from ar import ArweaveNetworkException
from ar.peer import HTTPClient, Peer
from ar.stream import GatewayStream

TURBO = 'https://turbo.ardrive.io'
TURBO_SUBSIDY_MAX_BYTES = 107520
ARDRIVE_UPLOAD = 'https://upload.ardrive.io/v1'
ARDRIVE_PAYMENT = 'https://payment.ardrive.io/v1'
ARDRIVE_SUBSIDY_MAX_BYTES = TURBO_SUBSIDY_MAX_BYTES
BUNDLR_NODE1 = 'https://node1.bundlr.network'
BUNDLR_NODE2 = 'https://node2.bundlr.network'
BUNDLR_SUBSIDY_MAX_BYTES = 102400
# note: these irys endpoints host files themselves outside arweave
IRYS_MAINNET = 'https://uploader.irys.xyz'
IRYS_DEVNET = 'https://devnet.irys.xyz'
IRYS_SUBSIDY_MAX_BYTES = BUNDLR_SUBSIDY_MAX_BYTES
ENDPOINTS = [
    TURBO, ARDRIVE_UPLOAD, ARDRIVE_PAYMENT, BUNDLR_NODE1, BUNDLR_NODE2, IRYS_MAINNET, IRYS_DEVNET
]
DEFAULT_API_URL = TURBO
DEFAULT_CHAIN = 'arweave'
import warnings
warnings.warn('disabled bundlr fingerprint verification, update with new fingerprint from certificate transparency')
DEFAULT_API_URL_FINGERPRINT = None#'e55fec18e416f39d0edf7807534257a188c7ec4cdd3d0d6de17eb3051a4e084c'

class Node(HTTPClient):
    def __init__(self, api_url = DEFAULT_API_URL, timeout = None, retries = 5, outgoing_connections = 100, requests_per_period = 10000, period_sec = 60, cert_fingerprint = DEFAULT_API_URL_FINGERPRINT, upload_api_url = None):
        if cert_fingerprint == DEFAULT_API_URL_FINGERPRINT and api_url != DEFAULT_API_URL:
            cert_fingerprint = None
        super().__init__(api_url, timeout, retries, outgoing_connections = outgoing_connections, requests_per_period = requests_per_period, period_sec = period_sec, cert_fingerprint = cert_fingerprint, extra_headers = {'x-irys-js-sdk-version':'0.2.0'})
        self.upload_api_url = upload_api_url

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
                "<currency>": "<address>",
            },
            #"gateway": "<arweave api host>",
        }
        '''
        # also available at /
        response = self._get_json('info')
        return response

    def price(self, bytes, currency = DEFAULT_CHAIN):
        '''Calculates the price for [bytes] bytes paid for with [currency]. Error code 400 indicates invalid byte count.'''
        return self._get_json('price', currency, str(bytes))
        
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
            # response.status_code == 201 indicates the tx is already held
            raise ArweaveNetworkException(response.text, response.status_code, exc, response)

    def send_chunks(self, databytes, txid, offset=-1, currency = DEFAULT_CHAIN):
        response = self._post(databytes, 'chunks', currency, txid, offset)
        return response.text # unsure

    def chunks(self, txid=-1, size=-1, currency = DEFAULT_CHAIN):
        response = self._get_json('chunks', currency, txid, size)
        return response

    def send_chunks_finished(self, txid, currency = DEFAULT_CHAIN):
        response = self._post(None, 'chunks', currency, txid, '-1')
        return response.text

    def graphql(self, query):
        # irys-only?
        return Peer.graphql(self, query)

    def tx(self, txid):
        # irys-only?
        response = self._get_json('tx', txid)
        return response

    def status(self, txid):
        response = self._get_json('tx', txid, 'status')
        return response

    def data(self, txid, range = None):
        # irys-only?
        if range is not None:
            headers = {'Range':f'bytes={range[0]}-{range[1]}'}
        else:
            headers = {}
        response = self._get('tx', txid, 'data', headers = headers)
        return response.content

    def stream(self, txid, range = None):
        # irys-only?
        if range is not None:
            headers = {'Range':f'bytes={range[0]}-{range[1]}'}
        else:
            headers = {}
        response = self._get('tx', txid, 'data', headers = headers, stream = True)
        return GatewayStream(response)
