"""M-06 workshop_node: исходы ARTIFACT/NEEDS_CLARIFICATION + все ERRORS из TSK-0601."""
from __future__ import annotations

import json
from pathlib import Path

from workshop.llm_client import FakeLLM, fake_ok
from workshop.models import Artifact, ArtifactRef, LLMParams, NodeConfig
from workshop.result import Err, Ok
from workshop.run_log import RunLog
from workshop.workshop_node import (
    LLM_FAILED,
    OUTPUT_UNPARSEABLE,
    PROMPT_BUILD_FAILED,
    ArtifactOutcome,
    ClarificationOutcome,
    run_workshop,
)

UPSTREAM = Artifact(
    ref=ArtifactRef("requirements", 1),
    content='<requirements><fr id="FR-01">a</fr></requirements>',
    derived_from=None,
)


def _run(config, llm, tmp_path, **kwargs):
    return run_workshop("domains", config, UPSTREAM, llm, RunLog(tmp_path / "log.jsonl"), **kwargs)


def test_artifact_outcome_with_crosslinks(make_config, tmp_path: Path) -> None:
    llm = FakeLLM([fake_ok('Готово:\n```xml\n<domains><domain id="D-01"><covers>FR-01</covers></domain></domains>\n```')])
    result = _run(make_config(), llm, tmp_path)
    assert isinstance(result, Ok)
    assert isinstance(result.value, ArtifactOutcome)
    assert result.value.crosslink_report is not None
    assert result.value.crosslink_report.broken_links == ()
    assert "FR-01" in llm.prompts[0]  # upstream впрыснут в INPUTS


def test_upstream_without_ids_gives_no_report(make_config, tmp_path: Path) -> None:
    upstream = Artifact(ArtifactRef("input", 1), "<request>анализ</request>", None)
    llm = FakeLLM([fake_ok("```xml\n<a/>\n```")])
    result = run_workshop("a", make_config(), upstream, llm, RunLog(tmp_path / "l.jsonl"))
    assert isinstance(result, Ok)
    assert isinstance(result.value, ArtifactOutcome)
    assert result.value.crosslink_report is None


def test_wiki_and_iteration_context_in_prompt(make_config, tmp_path: Path) -> None:
    wiki = tmp_path / "pandas.md"
    wiki.write_text("pandas: используй read_csv", encoding="utf-8")
    config = make_config(wiki_refs=((str(wiki), "v1"),))
    llm = FakeLLM([fake_ok("```xml\n<a/>\n```")])
    result = _run(config, llm, tmp_path, iteration=2, iteration_context="Находки ревью: p2 ...")
    assert isinstance(result, Ok)
    prompt = llm.prompts[0]
    assert "pandas: используй read_csv" in prompt
    assert "=== wiki:" in prompt  # бандл M-16 (TSK-1602)
    assert "<iteration_context>" in prompt
    assert "Находки ревью" in prompt


def test_tools_resolved_and_passed_to_llm(make_config, tmp_path: Path) -> None:
    from workshop.llm_client import LLMResponse

    config = make_config().model_copy(update={"tools": ["web_search"]})
    llm = FakeLLM([Ok(LLMResponse(text="```xml\n<a/>\n```", tool_trace=("web_search(q) → r",)))])
    result = _run(config, llm, tmp_path)
    assert isinstance(result, Ok)
    assert llm.tools_seen == [("web_search",)]  # TSK-2102 → TSK-0402
    # трейс инструментов — в журнале (NFR-04)
    record = json.loads((tmp_path / "log.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert record["tool_trace"] == ["web_search(q) → r"]


def test_unknown_tool_fails_before_llm(make_config, tmp_path: Path) -> None:
    from workshop.web_search import UNKNOWN_TOOL

    config = make_config().model_copy(update={"tools": ["web_fetch"]})
    llm = FakeLLM([fake_ok("```xml\n<a/>\n```")])
    result = _run(config, llm, tmp_path)
    assert isinstance(result, Err) and result.code == UNKNOWN_TOOL
    assert llm.prompts == []  # LLM не вызывался


def test_wiki_tree_listing_in_prompt(make_config, tmp_path: Path) -> None:
    root = tmp_path / "wiki"
    (root / "python").mkdir(parents=True)
    (root / "index.md").write_text("# карта\n", encoding="utf-8")
    (root / "python" / "page.md").write_text("# стр\n", encoding="utf-8")
    config = make_config(wiki_tree_root=str(root))
    llm = FakeLLM([fake_ok("```xml\n<a/>\n```")])
    result = _run(config, llm, tmp_path)
    assert isinstance(result, Ok)
    assert "=== wiki tree ===" in llm.prompts[0]
    assert "python/page.md" in llm.prompts[0]  # TSK-1606: дерево в INPUTS


def test_wiki_tree_missing_root_fails_prompt_build(make_config, tmp_path: Path) -> None:
    config = make_config(wiki_tree_root=str(tmp_path / "no_wiki"))
    llm = FakeLLM([fake_ok("```xml\n<a/>\n```")])
    result = _run(config, llm, tmp_path)
    assert isinstance(result, Err)  # явный отказ, не пустой листинг


def test_clarification_outcome(make_config, tmp_path: Path) -> None:
    llm = FakeLLM([fake_ok("NEEDS_CLARIFICATION: какой разделитель в CSV?")])
    result = _run(make_config(), llm, tmp_path)
    assert isinstance(result, Ok)
    assert isinstance(result.value, ClarificationOutcome)
    assert result.value.question == "какой разделитель в CSV?"


def test_clarification_without_question_unparseable(make_config, tmp_path: Path) -> None:
    llm = FakeLLM([fake_ok("NEEDS_CLARIFICATION")])
    result = _run(make_config(), llm, tmp_path)
    assert isinstance(result, Err)
    assert result.code == OUTPUT_UNPARSEABLE


def test_no_artifact_block_unparseable(make_config, tmp_path: Path) -> None:
    llm = FakeLLM([fake_ok("просто рассуждения без артефакта")])
    result = _run(make_config(), llm, tmp_path)
    assert isinstance(result, Err)
    assert result.code == OUTPUT_UNPARSEABLE


def test_llm_failed_but_run_is_logged(make_config, tmp_path: Path) -> None:
    llm = FakeLLM([Err("PROVIDER_ERROR", "500")])
    result = _run(make_config(), llm, tmp_path)
    assert isinstance(result, Err)
    assert result.code == LLM_FAILED
    entries = [
        json.loads(line)
        for line in (tmp_path / "log.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(entries) == 1
    assert "PROVIDER_ERROR" in entries[0]["response"]


def test_prompt_build_failed_on_missing_base(tmp_path: Path) -> None:
    config = NodeConfig(
        base_prompt_path=str(tmp_path / "нет.md"),
        stage_map_path=str(tmp_path / "тоже_нет.md"),
        llm=LLMParams(provider="fake", model="fake-1"),
    )
    result = _run(config, FakeLLM([]), tmp_path)
    assert isinstance(result, Err)
    assert result.code == PROMPT_BUILD_FAILED


def test_marker_inside_artifact_data_is_not_clarification(make_config, tmp_path: Path) -> None:
    """Слово NEEDS_CLARIFICATION в ДАННЫХ артефакта не инжектится в протокол.

    Реальный случай (09.07.2026): source_request упоминал маркер текстом —
    узел уходил в ложный clarification и вис на stdin.
    """
    response = (
        "```xml\n<spec><source_request>вопросы NEEDS_CLARIFICATION задаются "
        "в терминале</source_request></spec>\n```"
    )
    llm = FakeLLM([fake_ok(response)])
    result = _run(make_config(), llm, tmp_path)
    assert isinstance(result, Ok)
    assert isinstance(result.value, ArtifactOutcome)   # артефакт, не вопрос
    assert "NEEDS_CLARIFICATION задаются" in result.value.content
