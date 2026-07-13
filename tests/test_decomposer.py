"""M-15 decomposer: разрез по доменам + все ERRORS из TSK-1501/1502."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from workshop.__main__ import main
from workshop.artifact_store import ArtifactStore
from workshop.decomposer import (
    DECOMPOSE_NO_DOMAINS,
    DECOMPOSE_TARGET_EXISTS,
    decompose,
    parse_domains,
)
from workshop.result import Err, Ok

REQUIREMENTS = """<requirements module="url_shortener" version="1">
  <functional>
    <fr id="FR-01" priority="must">Создать короткую ссылку</fr>
    <fr id="FR-02" priority="must">Редирект по коду</fr>
    <fr id="FR-03" priority="should">Статистика переходов</fr>
    <fr id="FR-99" priority="could">Забытое требование</fr>
  </functional>
  <nonfunctional>
    <nfr id="NFR-01" type="portability">Офлайн</nfr>
  </nonfunctional>
</requirements>"""

DOMAINS = """<domains project="url_shortener" version="1" derived_from="requirements.xml@1">
  <domain id="D-01" name="shortening">
    <responsibility>Коды и разрешение в URL</responsibility>
    <covers>FR-01, FR-02</covers>
  </domain>
  <domain id="D-02" name="stats">
    <responsibility>Подсчёт переходов</responsibility>
    <covers>FR-03</covers>
  </domain>
  <relationships>
    <edge from="D-02" to="D-01" kind="async" via="C-transitions" data="событие перехода"/>
  </relationships>
</domains>"""


def _seed(tmp_path: Path) -> ArtifactStore:
    store = ArtifactStore(tmp_path / "store")
    input_ref = store.save_artifact("input", REQUIREMENTS)
    store.save_artifact("domains", DOMAINS, derived_from=input_ref.value)
    return store


# --- TSK-1501 ---

def test_parse_domains_and_edges() -> None:
    result = parse_domains(DOMAINS)
    assert isinstance(result, Ok)
    domains, edges = result.value
    assert [d.domain_id for d in domains] == ["D-01", "D-02"]
    assert domains[0].covers == ("FR-01", "FR-02")
    assert len(edges) == 1
    assert (edges[0].from_domain, edges[0].to_domain, edges[0].via) == (
        "D-02", "D-01", "C-transitions",
    )


def test_parse_no_domains() -> None:
    result = parse_domains("<domains><relationships/></domains>")
    assert isinstance(result, Err)
    assert result.code == DECOMPOSE_NO_DOMAINS


# --- TSK-1502 ---

def test_decompose_multidomain(tmp_path: Path) -> None:
    store = _seed(tmp_path)
    out = tmp_path / "submodules"
    result = decompose(store, "url_shortener", out)
    assert isinstance(result, Ok)
    assert result.value.submodules == ("shortening", "stats")
    assert result.value.uncovered_frs == ("FR-99",)   # непокрытый FR не потерян молча

    shortening = (out / "shortening" / "input.xml").read_text(encoding="utf-8")
    assert '<fr id="FR-01"' in shortening
    assert '<fr id="FR-02"' in shortening
    assert '<fr id="FR-03"' not in shortening          # чужой FR не попал
    assert '<nfr id="NFR-01"' in shortening            # NFR — всем подмодулям
    assert '<provides via="C-transitions" kind="async" to="stats"/>' in shortening

    stats = (out / "stats" / "input.xml").read_text(encoding="utf-8")
    assert '<fr id="FR-03"' in stats
    assert '<consumes via="C-transitions" kind="async" from="shortening"/>' in stats

    product = json.loads((out / "product.json").read_text(encoding="utf-8"))
    assert product["product"] == "url_shortener"
    stats_service = next(s for s in product["services"] if s["name"] == "stats")
    assert stats_service["env"] == {"SHORTENING_URL": "http://shortening:8000"}
    assert stats_service["depends_on"] == ["shortening"]
    assert stats_service["package"] == "projects/url_shortener-stats/package"


def test_decompose_target_exists(tmp_path: Path) -> None:
    store = _seed(tmp_path)
    out = tmp_path / "submodules"
    out.mkdir()
    (out / "занято").write_text("x", encoding="utf-8")
    result = decompose(store, "p", out)
    assert isinstance(result, Err)
    assert result.code == DECOMPOSE_TARGET_EXISTS


def test_decompose_missing_domains_artifact(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "store")
    store.save_artifact("input", REQUIREMENTS)
    result = decompose(store, "p", tmp_path / "submodules")
    assert isinstance(result, Err)
    assert result.code == "ARTIFACT_NOT_FOUND"


def test_single_domain_is_trivial_cut(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "store")
    store.save_artifact("input", REQUIREMENTS.replace(
        '<fr id="FR-99" priority="could">Забытое требование</fr>', ""
    ))
    single = DOMAINS.replace(
        '<covers>FR-01, FR-02</covers>', '<covers>FR-01, FR-02, FR-03</covers>'
    )
    single = single[:single.index('<domain id="D-02"')] + "<relationships/></domains>"
    store.save_artifact("domains", single)
    result = decompose(store, "p", tmp_path / "submodules")
    assert isinstance(result, Ok)
    assert result.value.submodules == ("shortening",)
    product = json.loads(Path(result.value.product_spec_path).read_text(encoding="utf-8"))
    assert len(product["services"]) == 1


# --- CLI ---

def test_cli_decompose(tmp_path: Path, capsys: pytest.CaptureFixture,
                       monkeypatch: pytest.MonkeyPatch, make_config_file) -> None:
    monkeypatch.chdir(tmp_path)
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps({
        "project": "url_shortener",
        "nodes": [{"id": "domains", "config_path": make_config_file("d")}],
    }), encoding="utf-8")
    store = ArtifactStore(tmp_path / "projects/url_shortener/artifacts")
    store.save_artifact("input", REQUIREMENTS)
    store.save_artifact("domains", DOMAINS)

    exit_code = main(["decompose", str(graph_path)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "подмодуль: shortening" in captured.out
    assert "черновик продукта:" in captured.out
    assert "FR-99 не покрыт" in captured.err
    assert (tmp_path / "projects/url_shortener/submodules/stats/input.xml").is_file()
