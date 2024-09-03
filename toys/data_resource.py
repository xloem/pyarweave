import base64, bisect, datetime, json, math, time

import ar
import tqdm

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
        return '[' + ','.join([encode_graphql_arguments(val,key,'{}') for val in obj]) + ']'
    elif type(obj) is dict:
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
    def __init__(self, peer, arguments, wallet = None, bundlr = None, prev_tagname = 'prev', clock_tagname = 'clock'):
        self.peer = peer
        #if type(arguments) is dict:
        #    arguments = ','.join(f'{key}:{val}' for key, val in arguments.items())
        self.arguments = arguments
        self.wallet = wallet
        self.bundlr = bundlr
        self.prev_tagname = prev_tagname
        self.clock_tagname = clock_tagname
        self.latest = dict(id=None,tags=dict(clock='-1'))
        self.update_latest()
    def iterate(self, _poll_seconds=1, _poll_instances=0, **arguments):
        arguments.setdefault('sort', 'HEIGHT_DESC')
        if type(arguments.get('tags')) is dict:
            arguments['tags'] = [dict(
                name = name,
                **{
                    list: {'values':values},
                    str: {'values':[values]},
                    dict: values,
                }[type(values)]
            ) for name, values in arguments['tags'].items()]
        reverse = -1 if arguments['sort'] == 'HEIGHT_DESC' else 1
        #arguments = ','.join(f'{key}:{val}' for key, val in arguments.items())
        block_entries = []
        for poll_instances in [0, _poll_instances]:
            last = None
            for idx, tx in enumerate(iterate_graphql(
                self.peer, 'transactions',
                {**self.arguments, **arguments},
                'id owner{address}tags{name value}block{id height}bundledIn{id}',
                poll_seconds = _poll_seconds,
                poll_instances = poll_instances,
            )):
                tx['tags'] = {tag['name']:tag['value'] for tag in tx['tags']}
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
    def update_latest(self):
        self.latest = self.get() or self.latest
        return self.latest
    def post(self, data, **tags):
        if data is None:
            data = b''
        elif type(data) is str:
            data = data.encode()
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
        print('sent', self.latest)
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
        with tqdm.tqdm(unit='s') as pbar:
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
    def use(self):
        if self._lock_tx is None or self._lock_tx['tags'][self.action_tagname] != self.locked_action:
            # not in a locked context
            raise KeyError('lock used without being held')
        if utctime() >= float(self._lock_tx['tags'][self.expiry_timeout_tagname]):
            # lost lock
            #return self.lock()
            # raise if timeout has passed
            raise KeyError('lock timed out while locked')
    def unlock(self):
        # unlock posted lock
        assert self._lock_tx['tags'][self.action_tagname] == self.locked_action
        self.use()
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
    def __init__(self, wallet_or_address, peer = None, bundlrnode = None, poll_time = 0.2, expected_completion_time = 1, timeout = 60):
        bundlr = bundlrnode
        peer = peer or ar.Peer()
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
        self.seq = Sequence(peer, dict(owners=[address]), wallet, bundlr)
        self.lock = Lock(self.seq)
        self.lock_params = dict(
            poll_time = poll_time,
            expected_completion_time = expected_completion_time,
            expiry_timeout_time = timeout
        )
    def store(self, data, **tags):
        self.lock.use()
        return self.seq.post(data, type='data', **tags)
    def __enter__(self):
        self.lock.lock(type='meta', **self.lock_params)
        self.seq.update_latest()
        return self
    def __exit__(self, *params):
        self.lock.unlock()
    def latest(self, **tags):
        tx = self.seq.get(tags=dict(type=dict(values=['meta'],op=NEQ), **tags))
        if tx is not None:
            tx['stream'] = self.seq.peer.gateway_stream(tx['id'])
        return tx

#
#    # we could optionally implement a network lock here for multiprocess synchronisation.
#    # it would use the iteration to find the latest lock tag.
#    # it could steal the lock after a timeout, i suppose.

if __name__ == '__main__':
    dr = DataResource('test.json')
    latest = dr.latest()
    with latest['stream'] as stream:
        print(latest)
        print(stream.read())
    with dr:
        dr.store('Hello world', tagname='tagvalue')
        dr.store('Hello world', tagname='tagvalue')
        dr.store('Hello world', tagname='tagvalue')
    latest = dr.latest()
    with latest['stream'] as stream:
        print(latest)
        print(stream.read())
    #print(dr.update_latest())
