import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add parent directories to import path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from memories_to_ics import convert, fold, ics_datetime, ics_text, stamp


class TestMemoriesToIcs(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dir_path = Path(self.temp_dir.name)
        self.out_ics = self.dir_path / "test.ics"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_ics_text_escaping(self):
        self.assertEqual(ics_text("hello;world,here\\now\nnext"), "hello\\;world\\,here\\\\now\\nnext")
        self.assertEqual(ics_text(None), "")
        self.assertEqual(ics_text(123), "123")

    def test_ics_datetime(self):
        dt = ics_datetime("2026-09-20T10:30:00Z")
        self.assertIsNotNone(dt)
        self.assertEqual(stamp(dt), "20260920T103000Z")
        self.assertIsNone(ics_datetime("invalid"))
        self.assertIsNone(ics_datetime(None))

    def test_fold_lines(self):
        short = "SUMMARY:Short line"
        self.assertEqual(fold(short), [short])

        long_line = "DESCRIPTION:" + "A" * 100
        folded = fold(long_line)
        self.assertGreater(len(folded), 1)
        self.assertTrue(folded[1].startswith(" "))

    def test_path_traversal_rejected(self):
        sample = [{"id": "m1", "content": "Memory", "created_at": "2026-09-20T10:00:00Z"}]
        json_file = self.dir_path / "data.json"
        json_file.write_text(json.dumps(sample), encoding="utf-8")

        with self.assertRaises(ValueError):
            convert(str(self.dir_path / ".." / "escape.ics"), [str(json_file)])

    def test_convert_generates_valid_vcalendar(self):
        sample = [
            {
                "id": "mem_101",
                "content": "Prefers dark mode in IDE",
                "category": "preferences",
                "created_at": "2026-09-20T10:30:00Z",
            },
            {
                "id": "mem_102",
                "content": "Follow up with client regarding milestone 2",
                "category": "work",
                "created_at": "2026-09-20T14:00:00Z",
            },
        ]
        json_file = self.dir_path / "memories.json"
        json_file.write_text(json.dumps(sample), encoding="utf-8")

        count = convert(str(self.out_ics), [str(json_file)])
        self.assertEqual(count, 2)

        content = self.out_ics.read_text(encoding="utf-8")
        self.assertIn("BEGIN:VCALENDAR", content)
        self.assertIn("VERSION:2.0", content)
        self.assertIn("UID:mem_101@omi.me", content)
        self.assertIn("UID:mem_102@omi.me", content)
        self.assertIn("SUMMARY:[Preferences] Prefers dark mode in IDE", content)
        self.assertIn("CATEGORIES:PREFERENCES", content)
        self.assertIn("END:VCALENDAR", content)

    def test_deduplication(self):
        sample1 = [{"id": "dup_1", "content": "First", "created_at": "2026-09-20T10:00:00Z"}]
        sample2 = [{"id": "dup_1", "content": "Duplicate", "created_at": "2026-09-20T10:00:00Z"}]

        f1 = self.dir_path / "f1.json"
        f2 = self.dir_path / "f2.json"
        f1.write_text(json.dumps(sample1), encoding="utf-8")
        f2.write_text(json.dumps(sample2), encoding="utf-8")

        count = convert(str(self.out_ics), [str(f1), str(f2)])
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
