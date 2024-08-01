def paginate(client, *path, params, **kwparams):
    while True:
        result = client._get_json(*path, params=params, **kwparams)
        yield from result['edges']
        if not result['pageInfo']['hasNextPage']:
            break
        params['from'] = (params['from'] or 0) + len(result['edges'])
