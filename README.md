# workflow_ai — Agent Workshop

Агентская мастерская: FSM-оркестрируемый конвейер «цехов» (workshop-агентов), где LLM-узлы генерируют, ревьюят и принимают артефакты по конфигурируемым графам.

## Структура

- `workshop/` — ядро: оркестратор, FSM-граф, LLM-клиент, кодогенерация, review-гейты, MCP-сервер, песочница.
- `configs/` — конфигурации цехов (граф, узлы, промпты, модели): `data_analyst`, `llm_wiki`, `microservice`, `products` и др.
- `prompts/` — общие промпты.
- `wiki/` — LLM-поддерживаемая вики проекта (домены, методология, агенты).
- `tests/` — pytest-тесты.
- `user_docs/` — постановка задачи и пользовательская документация.

## Запуск

Требуется Python ≥ 3.14 и [uv](https://docs.astral.sh/uv/):

```bash
uv sync
cp .env.example .env   # заполнить ключи
uv run python -m workshop --help
```

Тесты:

```bash
uv run pytest
```
