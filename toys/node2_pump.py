import concurrent.futures
import threading, queue
import time

# note: encoding may be cpu-bound

class InsertableRateQueueIterable:
    def __init__(self, at_once=10, period_secs=1):
        self.at_once = at_once
        self.period_secs = period_secs
        self.queue = queue.Queue()
        self.insertions = queue.Queue()
    def add(self, item):
        self.queue.put(item)
    def insert(self, item):
        self.inserts.put(item)
    def __iter__(self):
        mark = time.time() - self.period_secs
        ct = 0
        while True:
            for ct in range(self.at_once):
                if self.insertions.qsize():
                    yield self.insertions.get()
                elif self.queue.qsize():
                    yield self.queue.get()
                else:
                    return
            now = time.time()
            mark += self.period_secs
            if now < mark:
                time.sleep(mark - now)

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
                
    
