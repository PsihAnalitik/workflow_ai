"""FR-19 e2e: цех data_analyst (реальные конфиги) — стек из wiki, селективный инжект.

Прогон graph.autopilot.json на FakeLLM и фейковой песочнице: стадия tech_selection
выбирает python/pandas из каталога, executor получает в INPUTS ТОЛЬКО страницы
выбранной технологии (verify-критерий этапа 8 DevelopmentPlan v2).
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

GRAPH_PATH = "configs/data_analyst/graph.autopilot.json"

TASK_SPEC = (
    "Готово:\n```xml\n<analysis_spec><source_request>итог продаж</source_request>"
    '<fr id="FR-01" priority="must"><acceptance>сумма с точностью до копейки</acceptance></fr>'
    "</analysis_spec>\n```"
)
REVIEW_PASS = "Находок нет.\nГейт: PASS"
TECH_STACK = (
    "intent: анализ CSV, HTTP не нужен\n```xml\n"
    '<tech_stack derived_from="task_spec@v1">\n'
    '  <tech ref="python/pandas"><why>агрегаты по CSV (FR-01)</why></tech>\n'
    "</tech_stack>\n```"
)
CODE = "```file:main.py\nprint('ok')\n```\n```file:test_main.py\ndef test_ok(): pass\n```"
VERDICT = (
    "```xml\n<verdict derived_from=\"analysis_spec.xml@1, executor@0\">\n"
    '<coverage><fr id="FR-01" status="covered" module="main.py" test="test_main.py"/></coverage>\n'
    "<decision>READY</decision>\n<reasons></reasons>\n</verdict>\n```"
)


def _fake_sandbox(image, files, command, limits):
    return Ok(ExecReport(exit_code=0, stdout="2 passed", stderr="", duration_s=0.1))


def test_data_analyst_pipeline_injects_only_selected_stack(tmp_path: Path) -> None:
    graph = load_graph_config(GRAPH_PATH)
    assert isinstance(graph, Ok), f"{graph}"

    llm = FakeLLM([
        fake_ok(TASK_SPEC),      # task_spec
        fake_ok(REVIEW_PASS),    # task_spec review
        fake_ok(TECH_STACK),     # tech_selection
        fake_ok(CODE),           # executor codegen
        fake_ok(VERDICT),        # judge
    ])
    result = run_pipeline(
        graph.value,
        "посчитай итог продаж по demo/sales.csv",
        ArtifactStore(tmp_path / "store"),
        llm,
        RunLog(tmp_path / "log.jsonl"),
        hitl=None,  # autopilot: HITL-гейтов в графе нет
        sandbox=_fake_sandbox,
    )
    assert isinstance(result, Ok), f"{result}"
    accepted = {ref.name for ref in result.value.accepted_artifacts}
    assert {"task_spec", "tech_selection", "executor"} <= accepted

    executor_prompt = llm.prompts[3]
    # селективный инжект: страницы выбранной технологии — в контексте
    assert "=== wiki: wiki/python/pandas/index.md ===" in executor_prompt
    # невыбранные технологии и каталог целиком в контекст исполнителя не попадают
    assert "fastapi" not in executor_prompt
    # upstream исполнителя = ТЗ + принятый tech_stack (judge увидит стек там же)
    assert "<tech_stack" in executor_prompt
    assert "<analysis_spec>" in executor_prompt

    judge_prompt = llm.prompts[4]
    assert "<tech_stack" in judge_prompt  # правило стека судьи проверяемо по INPUTS
