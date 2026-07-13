"""M-14 assembler + TSK-0104 load_product_spec: сборка продукта и все ERRORS."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from workshop.__main__ import main
from workshop.assembler import (
    PRODUCT_TARGET_EXISTS,
    SERVICE_NO_DOCKERFILE,
    SERVICE_PACKAGE_NOT_FOUND,
    assemble_product,
)
from workshop.config_loader import CONFIG_INVALID, load_product_spec
from workshop.models import ProductSpec
from workshop.result import Err, Ok

requires_git = pytest.mark.skipif(shutil.which("git") is None, reason="git недоступен")


def _make_package(tmp_path: Path, name: str, with_dockerfile: bool = True) -> str:
    package_dir = tmp_path / f"pkg_{name}"
    package_dir.mkdir()
    (package_dir / "api.py").write_text(f"app = '{name}'", encoding="utf-8")
    if with_dockerfile:
        (package_dir / "Dockerfile").write_text("FROM python:3.14-slim\n", encoding="utf-8")
    # у пакета есть свой git-мусор — в продукт он попасть не должен
    (package_dir / ".git").mkdir()
    (package_dir / ".git" / "HEAD").write_text("ref: refs/heads/main", encoding="utf-8")
    return str(package_dir)


def _spec(tmp_path: Path, **service_overrides) -> ProductSpec:
    search = {"name": "search", "package": _make_package(tmp_path, "search"),
              "ports": ["8000:8000"]}
    reports = {"name": "reports", "package": _make_package(tmp_path, "reports"),
               "env": {"SEARCH_URL": "http://search:8000"}, "depends_on": ["search"]}
    reports.update(service_overrides)
    return ProductSpec.model_validate({"product": "platform", "services": [search, reports]})


@requires_git
def test_assemble_happy(tmp_path: Path) -> None:
    out = tmp_path / "product"
    result = assemble_product(_spec(tmp_path), out)
    assert isinstance(result, Ok)
    assert result.value.services == ("search", "reports")

    compose = (out / "docker-compose.yml").read_text(encoding="utf-8")
    assert "build: ./services/search" in compose
    assert '- "8000:8000"' in compose
    assert 'SEARCH_URL: "http://search:8000"' in compose
    assert "depends_on:" in compose and "- search" in compose

    assert (out / "services/search/api.py").is_file()
    assert not (out / "services/search/.git").exists()   # .git пакета не скопирован
    assert "| search |" in (out / "README.md").read_text(encoding="utf-8")

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=out, capture_output=True, text=True)
    assert head.returncode == 0
    assert result.value.git_commit == head.stdout.strip()


def test_assemble_target_exists(tmp_path: Path) -> None:
    out = tmp_path / "product"
    out.mkdir()
    (out / "занято").write_text("x", encoding="utf-8")
    result = assemble_product(_spec(tmp_path), out)
    assert isinstance(result, Err)
    assert result.code == PRODUCT_TARGET_EXISTS


def test_assemble_package_not_found_no_partial_result(tmp_path: Path) -> None:
    spec = _spec(tmp_path, package=str(tmp_path / "нет_такого"))
    out = tmp_path / "product"
    result = assemble_product(spec, out)
    assert isinstance(result, Err)
    assert result.code == SERVICE_PACKAGE_NOT_FOUND
    assert "reports" in result.details
    assert not out.exists()   # валидация до копирования — частичного результата нет


def test_assemble_no_dockerfile(tmp_path: Path) -> None:
    spec = _spec(tmp_path, package=_make_package(tmp_path, "cli", with_dockerfile=False))
    result = assemble_product(spec, tmp_path / "product")
    assert isinstance(result, Err)
    assert result.code == SERVICE_NO_DOCKERFILE


# --- TSK-0104 load_product_spec ---

def _write_spec(tmp_path: Path, payload: dict) -> str:
    path = tmp_path / "product.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_load_product_spec_ok(tmp_path: Path) -> None:
    result = load_product_spec(_write_spec(tmp_path, {
        "product": "platform",
        "services": [{"name": "search", "package": "pkg"}],
    }))
    assert isinstance(result, Ok)
    assert result.value.services[0].name == "search"


def test_load_product_spec_bad_service_name(tmp_path: Path) -> None:
    result = load_product_spec(_write_spec(tmp_path, {
        "product": "platform",
        "services": [{"name": "Bad_Name", "package": "pkg"}],
    }))
    assert isinstance(result, Err)
    assert result.code == CONFIG_INVALID


def test_load_product_spec_duplicate_names(tmp_path: Path) -> None:
    result = load_product_spec(_write_spec(tmp_path, {
        "product": "platform",
        "services": [{"name": "s", "package": "a"}, {"name": "s", "package": "b"}],
    }))
    assert isinstance(result, Err)
    assert result.code == CONFIG_INVALID


def test_load_product_spec_ghost_dependency(tmp_path: Path) -> None:
    result = load_product_spec(_write_spec(tmp_path, {
        "product": "platform",
        "services": [{"name": "s", "package": "a", "depends_on": ["ghost"]}],
    }))
    assert isinstance(result, Err)
    assert result.code == CONFIG_INVALID
    assert "ghost" in result.details


# --- CLI ---

@requires_git
def test_cli_assemble(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    spec_path = _write_spec(tmp_path, {
        "product": "platform",
        "services": [
            {"name": "search", "package": _make_package(tmp_path, "search"),
             "ports": ["8000:8000"]},
        ],
    })
    exit_code = main(["assemble", spec_path, "--out", str(tmp_path / "product")])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "сервис: search" in captured.out
    assert "git-коммит:" in captured.out


def test_cli_assemble_bad_spec(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    exit_code = main(["assemble", str(tmp_path / "нет.json")])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "CONFIG_NOT_FOUND" in captured.err
