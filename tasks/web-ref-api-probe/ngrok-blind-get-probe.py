#!/usr/bin/env python3
"""Compare real HTTP hits with Responses API web-tool output through ngrok.

Requires configured ngrok, Python 3, and OPENAI_WEB_SEARCH_API_KEY.
Usage: python3 ngrok-blind-get-probe.py --out /tmp/blind-get-results
Only generated probe pages are exposed; no filesystem content is served.
"""
import argparse
import concurrent.futures
import datetime
import html
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def say(value):
    print(json.dumps(value), flush=True)


def assistant_text(response):
    return '\n'.join(c.get('text', '') for item in response.get('output', [])
                     if item.get('type') == 'message'
                     for c in item.get('content', []) if c.get('type') == 'output_text')


class Experiment:
    def __init__(self, out, models, key):
        self.out, self.models, self.key = out, models, key
        self.routes, self.events, self.records = {}, [], []
        self.lock = threading.Lock()
        self.run_id = secrets.token_hex(10)
        self.public_url = None

    def add_route(self, label, kind='html', link=None):
        path = f'/probe/{self.run_id}/{label}/{secrets.token_hex(12)}'
        self.routes[path] = {'label': label, 'kind': kind, 'link': link}
        return path

    def handler(self):
        experiment = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_HEAD(self):
                self.respond(False)

            def do_GET(self):
                self.respond(True)

            def respond(self, send_body):
                parsed_path = urllib.parse.urlsplit(self.path).path
                route = experiment.routes.get(parsed_path)
                marker = None
                if parsed_path == '/robots.txt':
                    status, content_type, body = 200, 'text/plain', b'User-agent: *\nAllow: /\n'
                elif route is None:
                    status, content_type, body = 404, 'text/plain', b'Unknown probe path\n'
                else:
                    marker = 'PROBE_MARKER_' + secrets.token_hex(16)
                    status = 200
                    if route['kind'] == 'binary':
                        content_type, body = 'application/octet-stream', (marker + '\n').encode()
                    else:
                        content_type = 'text/html; charset=utf-8'
                        title = html.escape(route['label'])
                        link = ''
                        if route.get('link'):
                            link = f'<p><a href="{html.escape(route["link"], quote=True)}">Follow this probe link</a></p>'
                        body = (f'<!doctype html><html><head><title>{title}</title></head>'
                                f'<body><h1>{title}</h1><p>{marker}</p>{link}</body></html>').encode()
                event = {'time': utc(), 'monotonic': time.monotonic(), 'method': self.command,
                         'path': self.path, 'status': status, 'content_type': content_type,
                         'user_agent': self.headers.get('User-Agent'),
                         'response_marker': marker if send_body else None}
                try:
                    self.send_response(status)
                    self.send_header('Content-Type', content_type)
                    self.send_header('Content-Length', str(len(body)))
                    self.send_header('Cache-Control', 'no-store, no-cache, max-age=0')
                    self.send_header('Pragma', 'no-cache')
                    self.send_header('X-Robots-Tag', 'noindex')
                    self.end_headers()
                    if send_body:
                        self.wfile.write(body)
                    event['write_completed'] = True
                except (BrokenPipeError, ConnectionResetError):
                    event['write_completed'] = False
                finally:
                    with experiment.lock:
                        experiment.events.append(event)
                        with (experiment.out / 'http-events.jsonl').open('a') as f:
                            f.write(json.dumps(event) + '\n')
                    say({'http': {k: v for k, v in event.items() if k != 'monotonic'}})

        return Handler

    def base(self, model):
        return {'model': model, 'tools': [{'type': 'web_search'}],
                'reasoning': {'effort': 'low'}, 'store': True,
                'max_output_tokens': 2200, 'max_tool_calls': 1,
                'include': ['web_search_call.results', 'reasoning.encrypted_content'],
                'instructions': 'Execute the requested web calls exactly. Report actual tool results and errors. '
                                'Only report a PROBE_MARKER if the tool returned it. '
                                'Do not search, retry, or use workarounds.'}

    def api(self, model_dir, label, body):
        save(model_dir / (label + '.request.json'), body)
        started = time.monotonic()
        record = {'label': label, 'started_utc': utc(), 'started_monotonic': started}
        say({'started': label, 'model': body['model'], 'utc': record['started_utc']})
        req = urllib.request.Request('https://api.openai.com/v1/responses',
                                     data=json.dumps(body).encode(), method='POST',
                                     headers={'Authorization': 'Bearer ' + self.key,
                                              'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                record.update(http_status=r.status, request_id=r.headers.get('x-request-id'),
                              response=json.loads(r.read().decode().replace(self.key, '[REDACTED]')))
        except urllib.error.HTTPError as error:
            record.update(http_status=error.code,
                          error=error.read().decode().replace(self.key, '[REDACTED]'))
        except Exception as error:
            record['error'] = str(error).replace(self.key, '[REDACTED]')
        record.update(ended_utc=utc(), ended_monotonic=time.monotonic())
        record['elapsed_s'] = round(record['ended_monotonic'] - started, 3)
        save(model_dir / (label + '.response.json'), record)
        self.records.append(record)
        response = record.get('response', {})
        say({'completed': label, 'model': body['model'], 'http_status': record.get('http_status'),
             'elapsed_s': record['elapsed_s'], 'status': response.get('status'),
             'tool_actions': [i.get('action') for i in response.get('output', [])
                              if i.get('type') == 'web_search_call'],
             'assistant_report': assistant_text(response), 'error': record.get('error')})
        if record.get('http_status') != 200 or response.get('status') != 'completed':
            raise RuntimeError(f'API call did not complete: {model_dir.name}/{label}')
        return record

    def summarize(self, record, expected_path):
        response = record['response']
        calls = [i for i in response.get('output', []) if i.get('type') == 'web_search_call']
        tool_text = '\n'.join(r.get('snippet', '') for c in calls for r in c.get('results', []))
        with self.lock:
            all_hits = [e.copy() for e in self.events if e['path'] == expected_path]
        new_hits = [e for e in all_hits if record['started_monotonic'] <= e['monotonic'] <= record['ended_monotonic']]
        markers = [e['response_marker'] for e in all_hits if e.get('response_marker')]
        return {'label': record['label'], 'model': response.get('model'),
                'expected_url': self.public_url + expected_path,
                'actions': [c.get('action') for c in calls],
                'result_count': sum(len(c.get('results', [])) for c in calls),
                'http_hits_during_call': len(new_hits),
                'get_hits_during_call': sum(e['method'] == 'GET' for e in new_hits),
                'new_marker_in_tool_result': any(e.get('response_marker') and e['response_marker'] in tool_text for e in new_hits),
                'any_served_marker_in_tool_result': any(m in tool_text for m in markers),
                'any_served_marker_in_assistant_report': any(m in assistant_text(response) for m in markers),
                'assistant_report': assistant_text(response), 'http_events': new_hits}

    def run_model(self, model):
        model_dir = self.out / model
        model_dir.mkdir()
        clicked = self.add_route(model + '-clicked')
        seed = self.add_route(model + '-seed', link=clicked)
        file_only = self.add_route(model + '-file-only')
        binary = self.add_route(model + '-binary', kind='binary')
        urls = {k: self.public_url + v for k, v in
                [('seed', seed), ('clicked', clicked), ('file_only', file_only), ('binary', binary)]}
        save(model_dir / 'urls.json', urls)
        summaries = []

        # The first user supplies only the seed URL; the clicked URL is discovered in HTML.
        body = self.base(model)
        body.update(max_tool_calls=2, input=f'Open {urls["seed"]}. Inspect the returned page and click its '
                    'only numbered link, using the returned page reference and numbered link ID. '
                    'Exactly two sequential web calls: open, then click. After clicking, note the '
                    'destination URL, title, and PROBE_MARKER in your final answer. Do not search or open extra pages.')
        seed_record = self.api(model_dir, 'seed-and-click', body)
        summaries.append(self.summarize(seed_record, seed))
        summaries.append({**self.summarize(seed_record, clicked), 'label': 'same-turn-click'})
        seed_response = seed_record['response']
        calls = [i for i in seed_response['output'] if i['type'] == 'web_search_call']
        click_ok = (len(calls) == 2 and any(r.get('url') == urls['clicked'] and 'Source: click(' in r.get('snippet', '')
                                         for r in calls[1].get('results', []))
                    and urls['clicked'] in assistant_text(seed_response))
        if click_ok:
            body = self.base(model)
            body.update(previous_response_id=seed_response['id'], input=
                        'Open the destination URL you reached by clicking in the previous turn. '
                        'Use the exact full URL you noted, not an opaque reference. Make exactly one open call. '
                        'Report the attempted URL and the PROBE_MARKER returned by this call, or the exact tool error. '
                        'Do not search, click, or retry.')
            record = self.api(model_dir, 'next-turn-clicked-url', body)
            summaries.append(self.summarize(record, clicked))
        else:
            summaries.append({'label': 'next-turn-clicked-url', 'skipped': 'Seed did not establish the required click and noted URL'})

        # A real host file read returns a brand-new URL only through function_call_output.
        (model_dir / 'target-url.txt').write_text(urls['file_only'] + '\n')
        function = {'type': 'function', 'name': 'read_probe_url',
                    'description': 'Read the saved target URL from the local probe file.',
                    'strict': True,
                    'parameters': {'type': 'object', 'properties': {}, 'required': [], 'additionalProperties': False}}
        body = self.base(model)
        body['tools'].append(function)
        body.update(tool_choice={'type': 'function', 'name': 'read_probe_url'}, input=
                    'Read the saved target URL using read_probe_url. Then make exactly one web open call '
                    'on that exact URL. Report the attempted URL, title, and PROBE_MARKER from the '
                    'returned content, or the exact tool error. Do not search, click, or retry.')
        read_record = self.api(model_dir, 'file-read-request', body)
        function_calls = [i for i in read_record['response']['output'] if i['type'] == 'function_call']
        if len(function_calls) != 1 or function_calls[0]['name'] != 'read_probe_url':
            raise RuntimeError('Expected exactly one read_probe_url function call')
        body = self.base(model)
        body['tools'].append(function)
        body.update(previous_response_id=read_record['response']['id'], input=[
                    {'type': 'function_call_output', 'call_id': function_calls[0]['call_id'],
                     'output': (model_dir / 'target-url.txt').read_text().strip()}])
        record = self.api(model_dir, 'file-only-open', body)
        summaries.append(self.summarize(record, file_only))

        # Same fetch mechanism, user-provided fresh URL, intentionally non-HTML media type.
        body = self.base(model)
        body['input'] = (f'Open {urls["binary"]} using exactly one web open call. '
                         'Report the attempted URL and any PROBE_MARKER in returned content, '
                         'or the exact tool error. Do not search, click, or retry.')
        record = self.api(model_dir, 'literal-binary-open', body)
        summaries.append(self.summarize(record, binary))
        save(model_dir / 'summary.json', summaries)
        return summaries

    def run(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), self.handler())
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        tunnel = None
        tunnel_log = (self.out / 'ngrok.log').open('w')
        try:
            port = server.server_address[1]
            tunnel = subprocess.Popen(['ngrok', 'http', f'http://127.0.0.1:{port}',
                                       '--log', 'stdout', '--log-format', 'json', '--log-level', 'info'],
                                      stdout=tunnel_log, stderr=subprocess.STDOUT)
            for _ in range(120):
                if tunnel.poll() is not None:
                    raise RuntimeError('ngrok exited; inspect ngrok.log')
                for line in (self.out / 'ngrok.log').read_text().splitlines():
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event.get('msg') == 'started tunnel' and str(event.get('url', '')).startswith('https://'):
                        self.public_url = event['url'].rstrip('/')
                        break
                if self.public_url:
                    break
                time.sleep(0.25)
            if not self.public_url:
                raise RuntimeError('Timed out waiting for public ngrok URL')
            say({'ngrok_url': self.public_url, 'out': str(self.out)})
            save(self.out / 'run.json', {'started': utc(), 'public_url': self.public_url,
                                        'run_id': self.run_id, 'models': self.models})
            # This independently validates the tunnel on a path never used in API tests.
            health_path = self.add_route('harness-health')
            req = urllib.request.Request(self.public_url + health_path,
                                         headers={'User-Agent': 'blind-get-probe-harness/1.0',
                                                  'ngrok-skip-browser-warning': '1'})
            with urllib.request.urlopen(req, timeout=30) as response:
                health = response.read().decode()
                if 'PROBE_MARKER_' not in health:
                    raise RuntimeError('Tunnel did not return the local probe page')
            say({'health': 'tunnel returned generated page'})
            results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.models)) as pool:
                jobs = {pool.submit(self.run_model, model): model for model in self.models}
                for job in concurrent.futures.as_completed(jobs):
                    try:
                        results.extend(job.result())
                    except Exception as error:
                        results.append({'model': jobs[job], 'error': str(error).replace(self.key, '[REDACTED]')})
            # Observe late HTTP activity before closing the endpoint.
            time.sleep(10)
            save(self.out / 'summary.json', results)
            say({'summary': [{k: v for k, v in r.items() if k not in ('http_events', 'assistant_report')} for r in results]})
        finally:
            if tunnel is not None:
                tunnel.terminate()
                try:
                    tunnel.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    tunnel.kill()
                    tunnel.wait(timeout=5)
            tunnel_log.close()
            server.shutdown()
            server.server_close()
            say({'cleanup': 'ngrok process and probe HTTP server stopped', 'utc': utc()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--models', nargs='+', default=['gpt-5.5', 'gpt-6-astra'])
    args = parser.parse_args()
    key = os.environ.get('OPENAI_WEB_SEARCH_API_KEY')
    if not key:
        parser.error('OPENAI_WEB_SEARCH_API_KEY must be set')
    if not shutil.which('ngrok'):
        parser.error('ngrok must be installed and configured')
    args.out.mkdir(parents=True, exist_ok=False)
    Experiment(args.out.resolve(), args.models, key).run()


if __name__ == '__main__':
    main()
