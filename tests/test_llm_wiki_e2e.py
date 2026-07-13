"""Цех llm_wiki e2e (реальные конфиги): большой материал → TOC + material_*, apply.

Прогон graph.autopilot.json на FakeLLM: спека → ревью → file map страниц → ревью;
вход больше inline_limit — узлы получают оглавление чанков и инструменты
material_search/material_get; затем применение артефакта к КОПИИ seed-wiki.
"""
from __future__ import annotations

from pathlib import Path

from workshop.artifact_store import ArtifactStore
from workshop.config_loader import load_graph_config
from workshop.llm_client import FakeLLM, fake_ok
from workshop.orchestrator import run_pipeline
from workshop.result import Ok
from workshop.run_log import RunLog
from workshop.wiki_applier import apply_file_map

GRAPH_PATH = "configs/llm_wiki/graph.autopilot.json"

MATERIAL = (
    "# Чат: интеграция платежей\n"
    + "Обсуждали подписки: страйп, вебхуки, ретраи. " * 400
)

SPEC = (
    "intent: область payments из чата об оплате\n```xml\n"
    '<wiki_change derived_from="input@v1">\n'
    "  <summary>решения по интеграции платежей из чата</summary>\n"
    '  <pages><page path="payments/index.md" action="add" unverified="false">\n'
    "    <purpose>решения по подпискам и вебхукам</purpose>\n"
    "    <source_chunks>d1:01</source_chunks>\n"
    "    <index_row>| [payments](payments/index.md) | интеграция платежей |</index_row>\n"
    "    <related>index.md</related>\n"
    "  </page></pages>\n"
    '  <index_updates><index path="index.md">строка payments</index></index_updates>\n'
    "  <backlog>пусто</backlog>\n"
    "</wiki_change>\n```"
)
REVIEW_PASS = "Находок нет.\nГейт: PASS"

PAYMENTS_PAGE = (
    "# wiki: payments (v1)\n\n"
    "Решения из чатов: подписки через страйп, вебхуки с ретраями.\n\n"
    "related: [карта областей](../index.md)\n"
)


SEED_INDEX = (
    "# llm wiki: карта областей (v1)\n\n"
    "Вики строится цехом llm_wiki из материала пользователя.\n\n"
    "| Область | Что внутри |\n"
    "|---|---|\n"
)


def _seed_wiki(tmp_path: Path) -> Path:
    # герметичный seed: живая projects/llm_wiki/wiki меняется прогонами цеха
    root = tmp_path / "wiki"
    root.mkdir()
    (root / "index.md").write_text(SEED_INDEX, encoding="utf-8")
    return root


def _pages_response() -> str:
    updated = SEED_INDEX.replace(
        "|---|---|",
        "|---|---|\n| [payments](payments/index.md) | интеграция платежей |",
    )
    return (
        "intent: добавляю область payments\n"
        f"```file:payments/index.md\n{PAYMENTS_PAGE}```\n\n"
        f"```file:index.md\n{updated}```"
    )


def test_llm_wiki_pipeline_big_material_then_apply(tmp_path: Path) -> None:
    graph = load_graph_config(GRAPH_PATH)
    assert isinstance(graph, Ok), f"{graph}"

    llm = FakeLLM([
        fake_ok(SPEC),               # wiki_spec
        fake_ok(REVIEW_PASS),        # wiki_spec review
        fake_ok(_pages_response()),  # wiki_pages
        fake_ok(REVIEW_PASS),        # wiki_pages review
    ])
    store = ArtifactStore(tmp_path / "store")
    result = run_pipeline(
        graph.value,
        MATERIAL,
        store,
        llm,
        RunLog(tmp_path / "log.jsonl"),
        hitl=None,  # autopilot: HITL-гейтов в графе нет
    )
    assert isinstance(result, Ok), f"{result}"

    # большой материал: узлам ушло оглавление, не сырой текст
    assert "Оглавление материала" in llm.prompts[0]
    assert MATERIAL not in llm.prompts[0]
    # спецификатор получил и material_*, и web_search; автор страниц — material_*
    assert llm.tools_seen[0] == ("web_search", "material_search", "material_get")
    assert llm.tools_seen[2] == ("material_search", "material_get")

    wiki_copy = _seed_wiki(tmp_path)
    artifact = store.load_artifact(result.value.accepted_artifacts[-1])
    assert isinstance(artifact, Ok)
    applied = apply_file_map(artifact.value.content, wiki_copy)
    assert isinstance(applied, Ok), f"{applied}"
    assert (wiki_copy / "payments" / "index.md").is_file()
