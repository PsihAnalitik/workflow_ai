"""Общие фабрики тестовых конфигов узлов."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import pytest

from workshop.models import LLMParams, NodeConfig, WikiRef

BASE_TEXT = "Задача узла.\n{{INPUTS}}\n"


@pytest.fixture
def make_config(tmp_path: Path) -> Callable[..., NodeConfig]:
    """Фабрика NodeConfig с реальными файлами base/stage в tmp_path."""

    def factory(
        name: str = "node",
        base_text: str = BASE_TEXT,
        wiki_refs: tuple[tuple[str, str], ...] = (),
        wiki_tree_root: str | None = None,
    ) -> NodeConfig:
        base = tmp_path / f"{name}_base.md"
        base.write_text(base_text, encoding="utf-8")
        stage = tmp_path / f"{name}_stage.md"
        stage.write_text("", encoding="utf-8")
        return NodeConfig(
            base_prompt_path=str(base),
            stage_map_path=str(stage),
            wiki_refs=[WikiRef(path=path, version=version) for path, version in wiki_refs],
            wiki_tree_root=wiki_tree_root,
            llm=LLMParams(provider="fake", model="fake-1"),
        )

    return factory


@pytest.fixture
def make_config_file(tmp_path: Path) -> Callable[..., str]:
    """Фабрика JSON-файла конфига узла (для оркестратора, который грузит по пути)."""

    def factory(name: str = "node", base_text: str = BASE_TEXT, **extra) -> str:
        base = tmp_path / f"{name}_base.md"
        base.write_text(base_text, encoding="utf-8")
        stage = tmp_path / f"{name}_stage.md"
        stage.write_text("", encoding="utf-8")
        config_path = tmp_path / f"{name}.json"
        config_path.write_text(
            json.dumps(
                {
                    "base_prompt_path": str(base),
                    "stage_map_path": str(stage),
                    "llm": {"provider": "fake", "model": "fake-1"},
                    **extra,
                }
            ),
            encoding="utf-8",
        )
        return str(config_path)

    return factory
