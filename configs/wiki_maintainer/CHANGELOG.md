# CHANGELOG — цех wiki_maintainer

## 2026-07-09 — первичная приёмка цеха (FR-21), v1

**Основание: приёмка автора постановки v4 / плана v3.** Стадии wiki_spec →
wiki_pages (обе с agent-review и HITL); применение артефакта — только через
детерминированный `wiki-apply` (валидация, wiki-check по временной копии,
атомарная запись, строки для wiki/CHANGELOG.md). Правка любого файла ниже =
новая запись здесь и повторная HITL-приёмка (FR-17).

| Файл | Роль | sha256[:16] |
|---|---|---|
| `graph.json` | — | `32cb8813aa84ecf9` |
| `graph.autopilot.json` | — | `1d8157acc5a53cb6` |
| `models.json` | — | `5302029cb42ac606` |
| `nodes/wiki_spec.json` | — | `4755a6800c69e40c` |
| `nodes/wiki_spec_review.json` | — | `7f9e658b96120600` |
| `nodes/wiki_pages.json` | — | `2eae5cbc071d50e9` |
| `nodes/wiki_pages_review.json` | — | `16eec586e2b30ff3` |
| `prompts/wiki_spec.base.md` | — | `7c9a063c984ec112` |
| `prompts/wiki_spec_review.base.md` | — | `dea0e8d4308e9461` |
| `prompts/wiki_pages.base.md` | — | `e17eb4bccccb24e7` |
| `prompts/wiki_pages_review.base.md` | — | `24830dec51341c4c` |
| `prompts/empty.stage.md` | — | `272cba99db5edfce` |

## 2026-07-09 — фикс обрезки file map (smoke-аудит), v2

**Основание: первый живой прогон — страницы duckdb обрезались лимитом 8192
токенов ДО секции related, ревьюер честно валил гейт (3/3 итераций).
Фикс: max_tokens 16384 (как у C4 microservice) + правило компактности
страницы (≤80 строк, страница обязана завершаться related).**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `models.json` | — | `c8e948ebf6d8865e` |
| `prompts/wiki_pages.base.md` | — | `3c9ead330d21238a` |

## 2026-07-09 — source_request в спеке (smoke-аудит #2), v3

**Основание: второй живой прогон — ревьюер спеки не видит запрос (читает
только артефакт) и не может проверить наличие материала (W4) — вечная
находка. Фикс по конвенции task_spec: запрос копируется в спеку вербатим
(<source_request>); W3/W4 переформулированы на проверяемые источники.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `prompts/wiki_spec.base.md` | — | `518328bca21df273` |
| `prompts/wiki_spec_review.base.md` | — | `038f3f145d1396ef` |

## 2026-07-09 — пути без префикса wiki/ и запрет литеральных скобок (smoke-аудит #3), v4

**Основание: wiki-apply отклонил артефакт CLI-доков — генератор добавил
префикс wiki/ к путям file map и процитировал двойные фигурные скобки,
документируя их запрет; ревьюер оба случая пропустил. Фикс: негативный
пример пути в output_format генератора; у ревьюера — p3-правило префикса
и пример-находка про скобки-цитату.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `prompts/wiki_pages.base.md` | — | `34c75e70f1bae29e` |
| `prompts/wiki_pages_review.base.md` | — | `f190d3af7e047d3a` |

## 2026-07-09 — динамические wiki_refs для wiki_pages (FR-21+FR-19), v5

**Основание: приёмка автора («оформи динамические wiki_refs», 09.07.2026).
Стадия wiki_pages и её ревьюер получают текущий текст update-страниц
автоматически из принятой спеки (wiki_refs_from=wiki_spec, парсер TSK-1604
обобщён; динамические ссылки добавляются к статическим). MVP-приём
«текущий текст в материале» больше не нужен; ревьюер сверяет сохранность
разделов update-страниц (P5).**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `nodes/wiki_pages.json` | — | `7eb187881f701a17` |
| `nodes/wiki_pages_review.json` | — | `1f466d44c5a69d13` |
| `prompts/wiki_pages.base.md` | — | `de09cfff4192d8c7` |
| `prompts/wiki_pages_review.base.md` | — | `44d8abe27ff0d429` |

## 2026-07-10 — дерево wiki в контексте ревьюера (аудит прогонов), v6

**Основание: аудит 2026-07-10 — ревью wiki_pages браковало ссылки на страницы,
применённые ПРОШЛЫМИ прогонами (видело только area-индексы wiki_refs + file map):
автор попадал в вилку p3 «битая ссылка» / p3 «цех не удаляет строки», гейт
не сходился за 3 итерации (обход требовал страниц-копий в file map).
Фикс: TSK-1606 tree_listing (M-16) + NodeConfig.wiki_tree_root — в INPUTS
ревьюера добавляется блок «=== wiki tree ===» с путями всех страниц;
P1/P3 чек-листа сверяются с деревом.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `nodes/wiki_pages_review.json` | + wiki_tree_root=wiki | `1924aa618a017f96` |
| `prompts/wiki_pages_review.base.md` | P1/P3 по дереву wiki | `b5e306ef6a8f6aab` |

## 2026-07-10 — web_search для wiki_spec (TSK-0402/M-21), v7

**Основание: инструменты агентов в цехах (запрос автора 2026-07-10).
Узел wiki_spec получает tools=["web_search"] (Tavily, ключ TAVILY_API_KEY):
точечная проверка фактов запроса (существование технологии, стабильная
версия, имя пакета) до составления спеки. Политика unverified НЕ меняется —
определяется наличием материала в запросе; поиск материал не заменяет.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `nodes/wiki_spec.json` | web_search у wiki_spec | `4142086fcb93e2d1` |
| `prompts/wiki_spec.base.md` | web_search у wiki_spec | `bd325e65f02ace06` |

## 2026-07-11 — no-op контракт wiki_spec (тест дубля через MCP), v8

**Основание: живой прогон с запросом-дублем (SQL к CSV/Parquet через duckdb —
покрыто python/duckdb/files-sql.md). wiki_spec корректно выдавал no-op-спеку
(пустой <pages>), но ревью зацикливалось: W3 «related пуст», после фикса — W4
«unverified», после — ревьюер не видел files-sql.md (страница в индексе
технологии, не области) → трижды MAX_ITERATIONS_EXCEEDED. Фикс: правило W0
(при пустом <pages> W2–W4 неприменимы; summary сверяется с деревом wiki),
no-op-форма в output_format wiki_spec, wiki_tree_root у wiki_spec_review.
Проверено: тот же запрос — PASS с 1-й итерации.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `nodes/wiki_spec_review.json` | + wiki_tree_root=wiki | `3783978dcb6edb49` |
| `prompts/wiki_spec_review.base.md` | W0 no-op, W3 постранично | `371da7284e8e8945` |
| `prompts/wiki_spec.base.md` | no-op-форма в output_format | `e545448b7000e279` |

## 2026-07-11 — вербатим-исходник рядом с пересказом (запрос автора), v9

**Основание: пересказ + исходник, ссылка из пересказа. Спека объявляет
<source_page path="<страница>.source.md" for="<страница>"/> (только при
материале в запросе); wiki_pages ставит строку «Исходник: [полный текст](...)»
перед related и сам файл НЕ генерирует; материализует его wiki-apply
детерминированно из <source_request> спеки (вербатим силами LLM ненадёжен).
Страницы *.source.md исключены из механических проверок wiki (сироты, линт
двойных скобок, ссылки) — вербатим-приложения. Ядро: TSK-1801 (spec_content,
SOURCE_SPEC_INVALID, wiki-apply --spec), TSK-1605. Ревью: W6 у wiki_spec_review,
исключение в P3 у wiki_pages_review. Живой прогон: python/httpx/retries.md +
retries.source.md применены, wiki-check чист.**

| Файл | Роль | sha256[:16] |
|---|---|---|
| `prompts/wiki_spec.base.md` | правило и пример <source_page> | `7f9cd27f46b5921b` |
| `prompts/wiki_spec_review.base.md` | W6 исходник; W0→W6 | `0e4292ac2ae1ed2f` |
| `prompts/wiki_pages.base.md` | строка «Исходник:» перед related | `407c8713a1152c4d` |
| `prompts/wiki_pages_review.base.md` | P3: ссылка на *.source.md не битая | `0767f13b59e3aef3` |
