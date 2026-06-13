"""S3 (input_path allowlist) and S4 (bearer-token auth) — docs/security-review-2026-06.md."""

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import ruwritingstyles.api as api

REPO_ROOT = Path(api.__file__).resolve().parents[2]


class AuthMiddlewareTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = api._API_TOKEN
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        api._API_TOKEN = self._saved

    def test_auth_disabled_by_default(self) -> None:
        # No token configured -> the loopback dev tool stays open.
        api._API_TOKEN = ""
        resp = self.client.get("/status")
        self.assertNotEqual(resp.status_code, 401)

    def test_protected_route_401_without_token(self) -> None:
        api._API_TOKEN = "secret123"
        resp = self.client.get("/status")
        self.assertEqual(resp.status_code, 401)

    def test_protected_route_ok_with_valid_token(self) -> None:
        api._API_TOKEN = "secret123"
        resp = self.client.get("/status", headers={"Authorization": "Bearer secret123"})
        self.assertEqual(resp.status_code, 200)

    def test_wrong_token_rejected(self) -> None:
        api._API_TOKEN = "secret123"
        resp = self.client.get("/status", headers={"Authorization": "Bearer nope"})
        self.assertEqual(resp.status_code, 401)


class InputPathAllowlistTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = api._API_TOKEN
        api._API_TOKEN = ""  # isolate S3 from S4
        self.client = TestClient(api.app)

    def tearDown(self) -> None:
        api._API_TOKEN = self._saved

    def test_input_path_outside_root_is_forbidden(self) -> None:
        outside = os.path.join(tempfile.gettempdir(), "rws-not-allowed.md")
        resp = self.client.post("/runs/execute", json={"input_path": outside, "execute": False})
        self.assertEqual(resp.status_code, 403)

    def test_input_root_defaults_to_repo_and_widens_via_env(self) -> None:
        self.assertEqual(api._input_root(REPO_ROOT), REPO_ROOT.resolve())
        tmp = Path(tempfile.gettempdir())
        os.environ["RWS_INPUT_ROOT"] = str(tmp)
        try:
            self.assertEqual(api._input_root(REPO_ROOT), tmp.resolve())
        finally:
            del os.environ["RWS_INPUT_ROOT"]


if __name__ == "__main__":
    unittest.main()
