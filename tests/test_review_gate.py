"""M-07 review_gate: парсинг отчёта, гейт p3/p2 + REPORT_UNPARSEABLE из TSK-0701/0702."""
from __future__ import annotations

from pathlib import Path

from workshop.llm_client import FakeLLM, fake_ok
from workshop.models import Artifact, ArtifactRef
from workshop.result import Err, Ok
from workshop.review_gate import (
    REPORT_UNPARSEABLE,
    VERDICT_UNPARSEABLE,
    evaluate_gate,
    findings_as_context,
    parse_verdict,
    run_review,
)
from workshop.run_log import RunLog

ARTIFACT = Artifact(ArtifactRef("domains", 0), "<domains/>", None)

REVIEW_WITH_FINDINGS = """Находки:
🟠p2 [R2] NFR-03: нет метрики → добавить target
🟡p1 [R5] терминология: «корпус» vs «текст» → унифицировать

Гейт: FAIL
"""


def test_run_review_parses_findings(make_config, tmp_path: Path) -> None:
    llm = FakeLLM([fake_ok(REVIEW_WITH_FINDINGS)])
    result = run_review(
        "domains", make_config("rev", base_text="Проверь.\n{{INPUTS}}\n"),
        ARTIFACT, llm, RunLog(tmp_path / "log.jsonl"),
    )
    assert isinstance(result, Ok)
    assert len(result.value.findings) == 2
    first = result.value.findings[0]
    assert (first.weight, first.rule, first.location) == (2, "R2", "NFR-03")
    assert "<domains/>" in llm.prompts[0]  # артефакт впрыснут в INPUTS


def test_gate_fails_on_open_p2(make_config, tmp_path: Path) -> None:
    llm = FakeLLM([fake_ok(REVIEW_WITH_FINDINGS)])
    report = run_review(
        "domains", make_config("rev", base_text="Проверь.\n{{INPUTS}}\n"),
        ARTIFACT, llm, RunLog(tmp_path / "log.jsonl"),
    )
    assert isinstance(report, Ok)
    gate = evaluate_gate(report.value)
    assert gate.passed is False
    assert len(gate.open_findings) == 1        # p1 не блокирует
    assert gate.open_findings[0].weight == 2
    assert "NFR-03" in findings_as_context(gate.open_findings)


def test_empty_report_with_explicit_gate_passes(make_config, tmp_path: Path) -> None:
    llm = FakeLLM([fake_ok("Находок нет.\nГейт: PASS")])
    report = run_review(
        "domains", make_config("rev", base_text="Проверь.\n{{INPUTS}}\n"),
        ARTIFACT, llm, RunLog(tmp_path / "log.jsonl"),
    )
    assert isinstance(report, Ok)
    assert report.value.findings == ()
    assert evaluate_gate(report.value).passed is True


# --- TSK-0703: parse_verdict ---

def test_parse_verdict_ready() -> None:
    result = parse_verdict("<verdict><decision>READY</decision><reasons></reasons></verdict>")
    assert isinstance(result, Ok)
    assert result.value.ready is True


def test_parse_verdict_not_ready_with_reasons() -> None:
    content = (
        "<verdict><coverage/>"
        "<decision>NOT_READY</decision>"
        "<reasons>\n  FR-03: нет модуля топ-3.\n</reasons></verdict>"
    )
    result = parse_verdict(content)
    assert isinstance(result, Ok)
    assert result.value.ready is False
    assert "FR-03" in result.value.reasons


def test_parse_verdict_unparseable() -> None:
    result = parse_verdict("<verdict>всё отлично, наверное</verdict>")
    assert isinstance(result, Err)
    assert result.code == VERDICT_UNPARSEABLE


def test_report_unparseable(make_config, tmp_path: Path) -> None:
    llm = FakeLLM([fake_ok("какие-то рассуждения без формата")])
    result = run_review(
        "domains", make_config("rev", base_text="Проверь.\n{{INPUTS}}\n"),
        ARTIFACT, llm, RunLog(tmp_path / "log.jsonl"),
    )
    assert isinstance(result, Err)
    assert result.code == REPORT_UNPARSEABLE
