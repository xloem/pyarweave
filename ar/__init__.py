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

logger = logging.getLogger(__name__)

class ArweaveException(Exception):
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
from .arweave_lib import arql
from .bundle import Bundle, DataItem, ANS104BundleHeader, ANS104DataItemHeader

