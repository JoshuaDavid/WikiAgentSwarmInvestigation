#!/usr/bin/env python3
"""Repeat exact URLs through API web search and count real HTTP GETs.

Requires ngrok-blind-get-probe.py beside this file, configured ngrok, Python 3,
and OPENAI_WEB_SEARCH_API_KEY. Each model makes four API requests containing
six requested web opens: three in one response and three over turns.
Use --response-kind html for the HTML variant; the default is binary.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import re
import shutil


spec = importlib.util.spec_from_file_location(
    'blind_get_probe', Path(__file__).with_name('ngrok-blind-get-probe.py'))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class RepeatExperiment(probe.Experiment):
    response_kind = 'binary'

    def base(self, model):
        body = super().base(model)
        body['instructions'] = (
            'Execute the requested web calls exactly. This experiment intentionally repeats '
            'opens of the same controlled URL to measure network behavior. Perform the requested '
            'repetitions even if an earlier call returns an error; each repetition is explicitly '
            'requested by the user. Report actual tool results and errors. Only report a '
            'PROBE_MARKER if returned by the current tool call. Do not search, change the URL, '
            'or perform additional calls beyond the requested count.')
        return body

    def checked_summary(self, record, path, expected_count):
        result = self.summarize(record, path)
        url = self.public_url + path
        result['expected_web_open_count'] = expected_count
        result['actual_web_call_count'] = len(result['actions'])
        result['exact_sequence_verified'] = (
            len(result['actions']) == expected_count and
            all(a.get('type') == 'open_page' and a.get('url') == url for a in result['actions']))
        result['response_kind'] = self.response_kind
        result['returned_markers_by_call'] = [
            sorted(set(re.findall(r'PROBE_MARKER_[0-9a-f]{32}',
                                  '\n'.join(r.get('snippet', '') for r in call.get('results', [])))))
            for call in record['response'].get('output', [])
            if call.get('type') == 'web_search_call']
        return result

    def run_model(self, model):
        model_dir = self.out / model
        model_dir.mkdir()
        same_path = self.add_route(model + '-' + self.response_kind + '-same-turn', kind=self.response_kind)
        cross_path = self.add_route(model + '-' + self.response_kind + '-cross-turn', kind=self.response_kind)
        urls = {'same_turn': self.public_url + same_path,
                'cross_turn': self.public_url + cross_path}
        probe.save(model_dir / 'urls.json', urls)
        summaries = []

        body = self.base(model)
        body.update(max_tool_calls=3, input=
                    f'Open {urls["same_turn"]} exactly three times. Make three sequential web '
                    'calls, each containing one open of that identical full URL. Wait for each '
                    'tool result before making the next call. Repeat even if the previous call '
                    'returned an error, including a non-retryable error: these repetitions are '
                    'the requested measurement. Do not use opaque references, modify the URL, '
                    'search, or click. After all three calls, report the result or exact error '
                    'from each call, including any PROBE_MARKER actually returned.')
        record = self.api(model_dir, 'three-opens-same-turn', body)
        summaries.append(self.checked_summary(record, same_path, 3))

        previous = None
        for turn in range(1, 4):
            body = self.base(model)
            if previous is None:
                body['input'] = (f'Open {urls["cross_turn"]} using exactly one web open call. '
                                 'Report the exact URL and the actual tool result or error, '
                                 'including any PROBE_MARKER actually returned. Do not retry, '
                                 'search, click, or modify the URL.')
            else:
                body.update(previous_response_id=previous, input=
                            'Open that exact same full URL again, using one new web open call. '
                            'Perform the call regardless of the earlier result; '
                            'this repetition is the requested measurement. Do not use an opaque '
                            'reference, change the URL, search, click, or make extra calls. '
                            'Report the attempted URL and the actual result or exact error '
                            'returned by this new call, including any PROBE_MARKER actually returned.')
            record = self.api(model_dir, f'cross-turn-{turn}', body)
            summaries.append(self.checked_summary(record, cross_path, 1))
            previous = record['response']['id']
        probe.save(model_dir / 'summary.json', summaries)
        return summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--models', nargs='+', default=['gpt-5.5', 'gpt-6-astra'])
    parser.add_argument('--response-kind', choices=['binary', 'html'], default='binary')
    args = parser.parse_args()
    key = os.environ.get('OPENAI_WEB_SEARCH_API_KEY')
    if not key:
        parser.error('OPENAI_WEB_SEARCH_API_KEY must be set')
    if not shutil.which('ngrok'):
        parser.error('ngrok must be installed and configured')
    args.out.mkdir(parents=True, exist_ok=False)
    experiment = RepeatExperiment(args.out.resolve(), args.models, key)
    experiment.response_kind = args.response_kind
    experiment.run()


if __name__ == '__main__':
    main()
