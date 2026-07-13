"""M-09 orchestrator: e2e мини-граф с FakeLLM, циклы FAIL/REVISE/CLARIFICATION, FSM (TSK-0901/0902)."""
from __future__ import annotations

from pathlib import Path

from workshop.artifact_store import ArtifactStore
from workshop.hitl_cli import Accept, HITLDecision, Reject, Revise
from workshop.llm_client import FakeLLM, fake_ok
from workshop.models import Artifact, ArtifactRef, GraphConfig
from workshop.orchestrator import (
    INVALID_TRANSITION,
    MAX_ITERATIONS_EXCEEDED,
    REJECTED_BY_USER,
    RESUME_STALE_UPSTREAM,
    Event,
    NodeState,
    PipelineResult,
    run_pipeline,
    transition,
)
from workshop.result import Err, Ok, Result
from workshop.run_log import RunLog

INITIAL = "<request>проанализируй продажи</request>"


class FakeHITL:
    def __init__(self, decisions: list[HITLDecision] = (), answers: list[str] = ()) -> None:
        self._decisions = list(decisions)
        self._answers = list(answers)
        self.seen_reports: list[list[str]] = []

    def request_acceptance(self, artifact: Artifact, reports: list[str]) -> Result[HITLDecision]:
        self.seen_reports.append(reports)
        return Ok(self._decisions.pop(0))

    def ask_clarification(self, question: str) -> Result[str]:
        return Ok(self._answers.pop(0))


def _graph(*nodes: dict, edges: list[dict] = ()) -> GraphConfig:
    return GraphConfig.model_validate({"nodes": list(nodes), "edges": list(edges)})


def _run(graph, llm, hitl, tmp_path):
    return run_pipeline(
        graph, INITIAL, ArtifactStore(tmp_path / "store"), llm,
        RunLog(tmp_path / "log.jsonl"), hitl,
    )


# --- TSK-0902: чистая функция перехода ---

def test_transition_valid_pairs() -> None:
    assert transition(NodeState.PENDING, Event.START) == Ok(NodeState.RUNNING)
    assert transition(NodeState.REVIEW, Event.REVIEW_FAILED) == Ok(NodeState.RUNNING)
    assert transition(NodeState.HITL, Event.HITL_REJECTED) == Ok(NodeState.FAILED)


def test_transition_invalid_pair() -> None:
    result = transition(NodeState.PENDING, Event.HITL_ACCEPTED)
    assert isinstance(result, Err)
    assert result.code == INVALID_TRANSITION


# --- TSK-0901: пайплайн ---

def test_happy_path_two_nodes(make_config_file, tmp_path: Path) -> None:
    graph = _graph(
        {"id": "a", "config_path": make_config_file("a")},
        {"id": "b", "config_path": make_config_file("b"),
         "gates": {"review_config_path": make_config_file("rev", base_text="Проверь.\n{{INPUTS}}\n"),
                    "hitl": True}},
        edges=[{"from": "a", "to": "b"}],
    )
    llm = FakeLLM([
        fake_ok('```xml\n<a id="D-01"/>\n```'),
        fake_ok('```xml\n<b><covers>D-01</covers></b>\n```'),
        fake_ok("Гейт: PASS"),
    ])
    hitl = FakeHITL(decisions=[Accept()])

    result = _run(graph, llm, hitl, tmp_path)
    assert isinstance(result, Ok)
    assert result.value.accepted_artifacts == (ArtifactRef("a", 1), ArtifactRef("b", 1))

    store = ArtifactStore(tmp_path / "store")
    saved_b = store.load_artifact(ArtifactRef("b", 1))
    assert isinstance(saved_b, Ok)
    assert saved_b.value.derived_from == ArtifactRef("a", 1)   # трассировка derived_from
    assert isinstance(store.load_artifact(ArtifactRef("input", 1)), Ok)
    # HITL видел оба отчёта: кросс-ссылки и ревью
    assert len(hitl.seen_reports[0]) == 2


def test_review_fail_retries_with_findings(make_config_file, tmp_path: Path) -> None:
    graph = _graph(
        {"id": "b", "config_path": make_config_file("b"),
         "gates": {"review_config_path": make_config_file("rev", base_text="Проверь.\n{{INPUTS}}\n")}},
    )
    llm = FakeLLM([
        fake_ok("```xml\n<b1/>\n```"),
        fake_ok("🔴p3 [R1] scope: дефект → чинить\nГейт: FAIL"),
        fake_ok("```xml\n<b2/>\n```"),
        fake_ok("Гейт: PASS"),
    ])
    result = _run(graph, llm, FakeHITL(), tmp_path)
    assert isinstance(result, Ok)
    # вторая итерация мастерской (3-й вызов LLM) получила rework-контекст (TSK-0601):
    # черновик прошлой итерации дословно + находки F-NN с якорем-локацией
    rework_prompt = llm.prompts[2]
    assert "<previous_artifact>" in rework_prompt and "<b1/>" in rework_prompt
    assert '<finding id="F-01" weight="p3" rule="R1" anchor="scope">' in rework_prompt
    # повторный проход ревьюера (4-й вызов) видит прошлые находки (TSK-0701)
    rereview_prompt = llm.prompts[3]
    assert "<prior_findings>" in rereview_prompt
    assert "F-01 [R1] scope: дефект" in rereview_prompt
    # проверяемый артефакт второй итерации тоже в промпте ревьюера
    assert "<b2/>" in rereview_prompt


def test_clarification_flows_into_next_iteration(make_config_file, tmp_path: Path) -> None:
    graph = _graph({"id": "a", "config_path": make_config_file("a")})
    llm = FakeLLM([
        fake_ok("NEEDS_CLARIFICATION: какой разделитель в CSV?"),
        fake_ok("```xml\n<a/>\n```"),
    ])
    hitl = FakeHITL(answers=["точка с запятой"])
    result = _run(graph, llm, hitl, tmp_path)
    assert isinstance(result, Ok)
    assert "точка с запятой" in llm.prompts[1]


def test_hitl_revise_then_accept(make_config_file, tmp_path: Path) -> None:
    graph = _graph({"id": "a", "config_path": make_config_file("a"), "gates": {"hitl": True}})
    llm = FakeLLM([fake_ok("```xml\n<a1/>\n```"), fake_ok("```xml\n<a2/>\n```")])
    hitl = FakeHITL(decisions=[Revise(comments="добавь колонку даты"), Accept()])
    result = _run(graph, llm, hitl, tmp_path)
    assert isinstance(result, Ok)
    assert "добавь колонку даты" in llm.prompts[1]


def test_hitl_reject_stops_pipeline(make_config_file, tmp_path: Path) -> None:
    graph = _graph({"id": "a", "config_path": make_config_file("a"), "gates": {"hitl": True}})
    llm = FakeLLM([fake_ok("```xml\n<a/>\n```")])
    hitl = FakeHITL(decisions=[Reject(reason="не та постановка")])
    result = _run(graph, llm, hitl, tmp_path)
    assert isinstance(result, Err)
    assert result.code == REJECTED_BY_USER
    assert "a" in result.details


def test_max_iterations_exceeded(make_config_file, tmp_path: Path) -> None:
    graph = _graph(
        {"id": "b", "config_path": make_config_file("b"), "max_iterations": 2,
         "gates": {"review_config_path": make_config_file("rev", base_text="Проверь.\n{{INPUTS}}\n")}},
    )
    failing_review = fake_ok("🔴p3 [R1] scope: всё плохо → переделать\nГейт: FAIL")
    llm = FakeLLM([
        fake_ok("```xml\n<b/>\n```"), failing_review,
        fake_ok("```xml\n<b/>\n```"), failing_review,
    ])
    result = _run(graph, llm, FakeHITL(), tmp_path)
    assert isinstance(result, Err)
    assert result.code == MAX_ITERATIONS_EXCEEDED


def test_llm_profile_resolved_from_registry(make_config_file, tmp_path: Path) -> None:
    import json

    profiles_path = tmp_path / "models.json"
    profiles_path.write_text(
        json.dumps({"profiles": {"cheap": {"provider": "openai", "model": "gpt-5-mini"}}}),
        encoding="utf-8",
    )
    # узел без inline llm — только ссылка на профиль
    node_config_path = tmp_path / "prof_node.json"
    base = tmp_path / "prof_base.md"
    base.write_text("Задача.\n{{INPUTS}}\n", encoding="utf-8")
    stage = tmp_path / "prof_stage.md"
    stage.write_text("", encoding="utf-8")
    node_config_path.write_text(
        json.dumps({
            "base_prompt_path": str(base),
            "stage_map_path": str(stage),
            "llm_profile": "cheap",
        }),
        encoding="utf-8",
    )
    graph = GraphConfig.model_validate({
        "llm_profiles_path": str(profiles_path),
        "nodes": [{"id": "a", "config_path": str(node_config_path)}],
        "edges": [],
    })
    result = _run(graph, FakeLLM([fake_ok("```xml\n<a/>\n```")]), FakeHITL(), tmp_path)
    assert isinstance(result, Ok)
    # параметры из профиля дошли до вызова LLM и попали в журнал
    log_entry = json.loads(
        (tmp_path / "log.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert log_entry["params"]["model"] == "gpt-5-mini"


# --- TSK-0905: resume ---

def _seed_store(tmp_path: Path) -> ArtifactStore:
    """Стор с принятым префиксом: input v1 и a v1 (derived_from input@1)."""
    store = ArtifactStore(tmp_path / "store")
    input_ref = store.save_artifact("input", INITIAL)
    assert isinstance(input_ref, Ok)
    saved_a = store.save_artifact("a", "<a>из прошлого прогона</a>", derived_from=input_ref.value)
    assert isinstance(saved_a, Ok)
    return store


def test_resume_skips_accepted_prefix(make_config_file, tmp_path: Path) -> None:
    _seed_store(tmp_path)
    graph = _graph(
        {"id": "a", "config_path": make_config_file("a")},
        {"id": "b", "config_path": make_config_file("b")},
        edges=[{"from": "a", "to": "b"}],
    )
    llm = FakeLLM([fake_ok("```xml\n<b/>\n```")])   # ровно один ответ — только для b
    result = run_pipeline(
        graph, INITIAL, ArtifactStore(tmp_path / "store"), llm,
        RunLog(tmp_path / "log.jsonl"), FakeHITL(), resume=True,
    )
    assert isinstance(result, Ok)
    assert result.value.accepted_artifacts == (ArtifactRef("a", 1), ArtifactRef("b", 1))
    assert len(llm.prompts) == 1                      # a не перегенерировался
    assert "из прошлого прогона" in llm.prompts[0]    # b получил upstream из стора


def test_resume_reruns_everything_after_first_live_node(
    make_config_file, tmp_path: Path
) -> None:
    store = _seed_store(tmp_path)
    # у c есть старая версия, но b отсутствует → c обязан перегенерироваться (v2)
    saved_c = store.save_artifact("c", "<c старый/>")
    assert isinstance(saved_c, Ok)
    graph = _graph(
        {"id": "a", "config_path": make_config_file("a")},
        {"id": "b", "config_path": make_config_file("b")},
        {"id": "c", "config_path": make_config_file("c")},
        edges=[{"from": "a", "to": "b"}, {"from": "b", "to": "c"}],
    )
    llm = FakeLLM([fake_ok("```xml\n<b/>\n```"), fake_ok("```xml\n<c новый/>\n```")])
    result = run_pipeline(
        graph, INITIAL, ArtifactStore(tmp_path / "store"), llm,
        RunLog(tmp_path / "log.jsonl"), FakeHITL(), resume=True,
    )
    assert isinstance(result, Ok)
    assert result.value.accepted_artifacts == (
        ArtifactRef("a", 1), ArtifactRef("b", 1), ArtifactRef("c", 2),
    )
    assert len(llm.prompts) == 2


def test_resume_stale_upstream(make_config_file, tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "store")
    saved = store.save_artifact("a", "<a/>", derived_from=ArtifactRef("input", 99))
    assert isinstance(saved, Ok)
    graph = _graph({"id": "a", "config_path": make_config_file("a")})
    result = run_pipeline(
        graph, INITIAL, ArtifactStore(tmp_path / "store"), FakeLLM([]),
        RunLog(tmp_path / "log.jsonl"), FakeHITL(), resume=True,
    )
    assert isinstance(result, Err)
    assert result.code == RESUME_STALE_UPSTREAM
    assert result.details == "a"


def test_resume_fully_accepted_pipeline_makes_no_llm_calls(
    make_config_file, tmp_path: Path
) -> None:
    _seed_store(tmp_path)
    graph = _graph({"id": "a", "config_path": make_config_file("a")})
    llm = FakeLLM([])
    result = run_pipeline(
        graph, INITIAL, ArtifactStore(tmp_path / "store"), llm,
        RunLog(tmp_path / "log.jsonl"), FakeHITL(), resume=True,
    )
    assert isinstance(result, Ok)
    assert result.value.accepted_artifacts == (ArtifactRef("a", 1),)
    assert llm.prompts == []


FILES_RESPONSE = (
    "```file:stats.py\ndef mean(xs): return sum(xs) / len(xs)\n```\n"
    "```file:test_stats.py\nfrom stats import mean\n\ndef test_mean(): assert mean([2, 4]) == 3\n```\n"
)


class OkSandbox:
    """Песочница-заглушка: тесты всегда проходят; запоминает вызовы."""

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def __call__(self, image, files, command, limits):
        from workshop.sandbox import ExecReport

        self.calls.append(files)
        return Ok(ExecReport(exit_code=0, stdout="2 passed", stderr="", duration_s=0.1))


def test_codegen_node_revise_then_accept(make_config_file, tmp_path: Path) -> None:
    graph = _graph({
        "id": "executor",
        "config_path": make_config_file("gen"),
        "kind": "codegen",
        "image": "python:3.14-slim",
        "gates": {"hitl": True},
    })
    llm = FakeLLM([fake_ok(FILES_RESPONSE), fake_ok(FILES_RESPONSE)])
    hitl = FakeHITL(decisions=[Revise(comments="добавь медиану"), Accept()])
    sandbox = OkSandbox()

    result = run_pipeline(
        graph, INITIAL, ArtifactStore(tmp_path / "store"), llm,
        RunLog(tmp_path / "log.jsonl"), hitl, sandbox=sandbox,
    )
    assert isinstance(result, Ok)
    # REVISE codegen-узла: правки + прошлый file map (TSK-0901)
    assert "добавь медиану" in llm.prompts[1] and "<user_comments>" in llm.prompts[1]
    assert "<previous_artifact>" in llm.prompts[1] and "```file:stats.py" in llm.prompts[1]
    assert "exit=0" in hitl.seen_reports[0][0]          # HITL видел отчёт тестов

    saved = ArtifactStore(tmp_path / "store").load_artifact(ArtifactRef("executor", 1))
    assert isinstance(saved, Ok)
    assert "```file:stats.py" in saved.value.content    # артефакт = сериализованный file map


VERDICT_NOT_READY = fake_ok(
    "```xml\n<verdict><coverage><fr id=\"FR-03\" status=\"missing\"/></coverage>"
    "<decision>NOT_READY</decision><reasons>FR-03: нет модуля топ-3</reasons></verdict>\n```"
)
VERDICT_READY = fake_ok(
    "```xml\n<verdict><coverage/><decision>READY</decision><reasons></reasons></verdict>\n```"
)


def _codegen_judged_graph(make_config_file, hitl: bool = False, max_iterations: int = 3):
    return _graph({
        "id": "executor",
        "config_path": make_config_file("gen"),
        "kind": "codegen",
        "image": "python:3.14-slim",
        "max_iterations": max_iterations,
        "gates": {
            "judge_config_path": make_config_file("judge", base_text="Суди.\n{{INPUTS}}\n"),
            "hitl": hitl,
        },
    })


def test_judge_gate_autocycle_not_ready_then_ready(make_config_file, tmp_path: Path) -> None:
    graph = _codegen_judged_graph(make_config_file)
    llm = FakeLLM([
        fake_ok(FILES_RESPONSE), VERDICT_NOT_READY,     # итерация 1: код + NOT_READY
        fake_ok(FILES_RESPONSE), VERDICT_READY,         # итерация 2: доработка + READY
    ])
    result = run_pipeline(
        graph, INITIAL, ArtifactStore(tmp_path / "store"), llm,
        RunLog(tmp_path / "log.jsonl"), FakeHITL(), sandbox=OkSandbox(),
    )
    assert isinstance(result, Ok)
    # вторая генерация получила rework-контекст: прошлый file map + полный вердикт
    assert "<previous_artifact>" in llm.prompts[2]
    assert "```file:stats.py" in llm.prompts[2]
    assert "<judge_verdict>" in llm.prompts[2]
    assert "NOT_READY" in llm.prompts[2]
    assert "FR-03" in llm.prompts[2]
    # judge видел ТЗ и код вместе
    assert "```file:stats.py" in llm.prompts[1]
    assert INITIAL in llm.prompts[1]

    store = ArtifactStore(tmp_path / "store")
    assert isinstance(store.load_artifact(ArtifactRef("executor", 1)), Ok)
    verdict = store.load_artifact(ArtifactRef("executor_verdict", 1))
    assert isinstance(verdict, Ok)
    assert "READY" in verdict.value.content
    assert verdict.value.derived_from == ArtifactRef("executor", 1)


def test_judge_gate_reports_to_hitl(make_config_file, tmp_path: Path) -> None:
    graph = _codegen_judged_graph(make_config_file, hitl=True)
    llm = FakeLLM([fake_ok(FILES_RESPONSE), VERDICT_READY])
    hitl = FakeHITL(decisions=[Accept()])
    result = run_pipeline(
        graph, INITIAL, ArtifactStore(tmp_path / "store"), llm,
        RunLog(tmp_path / "log.jsonl"), hitl, sandbox=OkSandbox(),
    )
    assert isinstance(result, Ok)
    assert any("Judge: READY" in report for report in hitl.seen_reports[0])


def test_judge_gate_always_not_ready_hits_max_iterations(
    make_config_file, tmp_path: Path
) -> None:
    graph = _codegen_judged_graph(make_config_file, max_iterations=2)
    llm = FakeLLM([
        fake_ok(FILES_RESPONSE), VERDICT_NOT_READY,
        fake_ok(FILES_RESPONSE), VERDICT_NOT_READY,
    ])
    result = run_pipeline(
        graph, INITIAL, ArtifactStore(tmp_path / "store"), llm,
        RunLog(tmp_path / "log.jsonl"), FakeHITL(), sandbox=OkSandbox(),
    )
    assert isinstance(result, Err)
    assert result.code == MAX_ITERATIONS_EXCEEDED


def test_judge_gate_unparseable_verdict_fails_node(make_config_file, tmp_path: Path) -> None:
    graph = _codegen_judged_graph(make_config_file)
    llm = FakeLLM([fake_ok(FILES_RESPONSE), fake_ok("```xml\n<verdict>мутно</verdict>\n```")])
    result = run_pipeline(
        graph, INITIAL, ArtifactStore(tmp_path / "store"), llm,
        RunLog(tmp_path / "log.jsonl"), FakeHITL(), sandbox=OkSandbox(),
    )
    assert isinstance(result, Err)
    assert result.code == "NODE_FAILED"
    assert "VERDICT_UNPARSEABLE" in result.details


def test_judge_gate_forbidden_on_workshop_node() -> None:
    import pytest

    with pytest.raises(Exception):
        _graph({
            "id": "a", "config_path": "a.json",
            "gates": {"judge_config_path": "judge.json"},
        })


def test_codegen_node_requires_image() -> None:
    import pytest

    with pytest.raises(Exception):
        _graph({"id": "x", "config_path": "x.json", "kind": "codegen"})


def test_codegen_node_forbids_review_gate() -> None:
    import pytest

    with pytest.raises(Exception):
        _graph({
            "id": "x", "config_path": "x.json", "kind": "codegen",
            "image": "python:3.14-slim",
            "gates": {"review_config_path": "rev.json"},
        })


def test_gateless_pipeline_result_shape(make_config_file, tmp_path: Path) -> None:
    graph = _graph({"id": "a", "config_path": make_config_file("a")})
    result = _run(graph, FakeLLM([fake_ok("```xml\n<a/>\n```")]), FakeHITL(), tmp_path)
    assert isinstance(result, Ok)
    assert isinstance(result.value, PipelineResult)
    assert result.value.log_path.endswith("log.jsonl")


# --- FR-19: динамические wiki-ссылки из артефакта tech_stack ---

def _seed_wiki(tmp_path: Path) -> None:
    pandas_dir = tmp_path / "wiki" / "python" / "pandas"
    pandas_dir.mkdir(parents=True)
    (pandas_dir / "index.md").write_text("pandas: используй read_csv", encoding="utf-8")


def test_wiki_refs_from_injects_selected_tech_pages(
    make_config_file, tmp_path: Path, monkeypatch
) -> None:
    _seed_wiki(tmp_path)
    monkeypatch.chdir(tmp_path)  # build_node_prompt читает wiki относительно CWD
    graph = _graph(
        {"id": "stack", "config_path": make_config_file("stack")},
        {"id": "exec",
         "config_path": make_config_file("exec", wiki_refs_from="stack")},
        edges=[{"from": "stack", "to": "exec"}],
    )
    llm = FakeLLM([
        fake_ok('```xml\n<tech_stack><tech ref="python/pandas"><why>CSV</why></tech></tech_stack>\n```'),
        fake_ok("```xml\n<code/>\n```"),
    ])
    result = _run(graph, llm, FakeHITL(), tmp_path)
    assert isinstance(result, Ok)
    exec_prompt = llm.prompts[1]
    assert "=== wiki: wiki/python/pandas/index.md ===" in exec_prompt
    assert "pandas: используй read_csv" in exec_prompt


def test_wiki_refs_from_artifact_missing_fails_node(
    make_config_file, tmp_path: Path
) -> None:
    graph = _graph(
        {"id": "exec", "config_path": make_config_file("exec", wiki_refs_from="stack")},
    )
    result = _run(graph, FakeLLM([]), FakeHITL(), tmp_path)
    assert isinstance(result, Err)
    assert result.code == "NODE_FAILED"
    assert "stack не найден" in result.details


def test_wiki_refs_from_unparseable_stack_fails_node(
    make_config_file, tmp_path: Path
) -> None:
    graph = _graph(
        {"id": "stack", "config_path": make_config_file("stack")},
        {"id": "exec", "config_path": make_config_file("exec", wiki_refs_from="stack")},
        edges=[{"from": "stack", "to": "exec"}],
    )
    llm = FakeLLM([fake_ok("```xml\n<tech_stack>без tech ref</tech_stack>\n```")])
    result = _run(graph, llm, FakeHITL(), tmp_path)
    assert isinstance(result, Err)
    assert result.code == "NODE_FAILED"
    assert "WIKI_REFS_SOURCE_UNPARSEABLE" in result.details


def test_hitl_revise_carries_previous_artifact(make_config_file, tmp_path: Path) -> None:
    """REVISE: правки пользователя приходят вместе с черновиком (TSK-0601)."""
    graph = _graph(
        {"id": "a", "config_path": make_config_file("a"), "gates": {"hitl": True}},
    )
    llm = FakeLLM([
        fake_ok("```xml\n<a1/>\n```"),
        fake_ok("```xml\n<a2/>\n```"),
    ])
    hitl = FakeHITL(decisions=[Revise(comments="уточни период"), Accept()])
    result = _run(graph, llm, hitl, tmp_path)
    assert isinstance(result, Ok)
    revise_prompt = llm.prompts[1]
    assert "<previous_artifact>" in revise_prompt and "<a1/>" in revise_prompt
    assert "<user_comments>" in revise_prompt and "уточни период" in revise_prompt
