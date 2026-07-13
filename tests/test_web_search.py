"""M-21 web_search: клиент Tavily (TSK-2101) и реестр инструментов (TSK-2102)."""
from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from workshop import web_search
from workshop.result import Err, Ok
from workshop.web_search import (
    SEARCH_KEY_MISSING,
    SEARCH_PROVIDER_ERROR,
    SEARCH_TIMEOUT,
    UNKNOWN_TOOL,
    FakeSearch,
    TavilySearch,
    build_tools,
)


def _http_response(status_code: int = 200, payload: object = None, text: str = ""):
    return SimpleNamespace(
        status_code=status_code,
        text=text,
        json=lambda: payload if payload is not None else (_ for _ in ()).throw(ValueError("no json")),
    )


# --- TSK-2101 TavilySearch ---

def test_tavily_formats_answer_and_results(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "answer": "pandas 3.0.3 — стабильная",
        "results": [
            {"title": "pandas · PyPI", "url": "https://pypi.org/project/pandas/", "content": "3.0.3"},
            {"title": "Release notes", "url": "https://pandas.pydata.org/", "content": "whatsnew"},
        ],
    }
    sent: list[dict] = []

    def fake_post(url, json, timeout):
        sent.append({"url": url, "json": json, "timeout": timeout})
        return _http_response(200, payload)

    monkeypatch.setattr(web_search.httpx, "post", fake_post)
    result = TavilySearch(api_key="tvly-test").search("pandas stable version", max_results=2)
    assert isinstance(result, Ok)
    assert result.value.splitlines()[0] == "Ответ провайдера: pandas 3.0.3 — стабильная"
    assert "1. pandas · PyPI" in result.value
    assert "https://pypi.org/project/pandas/" in result.value
    assert sent[0]["json"]["query"] == "pandas stable version"
    assert sent[0]["json"]["max_results"] == 2


def test_tavily_empty_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(web_search.httpx, "post", lambda *a, **k: _http_response(200, {"results": []}))
    result = TavilySearch(api_key="tvly-test").search("query")
    assert isinstance(result, Ok) and result.value == "Ничего не найдено."


def test_tavily_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    result = TavilySearch().search("query")
    assert isinstance(result, Err) and result.code == SEARCH_KEY_MISSING


def test_tavily_http_error_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        web_search.httpx, "post", lambda *a, **k: _http_response(432, text="quota exceeded")
    )
    result = TavilySearch(api_key="tvly-test").search("query")
    assert isinstance(result, Err) and result.code == SEARCH_PROVIDER_ERROR
    assert "432" in result.details


def test_tavily_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_timeout(*args, **kwargs):
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(web_search.httpx, "post", raise_timeout)
    result = TavilySearch(api_key="tvly-test").search("query")
    assert isinstance(result, Err) and result.code == SEARCH_TIMEOUT


def test_tavily_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(web_search.httpx, "post", lambda *a, **k: _http_response(200, None))
    result = TavilySearch(api_key="tvly-test").search("query")
    assert isinstance(result, Err) and result.code == SEARCH_PROVIDER_ERROR


# --- TSK-2102 build_tools ---

def test_build_tools_unknown_name() -> None:
    result = build_tools(["web_fetch"])
    assert isinstance(result, Err) and result.code == UNKNOWN_TOOL
    assert result.details == "web_fetch"


def test_build_tools_empty() -> None:
    result = build_tools([])
    assert isinstance(result, Ok) and result.value == []


def test_executor_returns_search_results() -> None:
    fake = FakeSearch([Ok("1. Title\n   url\n   snippet")])
    tools = build_tools(["web_search"], search=fake)
    assert isinstance(tools, Ok)
    output = tools.value[0].executor({"query": "pandas"})
    assert output == "1. Title\n   url\n   snippet"
    assert fake.queries == ["pandas"]


def test_executor_search_error_as_text_not_failure() -> None:
    fake = FakeSearch([Err(SEARCH_PROVIDER_ERROR, "HTTP 500")])
    tools = build_tools(["web_search"], search=fake)
    assert isinstance(tools, Ok)
    output = tools.value[0].executor({"query": "pandas"})
    assert output.startswith("ОШИБКА ПОИСКА")
    assert "HTTP 500" in output


def test_executor_empty_query_as_text() -> None:
    fake = FakeSearch([])
    tools = build_tools(["web_search"], search=fake)
    assert isinstance(tools, Ok)
    output = tools.value[0].executor({"query": "  "})
    assert output.startswith("ОШИБКА ИНСТРУМЕНТА")
    assert fake.queries == []  # до клиента не дошло


def test_executor_clamps_max_results() -> None:
    seen: list[int] = []

    class Recording:
        def search(self, query: str, max_results: int = 5):
            seen.append(max_results)
            return Ok("ок")

    tools = build_tools(["web_search"], search=Recording())
    assert isinstance(tools, Ok)
    executor = tools.value[0].executor
    executor({"query": "q", "max_results": 99})
    executor({"query": "q", "max_results": 0})
    executor({"query": "q", "max_results": "мусор"})
    assert seen == [10, 1, 5]
