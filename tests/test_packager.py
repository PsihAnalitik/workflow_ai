"""M-12 packager: сборка пакета + все ERRORS из TSK-1201 (+ TSK-0205)."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from workshop.artifact_store import ArtifactStore
from workshop.models import ArtifactRef, PackageSpec
from workshop.packager import (
    FREEZE_FAILED,
    PACKAGE_NO_CODE_ARTIFACT,
    PACKAGE_NO_RUN_LOG,
    PACKAGE_TARGET_EXISTS,
    build_package,
)
from workshop.result import Err, Ok, Result
from workshop.sandbox import ExecReport

requires_git = pytest.mark.skipif(shutil.which("git") is None, reason="git недоступен")

CODE_CONTENT = (
    "```file:api.py\napp = 'сервис'\n```\n"
    "```file:test_api.py\ndef test_ok(): assert True\n```\n"
)
VERDICT_CONTENT = "<verdict><decision>READY</decision><reasons></reasons></verdict>"

SPEC = PackageSpec(
    image="workshop-test:latest",
    serve="uvicorn api:app --host 0.0.0.0",
    ports=["8000:8000"],
)


class FreezeSandbox:
    def __init__(self, exit_code: int = 0) -> None:
        self._exit_code = exit_code

    def __call__(self, image, files, command, limits) -> Result[ExecReport]:
        assert command == "pip freeze"
        return Ok(ExecReport(
            exit_code=self._exit_code, stdout="fastapi==0.115.0\npytest==9.1.1\n",
            stderr="сломано" if self._exit_code else "", duration_s=0.1,
        ))


def _seed(tmp_path: Path) -> tuple[ArtifactStore, Path]:
    store = ArtifactStore(tmp_path / "store")
    input_ref = store.save_artifact("input", "<request/>")
    code_ref = store.save_artifact("executor", CODE_CONTENT, derived_from=input_ref.value)
    store.save_artifact("executor_verdict", VERDICT_CONTENT, derived_from=code_ref.value)
    log_path = tmp_path / "log.jsonl"
    log_path.write_text(
        json.dumps({"node_id": "executor:codegen", "iteration": 2,
                    "params": {"model": "deepseek-v4-pro"}}) + "\n",
        encoding="utf-8",
    )
    return store, log_path


@requires_git
def test_build_package_happy(tmp_path: Path) -> None:
    store, log_path = _seed(tmp_path)
    out = tmp_path / "package"

    result = build_package(store, SPEC, "demo", log_path, out, sandbox=FreezeSandbox())
    assert isinstance(result, Ok)
    assert {"api.py", "test_api.py", "README.md", "CHANGELOG.md", "report.md",
            "requirements.txt", "Dockerfile", "docker-compose.yml"} <= set(result.value.files)

    assert "fastapi==0.115.0" in (out / "requirements.txt").read_text(encoding="utf-8")
    assert "executor v1 ← input v1" in (out / "CHANGELOG.md").read_text(encoding="utf-8")
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "executor:codegen | 1 | 2 | deepseek-v4-pro" in report
    assert "READY" in report
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "docker compose up" in readme
    assert '"8000:8000"' in (out / "docker-compose.yml").read_text(encoding="utf-8")
    # git-репозиторий с коммитом
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=out, capture_output=True, text=True
    )
    assert head.returncode == 0
    assert result.value.git_commit == head.stdout.strip()


@requires_git
def test_build_package_without_serve_skips_docker_files(tmp_path: Path) -> None:
    store, log_path = _seed(tmp_path)
    spec = PackageSpec(image="workshop-test:latest")   # без serve
    result = build_package(store, spec, "demo", log_path, tmp_path / "pkg", sandbox=FreezeSandbox())
    assert isinstance(result, Ok)
    assert "Dockerfile" not in result.value.files
    assert "docker-compose.yml" not in result.value.files


def test_target_exists(tmp_path: Path) -> None:
    store, log_path = _seed(tmp_path)
    out = tmp_path / "package"
    out.mkdir()
    (out / "занято.txt").write_text("x", encoding="utf-8")
    result = build_package(store, SPEC, "demo", log_path, out, sandbox=FreezeSandbox())
    assert isinstance(result, Err)
    assert result.code == PACKAGE_TARGET_EXISTS


def test_no_code_artifact(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "store")
    log_path = tmp_path / "log.jsonl"
    log_path.write_text("", encoding="utf-8")
    result = build_package(store, SPEC, "demo", log_path, tmp_path / "pkg", sandbox=FreezeSandbox())
    assert isinstance(result, Err)
    assert result.code == PACKAGE_NO_CODE_ARTIFACT


def test_no_run_log(tmp_path: Path) -> None:
    store, _log = _seed(tmp_path)
    result = build_package(
        store, SPEC, "demo", tmp_path / "нет.jsonl", tmp_path / "pkg", sandbox=FreezeSandbox()
    )
    assert isinstance(result, Err)
    assert result.code == PACKAGE_NO_RUN_LOG


def test_freeze_failed(tmp_path: Path) -> None:
    store, log_path = _seed(tmp_path)
    result = build_package(
        store, SPEC, "demo", log_path, tmp_path / "pkg", sandbox=FreezeSandbox(exit_code=1)
    )
    assert isinstance(result, Err)
    assert result.code == FREEZE_FAILED


def test_list_artifacts_sorted(tmp_path: Path) -> None:
    store, _log = _seed(tmp_path)
    refs = store.list_artifacts()
    assert refs == [
        ArtifactRef("executor", 1),
        ArtifactRef("executor_verdict", 1),
        ArtifactRef("input", 1),
    ]
    assert ArtifactStore(tmp_path / "пусто").list_artifacts() == []
