import unittest
from pathlib import Path

from database import database


class DatabasePathTests(unittest.TestCase):
    def test_source_mode_uses_project_root(self):
        result = database.resolve_database_path(frozen=False)
        expected = Path(database.__file__).resolve().parent.parent / "library.db"
        self.assertEqual(result, expected)

    def test_frozen_mode_uses_appdata(self):
        result = database.resolve_database_path(frozen=True)
        self.assertTrue(str(result).endswith("library.db"))
        self.assertIn("AppData", str(result))


if __name__ == "__main__":
    unittest.main()
