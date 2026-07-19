import hashlib
import json
from pathlib import Path

import pytest

from ruwritingstyles.workspace import (
    WORKSPACE_MARKER,
    find_workspace,
    init_workspace,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_init_empty_workspace_and_resolve_marker(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "workspace"
    result = init_workspace(target)
    assert result["installed"]
    marker = json.loads((target / WORKSPACE_MARKER).read_text(encoding="utf-8"))
    assert marker["managed_files"]
    assert (target / "ClaudeStyles").is_dir()
    assert (target / "styles" / "manifest.yml").is_file()
    monkeypatch.delenv("RWS_WORKSPACE", raising=False)
    assert find_workspace(target / "styles") == target


def test_init_refuses_managed_path_collisions(tmp_path: Path) -> None:
    target = tmp_path / "collision"
    (target / "styles").mkdir(parents=True)
    (target / "styles" / "manifest.yml").write_text("local", encoding="utf-8")
    with pytest.raises(FileExistsError, match="managed workspace paths"):
        init_workspace(target)


def test_upgrade_preserves_local_edits_and_stages_vendor_copy(tmp_path: Path) -> None:
    target = tmp_path / "upgrade"
    init_workspace(target)
    edited = target / "model_policy.yml"
    edited.write_text("local edit\n", encoding="utf-8")
    result = init_workspace(target, upgrade=True)
    assert "model_policy.yml" in result["conflicts"]
    assert edited.read_text(encoding="utf-8") == "local edit\n"
    vendor_copy = target / ".rws-new" / "model_policy.yml"
    assert vendor_copy.is_file()
    marker = json.loads((target / WORKSPACE_MARKER).read_text(encoding="utf-8"))
    assert marker["managed_files"]["model_policy.yml"] == _sha(vendor_copy)


def test_upgrade_never_touches_user_data(tmp_path: Path) -> None:
    target = tmp_path / "userdata"
    init_workspace(target)
    run_artifact = target / "runs" / "mine" / "run.json"
    run_artifact.parent.mkdir(parents=True)
    run_artifact.write_text('{"mine": true}\n', encoding="utf-8")
    database = target / "rws.db"
    database.write_bytes(b"user database")
    env_file = target / ".env"
    env_file.write_text("SECRET=value\n", encoding="utf-8")
    init_workspace(target, upgrade=True)
    assert run_artifact.read_text(encoding="utf-8") == '{"mine": true}\n'
    assert database.read_bytes() == b"user database"
    assert env_file.read_text(encoding="utf-8") == "SECRET=value\n"


def test_explicit_workspace_requires_marker(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RWS_WORKSPACE", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="rws init"):
        find_workspace()
