import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import web_portal


class WebPortalTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "remote.db"
        self.path_patch = patch.object(web_portal, "REMOTE_DB_PATH", self.db_path)
        self.path_patch.start()
        web_portal.initialize_remote_database()
        web_portal.replace_catalog([{
            "book_code": "BK-01",
            "title": "Sách kiểm thử",
            "author": "Tác giả",
            "category": "Khoa học",
            "publisher": "Nhà xuất bản",
            "quantity": 3,
        }])

    def tearDown(self):
        self.path_patch.stop()
        self.temp_dir.cleanup()

    def make_payload(self, items=None):
        return web_portal.BorrowRequestInput(
            reader_code="RD-01",
            name="Nguyen Van A",
            requester_type="Học sinh",
            class_name="10A1",
            items=items or [web_portal.RequestItem(book_code="BK-01", quantity=2)],
        )

    def test_public_catalog_hides_private_fields_and_request_can_be_tracked(self):
        book = web_portal.list_catalog()[0]
        self.assertEqual(book["available"], 3)
        self.assertNotIn("phone", book)

        created = web_portal.submit_request(self.make_payload())
        status = web_portal.get_request_status(created["request_id"], created["tracking_token"])
        self.assertEqual(status["status"], "pending")
        self.assertIsNone(web_portal.get_request_status(created["request_id"], "wrong-token"))
        self.assertEqual(web_portal.list_requests()[0]["items"][0]["quantity"], 2)

    def test_request_cannot_exceed_synced_availability(self):
        with self.assertRaisesRegex(ValueError, "không đủ số lượng"):
            web_portal.submit_request(self.make_payload([
                web_portal.RequestItem(book_code="BK-01", quantity=2),
                web_portal.RequestItem(book_code="BK-01", quantity=2),
            ]))

    def test_rejection_requires_reason_and_is_final(self):
        created = web_portal.submit_request(self.make_payload())
        with self.assertRaisesRegex(ValueError, "lý do"):
            web_portal.decide_request(
                created["request_id"],
                web_portal.DecisionInput(status="rejected"),
            )

        web_portal.decide_request(
            created["request_id"],
            web_portal.DecisionInput(status="rejected", reason="Không còn bản phù hợp."),
        )
        self.assertTrue(web_portal.decide_request(
            created["request_id"],
            web_portal.DecisionInput(status="rejected", reason="Không còn bản phù hợp."),
        ))
        status = web_portal.get_request_status(created["request_id"], created["tracking_token"])
        self.assertEqual(status["status"], "rejected")
        self.assertEqual(status["decision_reason"], "Không còn bản phù hợp.")

    def test_approved_request_requires_internal_loan_id(self):
        created = web_portal.submit_request(self.make_payload())
        with self.assertRaisesRegex(ValueError, "chưa được tạo"):
            web_portal.decide_request(
                created["request_id"],
                web_portal.DecisionInput(status="approved"),
            )

    def test_request_submission_is_rate_limited_by_source(self):
        for _ in range(50):
            web_portal.submit_request(self.make_payload(), "192.0.2.10")
        with self.assertRaisesRegex(web_portal.RateLimitError, "quá nhiều"):
            web_portal.submit_request(self.make_payload(), "192.0.2.10")


if __name__ == "__main__":
    unittest.main()
