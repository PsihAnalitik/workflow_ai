# CHANGELOG — цех data-аналитик

## 2026-07-08 — приёмка FR-17 (шаблоны артефактов и wiki), v1

**HITL-решение автора: ACCEPT.** Промпты узлов цеха и wiki-подборка приняты как
рабочая версия v1. Приёмка привязана к содержимому (sha256, первые 16 символов):

| Файл | Роль | sha256[:16] |
|---|---|---|
| `prompts/stage.analysis_spec.md` | stage-карта постановщика ТЗ (для `artifact_generator.base.md`) | `fc706ac78f0c0f3d` |
| `prompts/spec_review.base.md` | приёмщик ТЗ (agent review, гейт p3/p2) | `9cd0450852f0af41` |
| `prompts/codegen.base.md` | исполнитель (кодогенерация file map) | `2eaa0d45e552ccdc` |
| `prompts/judge.base.md` | судья (вердикт READY/NOT_READY) | `5a874074492d014b` |
| `prompts/empty.stage.md` | пустая stage-карта для самодостаточных base | `272cba99db5edfce` |
| `../../wiki/pandas_analysis.md` | wiki v1 для исполнителя (`wiki_refs` пиннит "v1") | `a517b7c65c979903` |

Основание приёмки: сквозной прогон цеха на deepseek-v4-pro — ТЗ (review PASS),
executor v2 (19 тестов в песочнице), judge v2 = READY, `main.py` проверен на демо-CSV
(артефакты `artifacts/*`, журналы `runs/smoke.jsonl`, `runs/rework.jsonl`).

Правило изменений: правка любого из этих файлов = новая версия шаблонов цеха →
новая запись здесь и повторная HITL-приёмка (методология FR-17,
`user_docs/task_statement.md` §2.2).

## 2026-07-08 — приёмка конфигурации цеха, v2

**HITL-решение автора: ACCEPT** (правило приёмки распространено на конфиги цеха —
решение автора, зафиксировано в постановке §2.2). Состав:

| Файл | Роль | sha256[:16] |
|---|---|---|
| `graph.json` | рабочий граф (HITL; judge-гейт на executor) | `760c52d7a5f12016` |
| `graph.autopilot.json` | граф для smoke-прогонов | `51f46e64fedb2ce7` |
| `models.json` | реестр профилей моделей | `5302029cb42ac606` |
| `nodes/task_spec.json` | узел постановщика ТЗ | `c0083f97b8481e43` |
| `nodes/task_spec_review.json` | узел приёмщика ТЗ | `eda4a5ad3c3edd6a` |
| `nodes/executor.json` | узел исполнителя (codegen) | `d872f6f2914b610e` |
| `nodes/judge.json` | judge-гейт исполнителя | `6375b75ca10eb7c5` |
| `make_input.py` | инструмент: профилировщик CSV | `149539dd7fdc1c83` |

Ключевые изменения против исходной структуры: judge — гейт codegen-узла
(автоцикл judge→executor), отдельный judge-узел убран; поле project=sales_analysis
(выходы в projects/sales_analysis/); блок package (FR-13).

Правило изменений: с этой записи приёмка покрывает шаблоны, wiki И конфиги цеха.

## 2026-07-09 — wiki по областям знаний (FR-18) + стадия tech_selection (FR-19), v3

**Основание: приёмка автора постановки v3 / плана v2 (wiki-база знаний, 09.07.2026).**
Wiki перенесена в структуру областей; добавлена стадия `tech_selection`:
стек выбирается из каталога `wiki/python/index.md`, артефакт `tech_stack.xml`
проходит гейты, исполнитель получает ТОЛЬКО страницы выбранных технологий
(`wiki_refs_from`), judge проверяет код на соответствие принятому стеку.

Сняты с проверки (переезд):

| Файл | Роль | sha256[:16] |
|---|---|---|
| `../../wiki/pandas_analysis.md` | перемещён → python/pandas/index.md | `removed` |

Приняты (новые пути и файлы стадии):

| Файл | Роль | sha256[:16] |
|---|---|---|
| `../../wiki/python/index.md` | каталог технологий (вход tech_selection, FR-19) | `8f1a990761aaca6f` |
| `../../wiki/python/pandas/index.md` | wiki pandas (контент без изменений, hash = v1) | `a517b7c65c979903` |
| `prompts/tech_selection.base.md` | промпт выбора стека (ранний коллапс, ref из каталога) | `cf90c4de832ab012` |
| `nodes/tech_selection.json` | узел выбора стека | `d5976f99c2b06e29` |
| `nodes/executor.json` | исполнитель: wiki_refs_from=tech_selection | `5ba5a0f019e088d8` |
| `prompts/judge.base.md` | судья: правило «код в пределах принятого стека» | `b6e1f99026b5f1eb` |
| `graph.json` | рабочий граф: + tech_selection (HITL), executor от двух старших | `6d7ee42f034e0340` |
| `graph.autopilot.json` | smoke-граф: + tech_selection | `c50b39a2bbc8006b` |

## 2026-07-09 — rework-цикл ревью (аудит нестабильности), v4

**Основание: аудит расходимости цикла task_spec (09.07.2026) + выбор автором
варианта B (блок находок с якорями-id).** Оркестратор теперь передаёт на
доработку предыдущий артефакт + находки F-NN с anchor; генератор правит адресно
(зона rework_rules каркаса); ревьюер получил операционализированные веса, зону
«не-находки», якорные локации и режим повторного прохода.

| Файл | Роль | sha256[:16] |
|---|---|---|
| `prompts/spec_review.base.md` | приёмщик ТЗ v2: веса, не-находки, повторный проход | `b4331ef0d5e135fe` |
| `../../user_docs/prompts/artifact_generator.base.md` | каркас генератора: + rework_rules, пометка данных на INPUTS (ранее не пинился) | `ec7812f8a1140714` |

## 2026-07-09 — rework-цикл для codegen-узла, v5

**Основание: продолжение записи v4 (вариант B) — та же механика для кодогенерации.**
Внутренний тест-цикл, judge NOT_READY и HITL REVISE передают прошлый file map
(<previous_artifact>) + замечания в тегах; iteration_rules кодогенератора —
адресная правка, нетронутые файлы копируются дословно.

| Файл | Роль | sha256[:16] |
|---|---|---|
| `prompts/codegen.base.md` | исполнитель: rework по previous_artifact | `f0be3e0a556e15ee` |
