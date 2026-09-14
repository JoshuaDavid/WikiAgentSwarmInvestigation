import importlib.util
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("orchestrator.py")
SPEC = importlib.util.spec_from_file_location("dating_orchestrator", MODULE_PATH)
assert SPEC and SPEC.loader
dating = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dating)


class ParsingTests(unittest.TestCase):
    def test_parse_exact_result_and_age(self) -> None:
        text = ("Wanted (https://example.com/a)\n"
                "cite Crawled: 3 days ago; snippet\n"
                + "-" * 40 + "\n"
                "Other (https://example.com/b)\nCached: 2 weeks ago;")
        results = dating.parse_results(text)
        self.assertEqual("https://example.com/a", results[0]["page_url"])
        self.assertEqual("3 days ago", results[0]["raw_cache_age"])
        self.assertEqual("Cached", results[1]["cache_field"])

    def test_make_observation_uses_request_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run = dating.DatingRun("test")
            run.path = Path(directory)
            (run.path / "observations.jsonl").touch()
            probe = {"probe_id": "p1", "target_id": "t1",
                     "series_id": "web-default"}
            target = {"query": "needle", "page_url": "https://example.com/a",
                      "title_contains": "Want"}
            observation = run.make_observation(
                probe, target,
                "Wanted (https://example.com/a)\nCrawled: 1 day ago;", 1000, 3000,
                "raw/search_1.txt", 0
            )
            self.assertEqual("exact", observation["match_status"])
            self.assertEqual(2000, observation["retrieved_at_unix_ms"])
            self.assertEqual(1000, observation["clock_uncertainty_ms"])
            self.assertIn("implied_lower_unix_ms", observation)

    def test_stdout_summary_includes_match_and_raw_path(self) -> None:
        run = dating.DatingRun("test")
        run.path = Path("/tmp/example-dating-run")
        observation = {"probe_id": "p1", "target_id": "t1",
                       "match_status": "exact", "cache_field": "Crawled",
                       "raw_cache_age": "3 days ago",
                       "raw_response": "raw/search_000001.txt",
                       "returned_results": [{}]}
        output = StringIO()
        with redirect_stdout(output):
            dating.print_observation(run, observation, False)
            dating.print_batch_summary([observation])
        self.assertIn("status=exact", output.getvalue())
        self.assertIn("Crawled: 3 days ago", output.getvalue())
        self.assertIn("batch complete: probes=1 exact=1", output.getvalue())

    def test_structured_results_preserve_cache_metadata(self) -> None:
        document = {"output": [{"type": "web_search_call", "results": [{
            "type": "text_result", "title": "Wanted",
            "url": "https://example.com/a",
            "snippet": "Published: last month; Crawled: 4 days ago; body",
        }]}]}
        result = dating.parse_structured_results(document)[0]
        self.assertEqual("https://example.com/a", result["page_url"])
        self.assertEqual("Crawled", result["cache_field"])
        self.assertEqual("4 days ago", result["raw_cache_age"])

    def test_responses_request_disables_external_access(self) -> None:
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def read(self):
                return b'{"output":[]}'

        captured = {}

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data)
            captured["timeout"] = timeout
            return Response()

        with patch.object(dating.urllib.request, "urlopen", fake_urlopen):
            body, before, after = dating.responses_search("needle", "secret")
        self.assertEqual(b'{"output":[]}', body)
        tool = captured["payload"]["tools"][0]
        self.assertEqual("web_search", tool["type"])
        self.assertIs(False, tool["external_web_access"])
        self.assertIn("web_search_call.results", captured["payload"]["include"])
        self.assertLessEqual(before, after)


class RunStateTests(unittest.TestCase):
    def test_init_add_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run = dating.DatingRun("test")
            run.path = Path(directory) / "test"
            run.init(86_400_000, True)
            with patch.object(dating, "now_ms", return_value=1234):
                run.add_target("t1", "needle", "https://example.com/a", None,
                               "web-default")
            status = run.status()
            self.assertEqual(1, status["target_count"])
            self.assertEqual(1, status["schedule"]["pending"])
            self.assertEqual(1234, status["next_probe_at"])
            events = dating.read_jsonl(run.path / "events.jsonl")
            self.assertEqual(["target_registered", "probe_scheduled"],
                             [row["event_type"] for row in events])

    def test_unparsed_month_label_schedules_monitor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run = dating.DatingRun("test")
            run.path = Path(directory) / "test"
            run.init(86_400_000, False)
            run.add_target("t1", "needle", "https://example.com/a", None,
                           "web-default")
            schedule = dating.read_jsonl(run.path / "schedule.jsonl")
            schedule[0]["state"] = "complete"
            dating.write_jsonl(run.path / "schedule.jsonl", schedule)
            dating.write_jsonl(run.path / "observations.jsonl", [{
                "observation_id": "o1", "target_id": "t1",
                "series_id": "web-default", "match_status": "exact",
                "raw_cache_age": "2 months ago", "parse_error": "unsupported",
            }])
            run.rematerialize()
            schedule = dating.read_jsonl(run.path / "schedule.jsonl")
            self.assertEqual("coarse_or_unparsed_label_monitor",
                             schedule[-1]["reason"])
            self.assertEqual("pending", schedule[-1]["state"])

    def test_unverified_narrow_bound_is_not_completed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run = dating.DatingRun("test")
            run.path = Path(directory) / "test"
            run.init(86_400_000, False)
            run.add_target("t1", "needle", "https://example.com/a", None,
                           "web-default")
            schedule = dating.read_jsonl(run.path / "schedule.jsonl")
            schedule[0]["state"] = "complete"
            dating.write_jsonl(run.path / "schedule.jsonl", schedule)
            dating.write_jsonl(run.path / "observations.jsonl", [{
                "observation_id": "o1", "target_id": "t1",
                "series_id": "web-default", "parsed_value": 1,
                "parsed_unit": "day", "implied_lower_unix_ms": 0,
                "implied_lower_inclusive": False,
                "implied_upper_unix_ms": 86_400_000,
                "implied_upper_inclusive": True,
            }])
            run.rematerialize()
            estimate = dating.read_jsonl(run.path / "estimates.jsonl")[0]
            self.assertEqual("unverified_model", estimate["status"])
            self.assertEqual(1, sum(row["state"] == "pending" for row in
                                    dating.read_jsonl(run.path / "schedule.jsonl")))

    def test_interrupted_claim_is_requeued(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run = dating.DatingRun("test")
            run.path = Path(directory) / "test"
            run.init(86_400_000, True)
            run.add_target("t1", "needle", "https://example.com/a", None,
                           "web-default")
            schedule = dating.read_jsonl(run.path / "schedule.jsonl")
            schedule[0]["state"] = "running"
            dating.write_jsonl(run.path / "schedule.jsonl", schedule)
            run.recover_running()
            self.assertEqual("pending", dating.read_jsonl(
                run.path / "schedule.jsonl")[0]["state"])

    def test_bulk_import_is_atomic_on_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run = dating.DatingRun("test")
            run.path = Path(directory) / "test"
            run.init(86_400_000, True)
            rows = [
                {"target_id": "same", "query": "one",
                 "page_url": "https://example.com/1"},
                {"target_id": "same", "query": "two",
                 "page_url": "https://example.com/2"},
            ]
            with self.assertRaisesRegex(ValueError, "duplicate target ID"):
                run.add_targets(rows)
            self.assertEqual([], dating.read_jsonl(run.path / "targets.jsonl"))
            self.assertEqual([], dating.read_jsonl(run.path / "schedule.jsonl"))

    def test_bulk_file_requires_exact_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "targets.jsonl"
            path.write_text(json.dumps({"target_id": "t", "query": "q",
                                        "page_url": "https://example.com",
                                        "extra": 1}) + "\n")
            with self.assertRaisesRegex(ValueError, "exactly"):
                dating.read_target_import(path)


if __name__ == "__main__":
    unittest.main()
