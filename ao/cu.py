from ar.peer import HTTPClient
from . import DEFAULT_CU_HOST
from .utils import paginate

class ComputeUnit(HTTPClient):
    # ao/servers/cu/src/routes

    def __init__(self, host = DEFAULT_CU_HOST, *params, **kwparams):
        super().__init__(host, *params, **kwparams)

    def healthcheck(self):
        return self._get_json()

    identify = healthcheck

    def state(self, process_id, to = None):
        return self._get(
            'state', process_id,
            params = {'to': to},
            stream = True)

    def result(self, message_tx_id, process_id, no_busy = False):
        return self._get(
            'result', message_tx_id,
            params = {'process-id': process_id, 'no-busy': no_busy})

    def dry_run(self, process_id, to = None, id = None, signature = None, owner = None, target = None, data = None, tags = None, anchor = None, timestamp = None, block_height = None):
        if type(tags) is dict:
            tags = [{'name':k,'value':v} for k,v in tags.items()]
        return self._post_json(
            {
                'Id': id,
                'Signature': signature,
                'Owner': owner,
                'Target': target,
                'Data': data,
                'Tags': tags,
                'Anchor': anchor,
                'Timestamp': timestamp,
                'Block-Height': block_height,
            },
            'dry-run',
            params = {
                'process-id': process_id,
                'to': to,
            })

    def results(self, process_id, from_ = None, to = None, sort = 'ASC', limit = 25):
        yield from paginate(self, 'results', process_id, 
            params = {'from':from_, 'to':to, 'limit':limit, 'sort':sort})

    def cron(self, process_id, from_ = None, to = None, limit = 500):
        assert limit <= 1000 # hard max on server side 2024-07-31
        yield from paginate(self, 'cron', process_id, 
            params = {'from': from_, 'to': to, 'limit': limit})

    def metrics(self):
        # this will raise 404 if the unit is not configured to enable it
        return self._get_json('metrics')

if __name__ == '__main__':
    import json
    PID = 'agYcCFJtrMG6cqMuZfskIkFTGvUPddICmtQSBIoPdiA'
    unit = ComputeUnit()
    print(unit.healthcheck())
    for cron in unit.cron(PID):
        print(cron)
    for result in unit.results(PID):
        node = result['node']
        if node['Output']:
            print(node['Output']['data'])
        for msg in node['Messages']:
            print(json.loads(msg['Data']))
    #print(unit.result(PID))
    #print(unit.state(PID))
    result = unit.dry_run(
        PID,
        id = '1234',
        target = PID,
        owner = '1234',
        anchor = '0',
        data = '1234',
        tags = {
            'Action': 'Gateways', #'Paginated-Gateways', optional 'Cursor':
            'Data-Protocol': 'ao',
            'Type': 'Message',
            'Variant': 'ao.TN.1',
        },
    )
    result = json.loads(result['Messages'][0]['Data'])
    #print(result)
