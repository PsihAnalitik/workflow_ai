"""M-24 db_query: валидация запроса, исполнитель, текстовые сбои (TSK-2401, TSK-2402)."""
from __future__ import annotations

from workshop.db_query import (
    DB_DSN_MISSING,
    DB_QUERY_REJECTED,
    FakeDbClient,
    PsycopgClient,
    build_db_tools,
    validate_query,
)
from workshop.result import Err, Ok


# --- TSK-2401: валидация ---

def test_validate_appends_limit() -> None:
    result = validate_query("SELECT dt FROM t")
    assert result == Ok("SELECT dt FROM t LIMIT 100")


def test_validate_keeps_existing_limit() -> None:
    result = validate_query("select dt from t limit 5;")
    assert result == Ok("select dt from t limit 5")


def test_validate_rejects_non_select() -> None:
    for query in ("DELETE FROM t", "DROP TABLE t", "UPDATE t SET a=1", ""):
        result = validate_query(query)
        assert isinstance(result, Err), query
        assert result.code == DB_QUERY_REJECTED


def test_validate_rejects_multistatement() -> None:
    result = validate_query("SELECT 1; DROP TABLE t")
    assert isinstance(result, Err)
    assert result.code == DB_QUERY_REJECTED


# --- TSK-2402: исполнитель ---

def _db_tool(client) -> object:
    return build_db_tools(client)[0]


def test_executor_formats_rows() -> None:
    client = FakeDbClient([Ok([("dt", "cnt"), ("2026-01-01", 5)])])
    answer = _db_tool(client).executor({"query": "SELECT dt, cnt FROM t"})
    assert "dt | cnt" in answer and "2026-01-01 | 5" in answer
    assert client.queries == ["SELECT dt, cnt FROM t LIMIT 100"]


def test_executor_rejects_ddl_before_db() -> None:
    client = FakeDbClient([])
    answer = _db_tool(client).executor({"query": "DROP TABLE t"})
    assert "ОШИБКА ИНСТРУМЕНТА" in answer and DB_QUERY_REJECTED in answer
    assert client.queries == []  # до клиента не дошло


def test_executor_missing_dsn_is_text(monkeypatch) -> None:
    monkeypatch.delenv("WORKSHOP_DB_DSN", raising=False)
    answer = _db_tool(PsycopgClient()).executor({"query": "SELECT 1"})
    assert "ОШИБКА ИНСТРУМЕНТА" in answer and DB_DSN_MISSING in answer
