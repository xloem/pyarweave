#!/usr/bin/env python3
from ar.gateways import fetch_from_registry
import requests
import sys, time
from pqdm.threads import pqdm # maybe joblib Parallel verbose=True instead

if len(sys.argv) > 1:
    fetchid = sys.argv[1]
    fetchid_text = requests.get(f'https://permagate.io/{fetchid}').text
#    fastest_time = float('inf')
#    fastest_url = None
else:
    fetchid = None

def measure_entry(entry):
    start = time.time()
    url = entry['url']
    try:
        response = requests.get(f'{url}/{fetchid}', timeout=15)
        response.raise_for_status()
        assert response.text == fetchid_text
    except:
        pass
    else:
        entry['duration'] = time.time() - start

def process_entry(entry):
    settings = entry['settings']
    protoport = [settings['protocol'], settings['port']]
    if protoport in [['http',80],['https',443]]:
        url = '{protocol}://{fqdn}'.format(**settings)
    else:
        url = '{protocol}://{fqdn}:{port}'.format(**settings)
    entry['url'] = url
    if fetchid is not None and entry['status'] == 'joined':
        measure_entry(entry)
    return entry

gws = pqdm(
    fetch_from_registry(raw=True), process_entry, n_jobs=32,
    unit='gw', leave=False, desc='measuring',
)
if fetchid is not None:
    gws = [[gw['duration'], gw['url']] for gw in gws if 'duration' in gw]
    gws.sort()
    for time, url in gws[:4]:
        print(url)
else:
    for gw in gws:
        if isinstance(gw, Exception):
            raise gw
        print(gw['url'])
