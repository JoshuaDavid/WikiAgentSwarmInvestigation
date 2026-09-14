import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("cache_age_bounds.py")
SPEC = importlib.util.spec_from_file_location("cache_age_bounds", MODULE_PATH)
assert SPEC and SPEC.loader
bounds = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bounds)


class CacheAgeBoundsTests(unittest.TestCase):
    def test_day_bound_has_correct_endpoint_semantics(self) -> None:
        result = bounds.implied_bounds(
            bounds.parse_time("2026-09-11T12:00:00Z"), "3 days ago"
        )
        self.assertEqual("2026-09-07T12:00:00.000Z", result["lower_utc"])
        self.assertEqual("2026-09-08T12:00:00.000Z", result["upper_utc"])
        self.assertFalse(result["lower_inclusive"])
        self.assertTrue(result["upper_inclusive"])
        self.assertEqual(86_400_000, result["width_ms"])

    def test_uncertainty_expands_both_ends(self) -> None:
        result = bounds.implied_bounds(1_000_000_000, "1 hour ago", 250)
        self.assertEqual(3_600_500, result["width_ms"])

    def test_month_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "provider model"):
            bounds.implied_bounds(1_000_000_000, "2 months ago")

    def test_intersection_narrows_and_preserves_open_lower(self) -> None:
        first = bounds.implied_bounds(1_000_000_000, "1 day ago")
        second = bounds.implied_bounds(1_000_003_000, "1 day ago")
        result = bounds.intersection([first, second])
        self.assertEqual("bounded", result["status"])
        self.assertEqual(first["lower_unix_ms"] + 3_000,
                         result["lower_unix_ms"])
        self.assertEqual(first["upper_unix_ms"], result["upper_unix_ms"])
        self.assertFalse(result["lower_inclusive"])

    def test_empty_intersection_is_conflict(self) -> None:
        first = bounds.implied_bounds(1_000_000_000, "1 day ago")
        second = bounds.implied_bounds(2_000_000_000, "1 day ago")
        result = bounds.intersection([first, second])
        self.assertEqual("conflict", result["status"])
        self.assertIsNone(result["width_ms"])


if __name__ == "__main__":
    unittest.main()
