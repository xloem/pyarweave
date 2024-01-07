import concurrent.futures
import threading, queue
import time
import logging
logger = logging.getLogger(__name__)

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
    reach a defined number of bytes per period of time.

    This class has been updated to work in terms of bytes rather
    than transactions, which seems to better reflect real-world
    conditions.
    
    Ongoing data can be passed to feed() and batches of receipts
    iterated with fetch() in order. Incidental data can be returned
    in a single call to immed() and will be moved toward the top of
    the queue to get a quick result.

    The default parameters were those listed in the bundler developer
    Discord FAQ in January 2024, and provide for speeds of 1MB/s.
    Passing None for bytes_per_period will maintain a running
    measurement of capacity.
    '''
    def __init__(self, node, bytes_per_period=600*102400, period_secs=60):
        self.node = node
        self.period_bytes_limit = bytes_per_period
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
        period_bytes_limit = self.period_bytes_limit
        period_bytes_best = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=128) as pool:
            mark_send = time.time()
            mark_send_next = mark_send + self.period_secs
            mark_recv = None
            mark_recv_next = None
            sys_futs = set()
            period_bytes_sent = 0
            period_bytes_returned = 0
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
                now = time.time()
                if period_bytes_limit is not None and period_bytes_sent >= period_bytes_limit and mark_send_next > now:
                    time.sleep(mark_send_next - now)
                    now = mark_send_next
                if now >= mark_send_next:
                    period_bytes_sent = 0
                    mark_send_next += self.period_secs
                    if now > mark_send_next:
                        mark_send_next = now + self.period_secs
                period_bytes_sent += len(di)
                sys_fut = pool.submit(self.node.send_tx, di)
                sys_fut.size = len(di)
                sys_fut.time = now
                user_fut.proxy(sys_fut)
                sys_futs.add(sys_fut)
                done, sys_futs = concurrent.futures.wait(
                    sys_futs,
                    timeout=0,
                    return_when=concurrent.futures.FIRST_COMPLETED
                )
                if done:
                    if mark_recv is None:
                        mark_recv = min([fut.time for fut in done])
                        mark_recv_next = mark_recv + self.period_secs
                    while True:
                        done_next_period = set([fut for fut in done if fut.time >= mark_recv_next])
                        done_this_period = done - done_next_period
                        period_bytes_returned += sum([fut.size for fut in done_this_period])

                        if not done_next_period:
                            break
                        
                        if period_bytes_returned > period_bytes_best:
                            period_bytes_best = period_bytes_returned
                            if self.period_bytes_limit is None:
                                # whatever we actually send is the max bandwidth
                                period_bytes_limit = period_bytes_best
                            elif period_bytes_best < self.period_bytes_limit:
                                import inspect
                                logger.warn(inspect.cleandoc(f'''-v
                                    Measured bytes_per_period underperforms passed bytes_per_period;
                                    this will slow behavior from backpressure if it persists.
                                    Pass None to simply use measured value.
                                    measured={period_bytes_best}/{self.period_secs}
                                    passed={self.period_bytes_limit}/{self.period_secs}
                                '''))

                        mark_recv = mark_recv_next
                        mark_recv_next += self.period_secs
                        done = done_next_period
                        period_bytes_returned = 0
                    
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
