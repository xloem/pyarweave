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

DEFAULT_GATEWAY_ADDRESS_REGISTRY_CACHE = 'https://dev.arns.app/v1/contract/bLAgYxAdX2Ry-nt6aH2ixgvJXbpsEYm28NgJgyqfs-U/gateways'
TEST_GATEWAY_ADDRESS_REGISTRY_CACHE = 'https://dev.arns.app/v1/contract/E-pRI1bokGWQBqHnbut9rsHSt9Ypbldos3bAtwg4JMc/gateways'

PUBLIC_GATEWAYS = [
    'https://arweave.net',
    'https://ar-io.dev',
    'http://gatewaypie.com',
    'https://vilenarios.com',
    'https://permagate.io',
    'https://g8way.io',
    'https://frostor.xyz',
    'https://blessingway.xyz',
    'https://bobinstein.com',
    'https://ar-dreamnode.xyz',
    'https://dwentz.xyz',
    'https://sulapan.com',
    'https://ruesandora.xyz',
    'https://rnodescrns.online',
    'https://ar-kynraze.xyz',
    'https://neuweltgeld.xyz',
    'https://mpiicha.games',
    'https://jajangmedia.games',
    'https://mojochoirul.works',
    'https://crbaa.xyz',
    'https://saktinaga.live',
    'https://ahmkah.online',
    'https://spt-node.dev',
    'https://cappucino.online',
    'https://nodecoyote.xyz',
    'https://warbandd.store',
    'https://sannane.online',
    'https://logosnodos.site',
    'https://ruangnode.xyz',
    'https://optimysthic.site',
    'https://dnsarz.wtf',
    'https://anekagame.live',
    'https://learnandhunt.me',
    'https://arweave.tech',
    'https://kaelvnode.xyz',
    'https://daffhaidar.me',
    'https://commissar.xyz',
    'https://tuga5.tech',
    'https://diafora.site',
    'https://azxx.xyz',
    'https://elessardarken.xyz',
    'https://thekayz.click',
    'https://002900.xyz',
    'https://kingsharald.xyz',
    'https://0xyvz.xyz',
    'https://yukovskibot.com',
    'https://mutu.pro',
    'https://shapezero.xyz',
    'https://kanan1.shop',
    'https://nodetester.com',
    'https://permanence-testing.org',
    'https://erenynk.xyz',
    'https://chaintech.site',
    'https://redwhiteconnect.xyz',
    'https://kriptosekici.online',
    'https://olpakmetehan.site',
    'https://kenyaligeralt.xyz',
    'https://yusufaytn.xyz',
    'https://mysbe.xyz',
    'https://kazazel.xyz',
    'https://aralper.xyz',
    'https://berkanky.site',
    'https://vevivo.xyz',
    'https://macanta.site',
    'https://mrdecode.tech',
    'https://jembutkucing.tech',
    'https://xyznodes.site',
    'https://0xmonyaaa.xyz',
    'https://malghz.cloud',
    'https://fisneci.com',
    'https://blackswannodes.xyz',
    'https://salakk.online',
    'https://scriqtar.site',
    'https://rodruquez.online',
    'https://velaryon.xyz',
    'https://mtntkcn1.store',
    'https://validatorario.xyz',
    'https://blockchainzk.website',
    'https://lostgame.online',
    'https://tikir.store',
    'https://dilsinay.online',
    'https://testnetnodes.xyz',
    'https://analin.xyz',
    'https://zionalc.online',
    'https://bootstrap.lol',
    'https://cayu7pa.xyz',
    'https://grenimo.xyz',
    'https://cahil.store',
    'https://sefaaa.online',
    'https://jaxtothehell.xyz',
    'https://canduesed.xyz',
    'https://anaraydinli.xyz',
    'https://blacktokyo.online',
    'https://coinhunterstr.site',
    'https://digitclone.online',
    'https://armanmind.lol',
    'https://htonka.xyz',
    'https://afiq.wiki',
    'https://byfalib.xyz',
    'https://crtexpert.com.tr',
    'https://ezraike.art',
    'https://bolobolo.site',
    'https://rerererararags.store',
    'https://aleko0o.store',
    'https://shadow39.online',
    'https://thecoldblooded.net',
    'https://omersukrubektas.website',
    'https://sedat07.xyz',
    'https://flechemano.com',
    'https://love4src.com',
    'https://mustafakaya.xyz',
    'https://lethuan.xyz',
    'https://0xknowledge.store',
    'https://shibamaru.tech',
    'https://maidyo.xyz',
    'https://arweave.fllstck.dev',
    'https://permabridge.com',
    'https://arbr.pro',
    'https://khaldrogo.site',
    'https://sacittnoderunner.store',
    'https://enesss.online',
    'https://cyanalp.cfd',
    'https://genesisprime.site',
    'https://soulbreaker.xyz',
    'https://alicans.online',
    'https://mpsnode.online',
    'https://itachistore.tech',
    'https://beritcryptoo.me',
    'https://arendor.xyz',
    'https://ancolclown.xyz',
    'https://suanggi.live',
    'https://valarian.xyz',
    'https://gojosatorus.live',
    'https://maplesyrup-ario.my.id',
    'https://alpt.autos',
    'https://moruehoca.online',
    'https://dasamuka.cloud',
    'https://0xsaitomo.xyz',
    'https://bunyaminbakibaltaci.com',
    'https://kagithavlu.store',
    'https://karakura.xyz',
    'https://alexxis.store',
    'https://dlzvy.tech',
    'https://200323.xyz',
    'https://sokrates.site',
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

