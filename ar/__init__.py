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

logger = logging.getLogger(__name__)

from ar.gateways import GOOD as PUBLIC_GATEWAYS

DEFAULT_API_URL = PUBLIC_GATEWAYS[0] if len(PUBLIC_GATEWAYS) else 'https://arweave.net/'

DEFAULT_HTTP_IFACE_PORT = 1984

FORK_1_7   = 235200  # Targeting 2019-07-08 UTC
FORK_1_8   = 269510  # Targeting 2019-08-29 UTC
FORK_1_9   = 315700  # Targeting 2019-11-04 UTC
FORK_2_0   = 422250  # Targeting 2020-04-09 10:00 UTC
FORK_2_2   = 552180  # Targeting 2020-10-21 13:00 UTC
FORK_2_3   = 591140  # Targeting 2020-12-21 11:00 UTC
FORK_2_4   = 633720  # Targeting 2021-02-24 11:50 UTC
FORK_2_5   = 812970
FORK_2_6   = 1132210 # Targeting 2023-03-06 14:00 UTC
FORK_2_6_8 = 1189560 # Targeting 2023-05-30 16:00 UTC
FORK_2_7   = 1275480 # Targeting 2023-10-04 14:00 UTC
FORK_2_7_1 = 1316410 # Targeting 2023-12-05 14:00 UTC
FORK_2_7_2 = 1391330 # Targeting 2024-03-26 14:00 UTC
FORK_2_8   = float('inf')

# todo use these
HASH_ALG = 'sha256'
DEEP_HASH_ALG = 'sha384'
MERKLE_HASH_ALG = 'sha384'
HASH_SZ = 256
SIGN_ALG = 'rsa'
PRIV_KEY_SZ = 4096

DEFAULT_DIFF = 6
TARGET_BLOCK_TIME = 120
RETARGET_BLOCKS = 10

BLOCK_PER_YEAR = 525600 / (TARGET_BLOCK_TIME / 60)
#RETARGET_TOLERANCE_UPPER_BOUND = TARGET_TIME * RETARGET_BLOCKS + TARGET_TIME
#RETARGET_TOLERANCE_LOWER_BOUND = TARGET_TIME * RETARGET_BLOCKS - TARGET_TIME
RETARGET_TOLERANCE = 0.1

JOIN_CLOCK_TOLERANCE = 15
MAX_BLOCK_PROPAGATION_TIME = 60
CLOCK_DRIFT_MAX = 5

GENESIS_TOKENS = 55000000
WINSTON_PER_AR = 1000000000000

# How far into the past or future the block can be in order to be accepted for
# processing.
STORE_BLOCKS_BEHIND_CURRENT = 50
# The maximum lag when fork recovery (chain reorganisation) is performed.
CHECKPOINT_DEPTH = 18

# The recommended depth of the block to use as an anchor for transactions.
# The corresponding block hash is returned by the GET/tx_anchor endpoint.
SUGGESTED_TX_ANCHOR_DEPTH = 5

# The number of blocks returned in the /info 'recent' field
RECENT_BLOCKS_WITHOUT_TIMESTAMP = 5

# The maximum byte size of a single POST body.
MAX_BODY_SIZE = 15 * 1024 * 1024

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
# Default timeout for establishing an HTTP connection.
NETWORK_HTTP_REQUEST_CONNECT_TIMEOUT = 10 * 1000
# Default timeout used when sending to and receiving from a TCP socket
# when making an HTTP request.
NETWORK_REQUEST_SEND_TIMEOUT = 60 * 1000
# The time in milliseconds to wait before retrying
# a failed join (block index download) attempt.
REJOIN_TIMEOUT = 10 * 1000
# How many times to retry fetching the block index from each of
# the peers before giving up.
REJOIN_RETRIES = 3
# Maximum allowed number of accepted requests per minute per IP.
DEFAULT_REQUESTS_PER_MINUTE_LIMIT  = 900
# Number of seconds an IP address should be completely banned from doing
# HTTP requests after posting an invalid block.
BAD_BLOCK_BAN_TIME = 24 * 60 * 60

# A part of transaction propagation delay independent from the size, in seconds.
BASE_TX_PROPAGATION_DELAY = 30

# A conservative assumption of the network spede used to
# estimate the transaction propagation delay. It does not include
# the base delay, the time the transaction spends in the priority queue,
# and the time it takes to propagate the transaction to peers.
TX_PROPAGATION_BITS_PER_SECOND = 3000000 # 3 mbps

# The number of peers to send new blocks to in parallel.
BLOCK_PROPAGATION_PARALLELIZATION = 20

# The maximum number of peers to propagate txs to, by default.
DEFAULT_MAX_PROPAGATION_PEERS = 16

# The maximum number of peers to propagate blocks to, by default.
DEFAULT_MAX_BLOCK_PROPAGATION_PEERS = 1000

# When the transaction data size is smller than this number of bytes,
# the transaction is gossiped to the peer without a prior check if the peer
# already has this transaction
TX_SEND_WITHOUT_ASKING_SIZE_LIMIT = 1000

#REWARD_DELAY = BLOCK_PER_YEAR/4

RANDOMX_DIFF_ADJUSTMENT = -14
RANDOMX_KEY_SWAP_FREQ = 2000
RANDOMX_MIN_KEY_GEN_AHEAD = 30 + STORE_BLOCKS_BEHIND_CURRENT
RANDOMX_MAX_KEY_GEN_AHEAD = 90 + STORE_BLOCKS_BEHIND_CURRENT
#RANDOMX_STATE_POLL_INTERVAL = TARGET_TIME
RANDOMX_KEEP_KEY = STORE_BLOCKS_BEHIND_CURRENT

# Max allowed difficulty multiplication and division factors, before the fork 2.4
DIFF_ADJUSTMENT_DOWN_LIMIT = 2
DIFF_ADJUSTMENT_UP_LIMIT = 4

# Maximum size of a single data chunk, in bytes.
DATA_CHUNK_SIZE = 256 * 1024

# The maximum allowed packing difficulty.
MAX_PACKING_DIFFICULTY = 32

# The number of sub-chunks in a compositely packed chunk.
# The composite packing with the pcking difficulty 1 matches approximately the non-composite
# 2.6 packing in terms of computational costs.
COMPOSITE_PACKING_SUB_CHUNK_COUNT = 32

# The size of a unit sub-chunk in the compositely packed chunk.
COMPOSITE_PACKING_SUB_CHUNK_SIZE = DATA_CHUNK_SIZE // COMPOSITE_PACKING_SUB_CHUNK_COUNT

# The number of RndomX rounds used for a single iteration of packing of a single sub-chunk
# during the composite packing.
COMPOSITE_PACKING_ROUND_COUNT = 10

# Maximum size of a `data_path`, in bytes.
MAX_PATH_SIZE = 256 * 1024

# The size of data chunk hashes, in bytes.
CHUNK_ID_HASH_SIZE = 32

NOTE_SIZE = 32

# The speed in chunks/s of moving the fork 2.5 packing treshold.
PACKING_2_5_THRESHOLD_CHUNKS_PER_SECOND = 10

PADDING_NODE_DATA_ROOT = b''

INITIAL_VDF_DIFFICULTY = 600_000

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
from .manifest import Manifest
from .bundle import Bundle, DataItem, ANS104BundleHeader, ANS104DataItemHeader

