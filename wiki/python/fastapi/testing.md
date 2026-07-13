# wiki: FastAPI-сервис и его тесты в офлайн-песочнице (v1)

Для кодогенератора цеха «микросервис». Песочница без сети: тесты — только in-process.
Стабильная версия: 0.139.0 (PyPI, 01.07.2026; Python >=3.10, Pydantic 2).

## Обработчики: ошибки контракта → {code, message} + 400

```python
# GOOD: код ошибки из контракта, машиночитаемое тело, статус 400 для ошибок входа
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post("/search/exact")
def search_exact(body: SearchRequest) -> JSONResponse:
    result = exact_search(body.query)          # ядро возвращает Result-стиль, не бросает
    if result is None:
        return JSONResponse(status_code=400,
                            content={"code": "EMPTY_QUERY", "message": "query пуст"})
    return JSONResponse(status_code=200, content=result)

# BAD: raise HTTPException(500, "error") на ошибку ВХОДА — клиентская ошибка стала серверной,
# тело не содержит code из контракта
```

## Тесты: TestClient, без сети и файлов

**Требования:** `TestClient` основан на HTTPX и требует установленный пакет `httpx`.
Тестовые функции — обычные `def` (не `async def`), вызовы клиента синхронны (без `await`).
Данные передаются именованными параметрами: `json=...`, `headers=...`, `cookies=...`.

**Подмена зависимостей:** для изоляции тестов используй `app.dependency_overrides`
(подробнее — [dependencies.md](dependencies.md)). После каждого теста обязателен сброс: `app.dependency_overrides.clear()`.

```python
# GOOD: in-process клиент; фикстуры в тесте; проверяется и happy, и код ошибки
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_exact_search_ok() -> None:
    response = client.post("/search/exact", json={"query": "кот"})
    assert response.status_code == 200

def test_exact_search_empty_query_maps_to_400() -> None:
    response = client.post("/search/exact", json={"query": ""})
    assert response.status_code == 400
    assert response.json()["code"] == "EMPTY_QUERY"

# BAD: httpx.get("http://localhost:8000/...") — реальная сеть, в песочнице упадёт;
# BAD: тест без проверки тела ошибки — код контракта не зафиксирован
```

## Ядро отдельно от транспорта

```python
# GOOD: ядро тестируется без FastAPI вообще (модульные тесты быстрее и точнее)
def test_core_empty_query_returns_none() -> None:
    assert exact_search("") is None
```

Правило: unit-тесты на каждый модуль ядра + TestClient-тесты на каждый endpoint;
каждая ошибка контракта достижима хотя бы одним тестом.

related: [fastapi](index.md), [зависимости](dependencies.md)
