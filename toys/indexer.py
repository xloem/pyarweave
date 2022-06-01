import hashlib, math, os, time

import json

import ar
#import ar.multipeer

from ar.utils import b64enc, b64dec, b64dec_if_not_bytes, utf8enc_if_not_bytes, create_tag, change_tag, ensure_tag, get_tags

## HashMap

# Composed of table documents.

# Table document structure:
# TODO: TYPE could be a bitfield at the start of the document, which would provide
#       for including more records. For further compression, BLOCKHASH and TXHASH
#       could be indexed for reuse.
#
# not implemented: VERSION         1 byte = 1
#
# A sequence of 113 byte entries:
####### note, it would be more efficient to retrieve tx tags and sigs if the 2-byte index in the alphabetized block were here
#   TYPE          1 byte
#   BLOCKHASH    48 bytes
#   TXHASH       32 bytes
#   DATAITEMHASH 32 bytes
#
# Additionally, table documents have the properties:
#   COUNT
#   DEPTH

# BLOCKHASH, TXHASH, DATAITEMHASH
#   These refer uniquely to a range of bytes within a transaction containing
#   another document.
#
#   TXHASH refers to an L1 transaction containing the document, not a bundled dataitem.
#   DATAITEMHASH refers to the document's smallest surrounding transaction, a dataitem id
#               if the document is bundled, or the same L1 transaction id if it is not.
#   BLOCKHASH is the mined block containing TXHASH.
#
#   The document is defined as occupying the entire data portion of DATAITEMHASH.
#
# TYPE
#   May take on one of the following values:
#   0 or TYPE_EMPTY
#   1 or TYPE_TABLE: DATAITEMHASH is a table document with 1 greater DEPTH.
#   2 or TYPE_DATA: DATAITEMHASH is a data document
#   3 or TYPE_MANY: DATAITEMHASH is a table document tree where all children match.
#
# COUNT
#   Count is the number of txhashes in a table, and is equal to the size divided by 113.
#
# DEPTH
#   Depth reflects which part of a hash the table document relates to.
#   At depth == 0, the table reflects the leftmost bytes of the hash.
#   At maximum depth, the table reflects the rightmost bytes of the hash.
#   The root document of a hashmap has a depth of 0, and each table document a table
#   references has one greater depth.
#
#   The maximum depth can be calculated by taking the base-COUNT logarithm of the
#   base-2 exponent of the number of bits in the hash:
#      ceil(log(2**256) / log(884)) = 27, for a COUNT of 884=floor(100000/113)
#
#   But the maximum depth is never reached, because there are not 2**256 different
#   data documents to be indexed.


# Looking up items using a hashmap:
#
# Each hashmap revision is associated with a canonical root table document.
# To look up the value for a key, the key is broken up into offsets into table documents
# using modular arithmetic based on each table document's COUNT.
# 
# 1. Convert the hash to a biginteger in a little-endian manner.
# 2. Perform the modulo of the hash with the table COUNT to get the item INDEX.
# 3. Multiply INDEX by 113 to get the offset of the next TX/DATAITEM and TYPE and read them.
# 4. If the TYPE is TYPE_TABLE:
#    a. Subtract INDEX from the hash then divide the hash by COUNT for the next table.
#    b. Retrieve TXHASH and return to step 2 using the next table document.
# 5. Once the TYPE is TYPE_DATA, TYPE_EMPTY, or TYPE_MANY, the lookup is complete.
















# Creating a hashmap????
#
# The hashmap must be create at the leaves of its tree first, so as to know the txhashes
# to place in the higher indices.
#
# 1. Decide upon a maximum document size for each tree depth.
# 2. For all documents, hash and process each one using steps 4a and 4b above,
#    to create a list of item INDEXes in table documents.
# 3. Sort the list and process each item in order:
#    a. The leftmost INDEX in the item that matches the preceding item
#       represents the table document it belongs in.

# 3. Begin filling documents in-memory or on-disk in a top-down manner.
### TODO update creation steps

ZEROS32 = bytes(32)
ZEROS48 = bytes(48)

import threading

class BackedStructur:
    def __init__(self, loader, size = None, item_count = None, item_size = None, id_raw = None, bundle_raw = None, block_raw = None, tags = [], name = 'TableDoc'):
        if size is None:
            size = item_count * item_size
        elif item_count is None:
            item_count = size // item_size
            size = item_count * item_size
        elif item_size is None:
            item_size = size // item_count
        self.size = size
        self.item_size = item_size
        self.item_count = item_count
        self._id_raw = id_raw
        self._bundle_raw = bundle_raw
        self._block_raw = block_raw
        self.bytes = bytes
        self.loader = loader
        self.tags = tags
        self.dirty = False
        self.name = name

        if self.id_raw is None:
            self.shadow = bytearray(size)
        else:
            self.shadow = None

    @property
    def ids(self):
        return b64enc(self.id_raw), b64enc(self.bundle_raw), b64enc(self.block_raw)

    @property
    def ids_raw(self):
        txid_raw = self.bundle_raw if self.bundle_raw != ZEROS32 else self.id_raw
        return self.block_raw + txid_raw + self.id_raw

    @property
    def id_raw(self):
        self.flush()
        return self._id_raw

    @property
    def bundle_raw(self):
        if self._bundle_raw is None:
            # instead of graphql, this could call a method on loader that would watch for
            # bundles and parse them, as in bundlewatcher.py
            result = self.loader.graphql('''
                query {
                    transaction(id: "'''+b64enc(self._id_raw)+'''") {
                        bundledIn { id }
                        block { id }
                    }
                }''')['data']['transaction']
            if result is None:
                ar.logger.info(f'Waiting for {b64enc(self._id_raw)} to propagate ...')
                time.sleep(60)
                return self.bundle_raw
            bundledIn = result['bundledIn']
            block = result['block']
            if bundledIn is None and block is None:
                ar.logger.info(f'Waiting for {b64enc(self._id_raw)} to be mined ...')
                time.sleep(60)
                return self.bundle_raw
            if bundledIn is None:
                self._bundle_raw = ZEROS32
            else:
                self._bundle_raw = b64dec(bundledIn['id'])
            if block is None:
                self._block_raw = None
            else:
                self._block_raw = b64dec(block['id'])
        return self._bundle_raw

    @property
    def block_raw(self):
        if self._block_raw is None:
            bundle_raw = self.bundle_raw
        if self._block_raw is None:
            id_raw = self._id_raw if bundle_raw == ZEROS32 else bundle_raw
            interim_result = self.loader.graphql('''
                query {
                    transaction(id: "'''+b64enc(id_raw)+'''") {
                        block { id }
                    }
                }''')
            result = interim_result['data']['transaction']
            if result is None:
                ar.logger.info(f'Waiting for {b64enc(id_raw)} to propagate ...')
                time.sleep(60)
                return self.block_raw
            block = result['block']
            if block is None:
                ar.logger.info(f'Waiting for {b64enc(id_raw)} to be mined ...')
                time.sleep(60)
                return self.block_raw
            else:
                self._block_raw = b64dec(block['id'])
        return self._block_raw

    def __enter__(self):
        self.get()

    def __exit__(self, *params):
        self.flush()

    def __getitem__(self, index):
        offset = index * self.item_size
        return bytes(self.get()[offset : offset + self.item_size])

    def __setitem__(self, index, value):
        offset = index * self.item_size
        assert offset + self.item_size <= self.size
        assert len(value) == self.item_size
        shadow = self.get()
        if shadow[offset : offset + self.item_size] != value:
            shadow[offset : offset + self.item_size] = value
            self.dirty = True

    def __len__(self):
        return self.item_count

    def __iter__(self):
        shadow = self.get()
        for offset in range(0, self.size, self.item_size):
            yield bytes(shadow[offset : offset + self.item_size])

    def append(self, value):
        assert len(value) == self.item_size
        self.item_count += 1
        self.dirty = True
        self.shadow += value
    
    def get(self):
        if self.shadow is None:
            self.shadow = bytearray(self.loader.data(b64enc(self.id_raw), b64enc(self.bundle_raw), b64enc(self.block_raw)))
            self.size = len(self.shadow)
        return self.shadow

    def flush(self):
        if self.dirty:
            assert len(self.shadow) == self.size
            tags = [*self.tags]
            try:
                change_tag(tags, 'Application', 'HashMap', condense_to_one=False)
            except:
                pass
            try:
                change_tag(tags, 'Name', self.name, condense_to_one=False)
            except:
                pass
            change_tag(tags, 'Item-Size', str(self.item_size), condense_to_one=True)
            change_tag(tags, 'Item-Count', str(self.item_count), condense_to_one=True)
            if self._id_raw is not None:
                change_tag(tags, 'Previous-Revision', b64enc(self._id_raw), condense_to_one=True)
            if self._block_raw is not None:
                change_tag(tags, 'Previous-Revision-Block', b64enc(self._block_raw), condense_to_one=True)
            if self._bundle_raw is not None:
                change_tag(tags, 'Previous-Revision-Bundle', b64enc(self._bundle_raw), condense_to_one=True)
            assert len(self.shadow) == self.size
            id = self.loader.send(self.shadow, tags=tags)
            ar.logger.info(f'sent {id} with tags {tags}.')
            self._id_raw = b64dec(id)
            self._bundle_raw = None
            self._block_raw = None
            self.dirty = False

class WorkerPool:
    def __init__(self, action, max_jobs):
        self.action = action
        self.max_jobs = max_jobs
        self.job_semaphore = threading.BoundedSemaphore(max_jobs)
    def single_job(self, data, idx):
        data[idx] = self.action(data[idx])
        self.job_semaphore.release()
    def process(self, data):
        data = [*data]
        for idx in range(len(data)):
            self.job_semaphore.acquire() # blocks on max_jobs acquires
            threading.Thread(target=self.single_job, args=(data, idx,)).start()
        for done in range(self.max_jobs): # wait for all to complete
            self.job_semaphore.acquire()
        return data

class TableDoc:
    EMPTY = 0
    TABLE = 1
    DATA = 2
    MANY = 3

    def __init__(self, loader, txcontent_to_digits, name = 'TableDoc', size = None, item_count = None, id_raw = None, dataitem_raw = None, block_raw = None, parent = None, tags = [], type = TABLE, outer_idx = None):
        if dataitem_raw is None or dataitem_raw == id_raw:
            bundle_raw = None
        else:
            bundle_raw = id_raw
            id_raw = dataitem_raw
        self.type = type
        self.outer_idx = outer_idx
        self.txcontent_to_digits = txcontent_to_digits
        self.remote_data = BackedStructur(loader, size = size, item_count = item_count, item_size = 113, tags = tags, id_raw = id_raw, bundle_raw = bundle_raw, block_raw = block_raw, name = name)
        if parent is None:
            self.depth = 0
            self.total_height = math.ceil(
                math.log(2**256) /
                math.log(self.remote_data.item_count)
            )
        else:
            if type == self.MANY:
                self.depth = 0
            else:
                self.depth = parent.depth + 1
            self.total_height = parent.total_height
        self.obj_list = [
            (entry_raw[0], entry_raw[1:113])
            for entry_raw in self.remote_data
        ]
        self.count = sum((type != self.EMPTY for type, entry in self.obj_list))

    def get_filling_if_needed(self, hash_digit):
        entry = self.obj_list[hash_digit]
        entry_type, entry = entry
        if isinstance(entry, (bytes, bytearray)):
            assert len(entry) == 112
            if entry_type == self.EMPTY:
                entry = None
            elif entry_type == self.TABLE or entry_type == self.MANY:
                block_raw = entry[:48]
                txid_raw = entry[48:80]
                dataitem_raw = entry[80:112]
                entry = TableDoc(
                    name = f'{self.remote_data.name}-{hash_digit}' if entry_type == self.TABLE else b64enc(entry),
                    size = self.remote_data.size,
                    item_count = self.remote_data.item_count,
                    #item_size = self.remote_data.item_size,
                    dataitem_raw = dataitem_raw,
                    id_raw = txid_raw,
                    block_raw = block_raw,
                    loader = self.remote_data.loader,
                    txcontent_to_digits = self.txcontent_to_digits if entry_type is self.TABLE else self.txids_to_digits,
                    parent = self if entry_type is self.TABLE else None,
                    type = entry_type,
                    outer_idx = hash_digit
                )
            elif entry_type == self.DATA:
                block_raw = entry[:48]
                txid_raw = entry[48:80]
                dataitem_raw = entry[80:112]
                digits = self.txcontent_to_digits(dataitem_raw=dataitem_raw, txid_raw=txid_raw,block_raw=block_raw)
                if self.outer_idx is not None and self.type is self.TABLE:
                    assert digits[self.depth - 1] == self.outer_idx
                entry = (digits, (block_raw, txid_raw, dataitem_raw))
            else:
                raise StructureException('unhandled table entry type', entry_type)
            self.obj_list[hash_digit] = (entry_type, entry)
        return entry_type, entry

    #def set(self, hash_digits, block_raw, txid_raw, dataitem_raw):
    #    return self.add(hash_digits, block_raw, txid_raw, dataitem_raw, replace = True)

    def add(self, hash_digits, block_raw, txid_raw, dataitem_raw):#, replace = False):
        hash_digit = hash_digits[self.depth]
        entry_type, entry = self.get_filling_if_needed(hash_digit)
        if entry_type == self.MANY:
            # it's already a table
            # get 1 item from it, and compare the digits.
            example_digits, *example_ids = next(iter(entry))
            if example_digits == hash_digits:
                # if they are same, add this one.
                entry.add(hash_digits, block_raw, txid_raw, dataitem_raw)
            else:
                # if they differ, add a table.
                subtable = TableDoc(
                    name = f'{self.remote_data.name}-{hash_digit}',
                    loader = self.remote_data.loader,
                    txcontent_to_digits = self.txcontent_to_digits,
                    size = self.remote_data.size,
                    item_count = self.remote_data.item_count,
                    parent = self,
                    type = self.TABLE,
                    outer_idx = hash_digit,
                )
                example_digit = example_digits[subtable.depth]
                subtable.obj_list[example_digit] = (entry_type, entry) # replaced entry
                # since evaluation continues, the new entry will be added below
                #subtable.add(hash_digits, block_raw, txid_raw, dataitem_raw) # new entry
                entry = subtable
                entry_type = self.TABLE
        if entry_type == self.EMPTY:
            entry_type, entry = (self.DATA, (hash_digits, (block_raw, txid_raw, dataitem_raw)))
            self.count += 1
        elif entry_type == self.TABLE:
            entry.add(hash_digits, block_raw, txid_raw, dataitem_raw)
        elif entry_type == self.DATA:
            entry_digits, entry_ids = entry
            if entry_digits == hash_digits:
                assert entry_ids != (block_raw, txid_raw, dataitem_raw)
                entry_type = self.MANY
                parent = None
                txcontent_to_digits = self.txids_to_digits
                hash_digits = txcontent_to_digits(dataitem_raw=dataitem_raw, txid_raw=txid_raw, block_raw=block_raw)
                entry_digits = txcontent_to_digits(block_raw=entry_ids[0], txid_raw=entry_ids[1], dataitem_raw=entry_ids[2])
                name = b64enc(self.digits_to_hash_raw(hash_digits))
            else:
                entry_type = self.TABLE
                parent = self
                txcontent_to_digits = self.txcontent_to_digits
                name = f'{self.remote_data.name}-{hash_digit}'
            entry = TableDoc(
                loader = self.remote_data.loader,
                txcontent_to_digits = txcontent_to_digits,
                size = self.remote_data.size,
                item_count = self.remote_data.item_count,
                parent = parent,
                type = entry_type,
                outer_idx = hash_digit,
                name = name
            )
            entry.add(entry_digits, *entry_ids) # add back replaced entry
            entry.add(hash_digits, block_raw, txid_raw, dataitem_raw) # new entry
        else:
            raise StructureException('unhandled table entry type', entry_type)
        self.obj_list[hash_digit] = (entry_type, entry)

    def get(self, hash_digits):
        hash_digit = hash_digits[self.depth]
        entry_type, entry = self.get_filling_if_needed(hash_digit)
        if entry_type == self.EMPTY:
            return None
        elif entry_type == self.TABLE:
            return entry.get(hash_digits)
        elif entry_type == self.DATA:
            return [entry[1]]
        elif entry_type == self.MANY:
            return [*entry]
        else:
            raise StructureException('unhandled table entry type', entry_type)

    def needs_flush(self):
        if self.remote_data.dirty:
            return True
        for entry_type, entry in self.obj_list:
            if (isinstance(entry, self.__class__) or isinstance(self, entry.__class__)) and entry.needs_flush():
                return True
        return False

    def get_flush_leaves(self):
        leaves = []
        for idx, (entry_type, entry) in enumerate(self.obj_list):
            if (isinstance(entry, self.__class__) or isinstance(self, entry.__class__)):
                subleaves = entry.get_flush_leaves()
                if len(subleaves):
                    leaves.extend(subleaves)
                else:
                    # this hack sets the dirty flag if the outer document needs to update its entry for the inner document
                    subid = entry.remote_data.id_raw
                    if self.remote_data[idx][-len(subid):] != subid:
                        self.remote_data.dirty = True
            elif entry_type == self.DATA and not isinstance(entry, (bytes, bytearray)):
                self.remote_data[idx] = bytes([entry_type]) + b''.join(entry[1])
        if not len(leaves) and self.remote_data.dirty:
            leaves.append(self)
        return leaves

    def flush(self, top_down=False):
        if not top_down:
            flush_leaves = self.get_flush_leaves()
            while len(flush_leaves):
                for leaf in flush_leaves:
                    leaf.flush(top_down = True)
                flush_leaves = self.get_flush_leaves()
        else:
            if self.remote_data._id_raw is None:
                print(f'TableDoc.flush(): flushing new tabledoc with depth {self.depth}')
            else:
                print(f'TableDoc.flush(): flushing tabledoc {b64enc(self.remote_data._id_raw)} with depth {self.depth}')
            with self.remote_data:
                for idx, (entry_type, entry) in enumerate(self.obj_list):
                    if isinstance(entry, (bytes, bytearray)):
                        continue
                    if entry_type == self.EMPTY:
                        continue
                    elif entry_type in (self.TABLE, self.MANY):
                        entry = entry.raw_ids
                    elif entry_type == self.DATA:
                        entry = b''.join(entry[1])
                    self.remote_data[idx] = bytes([entry_type]) + entry

    @property
    def ids(self):
        if self.count == 0:
            return None
        self.flush()
        return self.remote_data.ids

    @property
    def raw_ids(self):
        self.flush()
        return self.remote_data.ids_raw
    
    def __getitem__(self, hash):
        digits = self.hash_to_digits(hash)
        result = self.get(digits)
        return result

    def __setitem__(self, hash, tuple):
        block, txid, dataitem = tuple
        block_raw = b64dec_if_not_bytes(block)
        txid_raw = b64dec_if_not_bytes(txid)
        dataitem_raw = b64dec_if_not_bytes(dataitem)
        digits = self.hash_to_digits(hash)
        self.add(digits, block_raw, txid_raw, dataitem_raw)

    def __iter__(self):
        
        for idx, (entry_type, entry) in enumerate(self.obj_list):
            if entry_type == self.DATA:
                digits, (block_raw, txid_raw, dataitem_raw) = self.get_filling_if_needed(idx)[1]
                assert digits[self.depth] == idx
                # this is already how the digits are generated
                #assert digits == self.txcontent_to_digits(block_raw=block_raw, txid_raw=txid_raw, dataitem_raw=dataitem_raw)
                yield digits, (block_raw, txid_raw, dataitem_raw)
        for idx, (entry_type, entry) in enumerate(self.obj_list):
            if entry_type is self.TABLE:
                yield from self.get_filling_if_needed(idx)[1]
            elif entry_type is self.MANY:
                digits = None
                count = 0
                for _, (block_raw, txid_raw, dataitem_raw) in self.get_filling_if_needed(idx)[1]:
                    if digits is None:
                        digits = self.txcontent_to_digits(dataitem_raw=dataitem_raw, txid_raw=txid_raw, block_raw=block_raw)
                    count += 1
                    yield digits, (block_raw, txid_raw, dataitem_raw)
                assert count > 1
            #if entry_type in (self.TABLE, self.MANY):
            #    yield from self.get_filling_if_needed(idx)[1]

    def __enter__(self):
        return self
    def __exit__(self, *params):
        self.flush()

    def hash_to_digits(self, hash):
        digits = []
        hash_raw = b64dec_if_not_bytes(hash)
        hash_int = int.from_bytes(hash_raw, 'little')
        base = self.remote_data.item_count
        for idx in range(self.total_height):
            hash_int, digit = divmod(hash_int, self.remote_data.item_count)
            digits.append(digit)
        return digits

    def digits_to_hash_raw(self, digits):
        hash_int = 0
        for digit in digits[::-1]:
            hash_int = hash_int * self.remote_data.item_count + digit
        hash_raw = hash_int.to_bytes(32, 'little')
        return hash_raw

    def txids_to_digits(self, dataitem_raw, txid_raw, block_raw):
        hash = hashlib.sha256(dataitem_raw + txid_raw + block_raw)
        hash = hash.digest()
        return self.hash_to_digits(hash)

class HashMap(TableDoc):
    def __init__(self, txcontent_to_digits, size, id = None, block = None, dataitem = None, loader = None, tags = {}):
        if loader is None:
            loader = ar.Peer()
        id_raw = b64dec_if_not_bytes(id)
        block_raw = b64dec_if_not_bytes(block)
        dataitem_raw = b64dec_if_not_bytes(dataitem)
        super().__init__(txcontent_to_digits, size = size, item_count = None, id_raw = id_raw, block_raw = block_raw, dataitem_raw = dataitem_raw, loader = loader)

from ar.utils.merkle import compute_root_hash, generate_transaction_chunks
def reupload(peer, tx):
    data = peer.data(tx)

    chunks = generate_transaction_chunks(io.BytesIO(data))
    offset = 0
    for proof, chunk in zip(chunks['proofs'], chunks['chunks']):
        chunk_size = chunk.data_size
        chunk = {
            'data_root': b64enc(chunks['data_root']).decode(),
            'data_size': str(len(data)),
            'data_path': b64enc(proof.proof),
            'offset': str(proof.offset),
            'chunk': b64enc(data[offset:offset+chunk_size])
        }
        peer.send_chunk(chunk)
        offset+=chunk_size


from ar import ANS104BundleHeader
class BundleIndexer:
    def __init__(self, loader, filename, id = None, bundle = None, block = None, start_block = 761917, size = 100000):
        self.filename = filename
        if os.path.exists(filename):
            with open(filename) as file:
                metadata = json.load(file)
            id = metadata['id']
            bundle = metadata['bundle']
            block =metadata['block']
        if id is not None:
            id_raw = b64dec_if_not_bytes(id)
            tags = [tag for tag in loader.tags(id, bundle, block) if tag['name'] not in (b'Application', b'Previous-Revision', b'Previous-Revision-Block', b'Previous-Revision-Bundle')]
            tagsblockmin = get_tags(tags, 'Block-Min')
            tagsblockmax = get_tags(tags, 'Block-Max')
            if tagsblockmin:
                self.prev_block = min((int(i) for i in tagsblockmin)) - 1
                if tagsblockmax:
                    self.next_block = max((int(i) for i in tagsblockmax)) + 1
                else:
                    self.next_block = self.prev_block + 2
            elif tagsblockmax:
                self.next_block = max((int(i) for i in tagsblockmax)) + 1
                self.prev_block = self.next_block - 2
            else:
                self.prev_block = start_block
                self.next_block = start_block
            #tags = [tag for tag in tags if tag['name'] not in (b'Block-Min', b'Block-Max')]
            if not get_tags(tags, b'Block-Min'):
                ensure_tag(tags, b'Block-Min', str(start_block))
        else:
            id_raw = None
            tags = [
                create_tag('Block-Min', str(start_block), True),
                create_tag('Block-Max', str(start_block), True)
            ]
            self.prev_block = start_block
            self.next_block = start_block
        self.root = TableDoc(loader, self.txcontent_to_digits, size=size, id_raw = id_raw, tags = tags, name = 'DataItems')
    def txcontent_to_digits(self, dataitem_raw, txid_raw, block_raw):
        #self.remote_data.add()
        return self.root.hash_to_digits(dataitem_raw)
    def add_forward(self):
            loader = self.root.remote_data.loader
        #with self.root:
            try:
                block_bytes = loader.block2_height(self.next_block, b'\xff'*125)
            except ar.ArweaveNetworkException:
                block_bytes = loader.block2(self.next_block)
                ar.logger.warning('Peer does not support HTTP GET body data. Try a different peer for faster block processing.')
            block = ar.Block.frombytes(block_bytes)
            ar.logger.info(f'Reading block {self.next_block}: {block.indep_hash}')

            # fetch missing tx tags
            txs_tags = WorkerPool(
                action = lambda tx: tx.tags if type(tx) is ar.Transaction else loader.tags(tx),
                max_jobs = 10, # default requests urllib3 connection pool size
            ).process(block.txs)

            for tx_tags, tx in zip(txs_tags, block.txs):
                if not get_tags(tx_tags, b'Bundle-Format'):
                    continue
                try:
                    header = ANS104BundleHeader.from_tags_stream(tx_tags, loader.stream(tx))
                except ar.ArweaveNetworkException:
                    ensure_tag(self.root.remote_data.tags, b'Block-Missing-Data', block.indep_hash)
                    continue
                #if header is None:
                #    continue
                for bundled_id in header.length_by_id.keys():
                    self.root[bundled_id] = (block.indep_hash, tx, bundled_id)
            change_tag(self.root.remote_data.tags, 'Block-Max', str(self.next_block), condense_to_one=True)
            self.next_block += 1
    def save(self):
        id, bundle, block = self.root.ids
        with open(self.filename + '.new', 'wt') as file:
            json.dump({
                'id': id,
                'bundle': bundle,
                'block': block
            }, file)
        os.rename(self.filename + '.new', self.filename)
    def __del__(self):
        self.root.flush()

#class TableDoc(BackedStructure):
#        super().__init__(size = size, item_count = item_count, item_size = 33, id_raw = id_raw, loader = loader)
#        self.
#    def __getitem__(self, idx):
#        item = super().__getitem__(idx)
#        return item[-1], item[:-1]
#    def __setitem__(self, idx, data_and_type):
#        data, type = data_and_type
#        super().__setitem__(idx, data + bytes([type]))
#
#class HashMap:
#    def __init__(self, document_size, id = None, loader = None):
#        if loader is None:
#            loader = ar.Peer()
#        self.id_raw = utfdec_if_not_bytes(id)
#        self.root = TableDoc(size = document_size, id_raw = self.id_raw, loader = loader)
#    
#
##class Array:
##    def __init__(self, entry_size, max_doc_size, id_raw = None):
##        self.entry_size = entry_size
##        self.max_doc_size = max_doc_size
##    def
##
##class Index:
##    def __init__(self, max_doc_size, entry_size, id_raw = None, bytes = None):
##        self.entry_size = entry_size
##        self.max_doc_size = document_size
##        self.id_raw = id_raw
##        self.bytes = bytes
##
##    def 
#class HashIndex(BackedStructur):
#    def __init__(self, max_doc_size, id_raw = None, item_size = 32, type_size = 1, byteorder = 'big'):
#        self.type_Size = type_size
#        super().__init__(size = max_doc_size, item_size = (item_size+type_size), id_raw = id_raw)
#        self.byteorder = byteorder
#    def reduce_hash(self, hash_raw):
#        hash_int = int.from_bytes(hash_raw, self.byteorder)
#        smaller_hash, idx = divmod(hash_int, self.item_count)
#        return idx, smaller_hash
#    def get_item_type(self, hash_raw):
#        entry = self[idx]
#        return entry[:-self.type_size], int.frombytes(entry[-self.type_size:])
#    def put(self, hash_raw):
#        self[idx] = hash_raw
#        
#        
#
#class Index
#    ENTRYSIZE = 32
#
#    TYPE_INDEX = 0 # list of typed documents in a tree
#    TYPE_DATA = 1 # a single reference to data
#    #TYPE_DOCINDEX = 2 # 
#    #TYPE_SHORTLIST = 3
#    #TYPE_SHORTMAP = 4
#
#    zero_entry_raw = bytes(ENTRYSIZE)
#
#    def __init__(self, indexid = None, loader = None, index_size = 100000, reverse = False):#, large_list = False):
#        self.loader = loader if loader is not None else ar.Peer()
#        self.ids_per_index = index_size // (self.ENTRYSIZE + 1)
#        self.ids_per_shortmap = index_size // (self.ENTRYSIZE * 2)
#        self.id_raw = (
#            b64dec_if_not_bytes(indexid) if indexid is not None else self.zero_entry_raw
#        )
#        self.byteorder = 'little' if reverse else 'big'
#        #self.large_list = large_list
#
#    @property
#    def index_size()
#        return self.ids_per_index * (self.ENTRYSIZE + 1)
#
#    def hash_raw_to_ids(self, recordhash):
#        #recordhash = utf8enc_if_not_bytes(recordhash)
#        recordid = int.from_bytes(recordhash, byteorder=self.byteorder)
#        digits = []
#        while recordid:
#            number, digit = divmod(number, self.ids_per_index - 1)
#            digits.append(digit + 1)
#        digits.append(0)
#        return digits
#
#    #def ids_to_name(self, recordids):
#    #    if recordids[-1] = 0:
#    #        recordids = recordids[:-1]
#    #    recordid = 0
#    #    length = len(ids)
#    #    while len(ids):
#    #        id = ids.pop()
#    #        recordid = recordid * (self.ids_per_per_index - 1) + (id  - 1)
#    #    recordname = int.to_bytes(recordid, length, self.byteorder)
#    #    return recordname
#
#    def create_single_valued_index(self, record_id, raw_entry, type):
#        index = bytearray(self.index_size)
#        offset = record_id * (self.ENTRYSIZE + 1)
#        index[offset : offset + self.ENTRYSIZE] = entry_raw
#        index[offset + self.ENTRYSIZE] = entry_type
#        return self.loader.send(index)
#
#    def create_index(self, recordids_value_raw_entry_raw_type_tuples):
#        plan = {}
#        for recordids, value_raw, entry_raw, type) in recordids_value_entry_raw_type_tuples:
#            recordid = recordids[0]
#            entry = plan.setdefault(recordid, [])
#            entry.append((
#                recordids[1:], value_raw, entry_raw, type
#            ))
#        for recordid, entries in plan.items():
#            needs_expansion = len(entries) > self.ids_per_shortmap:
#            if not needs_expansion and len(entries) > 1:
#                for recordids, entry_raw, type in entries: # could this get too large?
#                    if type != self.TYPE_DOCID:
#                        needs_expansion = True
#                        break
#            if needs_expansion:
#                entry_raw = self.create_index(entries))
#                type = self.TYPE_DOCINDEX
#            elif len(entries) > 1:
#                entry_raw = self.create_shortmap(
#                type = self.TYPE_
#    #    index = bytearray(self.index_size)
#    #    for recordids, (entry_raw, type) in raw_entries_and_type_by_recordid:
#    #        offset = recordid * (self.ENTRYSIZE + 1)
#    #        index[offset : offset + self.ENTRYSIZE] = entry_raw
#    #        index[offset + self.ENTRYSIZE] = entry_type
#    #    return self.loader.send(index)
#
#    def read_index_for(self, indexid_raw, recordid):
#        with self.loader.stream(indexid_raw) as stream:
#            stream.seek(recordid * (self.ENTRYSIZE+1))
#            next_entry_raw = stream.read(self.ENTRYSIZE)
#            next_type = strem.read(1)[0]
#        return next_type, next_try_raw
#
#    def add_to_index(self, indexbytes, record
#
#    def read_list(self, indexid_raw, index_type, hash_raw = None):
#        if index_type == self.TYPE_DOCINDEX:
#            yield from Index(indexid_raw, self.loader, self.index_size)
#        #elif index_type == self.TYPE_SHORTLIST:
#        #    with self.loader.stream(indexid_raw) as stream:
#        #        while True:
#        #            id_raw = stream.read(self.ENTRYSIZE)
#        #            if not id_raw:
#        #                break
#        #            yield b64enc(id_raw)
#        elif index_type = self.TYPE_SHORTMAP:
#            with self.loader.stream(indexid_raw) as stream:
#                while True:
#                    key_raw = stream.read(self.ENTRYSIZE)
#                    if not key_raw:
#                        break
#                    value_raw = stream.read(self.ENTRYSIZE)
#                    if hash_raw is None or key_raw == hash_raw:
#                        yield b64enc(value_raw)
#        else:
#            raise StructureError('index type is not a list', indexid_raw, index_type)
#
#    #def read_index_for(self, indexid_raw, recordid):
#    #    with self.loader.stream(indexid_raw) as stream:
#    #        indextype = stream.read(1)[0]
#    #        if indextype == self.TYPE_DOCINDEX:
#    #            if indexid_raw != self.id_raw:
#    #                data = None
#    #                break
#    #            else:
#    #                indextype = self.TYPE_NAMEINDEX
#
#    #        if indextype == self.TYPE_NAMEINDEX:
#    #            stream.seek(1 + recordid * self.ENTRYSIZE)
#    #            data = stream.read(self.ENTRYSIZE)
#
#    #        elif indextype = self.TYPE_SHORTLIST:
#    #            data = []
#    #            while True:
#    #                entry_raw = stream.read(self.ENTRYSIZE)
#    #                if not entry_raw:
#    #                    break
#    #                data.append(entry_raw)
#    #            data = [stream.read(self.ENTRYSIZE) for x in range(self.ids_per_index)]
#
#    #        else:
#    #            raise StructureError('unrecognized index type', b64enc(indexid_raw), indextype)
#    #    return indextype, data
#
#    def insert(self, recordhash, id):
#        recordhash_raw = utf8enc_if_not_bytes(recordhash)
#        recordids = self.hash_raw_to_ids(recordhash_raw)
#        id_raw = utf8enc_if_not_Bytes(id)
#
#        if self.id_raw == self.zero_entry_raw:
#            # make first index and first shortmap
#            first_shortmap = recordhash_raw + id_raw
#            first_shortmap_txid = self.loader.send(first_shortmap)
#            first_index = bytearray(self.index_size)
#            first_index[recordids[0] * 
#            
#        parents = []
#        indexid_raw = self.id_raw
#
#        if indexid_raw == self.zero_entry_raw:
#            # insert here
#        # when inserting, it helps ot have the recordhash
#
#        # when inserting, basically we search for it, getting back helpful data.
#
#    def find(self, recordhash):
#        recordhash_raw = utf8enc_if_not_bytes(recordhash)
#        recordids = self.hash_raw_to_ids(recordhash_raw)
#        indexid_raw = self.id_raw
#        index_type = self.TYPE_NAMEINDEX
#
#        for depth, recordid in enumerate(recordids):
#            if indexid_raw == self.zero_entry_raw:
#                return []
#            index_type, indexid_raw = self.read_index_for(indexid_raw, recordid)
#            if index_type != self.TYPE_NAMEINDEX:
#                # when ending early, it simply means the hash is unique now
#                break
#
#        if index_type == self.TYPE_NAMEINDEX:
#            raise StructureError('record hash did not end with record list')
#
#        yield from self.read_list(indexid_raw, index_type)
#
#        #if indextype == self.TYPE_SHORTLIST:
#        #    yield from (b64enc(record_raw) for record_raw in records_raw)
#
#        #elif indexType == self.TYPE_DOCINDEX:
#        #    yield from Index(indexid, self.peer, self.index_size)
#
#        #elif indextype == self.TYPE_NAMEINDEX:
#        #    raise StructureError('record hash did not end with record list')
#
#        #else:
#        #    raise StructureError('unhandled index type', b64enc(indexid_raw), indextype)
#
#    def __iter__(self):
#        indexid_raw = self.id_raw
#        if indexid == self.zeros_bytes
#            return
#        indexid = b64enc(indexid_raw)
#
#        with self.peer.stream(indexid) as stream:
#            entry_raw = stream.read(self.ENTRYSIZE)
#            if entry_raw != self.zeros_bytes:
#                yield b64enc(entry_raw)
#            while True:
#                entryid_raw = stream.read(self.ENTRYSIZE)
#                yield from self.__class__(entryid_raw, peer = self.peer, index_size = self.index_size, byteorder = self.byteorder)
#            
#            
#
#    def insert(self, recordhash, entry):
#        # make a new tree
#        
#        # we can reverse recordhash, convert it to an int, and process it in base ids_per_index
#        recordhash = utf8enc_if_not_bytes(recordhash)
#        recordid = int.from_bytes(recordhash, byteorder='little')
#        indexids = number_to_digits(recordid)
#        
#        index = self.id_raw
#        
#        for depth, indexid in enumerate(indexids)
#            if index is None:
#                index = bytearray(self.index_size)
#            index[self.entrysize * indexids


def makedefault():
    ar.logging.basicConfig(level=ar.logging.INFO)
    from bundlr import Node
    from bundlr.loader import Loader
    from ar import Peer, Wallet
    wallet = {
        "alg": "RS256",
        "kty": "RSA",
        "n": "zEiPuKuOPAloc9Bzi0LCaVxcgO7aWrcvPKfRUeWfeAHADZfyWvcHyjU89LFK4mbBxbf7e0foKftKU32E5kWrvpBoBjosaIwsCPJ0_RY1U2fH7UXFQkKaP3N09vtR729iCZh71sX-lsDb5J5krjpPgb0wFLQiXxdhuFDglJwDgml3k2s90BmM2YinBBE2RKecVHi6B8s4cfl9QuTN4XbqLdFJRz22bxELD1Fqko6qTAjfKymV9ZC8F7IxHG_Db_S1mk5RMZU7BvJfxXLh1pHav_pAqiQtAsxu4ZauxBWfYObdoZFeVoE90Q14Rc1_VvKexoqzh-QV4Z51G9D5k0S2mXOs0LgdValQeDWzLIvbRQX7hEJqZmHEYMZM1hJCZGNkdit0H2zYoSMlCUQruWhgD9kGJG-lcKW1U0a5N-7GoQM_hlrPYP4i0_x2RNhIn370Dl5Pofttok7XZEGLCQf8IZuSQWvSZqrurEPIK-DdFf7piGJI4kYAtfqMr11rZfPOOeFCtmtyomkwSGOckuq2Kiieco1qWXBrYq5QgnmUiZZijJ1Tt2Gwxlltnd8yKF-mCDdtZRObpmRoOfPUdq7-i-yglgoWA41cl0kZNwfrWKE8jLdv5nmuDZJqglagtTtIgScOvoTg8v0SLaAiB35i20tSqAQVoa45TbBMgFemnrE",
        "e": "AQAB",
        "d": "GBWl_DEdv9j2xlDD4_NRqyJcivGeL3vRceacjc9IvIQC-eykLN1bFG1aa8RLU-NRjSy31ZJmE4JbrPmWJZ_-iPp1iTu_6JjoyCqYaGOp6H91LsrptXosvWEGCpMZgeUxOyMN1rCD54-CsrLfTpCetxPFthXWx5H2JMju8WvDbiizvwmxwUssiVPMfR-aX6sd30eshya1LPAr4yseqtUI9FtBtx3WLcS7TRRdlZHZuhqBqpETQQnODe0lpSNNeMbycj2G4mr5s-6iI_amHFTDOZxuQKEAkt06EBa33B5rKqg4ER3BGunPOUp2l6Q2vdrfpVYiUdnY9T9oBzOII-Nss6IbM4zbz_4L3y62y_4q2uRwVOPNuW8o3dJyCBMyZq8BS7f0qIM8MuZeSO30foQlp27Yh0YOJTy3JwcbQj6d-EAjDHi6ZeyIU5Pyyap7pisFSirEyR__EBbXfZ417MBg6FBPLvfMAQLXPv8EU3r8VWAnsmthmJ0Pt5Ar_7Ypng701Bv1a1PY294K6V-gufTJpnXJB_ZORY6Ccaor9RHg_DvMqWak1VA1Yp6OoMO9Oa3udGcLUopsxa8stLrl9H_Gc0ya7f6IGQ2TtgYkV4v8N_5DAFQYh1ato_6kX9-VmmOS32w0HX4f1ULDV5MVAaduqbM5u4BNrU3ynfYRlBVkl9E",
        "p": "1VITXO-tCfYh0JUvCA3qKNOzvgjAavvPRlSVRORTdEDdQjr3BKmOvcqhs1wGhMeJ5vOUggaKOa01KgtCj__JDm48cf91TNXpQjC5zbKpgEwJFOfnbpi1ZROv2V95rfua6RRaLAxCZpTWz0ye3PzxiPC29cn-a1wS8HacPNmiWJDRkmdN6IrpDhBpr1fUzq6Pm3QVk2FWXYZ_lE1wibIDd-y7HtDaNXz4Du5zU19-ahbIvDTMC3uqp2aWLKl1jJkOIoa4feiunXNHtStLl-73ahM171jcGhKQ-ec5fiDxZCH3vokB-Aj7TXw1x68x8FKQH8QlU4_toNfI0SaOpUhtgw",
        "q": "9SeeCIvQUb14z49YOG6P8VNT-v7rBqef7I8pyjy9QymadbwUfLPAAs0nJircynQ5ddnQbY01fZnRkYmlLDt2K09Nfr0ld0-m89fM9Du7X4IUCiK6s29zRxQAYKGWpxQSvTL157iY13LSHGsI3QG_lz7AclONtg3uijYP3_v0tgwjUrzzUInQt6AWi_-v7EnZNjMj96n-dCAfEn4UyrV7lD98enYZN6_kEloUsGD_Bqa3aenHiQ2ljXtvqdWh1WNmzhdkz26X8NuhJ1rNQR90yqeCGqBnCW6D62tB__GKjKDCx4QiWIobB26S9J0WFODa8dZiBSstddwcSMnPXKTguw",
        "dp": "BmVgmT_Cc3MCzos6jsZECBdY41DF3C9SpqwwkZE7A1hSigLUlzoyQnSJ5qPSujZ1ZwxUnpVtnY8Y8frGcyTbNWiOvWhIbxZW2Ro25_j8ZhFhkFPnt4QypCYz9pOLRXEu0uA-V-XCM-swiaSlesDGyTFWewYkb7miA726r4Ri_r7Q2c_pIRjRJg_N62j5w3yuZ53Sa8nWWhWHS74KqsZAnl7luWXPtRzbHy99G7nYQ3wNZr86gvmhQ0WrKQmnsaCBMP3TGEtauPPU6ZSzvol2t6J90oBakRmPaT7KlYKNWlA-amMXQQWb61XXEvaoy6jeE2XBLME7AcCWj9bVHhWO2w",
        "dq": "HbhMz0pr2cz3fWoqTsUQjDgG4VHQGkFuANamQU81vpOnlwhTD38XEv_d9CGUHLMUWDYsr2tEBdME9fjS3lbjD4MQqQGzLhCo87zAqwcmwwBY_5WQPrqPJhnFpfFQ-zZSwz8PUqUtWkkgMbPEIk7Y9DP2TqXUczKjLXw6VnQMCZnVGm2vrZ7Xf7tXoGdB44pcW9a9UIP6Rgey3KIOUTjJH4LGy23PxtF6-8KR6YQIxrylVaCywOm3nTxOoC827FCdoPRzEzacEuX9VnEKmw9-MCc4fZPeieUs9vhMywN0QXInyto487Tia_c6t47no2ZTBKhxv6CpZTVm9GgKzHdsiw",
        "qi": "SU5Gcmtyz39P0pVfMWYCaVvW43w8hoDPRFjrgPnv6LYtXxOKDNchBP0s7gtysdwqSKT23bxrkRyPQ1rFexzOGfbwelSVFC47JbmCrXLqUkGrSKlZHtpifldWfcxiEeuTyZQ2DB5gQMlyh9Ynh8SsLcmhuUW8A7sI1RMGZfj4prR0PitQophRJ2VJSKOtTv_PHMrfYmM3gvVeCf7LaxJdY4qetkW9R9q7wGCFBNq75OOBBiqI5uEuhzU2YaOoAGyPsj-GRxnsT6q94B32mb459d5EMn4yf0sz-E9G7fj2_yQaslxGKmrmy9msQbNiBcBjl7qvEumxYpaZ-MfPcvA7aw",
        "p2s": ""
    }
    wallet = Wallet.from_data(wallet)
    node = Node()
    peer = Peer(Peer('https://arweave.net').health()['origins'][-1]['endpoint'])#ar.multipeer.MultiPeer()
    #peer = Peer('http://gateway-3.arweave.net:1984')
    gateway = Peer('https://arweave.net')
    #peer = gateway
    loader = Loader(node, gateway, peer, wallet)
    indexer = BundleIndexer(loader, 'arweave-index.json')
    return indexer

if __name__ == '__main__':
    #import pdb; pdb.set_trace()
    indexer = makedefault()
    #for item in indexer.root:
    #    print(item)
    then = time.time()
    while True:
        indexer.add_forward()
        #for item in indexer.root:
        #    print(item)
        now = time.time()
        #if True:
        if now - then > 60*60*5:
            then = now
            indexer.save()
            print(indexer.root.ids)
            #break
