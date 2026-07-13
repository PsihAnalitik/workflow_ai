"""M-05 run_log: happy path + LOG_IO_ERROR из TSK-0501."""
from __future__ import annotations

import json
from pathlib import Path

from workshop.result import Err, Ok
from workshop.run_log import LOG_IO_ERROR, RunLog, RunRecord


def _record(iteration: int) -> RunRecord:
    return RunRecord(
        node_id="domains",
        iteration=iteration,
        prompt="собранный промпт",
        input_ref="requirements@v1",
        params={"provider": "anthropic", "model": "claude-sonnet-5"},
        response="<domains/>",
    )


def test_append_is_replayable(tmp_path: Path) -> None:
    log = RunLog(tmp_path / "runs" / "log.jsonl")

    first = log.append(_record(1))
    second = log.append(_record(2))
    assert isinstance(first, Ok) and first.value.line_number == 1
    assert isinstance(second, Ok) and second.value.line_number == 2

    lines = (tmp_path / "runs" / "log.jsonl").read_text(encoding="utf-8").splitlines()
    entries = [json.loads(line) for line in lines]
    assert len(entries) == 2
    # запись содержит всё для воспроизведения прогона (NFR-04)
    assert entries[0]["prompt"] == "собранный промпт"
    assert entries[0]["params"]["model"] == "claude-sonnet-5"
    assert entries[1]["iteration"] == 2
    assert "logged_at" in entries[0]


def test_log_io_error(tmp_path: Path) -> None:
    result = RunLog(tmp_path).append(_record(1))  # путь — каталог, не файл
    assert isinstance(result, Err)
    assert result.code == LOG_IO_ERROR
