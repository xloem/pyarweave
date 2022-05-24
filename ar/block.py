import fractions
import io
from ar.utils import (
    arbinenc, arintenc, arbindec, arintdec, erlintenc, erlintdec, b64enc_if_not_str, b64enc, b64dec
)

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
            return setup().__getattr__(attr)

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
            for key, value in kwparams.pop('poa').items()
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
        return cls.fromstream(stream)
            
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
        usd_to_ar_rate_raw           =(arintdec(stream,  8),
                                       arintdec(stream,  8))
        scheduled_usd_to_ar_rate_raw =(arintdec(stream,  8),
                                       arintdec(stream,  8))
        poa_option                   = arintdec(stream,  8)
        poa_chunk_raw                = arbindec(stream, 24)
        poa_tx_path_raw              = arbindec(stream, 24)
        poa_data_path_raw            = arbindec(stream, 24)

        tags_count = erlintdec(stream, 16)
        tags       = [arbindec(stream, 16) for idx in range(tags_count)]

        # either 32-byte txids or complete txs
        txs_count = erlintdec(stream, 16)
        txs_raw = [arbindec(stream, 24) for idx in range(txs_count)]
        txs = [b64enc(tx) for tx in txs_raw[::-1]]

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
            'txs': self.txs,
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
        stream.write(erlintenc(len(self.tags), 16))
        for tag in self.tags:
            stream.write(arbinenc(tag,                             16))
        stream.write(erlintenc(len(self.txs), 16))
        for tx in self.txs[::-1]:
            stream.write(arbinenc(b64dec(tx),                      24))
        return stream.getvalue()
