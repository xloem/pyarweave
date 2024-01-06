import concurrent.futures
import threading, queue
import time

import ar
import tqdm

# This was made for https://github.com/xloem/flat_tree .
# License is casually GPL i.e. no closed-source derivatives; otherwise
# have at it, relicense to something copyleft, claim you wrote it, etc.

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

class Pump(threading.Thread):
    '''
    A Thread that autostarts when used as a context manager and pumps
    data to a bundlr node in the background, attempting to maximally
    reach a defined number of transactions per period of time.
    
    Ongoing data can be passed to feed() and batches of receipts
    iterated with fetch() in order. Incidental data can be returned
    in a single call to immed() and will be moved toward the top of
    the queue to get a quick result.
    '''
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
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.at_once) as pool:
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
                        next_mark += self.period_secs
                        if now > next_mark:
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
