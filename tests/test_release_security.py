import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask_migrate import upgrade
from PIL import Image
from werkzeug.datastructures import FileStorage


class ReleaseSecurityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.old_environment = os.environ.copy()
        os.environ.update(
            {
                "APP_ENV": "development",
                "SECRET_KEY": "release-test-secret-release-test-secret",
                "DATABASE_URL": "sqlite:///" + (self.root / "test.db").as_posix(),
                "SCENARIOS_DIR": str(self.root / "scenarios"),
                "MEDIA_DIR": str(self.root / "media"),
                "REGISTRATION_MODE": "open",
                "TURNSTILE_REQUIRED": "false",
                "AUTH_MAX_FAILURES": "3",
            }
        )
        from app import create_app

        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        with self.app.app_context():
            upgrade(directory="migrations")

    def tearDown(self):
        from app.extensions import db

        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        os.environ.clear()
        os.environ.update(self.old_environment)
        self.temp.cleanup()

    def _create_user(self, login="release_user", password="correct horse battery staple"):
        from app.services.auth import register

        with self.app.app_context():
            self.assertTrue(bool(register(login, password)))
            from app.domain.models import User

            return User.query.filter_by(login=login).one().user_id

    def _authenticated_client(self, user_id, login="release_user"):
        client = self.app.test_client()
        with client.session_transaction() as session:
            session["user_id"] = user_id
            session["login"] = login
        return client

    def test_registration_requires_turnstile_when_configured(self):
        self.app.config.update(TURNSTILE_REQUIRED=True, TURNSTILE_SECRET_KEY="")
        response = self.app.test_client().post(
            "/register",
            data={"login": "no_bot", "password": "correct horse battery staple"},
        )
        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            from app.domain.models import User

            self.assertEqual(User.query.count(), 0)

    def test_legacy_password_is_upgraded_after_successful_login(self):
        from app.domain.models import User
        from app.extensions import db
        from app.services.auth import authenticate

        with self.app.app_context():
            db.session.add(User(login="legacy", password="legacy password value"))
            db.session.commit()
            ok, user = authenticate("legacy", "legacy password value")
            self.assertTrue(ok)
            self.assertTrue(user.password.startswith("scrypt:"))
            self.assertNotIn("legacy password value", user.password)

    def test_login_throttle_persists_in_database_and_blocks_route(self):
        client = self.app.test_client()
        for _ in range(self.app.config["AUTH_MAX_FAILURES"]):
            response = client.post(
                "/login", data={"login": "missing", "password": "wrong-password"}
            )
        self.assertEqual(response.status_code, 200)
        blocked = client.post(
            "/login", data={"login": "missing", "password": "wrong-password"}
        )
        self.assertEqual(blocked.status_code, 429)

        from app.services import auth_throttle

        with self.app.app_context():
            is_blocked, failures = auth_throttle.status(
                "login", "127.0.0.1", "missing"
            )
            self.assertTrue(is_blocked)
            self.assertGreaterEqual(failures, self.app.config["AUTH_MAX_FAILURES"])

    def test_csrf_rejects_form_json_and_delete_mutations(self):
        user_id = self._create_user()
        client = self._authenticated_client(user_id)
        self.app.config["WTF_CSRF_ENABLED"] = True
        requests = (
            client.post("/logout"),
            client.post("/profile/login", json={"login": "changed"}),
            client.delete("/profile/avatar"),
            client.post("/scenarios/api/create", json={"title": "Blocked"}),
        )
        self.assertTrue(all(response.status_code == 400 for response in requests))

    def test_credential_changes_require_password_and_rehash(self):
        from app.services import users
        from app.services.auth import authenticate

        user_id = self._create_user()
        with self.app.app_context():
            denied = users.change_login(user_id, "new_login", "wrong password")
            self.assertFalse(denied)
            self.assertEqual(denied.error, "wrong_password")
            changed = users.change_login(
                user_id, "new_login", "correct horse battery staple"
            )
            self.assertTrue(changed)
            changed_password = users.change_password(
                user_id,
                "correct horse battery staple",
                "a newer correct horse battery staple",
                "a newer correct horse battery staple",
            )
            self.assertTrue(changed_password)
            self.assertTrue(
                changed_password.value.password.startswith("scrypt:")
            )
            self.assertEqual(authenticate("new_login", "correct horse battery staple")[0], False)
            self.assertEqual(
                authenticate("new_login", "a newer correct horse battery staple")[0],
                True,
            )

    def test_scenario_operations_enforce_owner(self):
        from app.services import scenarios
        from app.services.sessions import create_session, get_session

        owner_id = self._create_user("owner")
        other_id = self._create_user("other")
        with self.app.app_context():
            created = scenarios.create_scenario(owner_id, title="Private")
            self.assertTrue(created)
            scenario_id = created.value[0].scenario_id
            self.assertEqual(
                scenarios.load_document(scenario_id, other_id).error, "not_found"
            )
            self.assertEqual(
                scenarios.delete_scenario(scenario_id, other_id).error, "not_found"
            )
            self.assertTrue(scenarios.load_document(scenario_id, owner_id))
            session_result = create_session(owner_id, scenario_id)
            self.assertTrue(session_result)
            session_id = session_result.value.session_id
            self.assertTrue(scenarios.delete_scenario(scenario_id, owner_id))
            preserved_session = get_session(session_id)
            self.assertIsNotNone(preserved_session)
            self.assertIsNone(preserved_session.scenario_id)
            self.assertEqual(
                json.loads(preserved_session.scenario_snapshot)["format"],
                "roleplay-scenario",
            )

    def test_fresh_lobby_session_heartbeat_succeeds(self):
        from app.services import scenarios
        from app.services.sessions import create_session, participants

        owner_id = self._create_user("prune_owner")
        with self.app.app_context():
            created = scenarios.create_scenario(owner_id, title="Prune test")
            self.assertTrue(created)
            session = create_session(owner_id, created.value[0].scenario_id)
            self.assertTrue(session)
            heartbeat = participants.heartbeat(
                session.value.session_id,
                owner_id,
            )
            self.assertTrue(heartbeat)

    def test_scenario_payload_limit_rejects_before_json_parsing(self):
        user_id = self._create_user()
        client = self._authenticated_client(user_id)
        self.app.config["MAX_SCENARIO_BYTES"] = 64
        response = client.post(
            "/scenarios/1/api/save",
            data=b'{"document":"' + (b"x" * 100) + b'"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json["error"], "scenario_too_large")

    def test_avatar_oversize_and_dimension_bomb_are_rejected(self):
        from app.services.media import set_user_avatar

        user_id = self._create_user()
        with self.app.app_context():
            self.app.config["MAX_AVATAR_BYTES"] = 10
            oversized = FileStorage(
                stream=io.BytesIO(b"x" * 11), filename="avatar.png"
            )
            self.assertFalse(set_user_avatar(user_id, oversized))

            image_bytes = io.BytesIO()
            Image.new("RGB", (11, 1), "red").save(image_bytes, "PNG")
            image_bytes.seek(0)
            self.app.config.update(
                MAX_AVATAR_BYTES=1024 * 1024,
                MAX_AVATAR_DIMENSION=10,
                MAX_AVATAR_PIXELS=1000,
            )
            dimensions = FileStorage(stream=image_bytes, filename="avatar.png")
            self.assertFalse(set_user_avatar(user_id, dimensions))
            self.assertEqual(list((self.root / "media" / "avatars").glob("*.jpg")), [])

    def test_security_headers_and_hsts(self):
        self.app.config["HSTS_ENABLED"] = True
        response = self.app.test_client().get("/health/live", base_url="https://example.test")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        self.assertIn("max-age=31536000", response.headers["Strict-Transport-Security"])

    def test_liveness_and_readiness(self):
        client = self.app.test_client()
        live = client.get("/health/live")
        ready = client.get("/health/ready")
        self.assertEqual(live.status_code, 200)
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json["checks"], {"database": True, "storage": True})
        self.assertEqual(ready.headers["Cache-Control"], "no-store")

        with patch("web.routes.health.db.session.execute", side_effect=RuntimeError):
            not_ready = client.get("/health/ready")
        self.assertEqual(not_ready.status_code, 503)
        self.assertFalse(not_ready.json["checks"]["database"])

    def test_migration_is_idempotent_and_schema_is_complete(self):
        from sqlalchemy import inspect
        from app.extensions import db

        with self.app.app_context():
            upgrade(directory="migrations")
            tables = set(inspect(db.engine).get_table_names())
        self.assertTrue({"users", "scenarios", "auth_attempts", "alembic_version"} <= tables)

    def test_import_copy_is_atomic_idempotent_and_conflict_safe(self):
        import importlib.util

        script = (
            Path(__file__).resolve().parents[1]
            / "ops"
            / "scripts"
            / "import_sqlite_to_mysql.py"
        )
        spec = importlib.util.spec_from_file_location("import_sqlite_to_mysql", script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _copy_atomic = module._copy_atomic

        source = self.root / "source.rpscene"
        destination = self.root / "target" / "scenario.rpscene"
        source.write_bytes(b"first")
        self.assertTrue(_copy_atomic(source, destination))
        self.assertFalse(_copy_atomic(source, destination))
        source.write_bytes(b"different")
        with self.assertRaises(RuntimeError):
            _copy_atomic(source, destination)
        self.assertEqual(destination.read_bytes(), b"first")

    def test_production_rejects_default_secret(self):
        from app.config import load_config

        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "SECRET_KEY": "dev-change-me",
                "DATABASE_URL": "mysql+pymysql://u:p@db/app",
            },
            clear=True,
        ):
            with self.assertRaises(RuntimeError):
                load_config(str(self.root))

    def test_production_honors_explicit_turnstile_override(self):
        from app.config import load_config

        production = {
            "APP_ENV": "production",
            "SECRET_KEY": "production-test-secret-production-test-secret",
            "DATABASE_URL": "mysql+pymysql://u:p@db/app",
        }
        with patch.dict(os.environ, production, clear=True):
            config = load_config(str(self.root))
            self.assertEqual(config["REGISTRATION_MODE"], "closed")
            self.assertFalse(config["TURNSTILE_REQUIRED"])

        production.update(
            {"REGISTRATION_MODE": "open", "TURNSTILE_REQUIRED": "false"}
        )
        with patch.dict(os.environ, production, clear=True):
            config = load_config(str(self.root))
            self.assertFalse(config["TURNSTILE_REQUIRED"])

    def test_deploy_allowlist_and_ignore_files_exclude_sensitive_data(self):
        project = Path(__file__).resolve().parents[1]
        deploy = (project / "ops" / "scripts" / "deploy.ps1").read_text(encoding="utf-8")
        remote = (project / "ops" / "scripts" / "deploy_remote.sh").read_text(
            encoding="utf-8"
        )
        dockerignore = (project / ".dockerignore").read_text(encoding="utf-8")
        dockerfile = (project / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn('[string]$RemotePython = "python3.14"', deploy)
        self.assertTrue(dockerfile.startswith("FROM python:3.14-slim"))
        self.assertIn('$directories = @("app", "web", "migrations")', deploy)
        self.assertIn('$_ .Name -eq ".env"'.replace("$_ ", "$_"), deploy)
        self.assertIn('("storage", "backups")', deploy)
        self.assertIn("artifact contains a forbidden", remote)
        for entry in (".env", "backups", "storage/db/*", "storage/scenarios/*"):
            self.assertIn(entry, dockerignore)


if __name__ == "__main__":
    unittest.main()
