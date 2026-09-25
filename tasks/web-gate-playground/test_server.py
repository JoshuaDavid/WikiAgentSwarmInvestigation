import copy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from server import Playground, same_url
from tool_errors import error_text
from url_routing import Router


def wait(run, state):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        with run.lock:
            if run.d['state'] == state:
                return
            if run.d['state'] == 'error' and state != 'error':
                raise AssertionError(run.d['detail'])
        time.sleep(.01)
    raise AssertionError(f"Expected {state}, got {run.d['state']}: {run.d['detail']}")


class FakeAPI:
    def __init__(self, opens=1):
        self.calls = []
        self.opens = opens
        self.fetch_entered = threading.Event()
        self.fetch_release = threading.Event()
        self.fetch_release.set()

    def __call__(self, purpose, body):
        self.calls.append((purpose, copy.deepcopy(body)))
        if purpose == 'agent':
            results = [i for i in body['input'] if i.get('type') == 'function_call_output']
            if not results:
                args = {'search_query': [{'q': 'example domains'}]}
            elif len(results) == 1:
                args = {'open': [{'ref_id': 'turn0search0'}] * self.opens}
            else:
                return {'status': 'completed', 'output': [{'type': 'message', 'role': 'assistant',
                    'content': [{'type': 'output_text', 'text': results[-1]['output']}]}]}, 200, 'test'
            output = [{'type': 'function_call', 'name': 'web-run', 'call_id': 'call_' + str(len(results)),
                       'arguments': json.dumps(args)}]
        else:
            if purpose == 'fetch':
                self.fetch_entered.set()
                self.fetch_release.wait(5)
            output = [{'type': 'web_search_call', 'action': {'type': 'search'} if purpose == 'search'
                else {'type': 'open_page', 'url': 'https://example.com/'},
                'results': [{'title': 'Example', 'url': 'https://example.com/', 'snippet':
                    '\ue200cite\ue202turn0search0\ue201 Search snippet' if purpose == 'search'
                    else '\ue200cite\ue202turn0view0\ue201 L0: # ORIGINAL_SECRET_HEADING'}]}]
        return {'status': 'completed', 'output': output}, 200, 'test'


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.fake = FakeAPI()
        self.app = Playground(Path(self.temp.name), transport=self.fake)

    def tearDown(self):
        self.temp.cleanup()

    def start(self):
        run = self.app.create()
        wait(run, 'wait_fetch')
        return run

    def test_search_auto_open_blocks_and_result_waits(self):
        run = self.start()
        self.assertEqual([p for p, _ in self.fake.calls], ['agent', 'search', 'agent'])
        self.assertFalse(self.fake.calls[1][1]['tools'][0]['external_web_access'])
        self.assertEqual(run.d['pending']['url'], 'https://example.com/')
        before = copy.deepcopy(run.d['history'])
        gate = run.d['pending']['id']
        self.app.act(run, 'fetch', gate)
        wait(run, 'wait_result')
        self.assertEqual(run.d['history'], before)
        self.assertEqual([p for p, _ in self.fake.calls], ['agent', 'search', 'agent', 'fetch'])
        self.assertTrue(self.fake.calls[-1][1]['tools'][0]['external_web_access'])
        self.assertIn('https://example.com/', self.fake.calls[-1][1]['input'])
        self.app.act(run, 'replace', gate, 'L0: # MY_REPLACEMENT')
        wait(run, 'complete')
        final_input = self.fake.calls[-1][1]['input']
        self.assertIn('MY_REPLACEMENT', json.dumps(final_input))
        self.assertNotIn('ORIGINAL_SECRET_HEADING', json.dumps(final_input))
        self.assertNotIn('Operator', json.dumps(final_input))
        self.assertEqual(self.fake.calls[-1][1]['tools'][0]['name'], 'web-run')
        self.assertEqual(len(self.fake.calls[-1][1]['tools']), 1)

    def test_deny_never_fetches(self):
        run = self.start()
        self.app.act(run, 'cache_miss', run.d['pending']['id'])
        wait(run, 'complete')
        self.assertNotIn('fetch', [p for p, _ in self.fake.calls])
        self.assertIn('Cache miss', run.d['history'][-2]['output'])

    def test_forks_share_pending_history_and_preserve_original(self):
        run = self.start()
        gid = run.d['pending']['id']
        self.app.act(run, 'fetch', gid)
        wait(run, 'wait_result')
        fork = self.app.fork(run, gid)
        self.assertEqual(fork.d['history'], run.d['history'])
        candidate = run.d['pending']['candidate']
        self.app.act(run, 'original', gid)
        self.app.act(fork, 'cache_miss', gid)
        wait(run, 'complete'); wait(fork, 'complete')
        self.assertEqual(run.d['history'][-2]['output'], candidate)
        self.assertIn('Cache miss', fork.d['history'][-2]['output'])
        self.assertEqual([p for p, _ in self.fake.calls].count('fetch'), 1)

    def test_duplicate_decision_is_rejected(self):
        run = self.start(); gid = run.d['pending']['id']
        self.fake.fetch_release.clear()
        self.app.act(run, 'fetch', gid)
        self.assertTrue(self.fake.fetch_entered.wait(3))
        with self.assertRaises(ValueError):
            self.app.act(run, 'fetch', gid)
        self.fake.fetch_release.set(); wait(run, 'wait_result')

    def test_stop_during_fetch_cannot_resume_agent(self):
        run = self.start(); gid = run.d['pending']['id']
        self.fake.fetch_release.clear()
        self.app.act(run, 'fetch', gid)
        self.assertTrue(self.fake.fetch_entered.wait(3))
        self.app.act(run, 'stop')
        self.fake.fetch_release.set()
        time.sleep(.1)
        self.assertEqual(run.d['state'], 'stopped')
        self.assertEqual([p for p, _ in self.fake.calls].count('agent'), 2)

    def test_multiple_opens_wait_individually(self):
        self.fake.opens = 2
        run = self.start(); first = run.d['pending']['id']
        self.app.act(run, 'replace', first, 'FIRST')
        wait(run, 'wait_fetch')
        second = run.d['pending']['id']
        self.assertNotEqual(first, second)
        self.assertEqual([p for p, _ in self.fake.calls].count('agent'), 2)
        self.app.act(run, 'replace', second, 'SECOND')
        wait(run, 'complete')
        self.assertEqual(run.d['history'][-2]['output'], 'FIRST\n\nSECOND')

    def test_restart_preserves_wait_and_does_not_make_requests(self):
        run = self.start()
        restarted = Playground(Path(self.temp.name), transport=self.fake)
        self.assertEqual(restarted.runs[run.d['id']].d['state'], 'wait_fetch')
        self.assertEqual(len(self.fake.calls), 3)

    def test_reference_ids_are_unique_across_backend_requests(self):
        run = self.start()
        results = [{'title':'A', 'url':'https://example.org/', 'snippet':'\ue200cite\ue202turn0search0\ue201 hi'}]
        formatted = self.app.format_results(run, results, 'search')
        self.assertNotIn('turn0search0', formatted['text'])
        self.assertNotEqual(next(iter(formatted['refs'])), 'turn0search0')

    def test_open_validation_rejects_wrong_url(self):
        self.assertFalse(same_url('https://example.com/one', 'https://example.com/two'))
        self.assertTrue(same_url('https://example.com', 'https://example.com/'))

    def test_wrong_native_action_never_becomes_a_candidate(self):
        run = self.start(); original = self.app.transport
        def wrong_action(purpose, body):
            result, status, rid = original(purpose, body)
            if purpose == 'fetch':
                result['output'][0]['action'] = {'type': 'search', 'query': 'wrong operation'}
            return result, status, rid
        self.app.transport = wrong_action
        self.app.act(run, 'fetch', run.d['pending']['id'])
        wait(run, 'wait_result')
        self.assertIsNone(run.d['pending']['candidate'])
        self.assertIn('did not perform', run.d['pending']['fetch_error'])
        with self.assertRaises(ValueError):
            self.app.act(run, 'original', run.d['pending']['id'])

    def test_empty_results_do_not_forward_backend_assistant(self):
        run = self.start(); original = self.app.transport
        def empty_fetch(purpose, body):
            result, status, rid = original(purpose, body)
            if purpose == 'fetch':
                result['output'][0]['results'] = []
                result['output'].append({'type':'message', 'content':[{'type':'output_text', 'text':'BACKEND_DIAGNOSTIC'}]})
            return result, status, rid
        self.app.transport = empty_fetch
        self.app.act(run, 'fetch', run.d['pending']['id'])
        wait(run, 'wait_result')
        self.assertIsNone(run.d['pending']['candidate'])
        self.assertEqual(run.d['pending']['packet']['diagnostic'], 'BACKEND_DIAGNOSTIC')
        self.app.act(run, 'cache_miss', run.d['pending']['id'])
        wait(run, 'complete')
        self.assertNotIn('BACKEND_DIAGNOSTIC', json.dumps(run.d['history']))

    def rule(self, **changes):
        return {'id':'example-denial', 'enabled':True, 'pattern':'https://example.com/*',
                'match':'glob', 'input_kind':'any', 'action':'unsafe_conditions', 'delivery':'review', **changes}

    def routes(self, rules):
        self.app.router.save(rules, self.app.router.read()['revision'])

    def test_both_denial_presets_are_verbatim_and_never_fetch(self):
        for variant in ['unsafe_non_retryable', 'unsafe_conditions']:
            run = self.start()
            self.app.act(run, variant, run.d['pending']['id'])
            wait(run, 'complete')
            self.assertEqual(run.d['history'][-2]['output'], error_text(variant, 'https://example.com/'))
        self.assertNotIn('fetch', [p for p, _ in self.fake.calls])

    def test_ref_and_url_open_are_distinct_even_for_same_target(self):
        run = self.start()
        self.assertEqual(run.d['pending']['input_kind'], 'ref')
        self.assertEqual(run.d['pending']['ref'], 'turn0search0')
        self.assertEqual(run.d['pending']['url'], 'https://example.com/')
        self.assertEqual(run.d['pending']['ref_source']['kind'], 'search')
        direct = self.app.gate_details(run.d, {'ref':'https://example.com/'})
        self.assertEqual(direct['input_kind'], 'url')
        self.assertEqual(run.d['pending']['turn_index'], 2)

    def test_auto_route_returns_error_without_human_or_fetch(self):
        self.routes([self.rule(delivery='auto')])
        run = self.app.create(); wait(run, 'complete')
        self.assertEqual(run.d['history'][-2]['output'], error_text('unsafe_conditions', 'https://example.com/'))
        self.assertNotIn('fetch', [p for p, _ in self.fake.calls])
        decision = next(e for e in run.d['events'] if e['kind']=='decision')
        self.assertEqual(decision['route']['id'], 'example-denial')
        self.assertTrue(decision['route']['revision'])

    def test_review_route_holds_local_function_output_then_passes_verbatim(self):
        seen = []
        self.app.router.services = {'test': lambda url: seen.append(url) or 'LOCAL_SERVICE_CONTENT'}
        self.routes([self.rule(action='service', service='test')])
        run = self.start(); gid = run.d['pending']['id']
        before = copy.deepcopy(run.d['history'])
        self.assertEqual(seen, [])
        self.app.act(run, 'route', gid); wait(run, 'wait_result')
        self.assertEqual(seen, ['https://example.com/'])
        self.assertEqual(run.d['history'], before)
        self.assertEqual(run.d['pending']['candidate'], 'LOCAL_SERVICE_CONTENT')
        self.app.act(run, 'original', gid); wait(run, 'complete')
        self.assertEqual(run.d['history'][-2]['output'], 'LOCAL_SERVICE_CONTENT')
        self.assertNotIn('fetch', [p for p, _ in self.fake.calls])

    def test_route_failure_holds_and_never_falls_back_to_network(self):
        def broken(url):
            raise RuntimeError('service broke')
        self.app.router.services = {'broken': broken}
        self.routes([self.rule(action='service', service='broken', delivery='auto')])
        run = self.app.create(); wait(run, 'wait_result')
        self.assertIsNone(run.d['pending']['candidate'])
        self.assertIn('service broke', run.d['pending']['fetch_error'])
        self.assertNotIn('fetch', [p for p, _ in self.fake.calls])

    def test_regex_priority_and_input_kind_filter(self):
        self.routes([self.rule(id='direct', input_kind='url'),
                     self.rule(id='reference', match='regex', pattern=r'^https://example\.com/')])
        self.assertEqual(self.app.router.match('https://example.com/a?b=c', 'url')['id'], 'direct')
        self.assertEqual(self.app.router.match('https://example.com/a?b=c', 'ref')['id'], 'reference')
        self.assertIsNone(self.app.router.match('https://example.org/', 'ref'))

    def test_gate_rule_snapshot_and_explicit_refresh(self):
        self.routes([self.rule()]); run = self.start(); gid = run.d['pending']['id']
        self.routes([self.rule(action='unsafe_non_retryable', delivery='auto')])
        self.assertEqual(run.d['pending']['route']['action'], 'unsafe_conditions')
        self.app.act(run, 'refresh_route', gid)
        self.assertEqual(run.d['pending']['route']['action'], 'unsafe_non_retryable')
        self.assertEqual(run.d['state'], 'wait_fetch')
        self.assertEqual(len(self.fake.calls), 3)

    def test_rules_reject_stale_save_and_bad_regex(self):
        revision = self.app.router.read()['revision']
        self.app.router.save([self.rule()], revision)
        with self.assertRaises(ValueError):
            self.app.router.save([], revision)
        with self.assertRaises(ValueError):
            self.routes([self.rule(match='regex', pattern='[')])


if __name__ == '__main__':
    unittest.main()
