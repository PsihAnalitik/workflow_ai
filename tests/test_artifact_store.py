"""M-02 artifact_store: happy paths + все ERRORS из TSK-0201..0203."""
from __future__ import annotations

from pathlib import Path

import pytest

from workshop.artifact_store import (
    ARTIFACT_NOT_FOUND,
    STORE_IO_ERROR,
    UPSTREAM_UNPARSEABLE,
    VERSION_EXISTS,
    ArtifactStore,
    validate_crosslinks,
)
from workshop.models import Artifact, ArtifactRef
from workshop.result import Err, Ok

REPO_ROOT = Path(__file__).parent.parent

UPSTREAM_XML = (
    '<requirements><fr id="FR-01">a</fr><fr id="FR-02">b</fr>'
    '<nfr id="NFR-01">c</nfr></requirements>'
)
DOMAINS_XML = (
    '<domains><domain id="D-01"><covers>FR-01, FR-99</covers>'
    '<relationships via="C-search"/></domain></domains>'
)


def _artifact(content: str, name: str = "doc") -> Artifact:
    return Artifact(ref=ArtifactRef(name, 1), content=content, derived_from=None)


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    upstream_ref = ArtifactRef("requirements", 1)

    saved = store.save_artifact("domains", DOMAINS_XML, derived_from=upstream_ref)
    assert isinstance(saved, Ok)
    assert saved.value == ArtifactRef("domains", 1)

    loaded = store.load_artifact(saved.value)
    assert isinstance(loaded, Ok)
    assert loaded.value.content == DOMAINS_XML
    assert loaded.value.derived_from == upstream_ref


def test_versions_are_append_only(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    first = store.save_artifact("req", "<v1/>")
    second = store.save_artifact("req", "<v2/>")
    assert isinstance(first, Ok) and first.value.version == 1
    assert isinstance(second, Ok) and second.value.version == 2

    loaded_first = store.load_artifact(ArtifactRef("req", 1))
    assert isinstance(loaded_first, Ok)
    assert loaded_first.value.content == "<v1/>"


def test_version_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = ArtifactStore(tmp_path)
    assert isinstance(store.save_artifact("req", "<v1/>"), Ok)
    # имитация гонки: вторая запись целится в уже занятую версию
    monkeypatch.setattr(store, "_next_version", lambda artifact_dir: 1)
    result = store.save_artifact("req", "<clash/>")
    assert isinstance(result, Err)
    assert result.code == VERSION_EXISTS


def test_store_io_error(tmp_path: Path) -> None:
    root = tmp_path / "store"
    root.mkdir()
    root.chmod(0o500)
    try:
        result = ArtifactStore(root).save_artifact("req", "<v1/>")
    finally:
        root.chmod(0o700)
    assert isinstance(result, Err)
    assert result.code == STORE_IO_ERROR


def test_latest_version(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path)
    store.save_artifact("req", "<v1/>")
    store.save_artifact("req", "<v2/>")
    result = store.latest_version("req")
    assert isinstance(result, Ok)
    assert result.value == ArtifactRef("req", 2)


def test_latest_version_not_found(tmp_path: Path) -> None:
    result = ArtifactStore(tmp_path).latest_version("ghost")
    assert isinstance(result, Err)
    assert result.code == ARTIFACT_NOT_FOUND


def test_artifact_not_found(tmp_path: Path) -> None:
    result = ArtifactStore(tmp_path).load_artifact(ArtifactRef("ghost", 1))
    assert isinstance(result, Err)
    assert result.code == ARTIFACT_NOT_FOUND


def test_crosslinks_broken_and_uncovered() -> None:
    result = validate_crosslinks(_artifact(DOMAINS_XML), _artifact(UPSTREAM_XML))
    assert isinstance(result, Ok)
    # FR-99 бит; C-search — ссылка «вперёд», не дефект; D-01 определён самим артефактом
    assert result.value.broken_links == ("FR-99",)
    assert result.value.uncovered_ids == ("FR-02", "NFR-01")


def test_crosslinks_upstream_unparseable() -> None:
    result = validate_crosslinks(_artifact(DOMAINS_XML), _artifact("<пусто/>"))
    assert isinstance(result, Err)
    assert result.code == UPSTREAM_UNPARSEABLE


def test_crosslinks_golden_text_searcher() -> None:
    requirements = (REPO_ROOT / "text_searcher/requirements.xml").read_text(
        encoding="utf-8"
    )
    domains = (REPO_ROOT / "text_searcher/domains.xml").read_text(encoding="utf-8")
    result = validate_crosslinks(_artifact(domains), _artifact(requirements))
    assert isinstance(result, Ok)
    assert result.value.broken_links == ()   # эталонная пара согласована по FR-id
