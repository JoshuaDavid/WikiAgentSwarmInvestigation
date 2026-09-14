import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("server.py")
SPEC = importlib.util.spec_from_file_location("search_ui_server", MODULE_PATH)
assert SPEC and SPEC.loader
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


class SearchResultParserTests(unittest.TestCase):
    def test_extracts_result_display_fields(self) -> None:
        text = """First title (https://example.com/a)
citeturn0search0 [wordlim: 200] Crawled: 2 months ago; Published: Jan 2, 2026; snippet
body cite12†Documentation†docs.example.com
again cite12†Documentation†docs.example.com
cite13†About†example.com
--------------------------------------------------------------------------------
Second title (https://other.example/b)
citeturn0search1 [wordlim: 200] Cached: yesterday; snippet"""
        results = server.parse_search_results(text)
        self.assertEqual(2, len(results))
        self.assertEqual("First title", results[0]["title"])
        self.assertEqual("https://example.com/a", results[0]["url"])
        self.assertEqual("2 months ago", results[0]["cached_at"])
        self.assertEqual("Crawled", results[0]["cache_field"])
        self.assertEqual("Jan 2, 2026", results[0]["published_at"])
        self.assertEqual("turn0search0", results[0]["ref_id"])
        self.assertEqual(2, results[0]["child_link_count"])
        self.assertEqual(
            {"link_id": 12, "anchor_text": "Documentation",
             "hostname_hint": "docs.example.com", "url": None},
            results[0]["child_links"][0],
        )
        self.assertEqual("yesterday", results[1]["cached_at"])
        self.assertEqual("Cached", results[1]["cache_field"])

    def test_extracts_bracket_and_truncated_child_links(self) -> None:
        text = """Title (https://example.com/)
citeturn0search0 Crawled: today;
【4†Reader†jina.ai】 and https://child.example/path, then 【5†truncated anchor--------------------------------------------------------------------------------
Next (https://next.example/)
citeturn0search1 Crawled: yesterday;"""
        results = server.parse_search_results(text)
        self.assertEqual(2, len(results))
        self.assertEqual(3, results[0]["child_link_count"])
        self.assertEqual("jina.ai", results[0]["child_links"][0]["hostname_hint"])
        self.assertEqual("truncated anchor", results[0]["child_links"][1]["anchor_text"])
        self.assertIsNone(results[0]["child_links"][1]["hostname_hint"])
        self.assertEqual("https://child.example/path",
                         results[0]["child_links"][2]["url"])

    def test_primary_result_url_is_not_a_child(self) -> None:
        results = server.parse_search_results(
            "Title (https://example.com/)\n"
            "citeturn0search0 Crawled: today; https://example.com/ "
            "https://child.example/a https://child.example/a"
        )
        self.assertEqual(1, results[0]["child_link_count"])


if __name__ == "__main__":
    unittest.main()
