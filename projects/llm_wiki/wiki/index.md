# wiki: карта областей (v1)

Вики строится цехом `llm_wiki` из материала пользователя — выгрузок чатов,
документов и ссылок. Области рождаются из тем материала: новая область =
директория со своим `index.md` + строка в таблице ниже. Содержимое страниц
трассируется к чанкам исходного материала (поле source_chunks спецификации).

| Область | Что внутри |
|---|---|
| [agent-workshop](agent-workshop/index.md) | MCP-сервер agent-workshop: цеха, конвейеры, smoke-тесты |
| [payments](payments/index.md) | интеграция платежей: Stripe, вебхуки, подписки |
| [search](search/index.md) | поиск по каталогу: Postgres FTS, ранжирование |
| [methodology](methodology/index.md) | методология фабрики: цеха, стадии, rework-циклы |
| [python](python/index.md) | документация Python-библиотек: pandas, fastapi, duckdb |

_Вики наполняется по мере прогона цеха `llm_wiki` — новые области
добавляются в таблицу выше._

## related

- [agent-workshop](agent-workshop/index.md) — MCP-сервер agent-workshop
- [payments](payments/index.md) — интеграция платежей
- [search](search/index.md) — поиск по каталогу
- [methodology](methodology/index.md) — методология фабрики
