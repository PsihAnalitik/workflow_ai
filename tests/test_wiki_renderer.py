"""M-17 wiki_renderer: статическая HTML-витрина wiki + CLI wiki-render (TSK-1701)."""
from __future__ import annotations

from pathlib import Path

import pytest

from workshop.__main__ import main
from workshop.result import Err, Ok
from workshop.wiki_renderer import RENDER_TARGET_EXISTS, render_wiki


@pytest.fixture
def wiki_root(tmp_path: Path) -> Path:
    root = tmp_path / "wiki"
    (root / "python" / "pandas").mkdir(parents=True)
    (root / "index.md").write_text(
        "# Карта\n\n| Область | kind |\n|---|---|\n| [python](python/index.md) | tech |\n",
        encoding="utf-8",
    )
    (root / "python" / "index.md").write_text(
        "# Каталог\n\nСм. [pandas](pandas/index.md) и [агентов](../agents).\n",
        encoding="utf-8",
    )
    (root / "python" / "pandas" / "index.md").write_text(
        "# pandas\n\n- когда использовать: **агрегаты** по `DataFrame`\n\n"
        "```mermaid\nflowchart LR\n  A --> B\n```\n\n"
        "```python\ndf.groupby('x')\n```\n",
        encoding="utf-8",
    )
    (root / "assets").mkdir()
    (root / "assets" / "logo.svg").write_text("<svg/>", encoding="utf-8")
    return root


def test_render_structure_links_and_mermaid(wiki_root: Path, tmp_path: Path) -> None:
    out = tmp_path / "site"
    result = render_wiki(wiki_root, out)
    assert isinstance(result, Ok)
    assert result.value.pages == ("index.md", "python/index.md", "python/pandas/index.md")

    index_html = (out / "index.html").read_text(encoding="utf-8")
    assert '<a href="python/index.html">python</a>' in index_html  # .md → .html
    assert "<table>" in index_html and "<th>Область</th>" in index_html

    pandas_html = (out / "python" / "pandas" / "index.html").read_text(encoding="utf-8")
    assert '<pre class="mermaid">flowchart LR' in pandas_html
    assert "mermaid.esm.min.mjs" in pandas_html          # скрипт только там, где схема
    assert "<strong>агрегаты</strong>" in pandas_html
    assert "<code>DataFrame</code>" in pandas_html
    assert '<a href="../../index.html">wiki</a>' in pandas_html  # хлебная крошка

    catalog_html = (out / "python" / "index.html").read_text(encoding="utf-8")
    assert "mermaid" not in catalog_html                  # нет схемы — нет скрипта
    assert '<a href="../agents/index.html">' in catalog_html  # директория → index.html

    assert (out / "assets" / "logo.svg").is_file()        # assets скопированы


def test_render_reports_broken_links(wiki_root: Path, tmp_path: Path) -> None:
    result = render_wiki(wiki_root, tmp_path / "site")
    assert isinstance(result, Ok)
    # ../agents не существует — битая ссылка в отчёте, рендер не прерван
    assert result.value.broken_links == ("python/index.md: ../agents",)


def test_render_target_exists(wiki_root: Path, tmp_path: Path) -> None:
    out = tmp_path / "site"
    out.mkdir()
    (out / "старое.html").write_text("x", encoding="utf-8")
    result = render_wiki(wiki_root, out)
    assert isinstance(result, Err)
    assert result.code == RENDER_TARGET_EXISTS


def test_cli_wiki_render(wiki_root: Path, tmp_path: Path, capsys) -> None:
    out = tmp_path / "site"
    assert main(["wiki-render", "--wiki", str(wiki_root), "--out", str(out)]) == 0
    captured = capsys.readouterr()
    assert "3 страниц" in captured.out
    assert "битая ссылка: python/index.md: ../agents" in captured.err

    # повторный запуск в непустой каталог → отказ
    assert main(["wiki-render", "--wiki", str(wiki_root), "--out", str(out)]) == 1
