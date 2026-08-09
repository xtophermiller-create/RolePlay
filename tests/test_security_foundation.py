import os
import tempfile
import unittest
from pathlib import Path

from flask_migrate import upgrade


class SecurityFoundationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        os.environ.update(
            {
                "APP_ENV": "development",
                "SECRET_KEY": "focused-test-secret-focused-test-secret",
                "DATABASE_URL": "sqlite:///" + (root / "test.db").as_posix(),
                "SCENARIOS_DIR": str(root / "scenarios"),
                "MEDIA_DIR": str(root / "media"),
                "REGISTRATION_MODE": "open",
                "TURNSTILE_REQUIRED": "false",
            }
        )
        from app import create_app

        self.app = create_app()
        self.app.config["WTF_CSRF_ENABLED"] = False
        with self.app.app_context():
            upgrade(directory="migrations")

    def tearDown(self):
        from app.extensions import db

        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp.cleanup()

    def test_registration_hash_login_and_headers(self):
        from app.domain.models import User

        client = self.app.test_client()
        response = client.post(
            "/register",
            data={
                "login": "focused_user",
                "password": "correct horse battery staple",
            },
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            self.assertTrue(User.query.one().password.startswith("scrypt:"))

        response = client.post(
            "/login",
            data={
                "login": "focused_user",
                "password": "correct horse battery staple",
            },
        )
        self.assertEqual(response.status_code, 302)
        response = client.get("/home/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_document_validation_rejects_untrusted_nodes(self):
        from app.domain.scenario.document import empty_document, validate_document

        document = empty_document(title="Focused")
        self.assertEqual(validate_document(document), [])
        document["roles"]["actor1"]["body"] = {
            "type": "doc",
            "content": [{"type": "script", "text": "bad"}],
        }
        self.assertTrue(validate_document(document))

    def test_csrf_and_persistent_throttle(self):
        from app.services import auth_throttle

        self.app.config["WTF_CSRF_ENABLED"] = True
        response = self.app.test_client().post(
            "/register", data={"login": "blocked", "password": "long-enough-password"}
        )
        self.assertEqual(response.status_code, 400)
        self.app.config["WTF_CSRF_ENABLED"] = False
        with self.app.app_context():
            for _ in range(self.app.config["AUTH_MAX_FAILURES"]):
                auth_throttle.record_failure("login", "127.0.0.1", "someone")
            blocked, failures = auth_throttle.status("login", "127.0.0.1", "someone")
            self.assertTrue(blocked)
            self.assertGreaterEqual(failures, self.app.config["AUTH_MAX_FAILURES"])


if __name__ == "__main__":
    unittest.main()
