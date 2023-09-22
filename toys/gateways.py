from ar import DEFAULT_GATEWAY_ADDRESS_REGISTRY_CACHE
import requests

cache = requests.get(DEFAULT_GATEWAY_ADDRESS_REGISTRY_CACHE).json()
for id, entry in cache['gateways'].items():
    settings = entry['settings']
    if entry['status'] != 'joined':
        continue
    protoport = [settings['protocol'], settings['port']]
    if protoport in [['http',80],['https',443]]:
        url = '{protocol}://{fqdn}'.format(**settings)
    else:
        url = '{protocol}://{fqdn}:{port}'.format(**settings)
    print(url)
