# CHANGELOG — wiki-база знаний

## 2026-07-09 — первичная приёмка wiki как самостоятельного пакета (FR-21), v1

**Основание: приёмка автора постановки v4 / плана v3 (цех wiki_maintainer).**
Дальнейшие изменения — через цех wiki_maintainer + `wiki-apply` (строки для
новых записей печатает applier); проверка: `verify-acceptance wiki/`.

| Файл | Роль | sha256[:16] |
|---|---|---|
| `agents/index.md` | — | `a614a0bab348a9d8` |
| `agents/prompts/examples/bad.md` | — | `7d8b810e03b735b4` |
| `agents/prompts/examples/good.md` | — | `3f3e8c0d5ca04307` |
| `agents/prompts/examples/index.md` | — | `e51db5a47bc614b9` |
| `agents/prompts/examples/practices.md` | — | `562984b09ba04ac8` |
| `agents/prompts/index.md` | — | `e2e5ef2d1ea1d50f` |
| `agents/prompts/review.md` | — | `dc3b3dd11c5fbc48` |
| `assets/index.md` | — | `3584c16b461c8233` |
| `domains/index.md` | — | `e6c0ecb6a4f47f1c` |
| `index.md` | — | `dd80f1a3bdbf1bd2` |
| `methodology/examples/contracts.md` | — | `e3c3420814674825` |
| `methodology/examples/developmentplan.md` | — | `f4ca19a45ba59ec2` |
| `methodology/examples/domains.md` | — | `f62b399a382240d4` |
| `methodology/examples/index.md` | — | `43a95421cf4dcf24` |
| `methodology/examples/openapi.md` | — | `e69728583e969c98` |
| `methodology/grace.md` | — | `3152af45113b418e` |
| `methodology/index.md` | — | `1f0a4838687b033a` |
| `python/fastapi/index.md` | — | `95394d49e96bccfa` |
| `python/fastapi/testing.md` | — | `b49563386dad862a` |
| `python/index.md` | — | `8f1a990761aaca6f` |
| `python/pandas/index.md` | — | `a517b7c65c979903` |

## 2026-07-09 — duckdb в каталоге python (цех wiki_maintainer), v2

**Основание: живой прогон цеха wiki_maintainer (wiki_spec v1 → wiki_pages v1,
оба гейта ревью PASS); применение — `wiki-apply` (проверки чисты).
HITL-приёмка страницы — за автором (autopilot-прогон).**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/duckdb/index.md` | карточка технологии duckdb (материал из запроса) | `4191679abfdf3020` |
| `python/index.md` | каталог python: + строка duckdb | `f2964b9da348bef1` |

## 2026-07-09 — страница CLI фабрики (цех wiki_maintainer), v3

**Основание: живой прогон цеха (wiki_spec v3 → wiki_pages v3, гейты PASS);
применение — `wiki-apply` (первая версия артефакта отклонена applier-ом:
префикс wiki/ в путях + литеральные скобки — исправлено промптами v4 цеха).
HITL-приёмка страницы — за автором (autopilot-прогон).**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `methodology/workshop-cli.md` | справочник CLI фабрики (материал из кода) | `344a0c86ed4f3de3` |
| `methodology/index.md` | индекс области: + строка workshop-cli | `af9078535fa0af08` |

## 2026-07-09 — workshop-cli: раздел MCP-интеграции (цех wiki_maintainer), v4

**Основание: прогон цеха (wiki_spec v4 → wiki_pages v4, гейты PASS);
обновление существующей страницы — текущий текст передан в материале
(MVP-приём). HITL-приёмка содержимого — за автором (autopilot).**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `methodology/workshop-cli.md` | справочник CLI + MCP-интеграция (FR-23) | `1983712af22c1bb3` |

## 2026-07-09 — workshop-cli: уточнение wiki_update (динамические refs, живой тест), v5

**Основание: прогон цеха (wiki_spec v5 → wiki_pages v5, гейты PASS);
первый живой update-прогон БЕЗ передачи текущего текста в материале —
дифф страницы: одна строка, остальное дословно (механика v5 цеха).
HITL-приёмка — за автором (autopilot).**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `methodology/workshop-cli.md` | справочник CLI+MCP: уточнение wiki_update | `17267bb25339473d` |

## 2026-07-10 — обновление через MCP wiki_update (артефакт wiki_pages v6)

**Основание: прогон цеха wiki_maintainer (гейты PASS), применение wiki-apply.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/index.md` | — | `3bbedfb407a54d17` |
| `python/pandas/aggregation.md` | — | `5e9fd1481b3763a9` |
| `python/pandas/index.md` | — | `0e40d27c953b031d` |
| `python/pandas/io-csv.md` | — | `8ae1063d42f90b2c` |
| `python/pandas/timeseries.md` | — | `3430a1e4c5612081` |

## 2026-07-10 — обновление через MCP wiki_update (артефакт wiki_pages v7)

**Основание: прогон цеха wiki_maintainer (гейты PASS), применение wiki-apply.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/fastapi/errors.md` | — | `2f39f95a53a882d5` |
| `python/fastapi/index.md` | — | `56892a8b227ca97a` |
| `python/fastapi/validation.md` | — | `f837290a6fcea88f` |

## 2026-07-10 — обновление через MCP wiki_update (артефакт wiki_pages v9)

**Основание: прогон цеха wiki_maintainer (гейты PASS), применение wiki-apply.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/fastapi/dependencies.md` | — | `cef431aa6f307b54` |
| `python/fastapi/errors.md` | — | `2f39f95a53a882d5` |
| `python/fastapi/index.md` | — | `43254f8103346fd3` |
| `python/fastapi/testing.md` | — | `2d43c077c6848465` |
| `python/fastapi/validation.md` | — | `f837290a6fcea88f` |

## 2026-07-10 — обновление через MCP wiki_update (артефакт wiki_pages v10)

**Основание: прогон цеха wiki_maintainer (гейты PASS), применение wiki-apply.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/duckdb/files-sql.md` | — | `1dc028b58fa86f39` |
| `python/duckdb/index.md` | — | `8cc519ec7f2d95c6` |
| `python/duckdb/pandas-integration.md` | — | `87e5e221b8556abd` |

## 2026-07-10 — обновление через MCP wiki_update (артефакт wiki_pages v11)

**Основание: прогон цеха wiki_maintainer (гейты PASS), применение wiki-apply.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/pandas/aggregation.md` | — | `5e9fd1481b3763a9` |
| `python/pandas/index.md` | — | `b876a3d7cec5bf51` |
| `python/pandas/io-csv.md` | — | `8ae1063d42f90b2c` |
| `python/pandas/timeseries.md` | — | `3430a1e4c5612081` |

## 2026-07-10 — обновление через MCP wiki_update (артефакт wiki_pages v12)

**Основание: прогон цеха wiki_maintainer (гейты PASS), применение wiki-apply.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/fastapi/dependencies.md` | — | `cef431aa6f307b54` |
| `python/fastapi/errors.md` | — | `2f39f95a53a882d5` |
| `python/fastapi/index.md` | — | `6d31b786406a6ecb` |
| `python/fastapi/testing.md` | — | `2d43c077c6848465` |
| `python/fastapi/validation.md` | — | `f837290a6fcea88f` |

## 2026-07-10 — обновление через MCP wiki_update (артефакт wiki_pages v13)

**Основание: прогон цеха wiki_maintainer (гейты PASS), применение wiki-apply.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/duckdb/files-sql.md` | — | `1dc028b58fa86f39` |
| `python/duckdb/index.md` | — | `cc20693c1b2221a2` |
| `python/duckdb/pandas-integration.md` | — | `87e5e221b8556abd` |

## 2026-07-10 — обновление через MCP wiki_update (артефакт wiki_pages v14)

**Основание: прогон цеха wiki_maintainer (гейты PASS), применение wiki-apply.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/duckdb/index.md` | — | `a655723fec4f624d` |

## 2026-07-10 — обновление через MCP wiki_update (артефакт wiki_pages v15)

**Основание: прогон цеха wiki_maintainer (гейты PASS), применение wiki-apply.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/duckdb/index.md` | — | `719bcef1e198f194` |

## 2026-07-10 — карточка httpx (артефакт wiki_pages v16)

**Основание: прогон цеха wiki_maintainer (гейты PASS, wiki_spec с web_search: версия 0.28.1 подтверждена), применение wiki-apply.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/httpx/index.md` | — | `e78784a87c912b0f` |
| `python/index.md` | — | `44e3e01feae767ca` |

## 2026-07-10 — карточка polars (артефакт wiki_pages v17)

**Основание: прогон цеха wiki_maintainer (гейты PASS; wiki_spec с wiki_search — проверка дублей/related по wiki, web_search — версия), применение wiki-apply.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/index.md` | — | `c7b421c7ee31ba59` |
| `python/polars/index.md` | — | `ea9ea38505116aab` |

## 2026-07-11 — хроника сессии Claude Code (артефакт wiki_pages v18)

**Основание: прогон цеха wiki_maintainer (гейты PASS; запрос через MCP wiki_update упал на устаревшем коде сервера — UNKNOWN_TOOL wiki_search, выполнен через CLI), применение wiki-apply.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `methodology/case-claude-code-session.md` | — | `36a18010802fd6fd` |
| `methodology/index.md` | — | `160e191a231561f3` |

## 2026-07-11 — httpx retries + первый вербатим-исходник (артефакт wiki_pages v19)

**Основание: прогон цеха wiki_maintainer через CLI (гейты PASS со 2-й итерации —
ревью поймало битую относительную ссылку), применение wiki-apply --spec:
страница-исходник retries.source.md материализована из source_request спеки v23.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/httpx/index.md` | — | `2c21d468cefe30f7` |
| `python/httpx/retries.md` | — | `67b9f53c66530b30` |
| `python/httpx/retries.source.md` | — | `4663e45cb07e7476` |

## 2026-07-20 — карточки Django для цеха frontend_site (артефакт wiki_pages v20)

**Основание: прогон цеха wiki_maintainer через MCP (run 541598ecd7aa). Гейт wiki_spec —
PASS со 2-й итерации: ревью поймало отсутствие index_update для родителя
python/django/index.md у трёх дочерних страниц. Гейт wiki_pages — PASS без находок.
Находка W3 «python/fastapi/testing.md не резолвится» отклонена как ложная (файл
существует и прописан в python/fastapi/index.md) — слепой угол видимости дерева.
Страницы unverified: материала в запросе не было, фактура Django/HTMX требует
проверки человеком. Применение wiki-apply --spec.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/django/index.md` | — | `30a8a77978d2e003` |
| `python/django/templates.md` | — | `a86ed75819014d37` |
| `python/django/testing.md` | — | `4f3ba1cad720d8ff` |
| `python/django/views_urls.md` | — | `c45018de634b00b2` |
| `python/index.md` | — | `227e7fb8aaa5e245` |

## 2026-07-24 — синхронизация промптинговой области из smart-assistant/.workflow_ai

**Основание: перенос обновлений методологии прожарки (review v4: канонический
шаблон, П9–П10, хвостовая `<task>`; examples v2; новый grounding-протокол
found_data) из копии фабрики smart-assistant. agents/index.md — merge (сохранена
related-ссылка на методологию). Проверка: wiki-check, 42 страницы.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `agents/index.md` | — | `7fc976efcdc36099` |
| `agents/prompts/index.md` | — | `8bf4adc440d4a384` |
| `agents/prompts/review.md` | — | `ce0ea9c0bd031082` |
| `agents/prompts/grounding_tags.md` | — | `70ef84ebe570e2c4` |
| `agents/prompts/examples/index.md` | — | `747bfdceab55ceeb` |
| `agents/prompts/examples/bad.md` | — | `d12c7ae1f8aba599` |
| `agents/prompts/examples/good.md` | — | `93b2d0fe8a6e8947` |
| `agents/prompts/examples/practices.md` | — | `12db0f05d4603b57` |

## 2026-07-26 — область python/errors: обработка исключений (запрос автора)

**Основание: обогащение по статье KDnuggets «Advanced Error Handling in Python»
и репозиторию balapriyac/python-basics/error-handling. handling.md — техники
Т1–Т5 формирования обработки; swallowing.md — каталог проглатывания S1–S8
для цехов exception_hardener / exception_roaster. python/index.md — блок
методологических областей. Проверка: wiki-check, 45 страниц.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/index.md` | — | `4eb306637afdc216` |
| `python/errors/index.md` | — | `f261e6c81d2fe35a` |
| `python/errors/handling.md` | — | `c04d9c30126e867d` |
| `python/errors/swallowing.md` | — | `2eb8bf83e05c0141` |

## 2026-07-26 — handling.md v2: сверка контрактов возврата после правок

**Основание: находка ревью пользователя на выходе exception_hardener —
правки обработки ошибок добавляют точки возврата, а аннотация остаётся
старой (частный случай: return False при -> None в __exit__). Добавлен
общий п.5 методологии (сверка аннотации с фактическими return по всем
путям, с негативными случаями) и Е6 в чеклист harden_review.
Перепин harden.json → v2.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `python/errors/handling.md` | — | `da5e44f1f5c5ed01` |

## 2026-07-29 — область security: каталог внедрения, таксономия CWE, достижимость

**Основание: ТЗ на цеха анализа безопасности (`materials/security_shops_task_statement.md`),
этап 1 «Область wiki security». Страницы написаны напрямую (не через
цех wiki_maintainer) как справочники цехов `manifest_auditor` и `code_auditor`.
`injection-patterns.md` доведена до v2 по результатам прогона №1 корпуса:
добавлены разделы «Одна находка на один фрагмент» (частный класс поглощает
общий) и «Локатор: где именно находка» — precision прогона вырос 0.523 → 0.735.
Узлы обоих цехов пиннят версии страниц; смена содержания требует пересчёта
метрик по корпусу (NFR-0.4).**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `index.md` | — | `c8eda1ed44d24a24` |
| `security/index.md` | — | `4967964a57df340f` |
| `security/injection-patterns.md` | — | `e8213d70ad69a05a` |
| `security/cwe.md` | — | `e84cff847331ccd7` |
| `security/reachability.md` | — | `d7bb0d19cc35327f` |

## 2026-07-29 — security: переход на шкалу весов постановки задачи (p0 блокирующий)

**Основание: решение автора — оставить шкалу ТЗ как есть и поддержать её в
движке, а не подгонять цеха под шкалу фабрики. Движок расширен точкой
конфигурации `GraphConfig.severity_scale` (`p3_high` по умолчанию | `p0_high`),
`evaluate_gate` вычисляет блокирующие находки по объявленной шкале; глобальный
переворот отвергнут — у восьми существующих цехов промпты в шкале 🔴p3.
Все четыре страницы области переведены на шкалу 🔴p0 → 🟢p3 и явно помечают,
что она обратна остальной вике. Узлы обоих цехов перепиннены.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `security/index.md` | — | `fe83e31ed3e6e733` |
| `security/injection-patterns.md` | — | `d36c3d6d203d77a6` |
| `security/cwe.md` | — | `99ee62d52f9d3d0d` |
| `security/reachability.md` | — | `65206b3bcf4a4b98` |
