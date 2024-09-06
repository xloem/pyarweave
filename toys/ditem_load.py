# A higher-speed ditem datapusher.

# Copyright (C) 2022, 2023 Chris Calderon
# Copyright (C) 2024 Karl Semich

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse
import hashlib
import io
import json
import os
import sys
import threading
from accelerated_ditem_signing import AcceleratedSigner
import yarl39
import ar, bundlr
import tqdm

#GATEWAY='https://baristestnet.xyz'
GATEWAY='https://arweave.net'

# T_T we made it so near. it could become useful soon :)
class Sender:
    def __init__(self, key, *ditem_header_params, **ditem_header_kwparams):
        self.signing = AcceleratedSigner(ar.DataItem(ar.ANS104DataItemHeader(*ditem_header_params, **ditem_header_kwparams)), key)
        self.signing2 = AcceleratedSigner(ar.DataItem(ar.ANS104DataItemHeader(*ditem_header_params, **ditem_header_kwparams)), key)
        self.headersize = len(self.signing.header(b''))
        bufsize = 102400
        self.payloadsize = bufsize - self.headersize
        self.buf = bytearray(bufsize)
        self.bufview = memoryview(self.buf)
        self.headerview = self.bufview[:self.headersize]
        self.dataview  = self.bufview[self.headersize:]
        node = bundlr.Node()
        def send_tx(transaction_bytes, *params, **kwparams):
            while True:
                try:
                    result = node.send_tx(transaction_bytes, *params, **kwparams)
                except ar.ArweaveNetworkException as e:
                    print(e, file=sys.stderr)
                    if e.args[1] == 201: # already received, but no receipt provided
                        if type(transaction_bytes) is bytes:
                            transaction_bytes = bytearray(transaction_bytes)
                        transaction_bytes[:self.headersize] = self.signing2.header(transaction_bytes[self.headersize:])
                    continue
                else:
                    ## sent, verify it is correct
                    #txid = result['id']
                    #data = ar.Peer().gateway_stream(txid).read()
                    #if data != transaction_bytes[self.headersize:]:
                    #    print('upload did not succeed')
                    #    print('upload did not succeed')
                    #    #import pdb; pdb.set_trace()
                    return result
        self.send_tx = send_tx #bundlr.Node().send_tx
        with tqdm.tqdm(desc='current_block from ' + GATEWAY, leave=False):
            self.min_block = ar.Peer(GATEWAY).current_block()
    def push(self, stream, filesize, *digests):
        signing = self.signing
        headersize = self.headersize
        payloadsize = self.payloadsize
        bufview = self.bufview
        headerview = self.headerview
        dataview = self.dataview
        read = stream.readinto
        remaining_bytes = filesize
        remaining_chunks = (filesize - 1) // payloadsize + 1
        pump = yarl39.SyncThreadPump(
            self.send_tx,
            size_per_period=None,#512*1024*1,#None, # maybe output something if this is not None so user understands there is a speed cap
            period_secs=1,
        )
        feed = pump.feed
        header = signing.header
        #n_hash_updates = len(hash_updates)
        with pump, tqdm.tqdm(total=filesize, unit='B', unit_scale=True, smoothing=0) as pbar:
            while remaining_bytes:
                bytes_read = read(dataview)
                data = dataview[:bytes_read]
                headerview[:] = header(data)
                feed(bytes_read, bufview[:headersize+bytes_read].tobytes())
                [digest.update(data) for digest in digests]
                #for idx in range(n_hash_updates):
                #    hash_updates[idx](data)
                remaining_bytes -= bytes_read
            for result in pump.fetch(remaining_chunks):
                yield result
                pbar.update(min(pbar.n + payloadsize, filesize) - pbar.n)
        with tqdm.tqdm(desc='current_block from ' + GATEWAY, leave=False):
            self.min_block = ar.Peer(GATEWAY).current_block()


def main():
    parser = argparse.ArgumentParser(
        description='Minimal-overhead pushing of a file to bundlr node2.\nReceipts are output in jsonl format on stdout.'
    )
    parser.add_argument(
        'wallet',
        help='Arweave wallet file identifying sender or to create'
    )
    parser.add_argument(
        'file',
        type=argparse.FileType('rb', bufsize=0),
        help='The name of the file to push'
    )
    parser.add_argument(
        '--size',
        type=int,
        help='The size at which to stop reading the file',
    )
    parser.add_argument(
        '--update',
        type=argparse.FileType('r+b', bufsize=0),
        help='A pre-existing ditem_load json to update or fix.',
    )
    args = parser.parse_args()

    if not os.path.exists(args.wallet):
        sys.stderr.write(f'Creating {args.wallet} ...')
        wallet = ar.Wallet.generate(jwk_file = args.wallet)
    else:
        wallet = ar.Wallet(args.wallet)
    stream = args.file
    size = args.size or os.stat(stream.name).st_size
    if args.update:
        import ditem_down_stream
        num_gws = 4
        cachesize = 1024*1024*1024
        conns_per_gw = ar.Peer().max_outgoing_connections // num_gws
        gws = [
            ar.Peer(
                gw,
                outgoing_connections=conns_per_gw,
                requests_per_period=None,
            ) for gw in ar.gateways.GOOD[:num_gws]
        ]
        original = ditem_down_stream.DownStream(gws, args.update, cachesize=cachesize)
        while original.depth > 2:
            with original:
                original = ditem_down_stream.DownStream(gws, original, cachesize=cachesize)
        with original:
            jsondocs = []
            ids = []
            gw_idx = 0
            new_index = io.BytesIO()
            found_difference = False
            bundles = {}
            # so each stream might come from a different gw
            # or we could associate streams with gws
            bundles_lock = threading.Lock()
            def get_ditem_offset(jsondoc, gql_doc):#bundle_id, ditem_id):
                bundle_id = gql_doc['bundledIn']['id']
                ditem_id = gql_doc['id']
                with original.gws.use() as gw:
                    bundle_info = bundles.get(bundle_id)
                    bundle_stream = None
                    if bundle_info is None:
                        with bundles_lock:
                            bundle_info = bundles.get(bundle_id)
                            if bundle_info is None:
                                bundle_offset = gw.tx_offset(bundle_id)
                                # it could be helpful to reuse the stream, but i guess i will try this first
                                #bundle_stream = io.BufferedReader(ar.stream.PeerStream.from_tx_offset(gw, bundle_offset))
                                bundle_stream = ar.stream.GatewayStream.from_txid(gw, bundle_id)
                                with bundle_stream:
                                    bundle_header = ar.bundle.ANS104BundleHeader.fromstream(bundle_stream)
                                bundle_info = [
                                    bundle_offset,
                                    #{
                                    #    gw.api_url: bundle_stream
                                    #},
                                    bundle_header,
                                    #threading.Lock()
                                ]
                                bundles[bundle_id] = bundle_info
                    #bundle_offset, bundle_streams, bundle_header, bundle_lock = bundle_info
                    bundle_offset, bundle_header = bundle_info
                    ditem_start, ditem_end = bundle_header.get_range(ditem_id)
                    #bundle_stream = bundle_streams.get(gw.api_url)
                    #if bundle_stream is None:
                    #    with bundle_lock:
                    #        bundle_stream = bundle_streams.get(gw.api_url)
                    #        if bundle_stream is None:
                    #            bundle_stream = io.BufferedReader(ar.stream.PeerStream.from_tx_offset(gw, bundle_offset))
                    #            bundle_streams[gw.api_url] = bundle_stream
                    #if bundle_stream is None:
                    #    bundle_stream = io.BufferedReader(ar.stream.PeerStream.from_tx_offset(gw, bundle_offset))
                    #bundle_stream.seek(ditem_start)
                    bundle_stream = io.BufferedReader(ar.stream.GatewayStream.from_txid(gw, bundle_id, ditem_start, ditem_end - ditem_start))
                    with bundle_stream:
                        ditem_header = ar.bundle.ANS104DataItemHeader.fromstream(bundle_stream)
                data_start = bundle_stream.tell()
                return [jsondoc, gql_doc, {
                    'tx': bundle_offset,
                    'data': data_start,
                    'head': ditem_start - data_start,
                    'size': ditem_end - data_start,
                }]
            ditem_offset_pump = yarl39.SyncThreadPump(
                get_ditem_offset, size_per_period=None
            )
            with ditem_offset_pump:
                with tqdm.tqdm(desc='indexing', total=original.size, unit='B', unit_scale=True, leave=False) as pbar:
                    while original.offset < original.size:
                        jsonline = original.readline()
                        jsondoc = json.loads(jsonline)
                        jsondocs.append(jsondoc)
                        ids.append(jsondoc['id'])
                        if original.offset == original.size or len(ids) == 100: # cloudfront has a post limit of 20kb but graphql has a result limit of 100 items
                            while True:
                                gql_results = gws[gw_idx].graphql('query{transactions(first:'+str(len(ids))+',ids:'+json.dumps(ids,separators=',:')+'){edges{node{id block{id height}bundledIn{id}}}}}')
                                gql_results = gql_results['data']['transactions']['edges']
                                if gql_results:
                                    break
                                else:
                                    gw_idx += 1
                            assert len(gql_results) == len(ids)
                            gql_docs = {
                                gql_result['node']['id']:gql_result['node']
                                for gql_result in gql_results
                            }
                            for idx in range(len(ids)):
                                gql_doc = gql_docs[ids[idx]]
                                assert gql_doc['id'] == ids[idx]
                                ditem_offset_pump.feed(1,jsondocs[idx],gql_doc)#['bundledIn']['id'], ids[idx])
                            ids = []
                            jsondocs = []
                        pbar.update(original.offset - pbar.n)
                total = ditem_offset_pump.fetch_count()
                for idx, ditem_info in enumerate(tqdm.tqdm(ditem_offset_pump.fetch(total), total=total, desc='looking up ditems', unit='ditem', leave=False)):
                #for idx in tqdm.tqdm(range(len(ids)), desc='looking up', unit='ditem', leave=False):
                    old_doc, gql_doc, ditem_offset = ditem_info
                    #old_doc = jsondocs[idx]
                    #gql_doc = gql_docs[ids[idx]]
                    bundle_id = gql_doc['bundledIn']['id']
                    #bundle_info = bundles.get(bundle_id)
                    #if bundle_info is None:
                    #    bundle_offset = gws[gw_idx].tx_offset(bundle_id)
                    #    bundle_stream = io.BufferedReader(ar.stream.PeerStream.from_tx_offset(gws[gw_idx], bundle_offset))
                    #    bundle_header = ar.bundle.ANS104BundleHeader.fromstream(bundle_stream)
                    #    bundles[bundle_id] = [bundle_offset, bundle_stream, bundle_header]
                    #else:
                    #    bundle_offset, bundle_stream, bundle_header = bundle_info
                    #ditem_start, ditem_end = bundle_header.get_range(ids[idx])
                    #bundle_stream.seek(ditem_start)
                    #ditem_header = ar.bundle.ANS104DataItemHeader.fromstream(bundle_stream)
                    #data_start = bundle_stream.tell()
                    new_doc = {
                        'id': old_doc['id'],
                        'timestamp': old_doc['timestamp'],
                        'name': old_doc['name'],
                        'size': old_doc['size'],
                        **{
                            key: val
                            for key, val in old_doc.items()
                            if key[0] == '_'
                        },
                        'bundle': {
                            'id': gql_doc['bundledIn']['id'],
                            'offset': ditem_offset,
                            #'offset': {
                            #    'tx': bundle_offset,
                            #    'data': data_start,
                            #    'head': ditem_start - data_start,
                            #    'size': ditem_end - data_start,
                            #},
                            'height': gql_doc['block']['height'],
                            'block': gql_doc['block']['id'],
                        },
                        'off': old_doc['off'],
                    }
                    if 'bundle' not in old_doc:
                        # expected condition, update with block and bundle information
                        found_difference = True
                    else:
                        if old_doc == new_doc:
                            # expected condition, doc being updated twice, no changes
                            pass
                        else:
                            # i guess we detected a weavefork?
                            differences = []
                            for key in set(old_doc)|set(new_doc):
                                old_val = old_doc.get(key)
                                new_val = new_doc.get(key)
                                if old_val != new_val:
                                    differences.append(f'{key}:old={old_val} new={new_val}')
                            warnings.warn('weavefork? updated doc differs: ' + ','.join(differences))
                            found_difference = True
                    new_index.write(json.dumps(new_doc,separators=',:').encode('utf-8')+b'\n')
            if not found_difference:
                print('The new index would be identical to the old index.', file=sys.stderr)
        fields = dict(
            name = new_doc['name'],
            size = new_doc['size'],
            depth = 2
        )
        if 'time' in new_doc:
            fields['time'] = new_doc['time']
        assert new_doc['size'] == size
        stream = new_index
        assert len(stream) == stream.tell()
        size = stream.tell()
        stream.seek(0)
    else:
        fields = {
            'name': os.path.basename(stream.name),
            'size': size,
            #'time': int(datetime.datetime.now(datetime.UTC).timestamp())
        }
    sender = Sender(wallet.rsa)
    fields.update({
        'start_height': sender.min_block['height'],
        'start_block': sender.min_block['indep_hash'],
    })
    ct = 2
    while ct > 1:
        digests = {
            '_blake2b': hashlib.blake2b(),
            '_sha256': hashlib.sha256(),
        }
        ct = 0
        nextstream = io.TextIOWrapper(io.BytesIO())
        off = 0
        for result in sender.push(stream, size, *digests.values()):
            result.update(fields)
            result['off'] = off
            off += sender.payloadsize
            json.dump(result, nextstream)
            nextstream.write('\n')
            ct += 1
        nextstream.flush()
        stream = nextstream.buffer
        oldstream = nextstream
        size = stream.tell()
        stream.seek(0)
        fields['depth'] = fields.get('depth',1) + 1
        fields['start_height'] = sender.min_block['height']
        fields['start_block'] = sender.min_block['indep_hash']
        for digest_name, digest_object in digests.items():
            fields[digest_name] = digest_object.hexdigest()
    print(stream.read().decode())

    args.file.close()
    sys.exit(0)


if __name__ == '__main__':
    main()
