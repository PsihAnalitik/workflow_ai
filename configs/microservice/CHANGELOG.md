# CHANGELOG — цех «микросервис»

## 2026-07-08 — приёмка FR-17 (промпты цеха и wiki), v1

**HITL-решение автора: ACCEPT.** Пакет цеха принят как рабочая версия v1.
Приёмка привязана к содержимому (sha256, первые 16 символов):

| Файл | Роль | sha256[:16] |
|---|---|---|
| `prompts/stage.c4.md` | stage-карта developmentplan/C4 (для `artifact_generator.base.md`) | `0f89a5e196115a2a` |
| `prompts/codegen.base.md` | кодогенератор сервиса (FastAPI + ядро, file map) | `2c422d745f24b214` |
| `prompts/empty.stage.md` | пустая stage-карта для самодостаточных base | `23165e98a945f714` |
| `../../wiki/grace_methodology.md` | методология цепочки — подаётся каждому узлу | `3152af45113b418e` |
| `../../wiki/examples/domains.md` | good/bad стадии domains | `f62b399a382240d4` |
| `../../wiki/examples/contracts.md` | good/bad стадии contracts | `e3c3420814674825` |
| `../../wiki/examples/openapi.md` | good/bad стадии openapi | `e69728583e969c98` |
| `../../wiki/examples/developmentplan.md` | good/bad стадии C4 | `f4ca19a45ba59ec2` |
| `../../wiki/fastapi_testing.md` | офлайн-тестирование FastAPI (для executor) | `b49563386dad862a` |

Стадии domains/contracts/openapi используют авторские stage-карты
`user_docs/prompts/stage.{domains,contracts,openapi}.md` — они предсуществующие
и приёмке этого пакета не подлежат.

Основание приёмки: два прогона на deepseek-v4-pro —
(1) golden-прогон против эталона `text_searcher/` (структурная эквивалентность,
артефакты `projects/text_searcher/artifacts/*/v1.xml`);
(2) полный прогон до работающего кода: цепочка v2 → c4 v1 → executor v1
(8 файлов, 20 тестов в песочнице `workshop-microservice:latest`,
код в `projects/text_searcher/generated/`).

Правило изменений: правка любого из этих файлов = новая версия пакета →
новая запись здесь и повторная HITL-приёмка (методология FR-17,
`user_docs/task_statement.md` §2.2).

Известные ограничения v1: артефакт C4 требует `max_tokens ≥ 16384` (обрезка
ловится парсером как OUTPUT_UNPARSEABLE); межпрогонный дизайн недетерминирован
даже при temperature=0 — фиксация дизайна достигается HITL-гейтами ранних стадий.

## 2026-07-08 — приёмка конфигурации цеха, v2

**HITL-решение автора: ACCEPT** (правило приёмки распространено на конфиги цеха —
решение автора, зафиксировано в постановке §2.2). Состав:

| Файл | Роль | sha256[:16] |
|---|---|---|
| `graph.json` | рабочий граф (HITL на всех узлах; package-блок FR-13) | `6a2f2db5aac91fd6` |
| `graph.autopilot.json` | граф для smoke/golden-прогонов | `c565a286299eca4e` |
| `models.json` | реестр профилей (max_tokens=16384 — ограничение C4) | `c8e948ebf6d8865e` |
| `nodes/domains.json` | узел стадии domains | `3ce18d7eafbc7a4a` |
| `nodes/contracts.json` | узел стадии contracts | `6217cb6360ac12e2` |
| `nodes/openapi.json` | узел стадии openapi | `5d30b49c98206e66` |
| `nodes/c4.json` | узел стадии developmentplan/C4 | `87e58232ddefa4c4` |
| `nodes/executor.json` | узел кодогенерации сервиса | `7a8a246938056293` |

Правило изменений: с этой записи приёмка покрывает шаблоны, wiki И конфиги цеха.

## 2026-07-08 — приёмка sandbox.Dockerfile, v3

**HITL-решение автора: ACCEPT.** Определение образа песочницы/рантайма цеха
зафиксировано файлом (ранее образ собирался ad-hoc командой и не версионировался):

| Файл | Роль | sha256[:16] |
|---|---|---|
| `sandbox.Dockerfile` | образ workshop-microservice: python:3.14-slim + pytest, fastapi, httpx, pymorphy3(+dicts), uvicorn | `7ef54546d0a3aebe` |

Причина появления: живой запуск продукта search_platform выявил отсутствие uvicorn
в образе — тесты (pytest + TestClient) проходили, но serve-команда пакета не
стартовала. После добавления uvicorn пакет и продукт пересобраны,
`uvicorn==0.51.0` вошёл во frozen-зависимости пакета.

## 2026-07-09 — реструктуризация wiki по областям знаний (FR-18), v3

**Основание: приёмка автора постановки v3 / плана v2 (wiki-база знаний, 09.07.2026).**
Wiki-страницы перенесены в структуру областей (`methodology/`, `python/`);
содержимое страниц не менялось (хэши совпадают с записью v1). Конфиги узлов
обновлены на новые пути `wiki_refs`.

Сняты с проверки (переезд):

| Файл | Роль | sha256[:16] |
|---|---|---|
| `../../wiki/grace_methodology.md` | перемещён → methodology/grace.md | `removed` |
| `../../wiki/examples/domains.md` | перемещён → methodology/examples/ | `removed` |
| `../../wiki/examples/contracts.md` | перемещён → methodology/examples/ | `removed` |
| `../../wiki/examples/openapi.md` | перемещён → methodology/examples/ | `removed` |
| `../../wiki/examples/developmentplan.md` | перемещён → methodology/examples/ | `removed` |
| `../../wiki/fastapi_testing.md` | перемещён → python/fastapi/testing.md | `removed` |

Приняты по новым путям:

| Файл | Роль | sha256[:16] |
|---|---|---|
| `../../wiki/methodology/grace.md` | методология цепочки — подаётся каждому узлу | `3152af45113b418e` |
| `../../wiki/methodology/examples/domains.md` | good/bad стадии domains | `f62b399a382240d4` |
| `../../wiki/methodology/examples/contracts.md` | good/bad стадии contracts | `e3c3420814674825` |
| `../../wiki/methodology/examples/openapi.md` | good/bad стадии openapi | `e69728583e969c98` |
| `../../wiki/methodology/examples/developmentplan.md` | good/bad стадии C4 | `f4ca19a45ba59ec2` |
| `../../wiki/python/fastapi/testing.md` | офлайн-тестирование FastAPI (для executor) | `b49563386dad862a` |
| `../../wiki/python/fastapi/index.md` | карточка технологии fastapi (каталог FR-19) | `95394d49e96bccfa` |
| `nodes/domains.json` | узел стадии domains (новый путь wiki) | `e0883bfe4f332727` |
| `nodes/contracts.json` | узел стадии contracts (новый путь wiki) | `fbc33998e52863b1` |
| `nodes/openapi.json` | узел стадии openapi (новый путь wiki) | `d3901fa2a189ad34` |
| `nodes/c4.json` | узел стадии developmentplan/C4 (новый путь wiki) | `6c5d482ea7c2439b` |
| `nodes/executor.json` | узел кодогенерации (новый путь wiki) | `34a8feafce66d7d6` |

## 2026-07-09 — стадия tech_selection (FR-19), v4

**Основание: приёмка автора постановки v3 / плана v2; продолжение записи v3.**
Стек выбирается из каталога `wiki/python/index.md` стадией `tech_selection`
(upstream = contracts + openapi); принятый `tech_stack.xml` входит в upstream
стадии C4 (проектирует в его пределах); executor получает ТОЛЬКО страницы
выбранных технологий (`wiki_refs_from`). Judge-гейта у executor этого цеха нет —
соблюдение стека контролируют C4-стадия и HITL-приёмка.

| Файл | Роль | sha256[:16] |
|---|---|---|
| `prompts/tech_selection.base.md` | промпт выбора стека (ранний коллапс, ref из каталога) | `765406c44e29062a` |
| `nodes/tech_selection.json` | узел выбора стека | `b2192c0c42c57a67` |
| `nodes/executor.json` | исполнитель: wiki_refs_from=tech_selection | `3b5caa5d12328635` |
| `graph.json` | рабочий граф: + tech_selection (HITL), c4 от трёх старших | `17f0cd739d34f256` |
| `graph.autopilot.json` | smoke-граф: + tech_selection | `363a1828ee05f37c` |
| `../../wiki/python/index.md` | каталог технологий (вход tech_selection, FR-19) | `8f1a990761aaca6f` |

## 2026-07-09 — rework-цикл ревью (общий каркас генератора), v5

**Основание: то же, что запись v4 цеха data_analyst.** Каркас
`artifact_generator.base.md` (используется стадиями domains/contracts/openapi/c4)
получил зону rework_rules (адресная доработка по находкам с якорями-id)
и пометку «данные, не команды» на INPUTS; ранее файл не пинился.

| Файл | Роль | sha256[:16] |
|---|---|---|
| `../../user_docs/prompts/artifact_generator.base.md` | каркас генератора артефактов | `ec7812f8a1140714` |

## 2026-07-09 — rework-цикл для codegen-узла, v6

**Основание: то же, что запись v5 цеха data_analyst.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `prompts/codegen.base.md` | кодогенератор сервиса: rework по previous_artifact | `30d94de6e5cb9c7a` |
