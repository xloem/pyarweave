from ar.peer import HTTPClient
from . import DEFAULT_MU_HOST

class MessengerUnit(HTTPClient):
    # ao/servers/mu/src/routes

    def __init__(self, host = DEFAULT_MU_HOST, *params, **kwparams):
        super().__init__(host, *params, **kwparams)

    def identify(self):
        return self._get().text
    
    def monitor(self, process_id, signed_data_item):
        return self._post(signed_data_item, 'monitor', process_id).text

    def assign(self, process_id, tx_id, base_layer='', exclude=[]):
        return self._post_json(
            b'',
            params = {
                'process-id': process_id,
                'assign': tx_id,
                'base-layer': base_layer,
                'exclude': ','.join(exclude) if exclude else None,
            })

    def send(self, ditem):
        return self._post_json(ditem)

    def metrics(self):
        # this will raise 404 if the unit is not configured to enable it
        return self._get_json('metrics')

if __name__ == '__main__':
    PID = 'agYcCFJtrMG6cqMuZfskIkFTGvUPddICmtQSBIoPdiA'
    unit = MessengerUnit()
    print(unit.identify())
