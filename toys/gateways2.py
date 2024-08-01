#!/usr/bin/env python3
from ar.gateways import fetch_from_registry
import requests
import math, sys, time
from pqdm.threads import pqdm # maybe joblib Parallel verbose=True instead

import hashlib
fetch_id = '0eRcI5PpUQGIDcBGTPCcANkUkgY85a1VGf0o7Y-q01o'
fetch_sha512 = '7a240f64db4264370ad371a76837ac837f5bee9756bea793c5c27bae04e98e3d853c24c031ba350e3006ea8c83c2c93ec0d6549dca51970d4e12add24fd44b2f'

def measure_gw(url):
    start = time.time()
    try:
        response = requests.get(f'{url}/{fetch_id}', timeout=15)
        response.raise_for_status()
        assert hashlib.sha512(response.content).hexdigest() == fetch_sha512
    except:
        return [math.inf, url]
    else:
        return [time.time() - start, url]

gws = pqdm(
    fetch_from_registry(), measure_gw, n_jobs=32,
    unit='gw', leave=False, desc='measuring',
)
gws.sort()
for time, url in gws[:4]:
    if time < math.inf:
        print(time, url)
    else:
        print('FAIL')
