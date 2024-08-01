from ar.peer import HTTPClient

class SchedulerUnit(HTTPClient):
    # ao/servers/su/src/main.rs

    def health(self):
        return self._get_json()

    identify = health

    def assign(self, process_id, tx_id, base_layer = '', exclude = ''):
        return self._post_json('', params={
            'process_id': process_id,
            'assign': tx_id,
            'base_layer': base_layer,
            'exclude': exclude,
        })

    def write(self, ditem):
        return self._post_json(ditem)

    def timestamp(self, process_id):
        return self._get_json('timestamp')

    def health_check(self):
        return self._get('health')

    def metrics(self):
        return self._get_json('metrics')

    def messages(self, tx_id, from_ = None, to = None, limit = None):#, process_id = None):
        return self._get_json(tx_id, params = {'from':from_,'to':to,'limit':limit})

    def process(self, process_id):
        return self._get_json('processes', process_id)
