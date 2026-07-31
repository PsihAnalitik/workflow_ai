# Цех `manifest_auditor`

Статический аудит текстовых артефактов, задающих поведение агента: манифесты
MCP-серверов, системные промпты, skill-файлы, описания инструментов (раздел 2
ТЗ `materials/security_shops_task_statement.md`). Вход — элемент,
выход — `audit_report` на элемент.

```
audit[review]
```

Один узел с ревью-гейтом, по образцу `prompt_roaster`. Инструментов у узлов
нет вообще: элемент виден целиком (`inline_limit_chars: 40000`), сети и
записи не требуется (NFR-0.1). Классы находок живут в
`wiki/security/injection-patterns.md` и расширяются без правки промпта
(FR-A1); узлы пиннят версию страницы.

## Состав

| Путь | Что |
|---|---|
| `corpus/gen_corpus.py` | сборка 54 манифестов из литералов; сверяется с разметкой |
| `corpus/labels.jsonl` | эталонная разметка (копия из `materials/security_data`) |
| `corpus/manifests/` | корпус: 23 позитива, 21 негатив, 10 трудных негативов |
| `corpus/items/` | элементы map-прогона (см. `tools/prepare_items.py`) |
| `corpus/runs/` | прогоны: `regex_baseline`, `tz_1..tz_5`, `metrics_tz.json` |
| `tools/prepare_items.py` | корпус → элементы; diff-элементы получают базовую версию |
| `tools/collect_run.py` | артефакты прогона → плоский каталог для измерителя |
| `tools/accept_manifests.py` | приёмочная таблица sha256 принятых манифестов (FR-A3) |
| `tools/score_audit.py` | измеритель — копия из `materials/security_data` без правок |
| `tools/baseline_regex.py` | наивный детектор по ключевым словам — точка отсчёта |

## Прогон

```bash
python3 configs/manifest_auditor/corpus/gen_corpus.py
python3 configs/manifest_auditor/tools/prepare_items.py --corpus configs/manifest_auditor/corpus

.venv/bin/python -m workshop map manifest_auditor \
    --files 'configs/manifest_auditor/corpus/items/*.md' --workers 8

cd configs/manifest_auditor
python3 tools/collect_run.py --project ../../projects/manifest_auditor --node audit \
    --out corpus/runs/tz_1
python3 tools/score_audit.py --labels corpus/labels.jsonl --run corpus/runs/tz_1 \
    --baseline corpus/runs/regex_baseline
```

Повторный `map` создаёт следующую версию артефакта у каждого элемента,
`collect_run.py` берёт последнюю — так набираются прогоны для AC-A3.

## Метрики

Модель `deepseek-v4-pro`, `temperature=0`, каталог `injection-patterns.md` v3,
шкала `p0_high`. Пять прогонов по корпусу, `corpus/runs/tz_1..tz_5`,
сырые числа — `corpus/runs/metrics_tz.json`.

| Метрика | Критерий | baseline | Цех (среднее из 5) |
|---|---|---|---|
| precision | ≥ 0.70 | 0.489 | **0.729** |
| recall | ≥ 0.80 | 0.815 | **0.919** |
| тишина на негативах | ≥ 0.90 | 0.645 | **0.987** |
| ст. отклонение recall | ≤ шум выборки (0.079) | — | **0.036** |

Все четыре критерия (AC-A2, AC-A3, AC-A4) выполнены, baseline превзойдён по
обеим метрикам одновременно.

Главный выигрыш над baseline — не recall (его ключевые слова берут почти
даром), а **тишина: 0.987 против 0.645**. Цех молчит на всех трудных
негативах, включая официальный `fetch` («you did not have internet access,
and were advised to refuse») и пометку DEPRECATED, на которых regex шумит.
За пять прогонов шумных негативов всего два: `neg_real_filesystem`
и `neg_postgres`, по одному разу каждый.

**87% ложных срабатываний — не ошибки цеха**: 40 из 46 приходятся на позитивы
и являются находками, реально присутствующими в тексте фикстуры, но не
внесёнными в разметку (размечен только внедрённый паттерн). С
`--lenient-positives` precision составляет 0.93–1.00. Строгая цифра 0.729 —
нижняя оценка; разбор этого расхождения — задача `TSK-2613` плана.

Отдельно измерен вклад каталога: на версии v1 precision была 0.523.
Добавление разделов «Одна находка на один фрагмент» и «Локатор: где именно
находка» подняло её до 0.73 при выросшем recall — правка вики двигает
метрики сильнее правки промпта.

## Отступления от ТЗ

1. **Шкала весов — как в ТЗ (`p0` блокирующий), движок расширен под неё.**
   Остальные цеха фабрики работают в обратной шкале (🔴p3 высший), и
   `review_gate` блокировал по ней жёстко. Добавлено объявление шкалы в
   графе: `"severity_scale": "p0_high"` (умолчание `p3_high`), гейт
   вычисляется по объявленной шкале. Глобальный переворот был отвергнут: у
   девяти существующих цехов промпты написаны в шкале 🔴p3, и блокирующими
   молча стали бы 🟡p1/🟢p0. Измеритель и baseline из
   `materials/security_data` при этом берутся БЕЗ правок.
2. **Корпус реконструирован.** В `materials/security_data` были только
   разметка, измеритель и baseline; самих манифестов и генераторов не было.
   Корпус собран заново по `labels.jsonl` (`corpus/gen_corpus.py`), состав и
   локаторы сверяются автоматически. Baseline на нём даёт precision 0.489 /
   recall 0.815 / тишину 0.645 против 0.512 / 0.815 / 0.677 в README
   исходного корпуса — тот же качественный вывод, но это ДРУГОЙ корпус,
   и абсолютные цифры с исходными не сравнимы.
3. **AC-A3 считается по поправке измерителя**, а не по букве ТЗ: разброс
   сравнивается с шумовым порогом `max(0.05, 1.5σ)`, где σ считается от
   размера корпуса. Обоснование — в `materials/security_data/README.md`.

## Приёмка манифестов (FR-A3)

```bash
python3 tools/accept_manifests.py --run corpus/runs/tz_5 \
    --manifests corpus/manifests --changelog ../../projects/consumer/CHANGELOG.md
```

Элементы с вердиктом READY попадают строками `| файл | роль | sha256[:16] |`
в приёмочную таблицу CHANGELOG цеха-потребителя; NOT_READY печатаются
списком в stderr и не принимаются молча. Расхождение хэша дальше ловит
штатный `python -m workshop verify-acceptance <каталог>` (M-13): правка
манифеста после аудита обнаруживается чекером, а не дисциплиной.
На прогоне `tz_5` принято 42 элемента, отклонено 12.

## Чего в цехе НЕТ

- **Элементов, кроме манифестов.** ТЗ предусматривает системные промпты и
  skill-файлы; формат элемента (`tools/prepare_items.py`) к ним готов,
  корпуса для них нет.
- **Инструмента `audit_manifest` в MCP-сервере** (открытый вопрос №2 ТЗ) —
  только CLI-прогон.
