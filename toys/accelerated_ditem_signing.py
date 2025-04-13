import cryptography.hazmat.primitives.serialization
import cryptography.hazmat.primitives.asymmetric.padding
import hashlib

AR_DIGEST = cryptography.hazmat.primitives.hashes.SHA256()
AR_PADDING = cryptography.hazmat.primitives.asymmetric.padding.PSS(
    cryptography.hazmat.primitives.asymmetric.padding.MGF1(AR_DIGEST),
    512 - 32 - 2
)

def AcceleratedSigner(ditem, key):
    '''
    Returns an object for quickly re-encoding many ditems with the same
    metadata but different payloads.
    '''
    assert ditem.header.signature_type == 1 # arweave
    ditem = type(ditem).frombytes(ditem.tobytes())
    ditem.data = b''
    ditem.sign(key)
    key = cryptography.hazmat.primitives.serialization.load_pem_private_key(key.export_key(),password=None)
    partial_signing_data = ditem.get_raw_signature_data(include_data = False)
    template = ditem.tobytes()
    example_sig = ditem.header.raw_signature
    sig_offset = template.find(example_sig)
    while sig_offset != template.rfind(example_sig):
        ditem.sign(key)
        template = ditem.tobytes()
        sig_offset = template.find(example_sig)
    sig_end = sig_offset + len(example_sig)
    del ditem
    del example_sig
    deephash_digest = hashlib.sha384
    def instance():
        '''
        Clone this object for use in other threads.
        '''
        template_ = bytearray(template)
        class AcceleratedSigner:
            def header(data):
                '''
                Produce a raw signed header that will verify if suffixed with the passed data.
                Buffer is reused, so call .instance() to clone for other threads.
                '''
                acc = partial_signing_data
                chunk = data
                tag_hash = deephash_digest(b'blob' + str(len(chunk)).encode()).digest()
                data_hash = deephash_digest(chunk).digest()
                hash_pair = acc + deephash_digest(tag_hash + data_hash).digest()
                signing_data = deephash_digest(hash_pair).digest()
                template_[sig_offset:sig_end] = key.sign(signing_data, AR_PADDING, AR_DIGEST)
                return template_
            def signature_range():
                return [sig_offset, sig_end]
            clone = instance
        return AcceleratedSigner
    return instance()

    return acc

if __name__ == '__main__':
    import ar
    key = ar.Wallet.generate().rsa
    ditem = ar.DataItem(data=b'hello world')
    signer = AcceleratedSigner(ditem, key)
    accelerated = signer.header(ditem.data) + b'hello world'
    ditem.sign(key)
    accelerated = ar.DataItem.frombytes(accelerated)
    assert ditem.verify()
    assert accelerated.verify()
    ditem.header.raw_signature = accelerated.header.raw_signature
    assert ditem.tobytes() == accelerated.tobytes()
