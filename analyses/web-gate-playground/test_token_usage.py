import copy
import unittest

from prompt_cache import cache_request
from token_usage import normalize, run_usage


class TokenUsageTests(unittest.TestCase):
    def usage(self, inputs=1000, outputs=100, reads=700, writes=200):
        return {'input_tokens':inputs, 'output_tokens':outputs, 'total_tokens':inputs+outputs,
                'input_tokens_details':{'cached_tokens':reads, 'cache_write_tokens':writes},
                'output_tokens_details':{'reasoning_tokens':30}}

    def event(self, rid, key, purpose, usage):
        return {'kind':'api', 'run_id':rid, 'request_key':key, 'purpose':purpose,
                'artifact':key+'.response.json', 'meta':{'usage':usage}}

    def test_input_categories_are_disjoint(self):
        result=normalize(self.usage())
        self.assertEqual(result['ordinary_input_tokens'],100)
        self.assertEqual(result['cache_read_tokens'],700)
        self.assertEqual(result['cache_write_tokens'],200)
        self.assertEqual(result['input_tokens'],1000)
        self.assertEqual(result['total_tokens'],1100)
        self.assertEqual(result['reasoning_tokens'],30)

    def test_missing_write_not_inferred_from_uncached_input(self):
        usage=self.usage();del usage['input_tokens_details']['cache_write_tokens']
        result=normalize(usage)
        self.assertIsNone(result['cache_write_tokens'])
        self.assertIsNone(result['ordinary_input_tokens'])
        self.assertEqual(result['cache_read_tokens'],700)

    def test_explicit_zero_and_no_report_are_different(self):
        self.assertIsNone(normalize(None)['cache_read_tokens'])
        self.assertEqual(normalize(self.usage(reads=0,writes=0))['cache_read_tokens'],0)

    def test_fork_counts_only_own_requests(self):
        data={'id':'child','request_count':1,'events':[
            self.event('parent','001-agent','agent',self.usage(inputs=10000)),
            self.event('child','001-agent','agent',self.usage())]}
        result=run_usage(data)
        self.assertEqual(result['totals']['input_tokens'],1000)
        self.assertEqual(result['by_purpose']['agent']['requests'],1)

    def test_partial_usage_marks_report_coverage(self):
        partial=self.usage();del partial['input_tokens_details']['cache_write_tokens']
        data={'id':'run','request_count':3,'events':[
            self.event('run','001-agent','agent',self.usage()),
            self.event('run','002-fetch','fetch',partial),
            {'kind':'api','run_id':'run','purpose':'search','artifact':'003-search.request.json'}]}
        result=run_usage(data)
        self.assertEqual(result['totals']['input_tokens'],2000)
        self.assertEqual(result['reported_requests']['input_tokens'],2)
        self.assertEqual(result['totals']['cache_write_tokens'],200)
        self.assertEqual(result['reported_requests']['cache_write_tokens'],1)
        self.assertIsNone(result['by_purpose']['search']['totals']['input_tokens'])

    def test_demo_zero_requests_has_zero_usage(self):
        result=run_usage({'id':'demo','request_count':0,'events':[]})
        self.assertEqual(result['totals']['input_tokens'],0)
        self.assertEqual(result['totals']['cache_read_tokens'],0)

    def test_duplicate_response_event_not_double_counted(self):
        event=self.event('run','001-agent','agent',self.usage())
        result=run_usage({'id':'run','request_count':1,'events':[event,copy.deepcopy(event)]})
        self.assertEqual(result['totals']['input_tokens'],1000)

    def test_cache_key_stable_across_continuations_and_forks(self):
        body={'model':'gpt-5.6-luna','tools':[{'type':'function','name':'web-run'}],
              'input':[{'role':'user','content':'first prompt'}],'store':False}
        first=cache_request(body,'agent')
        later=cache_request({**body,'input':[{'role':'user','content':'other prompt'}]},'agent')
        self.assertEqual(first['prompt_cache_key'],later['prompt_cache_key'])
        self.assertEqual(first['input'],body['input'])
        self.assertNotIn('prompt_cache_key',body)
        self.assertFalse(first['store'])
        self.assertEqual(first['prompt_cache_options'],{'mode':'implicit','ttl':'30m'})

    def test_cache_key_separates_model_tools_and_request_role(self):
        body={'model':'gpt-5.6-luna','tools':[]}
        keys=[cache_request(body,'agent')['prompt_cache_key'],
              cache_request(body,'search')['prompt_cache_key'],
              cache_request({**body,'model':'gpt-6-astra'},'agent')['prompt_cache_key'],
              cache_request({**body,'tools':[{'type':'web_search'}]},'agent')['prompt_cache_key']]
        self.assertEqual(len(set(keys)),4)


if __name__=='__main__':
    unittest.main()
