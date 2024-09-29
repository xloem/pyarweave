import fractions
import io
from ar.utils import (
    erlintenc, arbinenc, arintenc,
    erlintdec, arbindec, arintdec,
    int_if_not_none,
    b64enc_if_not_str, b64dec_if_not_bytes,
    b64enc, b64dec, AutoRaw
)
from ar.utils.deep_hash import deep_hash
from .chunk import Chunk
from .transaction import Transaction
from . import (
    FORK_1_6, FORK_1_8,
    FORK_2_4, FORK_2_5, FORK_2_6, FORK_2_7, FORK_2_8
)
from . import INITIAL_VDF_DIFFICULTY

# STATUS
# MINING IS NOT PLANNED AT THIS TIME
# FORK      FROMBYTES   TOBYTES     FROMJSON    TOJSON      VALIDATION  MINING
# gen       [X]         [X]         [X]         [X]         unstarted   unstarted
# 1.8       [X]         [X]         [X]         [X]         unstarted   unstarted
# 2.0       [X]         [X]         [X]         [X]         unstarted   unstarted
# 2.4       [X]         [X]         [X]         [X]         unstarted   unstarted
# 2.5       [X]         [X]         [X]         [X]         notes       unstarted
# 2.6       [X]         [X]         [X]         [X]         unstarted   unstarted
# 2.6.8     drafted     drafted     [ ]         [ ]         unstarted   unstarted
# 2.7       drafted     drafted     [ ]         [ ]         unstarted   unstarted
# 2.7.1     drafted     drafted     [ ]         [ ]         unstarted   unstarted
# 2.8       drafted     drafted     [ ]         [ ]         unstarted   unstarted

TIMESTAMP_FIELD_SIZE_LIMIT = 12

class Block(AutoRaw):
    '''
        github.com/arweave
        apps/arweave/include/ar.hrl
        revision: N.2.7.4-22-g36dff9e2
        non-gossipped fields are not included in this class

%% @doc A block (txs is a list of tx records) or a block shadow (txs is a list of
%% transaction identifiers).
-record(block, {
	%% The nonce chosen to solve the mining problem.
	nonce,
	%% `indep_hash` of the previous block in the weave.
	previous_block = <<>>,
	%% POSIX time of block discovery.
	timestamp,
	%% POSIX time of the last difficulty retarget.
	last_retarget,
	%% Mining difficulty, the number `hash` must be greater than.
	diff,
	height = 0,
	%% Mining solution hash.
	hash = <<>>,
	%% The block identifier.
	indep_hash,
	%% The list of transaction identifiers or transactions (tx records).
	txs = [],
	%% The Merkle root of the tree of Merkle roots of block's transactions' data.
	tx_root = <<>>,
	%% The Merkle tree of Merkle roots of block's transactions' data. Used internally,
	%% not gossiped.
	tx_tree = [],
	%% Deprecated. Not used, not gossiped.
	hash_list = unset,
	%% The Merkle root of the block index - the list of
	%% {`indep_hash`, `weave_size`, `tx_root`} triplets describing the past blocks
	%% excluding this one.
	hash_list_merkle = <<>>,
	%% The root hash of the Merkle Patricia Tree containing all wallet (account) balances and
	%% the identifiers of the last transactions posted by them, if any
	wallet_list,
	%% The mining address. Before the fork 2.6, either the atom 'unclaimed' or
	%% a SHA2-256 hash of the RSA PSS public key. In 2.6, 'unclaimed' is not supported.
    reward_addr = unclaimed,
	%% Miner-specified tags (a list of strings) to store with the block.
    tags = [],
	%% The number of Winston in the endowment pool.
	reward_pool,
	%% The total number of bytes whose storage is incentivized.
	weave_size,
	%% The total number of bytes added to the storage incentivization by this block.
	block_size,
	%% The sum of the average number of hashes computed by the network to produce the past
	%% blocks including this one.
	cumulative_diff,
	%% The list of {{`tx_id`, `data_root`}, `offset`} pairs. Used internally, not gossiped.
	size_tagged_txs = unset,
	%% The first proof of access.
	poa = #poa{},
	%% The estimated USD to AR conversion rate used in the pricing calculations.
	%% A tuple {Dividend, Divisor}.
	%% Used until the transition to the new fee calculation method is complete.
	usd_to_ar_rate,
	%% The estimated USD to AR conversion rate scheduled to be used a bit later, used to
	%% compute the necessary fee for the currently signed txs. A tuple {Dividend, Divisor}.
	%% Used until the transition to the new fee calculation method is complete.
	scheduled_usd_to_ar_rate,
	%% The offset on the weave separting the data which has to be packed for mining after the
	%% fork 2.5 from the data which does not have to be packed yet. It is set to the
	%% weave_size of the 50th previous block at the hard fork block and moves down at a speed
	%% of ?PACKING_2_5_THRESHOLD_CHUNKS_PER_SECOND chunks/s. The motivation behind the
	%% threshold is a smooth transition to the new algorithm - big miners who might not want
	%% to adopt the new algorithm are still incentivized to upgrade and stay in the network
	%% for some time.
	packing_2_5_threshold,
	%% The offset on the weave separating the data which has to be split according to the
	%% stricter rules introduced in the fork 2.5 from the historical data. The new rules
	%% require all chunk sizes to be 256 KiB excluding the last or the only chunks of the
	%% corresponding transactions and the second last chunks of their transactions where they
	%% exceed 256 KiB in size when combined with the following (last) chunk. Furthermore, the
	%% new chunks may not be smaller than their Merkle proofs unless they are the last chunks.
	%% The motivation is to be able to put all chunks into 256 KiB buckets. It makes all
	%% chunks equally attractive because they have equal chances of being chosen as recall
	%% chunks. Moreover, every chunk costs the same in terms of storage and computation
	%% expenditure when packed (smaller chunks are simply padded before packing).
	strict_data_split_threshold,
	%% Used internally by tests.
	account_tree,

	%%
	%% The fields below were added at the fork 2.6.
	%%

	%% A part of the solution hash preimage. Used for the initial solution validation
	%% without a data chunk.
	hash_preimage = <<>>,
	%% The absolute recall offset.
	recall_byte,
	%% The total amount of winston the miner receives for this block.
	reward = 0,
	%% The solution hash of the previous block.
	previous_solution_hash = <<>>,
	%% The sequence number of the mining partition where the block was found.
	partition_number,
	%% The nonce limiter information.
	nonce_limiter_info = #nonce_limiter_info{},
	%% The second proof of access (empty when the solution was found with only one chunk).
	poa2 = #poa{},
	%% The absolute second recall offset.
	recall_byte2,
	%% The block signature.
	signature = <<>>,
	%% {KeyType, PubKey} - the public key the block was signed with.
	%% The only supported KeyType is currently {rsa, 65537}.
	reward_key,
	%% The estimated number of Winstons it costs the network to store one gibibyte
	%% for one minute.
	price_per_gib_minute = 0,
	%% The updated estimation of the number of Winstons it costs the network to store
	%% one gibibyte for one minute.
	scheduled_price_per_gib_minute = 0,
	%% The recursive hash of the network hash rates, block rewards, and mining addresses of
	%% the latest ?REWARD_HISTORY_BLOCKS blocks.
	reward_history_hash,
	%% The network hash rates, block rewards, and mining addresses from the latest
	%% ?REWARD_HISTORY_BLOCKS + ?STORE_BLOCKS_BEHIND_CURRENT blocks. Used internally, not gossiped.
	reward_history = [],
	%% The total number of Winston emitted when the endowment was not sufficient
	%% to compensate mining.
	debt_supply = 0,
	%% An additional multiplier for the transaction fees doubled every time the
	%% endowment pool becomes empty.
	kryder_plus_rate_multiplier = 1,
	%% A lock controlling the updates of kryder_plus_rate_multiplier. It is set to 1
	%% after the update and back to 0 when the endowment pool is bigger than
	%% ?RESET_KRYDER_PLUS_LATCH_THRESHOLD (redenominated according to the denomination
	%% used at the time).
	kryder_plus_rate_multiplier_latch = 0,
	%% The code for the denomination of AR in base units.
	%% 1 is the default which corresponds to the original denomination of 1^12 base units.
	%% Every time the available supply falls below ?REDENOMINATION_THRESHOLD,
	%% the denomination is multiplied by 1000, the code is incremented.
	%% Transaction denomination code must not exceed the block's denomination code.
	denomination = 1,
	%% The biggest known redenomination height (0 means there were no redenominations yet).
	redenomination_height = 0,
	%% The proof of signing the same block several times or extending two equal forks.
	double_signing_proof,
	%% The cumulative difficulty of the previous block.
	previous_cumulative_diff = 0,

	%%
	%% The fields below were added at the fork 2.7 (note that 2.6.8 was a hard fork too).
	%%

	%% The merkle trees of the data written after this weave offset may be constructed
	%% in a way where some subtrees are "rebased", i.e., their offsets start from 0 as if
	%% they were the leftmost subtree of the entire tree. The merkle paths for the chunks
	%% belonging to the subtrees will include a 32-byte 0-sequence preceding the pivot to
	%% the corresponding subtree. The rebases allow for flexible combination of data before
	%% registering it on the weave, extremely useful e.g., for the bundling services.
	merkle_rebase_support_threshold,
	%% The SHA2-256 of the packed chunk.
	chunk_hash,
	%% The SHA2-256 of the packed chunk2, when present.
	chunk2_hash,

	%% The hashes of the history of block times (in seconds), VDF times (in steps),
	%% and solution types (one-chunk vs two-chunk) of the latest
	%% ?BLOCK_TIME_HISTORY_BLOCKS blocks.
	block_time_history_hash,
	%% The block times (in seconds), VDF times (in steps), and solution types (one-chunk vs
	%% two-chunk) of the latest ?BLOCK_TIME_HISTORY_BLOCKS blocks.
	%% Used internally, not gossiped.
	block_time_history = [], % {block_interval, vdf_interval, chunk_count}

	%%
%% The fields below were added at the fork 2.8.
	%%

	%% The packing difficulty of the replica the block was mined with.
	%% Applies to both poa1 and poa2.
	%%
	%% Packing difficulty 0 denotes the usual pre-2.8 packing scheme.
	%% Packing difficulty 1 refers to the new composite packing of approximately the same
	%% computational cost as the difficulty 0 packing. Packing difficulty 2 is the composite
	%% packing where each sub-chunk is hashed twice as many times. The maximum allowed
	%% value is 32.
	%%
	%% When packing_difficulty >= 1, both poa1 and poa2 contain the unpacked chunks.
	%% The values of the "chunk" fields are now 8192-byte packed sub-chunks.
	packing_difficulty = 0,
	%% The SHA2-256 of the unpacked 0-padded (if less than 256 KiB) chunk.
	%% undefined when packing_difficulty == 0, has a value otherwise.
	unpacked_chunk_hash,
	%% The SHA2-256 of the unpacked 0-padded (if less than 256 KiB) chunk2.
	%% undefined when packing_difficulty == 0 or recall_byte2 == undefined,
	%% has a value otherwise.
	unpacked_chunk2_hash,

	%% Used internally, not gossiped. Convenient for validating potentially non-unique
	%% merkle proofs assigned to the different signatures of the same solution
	%% (see validate_poa_against_cached_poa in ar_block_pre_validator.erl).
	poa_cache,
	%% Used internally, not gossiped. Convenient for validating potentially non-unique
	%% merkle proofs assigned to the different signatures of the same solution
	%% (see validate_poa_against_cached_poa in ar_block_pre_validator.erl).
	poa2_cache,

	%% Used internally, not gossiped.
	receive_timestamp
}).

%% @doc A chunk with the proofs of its presence in the weave at a particular offset.
-record(poa, {
	%% DEPRECATED. Not used since the fork 2.4.
	option = 1,
	%% The path through the Merkle tree of transactions' "data_root"s.
	%% Proofs the inclusion of the "data_root" in the corresponding "tx_root"
%% under the particular offset.
	tx_path = <<>>,
	%% The path through the Merkle tree of the identifiers of the chunks
	%% of the corresponding transaction. Proofs the inclusion of the chunk
	%% in the corresponding "data_root" under a particular offset.
	data_path = <<>>,
	%% When packing difficulty is 0 chunk stores a full ?DATA_CHUNK_SIZE-sized packed chunk.
	%% When packing difficulty >= 1, chunk stores a ?COMPOSITE_PACKING_SUB_CHUNK_SIZE-sized
	%% packed sub-chunk.
	chunk = <<>>,
	%% When packing difficulty is 0 unpacked_chunk is <<>>.
	%% When packing difficulty >= 1, unpacked_chunk stores a full 0-padded
	%% ?DATA_CHUNK_SIZE-sized unpacked chunk.
	unpacked_chunk = <<>>
}).

%% @doc The information which simplifies validation of the nonce limiting procedures.
-record(nonce_limiter_info, {
	%% The output of the latest step - the source of the entropy for the mining nonces.
	output = <<>>,
	%% The output of the latest step of the previous block.
	prev_output = <<>>,
	%% The hash of the latest block mined below the current reset line.
	seed = <<>>,
	%% The hash of the latest block mined below the future reset line.
	next_seed = <<>>,
	%% The weave size of the latest block mined below the current reset line.
	partition_upper_bound = 0,
	%% The weave size of the latest block mined below the future reset line.
	next_partition_upper_bound = 0,
	%% The global sequence number of the nonce limiter step at which the block was found.
	global_step_number = 1,
	%% ?VDF_CHECKPOINT_COUNT_IN_STEP checkpoints from the most recent step in the nonce
%% limiter process.
	last_step_checkpoints = [],
	%% A list of the output of each step of the nonce limiting process. Note: each step
	%% has ?VDF_CHECKPOINT_COUNT_IN_STEP checkpoints, the last of which is that step's output.
	steps = [],

	%% The fields added at the fork 2.7

	%% The number of SHA2-256 iterations in a single VDF checkpoint. The protocol aims to keep the
	%% checkoint calculation time to around 40ms by varying this paramter. Note: there are
	%% 25 checkpoints in a single VDF step - so the protocol aims to keep the step calculation at
	%% 1 second by varying this parameter.
	vdf_difficulty = ?INITIAL_VDF_DIFFICULTY,
	%% The VDF difficulty scheduled for to be applied after the next VDF reset line.
	next_vdf_difficulty = ?INITIAL_VDF_DIFFICULTY
}).
    
    '''
    def __init__(
        self,
        nonce, previous_block, timestamp,
        last_retarget, diff, height, hash,
        indep_hash, txs, tx_root, # tx_tree, hash_list,
        hash_list_merkle = b'',
        wallet_list = None, reward_addr = 'unclaimed',
        tags = [], reward_pool = None,
        weave_size = None, block_size = None, cumulative_diff = 0,
        # size_tagged_txs,
        poa = None,
        # 2.5
        usd_to_ar_rate = [None,None], scheduled_usd_to_ar_rate = [None,None],
        packing_2_5_threshold = None,
        strict_data_split_threshold = None, # account_tree,
        # 2.6
        hash_preimage = '', recall_byte = None, reward = 0,
        previous_solution_hash = '', partition_number = None,
        nonce_limiter_info = None, poa2 = None, recall_byte2 = None,
        signature = '', reward_key = None,
        price_per_gib_minute = 0, scheduled_price_per_gib_minute = 0,
        reward_history_hash = None, # reward_history,
        debt_supply = 0, kryder_plus_rate_multiplier = 1,
        kryder_plus_rate_multiplier_latch = 0,
        denomination = 1, redenomination_height = 0,
        double_signing_proof = None,
        previous_cumulative_diff = 0,
        # 2.7
        merkle_rebase_support_threshold = None,
        chunk_hash = None, chunk2_hash = None,
        block_time_history_hash = None,
        # block_time_history,
        # 2.8
        packing_difficulty = 0,
        unpacked_chunk_hash = None, unpacked_chunk2_hash = None,
        # poa_cache, poa2_cache, receive_timestamp
    ):
        self.nonce = b64enc_if_not_str(nonce)
        self.previous_block = b64enc_if_not_str(previous_block)
        self.timestamp = int(timestamp)
        self.last_retarget = int(last_retarget)
        self.diff = int(diff)
        self.height = int(height)
        self.hash = b64enc_if_not_str(hash)
        self.indep_hash = b64enc_if_not_str(indep_hash)
        if len(txs) and not isinstance(txs[0],Transaction):
            self.txs = [b64enc_if_not_str(tx) for tx in txs]
        else:
            self.txs = txs
        self.tx_root = b64enc_if_not_str(tx_root)
        self.hash_list_merkle = b64enc_if_not_str(hash_list_merkle)
        self.wallet_list = b64enc_if_not_str(wallet_list)
        if reward_addr == 'unclaimed':
            self.reward_addr_raw = b''
        else:
            self.reward_addr_raw = b64dec_if_not_bytes(reward_addr)
        self.tags = tags
        self.reward_pool = int(reward_pool)
        self.weave_size = int(weave_size)
        self.block_size = int(block_size)
        self.cumulative_diff = int(cumulative_diff)
        self.poa = poa

        self.usd_to_ar_rate = [
            int_if_not_none(num)
            for num in usd_to_ar_rate
        ]
        self.scheduled_usd_to_ar_rate = [
            int_if_not_none(num)
            for num in scheduled_usd_to_ar_rate
        ]
        self.packing_2_5_threshold = int_if_not_none(packing_2_5_threshold)
        self.strict_data_split_threshold = int_if_not_none(strict_data_split_threshold)

        # 2.6

        self.hash_preimage = b64enc_if_not_str(hash_preimage)
        self.recall_byte = int_if_not_none(recall_byte)
        self.reward = int_if_not_none(reward)
        self.previous_solution_hash = b64enc_if_not_str(previous_solution_hash)
        self.partition_number = int_if_not_none(partition_number)
        if nonce_limiter_info is None:
            self.nonce_limiter_info = self.NonceLimiterInfo()
        else:
            self.nonce_limiter_info = nonce_limiter_info
        if poa2 is None:
            self.poa2 = self.POA()
        else:
            self.poa2 = poa2
        self.recall_byte2 = int_if_not_none(recall_byte2)
        self.signature = b64enc_if_not_str(signature)
        self.reward_key = b64enc_if_not_str(reward_key)
        self.price_per_gib_minute = int_if_not_none(price_per_gib_minute)
        self.scheduled_price_per_gib_minute = int_if_not_none(scheduled_price_per_gib_minute)
        self.reward_history_hash = b64enc_if_not_str(reward_history_hash)
        self.debt_supply = int_if_not_none(debt_supply)
        self.kryder_plus_rate_multiplier = int_if_not_none(kryder_plus_rate_multiplier)
        self.kryder_plus_rate_multiplier_latch = int_if_not_none(kryder_plus_rate_multiplier_latch)
        self.denomination = int_if_not_none(denomination)
        self.redenomination_height = int_if_not_none(redenomination_height)
        self.double_signing_proof = double_signing_proof
        self.previous_cumulative_diff = int_if_not_none(previous_cumulative_diff)

        # 2.7
        
        self.merkle_rebase_support_threshold = merkle_rebase_support_threshold
        self.chunk_hash = b64enc_if_not_str(chunk_hash)
        self.chunk2_hash = b64enc_if_not_str(chunk2_hash)
        
        # 2.8

        self.packing_difficulty = int_if_not_none(packing_difficulty)
        self.unpacked_chunk_hash = b64enc_if_not_str(unpacked_chunk_hash)
        self.unpacked_chunk2_hash = b64enc_if_not_str(unpacked_chunk2_hash)

    class POA(AutoRaw):
        def __init__(
            self, option = 1,
            tx_path = '', data_path = '',
            chunk = '', unpacked_chunk = '',
        ):
            self.option = int_if_not_none(option)
            self.tx_path = b64enc_if_not_str(tx_path)
            self.data_path = b64enc_if_not_str(data_path)
            self.chunk = b64enc_if_not_str(chunk)
            self.unpacked_chunk = b64enc_if_not_str(unpacked_chunk)
    class NonceLimiterInfo(AutoRaw):
        def __init__(
            self, output = '', prev_output = '', seed = '', next_seed = '',
            partition_upper_bound = 0, next_partition_upper_bound = 0,
            global_step_number = 1, last_step_checkpoints = [], steps = [],
            # 2.7
            vdf_difficulty = INITIAL_VDF_DIFFICULTY,
            next_vdf_difficulty = INITIAL_VDF_DIFFICULTY,
        ):
            self.output = b64enc_if_not_str(output)
            self.prev_output = b64enc_if_not_str(prev_output)
            self.seed = b64enc_if_not_str(seed)
            self.next_seed = b64enc_if_not_str(next_seed)
            self.partition_upper_bound = int_if_not_none(partition_upper_bound)
            self.next_partition_upper_bound = int_if_not_none(next_partition_upper_bound)
            self.global_step_number = int_if_not_none(global_step_number)
            if last_step_checkpoints and type(last_step_checkpoints[0]) is str:
                self.last_step_checkpoints = last_step_checkpoints
            else:
                self.last_step_checkpoints_raw = last_step_checkpoints
            if steps and type(steps[0]) is str:
                self.steps = steps
            else:
                self.steps_raw = steps

            # 2.7

            self.vdf_difficulty = vdf_difficulty
            self.next_vdf_difficulty = next_vdf_difficulty
    class DoubleSigningProof(list,AutoRaw):
        def __init__(
            self, key,
            signature1, cumulative_diff1,
            previous_cumulative_diff1, preimage1,
            signature2, cumulative_diff2,
            previous_cumulative_diff2, preimage2,
        ):
            self.key = b64enc_if_not_str(key)
            self.signature1 = b64enc_if_not_str(signature1)
            self.cumulative_diff1 = cumulative_diff1
            self.previous_cumulative_diff1 = previous_cumulative_diff1
            self.preimage1 = b64enc_if_not_str(preimage1)
            self.signature2 = b64enc_if_not_str(signature2)
            self.cumulative_diff2 = cumulative_diff2
            self.previous_cumulative_diff2 = previous_cumulative_diff2
            self.preimage2 = b64enc_if_not_str(preimage2)
            super([
                self.key,
                self.signature1, self.cumulative_diff1,
                self.previous_cumulative_diff1, self.preimage1,
                self.signature2, self.cumulative_diff2,
                self.previous_cumulative_diff2, self.preimage2,
            ])

    @property
    def reward_addr(self):
        if self.reward_addr_raw:
            return b64enc(self.reward_addr_raw)
        else:
            return 'unclaimed'

    @classmethod
    def fromjson(cls, data):
        kwparams = {**data}

        # process objects, rename subfields
        for param in ['poa', 'poa2']:
            poakwparams = kwparams.get(param)
            if poakwparams is not None:
                kwparams[param] = cls.POA(**poakwparams)
        for param in ['nonce_limiter_info']:
            nlikwparams = kwparams.get(param)
            if nlikwparams is not None:
                nlikwparams = {**nlikwparams}
                # rename
                nlikwparams['partition_upper_bound'] = nlikwparams.pop('zone_upper_bound')
                nlikwparams['next_partition_upper_bound'] = nlikwparams.pop('next_zone_upper_bound')
                nlikwparams['steps'] = nlikwparams.pop('checkpoints')
                kwparams[param] = cls.NonceLimiterInfo(**nlikwparams)

        # remove internal fields
        kwparams.pop('tx_tree', None)

        return cls(**kwparams)

    @classmethod
    def frombytes(cls, bytes):
        stream = io.BytesIO(bytes)
        block = cls.fromstream(stream)
        assert stream.tell() == len(bytes)
        return block

    @classmethod
    def fromstream(cls, stream):
        blk = cls(
            indep_hash                   = stream.read(48),
            previous_block               = arbindec(stream,  8),
            timestamp                    = arintdec(stream,  8),
            nonce                        = arbindec(stream, 16),
            height                       = arintdec(stream,  8),
            diff                         = arintdec(stream, 16),
            cumulative_diff              = arintdec(stream, 16),
            last_retarget                = arintdec(stream,  8),
            hash                         = arbindec(stream,  8),
            block_size                   = arintdec(stream, 16),
            weave_size                   = arintdec(stream, 16),
            reward_addr                  = arbindec(stream,  8),
            tx_root                      = arbindec(stream,  8),
            wallet_list                  = arbindec(stream,  8),
            hash_list_merkle             = arbindec(stream,  8),
            reward_pool                  = arintdec(stream,  8),
            packing_2_5_threshold        = arintdec(stream,  8),
            strict_data_split_threshold  = arintdec(stream,  8),
            usd_to_ar_rate               =[arintdec(stream,  8),
                                           arintdec(stream,  8)],
            scheduled_usd_to_ar_rate     =[arintdec(stream,  8),
                                           arintdec(stream,  8)],
            poa = cls.POA(
                option                   = arintdec(stream,  8),
                chunk                    = arbindec(stream, 24),
                tx_path                  = arbindec(stream, 24),
                data_path                = arbindec(stream, 24),
                unpacked_chunk           = None,
            ),
            tags = [
                arbindec(stream, 16)
                for idx in range(erlintdec(stream, 16))
            ][::-1],
            # either 32-byte txids or complete txs
            txs = [
                Transaction.fromstream(stream)
                for idx in range(erlintdec(stream, 16))
            ][::-1],
        )

        if blk.height >= FORK_2_6:
            blk.hash_preimage_raw          = arbindec(stream, 8)
            blk.recall_byte                = arintdec(stream, 16)
            blk.reward                     = arintdec(stream, 8)
            blk.signature_raw              = arbindec(stream, 16)
            blk.recall_byte2               = arintdec(stream, 16)
            blk.previous_solution_hash_raw = arbindec(stream, 8)
            blk.partition_number           = erlintdec(stream, 256)
            blk.nonce_limiter_info = cls.NonceLimiterInfo(
                output                     = stream.read(32),
                global_step_number         = erlintdec(stream, 64),
                seed                       = stream.read(48),
                next_seed                  = stream.read(48),
                prev_output                = arbindec(stream, 8),
                partition_upper_bound      = erlintdec(stream, 256),
                next_partition_upper_bound = erlintdec(stream, 256),
                last_step_checkpoints      = [
                    stream.read(32)
                    for idx in range(erlintdec(stream,16))
                ],
                steps                      = [
                    stream.read(32)
                    for idx in range(erlintdec(stream,16))
                ],
                vdf_difficulty             = None,
                next_vdf_difficulty        = None,
            )
            blk.poa2 = cls.POA(
                option = 1,
                tx_path = None,
                data_path = None,
                chunk            = arbindec(stream, 24),
                unpacked_chunk = None,
            )
            blk.reward_key_raw             = arbindec(stream, 16)
            blk.poa2.tx_path_raw           = arbindec(stream, 24)
            blk.poa2.data_path_raw         = arbindec(stream, 24)
            blk.price_per_gib_minute       = arintdec(stream, 8)
            blk.scheduled_price_per_gib_minute = arintdec(stream, 8)
            blk.reward_history_hash_raw    = stream.read(32)
            blk.debt_supply                = arintdec(stream, 8)
            blk.kryder_plus_rate_multiplier= erlintdec(stream, 24)
            blk.kryder_plus_rate_multiplier_latch = erlintdec(stream, 8)
            blk.denomination               = erlintdec(stream, 24)
            blk.redenomination_height      = arintdec(stream, 8)
            blk.previous_cumulative_diff   = arintdec(stream, 16)
            double_signing_proof_flag  = erlintdec(stream, 8)
            assert double_signing_proof_flag & 1 == double_signing_proof_flag
            if double_signing_proof_flag:
                blk.double_signing_proof = cls.DoubleSigningProof(
                    key                       = stream.read(512),
                    signature1                = stream.read(512),
                    cumulative_diff1          = arintdec(stream, 16),
                    previous_cumulative_diff1 = arintdec(stream, 16),
                    preimage1                 = stream.read(64),
                    signature2                = stream.read(512),
                    cumulative_diff2          = arintdec(stream, 16),
                    previous_cumulative_diff2 = arintdec(stream, 16),
                    preimage2                 = stream.read(64),
                )

        if blk.height >= FORK_2_7:
            blk.merkle_rebase_support_threshold        = arintdec(stream, 16)
            blk.chunk_hash_raw                         = stream.read(32)
            blk.chunk2_hash_raw                        = arbindec(stream, 8)
            blk.block_time_history_hash_raw            = stream.read(32)
            blk.nonce_limiter_info.vdf_difficulty      = arintdec(stream, 8)
            blk.nonce_limiter_info.next_vdf_difficulty = arintdec(stream, 8)

        if blk.height >= FORK_2_8:
            blk.packing_difficulty       = erlintdec(stream, 8)
            blk.unpacked_chunk_hash_raw  = arbindec(stream, 8)
            blk.unpacked_chunk2_hash_raw = arbindec(stream, 8)
            blk.poa.unpacked_chunk_raw   = arbindec(stream, 24)
            blk.poa2.unpacked_chunk_raw  = arbindec(stream, 24)

        return blk

    def tojson(self):
        json = {}
        if self.height >= FORK_2_6:
            json.update({
                'hash_preimage': self.hash_preimage,
                'recall_byte': str(self.recall_byte),
                'reward': str(self.reward),
                'previous_solution_hash': self.previous_solution_hash,
                'partition_number': self.partition_number,
                'nonce_limiter_info': {
                    'output': self.nonce_limiter_info.output,
                    'global_step_number': self.nonce_limiter_info.global_step_number,
                    'seed': self.nonce_limiter_info.seed,
                    'next_seed': self.nonce_limiter_info.next_seed,
                    'zone_upper_bound': self.nonce_limiter_info.partition_upper_bound,
                    'next_zone_upper_bound': self.nonce_limiter_info.next_partition_upper_bound,
                    'prev_output': self.nonce_limiter_info.prev_output,
                    'last_step_checkpoints': self.nonce_limiter_info.last_step_checkpoints,
                    'checkpoints': self.nonce_limiter_info.steps,
                },
                'poa2': {
                    'option': str(self.poa2.option),
                    'tx_path': self.poa2.tx_path,
                    'data_path': self.poa2.data_path,
                    'chunk': self.poa2.chunk,
                },
                'signature': self.signature,
                'reward_key': self.reward_key,
                'price_per_gib_minute': str(self.price_per_gib_minute),
                'scheduled_price_per_gib_minute': str(self.scheduled_price_per_gib_minute),
                'reward_history_hash': self.reward_history_hash,
                'debt_supply': str(self.debt_supply),
                'kryder_plus_rate_multiplier': str(self.kryder_plus_rate_multiplier),
                'kryder_plus_rate_multiplier_latch': str(self.kryder_plus_rate_multiplier_latch),
                'denomination': str(self.denomination),
                'redenomination_height': self.redenomination_height,
                'double_signing_proof': {
                    'key': self.double_signing_proof.key,
                    'signature1': self.double_signing_proof.signature1,
                    'cumulative_diff1': self.double_signing_proof.cumulative_diff1,
                    'previous_cumulative_diff1': self.double_signing_proof.previous_cumulative_diff1,
                    'preimage1': self.double_signing_proof.preimage1,
                    'signature2': self.double_signing_proof.signature2,
                    'cumulative_diff2': self.double_signing_proof.cumulative_diff2,
                    'previous_cumulative_diff2': self.double_signing_proof.previous_cumulative_diff2,
                    'preimage2': self.double_signing_proof.preimage2,
                } if self.double_signing_proof else {},
                'previous_cumulative_diff': str(self.previous_cumulative_diff),
            })
        if self.height >= FORK_2_5:
            json.update({
                'usd_to_ar_rate': [str(value) for value in self.usd_to_ar_rate],
                'scheduled_usd_to_ar_rate': [str(value) for value in self.scheduled_usd_to_ar_rate],
                'packing_2_5_threshold': str(self.packing_2_5_threshold),
                'strict_data_split_threshold': str(self.strict_data_split_threshold),
            })
        json.update({
            'nonce': self.nonce,
            'previous_block': self.previous_block,
            'timestamp': self.timestamp,
            'last_retarget': self.last_retarget,
        })

        # this verbosity does the following:
        # 1. adds tx_tree before 1.8
        # 2. hides cumulative_diff and hash_list_merkle prior to 1.6
        # 3. controls str vs int type of fields depending on height
        # conditioning the individual fields would be less verbose,
        #  and only a microhair slower
        if self.height >= FORK_2_4:
            json.update({
                'diff': str(self.diff),
                'height': self.height,
                'hash': self.hash,
                'indep_hash': self.indep_hash,
                'txs': [tx.id if type(tx) is Transaction else tx for tx in self.txs],
                'tx_root': self.tx_root,
                'wallet_list': self.wallet_list,
                'reward_addr': self.reward_addr,
                'tags': self.tags,
                'reward_pool': str(self.reward_pool),
                'weave_size': str(self.weave_size),
                'block_size': str(self.block_size),
                'cumulative_diff': str(self.cumulative_diff),
                'hash_list_merkle': self.hash_list_merkle,
            })
        elif self.height >= FORK_1_8:
            json.update({
                'diff': str(self.diff),
                'height': self.height,
                'hash': self.hash,
                'indep_hash': self.indep_hash,
                'txs': [tx.id if type(tx) is Transaction else tx for tx in self.txs],
                'tx_root': self.tx_root,
                'tx_tree': [],
                'wallet_list': self.wallet_list,
                'reward_addr': self.reward_addr,
                'tags': self.tags,
                'reward_pool': self.reward_pool,
                'weave_size': self.weave_size,
                'block_size': self.block_size,
                'cumulative_diff': str(self.cumulative_diff),
                'hash_list_merkle': self.hash_list_merkle,
            })
        elif self.height >= FORK_1_6:
            json.update({
                'diff': self.diff,
                'height': self.height,
                'hash': self.hash,
                'indep_hash': self.indep_hash,
                'txs': [tx.id if type(tx) is Transaction else tx for tx in self.txs],
                'tx_root': self.tx_root,
                'tx_tree': [],
                'wallet_list': self.wallet_list,
                'reward_addr': self.reward_addr,
                'tags': self.tags,
                'reward_pool': self.reward_pool,
                'weave_size': self.weave_size,
                'block_size': self.block_size,
                'cumulative_diff': self.cumulative_diff,
                'hash_list_merkle': self.hash_list_merkle,
            })
        else:
            json.update({
                'diff': self.diff,
                'height': self.height,
                'hash': self.hash,
                'indep_hash': self.indep_hash,
                'txs': [tx.id if type(tx) is Transaction else tx for tx in self.txs],
                'tx_root': self.tx_root,
                'tx_tree': [],
                'wallet_list': self.wallet_list,
                'reward_addr': self.reward_addr,
                'tags': self.tags,
                'reward_pool': self.reward_pool,
                'weave_size': self.weave_size,
                'block_size': self.block_size,
            })
        json.update({
            'poa': {
                'option': str(self.poa.option),
                'tx_path': self.poa.tx_path,
                'data_path': self.poa.data_path,
                'chunk': self.poa.chunk,
            }
        })
        return json

    def tobytes(self):
        stream = io.BytesIO()
        stream.write(self.indep_hash_raw)
        stream.write(arbinenc(self.previous_block_raw,              8))
        stream.write(arintenc(self.timestamp,                       8))
        stream.write(arbinenc(self.nonce_raw,                      16))
        stream.write(arintenc(self.height,                          8))
        stream.write(arintenc(self.diff,                           16))
        stream.write(arintenc(self.cumulative_diff,                16))
        stream.write(arintenc(self.last_retarget,                   8))
        stream.write(arbinenc(self.hash_raw,                        8))
        stream.write(arintenc(self.block_size,                     16))
        stream.write(arintenc(self.weave_size,                     16))
        stream.write(arbinenc(self.reward_addr_raw,                 8))
        stream.write(arbinenc(self.tx_root_raw,                     8))
        stream.write(arbinenc(self.wallet_list_raw,                 8))
        stream.write(arbinenc(self.hash_list_merkle_raw,            8))
        stream.write(arintenc(self.reward_pool,                     8))
        stream.write(arintenc(self.packing_2_5_threshold,           8))
        stream.write(arintenc(self.strict_data_split_threshold,     8))
        stream.write(arintenc(self.usd_to_ar_rate[0],               8))
        stream.write(arintenc(self.usd_to_ar_rate[1],               8))
        stream.write(arintenc(self.scheduled_usd_to_ar_rate[0],     8))
        stream.write(arintenc(self.scheduled_usd_to_ar_rate[1],     8))
        stream.write(arintenc(self.poa.option,                      8))
        stream.write(arbinenc(self.poa.chunk_raw,                  24))
        stream.write(arbinenc(self.poa.tx_path_raw,                24))
        stream.write(arbinenc(self.poa.data_path_raw,              24))
        stream.write(erlintenc(len(self.tags),                     16))
        for tag in self.tags:
            stream.write(arbinenc(tag,                             16))
        stream.write(erlintenc(len(self.txs),                      16))
        for tx in self.txs[::-1]:
            if type(tx) is Transaction:
                stream.write(tx.tobytes())
            else:
                stream.write(arbinenc(b64dec(tx),                  24))

        if self.height >= FORK_2_6:
            stream.write(arbinenc(self.hash_preimage_raw,           8))
            stream.write(arintenc(self.recall_byte,                16))
            stream.write(arintenc(self.reward,                      8))
            stream.write(arbinenc(self.signature_raw,              16))
            stream.write(arintenc(self.recall_byte2,               16))
            stream.write(arbinenc(self.previous_solution_hash_raw,  8))
            stream.write(erlintenc(self.partition_number,         256))
            stream.write(self.nonce_limiter_info.output_raw)
            stream.write(erlintenc(
                self.nonce_limiter_info.global_step_number,        64))
            stream.write(self.nonce_limiter_info.seed_raw)
            stream.write(self.nonce_limiter_info.next_seed_raw)
            stream.write(arbinenc(
                self.nonce_limiter_info.prev_output_raw,            8))
            stream.write(erlintenc(
                self.nonce_limiter_info.partition_upper_bound,    256))
            stream.write(erlintenc(
                self.nonce_limiter_info.next_partition_upper_bound,256))
            stream.write(erlintenc(
                len(self.nonce_limiter_info.last_step_checkpoints),16))
            for last_step_checkpoint in (
                self.nonce_limiter_info.last_step_checkpoints_raw
            ):
                stream.write(last_step_checkpoint)
            stream.write(erlintenc(
                len(self.nonce_limiter_info.steps),                16))
            for step in self.nonce_limiter_info.steps_raw:
                stream.write(step)
            stream.write(arbinenc(self.poa2.chunk_raw,             24))
            stream.write(arbinenc(self.reward_key_raw,             16))
            stream.write(arbinenc(self.poa2.tx_path_raw,           24))
            stream.write(arbinenc(self.poa2.data_path_raw,         24))
            stream.write(arintenc(self.price_per_gib_minute,        8))
            stream.write(arintenc(
                self.scheduled_price_per_gib_minute,                8))
            stream.write(self.reward_history_hash_raw)
            stream.write(arintenc(self.debt_supply,                 8))
            stream.write(erlintenc(
                self.kryder_plus_rate_multiplier,                  24))
            stream.write(erlintenc(
                self.kryder_plus_rate_multiplier_latch,             8))
            stream.write(erlintenc(self.denomination,              24))
            stream.write(arintenc(self.redenomination_height,       8))
            stream.write(arintenc(self.previous_cumulative_diff,   16))
            stream.write(erlintenc(
                1 if self.double_signing_proof else 0,              8))
            if self.double_signing_proof:
                stream.write(self.double_signing_proof.key_raw)
                stream.write(self.double_signing_proof.signature1_raw)
                stream.write(arintenc(
                    self.double_signing_proof.cumulative_diff1,    16))
                stream.write(arintenc(
                    self.double_signing_proof.previous_cumulative_diff1,
                                                                   16))
                stream.write(self.double_signing_proof.preimage1_raw)
                stream.write(self.double_signing_proof.signature2_raw)
                stream.write(arintenc(
                    self.double_signing_proof.cumulative_diff2,    16))
                stream.write(arintenc(self.
                    double_signing_proof.previous_cumulative_diff2,16))
                stream.write(self.double_signing_proof.preimage2_raw)

        if self.height >= FORK_2_7:
            stream.write(arintenc(
                self.merkle_rebase_support_threshold,              16))
            stream.write(self.chunk_hash_raw)
            stream.write(arbinenc(self.chunk2_hash_raw,             8))
            stream.write(self.block_time_history_hash_raw)
            stream.write(arintenc(
                self.nonce_limiter_info.vdf_difficulty,             8))
            stream.write(arintenc(
                self.nonce_limiter_info.next_vdf_difficulty,        8))

        if self.height >= FORK_2_8:
            stream.write(erlintenc(self.packing_difficulty,         8))
            stream.write(arbinenc(self.unpacked_chunk_hash_raw,     8))
            stream.write(arbinenc(self.unpacked_chunk2_hash_raw,    8))
            stream.write(arbinenc(self.poa.unpacked_chunk_raw,     24))
            stream.write(arbinenc(self.poa2.unpacked_chunk_raw,    24))

        return stream.getvalue()

    # ar_node_utils.erlt / validate_block

    # NOTE: the pip randomx module uses a backend funded by arweave.
    #  POW = ar_randomx_state:hash(Height, << Nonce/binary, BDS/binary >>),
                # uses randomx_state_by_height
                        # which calls get_state_by_height, swap_height, randomx_key
                                    # swap height floors the height to RANDOMX_KEY_SWAP_FREQ
                            # get_state_by_height and get_key_from_Cache also use swap_height
                # to branch to one of
                # ar_mine_randomx: hash_fast, hash_light, init_light;hash_light
    #   ar_mine:validate(POW, ar_poa:modify_diff(Diff, POA#poa.option, Height), Height)

    #def compute_indep_hash(self): # from ar_http_iface_middleware.erl
    #    bds = self._get_data_segment()
    #    return bds, ar_weave:indep_hash(BDS, self.hash_row, self.nonce_raw, self.poa)

    # from ar_block.erl
    def _get_data_segment(self):
        bds_base = self._get_data_segment_base()
        block_index_merkle = self.hash_list_merkle_raw
        return deep_hash([
            bds_base,
            str(self.timestamp).encode(),
            str(self.last_retarget).encode(),
            str(self.diff).encode(),
            str(self.cumulative_diff).encode(),
            str(self.reward_pool).encode(),
            self.wallet_list_raw,
            block_index_merkle
        ])
    def _get_data_segment_base(self):
        if self.height >= FORK_2_4:
            props = [
                str(self.height).encode(),
                self.previous_block_raw,
                self.tx_root_raw,
                [
                    b64dec(tx.id if type(tx) is Transaction else tx)
                    for tx in self.tx
                ],
                str(self.block_size).encode(),
                str(self.weave_size).encode(),
                self.reward_addr_raw,
                self.tags
            ]
            if self.height >= FORK_2_5:
                props2 = [
                    str(self.usd_to_ar_rate[0]).encode(),
                    str(self.usd_to_ar_rate[1]).encode(),
                    str(self.scheduled_usd_to_ar_rate[0]).encode(),
                    str(self.scheduled_usd_to_ar_rate[1]).encode(),
                    str(self.packing_threshold).encode(),
                    str(self.strict_data_split_threshold),
                    *props
                ]
            else:
                props2 = props
            return deep_hash(props2)
        else:
            return deep_hash([
                str(self.height).encode(),
                self.previous_block_raw,
                self.tx_root_raw,
                [
                    b64dec(tx.id if type(tx) is Transaction else tx)
                    for tx in self.tx
                ],
                str(self.block_size).encode(),
                str(self.weave_size).encode(),
                self.reward_addr_raw,
                [[tag['name'].encode(), tag['value'].encode()] for tag in self.tags],
                [
                    str(self.poa.option).encode(),
                    self.poa.tx_path,
                    self.poa.data_path,
                    self.poa.chunk,
                ]
            ])
    def _encode_tags(self):
        if self.height >= FORK_2_5:
            return


if __name__ == '__main__':
    def store_block_testdata():
        from .peer import Peer
        from . import (
            FORK_1_6, FORK_1_7, FORK_1_8, FORK_1_9,
            FORK_2_0, FORK_2_2, FORK_2_3,
            FORK_2_4, FORK_2_5,
            FORK_2_6, FORK_2_6_8,
            FORK_2_7, FORK_2_7_1, FORK_2_7_2,
            FORK_2_8,
        )
        peer = Peer()
        blocks = dict(
            BLOCK_GEN_bytes = peer.block2_height(0),
            BLOCK_GEN_json  = peer.block_height (0),
            BLOCK_HT1_bytes = peer.block2_height(1),
            BLOCK_HT1_json  = peer.block_height (1),
            BLOCK_1_6_bytes = peer.block2_height(FORK_1_6),
            BLOCK_1_6_json  = peer.block_height (FORK_1_6),
            BLOCK_1_7_bytes = peer.block2_height(FORK_1_7),
            BLOCK_1_7_json  = peer.block_height (FORK_1_7),
            BLOCK_1_8_bytes = peer.block2_height(FORK_1_8),
            BLOCK_1_8_json  = peer.block_height (FORK_1_8),
            BLOCK_1_9_bytes = peer.block2_height(FORK_1_9),
            BLOCK_1_9_json  = peer.block_height (FORK_1_9),
            BLOCK_2_0_bytes = peer.block2_height(FORK_2_0),
            BLOCK_2_0_json  = peer.block_height (FORK_2_0),
            BLOCK_2_2_bytes = peer.block2_height(FORK_2_2),
            BLOCK_2_2_json  = peer.block_height (FORK_2_2),
            BLOCK_2_3_bytes = peer.block2_height(FORK_2_3),
            BLOCK_2_3_json  = peer.block_height (FORK_2_3),
            BLOCK_2_4_bytes = peer.block2_height(FORK_2_4),
            BLOCK_2_4_json  = peer.block_height (FORK_2_4),
            BLOCK_2_5_bytes = peer.block2_height(FORK_2_5),
            BLOCK_2_5_json  = peer.block_height (FORK_2_5),
            BLOCK_2_6_bytes = peer.block2_height(FORK_2_6),
            BLOCK_2_6_json  = peer.block_height (FORK_2_6),
            BLOCK_2_6_8_bytes=peer.block2_height(FORK_2_6_8),
            BLOCK_2_6_8_json= peer.block_height (FORK_2_6_8),
            BLOCK_2_7_bytes = peer.block2_height(FORK_2_7),
            BLOCK_2_7_json  = peer.block_height (FORK_2_7),
            BLOCK_2_7_1_bytes=peer.block2_height(FORK_2_7_1),
            BLOCK_2_7_1_json= peer.block_height (FORK_2_7_1),
            BLOCK_2_7_2_bytes=peer.block2_height(FORK_2_7_2),
            BLOCK_2_7_2_json= peer.block_height (FORK_2_7_2),
        )
        with open('_block_testdata.py', 'wt') as fh:
            for name, val in blocks.items():
                print(f'{name} = {repr(val)}', file=fh)
        return blocks
    #store_block_testdata()
    from ._block_testdata import *

    def dict_cmp(a,b,ctx=''):
        if a != b:
            for k in set([*a.keys(),*b.keys()]):
                v1 = a.get(k,'MISSING')
                v2 = b.get(k,'MISSING')
                if v1 != v2:
                    subctx = ctx+f'["{k}"]'
                    if type(v1) is dict and type(v2) is dict:
                        return dict_cmp(v1, v2, ctx=subctx)
                    elif type(v1) is list and type(v2) is list:
                        dict_cmp(len(v1), len(v2), ctx=subctx)
                        for idx in range(min(len(v1),len(v2))):
                            if v1[idx] != v2[idx]:
                                print(f'{subctx}[{idx}]', repr(v1[idx]), '!=', repr(v2[idx]))
                    else:
                        print(subctx, repr(v1), '!=', repr(v2))
            return False
        else:
            return True
    def bin_cmp(a, b):
        if a != b:
            import binascii
            for idx in range(max(len(a),len(b))):
                if idx >= len(a) or idx >= len(b) or a[idx] != b[idx]:
                    for line in range(idx, max(len(a),len(b)), 16):
                        chunk_a = a[line:line+16]
                        chunk_b = b[line:line+16]
                        print(line, binascii.hexlify(chunk_a, ' ').decode(), '!=', binascii.hexlify(chunk_b, ' ').decode())
                        if line > idx + 1024:
                            break
                    return False
        else:
            return True
    assert dict_cmp(Block.frombytes(BLOCK_GEN_bytes).tojson(), BLOCK_GEN_json)
    assert bin_cmp(Block.fromjson(  BLOCK_GEN_json).tobytes(), BLOCK_GEN_bytes)
    assert dict_cmp(Block.frombytes(BLOCK_HT1_bytes).tojson(), BLOCK_HT1_json)
    assert bin_cmp(Block.fromjson(  BLOCK_HT1_json).tobytes(), BLOCK_HT1_bytes)
    assert dict_cmp(Block.frombytes(BLOCK_1_6_bytes).tojson(), BLOCK_1_6_json)
    assert bin_cmp(Block.fromjson(  BLOCK_1_6_json).tobytes(), BLOCK_1_6_bytes)
    assert dict_cmp(Block.frombytes(BLOCK_1_7_bytes).tojson(), BLOCK_1_7_json)
    assert bin_cmp(Block.fromjson(  BLOCK_1_7_json).tobytes(), BLOCK_1_7_bytes)
    assert dict_cmp(Block.frombytes(BLOCK_1_8_bytes).tojson(), BLOCK_1_8_json)
    assert bin_cmp(Block.fromjson(  BLOCK_1_8_json).tobytes(), BLOCK_1_8_bytes)
    assert dict_cmp(Block.frombytes(BLOCK_1_9_bytes).tojson(), BLOCK_1_9_json)
    assert bin_cmp(Block.fromjson(  BLOCK_1_9_json).tobytes(), BLOCK_1_9_bytes)
    assert dict_cmp(Block.frombytes(BLOCK_2_0_bytes).tojson(), BLOCK_2_0_json)
    assert bin_cmp(Block.fromjson(  BLOCK_2_0_json).tobytes(), BLOCK_2_0_bytes)
    assert dict_cmp(Block.frombytes(BLOCK_2_2_bytes).tojson(), BLOCK_2_2_json)
    assert bin_cmp(Block.fromjson(  BLOCK_2_2_json).tobytes(), BLOCK_2_2_bytes)
    assert dict_cmp(Block.frombytes(BLOCK_2_3_bytes).tojson(), BLOCK_2_3_json)
    assert bin_cmp(Block.fromjson(  BLOCK_2_3_json).tobytes(), BLOCK_2_3_bytes)
    assert dict_cmp(Block.frombytes(BLOCK_2_4_bytes).tojson(), BLOCK_2_4_json)
    assert bin_cmp(Block.fromjson(  BLOCK_2_4_json).tobytes(), BLOCK_2_4_bytes)
    assert dict_cmp(Block.frombytes(BLOCK_2_5_bytes).tojson(), BLOCK_2_5_json)
    assert bin_cmp(Block.fromjson(  BLOCK_2_5_json).tobytes(), BLOCK_2_5_bytes)
    assert dict_cmp(Block.frombytes(BLOCK_2_6_bytes).tojson(), BLOCK_2_6_json)
    assert bin_cmp(Block.fromjson(  BLOCK_2_6_json).tobytes(), BLOCK_2_6_bytes)
