"""M-19 factory_cli: реестр цехов, статус проектов, меню, run-по-имени (FR-22)."""
from __future__ import annotations

import json
from pathlib import Path

from workshop.__main__ import main
from workshop.factory_cli import (
    PROJECT_NOT_FOUND,
    SHOPS_ROOT_NOT_FOUND,
    discover_shops,
    project_status,
    run_menu,
)
from workshop.result import Err, Ok


# --- TSK-1901 discover_shops ---

def test_discover_shops_on_real_configs() -> None:
    result = discover_shops()
    assert isinstance(result, Ok)
    by_name = {shop.name: shop for shop in result.value}
    assert {"data_analyst", "microservice", "wiki_maintainer"} <= set(by_name)
    assert "products" not in by_name  # каталог без graph.json — не цех
    analyst = by_name["data_analyst"]
    assert analyst.error is None and analyst.project == "sales_analysis"
    assert [stage.node_id for stage in analyst.stages] == [
        "task_spec", "tech_selection", "executor",
    ]
    assert analyst.autopilot_path is not None
    assert any("hitl" in stage.gates for stage in analyst.stages)


def test_discover_shops_broken_graph_does_not_break_registry(tmp_path: Path) -> None:
    (tmp_path / "good").mkdir()
    (tmp_path / "good" / "graph.json").write_text('{"nodes": []}', encoding="utf-8")
    (tmp_path / "broken").mkdir()
    (tmp_path / "broken" / "graph.json").write_text("не json", encoding="utf-8")
    result = discover_shops(tmp_path)
    assert isinstance(result, Ok)
    by_name = {shop.name: shop for shop in result.value}
    assert by_name["good"].error is None
    assert by_name["broken"].error is not None


def test_discover_shops_root_missing(tmp_path: Path) -> None:
    result = discover_shops(tmp_path / "нет")
    assert isinstance(result, Err) and result.code == SHOPS_ROOT_NOT_FOUND


# --- TSK-1902 project_status ---

def test_project_status(tmp_path: Path) -> None:
    project = tmp_path / "demo"
    (project / "artifacts" / "task_spec").mkdir(parents=True)
    (project / "artifacts" / "task_spec" / "v1.xml").write_text("<a/>", encoding="utf-8")
    (project / "artifacts" / "task_spec" / "v2.xml").write_text("<b/>", encoding="utf-8")
    (project / "runs").mkdir()
    (project / "runs" / "log.jsonl").write_text(
        json.dumps({"node_id": "task_spec", "iteration": 2}) + "\n"
        + "битая строка\n",
        encoding="utf-8",
    )
    result = project_status(project)
    assert isinstance(result, Ok)
    assert result.value.artifacts == (("task_spec", 2),)
    assert result.value.journal == (("task_spec", 2),)


def test_project_status_not_found(tmp_path: Path) -> None:
    result = project_status(tmp_path / "нет")
    assert isinstance(result, Err) and result.code == PROJECT_NOT_FOUND


# --- TSK-1903 меню (скриптованный ввод) ---

def test_menu_run_shop_and_exit() -> None:
    shops = discover_shops()
    assert isinstance(shops, Ok)
    launched: list[tuple[str, str]] = []
    answers = iter([
        "1",            # действие: запустить цех
        "6",            # цех №6 (wiki_maintainer — последний по алфавиту среди 6 цехов)
        "a",            # режим autopilot
        "тестовый вход",
        "3",            # действие: выход
    ])
    printed: list[str] = []
    code = run_menu(
        shops.value,
        runner=lambda graph, material: launched.append((graph, material)) or 0,
        input_fn=lambda _prompt: next(answers),
        print_fn=printed.append,
    )
    assert code == 0
    assert launched == [
        ("configs/wiki_maintainer/graph.autopilot.json", "тестовый вход"),
    ]
    assert any("Цеха:" in line for line in printed)


def test_menu_eof_exits_cleanly() -> None:
    def raise_eof(_prompt: str) -> str:
        raise EOFError
    code = run_menu([], runner=lambda g, m: 0, input_fn=raise_eof, print_fn=lambda s: None)
    assert code == 0


# --- CLI: shops / status / run по имени ---

def test_cli_shops(capsys) -> None:
    assert main(["shops"]) == 0
    out = capsys.readouterr().out
    assert "data_analyst" in out and "wiki_maintainer" in out
    assert "task_spec[review+hitl]" in out


def test_cli_run_resolves_shop_name(capsys) -> None:
    # имя цеха без autopilot-флага резолвится в graph.json; несуществующее имя — ошибка
    assert main(["run", "нет_такого_цеха", "вход"]) == 1
    assert "ни файл, ни цех" in capsys.readouterr().err
