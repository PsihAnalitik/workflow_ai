# wiki: pilot-workflow-ai (v1)

Пилот `.workflow_ai` в проекте smart-assistant — фабрика, встроенная внутрь
чужого проекта. Все пути фабрики (`configs/`, `wiki/`, `projects/`)
относительны к рабочей директории, поэтому `.workflow_ai/` как «фабричный
корень» внутри smart-assistant работает из коробки.

## Структура

```
smart-assistant/.workflow_ai/
├── configs/         # конфиги цехов prompt_roaster и table_roaster
├── wiki/            # методология прожарки (реплика из фабрики)
├── projects/        # результаты прогонов
│   ├── prompt_roaster/map/summary.md
│   └── table_validator/map/summary.md
├── Makefile         # roast-prompts, roast-tables, PYTHONPATH
└── .gitignore       # журналы прогонов и .env не коммитятся
```

## Интеграция

- Пакет `workshop` не установлен в venv — работает из корня репо через
  `PYTHONPATH` в Makefile: `cd .workflow_ai && PYTHONPATH=<workflow_ai> python -m workshop map ...`
- `.env` — `WORKSHOP_DB_DSN` для db_query; лежит в `.gitignore`, никогда
  не коммитится.
- Журналы прогонов (`projects/*/runs/`, `projects/*/map/`) и материалы
  smart-assistant (промпты, schema.yaml) — в `.gitignore`: чужой проект,
  на публичном GitHub не место.

## Извлечённые уроки

1. **Правила ревью без негативного случая:** R3 зациклилось на 4 промптах,
   пока не добавили негативный пример; V3 зациклилось на таблице, пока не
   ввели белый список локаций — «браковать можно только локации,
   не ссылающиеся на данные вовсе».
2. **Шаблоны эталонов с краевыми случаями:** при усечённом эталоне (топ-10
   ключей) T1 выдал 231 ложную находку — переделали на полный перечень.
3. **Батчинг — на уровне драйвера, не FSM:** map-драйвер гоняет элементы
   независимо; батчи внутри одного прогона оказались не нужны — независимость
   элементов достаточна для параллелизма.

## related

- [methodology](index.md) — методология фабрики
- [tech-selection](tech-selection.md) — технические решения фабрики
