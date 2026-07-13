"""M-03 prompt_builder: happy paths + все ERRORS из TSK-0301/0302 + golden на реальных файлах."""
from __future__ import annotations

from pathlib import Path

from workshop.prompt_builder import (
    DUPLICATE_FRAGMENT,
    FRAGMENT_MALFORMED,
    INPUTS_EMPTY,
    UNRESOLVED_PLACEHOLDER,
    assemble,
    parse_stage_map,
)
from workshop.result import Err, Ok

REPO_ROOT = Path(__file__).parent.parent

STAGE_MAP = (
    "<!-- @fragment: A -->\nalpha\n<!-- @end -->\n"
    "<!-- @fragment: B -->\nbeta\nline2\n<!-- @end -->\n"
)


def test_parse_stage_map_ok() -> None:
    result = parse_stage_map(STAGE_MAP)
    assert isinstance(result, Ok)
    assert result.value == {"A": "alpha", "B": "beta\nline2"}


def test_parse_fragment_malformed() -> None:
    result = parse_stage_map("<!-- @fragment: A -->\nalpha без закрытия")
    assert isinstance(result, Err)
    assert result.code == FRAGMENT_MALFORMED
    assert "A" in result.details


def test_parse_duplicate_fragment() -> None:
    result = parse_stage_map(STAGE_MAP + "<!-- @fragment: A -->\nagain\n<!-- @end -->\n")
    assert isinstance(result, Err)
    assert result.code == DUPLICATE_FRAGMENT
    assert result.details == "A"


def test_assemble_ok() -> None:
    result = assemble("X {{A}} Y {{INPUTS}}", {"A": "alpha"}, "<req/>")
    assert isinstance(result, Ok)
    assert result.value == "X alpha Y <req/>"


def test_assemble_unresolved_placeholder() -> None:
    result = assemble("{{A}} {{B}}", {"A": "alpha"}, "<req/>")
    assert isinstance(result, Err)
    assert result.code == UNRESOLVED_PLACEHOLDER
    assert result.details == "B"


def test_assemble_inputs_empty() -> None:
    result = assemble("{{INPUTS}}", {}, "   ")
    assert isinstance(result, Err)
    assert result.code == INPUTS_EMPTY


def test_assemble_nested_placeholder_is_deterministic_refusal() -> None:
    result = assemble("{{A}}", {"A": "see {{HIDDEN}}"}, "<req/>")
    assert isinstance(result, Err)
    assert result.code == UNRESOLVED_PLACEHOLDER
    assert "HIDDEN" in result.details


def test_assemble_strips_leading_header_comment() -> None:
    base = "<!-- doc: тут упоминается {{NAME}} -->\nbody {{A}}"
    result = assemble(base, {"A": "x"}, "<req/>")
    assert isinstance(result, Ok)
    assert result.value == "\nbody x"
    assert "NAME" not in result.value


def test_assemble_preserves_body_comments() -> None:
    base = "<!-- заголовок -->\nФормат: XML <!-- WHY: пример --> и {{A}}"
    result = assemble(base, {"A": "x"}, "<req/>")
    assert isinstance(result, Ok)
    assert "<!-- WHY: пример -->" in result.value


def test_golden_real_base_and_stage_domains() -> None:
    base = (REPO_ROOT / "user_docs/prompts/artifact_generator.base.md").read_text(
        encoding="utf-8"
    )
    stage_text = (REPO_ROOT / "user_docs/prompts/stage.domains.md").read_text(
        encoding="utf-8"
    )
    requirements = (REPO_ROOT / "text_searcher/requirements.xml").read_text(
        encoding="utf-8"
    )

    fragments = parse_stage_map(stage_text)
    assert isinstance(fragments, Ok)
    assert set(fragments.value) == {
        "ARTIFACT",
        "UPSTREAM_REF",
        "TECH_MODE",
        "CROSS_LINKS",
        "STAGE_RULES",
        "PROCESS",
        "SELF_CHECK_EXTRA",
        "TRACE_COLUMNS",
    }

    result = assemble(base, fragments.value, requirements)
    assert isinstance(result, Ok)
    assert "{{" not in result.value
    assert "domains.xml" in result.value          # ARTIFACT подставлен
    assert "FR-01" in result.value                # requirements впрыснуты в INPUTS
