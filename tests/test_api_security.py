"""S3 (input_path allowlist) and S4 (bearer-token auth) — docs/security-review-2026-06.md."""

import os
import shutil
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

    def test_default_deny_unknown_route_requires_token(self) -> None:
        # An unlisted route must require the token (default-deny), so a future
        # endpoint can't ship unauthenticated by being absent from a prefix list.
        api._API_TOKEN = "secret123"
        self.assertEqual(self.client.get("/zzz-not-a-route").status_code, 401)

    def test_public_static_paths_never_blocked(self) -> None:
        # The SPA shell must load without a token (404 here since web/dist is not
        # built in tests — but never 401).
        api._API_TOKEN = "secret123"
        self.assertNotEqual(self.client.get("/").status_code, 401)


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

    def test_execute_run_in_repo_file_does_not_crash(self) -> None:
        # Regression for the missing-import NameError: an in-repo file on the
        # happy path must prepare a run, not 500. (execute=False = prepare only.)
        os.environ["RWS_OFFLINE"] = "1"
        resp = self.client.post(
            "/runs/execute", json={"input_path": "CLAUDE.md", "execute": False}
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        run_id = resp.json()["run_id"]
        self.addCleanup(shutil.rmtree, REPO_ROOT / "runs" / run_id, ignore_errors=True)
        self.assertTrue(run_id)


class GuardHelperTests(unittest.TestCase):
    """Direct coverage of the path-containment primitive and the public-path
    predicate — the S1 static-route guard's @app.get('/{full_path:path}') is only
    mounted when web/dist exists, so its logic is verified here at the unit level."""

    def test_within_blocks_traversal_escape(self) -> None:
        root = (REPO_ROOT / "web" / "dist").resolve()
        # An LFI attempt resolves outside web/dist -> not contained.
        escaped = (root / ".." / ".." / ".env").resolve()
        self.assertFalse(api._within(root, escaped))
        # A real asset under the root -> contained.
        self.assertTrue(api._within(root, (root / "assets" / "app.js").resolve()))
        # Sibling-prefix collision must not be a false positive.
        self.assertFalse(api._within(root, root.parent / (root.name + "-evil") / "x"))

    def test_assets_prefix_requires_trailing_slash(self) -> None:
        # Hardening: /assets../x must NOT be treated as public.
        self.assertTrue(api._is_public_request("GET", "/assets/app.js"))
        self.assertFalse(api._is_public_request("GET", "/assets../secret"))
        self.assertFalse(api._is_public_request("GET", "/assetsx"))
        self.assertFalse(api._is_public_request("GET", "/runs"))

    def test_provider_from_name_is_module_global(self) -> None:
        # Regression: provider_from_name must resolve in resolve_run's scope
        # (it was used there but only imported inside a different function).
        self.assertTrue(hasattr(api, "provider_from_name"))


if __name__ == "__main__":
    unittest.main()
