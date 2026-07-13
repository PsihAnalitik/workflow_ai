# wiki: fastapi (v1)

Стабильная версия: 0.139.0 (PyPI, 01.07.2026; Python >=3.10, Pydantic 2, Starlette).
Документация: https://fastapi.tiangolo.com/

Каркас HTTP-микросервисов. `ref: python/fastapi`.

Когда использовать: сервис с REST API по openapi-проекции контрактов;
целевая среда — Docker Compose (антицели постановки §5).
Когда НЕ использовать: разовый анализ данных без сетевого интерфейса
(это класс задач [pandas](../pandas/index.md)); фоновые воркеры без HTTP.

- [testing.md](testing.md) — офлайн-тестирование FastAPI-приложений
  (TestClient, без сети — обязательное требование песочницы).
- [dependencies.md](dependencies.md) — зависимости FastAPI: `Depends` с Annotated, переиспользование, подмена в тестах
- [validation.md](validation.md) — модели запроса и ответа (Pydantic body, path/query, фильтрация полей)
- [errors.md](errors.md) — обработка ошибок (HTTPException, exception_handler, переопределение валидации)

related: [каталог python](../index.md), [validation.md](validation.md), [errors.md](errors.md)
