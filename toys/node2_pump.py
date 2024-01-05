import concurrent.futures
import threading, queue
import time

import ar
import tqdm

# note: encoding may be cpu-bound

class DeferredProxiedFuture(concurrent.futures.Future):
    def proxy(self, fut):
        fut.add_done_callback(self._proxy_result)
    def _proxy_result(self, fut):
        try:
            self.set_result(fut.result())
        except concurrent.futures.CancelledError:
            self.cancel()
        except Exception as e:
            self.set_exception(e)

class Bisect:
    def __init__(self, node, data, wallet, TOTAL_COUNT):
        self.node = node
        self.data = data
        self.wallet = wallet
        self.lock = threading.Lock()
        self.TOTAL_COUNT = TOTAL_COUNT
    def encode(self):
        self.dataitems = []
        for idx in tqdm.tqdm(range(len(self.data)),total=len(self.data),desc='Encoding',leave=False,unit='di'):
            d = self.data[idx]
            di = ar.DataItem(data=d)
            di.sign(self.wallet.rsa)
            bytes = di.tobytes()   
            self.dataitems.append(bytes)
    def send(self, item):
        result = self.node.send_tx(item)
        with self.lock:
            self.pbar.update(100000)
    def go(self):
        self.encode()
        self.pbar = tqdm.tqdm(total=100000*len(self.data), unit='B', unit_scale=True, smoothing=0)
        with self.pbar, concurrent.futures.ThreadPoolExecutor() as pool:
            mark = time.time() - 1
            for chunk_offset in range(0, self.TOTAL_COUNT, 10):
                results = pool.map(self.send, self.dataitems[chunk_offset:chunk_offset+10])
                results = list(results)
                now = time.time()
                mark += 1
                if now < mark:
                    self.pbar.display(f'sleeping for {mark - now}')
                    time.sleep(mark - now)

class Bisect2:
    def __init__(self, node, wallet, at_once=10, period_secs=1):
        self.node = node
        self.wallet = wallet
        self.at_once = at_once
        self.period_secs = period_secs
        self.queue_bg_in = queue.Queue()
        self.queue_fg = queue.Queue()
        self.queue_bg_out = queue.Queue()
        self.thread = None
    def _encode(self, d):
        di = ar.DataItem(data=d)
        di.sign(self.wallet.rsa)
        return di.tobytes()   
    def feed(self, data):
        for idx in tqdm.tqdm(range(len(data)),total=len(data),desc='Encoding',leave=False,unit='di'):
            fut = DeferredProxiedFuture()
            self.queue_bg_in.put([self._encode(data[idx]), fut])
            self.queue_bg_out.put(fut)
            if self.thread is None:
                self.thread = threading.Thread(target=self._go)
                self.thread.start()
    def fetch(self, ct):
        return (self.queue_bg_out.get().result() for x in range(ct))
    def immed(self, data):
        fut = DeferredProxiedFuture()
        self.queue_fg.put([self._encode(data[idx]), fut])
        return fut.result()
    def _go(self):
        with concurrent.futures.ThreadPoolExecutor() as pool:
            mark = time.time()
            next_mark = mark + self.period_secs
            sys_futs = set()
            tx_count = 0
            while self.queue_bg_in.qsize() or self.queue_fg.qsize():
                try:
                    di, user_fut = self.queue_fg.get_nowait()
                except queue.Empty:
                    di, user_fut = self.queue_bg_in.get_nowait()
                while True:
                    now = time.time()
                    if now > next_mark:
                        tx_count = 0
                        next_mark = now + self.period_secs
                    if tx_count < self.at_once:
                        sys_fut = pool.submit(self.node.send_tx, di)
                        user_fut.proxy(sys_fut)
                        sys_futs.add(sys_fut)
                        tx_count += 1
                        break
                    done, sys_futs = concurrent.futures.wait(
                        sys_futs,
                        timeout=next_mark-now,
                        return_when=concurrent.futures.FIRST_COMPLETED
                    )
            while len(sys_futs):
                done, sys_futs = concurrent.futures.wait(
                    sys_futs,
                    timeout=None,
                    return_when=concurrent.futures.FIRST_COMPLETED
                )
        self.thread = None

class Bisect3(threading.Thread):
    def __init__(self, node, at_once=600, period_secs=60):
        self.node = node
        self.at_once = at_once
        self.period_secs = period_secs
        self.queue_bg_in = queue.Queue()
        self.queue_fg = queue.Queue()
        self.queue_bg_out = queue.Queue()
        self.data_event = threading.Event()
        super().__init__()
    def _encode(self, ditem):
        if isinstance(ditem, ar.DataItem):
            ditem = ditem.tobytes()
        return ditem
    def feed(self, ditem):
        assert self.running
        fut = DeferredProxiedFuture()
        self.queue_bg_in.put([self._encode(ditem), fut])
        self.queue_bg_out.put(fut)
        return fut
    def fetch(self, ct):
        assert self.running or self.queue_bg_out.qsize() >= ct
        return (self.queue_bg_out.get().result() for x in range(ct))
    def immed(self, ditem):
        assert self.running
        fut = DeferredProxiedFuture()
        self.queue_fg.put([self._encode(ditem), fut])
        self.data_event.set()
        return fut.result()
    def run(self):
        with concurrent.futures.ThreadPoolExecutor() as pool:
            mark = time.time()
            next_mark = mark + self.period_secs
            sys_futs = set()
            tx_count = 0
            while True:
                self.data_event.clear()
                if self.queue_fg.qsize():
                    di, user_fut = self.queue_fg.get_nowait()
                elif self.queue_bg_in.qsize():
                    di, user_fut = self.queue_bg_in.get_nowait()
                elif not self.running:
                    break
                else:
                    self.data_event.wait(timeout=0.125)
                    continue
                while True:
                    now = time.time()
                    if now > next_mark:
                        tx_count = 0
                        next_mark = now + self.period_secs
                    if tx_count < self.at_once:
                        sys_fut = pool.submit(self.node.send_tx, di)
                        user_fut.proxy(sys_fut)
                        sys_futs.add(sys_fut)
                        tx_count += 1
                        break
                    done, sys_futs = concurrent.futures.wait(
                        sys_futs,
                        timeout=next_mark-now,
                        return_when=concurrent.futures.FIRST_COMPLETED
                    )
            while len(sys_futs):
                done, sys_futs = concurrent.futures.wait(
                    sys_futs,
                    timeout=None,
                    return_when=concurrent.futures.FIRST_COMPLETED
                )
    def start(self):
        self.running = True
        return super().start()
    def join(self):
        self.running = False
        return super().join()
    def __enter__(self):
        self.start()
        return self
    def __exit__(self, e1, e2, e3):
        self.running = False
        if e1 is None:
            self.join()

class Pump(threading.Thread):
    def __init__(self, node, at_once=10, period_secs=1):
        self.node = node
        self.queue = queue.Queue()
        self.urgent_queue = queue.Queue()
        self.at_once = at_once
        self.period_secs = period_secs
        super().__init__()
    def enqueue(self, dataitem):
        fut = concurrent.futures.Future()
        self.queue.put([dataitem, fut])
        return fut
    def immediate(self, dataitem):
        fut = concurrent.futures.Future()
        self.urgent_queue.put([dataitem, fut])
        return fut.result()
    def run(self):
        self.running = True
        mark = time.time() - self.period_secs
        with concurrent.futures.ThreadPoolExecutor(max_workers = self.at_once) as pool:
            work = []
            while True:
                try:
                    while len(work) < self.at_once:
                        work.append(self.urgent_queue.get_nowait())
                except queue.Empty:
                    pass
                try:
                    while len(work) < self.at_once:
                        work.append(self.queue.get_nowait())
                except queue.Empty:
                    pass
                if not len(work):
                    if not self.running:
                        break
                    try:
                        work.append(self.queue.get(timeout = self.period_secs))
                    except queue.Empty:
                        pass
                    continue
                for result in pool.map(self._work, work):
                    pass
                work = []
                mark += self.period_secs
                now = time.time()
                if mark > now:
                    time.sleep(mark - now)
    def join(self):
        self.running = False
        return super().join()
    def __enter__(self):
        self.start()
        return self
    def __exit__(self, et, ev, etb):
        self.running = False
        if et is None:
            super().join()
    def _work(self, item):
        dataitem, fut = item
        result = self.node.send_tx(dataitem)
        fut.set_result(result)
        #return fut or whatnot
                
    
