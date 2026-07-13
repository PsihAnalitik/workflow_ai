# wiki: fastapi — зависимости (v1)

Стабильная версия: 0.139.0 (PyPI, 01.07.2026; Python >=3.10, Pydantic 2).

Сценарий: внедрение переиспользуемой логики (параметры, проверки, подключения)
в обработчики через `Depends` с минимальным дублированием.

## Когда использовать

- общая логика (параметры запроса, заголовки, сессии БД) используется в нескольких обработчиках;
- нужно автоматически включить параметры зависимости в OpenAPI-схему;
- требуется подменить зависимость в тестах (через `app.dependency_overrides`).

## Когда НЕ использовать

- логика нужна только в одном обработчике и не планируется к переиспользованию — добавь параметр прямо в функцию;
- действие должно выполняться на уровне middleware для всех запросов (CORS, логгирование) — используй `app.add_middleware`;
- зависимость выполняет только side-effect и не возвращает значение — рассмотри `BackgroundTasks` или middleware.

## Good

```python
from fastapi import Depends, FastAPI
from typing import Annotated

app = FastAPI()

def common_parameters(q: str | None = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}

CommonsDep = Annotated[dict, Depends(common_parameters)]
# Type alias — единая точка правды, сохраняет автодополнение и проверку типов

@app.get("/items/")
def read_items(commons: CommonsDep):
    return commons

@app.get("/users/")
def read_users(commons: CommonsDep):
    return commons
```

```python
# Подмена в тестах — ключом выступает оригинальная функция
def override_dependency():
    return {"q": "test", "skip": 0, "limit": 10}

app.dependency_overrides[common_parameters] = override_dependency

# После теста обязательно сбрасывать, иначе подмена утечёт в соседние тесты
app.dependency_overrides.clear()
```

## Bad

```python
# Depends(func()) — вызов функции вместо передачи самой функции
def read_items(commons: Annotated[dict, Depends(common_parameters())]):
    ...
```

```python
# Подмена не сброшена после теста — другие тесты получают чужую зависимость
def test_one():
    app.dependency_overrides[common_parameters] = fake1
    # нет clear()

def test_two():
    # здесь всё ещё активна fake1 из test_one
    ...
```

```python
# Ручное разрешение зависимости внутри обработчика
@app.get("/items/")
def read_items(q: str | None = None, skip: int = 0, limit: int = 100):
    params = common_parameters(q, skip, limit)  # дублирование, потеря OpenAPI-схемы
```

related: [fastapi](index.md), [тестирование](testing.md)
