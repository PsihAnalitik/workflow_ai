"""M-01 config_loader: happy paths + все ERRORS из TSK-0101/0102."""
from __future__ import annotations

import json
from pathlib import Path

from workshop.config_loader import (
    CONFIG_INVALID,
    CONFIG_NOT_FOUND,
    GRAPH_CYCLE,
    UNKNOWN_LLM_PROFILE,
    UNKNOWN_NODE_REF,
    load_graph_config,
    load_model_registry,
    load_node_config,
)
from workshop.models import LLMParams, ModelPolicy, ModelRegistry
from workshop.result import Err, Ok

VALID_NODE = {
    "base_prompt_path": "prompts/base.md",
    "stage_map_path": "prompts/stage.domains.md",
    "wiki_refs": [{"path": "wiki/pandas.md", "version": "v1"}],
    "tools": ["read_csv"],
    "llm": {"provider": "anthropic", "model": "claude-sonnet-5", "seed": 42},
}

VALID_GRAPH = {
    "nodes": [
        {"id": "requirements", "config_path": "nodes/req.json", "gates": {"hitl": True}},
        {"id": "domains", "config_path": "nodes/dom.json"},
    ],
    "edges": [{"from": "requirements", "to": "domains"}],
}


def _write(tmp_path: Path, payload: object) -> str:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_load_node_config_ok(tmp_path: Path) -> None:
    result = load_node_config(_write(tmp_path, VALID_NODE))
    assert isinstance(result, Ok)
    assert result.value.llm.temperature == 0.0
    assert result.value.wiki_refs[0].version == "v1"


def test_node_config_not_found(tmp_path: Path) -> None:
    result = load_node_config(str(tmp_path / "missing.json"))
    assert isinstance(result, Err)
    assert result.code == CONFIG_NOT_FOUND


def test_node_config_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{not json", encoding="utf-8")
    result = load_node_config(str(path))
    assert isinstance(result, Err)
    assert result.code == CONFIG_INVALID


def test_node_config_not_an_object(tmp_path: Path) -> None:
    result = load_node_config(_write(tmp_path, [1, 2]))
    assert isinstance(result, Err)
    assert result.code == CONFIG_INVALID


def test_node_config_missing_field(tmp_path: Path) -> None:
    payload = {key: value for key, value in VALID_NODE.items() if key != "llm"}
    result = load_node_config(_write(tmp_path, payload))
    assert isinstance(result, Err)
    assert result.code == CONFIG_INVALID
    assert "llm" in result.details


def test_load_graph_config_ok(tmp_path: Path) -> None:
    result = load_graph_config(_write(tmp_path, VALID_GRAPH))
    assert isinstance(result, Ok)
    assert result.value.edges[0].from_node == "requirements"
    assert result.value.nodes[0].max_iterations == 3


def test_graph_unknown_node_ref(tmp_path: Path) -> None:
    payload = {
        "nodes": VALID_GRAPH["nodes"],
        "edges": [{"from": "requirements", "to": "ghost"}],
    }
    result = load_graph_config(_write(tmp_path, payload))
    assert isinstance(result, Err)
    assert result.code == UNKNOWN_NODE_REF
    assert result.details == "ghost"


def test_graph_cycle(tmp_path: Path) -> None:
    payload = {
        "nodes": VALID_GRAPH["nodes"],
        "edges": [
            {"from": "requirements", "to": "domains"},
            {"from": "domains", "to": "requirements"},
        ],
    }
    result = load_graph_config(_write(tmp_path, payload))
    assert isinstance(result, Err)
    assert result.code == GRAPH_CYCLE
    assert "domains" in result.details
    assert "requirements" in result.details


# --- TSK-0103 (реестр + политика FR-16) и резолюция источников модели ---

REGISTRY = ModelRegistry(
    profiles={
        "strong": LLMParams(provider="openai", model="gpt-5"),
        "cheap": LLMParams(provider="openai", model="gpt-5-mini"),
    },
    policy=ModelPolicy(by_class={"projection": "cheap", "design": "strong"}, default="strong"),
)


def _profile_node(tmp_path: Path, **overrides) -> str:
    payload = {key: value for key, value in VALID_NODE.items() if key != "llm"}
    payload.update(overrides)
    return _write(tmp_path, payload)


def test_load_model_registry_ok_with_policy(tmp_path: Path) -> None:
    path = _write(tmp_path, {
        "profiles": {
            "strong": {"provider": "openai", "model": "gpt-5"},
            "cheap": {"provider": "openai", "model": "gpt-5-mini", "temperature": 0.2},
        },
        "policy": {"by_class": {"projection": "cheap"}, "default": "strong"},
    })
    result = load_model_registry(path)
    assert isinstance(result, Ok)
    assert result.value.profiles["cheap"].temperature == 0.2
    assert result.value.policy.by_class["projection"] == "cheap"


def test_load_model_registry_without_policy_is_valid(tmp_path: Path) -> None:
    path = _write(tmp_path, {"profiles": {"default": {"provider": "openai", "model": "m"}}})
    result = load_model_registry(path)
    assert isinstance(result, Ok)
    assert result.value.policy is None


def test_load_model_registry_invalid_profile(tmp_path: Path) -> None:
    path = _write(tmp_path, {"profiles": {"broken": {"provider": "openai"}}})  # нет model
    result = load_model_registry(path)
    assert isinstance(result, Err)
    assert result.code == CONFIG_INVALID
    assert "broken" in result.details


def test_load_model_registry_policy_ghost_profile(tmp_path: Path) -> None:
    path = _write(tmp_path, {
        "profiles": {"strong": {"provider": "openai", "model": "gpt-5"}},
        "policy": {"by_class": {"projection": "ghost"}},
    })
    result = load_model_registry(path)
    assert isinstance(result, Err)
    assert result.code == CONFIG_INVALID
    assert "ghost" in result.details


def test_load_model_registry_missing_profiles_key(tmp_path: Path) -> None:
    result = load_model_registry(_write(tmp_path, {"models": {}}))
    assert isinstance(result, Err)
    assert result.code == CONFIG_INVALID


def test_node_config_resolves_profile(tmp_path: Path) -> None:
    result = load_node_config(_profile_node(tmp_path, llm_profile="cheap"), REGISTRY)
    assert isinstance(result, Ok)
    assert result.value.llm == REGISTRY.profiles["cheap"]


def test_node_config_unknown_profile(tmp_path: Path) -> None:
    result = load_node_config(_profile_node(tmp_path, llm_profile="ghost"), REGISTRY)
    assert isinstance(result, Err)
    assert result.code == UNKNOWN_LLM_PROFILE
    assert result.details == "ghost"


def test_node_config_profile_without_registry(tmp_path: Path) -> None:
    result = load_node_config(_profile_node(tmp_path, llm_profile="cheap"), registry=None)
    assert isinstance(result, Err)
    assert result.code == CONFIG_INVALID
    assert "llm_profiles_path" in result.details


def test_node_config_resolves_consultant_profile(tmp_path: Path) -> None:
    result = load_node_config(
        _profile_node(tmp_path, llm_profile="cheap", consultant_profile="strong"), REGISTRY
    )
    assert isinstance(result, Ok)
    assert result.value.llm == REGISTRY.profiles["cheap"]
    assert result.value.consultant_llm == REGISTRY.profiles["strong"]


def test_node_config_unknown_consultant_profile(tmp_path: Path) -> None:
    result = load_node_config(
        _profile_node(tmp_path, llm_profile="cheap", consultant_profile="ghost"), REGISTRY
    )
    assert isinstance(result, Err)
    assert result.code == UNKNOWN_LLM_PROFILE
    assert result.details == "ghost"


def test_node_config_inline_llm_still_resolves_consultant(tmp_path: Path) -> None:
    payload = dict(VALID_NODE)
    payload["consultant_profile"] = "strong"
    result = load_node_config(_write(tmp_path, payload), REGISTRY)
    assert isinstance(result, Ok)
    assert result.value.consultant_llm == REGISTRY.profiles["strong"]


def test_node_config_both_llm_sources_invalid(tmp_path: Path) -> None:
    payload = dict(VALID_NODE)
    payload["llm_profile"] = "cheap"
    result = load_node_config(_write(tmp_path, payload), REGISTRY)
    assert isinstance(result, Err)
    assert result.code == CONFIG_INVALID


def test_node_config_no_llm_source_invalid(tmp_path: Path) -> None:
    result = load_node_config(_profile_node(tmp_path), REGISTRY)
    assert isinstance(result, Err)
    assert result.code == CONFIG_INVALID
    assert "нет источника модели" in result.details


# --- FR-16: резолюция по task_class ---

def test_task_class_resolves_via_policy(tmp_path: Path) -> None:
    result = load_node_config(_profile_node(tmp_path, task_class="projection"), REGISTRY)
    assert isinstance(result, Ok)
    assert result.value.llm == REGISTRY.profiles["cheap"]     # проекция → дешёвая


def test_task_class_falls_back_to_default(tmp_path: Path) -> None:
    result = load_node_config(_profile_node(tmp_path, task_class="review"), REGISTRY)
    assert isinstance(result, Ok)
    assert result.value.llm == REGISTRY.profiles["strong"]    # класс не в by_class → default


def test_task_class_without_policy_invalid(tmp_path: Path) -> None:
    registry = ModelRegistry(profiles=REGISTRY.profiles)      # без policy
    result = load_node_config(_profile_node(tmp_path, task_class="projection"), registry)
    assert isinstance(result, Err)
    assert result.code == CONFIG_INVALID
    assert "policy" in result.details


def test_task_class_uncovered_and_no_default_invalid(tmp_path: Path) -> None:
    registry = ModelRegistry(
        profiles=REGISTRY.profiles,
        policy=ModelPolicy(by_class={"projection": "cheap"}),  # default нет
    )
    result = load_node_config(_profile_node(tmp_path, task_class="review"), registry)
    assert isinstance(result, Err)
    assert result.code == CONFIG_INVALID


def test_inline_llm_beats_task_class(tmp_path: Path) -> None:
    payload = dict(VALID_NODE)
    payload["task_class"] = "projection"
    result = load_node_config(_write(tmp_path, payload), REGISTRY)
    assert isinstance(result, Ok)
    assert result.value.llm.model == "claude-sonnet-5"        # inline сильнее политики


def test_graph_duplicate_node_ids(tmp_path: Path) -> None:
    payload = {
        "nodes": [
            {"id": "same", "config_path": "a.json"},
            {"id": "same", "config_path": "b.json"},
        ],
        "edges": [],
    }
    result = load_graph_config(_write(tmp_path, payload))
    assert isinstance(result, Err)
    assert result.code == CONFIG_INVALID


def test_wiki_refs_and_wiki_refs_from_coexist(tmp_path):
    """FR-19/FR-21: статические и динамические wiki-ссылки сосуществуют (union)."""
    import json as _json
    from workshop.config_loader import load_node_config
    from workshop.result import Ok as _Ok

    config_path = tmp_path / "node.json"
    config_path.write_text(_json.dumps({
        "base_prompt_path": "base.md",
        "stage_map_path": "stage.md",
        "wiki_refs": [{"path": "wiki/python/pandas", "version": "v1"}],
        "wiki_refs_from": "tech_selection",
        "llm": {"provider": "fake", "model": "fake-1"},
    }), encoding="utf-8")
    result = load_node_config(str(config_path))
    assert isinstance(result, _Ok)
    assert result.value.wiki_refs_from == "tech_selection"
    assert len(result.value.wiki_refs) == 1
