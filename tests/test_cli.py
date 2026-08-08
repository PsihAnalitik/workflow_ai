"""TSK-0903 CLI-вход: exit-коды и вывод."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from workshop.__main__ import load_dotenv, main
from workshop.hitl_cli import HITLDecision
from workshop.llm_client import FakeLLM, fake_ok
from workshop.models import Artifact
from workshop.result import Ok, Result


class AutoAcceptHITL:
    def request_acceptance(self, artifact: Artifact, reports: list[str]) -> Result[HITLDecision]:
        raise AssertionError("узлы без hitl-гейта не должны звать приёмку")

    def ask_clarification(self, question: str) -> Result[str]:
        raise AssertionError("clarification не ожидался")


def _write_graph(tmp_path: Path, make_config_file) -> str:
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(
        json.dumps({
            "nodes": [{"id": "a", "config_path": make_config_file("a")}],
            "edges": [],
        }),
        encoding="utf-8",
    )
    return str(graph_path)


def test_cli_happy_path(make_config_file, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    input_file = tmp_path / "input.txt"
    input_file.write_text("<request>анализ</request>", encoding="utf-8")

    exit_code = main(
        [
            "run",
            _write_graph(tmp_path, make_config_file),
            str(input_file),
            "--store", str(tmp_path / "store"),
            "--log", str(tmp_path / "log.jsonl"),
        ],
        llm=FakeLLM([fake_ok("```xml\n<a/>\n```")]),
        hitl=AutoAcceptHITL(),
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "принят: a v1" in captured.out
    assert "log.jsonl" in captured.out


def test_load_dotenv_does_not_override_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# комментарий\nWORKSHOP_TEST_A=из_файла\nWORKSHOP_TEST_B=из_файла\nПУСТО=\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("WORKSHOP_TEST_A", raising=False)
    monkeypatch.setenv("WORKSHOP_TEST_B", "из_окружения")

    load_dotenv(env_file)
    assert os.environ["WORKSHOP_TEST_A"] == "из_файла"
    assert os.environ["WORKSHOP_TEST_B"] == "из_окружения"   # окружение не перекрыто
    assert "ПУСТО" not in os.environ
    monkeypatch.delenv("WORKSHOP_TEST_A", raising=False)


def test_cli_bad_graph_config(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    exit_code = main(
        ["run", str(tmp_path / "нет.json"), "текст запроса"],
        llm=FakeLLM([]),
        hitl=AutoAcceptHITL(),
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    # аргумент run — имя цеха ИЛИ путь (FR-22): несуществующее — общая ошибка резолва
    assert "ни файл, ни цех" in captured.err


def test_cli_project_default_paths(
    make_config_file, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
) -> None:
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(
        json.dumps({
            "project": "demo_project",
            "nodes": [{"id": "a", "config_path": make_config_file("a")}],
            "edges": [],
        }),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(
        ["run", str(graph_path), "текст запроса"],
        llm=FakeLLM([fake_ok("```xml\n<a/>\n```")]),
        hitl=AutoAcceptHITL(),
    )
    assert exit_code == 0
    # выходы легли в projects/<project>/, корень не засорён
    assert (tmp_path / "projects/demo_project/artifacts/a/v1.xml").is_file()
    assert (tmp_path / "projects/demo_project/runs/log.jsonl").is_file()
    assert not (tmp_path / "artifacts").exists()
    captured = capsys.readouterr()
    assert "projects/demo_project/runs/log.jsonl" in captured.out


def test_cli_resume_flag(make_config_file, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    from workshop.artifact_store import ArtifactStore

    store = ArtifactStore(tmp_path / "store")
    input_ref = store.save_artifact("input", "текст запроса")
    store.save_artifact("a", "<a/>", derived_from=input_ref.value)

    exit_code = main(
        [
            "run", "--resume",
            _write_graph(tmp_path, make_config_file),
            "текст запроса",
            "--store", str(tmp_path / "store"),
            "--log", str(tmp_path / "log.jsonl"),
        ],
        llm=FakeLLM([]),          # ни одного вызова LLM не ожидается
        hitl=AutoAcceptHITL(),
    )
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "принят: a v1" in captured.out


ARTIFACT_WITH_FILES = (
    "```file:stats.py\nX = 1\n```\n\n```file:sub/mod.py\nY = 2\n```\n"
)


def test_cli_extract_happy(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    artifact = tmp_path / "executor_v1.xml"
    artifact.write_text(ARTIFACT_WITH_FILES, encoding="utf-8")
    out_dir = tmp_path / "out"

    exit_code = main(["extract", str(artifact), str(out_dir)])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert (out_dir / "stats.py").read_text(encoding="utf-8") == "X = 1\n"
    assert (out_dir / "sub" / "mod.py").read_text(encoding="utf-8") == "Y = 2\n"
    assert "записан" in captured.out


def test_cli_extract_refuses_overwrite(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    artifact = tmp_path / "executor_v1.xml"
    artifact.write_text(ARTIFACT_WITH_FILES, encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "stats.py").write_text("не перезаписывай меня", encoding="utf-8")

    exit_code = main(["extract", str(artifact), str(out_dir)])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "EXTRACT_TARGET_EXISTS" in captured.err
    assert (out_dir / "stats.py").read_text(encoding="utf-8") == "не перезаписывай меня"
    assert not (out_dir / "sub").exists()   # частичной записи нет


def test_cli_extract_no_blocks(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    artifact = tmp_path / "spec.xml"
    artifact.write_text("<spec>обычный артефакт без file map</spec>", encoding="utf-8")
    exit_code = main(["extract", str(artifact), str(tmp_path / "out")])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "NO_FILE_BLOCKS" in captured.err


def test_cli_extract_invalid_path(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    artifact = tmp_path / "evil.xml"
    artifact.write_text("```file:../evil.py\nX = 1\n```\n", encoding="utf-8")
    exit_code = main(["extract", str(artifact), str(tmp_path / "out")])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "EXTRACT_INVALID_PATH" in captured.err


def test_cli_pipeline_error_maps_to_exit_1(
    make_config_file, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    exit_code = main(
        [
            "run",
            _write_graph(tmp_path, make_config_file),
            "текст запроса",
            "--store", str(tmp_path / "store"),
            "--log", str(tmp_path / "log.jsonl"),
        ],
        llm=FakeLLM([fake_ok("ответ без блока артефакта")] * 3),
        hitl=AutoAcceptHITL(),
    )
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "MAX_ITERATIONS_EXCEEDED" in captured.err
