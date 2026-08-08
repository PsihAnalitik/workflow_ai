"""M-23 map_driver: нарезка элементов, дет.проверки таблиц, map-прогон (TSK-2301..2303)."""
from __future__ import annotations

from pathlib import Path

from workshop.llm_client import FakeLLM, fake_ok
from workshop.map_driver import (
    MAP_NO_ITEMS,
    MAP_PARALLEL_HITL,
    MAP_SOURCE_INVALID,
    MapItem,
    check_table,
    check_template,
    map_run,
    split_files,
    split_schema_tables,
)
from workshop.models import GraphConfig
from workshop.result import Err, Ok

SCHEMA_YAML = """\
databases:
  DWH:
    schemas:
      calc:
        tables:
          b_table:
            description: агрегат поездок
            granularity: дневная
            fact_metrics:
            - column: trips_cnt
              aggregation: SUM
              additive: true
            columns:
              dt: {type: DATE}
              trips_cnt: {type: INT}
          a_table:
            description: ''
            columns: {}
"""


# --- TSK-2301а: файлы ---

def test_split_files_sorted_and_slugged(tmp_path: Path) -> None:
    (tmp_path / "B_PROMPT.md").write_text("б", encoding="utf-8")
    (tmp_path / "A_PROMPT.md").write_text("а", encoding="utf-8")
    result = split_files(str(tmp_path / "*.md"))
    assert isinstance(result, Ok)
    assert [item.slug for item in result.value] == ["A_PROMPT", "B_PROMPT"]
    assert "Ревьюируемый файл: A_PROMPT.md" in result.value[0].content
def test_split_files_defuses_double_braces_with_note(tmp_path: Path) -> None:
    """TSK-2619: цитата двойных скобок в отчёте роняет сборку промпта приёмщика.

    Замена детерминирована и до модели; молчаливой она быть не может —
    у prompt_roaster двойные скобки сами являются предметом ревью.
    """
    (tmp_path / "prompt.md").write_text(
        "Шаблон: " + "{" "{INPUTS}" "}" + " и хвост", encoding="utf-8"
    )
    result = split_files(str(tmp_path / "*.md"))
    assert isinstance(result, Ok)
    content = result.value[0].content
    assert "{" "{" not in content and "}" "}" not in content
    assert "{ {INPUTS} }" in content
    assert "разведены пробелом" in content


def test_split_files_without_braces_has_no_note(tmp_path: Path) -> None:
    (tmp_path / "plain.md").write_text("обычный текст", encoding="utf-8")
    result = split_files(str(tmp_path / "*.md"))
    assert isinstance(result, Ok)
    assert "разведены пробелом" not in result.value[0].content


def test_split_files_slug_collision_gets_parent_prefix(tmp_path: Path) -> None:
    """11 __init__.py разных пакетов не должны сливаться в один элемент."""
    for pkg in ("core", "nodes"):
        (tmp_path / pkg).mkdir()
        (tmp_path / pkg / "__init__.py").write_text("", encoding="utf-8")
        (tmp_path / pkg / f"{pkg}_mod.py").write_text("x = 1", encoding="utf-8")
    result = split_files([str(tmp_path / "*" / "*.py")])
    assert isinstance(result, Ok)
    slugs = {item.slug for item in result.value}
    assert {"core____init__", "nodes____init__", "core_mod", "nodes_mod"} == slugs


def test_split_files_multiple_patterns_deduped(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("A", encoding="utf-8")
    (tmp_path / "b.md").write_text("B", encoding="utf-8")
    result = split_files([str(tmp_path / "a.md"), str(tmp_path / "*.md")])
    assert isinstance(result, Ok)
    assert [item.slug for item in result.value] == ["a", "b"]  # дедуп + сортировка


def test_split_files_empty_glob(tmp_path: Path) -> None:
    result = split_files(str(tmp_path / "*.md"))
    assert isinstance(result, Err)
    assert result.code == MAP_NO_ITEMS


# --- TSK-2301б: таблицы schema.yaml ---

def test_split_schema_tables_items_and_cards(tmp_path: Path) -> None:
    schema = tmp_path / "schema.yaml"
    schema.write_text(SCHEMA_YAML, encoding="utf-8")
    cards = tmp_path / "cards"
    cards.mkdir()
    (cards / "calc_b_table.yaml").write_text("typical_questions: [сколько поездок]", encoding="utf-8")

    result = split_schema_tables(str(schema), str(cards))
    assert isinstance(result, Ok)
    slugs = [item.slug for item in result.value]
    assert slugs == ["calc.a_table", "calc.b_table"]
    a_item, b_item = result.value
    # у a_table дет.находки (пустые description/columns), карточки нет
    assert "<deterministic_findings>" in a_item.content
    assert "Карточки таблицы в table_cards НЕТ" in a_item.content
    # у b_table карточка подшита, дет.находок нет
    assert "typical_questions" in b_item.content
    assert "<deterministic_findings>" not in b_item.content


def test_split_schema_tables_invalid_yaml(tmp_path: Path) -> None:
    schema = tmp_path / "schema.yaml"
    schema.write_text("databases: [::", encoding="utf-8")
    result = split_schema_tables(str(schema))
    assert isinstance(result, Err)
    assert result.code == MAP_SOURCE_INVALID


# --- TSK-2304: шаблонные проверки ---

TEMPLATE = {
    "required": ["description", "columns"],
    "optional": ["granularity"],
    "nested": {"columns": {"required": ["type"], "optional": ["description"]}},
}


def test_check_template_missing_unknown_nested() -> None:
    findings = check_template(
        {"columns": {"dt": {"description": "дата"}}, "лишний": 1},
        TEMPLATE,
        "table",
    )
    assert any("обязательный ключ «description»" in f for f in findings)
    assert any("неизвестный ключ «лишний»" in f for f in findings)
    assert any("columns.dt" in f and "«type»" in f for f in findings)


def test_check_template_clean() -> None:
    data = {"description": "агрегат", "columns": {"dt": {"type": "DATE"}}}
    assert check_template(data, TEMPLATE, "table") == []


# --- TSK-2305: трёхсторонний join ---

TOOLS_YAML = """\
tools:
  - name: mcp_b
    table: calc.b_table
    description: тул таблицы b
    params: [metrics]
"""


def test_split_with_tools_and_templates(tmp_path: Path) -> None:
    schema = tmp_path / "schema.yaml"
    schema.write_text(SCHEMA_YAML, encoding="utf-8")
    tools = tmp_path / "tools.yaml"
    tools.write_text(TOOLS_YAML, encoding="utf-8")
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "tool.yaml").write_text(
        "required: [name, table, description, required_params]\n"
        "optional: [params]\n",
        encoding="utf-8",
    )

    result = split_schema_tables(str(schema), None, str(tools), str(templates))
    assert isinstance(result, Ok)
    a_item, b_item = result.value
    assert "MCP-инструментов для таблицы в tools.yaml НЕТ" in a_item.content
    assert "mcp_b" in b_item.content
    # шаблон tool: у mcp_b нет required_params → дет-находка
    assert "обязательный ключ «required_params»" in b_item.content


def test_split_templates_dir_invalid(tmp_path: Path) -> None:
    schema = tmp_path / "schema.yaml"
    schema.write_text(SCHEMA_YAML, encoding="utf-8")
    result = split_schema_tables(str(schema), None, None, str(tmp_path / "нет"))
    assert isinstance(result, Err)
    assert result.code == MAP_SOURCE_INVALID


# --- TSK-2303: детерминированные проверки ---

def test_check_table_finds_gaps() -> None:
    findings = check_table(
        {
            "description": "",
            "columns": {"dt": {"type": "DATE"}},
            "fact_metrics": [{"column": "нет_такой", "aggregation": "SUM"}],
        }
    )
    assert any("description" in finding for finding in findings)
    assert any("granularity" in finding for finding in findings)
    assert any("нет_такой" in finding for finding in findings)


def test_check_table_clean() -> None:
    findings = check_table(
        {
            "description": "агрегат",
            "granularity": "дневная",
            "columns": {"dt": {}, "cnt": {}},
            "fact_metrics": [{"column": "cnt"}],
        }
    )
    assert findings == []


# --- TSK-2302: map-прогон ---

def _mini_graph(make_config_file) -> GraphConfig:
    return GraphConfig.model_validate(
        {"nodes": [{"id": "check", "config_path": make_config_file("check")}]}
    )


def test_map_run_per_item_stores_and_summary(make_config_file, tmp_path: Path) -> None:
    graph = _mini_graph(make_config_file)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "one.md").write_text("раз", encoding="utf-8")
    (tmp_path / "src" / "two.md").write_text("два", encoding="utf-8")
    items = split_files(str(tmp_path / "src" / "*.md"))
    assert isinstance(items, Ok)

    llm = FakeLLM([fake_ok("```xml\n<r/>\n```"), fake_ok("```xml\n<r/>\n```")])
    report = map_run(graph, items.value, llm, hitl=None, base_dir=tmp_path / "proj")
    assert isinstance(report, Ok)
    assert [row.status for row in report.value.rows] == ["done", "done"]
    assert (tmp_path / "proj" / "map" / "one" / "artifacts").is_dir()
    summary = Path(report.value.summary_path).read_text(encoding="utf-8")
    assert "| `one` | done |" in summary
    assert "done 2, failed 0, skipped 0" in summary


def test_map_run_failure_does_not_stop_and_resume_skips(
    make_config_file, tmp_path: Path
) -> None:
    graph = _mini_graph(make_config_file)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "one.md").write_text("раз", encoding="utf-8")
    (tmp_path / "src" / "two.md").write_text("два", encoding="utf-8")
    items = split_files(str(tmp_path / "src" / "*.md")).value

    # первый элемент упадёт (3 ответа без артефакта — rework исчерпан), второй пройдёт
    llm = FakeLLM([fake_ok("нет ни блока, ни маркера")] * 3 + [fake_ok("```xml\n<r/>\n```")])
    report = map_run(graph, items, llm, hitl=None, base_dir=tmp_path / "proj")
    assert isinstance(report, Ok)
    assert [row.status for row in report.value.rows] == ["failed", "done"]

    # resume: two принят → skipped; one перезапускается и проходит
    llm2 = FakeLLM([fake_ok("```xml\n<r/>\n```")])
    report2 = map_run(
        graph, items, llm2, hitl=None, base_dir=tmp_path / "proj", resume=True
    )
    assert isinstance(report2, Ok)
    assert [row.status for row in report2.value.rows] == ["done", "skipped"]


# --- TSK-2306: параллельный map ---

class StatelessFakeLLM:
    """Потокобезопасный фейк: всем один и тот же ответ (без разделяемого сценария)."""

    def __init__(self, text: str) -> None:
        self._text = text

    def complete(self, prompt, params, tools=()):
        return fake_ok(self._text)


def test_map_run_parallel_keeps_item_order(make_config_file, tmp_path: Path) -> None:
    graph = _mini_graph(make_config_file)
    (tmp_path / "src").mkdir()
    for name in ("a.md", "b.md", "c.md", "d.md"):
        (tmp_path / "src" / name).write_text(name, encoding="utf-8")
    items = split_files(str(tmp_path / "src" / "*.md")).value

    llm = StatelessFakeLLM("```xml\n<r/>\n```")
    report = map_run(
        graph, items, llm, hitl=None, base_dir=tmp_path / "proj", workers=4
    )
    assert isinstance(report, Ok)
    assert [row.slug for row in report.value.rows] == ["a", "b", "c", "d"]
    assert all(row.status == "done" for row in report.value.rows)


def test_map_run_parallel_rejects_hitl_graph(make_config_file, tmp_path: Path) -> None:
    graph = GraphConfig.model_validate(
        {
            "nodes": [
                {
                    "id": "check",
                    "config_path": make_config_file("check"),
                    "gates": {"hitl": True},
                }
            ]
        }
    )
    # содержимое не важно: отказ обязан случиться ДО прогонов
    items = [MapItem("x", "x", "х")]
    report = map_run(
        graph, items, StatelessFakeLLM(""), hitl=None,
        base_dir=tmp_path / "proj", workers=2,
    )
    assert isinstance(report, Err)
    assert report.code == MAP_PARALLEL_HITL


def test_map_run_limit(make_config_file, tmp_path: Path) -> None:
    graph = _mini_graph(make_config_file)
    (tmp_path / "src").mkdir()
    for name in ("a.md", "b.md", "c.md"):
        (tmp_path / "src" / name).write_text(name, encoding="utf-8")
    items = split_files(str(tmp_path / "src" / "*.md")).value

    llm = FakeLLM([fake_ok("```xml\n<r/>\n```")])
    report = map_run(graph, items, llm, hitl=None, base_dir=tmp_path / "proj", limit=1)
    assert isinstance(report, Ok)
    assert len(report.value.rows) == 1
