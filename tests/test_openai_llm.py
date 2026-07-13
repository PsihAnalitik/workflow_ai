"""M-04 OpenAILLM: контрактные тесты адаптера на стабе SDK (без сети)."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Callable

import httpx
import pytest
from openai import APITimeoutError, OpenAIError

from workshop.llm_client import PROVIDER_ERROR, TIMEOUT
from workshop.models import LLMParams
from workshop.openai_llm import OpenAILLM
from workshop.result import Err, Ok

PARAMS = LLMParams(provider="openai", model="gpt-5", temperature=0.0, seed=42)


def _adapter_with_stub(create_fn: Callable) -> tuple[OpenAILLM, list[dict]]:
    """Адаптер с подменённым SDK-клиентом; возвращает и журнал kwargs вызовов."""
    calls: list[dict] = []

    def recording_create(**kwargs):
        calls.append(kwargs)
        return create_fn(**kwargs)

    adapter = OpenAILLM(api_key="test-key")
    adapter._client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=recording_create))
    )
    return adapter, calls


def _response(text: str | None):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )


def test_success_maps_text_and_usage() -> None:
    adapter, calls = _adapter_with_stub(lambda **_: _response("<domains/>"))
    result = adapter.complete("собранный промпт", PARAMS)
    assert isinstance(result, Ok)
    assert result.value.text == "<domains/>"
    assert result.value.usage == {"prompt_tokens": 10, "completion_tokens": 5}
    assert calls[0]["messages"] == [{"role": "user", "content": "собранный промпт"}]
    assert calls[0]["model"] == "gpt-5"
    assert calls[0]["seed"] == 42


def test_seed_none_is_not_sent() -> None:
    adapter, calls = _adapter_with_stub(lambda **_: _response("ok"))
    params = LLMParams(provider="openai", model="gpt-5", seed=None)
    assert isinstance(adapter.complete("p", params), Ok)
    assert "seed" not in calls[0]


def test_wrong_provider_refused() -> None:
    adapter, _calls = _adapter_with_stub(lambda **_: _response("ok"))
    params = LLMParams(provider="anthropic", model="claude-sonnet-5")
    result = adapter.complete("p", params)
    assert isinstance(result, Err)
    assert result.code == PROVIDER_ERROR
    assert "anthropic" in result.details


def test_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = OpenAILLM().complete("p", PARAMS)
    assert isinstance(result, Err)
    assert result.code == PROVIDER_ERROR
    assert "OPENAI_API_KEY" in result.details


def test_timeout_mapped() -> None:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")

    def raise_timeout(**_):
        raise APITimeoutError(request=request)

    adapter, _calls = _adapter_with_stub(raise_timeout)
    result = adapter.complete("p", PARAMS)
    assert isinstance(result, Err)
    assert result.code == TIMEOUT


def test_api_error_mapped() -> None:
    def raise_api_error(**_):
        raise OpenAIError("insufficient_quota")

    adapter, _calls = _adapter_with_stub(raise_api_error)
    result = adapter.complete("p", PARAMS)
    assert isinstance(result, Err)
    assert result.code == PROVIDER_ERROR
    assert "insufficient_quota" in result.details


def test_empty_content_is_provider_error() -> None:
    adapter, _calls = _adapter_with_stub(lambda **_: _response(None))
    result = adapter.complete("p", PARAMS)
    assert isinstance(result, Err)
    assert result.code == PROVIDER_ERROR


def test_base_url_from_argument() -> None:
    adapter = OpenAILLM(api_key="k", base_url="http://localhost:8000/v1")
    assert str(adapter._ensure_client().base_url).rstrip("/") == "http://localhost:8000/v1"


def test_base_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.corp/v1")
    adapter = OpenAILLM(api_key="k")
    assert str(adapter._ensure_client().base_url).rstrip("/") == "https://proxy.corp/v1"


def test_empty_env_base_url_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", "")
    adapter = OpenAILLM(api_key="k")
    assert "api.openai.com" in str(adapter._ensure_client().base_url)


def test_no_choices_is_provider_error() -> None:
    adapter, _calls = _adapter_with_stub(
        lambda **_: SimpleNamespace(choices=[], usage=None)
    )
    result = adapter.complete("p", PARAMS)
    assert isinstance(result, Err)
    assert result.code == PROVIDER_ERROR


# --- TSK-0402 tool-calling цикл ---

def _tool_call(call_id: str, name: str, arguments: str):
    return SimpleNamespace(
        id=call_id, function=SimpleNamespace(name=name, arguments=arguments)
    )


def _tool_response(*calls):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=None, tool_calls=list(calls)))],
        usage=SimpleNamespace(prompt_tokens=7, completion_tokens=3),
    )


def _search_spec(executor):
    from workshop.llm_client import ToolSpec

    return ToolSpec(
        name="web_search",
        description="поиск",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}},
        executor=executor,
    )


def test_no_tools_keeps_request_shape() -> None:
    adapter, calls = _adapter_with_stub(lambda **_: _response("ok"))
    assert isinstance(adapter.complete("p", PARAMS), Ok)
    assert "tools" not in calls[0]


def test_tool_loop_executes_and_returns_final() -> None:
    responses = [
        _tool_response(_tool_call("c1", "web_search", '{"query": "pandas"}')),
        _response("итог: pandas 3.0.3"),
    ]
    adapter, calls = _adapter_with_stub(lambda **_: responses.pop(0))
    seen_args: list[dict] = []

    def executor(args: dict) -> str:
        seen_args.append(args)
        return "1. pandas · PyPI"

    result = adapter.complete("вопрос", PARAMS, tools=[_search_spec(executor)])
    assert isinstance(result, Ok)
    assert result.value.text == "итог: pandas 3.0.3"
    assert seen_args == [{"query": "pandas"}]
    assert result.value.tool_trace == ('web_search({"query": "pandas"}) → 1. pandas · PyPI',)
    # usage суммируется по раундам: 7+10 / 3+5
    assert result.value.usage == {"prompt_tokens": 17, "completion_tokens": 8}
    # второй запрос содержит инструментальный диалог
    assert calls[0]["tools"][0]["function"]["name"] == "web_search"
    roles = [m["role"] for m in calls[1]["messages"]]
    assert roles == ["user", "assistant", "tool"]
    assert calls[1]["messages"][2]["content"] == "1. pandas · PyPI"


def test_exhausted_rounds_force_final_answer_without_tools() -> None:
    from workshop.openai_llm import MAX_TOOL_ROUNDS

    responses = [
        _tool_response(_tool_call(f"c{i}", "web_search", '{"query": "x"}'))
        for i in range(MAX_TOOL_ROUNDS)
    ] + [_response("итог из накопленного")]
    adapter, calls = _adapter_with_stub(lambda **_: responses.pop(0))
    result = adapter.complete("p", PARAMS, tools=[_search_spec(lambda args: "r")])
    assert isinstance(result, Ok)
    assert result.value.text == "итог из накопленного"
    assert len(result.value.tool_trace) == MAX_TOOL_ROUNDS
    # принудительный финал: tools остаются, вызовы запрещены + явная инструкция
    assert "tool_choice" not in calls[MAX_TOOL_ROUNDS - 1]
    final_call = calls[MAX_TOOL_ROUNDS]
    assert "tools" in final_call
    assert final_call["tool_choice"] == "none"
    assert final_call["messages"][-1]["role"] == "user"
    assert "финальный ответ" in final_call["messages"][-1]["content"]


def test_tool_loop_exceeded_when_final_still_calls_tools() -> None:
    from workshop.llm_client import TOOL_LOOP_EXCEEDED
    from workshop.openai_llm import MAX_TOOL_ROUNDS

    adapter, calls = _adapter_with_stub(
        lambda **_: _tool_response(_tool_call("c", "web_search", '{"query": "x"}'))
    )
    result = adapter.complete("p", PARAMS, tools=[_search_spec(lambda args: "r")])
    assert isinstance(result, Err)
    assert result.code == TOOL_LOOP_EXCEEDED
    assert 'web_search({"query": "x"})' in result.details  # трейс для диагностики
    assert len(calls) == MAX_TOOL_ROUNDS + 1


def test_tool_bad_args_and_unknown_name_reported_to_model() -> None:
    responses = [
        _tool_response(
            _tool_call("c1", "web_search", "не-json"),
            _tool_call("c2", "unknown_tool", "{}"),
        ),
        _response("итог"),
    ]
    adapter, calls = _adapter_with_stub(lambda **_: responses.pop(0))
    result = adapter.complete("p", PARAMS, tools=[_search_spec(lambda args: "r")])
    assert isinstance(result, Ok)
    tool_messages = [m for m in calls[1]["messages"] if m["role"] == "tool"]
    assert tool_messages[0]["content"].startswith("ОШИБКА ИНСТРУМЕНТА")
    assert "неизвестный инструмент unknown_tool" in tool_messages[1]["content"]
