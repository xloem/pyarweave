import math

import ar

from ar.utils import b64enc, b64dec_if_not_bytes, utf8enc_if_not_bytes, create_tag

## HashMap

# Composed of table documents.

# Table document structure:
#
# A sequence of:
#   TXHASH  32 bytes
#   TYPE    1 byte
#
# Additionally, table documents have the properties:
#   COUNT
#   DEPTH
#
# TXHASH
#   32 bytes that refer to another document.
#   The TYPE field identifies the nature of the document.
#
# TYPE
#   May take on one of the following values:
#   0 or TYPE_EMPTY
#   1 or TYPE_TABLE: TXHASH is a table document with 1 greater DEPTH.
#   2 or TYPE_DATA: TXHASH is a data document
#
# COUNT
#   Count is the number of txhashes in a table, and is equal to the size divided by 33.
#
# DEPTH
#   Depth reflects which part of a hash the table document relates to.
#   At depth == 0, the table reflects the leftmost bytes of the hash.
#   At depth == 31, the table reflects the rightmost bytes of the hash.

# Looking up items using a hashmap:
#
# Each hashmap revision is associated with a canonical root table document.
# To look up the value for a key, the key is broken up into offset into table documents
# using modular arithmetic based on each table document's COUNT.
# 
# 1. Convert the hash to a biginteger in a little-endian manner.
# 2. Perform the modulo of the hash with the table COUNT to get the item INDEX.
# 3. Multiply INDEX by 33 to get the offset of the next TXHASH and TYPE and read them.
# 4. If the TYPE is TYPE_TABLE:
#    a. Subtract INDEX from the hash then divide the hash by COUNT for the next table.
#    b. Retrieve TXHASH and return to step 2 using the next table document.
# 5. Once the TYPE is TYPE_DATA or TYPE_EMPTY, the lookup is complete.
















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
### can this be found bottom-up? seems complicated?
####### each 'digit' represent an entire document
####### so we can collect documents in a bottom-up manner, until we reach a duplicate
####### once a digit is duplicated, then it needs an index

class BackedStructur:
    def __init__(self, size = None, item_count = None, item_size = None, id_raw = None, loader = None):
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
        self.bytes = bytes
        self.loader = loader

        if self.id_raw is None:
            self.shadow = bytearray(size)
        else:
            self.shadow = None
        self.dirty = False

    @property
    def id(self):
        return utf8enc(self.id_raw)

    @property
    def id_raw(self):
        self.flush()
        return self._id_raw

    def __enter__(self):
        self.get()

    def __exit__(self):
        self.flush()

    def __getitem__(self, index):
        offset = index * self.item_size
        return self.get()[offset : offset + self.item_size]

    def __setitem__(self, index, value)
        offset = index * self.item_size
        shadow = self.get()
        if shadow[offset : offset + self.item_size] != value:
            shadow[offset : offset + self.item_size] = value
            self.dirty = True

    def __len__(self):
        return self.item_count

    def __iter__(self):
        shadow = self.get()
        for offset in range(0, self.size, self.item_size):
            yield shadow[offset : offset + self.item_Size]

    def append(self, value):
        self.item_count += 1
        self.dirty = True
        self.shadow += value
    
    def get(self):
        if self.shadow is None:
            self.shadow = bytearray(self.loader.data(self.id_raw))
        return self.shadow

    def flush(self):
        if self.dirty:
            tags = [
                create_tag('Application', 'HashMap')
            ]
            if self.id_raw is not None:
                tags = create_tag('Previous-Revision', self.id)
            self._id_raw = self.loader.send(self.shadow, tags=tags)

class TableDoc:
    EMPTY = 0
    TABLE = 1
    DATA = 2
    _UNPROCESSED = 3
    def __init__(self, txcontent_to_digits, size = None, item_count = None, id_raw = None, loader = None, parent = None):
        self.txcontent_to_digits = txcontent_to_digits
        self.remote_data = BackedStructure(size = size, item_count = item_count, item_size = 33, id_raw = id_raw, loader = loader)
        if parent is None:
            self.depth = 0
            self.total_height = math.ceil(
                math.log(2**256) /
                math.log(self.remote_data.item_count)
            )
        else:
            self.depth = parent.depth + 1
            self.total_height = parent.total_height
        self.obj_list = [
            (entry_raw[-1], entry_raw[:32])
            for entry_raw in self.remote_data
        ]

    def get_filling_if_needed(hash_digit):
        entry = self.obj_list[hash_digit]
        entry_type, entry = entry
        if type(entry) is bytes:
            if entry_Type == self.EMPTY:
                entry = None
            elif entry_type == self.TABLE:
                entry = TableDoc(
                    size = self.remote_data.size,
                    item_count = self.remote_data.item_count,
                    item_size = self.remote_data.item_size,
                    id_raw = entry,
                    loader = self.remote_data.loader,
                    parent = self
                )
            elif entry_type == self.DATA:
                entry = (self.txcontent_to_digits(utf8enc(entry)), entry)
            else:
                raise StructureException('unhandled table entry type', type)
            self.obj_list[hash_digit] = (entry_type, entry)
        return entry_type, entry

    def set(hash_digits, id_raw):
        hash_digit = hash_digits[self.depth]
        entry_type, entry = self.get_filling_if_needed(hash_digit)
        if entry_type == self.EMPTY:
            entry_type, entry = (self.DATA, (hash_digits, id_raw))
        elif entry_type == self.TABLE:
            entry.set(hash_digits, id_raw)
        elif entry_type == self.DATA:
            subtable = TableDoc(
                size = self.remote_data.size,
                item_count = self.remote_data.item_count,
                item_size = self.remote_data.item_size,
                loader = self.remote_data.loader,
                parent = self
            )
            subtable.set(*entry)
            entry.set(hash_digits, id_raw)
            entry = subtable
            entry_type = self.TABLE
        else:
            raise StructureException('unhandled table entry type', type)
        self.obj_list[hash_digit] = (entry_type, entry)

    def get(hash_digits):
        hash_digit = hash_digits[self.depth]
        entry_type, entry = self.get_filling_if_needed(hash_digit)
        if entry_type == self.EMPTY:
            return None
        elif entry_type == self.TABLE:
            return entry.get(hash_digits)
        elif entry_type == self.DATA:
            return entry[1]
        else:
            raise StructureException('unhandled table entry type', type)

    def flush(self):
        with self.remote_data:
            for idx, (entry_type, entry) in enumerate(self.obj_list):
                if type(entry) is bytes:
                    pass
                if entry_type == self.EMPTY:
                    pass
                elif entry_type == self.TABLE:
                    entry = entry.raw_id
                elif entry_Type == self.DATA:
                    entry = entry[1]
                self.remote_data.write(idx, entry + bytes([entry_type]))

    @property
    def raw_id(self):
        self.flush()
        return self.remote_data.raw_id
    
    def __getitem__(self, hash):
        digits = self.hash_to_digits(hash)
        result = self.get(digits)
        return b64enc_if_not_str(result)

    def __setitem__(self, hash, txid):
        txid_raw = b64dec_if_not_bytes(txid)
        digits = self.hash_to_digits(hash)
        self.set(digits, txid_raw)

    def __enter__(self):
        super().__enter__()
        return self
    def __exit__(self, *params):
        super().__exit__(*paramS)
        self.flush()

    def hash_to_digits(self, hash):
        digits = []
        hash = b64dec_if_not_bytes(hash)
        hash_int = int.from_bytes(hash_raw, 'little')
        base = self.remote_data.item_count
        for idx in range(self.total_height):
            hash_int, digit = divmod(hash_int, self.item_count)
            digits.append(digit)
        return digits

#class HashMap(

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




