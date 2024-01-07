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
import io
import sys
import os
import json
from accelerated_ditem_signing import AcceleratedSigner
import yarl39
import ar, bundlr
import tqdm

# T_T we made it so near. it could become useful soon :)
class Sender:
    def __init__(self, key):
        self.signing = AcceleratedSigner(ar.DataItem(), key)
        self.headersize = len(self.signing.header(b''))
        bufsize = 102400
        self.payloadsize = bufsize - self.headersize
        self.buf = bytearray(bufsize)
        self.bufview = memoryview(self.buf)
        self.headerview = self.bufview[:self.headersize]
        self.dataview  = self.bufview[self.headersize:]
        self.send_tx = bundlr.Node().send_tx
    def push(self, stream, filesize):
        self.min_block = ar.Peer().current_block()
        signing = self.signing
        headersize = self.headersize
        payloadsize = self.payloadsize
        bufview = self.bufview
        headerview = self.headerview
        dataview = self.dataview
        read = stream.readinto
        remaining_bytes = filesize
        remaining_chunks = (filesize - 1) // payloadsize + 1
        pump = yarl39.SyncThreadPump(self.send_tx, size_per_period=None, period_secs=60)
        feed = pump.feed
        header = signing.header
        #n_hash_updates = len(hash_updates)
        with pump, tqdm.tqdm(total=filesize, unit='B', unit_scale=True, smoothing=0) as pbar:
            while remaining_bytes:
                bytes_read = read(dataview)
                data = dataview[:bytes_read]
                headerview[:] = header(data)
                feed(bytes_read, bufview[:headersize+bytes_read].tobytes())
                #for idx in range(n_hash_updates):
                #    hash_updates[idx](data)
                remaining_bytes -= bytes_read
            for result in pump.fetch(remaining_chunks):
                yield result
                pbar.update(min(pbar.n + payloadsize, filesize) - pbar.n)


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
    args = parser.parse_args()

    if not os.path.exists(args.wallet):
        sys.stderr.write(f'Creating {args.wallet} ...')
        wallet = ar.Wallet.generate(jwk_file = args.wallet)
    else:
        wallet = ar.Wallet(args.wallet)
    stream = args.file
    size = os.stat(stream.name).st_size
    ct = 2
    sender = Sender(wallet.rsa)
    fields = {
        'name': os.path.basename(stream.name),
        'size': size,
    }
    fields['name'] = os.path.basename(stream.name)
    while ct > 1:
        ct = 0
        nextstream = io.TextIOWrapper(io.BytesIO())
        for result in sender.push(stream, size):
            result.update(fields)
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
    print(stream.read().decode())

    args.file.close()
    sys.exit(0)


if __name__ == '__main__':
    main()
