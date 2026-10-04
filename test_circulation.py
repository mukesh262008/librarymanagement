import tempfile
import unittest
from pathlib import Path

import database


class CirculationTests(unittest.TestCase):
    TEST_PASSWORD = "TestLibraryPassword2026!"

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        database.DATABASE_PATH = Path(cls.temp_dir.name) / "test-library.db"
        import app as application
        cls.app = application.app
        cls.app.config.update(TESTING=True)
        with cls.app.app_context():
            database.init_db()
        cls.client = cls.app.test_client()
        cls.client.get("/setup")
        with cls.client.session_transaction() as current_session:
            token = current_session["csrf_token"]
        response = cls.client.post("/setup", data={
            "csrf_token": token,
            "username": "librarian",
            "password": cls.TEST_PASSWORD,
        })
        if response.status_code != 302:
            raise RuntimeError(f"Test staff account setup failed: {response.status_code}")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def post_json(self, path, payload):
        with self.client.session_transaction() as current_session:
            token = current_session["csrf_token"]
        return self.client.post(path, json=payload, headers={"X-CSRF-Token": token})

    def test_overview_and_operational_pages_render(self):
        for route in ("/", "/members", "/members/1", "/catalogue", "/circulation", "/policies"):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                if route == "/circulation":
                    self.assertIn(b"Add a member", response.data)
                    self.assertIn(b"Student", response.data)
                    self.assertIn(b"Staff", response.data)

    def test_member_and_catalogue_endpoints_return_seeded_records(self):
        members = self.client.get("/api/members").get_json()
        books = self.client.get("/api/books").get_json()
        self.assertGreaterEqual(len(members), 50)
        self.assertEqual(len(books), 108)
        self.assertEqual(sum(book["category"] == "Artificial Intelligence" for book in books), 8)
        self.assertEqual(self.client.get("/api/dashboard").get_json()["metrics"]["total_members"], len(members))

    def test_overdue_member_is_denied_issue_and_renewal(self):
        issue = self.post_json("/api/circulation/check", {
            "action": "issue", "member_id": 1, "book_id": 2,
        }).get_json()
        renewal = self.post_json("/api/circulation/renew", {"loan_id": 1})
        self.assertFalse(issue["approved"])
        self.assertEqual(issue["reason"], "Member has an overdue item.")
        self.assertEqual(renewal.status_code, 409)
        self.assertFalse(renewal.get_json()["approved"])

    def test_eligible_issue_creates_loan_using_active_policy_period(self):
        response = self.post_json("/api/circulation/issue", {
            "member_id": 2, "book_id": 4,
        })
        self.assertEqual(response.status_code, 201)
        result = response.get_json()
        self.assertTrue(result["approved"])
        self.assertTrue(result["loan_id"])
        active = self.client.get("/api/circulation/active-loans").get_json()
        self.assertIn(result["loan_id"], [loan["id"] for loan in active])

    def test_suspended_member_is_denied(self):
        response = self.post_json("/api/circulation/check", {
            "action": "issue", "member_id": 5, "book_id": 4,
        })
        self.assertFalse(response.get_json()["approved"])
        self.assertEqual(response.get_json()["reason"], "Member account is not active.")

    def test_eligible_loan_can_be_renewed(self):
        response = self.post_json("/api/circulation/renew", {"loan_id": 2})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["approved"])
        self.assertIn("due_on", response.get_json())

    def test_overdue_return_assesses_policy_fine(self):
        response = self.post_json("/api/circulation/return", {"loan_id": 1})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["returned"])
        self.assertGreater(response.get_json()["fine_assessed"], 0)

    def test_add_student_or_staff_from_circulation(self):
        student = self.post_json("/api/members", {
            "name": "New Student", "email": "new.student@example.org", "member_type": "Student",
        })
        staff = self.post_json("/api/members", {
            "name": "New Staff", "email": "new.staff@example.org", "member_type": "Staff",
        })
        self.assertEqual(student.status_code, 201)
        self.assertEqual(student.get_json()["member_type"], "Student")
        self.assertEqual(staff.status_code, 201)
        self.assertEqual(staff.get_json()["member_type"], "Staff")

    def test_staff_login_is_required_and_password_is_checked(self):
        with self.client.session_transaction() as current_session:
            csrf = current_session["csrf_token"]
        self.client.post("/logout", data={"csrf_token": csrf})
        self.assertEqual(self.client.get("/api/members").status_code, 401)
        self.client.get("/login")
        with self.client.session_transaction() as current_session:
            csrf = current_session["csrf_token"]
        wrong = self.client.post("/login", data={
            "csrf_token": csrf, "username": "librarian", "password": "incorrect-password",
        })
        self.assertEqual(wrong.status_code, 401)
        self.client.get("/login")
        with self.client.session_transaction() as current_session:
            csrf = current_session["csrf_token"]
        valid = self.client.post("/login", data={
            "csrf_token": csrf, "username": "librarian", "password": self.TEST_PASSWORD,
        })
        self.assertEqual(valid.status_code, 302)


if __name__ == "__main__":
    unittest.main()
