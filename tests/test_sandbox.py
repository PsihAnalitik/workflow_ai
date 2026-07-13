"""M-10 sandbox: реальный docker (пропускается, если docker недоступен) + guard путей."""
from __future__ import annotations

import shutil

import pytest

from workshop.result import Err, Ok
from workshop.sandbox import (
    DOCKER_UNAVAILABLE,
    IMAGE_UNAVAILABLE,
    SANDBOX_INVALID_PATH,
    SANDBOX_TIMEOUT,
    ExecLimits,
    run_in_docker,
)

requires_docker = pytest.mark.skipif(
    shutil.which("docker") is None, reason="docker недоступен"
)

IMAGE = "alpine:3.20"


def _skip_if_env_limited(result) -> None:
    if isinstance(result, Err) and result.code in (DOCKER_UNAVAILABLE, IMAGE_UNAVAILABLE):
        pytest.skip(f"docker-окружение ограничено: {result.details}")


def test_invalid_path_rejected_without_docker_run() -> None:
    result = run_in_docker(IMAGE, {"../evil.txt": "x"}, "true")
    assert isinstance(result, Err)
    assert result.code == SANDBOX_INVALID_PATH


@requires_docker
def test_files_mounted_and_stdout_captured() -> None:
    result = run_in_docker(IMAGE, {"data/a.txt": "привет"}, "cat data/a.txt")
    _skip_if_env_limited(result)
    assert isinstance(result, Ok)
    assert result.value.exit_code == 0
    assert "привет" in result.value.stdout


@requires_docker
def test_nonzero_exit_is_ok_result() -> None:
    result = run_in_docker(IMAGE, {}, "exit 7")
    _skip_if_env_limited(result)
    assert isinstance(result, Ok)
    assert result.value.exit_code == 7


@requires_docker
def test_timeout() -> None:
    result = run_in_docker(IMAGE, {}, "sleep 30", ExecLimits(timeout_s=2))
    if isinstance(result, Err) and result.code in (DOCKER_UNAVAILABLE, IMAGE_UNAVAILABLE):
        pytest.skip(f"docker-окружение ограничено: {result.details}")
    assert isinstance(result, Err)
    assert result.code == SANDBOX_TIMEOUT


@requires_docker
def test_image_unavailable() -> None:
    result = run_in_docker("workshop-missing-image-xyz:latest", {}, "true")
    assert isinstance(result, Err)
    # без сети docker отвечает иначе — допускаем оба кода отказа механизма
    assert result.code in (IMAGE_UNAVAILABLE, DOCKER_UNAVAILABLE)
