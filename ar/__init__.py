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

import logging

PUBLIC_GATEWAYS = [
    'https://arweave.net',
    'https://arweave.live',
    'https://arweave-dev.everpay.io'
]

DEFAULT_API_URL = PUBLIC_GATEWAYS[0]

DEFAULT_HTTP_IFACE_PORT = 1984

FORK_1_7 = 235200 # Targeting 2019-07-08 UTC
FORK_1_8 = 269510 # Targeting 2019-08-29 UTC
FORK_1_9 = 315700 # Targeting 2019-11-04 UTC
FORK_2_0 = 422250 # Targeting 2020-04-09 10:00 UTC
FORK_2_2 = 552180 # Targeting 2020-10-21 13:00 UTC
FORK_2_3 = 591140 # Targeting 2020-12-21 11:00 UTC
FORK_2_4 = 633720 # Targeting 2021-02-24 11:50 UTC
FORK_2_5 = 812970

# todo use these
HASH_ALG = 'sha256'
DEEP_HASH_ALG = 'sha384'
MERKLE_HASH_ALG = 'sha384'
HASH_SZ = 256
SIGN_ALG = 'rsa'
PRIV_KEY_SZ = 4096

DEFAULT_DIFF = 6
TARGET_TIME = 120
RETARGET_BLOCKS = 10

BLOCK_PER_YEAR = 525600 / (TARGET_TIME / 60)
RETARGET_TOLERANCE_UPPER_BOUND = TARGET_TIME * RETARGET_BLOCKS + TARGET_TIME
RETARGET_TOLERANCE_LOWER_BOUND = TARGET_TIME * RETARGET_BLOCKS - TARGET_TIME
RETARGET_TOLERANCE = 0.1

JOIN_CLOCK_TOLERANCE = 15
MAX_BLOCK_PROPAGATION_TIME = 60
CLOCK_DRIFT_MAX = 5

GENESIS_TOKENS = 55000000
WINSTON_PER_AR = 1000000000000

# How far into the past or future the block can be in order to be accepted for
# processing. The maximum lag when fork recovery (chain reorganisation) is performed.
STORE_BLOCKS_BEHIND_CURRENT = 50

# The maximum allowed size in bytes for the data field of
# a format=1 transaction.
TX_DATA_SIZE_LIMIT = 10 * 1024 * 1024

# The maximum allowed size in bytes for the combined data fields of
# the format=1 transactions included in a block. Must be greater than
# or equal to ?TX_DATA_SIZE_LIMIT.
BLOCK_TX_DATA_SIZE_LIMIT = TX_DATA_SIZE_LIMIT

# The maximum number of transactions (both format=1 and format=2) in a block.
BLOCK_TX_COUNT_LIMIT = 1000

# The base transaction size the transaction fee must pay for.
TX_SIZE_BASE = 3210

MEMPOOL_HEADER_SIZE_LIMIT = 250 * 1024 * 1024
MEMPOOL_DATA_SIZE_LIMIT = 500 * 1024 * 1024

MAX_TX_ANCHOR_DEPTH = STORE_BLOCKS_BEHIND_CURRENT

# defaults from the erlang peer
NETWORK_HTTP_REQUEST_CONNECT_TIMEOUT = 10 * 1000
NETWORK_REQUEST_SEND_TIMEOUT = 60 * 1000
# Maximum allowed number of accepted requests per minute per IP.
DEFAULT_REQUESTS_PER_MINUTE_LIMIT  = 900
# Default number of seconds an IP address is completely banned from doing
# HTTP requests after posting a block with bad PoW.
DEFAULT_BAD_POW_BAN_TIME = 24 * 60 * 60

REWARD_DELAY = BLOCK_PER_YEAR/4

RANDOMX_DIFF_ADJUSTMENT = -14
RANDOMX_KEY_SWAP_FREQ = 2000
RANDOMX_MIN_KEY_GEN_AHEAD = 30 + STORE_BLOCKS_BEHIND_CURRENT
RANDOMX_MAX_KEY_GEN_AHEAD = 90 + STORE_BLOCKS_BEHIND_CURRENT
RANDOMX_STATE_POLL_INTERVAL = TARGET_TIME
RANDOMX_KEEP_KEY = STORE_BLOCKS_BEHIND_CURRENT

DIFF_ADJUSTMENT_DOWN_LIMIT = 2
DIFF_ADJUSTMENT_UP_LIMIT = 4

# Maximum size of a single data chunk, in bytes.
DATA_CHUNK_SIZE = 256 * 1024

# Maximum size of a `data_path`, in bytes.
MAX_PATH_SIZE = 256 * 1024

# The size of data chunk hashes, in bytes.
CHUNK_ID_HASH_SIZE = 32

NOTE_SIZE = 32

PACKING_THRESHOLD_CHUNKS_PER_SECOND = 10

PADDING_NODE_DATA_ROOT = b''

logger = logging.getLogger(__name__)

class ArweaveException(Exception):
    pass

class ArweaveNetworkException(ArweaveException):
    pass

__all__ = [
    'Peer', 'Wallet', 'Transaction', 'Block',
    'Bundle', 'DataItem', 'ANS104BundleHeader', 'ANS104DataItemHeader',
    'arql', 'ArweaveException', 'logger', 'ArweaveTransactionException']

ArweaveTransactionException = ArweaveException

from .peer import Peer
from .wallet import Wallet
from .transaction import Transaction
from .block import Block
from .chunk import Chunk
from .stream import PeerStream, GatewayStream
from .arweave_lib import arql
from .bundle import Bundle, DataItem, ANS104BundleHeader, ANS104DataItemHeader

