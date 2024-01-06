#!/usr/bin/env python3

print()
print('Bundlr node2 can theoretically provide free uploads at a rate of 1MB/s,')
print(' if they are blocked into 100kb transactions and limited to 600/min.')
print()
print('Can we accomplish this speed?')

import os, random, time
import tqdm
import concurrent.futures, threading, multiprocessing.pool, joblib
from ar import Peer, Wallet, DataItem
from bundlr import Node
import toys.node2_pump

di_header_size = len(DataItem(data=b'').tobytes())
raw_size = 100*1024
payload_size = raw_size - di_header_size
print(f'Raw size: {raw_size}B')
print(f'Payload size: {payload_size}B')
TOTAL_COUNT = 1200

print('Prepping data ...')

wallet = (
    Wallet('testwallet.json')
    if os.path.exists('testwallet.json')
    else Wallet.generate(jwk_file='testwallet.json')
)

with open('testdata.bin', 'ab+') as f:
    if f.tell() < TOTAL_COUNT*payload_size:
        f.write(random.randbytes(TOTAL_COUNT*payload_size-f.tell()))
    f.seek(0)
    data = [f.read(payload_size) for idx in tqdm.tqdm(range(TOTAL_COUNT),total=TOTAL_COUNT,desc='Reading',leave=False,unit='blk')]

def encode():
    global dataitems
    dataitems = []
    for idx in tqdm.tqdm(range(len(data)),total=len(data),desc='Encoding',leave=False,unit='di'):
        d = data[idx]
        di = DataItem(data=d)
        di.sign(wallet.rsa)
        bytes = di.tobytes()   
        assert len(bytes) == raw_size and len(di.data) == payload_size
        dataitems.append(bytes)

node = Node()

#print('joblib ...')
#encode()
#mark = time.time() - 1
#expected_sent = 0
#def send(di):
#    node = Node()
#    return node.send_tx(di)
#    #pbar.update(len(di))
#    #return 
#with tqdm.tqdm(total=100000*TOTAL_COUNT, unit='B', unit_scale=True, smoothing=0) as pbar, multiprocessing.pool.ThreadPool() as pool:
#    for chunk_offset in range(0, TOTAL_COUNT, 10):
#        results = joblib.Parallel(n_jobs=10)(joblib.delayed(send)(di) for di in dataitems[chunk_offset:chunk_offset+10])
#        pbar.update(10*100000)
#        #expected_sent += 10 * 100000
#        #assert pbar.n == expected_sent
#        now = time.time()
#        mark += 1
#        if now < mark:
#            pbar.display(f'sleeping for {mark - now}')
#            time.sleep(mark - now)

'''
print('toys/node2_pump InsertableQueue with ThreadPoolExecutor')
encode()
queue = toys.node2_pump.InsertableRateQueueIterable(at_once=10, period_secs=1)
for di in dataitems:
    queue.add(di)
with tqdm.tqdm(total=100000*TOTAL_COUNT, unit='B', unit_scale=True, smoothing=0) as pbar, concurrent.futures.ThreadPoolExecutor() as pool:
    for result in pool.map(node.send_tx, queue):
        pbar.update(100000)
'''

print('toys.node2_pump.Pump ...')
with toys.node2_pump.Pump(node, at_once=10, period_secs=1) as pump:
    with tqdm.tqdm(total=100000*len(data), unit='B', unit_scale=True, smoothing=0) as pbar:
        for idx in tqdm.tqdm(range(len(data)),total=len(data),desc='Encoding',leave=False,unit='di'):
            di = DataItem(data=data[idx])
            di.sign(wallet.rsa)
            pump.feed(di)
        for result in pump.fetch(len(data)):
            pbar.update(100000)

print('concurrent.futures.ThreadPoolExecutor ...')
encode()
mark = time.time() - 1
lock = threading.Lock()
expected_sent = 0
def send(di):
    result = node.send_tx(di)
    with lock:
        pbar.update(100000)#len(di))
    return result
with tqdm.tqdm(total=100000*TOTAL_COUNT, unit='B', unit_scale=True, smoothing=0) as pbar, concurrent.futures.ThreadPoolExecutor() as pool:
    for chunk_offset in range(0, TOTAL_COUNT, 10):
        results = pool.map(send, dataitems[chunk_offset:chunk_offset+10])
        results = list(results) # enumerates generator
        expected_sent += 10 * 100000
        assert pbar.n == expected_sent
        now = time.time()
        mark += 1
        if now < mark:
            pbar.display(f'sleeping for {mark - now}')
            time.sleep(mark - now)

print('multiprocessing.pool.ThreadPool ...')
encode()
mark = time.time() - 1
lock = multiprocessing.Lock()
expected_sent = 0
def send(di):
    result = node.send_tx(di)
    with lock:
        pbar.update(100000)#len(di))
    return result
with tqdm.tqdm(total=100000*TOTAL_COUNT, unit='B', unit_scale=True, smoothing=0) as pbar, multiprocessing.pool.ThreadPool() as pool:
    for chunk_offset in range(0, TOTAL_COUNT, 10):
        results = pool.map(send, dataitems[chunk_offset:chunk_offset+10])
        expected_sent += 10 * 100000
        assert pbar.n == expected_sent
        now = time.time()
        mark += 1
        if now < mark:
            pbar.display(f'sleeping for {mark - now}')
            time.sleep(mark - now)

print('single-threaded serial sends ...')
encode()
mark = time.time() - 1
expected_sent = 0
def send(di):
    node.send_tx(di)
    pbar.update(100000)#len(di))
with tqdm.tqdm(total=100000*TOTAL_COUNT, unit='B', unit_scale=True, smoothing=0) as pbar, multiprocessing.pool.ThreadPool() as pool:
    for chunk_offset in range(0, TOTAL_COUNT, 10):
        results = [send(di) for di in dataitems[chunk_offset:chunk_offset+10]]
        expected_sent += 10 * 100000
        assert pbar.n == expected_sent
        now = time.time()
        mark += 1
        if now < mark:
            pbar.display(f'sleeping for {mark - now}')
            time.sleep(mark - now)
