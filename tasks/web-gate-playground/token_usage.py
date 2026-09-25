"""Usage accounting from API reports, preserving unknown versus zero values."""
FIELDS = ('ordinary_input_tokens', 'output_tokens', 'cache_write_tokens', 'cache_read_tokens',
          'input_tokens', 'total_tokens', 'reasoning_tokens')


def count(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def normalize(usage):
    usage = usage if isinstance(usage, dict) else {}
    inputs = usage.get('input_tokens_details') or {}
    outputs = usage.get('output_tokens_details') or {}
    result = {
        'input_tokens': count(usage.get('input_tokens')),
        'output_tokens': count(usage.get('output_tokens')),
        'cache_write_tokens': count(inputs.get('cache_write_tokens')),
        'cache_read_tokens': count(inputs.get('cached_tokens')),
        'reasoning_tokens': count(outputs.get('reasoning_tokens')),
        'total_tokens': count(usage.get('total_tokens')),
        'ordinary_input_tokens': None,
    }
    total, reads, writes = (result[k] for k in ('input_tokens', 'cache_read_tokens', 'cache_write_tokens'))
    if all(value is not None for value in (total, reads, writes)) and reads + writes <= total:
        result['ordinary_input_tokens'] = total - reads - writes
    if result['total_tokens'] is None and total is not None and result['output_tokens'] is not None:
        result['total_tokens'] = total + result['output_tokens']
    return result


def summarize(records, requests):
    counts = [normalize(record.get('usage')) for record in records]
    coverage = {field: sum(row[field] is not None for row in counts) for field in FIELDS}
    totals = {field: (sum(row[field] for row in counts if row[field] is not None)
                      if coverage[field] or requests == 0 else None) for field in FIELDS}
    return {'requests': requests, 'responses': sum(record.get('responded', False) for record in records),
            'totals': totals, 'reported_requests': coverage}


def run_usage(data):
    records = {}
    for event in data.get('events', []):
        if event.get('kind') != 'api' or event.get('run_id', data['id']) != data['id']:
            continue
        artifact = event.get('artifact', '')
        if not artifact.endswith(('.request.json', '.response.json')):
            continue
        key = event.get('request_key') or artifact.rsplit('.', 2)[0]
        record = records.setdefault(key, {'purpose': event.get('purpose', 'unknown')})
        if artifact.endswith('.response.json'):
            record.update(usage=(event.get('meta') or {}).get('usage'), responded=True)
    result = summarize(list(records.values()), data.get('request_count', len(records)))
    result['by_purpose'] = {}
    for purpose in ('agent', 'search', 'fetch'):
        subset = [r for r in records.values() if r['purpose'] == purpose]
        result['by_purpose'][purpose] = summarize(subset, len(subset))
    result['scope'] = 'this_branch'
    return result
