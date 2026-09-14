#!/usr/bin/env python3
"""Regression tests for transferring agent-local WebRun ref chains."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("orchestrator.py")
SPEC = importlib.util.spec_from_file_location("spider_orchestrator", MODULE_PATH)
assert SPEC and SPEC.loader
orchestrator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(orchestrator)


class RouteRehydrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="spider-route-test-")
        self.run_dir = Path(self.tempdir.name)
        for child in (self.run_dir / "logs", self.run_dir / "raw" / "hooks"):
            child.mkdir(parents=True)
        db = orchestrator.sqlite3.connect(self.run_dir / "state.sqlite3",
                                          isolation_level=None)
        db.executescript(orchestrator.SCHEMA)
        db.executemany(
            "INSERT INTO meta(key,value) VALUES(?,?)",
            [("max_pages", "100"), ("max_calls_per_agent", "0"),
             ("direct_url_opens", "0")],
        )
        db.close()
        self.state = orchestrator.State(self.run_dir)

    def tearDown(self) -> None:
        self.state.close()
        self.tempdir.cleanup()

    def test_no_outbound_prefixes_are_host_bounded(self) -> None:
        for url in (
            "https://swarm.termina.digital/db/page.html",
            "http://swarm.termina.digital/",
            "https://collusion.wiki/path",
            "http://collusion.wiki:8080/path",
        ):
            self.assertTrue(orchestrator.suppress_outbound_links(url), url)
        for url in (
            "https://swarm.termina.digital.example/path",
            "https://collusion.wiki.example/path",
            "https://example.com/?next=https://collusion.wiki",
        ):
            self.assertFalse(orchestrator.suppress_outbound_links(url), url)

    def test_result_splitter_preserves_markdown_heading_rules(self) -> None:
        body = "Heading\n---------------------------\nbody"
        other = "Second result"
        text = body + "\n" + ("-" * 80) + "\n" + other
        self.assertEqual([body, other], orchestrator.result_sections(text))

    def test_search_only_does_not_queue_result_opens(self) -> None:
        self.state.db.execute(
            "INSERT OR REPLACE INTO meta(key,value) VALUES('search_only','1')"
        )
        self.state.add_operation(
            "search", {"search_query": [{"q": "swarm"}], "response_length": "long"},
            None, None,
        )
        search = self.state.lease("agent-a")
        self.commit(search, "agent-a", """
https://target.example/a
Published: January 1, 2026
citeturn0search0
Source: search({"q":"swarm"})
""")
        self.assertEqual(
            0,
            self.state.db.execute(
                "SELECT COUNT(*) FROM operations WHERE kind='open'"
            ).fetchone()[0],
        )

    def test_click_selection_rejects_noise_prioritizes_and_caps(self) -> None:
        details = {
            1: ("[email protected]", None),
            2: ("Image: logo", None),
            3: (None, None),
            4: ("ordinary page", "example.com"),
            5: ("https://md.succ.ai/?url=x", "md.succ.ai"),
            **{link_id: (f"page {link_id}", "example.com")
               for link_id in range(6, 40)},
        }
        selected, rejected = orchestrator.select_click_links(details, 7)
        self.assertEqual(25, len(selected))
        self.assertEqual(5, selected[0])
        self.assertNotIn(1, selected)
        self.assertNotIn(2, selected)
        self.assertNotIn(3, selected)
        self.assertEqual(1, rejected["email_anchor"])
        self.assertEqual(1, rejected["non_navigation_anchor"])
        self.assertEqual(1, rejected["missing_anchor_and_hostname"])
        self.assertGreater(rejected["parent_link_cap"], 0)

    def commit(self, row, agent: str, result: str) -> None:
        self.state.parse_result(row, agent, result)
        self.state.db.execute(
            "UPDATE operations SET state='committed',owner_agent_id=? WHERE operation_id=?",
            (agent, row["operation_id"]),
        )

    def test_replacement_worker_replays_full_chain(self) -> None:
        root_input = {"search_query": [{"q": "swarm"}],
                      "response_length": "long"}
        self.state.add_operation("search", root_input, None, None)
        search = self.state.lease("agent-a")
        self.commit(search, "agent-a", """
https://target.example/a
Published: January 1, 2026
citeturn0search0
Source: search({"q":"swarm"})
""")

        open_a = self.state.lease("agent-a")
        self.commit(open_a, "agent-a", """
https://target.example/a
Cached: 2 months ago
SECcountyM
citeturn1view0
cite7†next page†target.example
Source: open({"ref_id":"turn0search0"})
""")

        click_b = self.state.lease("agent-a")
        self.commit(click_b, "agent-a", """
https://target.example/b
Crawled: last week
SECcountyF
citeturn2view0
cite9†tip link†target.example
Source: click({"ref_id":"turn1view0","id":7})
""")

        pending = self.state.lease("agent-a")
        self.assertEqual("click", pending["kind"])
        self.assertIn('"id":9', pending["tool_input_json"])
        self.state.db.execute(
            "UPDATE operations SET state='ready',owner_agent_id=NULL,leased_at=NULL WHERE operation_id=?",
            (pending["operation_id"],),
        )

        self.state.db.execute(
            "INSERT INTO agents(agent_id,state,stop_attempts) VALUES('agent-a','active',0)"
        )
        stop_response = self.state.handle_stop({"agent_id": "agent-a"})
        self.assertEqual("allow", stop_response["action"])
        self.assertEqual(
            "cancelled",
            self.state.db.execute(
                "SELECT state FROM operations WHERE operation_id=?",
                (pending["operation_id"],),
            ).fetchone()[0],
        )

        replay_search = self.state.lease("agent-b")
        self.assertEqual("search", replay_search["kind"])
        self.commit(replay_search, "agent-b", """
https://target.example/a
Published: January 1, 2026
citeturn9search3
Source: search({"q":"swarm"})
""")

        replay_open = self.state.lease("agent-b")
        self.assertEqual({"open": [{"ref_id": "turn9search3"}],
                          "response_length": "long"},
                         orchestrator.json.loads(replay_open["tool_input_json"]))
        self.commit(replay_open, "agent-b", """
https://target.example/a
Cached: yesterday
SECcountyM
citeturn10view2
cite7†next page†target.example
Source: open({"ref_id":"turn9search3"})
""")

        replay_click = self.state.lease("agent-b")
        self.assertEqual({"click": [{"id": 7, "ref_id": "turn10view2"}],
                          "response_length": "long"},
                         orchestrator.json.loads(replay_click["tool_input_json"]))
        self.commit(replay_click, "agent-b", """
https://target.example/b
Crawled: today
SECcountyF
citeturn11view4
cite9†tip link†target.example
Source: click({"ref_id":"turn10view2","id":7})
""")

        restored_tip = self.state.lease("agent-b")
        self.assertEqual("click", restored_tip["kind"])
        self.assertEqual({"click": [{"id": 9, "ref_id": "turn11view4"}],
                          "response_length": "long"},
                         orchestrator.json.loads(restored_tip["tool_input_json"]))
        restored_capability = self.state.db.execute(
            "SELECT anchor_text,hostname_hint FROM capabilities WHERE agent_id='agent-b' AND parent_ref_id='turn11view4' AND link_id=9"
        ).fetchone()
        self.assertEqual(("tip link", "target.example"),
                         tuple(restored_capability))
        errors = self.state.enrich_internal_errors(
            "agent-b", restored_tip,
            'Internal Error\nSource: click({"ref_id":"turn11view4","id":9})',
        )
        self.assertEqual(
            [
                ("search", None, None),
                ("open", "turn9search3", None),
                ("click", "turn10view2", 7),
                ("click", "turn11view4", 9),
            ],
            [(hop["kind"], hop.get("ref_id", hop.get("parent_ref_id")),
              hop.get("link_id")) for hop in errors[0]["ref_chain"]],
        )
        composite = ("Internal Error ()\n"
                     "Source: click({\"ref_id\":\"turn11view4\",\"id\":9})\n"
                     "L0: Failed to fetch https://target.example/missing: Cache miss")
        compliant, has_internal_error, unknown = self.state.validate_result(
            restored_tip, composite
        )
        self.assertTrue(compliant)
        self.assertFalse(has_internal_error)
        self.assertEqual([], unknown)
        classified = self.state.enrich_internal_errors(
            "agent-b", restored_tip, composite
        )[0]
        self.assertEqual("cache_miss", classified["classification"])
        self.assertEqual("https://target.example/missing", classified["failed_url"])
        self.assertTrue(classified["destination_url_known"])
        hydration = self.state.db.execute(
            "SELECT state,owner_agent_id FROM hydrations"
        ).fetchone()
        self.assertEqual(("completed", "agent-b"), tuple(hydration))

    def test_stopped_replay_worker_restarts_from_search_root(self) -> None:
        route = {"root_search_input": {"search_query": [{"q": "swarm"}],
                                       "response_length": "long"},
                 "hops": [{"kind": "open", "old_ref_id": "turn0search0",
                            "expected_url": "https://target.example/a"}]}
        self.state.db.execute(
            "INSERT INTO hydrations(hydration_id,target_page_url,route_json,state,created_at) VALUES('hydrate_00000001','https://target.example/a',?,'ready',?)",
            (orchestrator.compact(route), orchestrator.now()),
        )
        self.state.add_hydration_operation(
            "search", route["root_search_input"], None, None,
            "hydrate_00000001", 0,
        )
        replay_search = self.state.lease("agent-b")
        self.commit(replay_search, "agent-b", """
https://target.example/a
Published: January 1, 2026
citeturn9search3
Source: search({"q":"swarm"})
""")
        replay_open = self.state.lease("agent-b")
        self.assertEqual("open", replay_open["kind"])
        self.state.db.execute(
            "INSERT INTO agents(agent_id,state,stop_attempts) VALUES('agent-b','active',0)"
        )

        response = self.state.handle_stop({"agent_id": "agent-b"})
        self.assertEqual("allow", response["action"])
        replacement_root = self.state.lease("agent-c")
        self.assertEqual("search", replacement_root["kind"])
        self.assertEqual("hydrate_00000001", replacement_root["hydration_id"])
        self.assertEqual(0, replacement_root["hydration_step"])


if __name__ == "__main__":
    unittest.main()
