import tempfile
import unittest
from pathlib import Path

import worker_pool


class CollectSeedsTests(unittest.TestCase):
    def test_file_ignores_blank_lines_and_trims_seeds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "seeds.txt"
            path.write_text("first seed\n\n  second seed  \n", encoding="utf-8")
            self.assertEqual(worker_pool.collect_seeds(None, str(path)),
                             ["first seed", "second seed"])

    def test_file_and_inline_seeds_are_combined(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "seeds.txt"
            path.write_text("from file\n", encoding="utf-8")
            self.assertEqual(worker_pool.collect_seeds(["inline"], str(path)),
                             ["inline", "from file"])

    def test_search_only_workers_partition_instead_of_replicating(self) -> None:
        self.assertEqual(worker_pool.initial_search_layout(10, True), (10, 1))
        self.assertEqual(worker_pool.initial_search_layout(10, False), (1, 10))


if __name__ == "__main__":
    unittest.main()
