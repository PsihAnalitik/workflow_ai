"""M-11 codegen_loop: цикл генерация→тесты→улучшение с фейковой песочницей (TSK-1101)."""
from __future__ import annotations

from pathlib import Path

from workshop.codegen_loop import (
    MAX_ITERATIONS_EXCEEDED,
    _FILE_BLOCK_RE,
    run_codegen,
    serialize_files,
)
from workshop.llm_client import PROVIDER_ERROR, FakeLLM, fake_ok
from workshop.models import Artifact, ArtifactRef, LLMParams
from workshop.result import Err, Ok, Result
from workshop.run_log import RunLog
from workshop.sandbox import DOCKER_UNAVAILABLE, ExecLimits, ExecReport
from workshop.workshop_node import OUTPUT_UNPARSEABLE

C4 = Artifact(ArtifactRef("developmentplan", 1), "<c4>модуль stats</c4>", None)

FILES_RESPONSE = (
    "```file:stats.py\ndef mean(xs): return sum(xs) / len(xs)\n```\n"
    "```file:test_stats.py\nfrom stats import mean\n\ndef test_mean(): assert mean([2, 4]) == 3\n```\n"
)


class FakeSandbox:
    def __init__(self, scripted: list[Result[ExecReport]]) -> None:
        self._scripted = list(scripted)
        self.calls: list[dict[str, str]] = []

    def __call__(self, image, files, command, limits) -> Result[ExecReport]:
        self.calls.append(files)
        return self._scripted.pop(0)


def _report(exit_code: int, stdout: str = "") -> Ok[ExecReport]:
    return Ok(ExecReport(exit_code=exit_code, stdout=stdout, stderr="", duration_s=0.1))


def _run(llm, sandbox, tmp_path, **kwargs):
    return run_codegen(
        "executor", kwargs.pop("config"), C4, llm, RunLog(tmp_path / "log.jsonl"),
        image="python:3.14-slim", sandbox=sandbox, limits=ExecLimits(), **kwargs,
    )


def test_success_after_failed_iteration(make_config, tmp_path: Path) -> None:
    llm = FakeLLM([fake_ok(FILES_RESPONSE), fake_ok(FILES_RESPONSE)])
    sandbox = FakeSandbox([_report(1, "1 failed: деление на ноль"), _report(0, "2 passed")])
    result = _run(llm, sandbox, tmp_path, config=make_config("gen"))
    assert isinstance(result, Ok)
    assert set(result.value.files) == {"stats.py", "test_stats.py"}
    assert result.value.test_report.exit_code == 0
    # rework-контекст ушёл в следующую итерацию: прошлый file map + отчёт тестов
    assert "<previous_artifact>" in llm.prompts[1]
    assert "```file:stats.py" in llm.prompts[1]
    assert "<test_report>" in llm.prompts[1] and "1 failed" in llm.prompts[1]
    assert len(sandbox.calls) == 2


def test_output_without_file_blocks_unparseable(make_config, tmp_path: Path) -> None:
    llm = FakeLLM([fake_ok("вот код: ```python\nx=1\n```")])  # нет блоков file:
    result = _run(llm, FakeSandbox([]), tmp_path, config=make_config("gen"))
    assert isinstance(result, Err)
    assert result.code == OUTPUT_UNPARSEABLE


def test_max_iterations_exceeded(make_config, tmp_path: Path) -> None:
    llm = FakeLLM([fake_ok(FILES_RESPONSE)])
    sandbox = FakeSandbox([_report(1)])
    result = _run(llm, sandbox, tmp_path, config=make_config("gen"), max_iterations=1)
    assert isinstance(result, Err)
    assert result.code == MAX_ITERATIONS_EXCEEDED


def test_consultant_called_before_last_attempt(make_config, tmp_path: Path) -> None:
    """Эксперимент «слабый рабочий + консультант»: провал предпоследней итерации →
    один вызов консультанта со свежим контекстом, совет уходит в последнюю попытку."""
    config = make_config("gen").model_copy(
        update={"consultant_llm": LLMParams(provider="fake", model="consultant-1")}
    )
    llm = FakeLLM([
        fake_ok(FILES_RESPONSE),                     # итерация 1
        fake_ok(FILES_RESPONSE),                     # итерация 2
        fake_ok("Первопричина: mean([]) делит на 0"),  # консультант
        fake_ok(FILES_RESPONSE),                     # итерация 3
    ])
    sandbox = FakeSandbox([_report(1, "fail"), _report(1, "fail"), _report(0, "passed")])
    result = _run(llm, sandbox, tmp_path, config=config)
    assert isinstance(result, Ok)
    # консультации нет после итерации 1 — промпт итерации 2 без совета
    assert "<consultant_advice>" not in llm.prompts[1]
    # промпт консультанта свежий: контракт + файлы + отчёт, без цепочки rework
    assert "<contract>" in llm.prompts[2]
    assert "<previous_artifact>" not in llm.prompts[2]
    # консультант знает окружение и обязан проверить полноту file map
    assert "python:3.14-slim" in llm.prompts[2]  # image из _run
    assert "полноту file map" in llm.prompts[2]
    # sandbox_notes не задан — блока окружения нет (упоминание в инструкции остаётся)
    assert "\n<sandbox_env>\n" not in llm.prompts[2]
    # совет дошёл до последней попытки кодогена
    assert "<consultant_advice>" in llm.prompts[3]
    assert "делит на 0" in llm.prompts[3]


def test_consultant_prompt_includes_sandbox_notes(make_config, tmp_path: Path) -> None:
    config = make_config("gen").model_copy(update={
        "consultant_llm": LLMParams(provider="fake", model="consultant-1"),
        "sandbox_notes": "предустановлены: pytest, pymorphy3",
    })
    llm = FakeLLM([
        fake_ok(FILES_RESPONSE),
        fake_ok(FILES_RESPONSE),
        fake_ok("совет"),
        fake_ok(FILES_RESPONSE),
    ])
    sandbox = FakeSandbox([_report(1), _report(1), _report(0)])
    result = _run(llm, sandbox, tmp_path, config=config)
    assert isinstance(result, Ok)
    assert "<sandbox_env>" in llm.prompts[2]
    assert "pymorphy3" in llm.prompts[2]


def test_consultant_error_does_not_fail_node(make_config, tmp_path: Path) -> None:
    config = make_config("gen").model_copy(
        update={"consultant_llm": LLMParams(provider="fake", model="consultant-1")}
    )
    llm = FakeLLM([
        fake_ok(FILES_RESPONSE),
        fake_ok(FILES_RESPONSE),
        Err(PROVIDER_ERROR, "консультант недоступен"),
        fake_ok(FILES_RESPONSE),
    ])
    sandbox = FakeSandbox([_report(1), _report(1), _report(0)])
    result = _run(llm, sandbox, tmp_path, config=config)
    assert isinstance(result, Ok)
    assert "<consultant_advice>" not in llm.prompts[3]


def test_usage_written_to_run_log(make_config, tmp_path: Path) -> None:
    import json

    from workshop.llm_client import LLMResponse

    llm = FakeLLM([Ok(LLMResponse(text=FILES_RESPONSE, usage={"prompt_tokens": 10, "completion_tokens": 5}))])
    sandbox = FakeSandbox([_report(0)])
    result = _run(llm, sandbox, tmp_path, config=make_config("gen"))
    assert isinstance(result, Ok)
    record = json.loads((tmp_path / "log.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert record["usage"] == {"prompt_tokens": 10, "completion_tokens": 5}


def test_serialize_files_roundtrip() -> None:
    files = {"b.py": "x = 1", "a/mod.py": "y = 2\n"}
    serialized = serialize_files(files)
    parsed = dict(_FILE_BLOCK_RE.findall(serialized))
    assert parsed == {"b.py": "x = 1\n", "a/mod.py": "y = 2\n"}


def test_initial_context_reaches_first_prompt(make_config, tmp_path: Path) -> None:
    llm = FakeLLM([fake_ok(FILES_RESPONSE)])
    sandbox = FakeSandbox([_report(0)])
    result = _run(
        llm, sandbox, tmp_path, config=make_config("gen"),
        initial_context="Правки пользователя: добавь медиану",
    )
    assert isinstance(result, Ok)
    assert "добавь медиану" in llm.prompts[0]


def test_sandbox_error_propagates(make_config, tmp_path: Path) -> None:
    llm = FakeLLM([fake_ok(FILES_RESPONSE)])
    sandbox = FakeSandbox([Err(DOCKER_UNAVAILABLE, "нет docker")])
    result = _run(llm, sandbox, tmp_path, config=make_config("gen"))
    assert isinstance(result, Err)
    assert result.code == DOCKER_UNAVAILABLE


def test_file_map_with_nested_fenced_blocks_roundtrip() -> None:
    """Вложенные fenced-блоки внутри файла (wiki-страницы с примерами кода, FR-21)."""
    from workshop.codegen_loop import parse_file_map, serialize_files

    page = (
        "# wiki: duckdb (v1)\n\nПример:\n```python\nduckdb.query(df)\n```\n"
        "Ещё текст после примера.\n"
    )
    content = (
        f"```file:python/duckdb/index.md\n{page}```\n\n"
        "```file:python/index.md\n# каталог\n```"
    )
    files = parse_file_map(content)
    assert set(files) == {"python/duckdb/index.md", "python/index.md"}
    assert "Ещё текст после примера." in files["python/duckdb/index.md"]
    assert "```python" in files["python/duckdb/index.md"]  # вложенный блок цел
    # roundtrip: сериализация → парсинг возвращает те же файлы
    assert parse_file_map(serialize_files(files)) == files
