"""Stable, model-invisible cache routing for repeated request prefixes."""
import hashlib
import json

OPTIONS = {'mode': 'implicit', 'ttl': '30m'}


def cache_request(body, purpose):
    # No run ID, timestamp, user prompt, or tool result: continuations and forks
    # with the same static prefix must retain the same cache-routing key.
    prefix = {k: body.get(k) for k in ('model', 'tools', 'instructions', 'reasoning')}
    digest = hashlib.sha256(json.dumps(prefix, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:24]
    return {**body, 'prompt_cache_key': f'web-gate-v1:{purpose}:{digest}',
            'prompt_cache_options': dict(OPTIONS)}
