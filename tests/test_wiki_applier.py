"""M-18 wiki_applier + TSK-1605 orphan-детектор + CLI wiki-apply (TSK-1801)."""
from __future__ import annotations

from pathlib import Path

import pytest

from workshop.__main__ import main
from workshop.codegen_loop import NO_FILE_BLOCKS
from workshop.result import Err, Ok
from workshop.wiki_applier import (
    APPLY_INVALID_PATH,
    SOURCE_SPEC_INVALID,
    WIKI_CHECK_FAILED,
    apply_file_map,
    extract_source_page,
)
from workshop.wiki_loader import find_orphans


@pytest.fixture
def wiki_root(tmp_path: Path) -> Path:
    root = tmp_path / "wiki"
    (root / "python" / "pandas").mkdir(parents=True)
    (root / "index.md").write_text("# Карта\n\n- [python](python/index.md)\n", encoding="utf-8")
    (root / "python" / "index.md").write_text(
        "# Каталог\n\n| Технология | ref |\n|---|---|\n| [pandas](pandas/index.md) | `python/pandas` |\n",
        encoding="utf-8",
    )
    (root / "python" / "pandas" / "index.md").write_text("# pandas\n", encoding="utf-8")
    return root


DUCKDB_PAGE = "# duckdb\n\nКогда использовать: SQL по локальным файлам.\n"
CATALOG_WITH_DUCKDB = (
    "# Каталог\n\n| Технология | ref |\n|---|---|\n"
    "| [pandas](pandas/index.md) | `python/pandas` |\n"
    "| [duckdb](duckdb/index.md) | `python/duckdb` |\n"
)


def _file_map(*blocks: tuple[str, str]) -> str:
    return "\n\n".join(f"```file:{path}\n{body}```" for path, body in blocks)


# --- TSK-1605 find_orphans ---

def test_find_orphans_clean_and_detected(wiki_root: Path) -> None:
    result = find_orphans(wiki_root)
    assert isinstance(result, Ok) and result.value == []

    (wiki_root / "python" / "pandas" / "recipes.md").write_text("# рецепты\n", encoding="utf-8")
    result = find_orphans(wiki_root)
    assert isinstance(result, Ok)
    assert result.value == ["python/pandas/recipes.md"]  # нет ссылки ни в одном index.md


# --- TSK-1801 apply_file_map ---

def test_apply_new_tech_with_updated_index(wiki_root: Path) -> None:
    content = _file_map(
        ("python/duckdb/index.md", DUCKDB_PAGE),
        ("python/index.md", CATALOG_WITH_DUCKDB),
    )
    result = apply_file_map(content, wiki_root)
    assert isinstance(result, Ok), f"{result}"
    assert result.value.written == ("python/duckdb/index.md", "python/index.md")
    assert (wiki_root / "python" / "duckdb" / "index.md").read_text(encoding="utf-8") == DUCKDB_PAGE
    assert len(result.value.changelog_rows) == 2
    assert result.value.changelog_rows[0].startswith("| `python/duckdb/index.md` | — | `")


def test_apply_rejects_orphan_page_and_leaves_wiki_untouched(wiki_root: Path) -> None:
    # новая страница БЕЗ строки в индексе → сирота → отказ, реальная wiki не тронута
    content = _file_map(("python/duckdb/index.md", DUCKDB_PAGE))
    result = apply_file_map(content, wiki_root)
    assert isinstance(result, Err) and result.code == WIKI_CHECK_FAILED
    assert "сирота" in result.details
    assert not (wiki_root / "python" / "duckdb").exists()


def test_apply_rejects_path_escape(wiki_root: Path) -> None:
    content = _file_map(("../evil.md", "# зло\n"))
    result = apply_file_map(content, wiki_root)
    assert isinstance(result, Err) and result.code == APPLY_INVALID_PATH


def test_apply_rejects_literal_placeholders(wiki_root: Path) -> None:
    content = _file_map(
        ("python/duckdb/index.md", "# duckdb\n{{NAME}}\n"),
        ("python/index.md", CATALOG_WITH_DUCKDB),
    )
    result = apply_file_map(content, wiki_root)
    assert isinstance(result, Err) and result.code == WIKI_CHECK_FAILED
    assert "литеральные" in result.details


def test_apply_no_file_blocks(wiki_root: Path) -> None:
    result = apply_file_map("просто текст без блоков", wiki_root)
    assert isinstance(result, Err) and result.code == NO_FILE_BLOCKS


def test_apply_updates_existing_page(wiki_root: Path) -> None:
    content = _file_map(("python/pandas/index.md", "# pandas v2\n\nобновлено\n"))
    result = apply_file_map(content, wiki_root)
    assert isinstance(result, Ok)
    assert "обновлено" in (wiki_root / "python" / "pandas" / "index.md").read_text(encoding="utf-8")


# --- TSK-1801 шаг 1a: страница-исходник из спеки ---

DUCKDB_PAGE_WITH_SOURCE = (
    "# duckdb\n\nКогда использовать: SQL по локальным файлам.\n\n"
    "Исходник: [полный текст](index.source.md)\n"
)
SPEC_WITH_SOURCE = (
    "<wiki_change>\n"
    "  <source_request>Запрос: добавь duckdb.\n"
    "Материал: {{шаблон}} и [битая](nope.md) внутри вербатима.</source_request>\n"
    "  <pages><page path=\"python/duckdb/index.md\" action=\"add\"/></pages>\n"
    "  <source_page path=\"python/duckdb/index.source.md\" for=\"python/duckdb/index.md\"/>\n"
    "</wiki_change>\n"
)


def test_extract_source_page_absent_and_present() -> None:
    absent = extract_source_page("<wiki_change><pages/></wiki_change>")
    assert isinstance(absent, Ok) and absent.value is None

    present = extract_source_page(SPEC_WITH_SOURCE)
    assert isinstance(present, Ok) and present.value is not None
    path, body = present.value
    assert path == "python/duckdb/index.source.md"
    assert "Материал: {{шаблон}}" in body  # вербатим, без экранирования
    assert body.startswith("# wiki: исходник — python/duckdb/index.md")


def test_extract_source_page_invalid_spec() -> None:
    bad_suffix = extract_source_page(
        '<source_page path="python/duckdb/src.md" for="python/duckdb/index.md"/>'
        "<source_request>материал</source_request>"
    )
    assert isinstance(bad_suffix, Err) and bad_suffix.code == SOURCE_SPEC_INVALID

    empty_request = extract_source_page(
        '<source_page path="a/b.source.md" for="a/b.md"/><source_request>  </source_request>'
    )
    assert isinstance(empty_request, Err) and empty_request.code == SOURCE_SPEC_INVALID


def test_apply_materializes_source_page(wiki_root: Path) -> None:
    # исходник с {{ и битой ссылкой внутри применяется: вербатим-приложения
    # исключены из проверок содержимого и из orphan-детектора
    content = _file_map(
        ("python/duckdb/index.md", DUCKDB_PAGE_WITH_SOURCE),
        ("python/index.md", CATALOG_WITH_DUCKDB),
    )
    result = apply_file_map(content, wiki_root, SPEC_WITH_SOURCE)
    assert isinstance(result, Ok), f"{result}"
    source_file = wiki_root / "python" / "duckdb" / "index.source.md"
    assert "{{шаблон}}" in source_file.read_text(encoding="utf-8")
    assert "python/duckdb/index.source.md" in result.value.written
    assert len(result.value.changelog_rows) == 3

    orphans = find_orphans(wiki_root)
    assert isinstance(orphans, Ok) and orphans.value == []


def test_apply_without_spec_keeps_old_behaviour(wiki_root: Path) -> None:
    # ссылка на несуществующий исходник без спеки → явный отказ, wiki не тронута
    content = _file_map(
        ("python/duckdb/index.md", DUCKDB_PAGE_WITH_SOURCE),
        ("python/index.md", CATALOG_WITH_DUCKDB),
    )
    result = apply_file_map(content, wiki_root)
    assert isinstance(result, Err) and result.code == WIKI_CHECK_FAILED
    assert "битая ссылка" in result.details
    assert not (wiki_root / "python" / "duckdb").exists()


# --- CLI wiki-apply ---

def test_cli_wiki_apply(wiki_root: Path, tmp_path: Path, capsys) -> None:
    artifact = tmp_path / "wiki_pages_v1.xml"
    artifact.write_text(
        _file_map(
            ("python/duckdb/index.md", DUCKDB_PAGE),
            ("python/index.md", CATALOG_WITH_DUCKDB),
        ),
        encoding="utf-8",
    )
    assert main(["wiki-apply", str(artifact), "--wiki", str(wiki_root)]) == 0
    captured = capsys.readouterr()
    assert "записан:" in captured.out and "CHANGELOG" in captured.out

    bad_artifact = tmp_path / "bad.xml"
    bad_artifact.write_text("```file:orphan/page.md\n# сирота\n```", encoding="utf-8")
    assert main(["wiki-apply", str(bad_artifact), "--wiki", str(wiki_root)]) == 1
    assert "применение отклонено" in capsys.readouterr().err


def test_cli_wiki_apply_with_spec(wiki_root: Path, tmp_path: Path, capsys) -> None:
    artifact = tmp_path / "wiki_pages_v1.xml"
    artifact.write_text(
        _file_map(
            ("python/duckdb/index.md", DUCKDB_PAGE_WITH_SOURCE),
            ("python/index.md", CATALOG_WITH_DUCKDB),
        ),
        encoding="utf-8",
    )
    spec = tmp_path / "wiki_spec_v1.xml"
    spec.write_text(SPEC_WITH_SOURCE, encoding="utf-8")
    assert main(["wiki-apply", str(artifact), "--wiki", str(wiki_root), "--spec", str(spec)]) == 0
    assert "index.source.md" in capsys.readouterr().out
    assert (wiki_root / "python" / "duckdb" / "index.source.md").is_file()
