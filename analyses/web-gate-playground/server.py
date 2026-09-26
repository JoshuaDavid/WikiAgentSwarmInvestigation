#!/usr/bin/env python3
"""Local, disposable UI for a human-gated Responses API web agent. Stdlib only."""
import argparse
import copy
import datetime as dt
import json
import os
from pathlib import Path
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from tool_errors import PRESETS, error_text
from url_routing import Router
from prompt_cache import OPTIONS as CACHE_OPTIONS, cache_request
from token_usage import normalize as normalize_usage, run_usage

HERE = Path(__file__).resolve().parent
TOOL = json.loads((HERE / 'web-tool.json').read_text())
MODELS = ['gpt-5.6-luna', 'gpt-6-astra']
DEFAULT_PROMPT = ('Search for "IANA example domains", then open the first result. '
                  'Report the main heading of the opened page and a one-sentence summary. '
                  'Use the opened content. If the open fails, say so and stop without retrying.')
ACTIVE = {'running', 'searching', 'fetching', 'routing'}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)


def text_output(response):
    return '\n'.join(p.get('text', '') for i in response.get('output', [])
                     if i.get('type') == 'message' for p in i.get('content', [])
                     if p.get('type') == 'output_text')


def load_key(path):
    key = os.environ.get('OPENAI_API_KEY') or os.environ.get('OPENAI_WEB_SEARCH_API_KEY')
    if not key and path:
        key = path.read_text().strip()
        if key.startswith(('OPENAI_API_KEY=', 'OPENAI_WEB_SEARCH_API_KEY=')):
            key = key.split('=', 1)[1].strip().strip('\"\'')
    return key or ''


def http_url(value):
    try:
        p = urllib.parse.urlsplit(value)
        return p.scheme in {'http', 'https'} and bool(p.hostname) and not p.username
    except ValueError:
        return False


def same_url(a, b):
    def normalize(value):
        p = urllib.parse.urlsplit(value)
        return (p.scheme.lower(), p.netloc.lower(), p.path or '/', p.query)
    return normalize(a) == normalize(b)


class Stopped(Exception):
    pass


class Run:
    def __init__(self, data, folder):
        self.d = data
        self.folder = folder
        self.lock = threading.RLock()

    def save(self):
        self.d['updated_at'] = now()
        write_json(self.folder / 'state.json', self.d)

    def event(self, kind, title, **data):
        with self.lock:
            event = {'id': len(self.d['events']) + 1, 'time': now(),
                     'kind': kind, 'title': title, 'run_id': self.d['id'], **data}
            self.d['events'].append(event)
            self.save()

    def active(self):
        if self.d['state'] == 'stopped':
            raise Stopped()


class Playground:
    def __init__(self, data_dir, key='', transport=None, router=None):
        self.root = data_dir
        self.root.mkdir(parents=True, exist_ok=True)
        self.key = key
        self.transport = transport
        self.router = router or Router(data_dir / 'routing.json')
        self.runs = {}
        self.lock = threading.RLock()
        for path in self.root.glob('*/state.json'):
            data = json.loads(path.read_text())
            run = Run(data, path.parent)
            if data['state'] in ACTIVE:
                data['state'] = 'paused'
                data['detail'] = 'Server restarted. Resume when ready; no request was automatically retried.'
                run.save()
            self.runs[data['id']] = run

    def create(self, prompt=DEFAULT_PROMPT, model=MODELS[0], mode='api', max_steps=20):
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 50000:
            raise ValueError('Enter a prompt between 1 and 50,000 characters.')
        if model not in MODELS or mode not in {'api', 'demo'}:
            raise ValueError('Unknown model or mode.')
        if mode == 'api' and not self.key and not self.transport:
            raise ValueError('Restart the server with --api-key-file or OPENAI_API_KEY to use the API.')
        if not isinstance(max_steps, int) or not 1 <= max_steps <= 100:
            raise ValueError('Agent turn limit must be between 1 and 100.')
        rid = secrets.token_hex(6)
        data = {'schema_version': 2, 'id': rid, 'created_at': now(), 'updated_at': now(), 'parent': None,
                'prompt': prompt.strip(), 'model': model, 'backend_model': MODELS[0],
                'mode': mode, 'max_steps': max_steps, 'steps': 0, 'request_count': 0,
                'tokens': 0, 'state': 'running', 'detail': 'Starting agent',
                'history': [{'role': 'user', 'content': prompt.strip()}],
                'events': [], 'refs': {}, 'ref_sources': {}, 'ref_turn': 0,
                'turns': [], 'queue': [], 'pending': None}
        run = Run(data, self.root / rid)
        with self.lock:
            self.runs[rid] = run
        run.event('start', 'Run started', mode=mode, model=model, text=prompt.strip())
        self.launch(run, self.drive)
        return run

    def launch(self, run, fn):
        def work():
            try:
                fn(run)
            except Stopped:
                pass
            except Exception as exc:
                with run.lock:
                    if run.d['state'] == 'stopped':
                        return
                    message = str(exc).replace(self.key, '[REDACTED]') if self.key else str(exc)
                    run.d.update(state='error', detail=message)
                    run.event('error', 'Run paused after an error', text=message)
        threading.Thread(target=work, daemon=True).start()

    def request(self, run, purpose, body):
        body = cache_request(body, purpose)
        with run.lock:
            run.active()
            if run.d['request_count'] >= 150:
                raise RuntimeError('Run reached the prototype limit of 150 API requests. Fork a gate to continue.')
            run.d['request_count'] += 1
            stem = f"{run.d['request_count']:03d}-{purpose}"
            write_json(run.folder / f'{stem}.request.json', body)
            run.event('api', f'{purpose.capitalize()} API request', purpose=purpose,
                      artifact=f'{stem}.request.json', model=body['model'],
                      request_key=stem, turn_index=run.d['steps'] + (purpose == 'agent'),
                      gate_id=(run.d.get('pending') or {}).get('id'))
        started = time.monotonic()
        if self.transport:
            response, status, request_id = self.transport(purpose, body)
        else:
            req = urllib.request.Request('https://api.openai.com/v1/responses',
                    data=json.dumps(body).encode(), method='POST',
                    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {self.key}'})
            try:
                with urllib.request.urlopen(req, timeout=180) as result:
                    raw, status, request_id = result.read(), result.status, result.headers.get('x-request-id')
            except urllib.error.HTTPError as exc:
                raw, status, request_id = exc.read(), exc.code, exc.headers.get('x-request-id')
            except (urllib.error.URLError, TimeoutError) as exc:
                raise RuntimeError(f'{purpose} request failed: {exc}') from None
            response = json.loads(raw.decode().replace(self.key, '[REDACTED]'))
        with run.lock:
            write_json(run.folder / f'{stem}.response.json', response)
            meta = {'status': status, 'request_id': request_id, 'elapsed_s': round(time.monotonic()-started, 2),
                    'usage': response.get('usage'), 'response_status': response.get('status'),
                    'token_counts': normalize_usage(response.get('usage')),
                    'prompt_cache': {'requested_key': body['prompt_cache_key'],
                                     'requested_options': body['prompt_cache_options'],
                                     'reported_options': response.get('prompt_cache_options')}}
            write_json(run.folder / f'{stem}.meta.json', meta)
            run.d['tokens'] += (response.get('usage') or {}).get('total_tokens', 0)
            run.event('api', f'{purpose.capitalize()} API response · HTTP {status}',
                      purpose=purpose, artifact=f'{stem}.response.json', meta=meta,
                      request_key=stem, turn_index=run.d['steps'] + (purpose == 'agent'),
                      gate_id=(run.d.get('pending') or {}).get('id'))
            run.active()
        if status != 200 or response.get('status') != 'completed':
            raise RuntimeError(f"{purpose} request did not complete: {response.get('error') or response.get('incomplete_details') or status}")
        return response

    def native(self, run, operation, arguments):
        search = operation == 'search_query'
        prompt = ('Run exactly one web search_query with these arguments: ' + json.dumps(arguments) +
                  '. Do not open or click any page. Stop after the search.') if search else (
                  'Open this exact URL directly, once: ' + arguments['ref_id'] +
                  '. Do not search, click, or open any other URL. Use these open arguments: ' +
                  json.dumps(arguments) + '. Stop after the tool call.')
        response = self.request(run, 'search' if search else 'fetch', {
            'model': run.d['backend_model'], 'reasoning': {'effort': 'low'}, 'store': False,
            'max_output_tokens': 1200, 'max_tool_calls': 1,
            'tools': [{'type': 'web_search', 'external_web_access': not search}],
            'tool_choice': {'type': 'web_search'}, 'include': ['web_search_call.results'],
            'input': prompt,
        })
        calls = [i for i in response.get('output', []) if i.get('type') == 'web_search_call']
        expected = 'search' if search else 'open_page'
        valid = len(calls) == 1 and calls[0].get('action', {}).get('type') == expected
        if valid and not search:
            action = calls[0]['action']
            urls = [action['url']] if action.get('url') else action.get('urls', [])
            valid = len(urls) == 1 and same_url(urls[0], arguments['ref_id'])
        if not valid:
            raise RuntimeError(f'Backend did not perform the requested {expected}; inspect its raw response. No result forwarded.')
        return {'results': calls[0].get('results') or [], 'action': calls[0]['action'],
                'diagnostic': text_output(response)}

    def format_results(self, run, results, kind):
        # Native reference IDs are scoped to one backend request. Allocate IDs in
        # the evaluated agent's conversation and preserve all snippet prose.
        with run.lock:
            turn = run.d['ref_turn']
            run.d['ref_turn'] += 1
        mapping, refs = {}, {}
        for index, result in enumerate(results):
            ref = f'turn{turn}{kind}{index}'
            url = result.get('url', '')
            if url and http_url(url):
                refs[ref] = url
            for old in re.findall(r'\ue202([^\ue201]+)\ue201', result.get('snippet', '')):
                if re.fullmatch(r'turn\w+', old):
                    mapping[old] = ref
        rendered = []
        for index, result in enumerate(results):
            snippet = result.get('snippet', '')
            if not snippet:
                continue
            snippet = re.sub(r'\bturn\w+\b', lambda m: mapping.get(m[0], m[0]), snippet)
            if not re.search(r'\ue202turn', snippet):
                snippet = f'\ue200cite\ue202turn{turn}{kind}{index}\ue201 ' + snippet
            rendered.append(f"{result.get('title', '')} ({result.get('url', '')})\n{snippet}")
        return {'text': '\n\n'.join(rendered) or None, 'refs': refs}

    def agent(self, run):
        if run.d['mode'] == 'demo':
            time.sleep(0.25)
            outputs = [i for i in run.d['history'] if i.get('type') == 'function_call_output']
            if not outputs:
                args = {'search_query': [{'q': 'IANA example domains'}]}
            elif len(outputs) == 1:
                args = {'open': [{'ref_id': next(iter(run.d['refs']))}]}
            else:
                result = outputs[-1]['output']
                return {'output': [{'type': 'message', 'role': 'assistant', 'content': [
                    {'type': 'output_text', 'text': 'Demo agent received this exact tool result:\n\n' + result}]}]}
            return {'output': [{'type': 'function_call', 'call_id': 'demo_' + secrets.token_hex(6),
                                'name': 'web-run', 'arguments': json.dumps(args)}]}
        return self.request(run, 'agent', {
            'model': run.d['model'], 'reasoning': {'effort': 'low'}, 'store': False,
            'max_output_tokens': 3000, 'tools': [TOOL], 'parallel_tool_calls': False,
            'include': ['reasoning.encrypted_content'], 'tool_choice': 'auto',
            'input': copy.deepcopy(run.d['history']),
        })

    def operations(self, args):
        operations = []
        # Resolve searches before opens even if the model emits both in one call.
        keys = ['search_query'] + [k for k in args if k not in {'search_query', 'response_length'}]
        for kind in keys:
            values = args.get(kind)
            if values is None or values == []:
                continue
            if isinstance(values, list):
                for arg in values:
                    operations.append({'kind': kind, 'args': arg})
            else:
                operations.append({'kind': kind, 'args': values})
        return operations or [{'kind': 'unsupported', 'args': args}]

    def drive(self, run):
        while True:
            with run.lock:
                run.active()
                if run.d['pending']:
                    stage = 'wait_result' if run.d['pending'].get('fetched') else 'wait_fetch'
                    run.d.update(state=stage, detail='Waiting for your decision')
                    run.save()
                    return
                queued = bool(run.d['queue'])
            if queued:
                if not self.process_queue(run):
                    return
                continue
            with run.lock:
                if run.d['steps'] >= run.d['max_steps']:
                    run.d.update(state='limit', detail='Agent turn limit reached. Increase the limit to continue.')
                    run.save()
                    return
                run.d.update(state='running', detail='Agent is thinking')
                run.save()
            response = self.agent(run)
            with run.lock:
                run.active()
                outputs = response.get('output', [])
                if any(i.get('type') == 'web_search_call' for i in outputs):
                    raise RuntimeError('Unexpected native web call from the evaluated agent.')
                run.d['steps'] += 1
                turn_index = run.d['steps']
                run.d.setdefault('turns', []).append({
                    'index': turn_index, 'response_id': response.get('id'),
                    'history_start': len(run.d['history']),
                    'history_end': len(run.d['history']) + len(outputs),
                    'call_ids': [i['call_id'] for i in outputs if i.get('type') == 'function_call'],
                })
                run.d['history'].extend(outputs)
                for item in outputs:
                    if item.get('type') == 'message':
                        run.event('assistant', 'Agent message', text=text_output({'output': [item]}), turn_index=turn_index)
                    elif item.get('type') == 'function_call':
                        if item['name'] != 'web-run':
                            raise RuntimeError('Unexpected tool name: ' + item['name'])
                        args = json.loads(item['arguments'])
                        run.event('call', 'Agent called web-run', arguments=args, call_id=item['call_id'], turn_index=turn_index)
                        run.d['queue'].append({'call_id': item['call_id'], 'arguments': args,
                                               'turn_index': turn_index,
                                               'operations': self.operations(args), 'parts': []})
                if not run.d['queue']:
                    run.d.update(state='complete', detail='Agent finished')
                    run.event('complete', 'Run complete')
                    return
                run.save()

    def process_queue(self, run):
        auto_route = False
        with run.lock:
            run.active()
            call = run.d['queue'][0]
            if not call['operations']:
                text = '\n\n'.join(call['parts'])
                run.d['history'].append({'type': 'function_call_output', 'call_id': call['call_id'], 'output': text})
                run.d['queue'].pop(0)
                run.event('result', 'Tool result sent to agent', text=text, call_id=call['call_id'])
                return True
            op = call['operations'][0]
            if op['kind'] != 'search_query':
                ref = op['args'].get('ref_id', '') if isinstance(op['args'], dict) else ''
                url = ref if http_url(str(ref)) else run.d['refs'].get(str(ref))
                gate = {'id': secrets.token_hex(6), 'kind': op['kind'], 'arguments': op['args'],
                        'ref': ref, 'url': url, 'fetched': False, 'candidate': None,
                        'fetch_error': None, 'packet': None, 'call_id': call['call_id']}
                gate.update(self.gate_details(run.d, gate))
                gate['route'] = self.router.match(url, gate['input_kind']) if op['kind'] == 'open' else None
                run.d['pending'] = gate
                run.d.update(state='wait_fetch', detail='Open is blocked on your decision' if op['kind']=='open'
                             else 'This operation needs a supplied tool result')
                run.event('gate', 'Open blocked' if op['kind']=='open' else f"Manual result: {op['kind']}",
                          gate_id=gate['id'], url=url, arguments=op['args'],
                          call_id=call['call_id'], input_kind=gate['input_kind'],
                          original_ref=ref, turn_index=gate['turn_index'],
                          operation_index=gate['operation_index'], route=gate['route'])
                self.checkpoint(run)
                auto_route = bool(gate['route'] and gate['route']['delivery'] == 'auto')
                if auto_route:
                    run.d.update(state='routing', detail='Applying an automatic URL rule')
                    run.save()
                else:
                    return False
            else:
                run.d.update(state='searching', detail='Searching the cache-only backend')
                run.event('search', 'Search runs automatically', arguments=op['args'])
        if auto_route:
            return self.route_result(run, automatic=True)
        try:
            if run.d['mode'] == 'demo':
                packet = {'results': [{'title': 'Example Domain', 'url': 'https://example.com/',
                          'snippet': '\ue200cite\ue202turn0search0\ue201 [wordlim: 200] A domain for documentation examples.'}]}
            else:
                packet = self.native(run, 'search_query', op['args'])
            formatted = self.format_results(run, packet['results'], 'search')
            result = formatted['text'] or 'No search results found.'
            with run.lock:
                run.active()
                run.d['refs'].update(formatted['refs'])
                for ref in formatted['refs']:
                    run.d.setdefault('ref_sources', {})[ref] = {'kind': 'search', 'call_id': call['call_id']}
        except Stopped:
            raise
        except Exception as exc:
            with run.lock:
                run.active()
                run.event('warning', 'Search backend failed', text=str(exc))
            result = 'Search failed: the search service returned no usable result.'
        with run.lock:
            run.active()
            call['parts'].append(result)
            call['operations'].pop(0)
            run.event('search_result', 'Search result available', text=result)
        return True

    def checkpoint(self, run):
        write_json(run.folder / f"gate-{run.d['pending']['id']}.json", run.d)

    def gate_details(self, data, gate):
        arguments = gate.get('arguments') if isinstance(gate.get('arguments'), dict) else {}
        ref = str(gate.get('ref') or arguments.get('ref_id', ''))
        input_kind = 'url' if http_url(ref) else 'ref'
        queue = data.get('queue') or []
        call = queue[0] if queue else {}
        operation_index = len(self.operations(call.get('arguments', {}))) - len(call.get('operations', [])) + 1
        return {'input_kind': input_kind, 'ref': ref,
                'ref_source': data.get('ref_sources', {}).get(ref),
                'turn_index': gate.get('turn_index', call.get('turn_index', data['steps'])),
                'operation_index': gate.get('operation_index', operation_index)}

    def route_result(self, run, automatic=False):
        with run.lock:
            gate = copy.deepcopy(run.d['pending'])
            run.event('route', 'Applying URL rule', gate_id=gate['id'], route=gate['route'], automatic=automatic)
        try:
            text = self.router.execute(gate['route'], gate['url'])
        except Exception as exc:
            with run.lock:
                run.active()
                run.d['pending'].update(fetched=True, candidate=None, result_source='route',
                                        fetch_error='URL rule failed: ' + str(exc))
                run.d.update(state='wait_result', detail='URL rule failed. No native fetch was attempted.')
                run.event('error', 'URL rule failed; no network fallback', text=str(exc), gate_id=gate['id'])
                self.checkpoint(run)
            return False
        with run.lock:
            run.active()
            run.d['pending'].update(fetched=True, candidate=text, result_source='route', refs={},
                                    packet=None, fetch_error=None)
            run.d.update(state='wait_result', detail='Local rule result ready for review')
            run.event('fetched', 'URL rule result held for review', gate_id=gate['id'], text=text, route=gate['route'])
            self.checkpoint(run)
            if automatic:
                self.accept_result(run, 'route', text, actor='URL rule')
                return True
            return False

    def fetch(self, run):
        with run.lock:
            gate = copy.deepcopy(run.d['pending'])
        try:
            arguments = {**gate['arguments'], 'ref_id': gate['url']}
            if run.d['mode'] == 'demo':
                time.sleep(0.3)
                packet = {'results': [{'title': 'Example Domain', 'url': gate['url'],
                    'snippet': '\ue200cite\ue202turn0view0\ue201 [wordlim: 200] Content type: text/html; Total lines: 2\n'
                               'L0: # Example Domain\nL1: This domain is for use in documentation examples.'}],
                          'action': {'type': 'open_page', 'url': gate['url']}, 'diagnostic': ''}
            else:
                packet = self.native(run, 'open', arguments)
            formatted = self.format_results(run, packet['results'], 'view')
            error = None if formatted['text'] else 'The API returned no raw tool-result text. Inspect the backend response or provide your own result.'
        except Stopped:
            raise
        except Exception as exc:
            packet, formatted, error = None, {'text': None, 'refs': {}}, str(exc)
        with run.lock:
            run.active()
            run.d['pending'].update(fetched=True, candidate=formatted['text'], refs=formatted['refs'],
                                    packet=packet, fetch_error=error,
                                    result_source='demo' if run.d['mode']=='demo' else 'native')
            run.d.update(state='wait_result', detail='Fetch finished. Choose what the agent receives.')
            run.event('fetched', 'Fetched result held for review', gate_id=gate['id'],
                      text=formatted['text'], error=error)
            self.checkpoint(run)

    def act(self, run, action, gate_id=None, text=None):
        with run.lock:
            gate = run.d['pending']
            if action == 'stop':
                run.d.update(state='stopped', detail='Stopped. An in-flight API request may finish; it will not continue the agent.')
                run.event('stop', 'Run stopped by operator')
                return run
            if action == 'resume':
                if run.d['state'] not in {'error', 'paused', 'limit'}:
                    raise ValueError('This run cannot be resumed in its current state.')
                if run.d['state'] == 'limit':
                    run.d['max_steps'] += 20
                run.d.update(state='running', detail='Resuming')
                run.event('resume', 'Run resumed')
                self.launch(run, self.drive)
                return run
            if run.d['state'] not in {'wait_fetch', 'wait_result'} or not gate or gate['id'] != gate_id:
                raise ValueError('This decision is stale or the run is busy. Refresh the run.')
            gate.update(self.gate_details(run.d, gate))
            if action == 'refresh_route':
                gate.update(self.gate_details(run.d, gate))
                gate['route'] = self.router.match(gate['url'], gate['input_kind']) if gate['kind']=='open' else None
                run.event('route', 'Matched URL rule refreshed for this gate', gate_id=gate_id, route=gate['route'])
                self.checkpoint(run)
                return run
            if action == 'route':
                if not gate.get('route'):
                    raise ValueError('No URL rule matched this open.')
                run.d.update(state='routing', detail='Running the matched URL rule locally')
                run.event('allow', 'Operator selected local URL rule', gate_id=gate_id, route=gate['route'])
                self.launch(run, self.route_result)
                return run
            if action == 'fetch':
                if gate['kind'] != 'open' or not gate['url']:
                    raise ValueError('No resolvable HTTP(S) URL to fetch. Supply text or a cache miss.')
                run.d.update(state='fetching', detail='Separate live-enabled API request is opening the URL')
                run.event('allow', 'Operator allowed fetch', gate_id=gate_id, url=gate['url'])
                self.launch(run, self.fetch)
                return run
            if action == 'original':
                if gate['candidate'] is None or not gate['fetched']:
                    raise ValueError('No fetched result is available to pass through.')
                selected = gate['candidate']
            elif action == 'replace':
                if not isinstance(text, str) or len(text) > 500000:
                    raise ValueError('Replacement must be text under 500,000 characters.')
                selected = text
            elif action in PRESETS:
                selected = error_text(action, gate['url'] or gate['ref'] or 'resource')
            else:
                raise ValueError('Unknown action.')
            self.accept_result(run, action, selected)
            self.launch(run, self.drive)
            return run

    def accept_result(self, run, action, selected, actor='Operator'):
        gate = run.d['pending']
        for ref, url in gate.get('refs', {}).items():
            if ref in selected:
                run.d['refs'][ref] = url
                run.d.setdefault('ref_sources', {})[ref] = {'kind': 'open', 'call_id': gate['call_id'], 'gate_id': gate['id']}
        call = run.d['queue'][0]
        call['parts'].append(selected)
        call['operations'].pop(0)
        run.d['pending'] = None
        run.d.update(state='running', detail='Continuing with the selected tool result')
        run.event('decision', actor + ' selected ' + action.replace('_', ' '),
                  gate_id=gate['id'], selection=action, text=selected, call_id=gate['call_id'],
                  route=gate.get('route'), input_kind=gate.get('input_kind'),
                  turn_index=gate.get('turn_index'), operation_index=gate.get('operation_index'))

    def fork(self, source, gate_id):
        if not re.fullmatch(r'[a-f0-9]{12}', gate_id or ''):
            raise ValueError('Invalid gate ID.')
        with source.lock:
            path = source.folder / f'gate-{gate_id}.json'
            ancestor = source
            while not path.exists() and ancestor.d.get('parent') in self.runs:
                ancestor = self.runs[ancestor.d['parent']]
                path = ancestor.folder / f'gate-{gate_id}.json'
            if not path.exists():
                raise ValueError('Gate checkpoint not found.')
            data = json.loads(path.read_text())
        rid = secrets.token_hex(6)
        data.update(id=rid, parent=source.d['id'], created_at=now(), updated_at=now(),
                    request_count=0, tokens=0, detail='Forked at this gate. Choose another outcome.')
        run = Run(data, self.root / rid)
        with self.lock:
            self.runs[rid] = run
        run.event('fork', 'Forked from ' + source.d['id'], gate_id=gate_id)
        self.checkpoint(run)
        return run

    def view(self, run):
        with run.lock:
            result = copy.deepcopy(run.d)
            result['usage_summary'] = run_usage(result)
            result['prompt_cache_policy'] = {'options': CACHE_OPTIONS, 'stable_key': True,
                                             'applies_to': ['agent', 'search', 'fetch']}
            if result.get('pending'):
                result['pending'].update(self.gate_details(result, result['pending']))
            # Full replay history remains available through the export endpoint.
            result['history'] = [{k: v for k, v in i.items() if k != 'encrypted_content'} for i in result['history']]
            return result


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def send(self, status, body, mime='application/json'):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
            self.end_headers()
            try:
                self.wfile.write(body)
            except BrokenPipeError:
                pass

        def valid_host(self):
            return self.headers.get('Host') in {f'localhost:{self.server.server_port}',
                                               f'127.0.0.1:{self.server.server_port}'}

        def do_GET(self):
            if not self.valid_host():
                return self.send(403, {'error': 'Use localhost or 127.0.0.1.'})
            path = urllib.parse.urlsplit(self.path).path
            static = {'/': ('index.html', 'text/html; charset=utf-8'),
                      '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                      '/style.css': ('style.css', 'text/css; charset=utf-8')}
            if path in static:
                name, mime = static[path]
                return self.send(200, (HERE / 'static' / name).read_bytes(), mime)
            if path == '/api/config':
                return self.send(200, {'api_ready': bool(app.key or app.transport), 'models': MODELS,
                                       'default_prompt': DEFAULT_PROMPT, 'presets': PRESETS})
            if path == '/api/routing':
                try:
                    return self.send(200, app.router.read())
                except (ValueError, OSError, KeyError) as exc:
                    return self.send(400, {'error': str(exc)})
            if path == '/api/tool':
                return self.send(200, TOOL)
            if path == '/api/runs':
                with app.lock:
                    runs = list(app.runs.values())
                fields = ['id', 'prompt', 'state', 'model', 'mode', 'created_at', 'parent']
                summaries = []
                for r in sorted(runs, key=lambda r:r.d['created_at'], reverse=True):
                    with r.lock:
                        summaries.append({k: r.d[k] for k in fields})
                return self.send(200, summaries)
            match = re.fullmatch(r'/api/runs/([a-f0-9]{12})(?:/(export|artifact)/?([^/]*))?', path)
            if match and match[1] in app.runs:
                run = app.runs[match[1]]
                if match[2] == 'export':
                    with run.lock:
                        payload = {'run': copy.deepcopy(run.d), 'usage_summary': run_usage(run.d),
                                   'artifacts': {p.name: json.loads(p.read_text())
                                   for p in run.folder.glob('*.json') if p.name != 'state.json'}}
                    return self.send(200, payload)
                if match[2] == 'artifact':
                    name = match[3]
                    if re.fullmatch(r'\d{3}-[a-z]+\.(request|response|meta)\.json', name):
                        p = run.folder / name
                        if p.exists():
                            return self.send(200, p.read_bytes())
                    return self.send(404, {'error': 'Artifact not found in this branch. Inherited artifacts are in its parent run.'})
                return self.send(200, app.view(run))
            self.send(404, {'error': 'Not found'})

        def do_POST(self):
            if not self.valid_host() or self.headers.get('Origin', f'http://{self.headers.get("Host")}') != f'http://{self.headers.get("Host")}':
                return self.send(403, {'error': 'Only same-origin local requests are accepted.'})
            if self.headers.get_content_type() != 'application/json':
                return self.send(415, {'error': 'Expected application/json.'})
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= 600000:
                    raise ValueError('Request body is empty or too large.')
                data = json.loads(self.rfile.read(length))
                if self.path == '/api/routing':
                    return self.send(200, app.router.save(data.get('rules'), data.get('revision')))
                elif self.path == '/api/runs':
                    run = app.create(**{k: data[k] for k in ['prompt', 'model', 'mode', 'max_steps'] if k in data})
                else:
                    match = re.fullmatch(r'/api/runs/([a-f0-9]{12})/(act|fork)', self.path)
                    if not match or match[1] not in app.runs:
                        return self.send(404, {'error': 'Run not found'})
                    source = app.runs[match[1]]
                    run = app.fork(source, data.get('gate_id')) if match[2] == 'fork' else app.act(
                        source, data.get('action'), data.get('gate_id'), data.get('text'))
                self.send(200, app.view(run))
            except (ValueError, TypeError, KeyError) as exc:
                self.send(400, {'error': str(exc)})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--api-key-file', type=Path)
    parser.add_argument('--data-dir', type=Path, default=HERE / 'runs')
    parser.add_argument('--routes-file', type=Path, help='Default: <data-dir>/routing.json')
    parser.add_argument('--services-file', type=Path, default=HERE / 'fake_services.py')
    args = parser.parse_args()
    router = Router(args.routes_file or args.data_dir / 'routing.json', args.services_file)
    app = Playground(args.data_dir, load_key(args.api_key_file), router=router)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(app))
    print(f'Web Gate Playground: http://127.0.0.1:{server.server_port}', flush=True)
    print(f'API ready: {bool(app.key)}. Runs saved in {args.data_dir.resolve()}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
