"""M-22 material: инжест, чанкование, ретривер, инструменты, обвязка пайплайна (TSK-2201..2203)."""
from __future__ import annotations

from pathlib import Path

from workshop.artifact_store import ArtifactStore
from workshop.hitl_cli import HITLDecision
from workshop.llm_client import FakeLLM, fake_ok
from workshop.material import (
    EMBEDDINGS_UNAVAILABLE,
    MATERIAL_EMPTY,
    MATERIAL_FETCH_FAILED,
    WIKI_STORE_EMPTY,
    FakeFetcher,
    LexicalRetriever,
    MaterialStore,
    RemoteBGEM3Retriever,
    build_material_tools,
    build_wiki_tools,
    default_retriever,
    ingest,
    load_wiki_store,
)
from workshop.models import Artifact, ArtifactRef, GraphConfig, NodeConfig
from workshop.orchestrator import run_pipeline
from workshop.result import Err, Ok, Result
from workshop.run_log import RunLog
from workshop.workshop_node import MATERIAL_NOT_CONFIGURED, _build_node_tools


# --- TSK-2201: ingest ---

def test_ingest_empty_input() -> None:
    result = ingest("   \n  ")
    assert isinstance(result, Err)
    assert result.code == MATERIAL_EMPTY


def test_ingest_inline_single_chunk() -> None:
    result = ingest("Обсуждение: берём httpx для клиента.")
    assert isinstance(result, Ok)
    chunks = result.value.chunks
    assert len(chunks) == 1
    assert chunks[0].id == "d1:01"
    assert chunks[0].source == "inline"


def test_ingest_splits_by_headings_and_packs() -> None:
    text = "# Тема А\n" + "а" * 3000 + "\n# Тема Б\n" + "б" * 3000
    result = ingest(text, chunk_chars=4000)
    assert isinstance(result, Ok)
    chunks = result.value.chunks
    # два блока по ~3к не влезают в один чанк 4к → по чанку на заголовок
    assert len(chunks) == 2
    assert chunks[0].title == "Тема А"
    assert chunks[1].title == "Тема Б"


def test_ingest_hard_splits_oversized_block() -> None:
    result = ingest("х" * 9000, chunk_chars=4000, chunk_overlap=0)
    assert isinstance(result, Ok)
    sizes = [len(chunk.text) for chunk in result.value.chunks]
    assert sizes == [4000, 4000, 1000]


def test_hard_split_overlap_keeps_boundary_text() -> None:
    result = ingest("х" * 9000, chunk_chars=4000, chunk_overlap=400)
    assert isinstance(result, Ok)
    chunks = result.value.chunks
    # шаг 3600: [0:4000], [3600:7600], [7200:9000] — границы перекрыты
    assert [len(chunk.text) for chunk in chunks] == [4000, 4000, 1800]


def test_ingest_fetches_url_lines() -> None:
    fetcher = FakeFetcher({"https://example.com/doc": Ok("# Внешний док\nтело")})
    result = ingest("контекст чата\nhttps://example.com/doc\n", fetcher=fetcher)
    assert isinstance(result, Ok)
    sources = {chunk.source for chunk in result.value.chunks}
    assert sources == {"inline", "https://example.com/doc"}
    assert fetcher.fetched == ["https://example.com/doc"]


def test_ingest_fetch_failure_is_explicit() -> None:
    fetcher = FakeFetcher({})
    result = ingest("https://example.com/missing", fetcher=fetcher)
    assert isinstance(result, Err)
    assert result.code == MATERIAL_FETCH_FAILED


def test_toc_lists_every_chunk() -> None:
    result = ingest("# Тема А\nтекст\n# Тема Б\nещё", chunk_chars=10)
    assert isinstance(result, Ok)
    toc = result.value.toc()
    for chunk in result.value.chunks:
        assert chunk.id in toc


# --- TSK-2202: ретривер и инструменты ---

def _store() -> MaterialStore:
    result = ingest(
        "# Оплата\nстрайп подписка вебхук\n# Поиск\nиндекс эластик запрос",
        chunk_chars=40,
    )
    assert isinstance(result, Ok)
    return result.value


def test_retriever_ranks_and_drops_zero_scores() -> None:
    store = _store()
    found = LexicalRetriever(store).retrieve("страйп вебхук", k=5)
    assert isinstance(found, Ok)
    assert [chunk.title for chunk in found.value] == ["Оплата"]


def test_retriever_deterministic_tie_break() -> None:
    store = _store()
    first = LexicalRetriever(store).retrieve("запрос индекс", k=5)
    second = LexicalRetriever(store).retrieve("запрос индекс", k=5)
    assert isinstance(first, Ok) and isinstance(second, Ok)
    assert [c.id for c in first.value] == [c.id for c in second.value]


def test_search_tool_executor_contract() -> None:
    tools = build_material_tools(_store())
    search = next(spec for spec in tools if spec.name == "material_search")
    assert "ОШИБКА ИНСТРУМЕНТА" in search.executor({"query": "  "})
    assert "Ничего не найдено" in search.executor({"query": "qqqqqq"})
    assert "Оплата" in search.executor({"query": "вебхук страйп"})


def test_get_tool_executor_contract() -> None:
    store = _store()
    tools = build_material_tools(store)
    get = next(spec for spec in tools if spec.name == "material_get")
    first_id = store.chunks[0].id
    assert store.chunks[0].text in get.executor({"chunk_id": first_id})
    assert "неизвестный chunk_id" in get.executor({"chunk_id": "d9:99"})


# --- TSK-2207: скобки в материале ---

def test_toc_sanitizes_double_braces() -> None:
    result = ingest("{{question}} и {{context}} — шаблон промпта")
    assert isinstance(result, Ok)
    toc = result.value.toc()
    assert "{{" not in toc and "}}" not in toc
    # полный текст чанка через material_get — дословный (идёт мимо шаблона)
    assert "{{question}}" in result.value.chunks[0].text


def test_inline_limit_zero_means_always_toc(make_config_file, tmp_path: Path) -> None:
    graph = GraphConfig.model_validate(
        {
            "nodes": [{"id": "spec", "config_path": make_config_file("spec")}],
            "material": {"inline_limit_chars": 0},
        }
    )
    llm = FakeLLM([fake_ok("```xml\n<spec/>\n```")])
    result = run_pipeline(
        graph, "короткий материал с {{braces}}", ArtifactStore(tmp_path / "store"), llm,
        RunLog(tmp_path / "log.jsonl"), AcceptAllHITL(),
    )
    assert isinstance(result, Ok)
    assert "Оглавление материала" in llm.prompts[0]
    assert "{{braces}}" not in llm.prompts[0]


# --- TSK-2204: retry-подсказка и валидатор overlap ---

def test_search_tools_carry_retry_hint() -> None:
    tools = build_material_tools(_store())
    search = next(spec for spec in tools if spec.name == "material_search")
    assert "переформулируй запрос" in search.description
    assert "3 неудачных попыток" in search.description


def test_material_config_rejects_overlap_not_below_chunk() -> None:
    from pydantic import ValidationError

    import pytest

    from workshop.models import MaterialConfig

    with pytest.raises(ValidationError):
        MaterialConfig(chunk_chars=1000, chunk_overlap=1000)


# --- TSK-2205: wiki-стор и инструменты ---

def _wiki_root(tmp_path: Path) -> Path:
    root = tmp_path / "wiki"
    (root / "python").mkdir(parents=True)
    (root / "index.md").write_text("# wiki: карта (v1)\nобласти", encoding="utf-8")
    (root / "python" / "httpx.md").write_text(
        "# wiki: httpx (v1)\nHTTP-клиент, вебхуки, таймауты", encoding="utf-8"
    )
    return root


def test_load_wiki_store_pages_and_chunk_ids(tmp_path: Path) -> None:
    result = load_wiki_store(_wiki_root(tmp_path))
    assert isinstance(result, Ok)
    store, pages = result.value
    assert set(pages) == {"index.md", "python/httpx.md"}
    assert {chunk.id for chunk in store.chunks} == {"index.md:01", "python/httpx.md:01"}


def test_load_wiki_store_missing_root(tmp_path: Path) -> None:
    result = load_wiki_store(tmp_path / "нет")
    assert isinstance(result, Err)
    assert result.code == WIKI_STORE_EMPTY


def test_wiki_tools_search_and_get(tmp_path: Path) -> None:
    store, pages = load_wiki_store(_wiki_root(tmp_path)).value
    tools = {spec.name: spec for spec in build_wiki_tools(store, pages)}
    assert "httpx.md" in tools["wiki_search"].executor({"query": "вебхуки таймауты"})
    assert "HTTP-клиент" in tools["wiki_get"].executor({"path": "python/httpx.md"})
    assert "ОШИБКА ИНСТРУМЕНТА" in tools["wiki_get"].executor({"path": "нет.md"})


# --- TSK-2206: векторный ретривер ---

class FakeEncodeClient:
    """Скриптованный энкодер: вектор по словарю подстрок, запоминает вызовы."""

    def __init__(self, axis_terms: list[str], fail: str | None = None) -> None:
        self._axis_terms = axis_terms
        self._fail = fail
        self.calls: list[list[str]] = []

    def encode(self, texts: list[str]) -> Result[list[list[float]]]:
        self.calls.append(list(texts))
        if self._fail is not None:
            return Err(EMBEDDINGS_UNAVAILABLE, self._fail)
        return Ok([
            [float(term in text) for term in self._axis_terms]
            for text in texts
        ])


def test_bge_retriever_ranks_by_cosine_and_caches_chunks() -> None:
    store = _store()
    client = FakeEncodeClient(axis_terms=["страйп", "эластик"])
    retriever = RemoteBGEM3Retriever(store, client)
    first = retriever.retrieve("страйп", k=1)
    assert isinstance(first, Ok)
    assert first.value[0].title == "Оплата"
    second = retriever.retrieve("эластик", k=1)
    assert isinstance(second, Ok)
    assert second.value[0].title == "Поиск"
    # чанки закодированы один раз: [чанки], [запрос1], [запрос2]
    assert len(client.calls) == 3


def test_bge_retriever_failure_is_tool_text_not_crash() -> None:
    store = _store()
    retriever = RemoteBGEM3Retriever(store, FakeEncodeClient([], fail="сервис недоступен"))
    tools = build_material_tools(store, retriever=retriever)
    search = next(spec for spec in tools if spec.name == "material_search")
    answer = search.executor({"query": "страйп"})
    assert "ОШИБКА ИНСТРУМЕНТА" in answer and EMBEDDINGS_UNAVAILABLE in answer


def test_default_retriever_switches_on_env(monkeypatch) -> None:
    store = _store()
    monkeypatch.delenv("BGE_M3_SERVICE_URL", raising=False)
    assert isinstance(default_retriever(store), LexicalRetriever)
    monkeypatch.setenv("BGE_M3_SERVICE_URL", "http://bge-m3-service:8090")
    assert isinstance(default_retriever(store), RemoteBGEM3Retriever)


# --- TSK-2203: сборка инструментов узла ---

def _node_config(tools: list[str]) -> NodeConfig:
    return NodeConfig(
        base_prompt_path="unused.md",
        stage_map_path="unused.md",
        tools=tools,
        llm={"provider": "fake", "model": "fake-1"},
    )


def test_material_tools_require_store() -> None:
    result = _build_node_tools(_node_config(["material_search"]), material=None)
    assert isinstance(result, Err)
    assert result.code == MATERIAL_NOT_CONFIGURED


def test_material_and_web_tools_compose() -> None:
    result = _build_node_tools(
        _node_config(["web_search", "material_search", "material_get"]),
        material=_store(),
    )
    assert isinstance(result, Ok)
    assert [spec.name for spec in result.value] == [
        "web_search", "material_search", "material_get",
    ]


def test_wiki_tools_require_tree_root() -> None:
    from workshop.workshop_node import WIKI_TOOLS_NEED_TREE_ROOT

    result = _build_node_tools(_node_config(["wiki_search"]), material=None)
    assert isinstance(result, Err)
    assert result.code == WIKI_TOOLS_NEED_TREE_ROOT


def test_wiki_tools_built_from_tree_root(tmp_path: Path) -> None:
    root = _wiki_root(tmp_path)
    config = _node_config(["wiki_search", "wiki_get"]).model_copy(
        update={"wiki_tree_root": str(root)}
    )
    result = _build_node_tools(config, material=None)
    assert isinstance(result, Ok)
    assert [spec.name for spec in result.value] == ["wiki_search", "wiki_get"]


# --- TSK-2203: обвязка пайплайна ---

class AcceptAllHITL:
    def request_acceptance(self, artifact: Artifact, reports: list[str]) -> Result[HITLDecision]:
        raise AssertionError("hitl не ожидается в этом тесте")

    def ask_clarification(self, question: str) -> Result[str]:
        raise AssertionError("clarification не ожидается в этом тесте")


def _material_graph(make_config_file, inline_limit: int) -> GraphConfig:
    return GraphConfig.model_validate(
        {
            "nodes": [{"id": "spec", "config_path": make_config_file("spec")}],
            "material": {"chunk_chars": 1000, "inline_limit_chars": inline_limit},
        }
    )


def test_pipeline_big_material_becomes_toc(make_config_file, tmp_path: Path) -> None:
    graph = _material_graph(make_config_file, inline_limit=1000)
    llm = FakeLLM([fake_ok("```xml\n<spec/>\n```")])
    big_input = "# Тема\n" + "переговоры о продукте " * 300
    result = run_pipeline(
        graph, big_input, ArtifactStore(tmp_path / "store"), llm,
        RunLog(tmp_path / "log.jsonl"), AcceptAllHITL(),
    )
    assert isinstance(result, Ok)
    assert "Оглавление материала" in llm.prompts[0]
    assert "переговоры о продукте " * 300 not in llm.prompts[0]
    # артефакт input в сторе — сырой материал (воспроизводимость)
    store = ArtifactStore(tmp_path / "store")
    saved = store.load_artifact(ArtifactRef(name="input", version=1))
    assert isinstance(saved, Ok)
    assert saved.value.content == big_input


def test_pipeline_small_material_stays_inline(make_config_file, tmp_path: Path) -> None:
    graph = _material_graph(make_config_file, inline_limit=10_000)
    llm = FakeLLM([fake_ok("```xml\n<spec/>\n```")])
    result = run_pipeline(
        graph, "короткая выгрузка чата", ArtifactStore(tmp_path / "store"), llm,
        RunLog(tmp_path / "log.jsonl"), AcceptAllHITL(),
    )
    assert isinstance(result, Ok)
    assert "короткая выгрузка чата" in llm.prompts[0]
    assert "Оглавление материала" not in llm.prompts[0]
