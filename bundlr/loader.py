from ar import DataItem, ANS104BundleHeader, ANS104DataItemHeader, logger
from ar.utils import create_tag, normalize_tag, get_tags

import threading

class Loader:
    def __init__(self, node, gateway, peer, wallet):
        self.node = node
        self.gateway = gateway
        self.peer = peer
        self.wallet = wallet

    def __getattr__(self, attr):
        return getattr(self.peer, attr)

    def graphql(self, *params, **kwparams):
        return self.gateway.graphql(*params, **kwparams)

    def send(self, data, tags):
        di = DataItem(data = data)
        if type(tags) is dict:
            di.header.tags = [create_tag(name, value, 2) for name, value in tags.items()]
        else:
            di.header.tags = [normalize_tag(tag) for tag in tags]
        di.sign(self.wallet.rsa)
        result = self.node.send_tx(di.tobytes())
        return result['id']

    # this applies to general bundles and could be part of an ans104-associated base class
    def data(self, txid, bundleid = None, blockid = None):
        if bundleid is not None:
            tags = self.gateway.tx_tags(bundleid)
            stream = self.gateway.stream(bundleid)
            header = ANS104BundleHeader.from_tags_stream(tags, stream)
            offset, end = header.get_range(txid)
            stream.seek(offset)
            dataitem = DataItem.fromstream(stream, length = end - offset)
            data = dataitem.data
        else:
            data = self.gateway.data(txid)
        logger.warning(f'{txid} was not verified') # check the hash tree
        return data
    def tags(self, txid, bundleid = None, blockid = None):
        if bundleid is not None:
            tags = self.gateway.tx_tags(bundleid)
            stream = self.gateway.stream(bundleid)
            if b'json' in get_tags(tags, b'Bundle-Format'):
                bundle = Bundle.from_tags_stream(tags, stream)
                tags = None
                for dataitem in bundle.dataitems:
                    if dataitem.id == txid:
                        tags = dataitem.tags
                        break
            else:
                header = ANS104BundleHeader.from_tags_stream(tags, stream)
                offset = header.get_offset(txid)
                stream.seek(offset)
                dataitem = ANS104DataItemHeader.fromstream(stream)
                tags = dataitem.tags
        else:
            tags = self.gateway.tx_tags(bundleid)
        logger.warning(f'{txid} was not verified') # check the hash tree
        return tags



