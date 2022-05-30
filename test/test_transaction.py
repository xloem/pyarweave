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


from ar import Peer, Transaction
import pytest


def test_live_transaction_reserialization():
    peer = Peer()
    height = peer.height()
    sometx = peer.current_block()['txs'][0]
    txbytes = peer.tx2(sometx)
    tx = Transaction.frombytes(txbytes)
    assert tx.tobytes() == txbytes

if __name__ == '__main__':
    test_live_transaction_reserialization()
