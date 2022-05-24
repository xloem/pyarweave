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


from ar import Peer, Block
import pytest


def test_live_block_reserialization():
    peer = Peer()
    height = peer.height()
    blockbytes = peer.block2(height)
    blockjson = peer.block(height)
    blockfrombytes = Block.frombytes(blockbytes)
    blockfromjson = Block.fromjson(blockjson)
    assert blockfrombytes.tobytes() == blockbytes
    assert blockfromjson.tobytes() == blockbytes
    assert blockfrombytes.tojson() == blockjson
    assert blockfromjson.tojson() == blockjson

if __name__ == '__main__':
    test_live_block_reserialization()
