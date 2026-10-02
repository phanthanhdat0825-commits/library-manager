import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from database import database


class RemoteLoanIdempotencyTests(unittest.TestCase):
    def test_retry_does_not_create_second_loan_or_decrement_again(self):
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "library.db"
            with patch.object(database, "DATABASE_PATH", database_path):
                database.initialize_database()
                database.add_reader("RD-01", "Nguyen Van A")
                database.add_book("BK-01", "Sách thử", "", "", "", None, 3, "", "")
                reader_id = database.get_all_readers()[0]["id"]
                book_id = database.get_all_books()[0]["id"]

                first_loan_id = database.create_loan(
                    reader_id, "2026-09-26", "2026-10-10", [(book_id, 2)],
                    remote_request_id=41,
                )
                retry_loan_id = database.create_loan(
                    reader_id, "2026-09-26", "2026-10-10", [(book_id, 2)],
                    remote_request_id=41,
                )

                self.assertEqual(first_loan_id, retry_loan_id)
                self.assertEqual(database.get_all_books()[0]["quantity"], 1)
                self.assertEqual(len(database.get_all_loans()), 1)


if __name__ == "__main__":
    unittest.main()
