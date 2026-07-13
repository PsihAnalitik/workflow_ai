"""M-20 mcp_server: RunManager с HITL-очередью, инструменты, эскейпы (TSK-2001/2002)."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from workshop.factory_cli import ShopInfo, StageInfo
from workshop.hitl_cli import Accept
from workshop.llm_client import FakeLLM, fake_ok
from workshop.mcp_server import (
    NO_PENDING_INTERACTION,
    RUN_IN_PROGRESS,
    UNKNOWN_RUN,
    UNKNOWN_SHOP,
    WIKI_REF_ESCAPES_ROOT,
    WRONG_DECISION_KIND,
    RunManager,
    _resolve_shop,
    _resolve_wiki_ref,
    build_server,
)
from workshop.result import Err, Ok


def _wait_status(manager: RunManager, run_id: str, statuses: set[str], timeout: float = 5.0) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = manager.get_state(run_id)
        assert isinstance(state, Ok)
        if state.value.status in statuses:
            return state.value.status
        time.sleep(0.01)
    raise AssertionError(f"статус не достигнут: ждали {statuses}")


def _shop(tmp_path: Path, make_config_file, hitl: bool) -> ShopInfo:
    import json
    graph = {
        "project": None,
        "nodes": [{
            "id": "a",
            "config_path": make_config_file("a"),
            "gates": {"hitl": hitl},
        }],
    }
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    return ShopInfo(
        name="testshop", graph_path=str(graph_path), autopilot_path=None,
        project=None, stages=(StageInfo("a", "workshop", "hitl" if hitl else "—"),),
    )


@pytest.fixture
def in_tmp(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.chdir(tmp_path)  # сторы прогонов уходят в projects/ под tmp
    return tmp_path


# --- TSK-2001: полный HITL-цикл ---

def test_run_gate_decision_cycle(in_tmp: Path, make_config_file) -> None:
    manager = RunManager()
    shop = _shop(in_tmp, make_config_file, hitl=True)
    llm = FakeLLM([fake_ok("```xml\n<a/>\n```")])
    started = manager.start_run(shop, "вход", llm=llm)
    assert isinstance(started, Ok)
    run_id = started.value

    assert _wait_status(manager, run_id, {"awaiting_decision"}) == "awaiting_decision"
    pending = manager.pending(run_id)
    assert isinstance(pending, Ok)
    assert pending.value.kind == "decision" and "<a/>" in pending.value.artifact_content

    # неверный вид решения — answer на гейт
    wrong = manager.decide(run_id, "просто текст")
    assert isinstance(wrong, Err) and wrong.code == WRONG_DECISION_KIND

    assert isinstance(manager.decide(run_id, Accept()), Ok)
    assert _wait_status(manager, run_id, {"done"}) == "done"
    state = manager.get_state(run_id).value
    assert any(name.startswith("a@v") for name in state.accepted)


def test_run_clarification_cycle(in_tmp: Path, make_config_file) -> None:
    manager = RunManager()
    shop = _shop(in_tmp, make_config_file, hitl=False)
    llm = FakeLLM([
        fake_ok("NEEDS_CLARIFICATION: какой формат?"),
        fake_ok("```xml\n<a/>\n```"),
    ])
    started = manager.start_run(shop, "вход", llm=llm)
    assert isinstance(started, Ok)
    run_id = started.value

    assert _wait_status(manager, run_id, {"awaiting_answer"}) == "awaiting_answer"
    pending = manager.pending(run_id).value
    assert pending.kind == "answer" and "какой формат" in pending.question

    wrong = manager.decide(run_id, Accept())  # решение гейта на вопрос
    assert isinstance(wrong, Err) and wrong.code == WRONG_DECISION_KIND

    assert isinstance(manager.decide(run_id, "XML"), Ok)
    assert _wait_status(manager, run_id, {"done"}) == "done"


def test_one_run_per_project(in_tmp: Path, make_config_file) -> None:
    manager = RunManager()
    shop = _shop(in_tmp, make_config_file, hitl=True)
    llm = FakeLLM([fake_ok("```xml\n<a/>\n```"), fake_ok("```xml\n<a/>\n```")])
    first = manager.start_run(shop, "вход", llm=llm)
    assert isinstance(first, Ok)
    _wait_status(manager, first.value, {"awaiting_decision"})

    second = manager.start_run(shop, "вход", llm=llm)
    assert isinstance(second, Err) and second.code == RUN_IN_PROGRESS

    assert isinstance(manager.decide(first.value, Accept()), Ok)
    _wait_status(manager, first.value, {"done"})
    third = manager.start_run(shop, "вход", llm=llm)   # завершённый не блокирует
    assert isinstance(third, Ok)
    _wait_status(manager, third.value, {"awaiting_decision"})
    manager.decide(third.value, Accept())


def test_failed_run_state(in_tmp: Path, make_config_file) -> None:
    manager = RunManager()
    shop = _shop(in_tmp, make_config_file, hitl=False)
    llm = FakeLLM([fake_ok("без блока артефакта")])
    started = manager.start_run(shop, "вход", llm=llm)
    assert isinstance(started, Ok)
    assert _wait_status(manager, started.value, {"failed"}) == "failed"
    assert "OUTPUT_UNPARSEABLE" in manager.get_state(started.value).value.error


def test_unknown_run_and_no_pending(in_tmp: Path) -> None:
    manager = RunManager()
    assert manager.get_state("нет").code == UNKNOWN_RUN
    assert manager.pending("нет").code == UNKNOWN_RUN
    assert manager.decide("нет", Accept()).code == UNKNOWN_RUN


# --- TSK-2002: валидация недоверенного ввода и сборка сервера ---

def test_resolve_shop_unknown() -> None:
    result = _resolve_shop("нет_такого")
    assert isinstance(result, Err) and result.code == UNKNOWN_SHOP


def test_wiki_ref_escape_rejected() -> None:
    result = _resolve_wiki_ref("../workshop/models.py")
    assert isinstance(result, Err) and result.code == WIKI_REF_ESCAPES_ROOT
    assert isinstance(_resolve_wiki_ref("python/duckdb"), Ok)


def test_build_server_registers_all_tools() -> None:
    import anyio
    server = build_server(RunManager())
    names = {tool.name for tool in anyio.run(server.list_tools)}
    assert {
        "list_shops", "run_shop", "run_status", "get_pending_interaction",
        "submit_decision", "list_artifacts", "get_artifact", "get_project_status",
        "verify_acceptance_tool", "wiki_update", "wiki_read", "wiki_check",
    } <= names


def test_input_material_file_resolution(tmp_path: Path, monkeypatch) -> None:
    """run_shop: путь внутри фабрики читается, .env и внешние файлы — запрещены."""
    from workshop.mcp_server import INPUT_FILE_FORBIDDEN, _resolve_input_material

    monkeypatch.chdir(tmp_path)
    (tmp_path / "demo.xml").write_text("<input>данные</input>", encoding="utf-8")
    (tmp_path / ".env").write_text("KEY=секрет", encoding="utf-8")
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("вне корня", encoding="utf-8")

    ok = _resolve_input_material("demo.xml")
    assert isinstance(ok, Ok) and ok.value == "<input>данные</input>"
    text = _resolve_input_material("просто текст задачи")
    assert isinstance(text, Ok) and text.value == "просто текст задачи"
    env = _resolve_input_material(".env")
    assert isinstance(env, Err) and env.code == INPUT_FILE_FORBIDDEN
    external = _resolve_input_material(str(outside))
    assert isinstance(external, Err) and external.code == INPUT_FILE_FORBIDDEN


def test_rejected_is_distinct_terminal_status(in_tmp: Path, make_config_file) -> None:
    """REJECTED_BY_USER — решение пользователя, отдельный статус rejected."""
    from workshop.hitl_cli import Reject

    manager = RunManager()
    shop = _shop(in_tmp, make_config_file, hitl=True)
    llm = FakeLLM([fake_ok("```xml\n<a/>\n```")])
    started = manager.start_run(shop, "вход", llm=llm)
    assert isinstance(started, Ok)
    _wait_status(manager, started.value, {"awaiting_decision"})
    assert isinstance(manager.decide(started.value, Reject(reason="не то")), Ok)
    assert _wait_status(manager, started.value, {"rejected"}) == "rejected"
    state = manager.get_state(started.value).value
    assert "не то" in state.error


def test_state_carries_journal_progress(in_tmp: Path, make_config_file) -> None:
    """Узел/итерация берутся из журнала ЭТОГО прогона (offset отрезает историю)."""
    # предзаполняем «чужую» историю журнала
    log = in_tmp / "projects" / "default" / "runs" / "log.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text('{"node_id": "старый_узел", "iteration": 9}\n', encoding="utf-8")

    manager = RunManager()
    shop = _shop(in_tmp, make_config_file, hitl=True)
    llm = FakeLLM([fake_ok("```xml\n<a/>\n```")])
    started = manager.start_run(shop, "вход", llm=llm, project="default")
    assert isinstance(started, Ok)
    _wait_status(manager, started.value, {"awaiting_decision"})
    state = manager.get_state(started.value).value
    assert state.node == "a" and state.iteration == 1   # не «старый_узел»
    manager.decide(started.value, Accept())
    _wait_status(manager, started.value, {"done"})
