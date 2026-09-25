"""First matching URL rule wins. Local services are plain functions URL -> text."""
import copy
import fnmatch
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import threading

from tool_errors import PRESETS, error_text


class Router:
    def __init__(self, path, services_path=None, services=None):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.services = services or {}
        if services_path:
            spec = importlib.util.spec_from_file_location('web_gate_local_services', services_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.services = module.SERVICES
        if not isinstance(self.services, dict) or not all(isinstance(k, str) and callable(v) for k, v in self.services.items()):
            raise ValueError('SERVICES must map service names to callable(url) handlers.')

    def validate(self, rules):
        if not isinstance(rules, list) or len(rules) > 50:
            raise ValueError('Expected at most 50 URL rules.')
        ids = set()
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValueError('Each rule must be an object.')
            if not isinstance(rule.get('id'), str) or not rule['id'] or rule['id'] in ids:
                raise ValueError('Rules need unique, nonempty IDs.')
            ids.add(rule['id'])
            if not isinstance(rule.get('pattern'), str) or not 0 < len(rule['pattern']) <= 2000:
                raise ValueError('Each rule needs a URL pattern of 1–2000 characters.')
            if rule.get('match') not in {'glob', 'regex'} or rule.get('input_kind') not in {'any', 'url', 'ref'}:
                raise ValueError('Use glob/regex matching and any/url/ref input kind.')
            if rule.get('delivery') not in {'review', 'auto'} or not isinstance(rule.get('enabled'), bool):
                raise ValueError('Rules need review/auto delivery and a boolean enabled flag.')
            if rule.get('action') not in {*PRESETS, 'service'}:
                raise ValueError('Unknown route action.')
            if rule['action'] == 'service' and rule.get('service') not in self.services:
                raise ValueError('Unknown local service: ' + str(rule.get('service')))
            if rule['match'] == 'regex':
                try:
                    re.compile(rule['pattern'])
                except re.error as exc:
                    raise ValueError('Invalid URL regex: ' + str(exc)) from None
        return copy.deepcopy(rules)

    def read(self):
        with self.lock:
            data = json.loads(self.path.read_text()) if self.path.exists() else {'rules': []}
            rules = self.validate(data['rules'])
            revision = hashlib.sha256(json.dumps(rules, sort_keys=True).encode()).hexdigest()[:16]
            return {'rules': rules, 'revision': revision, 'services': sorted(self.services)}

    def save(self, rules, revision):
        with self.lock:
            if self.read()['revision'] != revision:
                raise ValueError('Routes changed elsewhere. Reload before saving.')
            rules = self.validate(rules)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix('.tmp')
            temp.write_text(json.dumps({'rules': rules}, indent=2) + '\n')
            temp.replace(self.path)
            return self.read()

    def match(self, url, input_kind):
        config = self.read()
        if not url:
            return None
        for rule in config['rules']:
            if not rule['enabled'] or rule['input_kind'] not in {'any', input_kind}:
                continue
            matched = (fnmatch.fnmatchcase(url, rule['pattern']) if rule['match'] == 'glob'
                       else re.search(rule['pattern'], url) is not None)
            if matched:
                return {**rule, 'revision': config['revision']}
        return None

    def execute(self, rule, url):
        if rule['action'] in PRESETS:
            return error_text(rule['action'], url)
        result = self.services[rule['service']](url)
        if not isinstance(result, str) or len(result) > 500000:
            raise ValueError('A local service must return a text string of at most 500,000 characters.')
        return result
