# ТЗ: цех «frontend_site» (фабрика витрины портфолио-платформы)

Статус: черновик к утверждению. Версия 1 от 20.07.2026.
Контекст: производный документ от промпта заказчика «Портфолио-платформа (Django + PostgreSQL)».
Здесь описан **только frontend-скоуп** (витрина, темизация, виджет чата) и **то, как этот скоуп
производится фабрикой** — граф узлов, артефакты, гейты, песочница.

---

## 0. Зачем отдельный цех

Существующий цех `configs/microservice` производит **Python-ядро + FastAPI-биндинг**:

- `codegen.base.md` прямо предписывает FastAPI, in-memory данные, запрет сети и ФС;
- проверка = `python -m pytest -q` в одном docker-образе без сети, БД и compose;
- артефакты (`domains → contracts → openapi → c4`) описывают серверные операции, а не страницы,
  шаблоны, компоненты и дизайн-токены.

Витрина на Django Templates + HTMX/Alpine с темизацией через CSS-токены **не выражается** в этих
артефактах: у неё другой предмет (маршрут → шаблон → компонент → токен), другой критерий приёмки
(рендер, семантика, a11y/SEO, отсутствие захардкоженных значений) и другой рантайм (Django + БД).
Поэтому — отдельный цех, а не ветка microservice.

Разделение зон:

| Что | Чей цех |
|---|---|
| модели, миграции, storage, Celery, ai_assist, эндпоинты чата | `microservice` (или новый `django_backend`) |
| маршруты, view→шаблон, шаблоны/партиалы, тема, токены, статика, виджет чата (UI), SEO-разметка | **`frontend_site`** (этот документ) |
| сборка сайта + db/redis/minio в один compose | `products` (см. гэп G8) |

---

## 1. Вход цеха

**Материал:** `requirements.ui.xml` — frontend-подмножество требований (пишется человеком,
как и для microservice; узла-генератора требований в фабрике нет — см. G1).

Обязательные разделы материала:

- `<scope>`: витрина + тема; вне скоупа — админка, Celery, импортёр, LLM-провайдер.
- `<functional>`: FR со сквозными id (см. §5 — стартовый набор FR-U01…FR-U14).
- `<nonfunctional>`: NFR на Lighthouse (Perf ≥ 90, SEO ≥ 95, A11y ≥ 90 mobile),
  «ноль захардкоженных цветов/шрифтов/радиусов/отступов вне tokens.css»,
  «сайт работает при выключенном JS в части навигации и просмотра кейсов».
- `<fixed_decisions>`: Django Templates + HTMX/Alpine, без SPA/React/Vue; токены;
  `data-theme` на `<html>`; медиа только через Storage API (в шаблонах — только `{{ obj.file.url }}`
  / `srcset`, никаких путей ФС).
- `<data_read_model>`: какие поля моделей доступны шаблонам (контракт с backend-цехом).

---

## 2. Артефакты и граф узлов

```
input(requirements.ui.xml)
        │
        ▼
   ia (ia.xml) ────────────┐
        │                  │
        ▼                  ▼
 components (components.xml)   theme (theme.xml)
        │                  │
        └────────┬─────────┘
                 ▼
        view_contracts (view_contracts.xml)
                 ▼
         tech_selection (tech.xml)
                 ▼
        plan (developmentplan.ui.xml)
                 ▼
    codegen_theme → codegen_templates → codegen_views
                 ▼
             ui_lint (детерминированный гейт)
```

Все узлы, кроме codegen-узлов, — `kind: workshop` с `gates.hitl: true`.
Codegen-узлы — `kind: codegen` с `judge_config_path`.

### 2.1. `ia` → `ia.xml` (информационная архитектура)

PURPOSE: перечислить страницы сайта, их URL, источник данных, состояния.
INPUTS: `requirements.ui.xml@<v>`.
OUTPUTS: `<page id="PG-.." url slug template>` c элементами:
`covers` (FR-id), `data` (какие объекты read-model нужны), `states` (ok/empty/error/404),
`seo` (title/description/og/schema.org-тип), `partials` (какие HTMX-фрагменты страница подгружает).
ERRORS: `FR_NOT_COVERED` (FR без страницы), `URL_COLLISION`, `PAGE_WITHOUT_STATES`.
CROSS_LINKS: каждый FR закрыт ≥1 `<page>`; каждый `partial` ссылается на id из `view_contracts`.

### 2.2. `components` → `components.xml` (библиотека компонентов темы)

PURPOSE: зафиксировать компоненты (карточка кейса, галерея/лайтбокс, фильтр категорий, шапка,
футер, виджет чата) как контракты шаблонов-партиалов.
OUTPUTS: `<component id="CMP-.." template="…">` с `props` (имя+тип+обязательность),
`slots`, `states`, `interactions` (HTMX: триггер, целевой URL-id, swap; Alpine: локальное состояние),
`tokens_used` (список токенов), `a11y` (роль, aria-атрибуты, фокус-ловушка для лайтбокса/виджета).
ERRORS: `PROP_UNTYPED`, `INTERACTION_WITHOUT_ENDPOINT`, `TOKEN_NOT_DECLARED`, `A11Y_UNDEFINED`.

### 2.3. `theme` → `theme.xml` (контракт темы)

PURPOSE: полный реестр дизайн-токенов и структуры каталога темы.
OUTPUTS: `<tokens>` (имя, категория color|type|space|radius|shadow|motion, значение light,
значение dark, где используется), `<theme_json>` (схема `theme.json`),
`<layout>` (`themes/<name>/{tokens.css,templates/,static/,theme.json}`),
`<override_rules>` — что тема **может** переопределять и что ей запрещено (бизнес-логику, URL-схему).
ERRORS: `TOKEN_DUPLICATE`, `TOKEN_UNUSED`, `DARK_VALUE_MISSING`, `HARDCODED_IN_CONTRACT`.
CROSS_LINKS: объединение `tokens_used` из `components.xml` ⊆ `<tokens>` (проверяется механически, §4).

### 2.4. `view_contracts` → `view_contracts.xml`

PURPOSE: контракт «URL → view → контекст шаблона» + внутренние HTMX-эндпоинты (партиалы, чат-виджет).
OUTPUTS: на каждый endpoint — `method`, `url_pattern`, `name`, `INPUTS` (path/query/POST-поля с типами),
`OUTPUTS` (имя шаблона + ключи контекста с типами), `ERRORS` (404 / 400 / 429 / degraded-fallback),
`auth` (public|staff), `covers`.
ERRORS: `CONTEXT_KEY_UNUSED_BY_TEMPLATE`, `PARTIAL_WITHOUT_PAGE`, `PUBLIC_ENDPOINT_WITHOUT_RATE_LIMIT`
(для чат-эндпоинта), `DRAFT_LEAK` (в контракте страницы допускается объект со статусом draft).
Замечание: это **замена узла `openapi`** для витрины — REST-схема здесь не предмет.

### 2.5. `tech_selection` → `tech.xml`

Как в microservice, но словарь ограничен `fixed_decisions`: Django 5.x, django-htmx (опц.), Alpine.js,
Pillow-производные — уже на стороне backend-цеха. Узел решает только версии и набор
шаблонных тегов/фильтров + wiki-refs, которые попадут в codegen (`wiki_refs_from: tech_selection`).
Требуется страница вики `wiki/python/django/index.md` (см. G3).

### 2.6. `plan` → `developmentplan.ui.xml`

Как `c4` в microservice, но со стадийной картой `stage.c4.frontend.md`:
`<templates>` (файл → компоненты → контекст), `<static>` (css/js), `<view_binding>` (endpoint → view-функция),
`<tests>` (какие проверки на каждый шаблон), `<theme_files>`.
Обязателен мысленный тест (раздел 4a.3 глобальных правил) по каждому `<page>`:
запрос → view → контекст → рендер → видимые элементы.

### 2.7. Codegen-узлы (три, не один)

Один codegen-узел выдаёт **один file map** — вся тема + все шаблоны + все views в одну генерацию
не поместятся (G6). Разбиение:

| Узел | Что генерирует | test_command |
|---|---|---|
| `codegen_theme` | `themes/default/{tokens.css,theme.json,static/*}` | `python tools/token_lint.py` |
| `codegen_templates` | `templates/**/*.html` + партиалы компонентов | `python -m pytest -q tests/render` |
| `codegen_views` | `views.py`, `urls.py`, тесты рендера | `python -m pytest -q` |

Каждый — со своим `codegen.base.frontend.md`, где вместо FastAPI-правил:
шаблоны наследуются от `base.html`; значения оформления только `var(--token)`;
изображения только через `{{ obj.file.url }}`/`srcset`; каждый интерактив — HTMX-атрибуты
из `interactions` компонента; тесты — `pytest-django` + `django.test.Client`, БД = sqlite in-memory.

### 2.8. `ui_lint` — детерминированный гейт (не LLM)

Скрипты в образе песочницы, падение = красный `test_command`:

1. `token_lint` — regex по `themes/**/*.css` и шаблонам: литеральные `#rrggbb|rgb(|hsl(|px|rem`
   вне `tokens.css` → дефект (правило `coding_rules.2` заказчика).
2. `template_contract_lint` — каждый ключ контекста из `view_contracts.xml` встречается в шаблоне;
   каждая `{{ var }}` объявлена в контракте.
3. `seo_lint` — на каждой странице из `ia.xml`: `<title>`, meta description, OG-теги,
   JSON-LD нужного типа, canonical.
4. `a11y_lint` — `alt` у каждого `<img>`, `lang` у `<html>`, у интерактивных элементов —
   доступное имя, порядок заголовков без пропусков.

Lighthouse **вне** песочницы (нужен браузер и живой стек) → ручной HITL-гейт с приложенным отчётом.

---

## 3. Гейты и приёмка

- HITL на каждом артефактном узле (как в microservice).
- `judge`-гейт на codegen-узлах.
- Финальная приёмка цеха: зелёный `ui_lint` + отчёт Lighthouse (mobile) от человека
  + сценарий «новый дизайнер»: копия темы `default` с изменённым `tokens.css` меняет вид
  без правки шаблонов движка.
- Приёмочная таблица sha256 в `configs/frontend_site/CHANGELOG.md` (механизм `workshop/acceptance.py`).

---

## 4. Аудит достаточности цехов и артефактов

Проверено по коду фабрики (`workshop/models.py`, `orchestrator.py`, `codegen_loop.py`,
`sandbox.py`, `packager.py`, `map_driver.py`, `configs/microservice/*`).

| # | Гэп | Влияние | Решение |
|---|---|---|---|
| G1 | Нет узла генерации `requirements.xml` — вход пишется человеком | ТЗ фронта надо составить вручную (§5) | принять как есть; опционально — узел `requirements` в отдельном цехе |
| G2 | `contracts`/`openapi` не описывают страницы, компоненты, токены | без них codegen лишён «чертежа» витрины | новые артефакты `ia/components/theme/view_contracts` (§2) |
| G3 | `stage.c4.md` и wiki-refs заточены под Python-модули; нет `wiki/python/django/` | план получится «модульным», а не шаблонным | `stage.c4.frontend.md` + страница вики по Django/HTMX (через цех `wiki_maintainer`) |
| G4 | `codegen.base.md` предписывает FastAPI, запрещает ФС и сеть, данные in-memory | Django-код не сгенерируется корректно | `codegen.base.frontend.md` (§2.7) |
| G5 | Песочница = **один** образ, без сети и compose (`sandbox.run_in_docker`) | нельзя гонять Postgres/pgvector/Redis/MinIO и Lighthouse | тесты фронта на sqlite + `locmem` + dummy-storage; интеграция и Lighthouse — вне песочницы, ручной гейт. Расширение sandbox до compose — отдельная задача ядра, **в этот скоуп не входит** |
| G6 | Один codegen-узел = один file map | вся витрина не влезает в одну генерацию | три codegen-узла (§2.7); при росте числа страниц — `map_driver` по элементам `ia.xml` |
| G7 | Нет детерминированных чекеров качества разметки/токенов | правила «только var(--token)», SEO, a11y останутся на совести LLM | узел `ui_lint` + скрипты в образе (§2.8) |
| G8 | `ProductSpec.ServiceSpec` требует `package` (собранный пакет цеха) — нельзя добавить в compose готовый образ `postgres:16`/`redis`/`minio` | продукт «сайт целиком» не собирается фабрикой | либо расширить `ServiceSpec` полем `image` (правка ядра, отдельная задача), либо compose писать вручную в фазе 7 |
| G9 | `PackageSpec.serve` = одна команда, один образ | Django+worker+beat в одном пакете не выражаются | пакет цеха = `gunicorn`; worker/beat — на уровне продукта (см. G8) |
| G10 | Нет цеха/узла под миграции и модели Django | frontend-цех зависит от read-model, которой никто не производит | завести цех `django_backend` (модели/миграции/админка/Celery/ai_assist) **до** frontend_site; его `contracts.xml` = источник `<data_read_model>` |

**Вывод:** для разработки витрины существующих цехов и артефактов **недостаточно**.
Минимально необходимо: G2, G4, G6, G7 (внутри нового цеха — правки только в `configs/`),
плюс входной артефакт из G10. G5, G8, G9 — ограничения ядра; принимаются как ручные шаги,
их устранение оформляется отдельным ТЗ на `workshop/*`.

---

## 5. Frontend-скоуп: стартовый список FR (материал цеха)

Витрина:
- FR-U01 Главная: герой (SiteProfile), сетка опубликованных кейсов, фильтр по категориям.
- FR-U02 Страница кейса: обложка, галерея (ProjectImage по `order`), описание, теги, соседние кейсы.
- FR-U03 Лайтбокс галереи: клавиатура (←/→/Esc), фокус-ловушка, без потери позиции скролла.
- FR-U04 Страница «Обо мне»: био, клиенты, соцссылки.
- FR-U05 Страница «Контакты»: способы связи, без формы сбора ПД (или с явным согласием).
- FR-U06 Фильтрация по категориям без перезагрузки (HTMX-партиал), с рабочим fallback по ссылке.
- FR-U07 Изображения: `srcset` 480/960/1920 + WebP, `loading="lazy"`, фиксированные размеры (CLS).
- FR-U08 SEO: ЧПУ, meta title/description, OG, JSON-LD `Person` и `CreativeWork`, canonical, `sitemap.xml`, `robots.txt`.
- FR-U09 404 и пустые состояния (нет кейсов / нет кейсов в категории).
- FR-U10 Тёмная/светлая тема через `data-theme`, переключатель с запоминанием выбора.

Виджет чата (UI-часть; серверная логика — backend-цех):
- FR-U11 Кнопка в углу, диалоговое окно, история в рамках сессии, состояния: печатает / ошибка / лимит (429).
- FR-U12 При недоступности провайдера виджет заменяется ссылкой на страницу контактов.
- FR-U13 Оформление виджета — только через токены темы (виджет входит в тему).

Передача:
- FR-U14 `/styleguide/` (staff/DEBUG): все токены и все компоненты из `components.xml` со всеми состояниями.

NFR: Lighthouse mobile Perf ≥ 90 / SEO ≥ 95 / A11y ≥ 90; ноль захардкоженных значений оформления;
навигация и просмотр кейсов работают без JS.

---

## 6. План внедрения

1. `configs/frontend_site/{graph.json,models.json,nodes/*,prompts/*,sandbox.Dockerfile,CHANGELOG.md}`
   → verify: `uv run python -m workshop --help` и загрузка конфига без ошибок валидации (`config_loader`).
2. Образ песочницы: `python:3.14-slim` + `django`, `pytest`, `pytest-django`, скрипты `tools/*_lint.py`
   → verify: `docker build` + прогон линтеров на заведомо «грязном» примере (ожидаем красный).
3. Материал `requirements.ui.xml` по §5 → verify: HITL-приёмка узла `ia` без `FR_NOT_COVERED`.
4. Прогон цеха до `plan` → verify: мысленные тесты по каждой `<page>` пройдены, HITL-приёмка.
5. Codegen-узлы по очереди → verify: зелёные `test_command`, judge-гейт.
6. Сценарий «новый дизайнер» + Lighthouse → verify: ручной гейт, отчёт в CHANGELOG.

---

## 7. Открытые вопросы к заказчику

1. Порядок цехов: сначала `django_backend` (модели/миграции), затем `frontend_site`? Иначе
   `<data_read_model>` придётся фиксировать вручную и синхронизировать позже.
2. G8/G9 (compose со сторонними образами, worker/beat): править ядро `workshop/*` в этом же
   заходе или собрать compose вручную на фазе 7?
3. Мультиязычность витрины: в скоупе FR-U* её нет — подтвердить, что сайт одноязычный.
