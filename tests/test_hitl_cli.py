"""M-08 hitl_cli: решения ACCEPT/REVISE/REJECT + INPUT_ABORTED из TSK-0801/0802."""
from __future__ import annotations

from workshop.hitl_cli import INPUT_ABORTED, Accept, CliHITL, Reject, Revise
from workshop.models import Artifact, ArtifactRef
from workshop.result import Err, Ok

ARTIFACT = Artifact(ArtifactRef("domains", 0), "<domains/>", None)


def _cli(*answers: str) -> CliHITL:
    iterator = iter(answers)

    def scripted_input(_prompt: str) -> str:
        try:
            return next(iterator)
        except StopIteration:
            raise EOFError from None

    return CliHITL(input_fn=scripted_input, print_fn=lambda _line: None)


def test_accept() -> None:
    result = _cli("a").request_acceptance(ARTIFACT, ["отчёт"])
    assert isinstance(result, Ok)
    assert isinstance(result.value, Accept)


def test_revise_with_comments() -> None:
    result = _cli("r", "добавь NFR по памяти").request_acceptance(ARTIFACT, [])
    assert isinstance(result, Ok)
    assert result.value == Revise(comments="добавь NFR по памяти")


def test_reject_with_reason() -> None:
    result = _cli("x", "не та декомпозиция").request_acceptance(ARTIFACT, [])
    assert isinstance(result, Ok)
    assert result.value == Reject(reason="не та декомпозиция")


def test_invalid_input_reprompts() -> None:
    result = _cli("что?", "a").request_acceptance(ARTIFACT, [])
    assert isinstance(result, Ok)
    assert isinstance(result.value, Accept)


def test_input_aborted() -> None:
    result = _cli().request_acceptance(ARTIFACT, [])
    assert isinstance(result, Err)
    assert result.code == INPUT_ABORTED


def test_ask_clarification_skips_empty_answer() -> None:
    result = _cli("", "разделитель — точка с запятой").ask_clarification("какой разделитель?")
    assert isinstance(result, Ok)
    assert result.value == "разделитель — точка с запятой"


def test_ask_clarification_aborted() -> None:
    result = _cli().ask_clarification("вопрос?")
    assert isinstance(result, Err)
    assert result.code == INPUT_ABORTED
