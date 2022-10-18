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

import hashlib
import struct
import functools
from .file_io import read_file_chunks
from . import concat_buffers, b64enc, b64dec
from json import JSONEncoder

CHUNK_SIZE = 256 * 1024
NOTE_SIZE = 32
HASH_SIZE = 32
MAX_CHUNK_SIZE = 256 * 1024
MIN_CHUNK_SIZE = 32 * 1024


class NodeTypeException(Exception):
    pass


class Node:
    def __init__(self, id_raw=b'', type=None, byte_range=0, max_byte_range=0, parent=None):
        self.id_raw = id_raw
        self.type = type
        self.byte_range = byte_range
        self.max_byte_range = max_byte_range
        self.parent = parent

    # I patched binary coding of data paths in here, but it may go better
    # elsewhere. Haven't reviewed most of these things.
    @classmethod
    def frombytes(cls, bytes, min_byte_range = 0, max_byte_range = None):
        import io; stream = io.BytesIO(bytes)
        return cls.fromstream(stream, len(bytes), min_byte_range)
    @staticmethod
    def fromstream(stream, length, min_byte_range = 0, max_byte_range = None):
        branches_raw = []
        branches = []
        remaining = length

        while remaining > HASH_SIZE + NOTE_SIZE:
            raw = stream.read(2*HASH_SIZE + NOTE_SIZE)
            left_raw, right_raw, midpoint_raw = (
                raw[:HASH_SIZE],
                raw[HASH_SIZE:2*HASH_SIZE],
                raw[2*HASH_SIZE:]

            )
            midpoint = int.from_bytes(midpoint_raw, 'big')
            id_raw = hash_raw([
                hash_raw(left_raw),
                hash_raw(right_raw),
                hash_raw(midpoint_raw)
            ])
            branches_raw.append((left_raw, right_raw))
            branches.append(BranchNode(
                    id_raw = id_raw,
                    byte_range = midpoint,
                    max_byte_range = None,
                    parent = branches[-1] if len(branches) else None
            ))
            remaining -= 2*HASH_SIZE + NOTE_SIZE

        leaf_raw = stream.read(HASH_SIZE + NOTE_SIZE)
        leaf_data_hash = leaf_raw[:HASH_SIZE]
        leaf_max_byte_range = buffer_to_int(leaf_raw[HASH_SIZE:])
        branches_raw.append((leaf_data_hash,))
        branches.append(LeafNode(
            max_byte_range = leaf_max_byte_range,
            data_hash = leaf_data_hash,
            min_byte_range = None,
            parent = branches[-1] if len(branches) else None
        ))

        branches[0].min_byte_range = min_byte_range
        if branches[0].max_byte_range is None:
            branches[0].max_byte_range = max_byte_range

        leaf_min_byte_range = min_byte_range

        for branch, next_branch, (l_hash, r_hash) in zip(branches[:-1], branches[1:], branches_raw):
            midpoint = branch.byte_range
            if leaf_max_byte_range <= midpoint:
                assert next_branch.id_raw == l_hash
                if type(next_branch) is BranchNode:
                    assert next_branch.byte_range <= midpoint
                next_branch.min_byte_range = branch.min_byte_range
                if type(next_branch) is LeafNode:
                    assert next_branch.max_byte_range == midpoint
                next_branch.max_byte_range = midpoint
                branch.left_child = next_branch
                branch.right_child = type(next_branch)(
                    id_raw = r_hash,
                    min_byte_range = midpoint,
                    max_byte_range = branch.max_byte_range if branch.max_byte_range is not None else 0,
                    byte_range = None,
                    parent = branch,
                    data_hash = b''
                )
                branch.right_child.id_raw = r_hash
            else: # leaf_max_byte_range > midpoint
                assert next_branch.id_raw == r_hash
                if type(next_branch) is BranchNode:
                    assert next_branch.byte_range >= midpoint # note that branches can be zero-sized
                next_branch.min_byte_range = midpoint
                if type(next_branch) is LeafNode:
                    if branch.max_byte_range is not None:
                        assert next_branch.max_byte_range == branch.max_byte_range
                else:
                    next_branch.max_byte_range = branch.max_byte_range
                branch.left_child = type(next_branch)(
                    id_raw = l_hash,
                    min_byte_range = branch.min_byte_range,
                    max_byte_range = midpoint,
                    byte_range = None,
                    parent = branch,
                    data_hash = b''
                )
                branch.left_child.id_raw = l_hash
                branch.right_child = next_branch
        branches[0].leaf = branches[-1]
        branches[-1].root = branches[0]
        return branches


class BranchNode(Node):
    def __init__(self, *args, **kwargs):
        super(BranchNode, self).__init__(id_raw=kwargs['id_raw'], max_byte_range=kwargs['max_byte_range'],
                                         byte_range=kwargs['byte_range'], parent=kwargs['parent'])
        self.type = 'branch'
        self.left_child = kwargs.get('left_child', None)
        self.right_child = kwargs.get('right_child', None)
        if self.left_child is not None:
            self.left_child.parent = self
        if self.right_child is not None:
            self.right_child.parent = self

    def add(self, node):
        if node.max_byte_range <= self.byte_range:
            assert self.left_child is None
            self.left_child = node
        else:
            assert self.right_child is None
            self.right_child = node

    def tobytes(self):
        if self.byte_range is not None:
            return b''.join((
                self.left_child.id_raw,
                self.right_child.id_raw,
                int_to_buffer(self.byte_range),
                self.left_child.tobytes(),
                self.right_child.tobytes()
            ))
        else:
            return b''


class LeafNode(Node):
    def __init__(self, *args, **kwargs):
        super(LeafNode, self).__init__(max_byte_range=kwargs['max_byte_range'],parent=kwargs['parent'])
        self.data_hash = kwargs['data_hash'] # raw bytes
        self.min_byte_range = kwargs['min_byte_range']
        self.id_raw = hash_raw([hash_raw(self.data_hash), hash_raw(int_to_buffer(self.max_byte_range))])
        self.type = 'leaf'

    def tobytes(self):
        if self.data_hash:
            return b''.join((
                self.data_hash,
                int_to_buffer(self.max_byte_range)
            ))
        else:
            return b''


class TaggedChunk:
    def __init__(self, tc_id, end):
        self.id = tc_id
        self.end = end


class Chunk:
    def __init__(self, data_hash, data_size=0, min_byte_range=0, max_byte_range=0):
        self.data_size = data_size
        self.data_hash = data_hash
        self.min_byte_range = min_byte_range
        self.max_byte_range = max_byte_range

    def to_dict(self):
        print('boom!')
        return {
            'dataHash': b64enc(self.data_hash).decode(),
            'maxByteRange': self.max_byte_range,
            'minByteRange': self.min_byte_range
        }


class HashNode:
    def __init__(self, hn_id, max):
        self.id = hn_id
        self.max = max


class Proof:
    def __init__(self, offset, proof):
        self.offset = offset
        self.proof = proof

    def to_dict(self):
        return {
            'offset': self.offset,
            'proof': b64enc(self.proof).decode()
        }


class ValidatedPathResult:
    def __init__(self, offset, left_bound, right_bound, chunk_size):
        self.offset = offset
        self.left_bound = left_bound
        self.right_bound = right_bound
        self.chunk_size = chunk_size


def chunk_data(file_handler):
    '''
    Takes the input data and chunks it into (mostly) equal sized chunks.
    The last chunk will be a bit smaller as it contains the remainder
    from the chunking process.
    :param file_handler:
    :return: chunks
    '''
    chunks = [];
    chadd = chunks.append

    cursor = 0

    for chunk in read_file_chunks(file_handler, MAX_CHUNK_SIZE):
        data_hash = hash_raw(chunk)

        cursor += len(chunk)

        chadd(
            Chunk(
                data_hash,
                data_size=len(chunk),
                min_byte_range=cursor - len(chunk),
                max_byte_range=cursor
            )
        )

    return tuple(chunks)  # lets make this a fast processing tuple for later!


def compute_root_hash(file_handler):
    root_node = generate_tree(file_handler)

    return root_node.id_raw


def generate_leaves(chunks):
    leaves = [
        LeafNode(
            data_hash=chunk.data_hash,
            min_byte_range=chunk.min_byte_range,
            max_byte_range=chunk.max_byte_range,
            parent=None
        )
        for chunk in chunks
    ]

    return tuple(leaves)


def generate_tree(file_handler):
    root_node = build_layers(generate_leaves(chunk_data(file_handler)))

    return root_node


def build_layers(nodes, level=0):
    nodes_lenth = len(nodes)

    if nodes_lenth < 2:
        left = nodes[0]
        right = None if nodes_lenth == 1 else nodes[1]
        root = hash_branch(left, right)

        return root

    next_layer = [];
    nadd = next_layer.append

    for i in range(0, nodes_lenth, 2):
        left = nodes[i]
        right = None if i + 1 > (nodes_lenth - 1) else nodes[i + 1]

        nadd(hash_branch(left, right))

    return build_layers(next_layer, level + 1)


def generate_proofs(root):
    proofs = resolve_branch_proofs(root)

    if type(proofs) == Proof:
        proofs = (proofs,)

    if type(proofs) != tuple:
        return flatten_list(proofs)

    return flatten_tuple(proofs)


def generate_transaction_chunks(file_handler):
    chunks = chunk_data(file_handler)
    leaves = generate_leaves(chunks)
    root = build_layers(leaves)
    proofs = generate_proofs(root)

    last_chunk = chunks[-1]
    if last_chunk.max_byte_range - last_chunk.min_byte_range == 0:
        chunks = chunks[:-1]
        proofs = proofs[:-1]

    return {
        'data_root': b64enc(root.id_raw),
        'chunks': chunks,
        'proofs': proofs
    }


def flatten_tuple(inputs):
    flat = [];
    fadd = flat.append

    for item in inputs:
        if type(item) == tuple:
            fadd(flatten_tuple(item))
        else:
            fadd(item)

    return tuple(flat)


def flatten_list(inputs):
    flat = [];
    fadd = flat.append;
    fexd = flat.extend

    for item in inputs:
        if type(item) == list:
            fexd(flatten_list(item))
        else:
            fadd(item)

    return flat


def resolve_branch_proofs(node, proof=b'', depth=0):
    if node.type == 'leaf':
        return Proof(
            node.max_byte_range - 1,
            concat_buffers([proof, node.data_hash, int_to_buffer(node.max_byte_range)])
        )

    if node.type == 'branch':
        partial_proof = concat_buffers([
            proof,
            node.left_child.id_raw,
            node.right_child.id_raw,
            int_to_buffer(node.byte_range)
        ])

        return [
            resolve_branch_proofs(node.left_child, partial_proof, depth + 1),
            resolve_branch_proofs(node.right_child, partial_proof, depth + 1),
        ]

    raise NodeTypeException('Unexpected node type')


def hash_branch(left, right=None):
    if not right:
        return left

    return BranchNode(
        id_raw=hash_raw(
            [
                hash_raw(left.id_raw),
                hash_raw(right.id_raw),
                hash_raw(int_to_buffer(left.max_byte_range))
            ]
        ),
        byte_range=left.max_byte_range,
        max_byte_range=right.max_byte_range,
        left_child=left,
        right_child=right,
        parent=None
    )


def hash_leaf(data, note):
    return HashNode(
        hash([hash(data), hash(int_to_buffer(note))]),
        note
    )


def hash_raw(data):
    if type(data) == list:
        data = b''.join(data)

    digest = hashlib.sha256(data).digest()
    return digest


def hash(data):
    digest = hash_raw(data)
    b64_str = b64enc(digest)
    return digest


def int_to_buffer(note):
    return int(note).to_bytes(NOTE_SIZE, 'big')


def buffer_to_int(buffer):
    assert len(buffer) == NOTE_SIZE
    return int.from_bytes(buffer, 'big')


def array_compare(a, b):
    functools.reduce(lambda x, y: x and y, map(lambda p, q: p == q, a, b), True)


def validate_path(id_raw, dest, left_bound, right_bound, path):
    if right_bound < 0:
        return False

    if dest > right_bound:
        return validate_path(id_raw, 0, right_bound - 1, right_bound, path)

    if dest < 0:
        return validate_path(id_raw, 0, 0, right_bound, path)

    if len(path) == HASH_SIZE + NOTE_SIZE:
        path_data = path[0:HASH_SIZE]
        path_data_length = len(path_data)
        end_offset_buffer = path[path_data_length:path_data_length + NOTE_SIZE]

        path_data_hash = hash_raw([
            hash_raw(path_data),
            hash_raw(end_offset_buffer)
        ])

        result = id_raw == path_data_hash

        if result:
            return ValidatedPathResult(right_bound - 1, left_bound, right_bound, right_bound - left_bound)

        return False

    left = path[:HASH_SIZE]
    left_length = len(left)
    right = path[left_length: left_length + HASH_SIZE]
    right_length = len(right)

    offset_buffer = path[left_length + right_length: left_length + right_length + NOTE_SIZE]
    offset = buffer_to_int(offset_buffer)

    remainder = path[left_length + right_length + len(offset_buffer):]

    path_hash = hash([
        hash(left),
        hash(right),
        hash(offset_buffer)
    ])

    if id_raw == path_hash:
        if dest < offset:
            return validate_path(
                left,
                dest,
                left_bound,
                min(right_bound, offset),
                remainder
            )

        return validate_path(
            right,
            dest,
            max(left_bound, offset),
            right_bound,
            remainder
        )

    return False


def debug(proof, output=''):
    if len(proof) < 1:
        return output

    left = proof[:HASH_SIZE]
    right = proof[len(left):len(left) + HASH_SIZE]
    offset_buffer = proof[
                    len(left) + len(right): len(left) + len(right) + HASH_SIZE
                    ]

    offset = buffer_to_int(offset_buffer)

    remainder = proof[:len(left) + len(right) + len(offset_buffer)]

    path_hash = hash([
        hash(left),
        hash(right),
        hash(offset_buffer)
    ])

    updated_output = '{}\n{},{},{} => {}'.format(
        output,
        bytearray(left),
        bytearray(right),
        offset,
        bytearray(path_hash)
    )

    return debug(remainder, updated_output)
