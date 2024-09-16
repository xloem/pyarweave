import base64, bisect, collections, datetime, hashlib, io, json, math, os, threading, time
import concurrent.futures

import ar
import tqdm

import ditem_load, ditem_down_stream

# general utils
def utctime():
    return datetime.datetime.now(datetime.UTC).timestamp()

# graphql helper
HEIGHT_DESC = 'HEIGHT_DESC'
HEIGHT_ASC = 'HEIGHT_ASC'
EQ = 'EQ'
NEQ = 'NEQ'
def encode_graphql_arguments(obj,key=None,braces='()'):
    if type(obj) in [str, int, float]:
        if key in ['sort','op']:
            return obj
        else:
            return json.dumps(obj)
    elif type(obj) is list:
        return '[' + ','.join([encode_graphql_arguments(val,key+'[]','{}') for val in obj]) + ']'
    elif type(obj) is dict:
        if key == 'tags':
            obj = [dict(
                name = name,
                **{
                    list: {'values':values},
                    str: {'values':[values]},
                    dict: values,
                }[type(values)]
            ) for name, values in obj.items()]
            return encode_graphql_arguments(obj,key)
        else:
            return braces[0] + ','.join(key+':'+encode_graphql_arguments(val,key,'{}') for key, val in obj.items() if val is not None) + braces[1]
    else:
        raise ValueError(type(obj), obj)
#def encode_graphql_queries(obj):
#    if type(obj) is dict:
#        return ' '.join([key + ' ' + encode_graphql_queries(val) for key, val in obj.items()])
#    elif 
#def encode_graphql(field:str, arguments:dict, queries:dict):
#    return 'query{' + ' '.join([
#        field + '(' + encode_graphql_arguments(arguments) + '){' +
#    ])
#def gqlargs(arguments):
#    return encode_graphql_arguments(arguments)
#    #return ','.join(f'{key}:{val if key=="sort" else json.dumps(val)}' for key, val in arguments.items())
def iterate_graphql(peer, field:str, arguments:dict, queries:str, continuing_arguments:dict = None, poll_seconds = 1, poll_instances = 0):
    query = f'''query{{{field}{encode_graphql_arguments(arguments)}{{edges{{cursor node{{{queries}}}}}}}}}'''
    result = peer.graphql(query)['data'][field]['edges']
    yield from [{'cursor':item['cursor'],**item['node']} for item in result]
    if continuing_arguments is not None:
        arguments = continuing_arguments
    while True:
        if len(result):
            cursor = result[-1]['cursor']
            arguments['after'] = cursor
        else:
            if poll_instances <= 0:
                return
            else:
                time.sleep(poll_seconds)
                poll_instances -= 1
        query = f'query{{{field}{encode_graphql_arguments(arguments)}{{edges{{cursor node{{{queries}}}}}}}}}'
        result = peer.graphql(query)['data'][field]['edges']
        yield from [{'cursor':item['cursor'],**item['node']} for item in result]

# sequential data
class Sequence:
    def __init__(self, peers, arguments, wallet = None, bundlr = None, prev_tagname = 'prev', clock_tagname = 'clock', **extra_tags):
        self.peers = peers
        #if type(arguments) is dict:
        #    arguments = ','.join(f'{key}:{val}' for key, val in arguments.items())
        self.arguments = arguments
        self.wallet = wallet
        self.bundlr = bundlr
        self.prev_tagname = prev_tagname
        self.clock_tagname = clock_tagname
        self.extra_tags = extra_tags
        self.latest = dict(id=None,tags=dict(**extra_tags,clock='-1'))
        self.update_latest()
    def iterate(self, _poll_seconds=1, _poll_instances=0, **arguments):
        arguments.setdefault('sort', 'HEIGHT_DESC')
        arguments['tags'] = {**self.arguments.get('tags',{}),**arguments.get('tags',{})}
        #if type(arguments.get('tags')) is dict:
        #    arguments['tags'] = [dict(
        #        name = name,
        #        **{
        #            list: {'values':values},
        #            str: {'values':[values]},
        #            dict: values,
        #        }[type(values)]
        #    ) for name, values in arguments['tags'].items()]
        reverse = -1 if arguments['sort'] == 'HEIGHT_DESC' else 1
        #arguments = ','.join(f'{key}:{val}' for key, val in arguments.items())
        for poll_instances in [0, _poll_instances]:
            block_entries = []
            last = None
            for idx, tx in enumerate(iterate_graphql(
                self.peers[0], 'transactions',
                {**self.arguments, **arguments},
                'id owner{address}tags{name value}block{id height}bundledIn{id}',
                poll_seconds = _poll_seconds,
                poll_instances = poll_instances,
            )):
                tx['tags'] = {tag['name']:tag['value'] for tag in tx['tags']}
                if last and tx['id'] == last['id']:
                    break
                last = tx
                if len(block_entries) and tx['block'] != block_entries[0]['block']:
                    yield from block_entries
                    block_entries.clear()
                bisect.insort(block_entries, tx, key=lambda tx:[
                    reverse * int(tx['tags'][self.clock_tagname]),
                    reverse * int.from_bytes(tx['id'].encode()),
                ])
            yield from block_entries
            arguments['after'] = last and last['cursor']
    def get(self, **arguments):
        for tx in self.iterate(**arguments):
            #print('get', tx)
            return tx
    #def get_enforce_not_multiple(self, **arguments):
    #    tx = None
    #    for _tx in self.iterate(**arguments):
    #        #print('get', tx)
    #        if tx is not None:
    #            raise ValueError('>1 item matched', self, arguments)
    #        tx = _tx
    #    else:
    #        return tx
    def __getitem__(self, clock):
        tx = None
        for _tx in self.iterate(tags={self.clock_tagname:str(clock)}):
            if tx is not None:
                raise ValueError('>1 tx', self.clock_tagname, clock, self)
            tx = _tx
        if tx is None:
            raise KeyError('clock not found', self.clock_tagname, clock, self)
        return tx
    def __len__(self):
        return int(self.latest['tags'][self.clock_tagname]) + 1
    def update_latest(self):
        self.latest = self.get() or self.latest
        return self.latest
    def post(self, data, **post_tags):
        if data is None:
            data = b''
        elif type(data) is str:
            data = data.encode()
        tags = dict(self.extra_tags)
        tags.update(post_tags)
        di = ar.DataItem(data = data)
        assert self.clock_tagname not in tags
        assert self.prev_tagname not in tags
        tags[self.clock_tagname] = str(int(self.latest['tags'][self.clock_tagname]) + 1)
        tags[self.prev_tagname] = self.latest['id']
        di.header.tags = [
            {'name':key,'value':val}
            for key, val in tags.items()
        ]
        di.sign(self.wallet.rsa)
        result = self.bundlr.send_tx(di.tobytes())
        tx = dict(
            id = result['id'],
            owner = dict(address=self.wallet.address),
            tags = tags
        )
        self.latest = tx
        #print('sent', self.latest, result)
        #    # what about race conditions locking
        return tx

# simple network-shared lock, where access is controlled by ability to post to a sequence
class Lock:
    def __init__(self, sequence, action_tagname = 'lock', locking_action = 'locking', locked_action = 'lock', unlock_action = 'unlock', locking_tagname = 'locking', expected_completion_time_tagname = 'poll', expiry_timeout_tagname = 'expire'):
        self.seq = sequence
        self.action_tagname = action_tagname
        self.locking_action = locking_action
        self.locked_action = locked_action
        self.unlock_action = unlock_action
        self.locking_tagname = locking_tagname
        self.expected_completion_time_tagname = expected_completion_time_tagname
        self.expiry_timeout_tagname = expiry_timeout_tagname
        self._lock_tx = None

    # yields txs that presently hold this lock
    # or empty sequence if the lock is open
    def query_iterate(self, now=None, _poll_seconds=1, _poll_instances=0, **arguments):
        if now is None:
            now = utctime()
        assert 'sort' not in arguments # didn't see a need for this at the time
        argtags = arguments.pop('tags',{})
        lock = self.seq.get(
            tags = { **argtags,
                self.action_tagname: [self.locked_action, self.unlock_action],
            },
            sort = 'HEIGHT_DESC',
        )
        if lock and lock['tags'][self.action_tagname] == self.locked_action:
            if float(lock['tags'][self.expiry_timeout_tagname]) >= now:
                yield lock # anything else is queued after it
        #last_clock=-1
        locking = []
        last_txid = lock and lock['tags'][self.locking_tagname]
        # i didn't see a way within graphql to iterate txs starting with
        # a given one, so this iterates in reverse, then reverses the result,
        # as a solution without too many conditions to handle
        while True:
            for tx in self.seq.iterate(
                tags = { **argtags, self.action_tagname: [self.locking_action] },
                sort = 'HEIGHT_DESC', **arguments,
            ):
                if last_txid is not None and tx['id'] == last_txid:
                    break
                if float(tx['tags'][self.expiry_timeout_tagname]) >= now:
                    locking.append(tx)
            locking.reverse()
            yield from locking
            if not _poll_instances:
                break
            if len(locking):
                last_txid = locking[-1]['id']
                locking.clear()
            _poll_instances -= 1
            time.sleep(_poll_seconds)
    # returns a list of txs that presently hold this lock
    # or empty list if the lock is open
    def query(self, now=None, **arguments):
        return list(self.query_iterate(now, **arguments))

    def lock(self, poll_time, expected_completion_time, expiry_timeout_time, **tags):
        now = utctime()
        start = now
        timeout = start + expiry_timeout_time

        assert self.action_tagname not in tags
        assert self.expected_completion_time_tagname not in tags
        assert self.expiry_timeout_tagname not in tags
        assert self.locking_tagname not in tags

        # prepare to lock by advertising we are waiting
        self._locking_tx = self.seq.post(None, **{
            **tags,
            self.action_tagname: self.locking_action,
            self.expected_completion_time_tagname: str(poll_time),
            self.expiry_timeout_tagname: str(timeout),
        })

        # here we have to wait for it to be our turn to lock it
        with tqdm.tqdm(desc='lock',unit='s',leave=False) as pbar:
            while True:
                holder = next(self.query_iterate(
                    now, # this is intended to always let our transaction through, via the timeout catch in the next condition below
                    _poll_seconds = min(poll_time,1),
                    _poll_instances = math.inf
                ))
                now = utctime()
                if now >= timeout + expected_completion_time + 1:
                    raise KeyError('timeout waiting for lock')
                if holder['id'] == self._locking_tx['id']:
                    # it is now officially our turn to take the lock, until timeout
                    break
                pbar.total = float(holder['tags'][self.expiry_timeout_tagname]) - start
                pbar.set_description('waiting for ' + holder['id'], False)
                pbar.update(now - start - pbar.n)
                #print('waiting for', holder, 'now =', now, end='\r', flush=True)
                time.sleep(min(
                    float(holder['tags'][self.expected_completion_time_tagname]),
                    max(0,float(holder['tags'][self.expiry_timeout_tagname]) - now)
                ))

        # it is now officially our turn to take the lock, until timeout

        now = utctime()
        if now >= timeout + expected_completion_time + 1:
            raise KeyError('timeout waiting for lock')

        self.timeout = timeout
        self._lock_tx = self.seq.post(None, **{
            **tags,
            self.action_tagname: self.locked_action,
            self.expected_completion_time_tagname: str(expected_completion_time),
            self.expiry_timeout_tagname: str(timeout),
            self.locking_tagname: self._locking_tx['id'],
        })
        
#        # post lock with timeout, if free
#            # basically the contract is, after the timeout, you no longer have the lock. this is to clear up what to do if you don't unlock due to crash.
#            # since network posts are involved, this means your data needs ot be public before the timeout passed, to be within the lock, i guess!
#            # if you can figure out the maximum delay, i guess that would help too
#            # but maybe you could just set the timoeut to like an hour i guess
#
#                # thinking a litle on notifying
#                # maybe an expected poll time would help to share too
    def keepalive(self, expiry_timeout_time, expected_completion_time = None, post_seconds = 5, **tags):
        timeout = utctime() + expiry_timeout_time
        self.use(post_seconds)
        assert self._lock_tx['id']
        self._lock_tx = self.seq.post(None, **{
            **tags,
            self.action_tagname: self.locked_action,
            self.expected_completion_time_tagname:
                self._lock_tx['tags'][self.expected_completion_time_tagname]
                    if expected_completion_time is None
                    else str(expected_completion_time),
            self.expiry_timeout_tagname: str(timeout),
            self.locking_tagname: self._locking_tx['id'],
        })
    def use(self, seconds = 1):
        if self._lock_tx is None or self._lock_tx['tags'][self.action_tagname] != self.locked_action:
            # not in a locked context
            raise KeyError('lock used without being held')
        if utctime() + seconds >= float(self._lock_tx['tags'][self.expiry_timeout_tagname]):
            # lost lock
            #return self.lock()
            # raise if timeout has passed
            raise KeyError('lock timed out while locked')
    def unlock(self, post_seconds = 5):
        # unlock posted lock
        assert self._lock_tx['tags'][self.action_tagname] == self.locked_action
        self.use(post_seconds)
        tags = dict(self._lock_tx['tags'])
        tags.pop(self.seq.prev_tagname)
        tags.pop(self.seq.clock_tagname)
        tags.pop(self.expected_completion_time_tagname)
        tags.pop(self.expiry_timeout_tagname)
        self._lock_tx = self.seq.post(None, **{
            **tags,
            self.action_tagname: self.unlock_action,
            self.locking_tagname: self._locking_tx['id']
        })

class DataResource:
    def __init__(self, wallet_or_address, peers = None, bundlrnode = None, poll_time = 0.2, expected_completion_time = 1, timeout = 60):
        bundlr = bundlrnode
        if peers is None:
            peers = 8
        if type(peers) is int:
            num_gws = peers
            conns_per_gw = ar.Peer().max_outgoing_connections // num_gws
            peers = [ar.Peer(url,outgoing_connections=conns_per_gw,requests_per_period=None) for url in ar.PUBLIC_GATEWAYS[:num_gws]]
        # is it a representation of a wallet?
        if type(wallet_or_address) is ar.Wallet:
            # yes it's a wallet
            wallet = wallet_or_address
        if type(wallet_or_address) is dict:
            # yes it's data
            wallet = ar.Wallet(jwk_data=wallet_or_address)
        elif type(wallet_or_address) is str:
            try:
                # yes it's a file
                wallet = ar.Wallet(jwk_file=wallet_or_address)
            except:
                # no. is it a representation of an address?
                try:
                    assert len(ar.utils.b64dec(wallet_or_address)) == 32
                except:
                    # no, treat it is a new file
                    wallet = ar.Wallet.generate(jwk_file=wallet_or_address)
                else:
                    # yes, be readonly.
                    wallet = None
                    address = wallet_or_address
        if wallet is not None:
            if bundlr is None:
                import bundlr
                bundlr = bundlr.Node()
            address = wallet.address
        self.seq = Sequence(peers, dict(owners=[address],tags=dict(seq='data')), wallet, bundlr, seq='data')
        self.seq_lock = threading.Lock()
        self.lock = Lock(Sequence(peers, dict(owners=[address],tags=dict(seq='lock')), wallet, bundlr, seq='lock'))
        self.lock_params = dict(
            poll_time = poll_time,
            expected_completion_time = expected_completion_time,
            expiry_timeout_time = timeout
        )
        self._post_queue = collections.deque()
        self._post_time = 0
    def store(self, data, **tags):
        if type(data) is str:
            data = data.encode()
        if type(data) is bytes:
            size = len(data)
            data = io.BytesIO(data)
        else:
            size = os.stat(data.name).st_size
        self.lock.use(self._post_time)
        can_post_event = threading.Event()
        with self.seq_lock:
            if len(self._post_queue) == 0:
                can_post_event.set()
            self._post_queue.append(can_post_event)
        fut = self.pool.submit(self._store, can_post_event, data, size, tags)
        def fut_done(fut):
            with self.seq_lock:
                assert self._post_queue[0] is can_post_event
                assert self._post_queue.popleft() is can_post_event
                fut.result() # raise exception if one happened
                if len(self._post_queue):
                    self._post_queue[0].set()
        fut.add_done_callback(fut_done)
        return fut
    def __enter__(self):
        self.lock.lock(**self.lock_params)
        with self._update_post_time():
            self.seq.update_latest()
        self.pool = concurrent.futures.ThreadPoolExecutor()
        self.pool.__enter__()
        return self
    def keepalive(self):
        lock_params = dict(self.lock_params)
        lock_params.pop('poll_time')
        self.lock.keepalive(**lock_params,
            post_seconds=self._post_time,
        )
    def __exit__(self, *params):
        self.pool.__exit__(*params)
        self.lock.unlock(post_seconds=self._post_time)
    def __getitem__(self, clock):
        return self._get(self.seq[clock])
    def __len__(self):
        return len(self.seq)
    def latest(self, **tags):
        return self._get(self.seq.latest)

    def _update_post_time(self):
        now = utctime()
        class Ctx:
            def __enter__(ctx):
                return self
            def __exit__(ctx, *params):
                duration = utctime() - now
                if duration > self._post_time:
                    self._post_time = duration
        return Ctx()
    def _get(self, tx):
        if tx is None or tx['id'] is None:
            return None
        try:
            tx_stream = self.seq.peers[0].gateway_stream(tx['id']) # self.seq.peer.data
        except ar.ArweaveNetworkException as exc:
            if exc.args[1] == 404: # sent to private graphql endpoint but not processed yet
                tx_stream = self.seq.bundlr.stream(tx['id'])
            else:
                raise
        tx['stream'] = ditem_down_stream.DownStream(self.seq.peers, tx_stream, cachesize=1024*1024*1024, bundlrs=[self.seq.bundlr]).expand()
        return tx
    def _store(self, can_post_event, stream, size, tags):
        tags_dict = tags
        tags = [dict(name='seq',value='ditem')] + [dict(name=name,value=value) for name, value in tags.items()]
        sender = ditem_load.Sender(self.seq.wallet.rsa, tags=tags)
        fields = dict(
            size = size,
            name = self.seq.wallet.address + ':' + self.seq.latest['tags']['clock']
        )
        ct = 2
        while ct > 1:
            digests = dict(_blake2b = hashlib.blake2b(),_sha256=hashlib.sha256())
            ct = 0
            nextstream = io.TextIOWrapper(io.BytesIO())
            off = 0
            fields['start_height'] = sender.min_block['height']
            fields['start_block'] = sender.min_block['indep_hash']
            for result in sender.push(stream, size, *digests.values()):
                result.update(fields)
                result['off'] = off
                off += sender.payloadsize
                json.dump(result, nextstream)
                nextstream.write('\n')
                ct += 1
            nextstream.flush()
            stream = nextstream.detach()
            size = stream.tell()
            stream.seek(0)
            fields['depth'] = fields.get('depth',1) + 1
            for digest_name, digest_object in digests.items():
                fields[digest_name] = digest_object.hexdigest()
        self.lock.use(self._post_time)
        #post_fut.set_result([stream.read(), **tags_dict])
        #posted_condition.wait_for(lambda: self._post_queue[0] is posted_condition)

        #while True:
        #    with self.seq_lock:
        #        next_posted = self._post_queue[0]
        #    if next_posted is posted_event:
        #        break
        #    else:
        #        next_posted.wait()

        can_post_event.wait()
        #print('got can post event', can_post_event)
        with self._update_post_time():
            self.lock.use(self._post_time)
            result = self.seq.post(stream.read(), **tags_dict)
        #print('posted', can_post_event, result['id'])
        return result

#
#    # we could optionally implement a network lock here for multiprocess synchronisation.
#    # it would use the iteration to find the latest lock tag.
#    # it could steal the lock after a timeout, i suppose.

if __name__ == '__main__':
    dr = DataResource('test.json')
    latest = dr.latest()
    if latest is not None:
        print(latest)
        with latest['stream'] as stream:
            print(stream.read())
    with dr:
        one = dr.store('Hello world-1', tagname='tagvalue')
        print(one.result())
        two = dr.store('Hello world-2', tagname='tagvalue')
        dr.keepalive()
        three = dr.store('Hello world-3', tagname='tagvalue')
    latest = dr.latest()
    with latest['stream'] as stream:
        print(latest)
        print(stream.read())
    for idx in range(len(dr)-1,-1,-1):
        print(idx, dr[idx])
        with dr[idx]['stream'] as stream:
            print(stream.read())
    #print(dr.update_latest())
