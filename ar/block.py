import fractions
import io
from ar.utils import (
    erlintenc, arbinenc, arintenc,
    erlintdec, arbindec, arintdec,
    b64enc_if_not_str, b64enc, b64dec
)
from ar.utils.deep_hash import deep_hash
from .chunk import Chunk
from .transaction import Transaction
from . import FORK_2_4, FORK_2_5, FORK_2_6, FORK_2_7, FORK_2_8

# STATUS
# MINING IS NOT PLANNED AT THIS TIME
# FORK      FROMBYTES   TOBYTES     FROMJSON    TOJSON      VALIDATION  MINING
# gen       started     [ ]         [ ]         [ ]         unstarted   unstarted
# 2.4       started     [ ]         [ ]         [ ]         unstarted   unstarted
# 2.5       [X]         [X]         [X]         [X]         notes       unstarted
# 2.6       started     [ ]         [ ]         [ ]         unstarted   unstarted
# 2.7       started     [ ]         [ ]         [ ]         unstarted   unstarted
# 2.8       started     [ ]         [ ]         [ ]         unstarted   unstarted

class Block:
    def __init__(self, indep_hash, prev_block, timestamp, nonce,
                 height, diff, cumulative_diff, last_retarget,
                 hash, block_size, weave_size, reward_addr,
                 tx_root, wallet_list, hash_list_merkle, reward_pool,
                 packing_threshold, strict_chunk_threshold,
                 usd_to_ar_rate, scheduled_usd_to_ar_rate,
                 poa_option, poa_chunk, poa_tx_path, poa_data_path,
                 tags = [], txs = []):
        self.indep_hash = b64enc_if_not_str(indep_hash)
        self.prev_block = b64enc_if_not_str(prev_block)
        self.timestamp = timestamp
        self.nonce = b64enc_if_not_str(nonce)
        self.height = height
        self.diff = diff
        self.cumulative_diff = cumulative_diff
        self.last_retarget = last_retarget
        self.hash = b64enc_if_not_str(hash)
        self.block_size = block_size
        self.weave_size = weave_size
        self.reward_addr = b64enc_if_not_str(reward_addr)
        self.tx_root = b64enc_if_not_str(tx_root)
        self.wallet_list = b64enc_if_not_str(wallet_list)
        self.hash_list_merkle = b64enc_if_not_str(hash_list_merkle)
        self.reward_pool = reward_pool
        self.packing_threshold = packing_threshold
        self.strict_chunk_threshold = strict_chunk_threshold

        if not isinstance(usd_to_ar_rate, (tuple, list)):
            usd_to_ar_rate = fractions.Fraction(usd_to_ar_rate)
            self.usd_to_ar_rate_raw = (usd_to_ar_rate.numerator, usd_to_ar_rate.denominator)
        else:
            self.usd_to_ar_rate_raw = usd_to_ar_rate

        if not isinstance(scheduled_usd_to_ar_rate, (tuple, list)):
            scheduled_usd_to_ar_rate = fractions.Fraction(scheduled_usd_to_ar_rate)
            self.scheduled_usd_to_ar_rate_raw = (
                scheduled_usd_to_ar_rate.numerator, scheduled_usd_to_ar_rate.denominator
            )
        else:
            self.scheduled_usd_to_ar_rate_raw = scheduled_usd_to_ar_rate

        self.poa_option = poa_option
        self.poa_chunk = b64enc_if_not_str(poa_chunk)
        self.poa_tx_path = b64enc_if_not_str(poa_tx_path)
        self.poa_data_path = b64enc_if_not_str(poa_data_path)

        self.tags = tags
        if len(txs) and isinstance(txs[0], (bytes, bytearray)):
            self.txs = [b64enc_if_not_str(tx) for tx in txs[::-1]]
        else:
            self.txs = txs

    def __getattr__(self, attr):
        if attr.endswith('_raw'):
            return b64dec(getattr(self, attr[:-4]))
        else:
            return super().__getattr__(attr)

    @property
    def usd_to_ar_rate(self):
        try:
            return fractions.Fraction(*self.usd_to_ar_rate_raw)
        except ZeroDivisionError:
            return None

    @property
    def scheduled_usd_to_ar_rate(self):
        try:
            return fractions.Fraction(*self.sceduled_usd_to_ar_rate_raw)
        except ZeroDivisionError:
            return None

    @classmethod
    def fromjson(cls, data):
        kwparams = {**data}

        # pull out poa keys for now
        kwparams.update({
            'poa_' + key : value
            for key, value in kwparams.pop('poa', {}).items()
        })

        # convert integer strings to integers
        for param in ('usd_to_ar_rate', 'scheduled_usd_to_ar_rate'):
            kwparams[param] = [int(amount) for amount in kwparams[param]]
            kwparams[param] = [int(amount) for amount in kwparams[param]]
        for param in (
            'packing_2_5_threshold', 'strict_data_split_threshold',
            'timestamp', 'last_retarget', 'diff', 'reward_pool',
            'weave_size' , 'block_size', 'cumulative_diff',
            'poa_option'
        ):
            kwparams[param] = int(kwparams[param])

        # rename
        kwparams['packing_threshold'] = kwparams.pop('packing_2_5_threshold')
        kwparams['strict_chunk_threshold'] = kwparams.pop('strict_data_split_threshold')
        kwparams['prev_block'] = kwparams.pop('previous_block')

        return cls(**kwparams)

    @classmethod
    def frombytes(cls, bytes):
        stream = io.BytesIO(bytes)
        block = cls.fromstream(stream)
        assert stream.tell() == len(bytes)
        return block
            
    @classmethod
    def fromstream(cls, stream):
        indep_hash_raw               = stream.read(48)
        prev_block_raw               = arbindec(stream,  8)
        timestamp                    = arintdec(stream,  8)
        nonce_raw                    = arbindec(stream, 16)
        height                       = arintdec(stream,  8)
        diff                         = arintdec(stream, 16)
        cumulative_diff              = arintdec(stream, 16)
        last_retarget                = arintdec(stream,  8)
        hash_raw                     = arbindec(stream,  8)
        block_size                   = arintdec(stream, 16)
        weave_size                   = arintdec(stream, 16)
        reward_addr_raw              = arbindec(stream,  8)
        tx_root_raw                  = arbindec(stream,  8)
        wallet_list_raw              = arbindec(stream,  8)
        hash_list_merkle_raw         = arbindec(stream,  8)
        reward_pool                  = arintdec(stream,  8)
        packing_2_5_threshold        = arintdec(stream,  8)
        strict_data_split_threshold  = arintdec(stream,  8)
        usd_to_ar_rate_raw           =[arintdec(stream,  8),
                                       arintdec(stream,  8)]
        scheduled_usd_to_ar_rate_raw =[arintdec(stream,  8),
                                       arintdec(stream,  8)]
        poa_option                   = arintdec(stream,  8)
        poa_chunk_raw                = arbindec(stream, 24)
        poa_tx_path_raw              = arbindec(stream, 24)
        poa_data_path_raw            = arbindec(stream, 24)

        tags_count = erlintdec(stream, 16)
        tags       = [arbindec(stream, 16) for idx in range(tags_count)]

        # either 32-byte txids or complete txs
        txs_count = erlintdec(stream, 16)
        txs = [Transaction.fromstream(stream) for idx in range(txs_count)][::-1]

        if height >= FORK_2_6:
            hash_preimage  = arbindec(stream, 8)
            recall_byte    = arintdec(stream, 16)
            reward         = arintdec(stream, 8)
            sig            = arbindec(stream, 16)
            recall_byte_2  = arintdec(stream, 16)
            prev_soln_hash = arbindec(stream, 8)
            part_no        = erlintdec(stream, 256)
            nonce_limiter_output           = stream.read(32)
            nonce_limiter_global_step_no   = erlintdec(stream, 64)
            nonce_limiter_seed             = stream.read(48)
            nonce_limiter_next_seed        = stream.read(48)
            nonce_limiter_prev_output      = arbindec(stream, 8)
            nonce_limiter_part_ubound      = erlintdec(stream, 256)
            nonce_limiter_next_part_ubound = erlintdec(stream, 256)
            nonce_limiter_last_step_chkpts_ct   = erlintdec(stream, 16)
            nonce_limiter_last_step_chkpts      = [stream.read(32) for idx in range(nonce_limiter_last_step_chkpts_ct)][::-1]
            nonce_limiter_steps_ct              = erlintdec(stream, 16)
            nonce_limiter_steps                 = [stream.read(32) for idx in range(nonce_limiter_steps_ct)][::-1]
            poa2_chunk           = arbindec(stream, 24)
            reward_key           = arbindec(stream, 16)
            poa2_tx_path         = arbindec(stream, 24)
            poa2_data_path       = arbindec(stream, 24)
            price_per_gib_min    = arintdec(stream, 8)
            sched_price_per_gib_min = arintdec(stream, 8)
            reward_history_hash  = stream.read(32)
            debt_supply          = arintdec(stream, 8)
            kryder_plus_rate_mul = erlintdec(stream, 24)
            kryder_plus_rate_mul_latch = erlintdec(stream, 8)
            denom                = erlintdec(stream, 24)
            redenom_height       = arintdec(stream, 8)
            prev_cumulative_diff = arintdec(stream, 16)
            double_signing_proof_flag = erlintdec(stream, 8)
            assert double_signing_proof_flag & 1 == double_signing_proof_flag
            if double_Signing_proof_flag:
                double_signing_proof_key        = stream.read(512)
                double_signing_proof_sig1       = stream.read(512)
                double_signing_proof_cdiff1     = arintdec(stream, 16)
                double_signing_proof_prevcdiff1 = arintdec(stream, 16)
                double_signing_proof_preimage1  = stream.read(64)
                double_signing_proof_sig2       = stream.read(512)
                double_signing_proof_cdiff2     = arintdec(stream, 16)
                double_signing_proof_prevcdiff2 = arintdec(stream, 16)
                double_signing_proof_preimage2  = stream.read(64)

        if height >= FORK_2_7:
            merk_rebase_supp_thresh = arintdec(stream, 16)
            chunk_hash              = stream.read(32)
            chunk2_hash             = arbindec(stream, 8)
            block_time_hist_hash    = stream.read(32)
            nonce_limiter_vdf_difficulty      = arintdec(stream, 8)
            nonce_limiter_next_vdf_difficulty = arintdec(stream, 8)

        if height >= FORK_2_8:
            packing_difficulty   = erlintdec(stream, 8)
            unpacked_chunk_hash  = arbindec(stream, 8)
            unpacked_chunk2_hash = arbindec(stream, 8)
            poa_unpacked_chunk   = arbindec(stream, 24)
            poa2_unpacked_chunk  = arbindec(stream, 24)

        return cls(indep_hash = indep_hash_raw, prev_block = prev_block_raw,
                   timestamp = timestamp, nonce = nonce_raw, height = height,
                   diff = diff, cumulative_diff = cumulative_diff,
                   last_retarget = last_retarget, hash = hash_raw,
                   block_size = block_size, weave_size = weave_size,
                   reward_addr = reward_addr_raw, tx_root = tx_root_raw,
                   wallet_list = wallet_list_raw,
                   hash_list_merkle = hash_list_merkle_raw,
                   reward_pool = reward_pool,
                   packing_threshold = packing_2_5_threshold,
                   strict_chunk_threshold = strict_data_split_threshold,
                   usd_to_ar_rate = usd_to_ar_rate_raw,
                   scheduled_usd_to_ar_rate = scheduled_usd_to_ar_rate_raw,
                   poa_option = poa_option, poa_chunk = poa_chunk_raw,
                   poa_tx_path = poa_tx_path_raw,
                   poa_data_path = poa_data_path_raw,
                   tags = tags, txs = txs)

    def tojson(self):
        return {
            'usd_to_ar_rate': [str(value) for value in self.usd_to_ar_rate_raw],
            'scheduled_usd_to_ar_rate': [str(value) for value in self.scheduled_usd_to_ar_rate_raw],
            'packing_2_5_threshold': str(self.packing_threshold),
            'strict_data_split_threshold': str(self.strict_chunk_threshold),
            'nonce': self.nonce,
            'previous_block': self.prev_block,
            'timestamp': self.timestamp,
            'last_retarget': self.last_retarget,
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
            'poa': {
                'option': str(self.poa_option),
                'tx_path': self.poa_tx_path,
                'data_path': self.poa_data_path,
                'chunk': self.poa_chunk
            }
        }

    def tobytes(self):
        stream = io.BytesIO()
        stream.write(self.indep_hash_raw)
        stream.write(arbinenc(self.prev_block_raw,                  8))
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
        stream.write(arintenc(self.packing_threshold,               8))
        stream.write(arintenc(self.strict_chunk_threshold,          8))
        stream.write(arintenc(self.usd_to_ar_rate_raw[0],           8))
        stream.write(arintenc(self.usd_to_ar_rate_raw[1],           8))
        stream.write(arintenc(self.scheduled_usd_to_ar_rate_raw[0], 8))
        stream.write(arintenc(self.scheduled_usd_to_ar_rate_raw[1], 8))
        stream.write(arintenc(self.poa_option,                      8))
        stream.write(arbinenc(self.poa_chunk_raw,                  24))
        stream.write(arbinenc(self.poa_tx_path_raw,                24))
        stream.write(arbinenc(self.poa_data_path_raw,              24))
        stream.write(len(self.tags).to_bytes(2, 'big'))
        for tag in self.tags:
            stream.write(arbinenc(tag,                             16))
        stream.write(len(self.txs).to_bytes(2, 'big'))
        for tx in self.txs[::-1]:
            if type(tx) is Transaction:
                stream.write(tx.tobytes())
            else:
                stream.write(arbinenc(b64dec(tx),                  24))
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
                self.prev_block_raw,
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
                    str(self.strict_chunk_threshold),
                    *props
                ]
            else:
                props2 = props
            return deep_hash(props2)
        else:
            return deep_hash([
                str(self.height).encode(),
                self.prev_block_raw,
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
                    str(self.poa_option).encode(),
                    self.poa_tx_path,
                    self.poa_data_path,
                    self.poa_chunk
                ]
            ])
    def _encode_tags(self):
        if self.height >= FORK_2_5:
            return 


if __name__ == '__main__':
    def store_block_testdata():
        from .peer import Peer
        peer = Peer()
        blocks = dict(
            BLOCK_GEN_bytes = peer.block2_height(0),
            BLOCK_GEN_json  = peer.block_height (0),
            BLOCK_2_4_bytes = peer.block2_height(FORK_2_4),
            BLOCK_2_4_json  = peer.block_height (FORK_2_4),
            BLOCK_2_5_bytes = peer.block2_height(FORK_2_5),
            BLOCK_2_5_json  = peer.block_height (FORK_2_5),
            BLOCK_2_6_bytes = peer.block2_height(FORK_2_6),
            BLOCK_2_6_json  = peer.block_height (FORK_2_6),
            BLOCK_2_7_bytes = peer.block2_height(FORK_2_7),
            BLOCK_2_7_json  = peer.block_height (FORK_2_7),
        )
        with open('_block_testdata.py', 'wt') as fh:
            for name, val in blocks.items():
                print(f'{name} = {repr(val)}', file=fh)
        return blocks
    from ._block_testdata import *

    assert Block.fromjson(BLOCK_2_5_json).tobytes() == BLOCK_2_5_bytes
    assert Block.frombytes(BLOCK_2_5_bytes).tojson() == BLOCK_2_5_json
