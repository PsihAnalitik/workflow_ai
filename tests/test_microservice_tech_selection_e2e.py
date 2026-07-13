"""FR-19 e2e: цех microservice (реальные конфиги) — стек из wiki, селективный инжект.

Прогон graph.autopilot.json на FakeLLM и фейковой песочнице: tech_selection
выбирает python/fastapi из каталога; C4 получает принятый tech_stack в upstream;
executor получает в INPUTS только страницы выбранной технологии.
"""
from __future__ import annotations

from pathlib import Path

from workshop.artifact_store import ArtifactStore
from workshop.config_loader import load_graph_config
from workshop.llm_client import FakeLLM, fake_ok
from workshop.orchestrator import run_pipeline
from workshop.result import Ok
from workshop.run_log import RunLog
from workshop.sandbox import ExecReport

GRAPH_PATH = "configs/microservice/graph.autopilot.json"

DOMAINS = '```xml\n<domains><domain id="D-01"><covers>FR-01</covers></domain></domains>\n```'
CONTRACTS = '```xml\n<contracts><contract id="C-search"><covers>D-01</covers></contract></contracts>\n```'
OPENAPI = "```yaml\npaths: {/search: {get: {operationId: OP-search}}}\n```"
TECH_STACK = (
    "intent: HTTP-сервис поиска\n```xml\n"
    '<tech_stack derived_from="openapi@v1">\n'
    '  <tech ref="python/fastapi"><why>REST API по C-search/OP-search</why></tech>\n'
    "</tech_stack>\n```"
)
C4 = '```xml\n<developmentplan><container id="api"><covers>C-search</covers></container></developmentplan>\n```'
CODE = "```file:api.py\napp = None\n```\n```file:test_api.py\ndef test_ok(): pass\n```"


def _fake_sandbox(image, files, command, limits):
    return Ok(ExecReport(exit_code=0, stdout="2 passed", stderr="", duration_s=0.1))


def test_microservice_pipeline_stack_from_catalog(tmp_path: Path) -> None:
    graph = load_graph_config(GRAPH_PATH)
    assert isinstance(graph, Ok), f"{graph}"

    llm = FakeLLM([
        fake_ok(DOMAINS),      # domains
        fake_ok(CONTRACTS),    # contracts
        fake_ok(OPENAPI),      # openapi
        fake_ok(TECH_STACK),   # tech_selection
        fake_ok(C4),           # c4
        fake_ok(CODE),         # executor codegen
    ])
    result = run_pipeline(
        graph.value,
        "<requirements><fr id=\"FR-01\">поиск по тексту</fr></requirements>",
        ArtifactStore(tmp_path / "store"),
        llm,
        RunLog(tmp_path / "log.jsonl"),
        hitl=None,  # autopilot: HITL-гейтов в графе нет
        sandbox=_fake_sandbox,
    )
    assert isinstance(result, Ok), f"{result}"
    accepted = {ref.name for ref in result.value.accepted_artifacts}
    assert {"tech_selection", "c4", "executor"} <= accepted

    tech_prompt = llm.prompts[3]
    # каталог технологий — в контексте стадии выбора
    assert "=== wiki: wiki/python/index.md ===" in tech_prompt

    c4_prompt = llm.prompts[4]
    # C4 проектирует в пределах принятого стека: tech_stack в его upstream
    assert "<tech_stack" in c4_prompt

    executor_prompt = llm.prompts[5]
    # селективный инжект: обе страницы выбранной технологии, ничего лишнего
    assert "=== wiki: wiki/python/fastapi/index.md ===" in executor_prompt
    assert "=== wiki: wiki/python/fastapi/testing.md ===" in executor_prompt
    # страницы невыбранных технологий не инжектируются (упоминание словом
    # в related-ссылке карточки fastapi — не инжект)
    assert "=== wiki: wiki/python/pandas" not in executor_prompt
    assert "=== wiki: wiki/python/index.md ===" not in executor_prompt
