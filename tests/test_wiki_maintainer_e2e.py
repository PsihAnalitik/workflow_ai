"""FR-21 e2e: цех wiki_maintainer (реальные конфиги) + применение wiki-apply.

Прогон graph.autopilot.json на FakeLLM: спека → ревью → file map страниц → ревью;
затем детерминированное применение артефакта к КОПИИ реальной wiki и проверка,
что новая технология легла в структуру без сирот и битых ссылок.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from workshop.artifact_store import ArtifactStore
from workshop.config_loader import load_graph_config
from workshop.llm_client import FakeLLM, fake_ok
from workshop.orchestrator import run_pipeline
from workshop.result import Ok
from workshop.run_log import RunLog
from workshop.wiki_applier import apply_file_map

GRAPH_PATH = "configs/wiki_maintainer/graph.autopilot.json"

# вымышленная технология: тест накладывает file map на КОПИЮ реальной wiki,
# и существующее имя (реальный кейс duckdb 2026-07-10) делает её подстраницы
# сиротами — стаб-карточка не знает их ссылок
SPEC = (
    "intent: добавить python/exampletech в каталог\n```xml\n"
    '<wiki_change derived_from="input@1">\n'
    "  <summary>карточка exampletech в области python</summary>\n"
    '  <pages><page path="python/exampletech/index.md" action="add" unverified="false">\n'
    "    <purpose>карточка технологии</purpose>\n"
    "    <index_row>| [exampletech](exampletech/index.md) | `python/exampletech` | SQL по файлам | allowed |</index_row>\n"
    "    <related>python/index.md, python/pandas/index.md</related>\n"
    "  </page></pages>\n"
    '  <index_updates><index path="python/index.md">строка exampletech</index></index_updates>\n'
    "</wiki_change>\n```"
)
REVIEW_PASS = "Находок нет.\nГейт: PASS"

TECH_PAGE = (
    "# wiki: exampletech (v1)\n\n"
    "SQL-аналитика по локальным файлам. `ref: python/exampletech`.\n\n"
    "Когда использовать: агрегаты SQL по parquet/CSV без загрузки в память.\n"
    "Когда НЕ использовать: потоковые пайплайны в памяти — это класс задач\n"
    "[pandas](../pandas/index.md).\n\n"
    "related: [каталог python](../index.md)\n"
)


def _pages_response() -> str:
    original = Path("wiki/python/index.md").read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    last_row = max(i for i, line in enumerate(lines) if line.startswith("| ["))
    tech_row = "| [exampletech](exampletech/index.md) | `python/exampletech` | SQL по файлам | allowed |\n"
    updated = "".join(lines[: last_row + 1]) + tech_row + "".join(lines[last_row + 1:])
    return (
        "intent: добавляю карточку exampletech и строку каталога\n"
        f"```file:python/exampletech/index.md\n{TECH_PAGE}```\n\n"
        f"```file:python/index.md\n{updated}```"
    )


def test_wiki_maintainer_pipeline_then_apply(tmp_path: Path) -> None:
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
        "Добавь в wiki технологию exampletech (область python). Материал: SQL по локальным файлам.",
        store,
        llm,
        RunLog(tmp_path / "log.jsonl"),
        hitl=None,  # autopilot: HITL-гейтов в графе нет
    )
    assert isinstance(result, Ok), f"{result}"

    # ревьюер страниц видел текущие индексы wiki-блоками (самодостаточная сверка)
    assert "=== wiki: wiki/python/index.md ===" in llm.prompts[3]

    # применяем принятый артефакт к КОПИИ реальной wiki — детерминированный шаг
    wiki_copy = tmp_path / "wiki"
    shutil.copytree("wiki", wiki_copy)
    artifact = store.load_artifact(result.value.accepted_artifacts[-1])
    assert isinstance(artifact, Ok)
    applied = apply_file_map(artifact.value.content, wiki_copy)
    assert isinstance(applied, Ok), f"{applied}"
    assert applied.value.written == ("python/exampletech/index.md", "python/index.md")
    assert (wiki_copy / "python" / "exampletech" / "index.md").is_file()
    assert len(applied.value.changelog_rows) == 2


UPDATE_SPEC = (
    "intent: обновить страницу grace\n```xml\n"
    '<wiki_change derived_from="input@1">\n'
    "  <source_request>обнови methodology/grace.md: добавь абзац</source_request>\n"
    "  <summary>обновление grace.md</summary>\n"
    '  <pages><page path="methodology/grace.md" action="update" unverified="false">\n'
    "    <purpose>дополнение</purpose>\n"
    "    <index_row>—</index_row>\n"
    "    <related>methodology/index.md</related>\n"
    "  </page></pages>\n"
    "  <index_updates/>\n"
    "</wiki_change>\n```"
)


def test_update_page_injected_into_wiki_pages_context(tmp_path: Path) -> None:
    """FR-21 + динамические wiki_refs: текущий текст update-страницы попадает
    в INPUTS узла wiki_pages (и его ревьюера) автоматически из спеки."""
    graph = load_graph_config(GRAPH_PATH)
    assert isinstance(graph, Ok)

    grace_current = Path("wiki/methodology/grace.md").read_text(encoding="utf-8")
    updated_page = grace_current.rstrip() + "\n\nНовый абзац по спеке.\n"
    llm = FakeLLM([
        fake_ok(UPDATE_SPEC),        # wiki_spec
        fake_ok("Находок нет.\nГейт: PASS"),
        fake_ok(f"intent: обновляю grace\n```file:methodology/grace.md\n{updated_page}```"),
        fake_ok("Находок нет.\nГейт: PASS"),
    ])
    result = run_pipeline(
        graph.value,
        "обнови methodology/grace.md: добавь абзац",
        ArtifactStore(tmp_path / "store"),
        llm,
        RunLog(tmp_path / "log.jsonl"),
        hitl=None,
    )
    assert isinstance(result, Ok), f"{result}"

    # генератор страниц видел ТЕКУЩИЙ текст обновляемой страницы wiki-блоком
    pages_prompt = llm.prompts[2]
    assert "=== wiki: wiki/methodology/grace.md ===" in pages_prompt
    assert "методология артефактной цепочки" in pages_prompt
    # и ревьюер страниц — тоже (сверка сохранности разделов, P5)
    review_prompt = llm.prompts[3]
    assert "=== wiki: wiki/methodology/grace.md ===" in review_prompt
