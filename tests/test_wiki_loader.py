"""M-16 wiki_loader: страницы, бандлы, кросс-ссылки, парсинг tech_stack (TSK-1601..1604)."""
from __future__ import annotations

from pathlib import Path

import pytest

from workshop.result import Err, Ok
from workshop.wiki_loader import (
    WIKI_REFS_SOURCE_UNPARSEABLE,
    WIKI_BUNDLE_TOO_LARGE,
    WIKI_PAGE_INVALID,
    WIKI_PAGE_NOT_FOUND,
    build_bundle,
    check_links,
    load_page,
    parse_wiki_refs_source,
    tree_listing,
)


@pytest.fixture
def wiki_root(tmp_path: Path) -> Path:
    root = tmp_path / "wiki"
    (root / "python" / "pandas").mkdir(parents=True)
    (root / "python" / "pandas" / "index.md").write_text(
        "# pandas\n\nСм. [шаблоны](templates.md) и [агентов](../../agents).\n",
        encoding="utf-8",
    )
    (root / "python" / "pandas" / "templates.md").write_text("# шаблоны\n", encoding="utf-8")
    (root / "python" / "index.md").write_text(
        "# каталог python\n\n- [pandas](pandas/index.md)\n", encoding="utf-8"
    )
    (root / "agents").mkdir()
    (root / "agents" / "index.md").write_text("# agents\n", encoding="utf-8")
    (root / "index.md").write_text(
        "# карта областей\n\n- [python](python/index.md)\n- [agents](agents)\n",
        encoding="utf-8",
    )
    return root


# --- TSK-1601 load_page ---

def test_load_page_file_and_directory(wiki_root: Path) -> None:
    by_file = load_page(wiki_root, "python/pandas/templates.md")
    assert isinstance(by_file, Ok) and by_file.value == "# шаблоны\n"
    by_dir = load_page(wiki_root, "python/pandas")  # директория → index.md
    assert isinstance(by_dir, Ok) and by_dir.value.startswith("# pandas")


def test_load_page_not_found(wiki_root: Path) -> None:
    result = load_page(wiki_root, "go/gin")
    assert isinstance(result, Err) and result.code == WIKI_PAGE_NOT_FOUND


def test_load_page_directory_without_index(wiki_root: Path) -> None:
    (wiki_root / "empty_dir").mkdir()
    result = load_page(wiki_root, "empty_dir")
    assert isinstance(result, Err) and result.code == WIKI_PAGE_NOT_FOUND


# --- TSK-1602 build_bundle ---

def test_bundle_directory_index_first_and_dedup(wiki_root: Path) -> None:
    result = build_bundle(
        wiki_root, ["python/pandas", "python/pandas/templates.md"]  # дубликат templates
    )
    assert isinstance(result, Ok)
    assert result.value.index("=== wiki: python/pandas/index.md ===") < result.value.index(
        "=== wiki: python/pandas/templates.md ==="
    )
    assert result.value.count("=== wiki: python/pandas/templates.md ===") == 1


def test_bundle_empty_refs_is_ok(wiki_root: Path) -> None:
    result = build_bundle(wiki_root, [])
    assert isinstance(result, Ok) and result.value == ""


def test_bundle_rejects_literal_placeholders(wiki_root: Path) -> None:
    (wiki_root / "agents" / "bad.md").write_text("шаблон {{NAME}}\n", encoding="utf-8")
    result = build_bundle(wiki_root, ["agents"])
    assert isinstance(result, Err) and result.code == WIKI_PAGE_INVALID
    assert "agents/bad.md" in result.details


def test_bundle_too_large(wiki_root: Path) -> None:
    result = build_bundle(wiki_root, ["python/pandas"], limit_chars=10)
    assert isinstance(result, Err) and result.code == WIKI_BUNDLE_TOO_LARGE


def test_bundle_unknown_ref(wiki_root: Path) -> None:
    result = build_bundle(wiki_root, ["python/pandas", "нет/такого"])
    assert isinstance(result, Err) and result.code == WIKI_PAGE_NOT_FOUND


# --- TSK-1603 check_links ---

def test_check_links_ok_for_file_and_dir_targets(wiki_root: Path) -> None:
    result = check_links(wiki_root, "python/pandas/index.md")
    assert isinstance(result, Ok)
    # ссылки на существующий файл и директорию с index.md — не битые
    assert result.value.broken_links == ()


def test_check_links_reports_broken(wiki_root: Path) -> None:
    (wiki_root / "agents" / "index.md").write_text(
        "[внешняя](https://example.com) [битая](../python/numpy/index.md)\n",
        encoding="utf-8",
    )
    result = check_links(wiki_root, "agents/index.md")
    assert isinstance(result, Ok)
    assert result.value.broken_links == ("../python/numpy/index.md",)


def test_check_links_ignores_links_inside_code(wiki_root: Path) -> None:
    (wiki_root / "agents" / "index.md").write_text(
        "```\nИсходник: [полный текст](<страница>.source.md)\n```\n"
        "инлайн `[пример](тоже-нет.md)` не ссылка\n"
        "[битая](../python/numpy/index.md)\n",
        encoding="utf-8",
    )
    result = check_links(wiki_root, "agents/index.md")
    assert isinstance(result, Ok)
    # ссылки-примеры в fenced/inline коде игнорируются, реальная битая — нет
    assert result.value.broken_links == ("../python/numpy/index.md",)


def test_check_links_page_not_found(wiki_root: Path) -> None:
    result = check_links(wiki_root, "нет.md")
    assert isinstance(result, Err) and result.code == WIKI_PAGE_NOT_FOUND


# --- TSK-1604 parse_wiki_refs_source ---

def test_parse_source_tech_stack(wiki_root: Path) -> None:
    content = (
        '<tech_stack derived_from="task_spec@v1">\n'
        '  <tech ref="python/pandas"><why>агрегаты по CSV</why></tech>\n'
        '  <tech ref="python/fastapi"><why>HTTP-сервис</why></tech>\n'
        "</tech_stack>"
    )
    result = parse_wiki_refs_source(content)
    assert isinstance(result, Ok)
    assert result.value == ["python/pandas", "python/fastapi"]


def test_parse_source_wiki_change_update_pages_only() -> None:
    content = (
        "<wiki_change>\n"
        '  <page path="methodology/workshop-cli.md" action="update">x</page>\n'
        '  <page path="python/duckdb/index.md" action="add">y</page>\n'
        "</wiki_change>"
    )
    result = parse_wiki_refs_source(content)
    assert isinstance(result, Ok)
    assert result.value == ["methodology/workshop-cli.md"]  # add не инжектится


def test_parse_source_all_add_is_legally_empty() -> None:
    content = '<wiki_change><page path="a/b.md" action="add">y</page></wiki_change>'
    result = parse_wiki_refs_source(content)
    assert isinstance(result, Ok) and result.value == []


def test_parse_source_unparseable() -> None:
    result = parse_wiki_refs_source("<tech_stack>пусто</tech_stack>")
    assert isinstance(result, Err) and result.code == WIKI_REFS_SOURCE_UNPARSEABLE


# --- TSK-1606 tree_listing ---

def test_tree_listing_all_pages_sorted(wiki_root: Path) -> None:
    result = tree_listing(wiki_root)
    assert isinstance(result, Ok)
    lines = result.value.splitlines()
    assert lines[0] == "=== wiki tree ==="
    assert lines[1:] == sorted(lines[1:])
    # страница, не упомянутая ни в одном индексе, всё равно видна в дереве
    assert "python/pandas/templates.md" in lines[1:]


def test_tree_listing_missing_root_is_error(tmp_path: Path) -> None:
    result = tree_listing(tmp_path / "no_wiki")
    assert isinstance(result, Err) and result.code == WIKI_PAGE_NOT_FOUND


# --- CLI wiki-check (TSK-0903) ---

def test_cli_wiki_check_clean_and_broken(wiki_root: Path, capsys) -> None:
    from workshop.__main__ import main

    assert main(["wiki-check", "--wiki", str(wiki_root)]) == 0
    assert "проверено" in capsys.readouterr().out

    # ломаем: директория без index.md + битая ссылка + литеральные скобки
    (wiki_root / "domains").mkdir()
    (wiki_root / "agents" / "index.md").write_text(
        "[битая](../go/index.md) и {{NAME}}\n", encoding="utf-8"
    )
    assert main(["wiki-check", "--wiki", str(wiki_root)]) == 1
    captured = capsys.readouterr()
    assert "нет index.md: domains" in captured.err
    assert "битая ссылка в agents/index.md" in captured.err
    assert "литеральные {{ в agents/index.md" in captured.err
