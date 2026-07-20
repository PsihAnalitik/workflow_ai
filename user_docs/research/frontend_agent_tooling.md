# Исследование: open-source инструментарий для фидбэк-лупа frontend-агента

Дата: 20.07.2026. Метод: harness deep-research, два прогона (108 + 105 агентов,
48 источников, 231 утверждение → 42 проверено адверсариально, 8 убито).
Под задачу: цех `frontend_site` (витрина на Django Templates + HTMX/Alpine,
темизация через CSS-токены), см. `user_docs/TZ_frontend_site_factory.md`.

Статус: **черновик к обсуждению**. Решение build-vs-buy по `a11y_lint` и
`seo_lint` НЕ принято — см. §5.

---

## 1. Главная разделяющая линия: нужен ли живой браузер

Ограничение G5 нашей песочницы — один docker-образ, без сети и без compose.
Исследование подтверждает (голосование 2-1 и 3-0): **любой сигнал от настоящего
рендера требует бинарника Chrome/Chromium плюс Node**. Это относится к
Playwright MCP, chrome-devtools-mcp, BackstopJS и вообще к любому скриншоту.

| слой | что можно | где живёт |
|---|---|---|
| офлайн, без браузера | stylelint-плагины, regex-линтеры, сверка контрактов, пиксельный дифф готовых картинок | внутри песочницы, `test_command` codegen-узлов |
| нужен браузер | a11y-снимок, консоль, сеть, скриншоты, Lighthouse, визуальная регрессия | ручной / CI-гейт снаружи |
| нужна сеть + аккаунт | Figma MCP (любой), design-to-code | pre-fetch шаг до генерации |

**Открытый вопрос №1 (решающий):** можно ли запечь Chromium в образ песочницы?
Если да — `mcr.microsoft.com/playwright/mcp` работает офлайн и весь луп
(a11y-снимок, консоль, сеть, скриншот, дифф) переезжает внутрь. Один этот ответ
переставляет всю расстановку ниже.

---

## 2. Что заимствовать вместо самописного

### token_lint → `stylelint-declaration-strict-value` (MIT)

`AndyOGo/stylelint-declaration-strict-value`, v1.11.1 от 24.02.2026, peerDeps
stylelint >=16 <=17. **Внимание:** адрес `stylelint-scss/*` — ошибка, 404.

Делает ровно нашу задачу: требует `var()` / функции / allowlist ключевых слов
вместо литеральных цветов и размеров, таргетинг свойств по имени или regex
(`/color$/` ловит `color`, `background-color`, `border-color`; regex обязан быть
в слешах). Офлайн, без браузера, JSON через `stylelint --formatter json`.

**Но:** stylelint видит только `.css`/`.scss`. Литералы внутри Django-шаблонов
(`style=""`, инлайновый `<style>`, классы от HTMX/Alpine) он не поймает —
извлекатель из шаблонов писать в любом случае. Это открытый вопрос №3.

### Пиксельный дифф → `reg-cli` / `reg-suit` (MIT)

`reg-viz/reg-suit`, v0.14.6 от 16.03.2026, коммиты в пределах дней. Работает
офлайн, но **сам скриншоты не снимает** — только сравнивает готовые (у них для
захвата отдельный `storycap`). `core.ximgdiff` даёт структурный дифф, не наивный
попиксельный. Утверждение «у reg-suit нет JSON» опровергнуто 0-3 — JSON есть,
точный флаг не уточнён.

### template_contract_lint → прецедент не найден

Ничего в проверенном наборе не решает сверку ключей контекста шаблона с
контрактом. Целевой поиск (`djlint`, `curlylint`, `django-template-check`) не
запускался — возможно, это не самописная территория. Открытый вопрос №4.

---

## 3. Образцы организации фидбэк-лупа

### screenshot-to-code (MIT, `abi/screenshot-to-code`) — единственный, кто замыкает луп

Коммиты от 20.07.2026, 73.4k звёзд. Дословно из README:

> Screenshot preview (optional) lets the agent render its own generated page in a
> headless browser and visually check its work. It's enabled automatically once
> Chromium is installed… If Chromium is missing, the app just skips the tool.

Это агент с браузерным инструментом самопроверки, а не одноразовая генерация.
Прямого пиксельного диффа с исходником README не декларирует.

**Прямая связь с нашим M-25** (`.grace/DevelopmentPlan.xml` v11,
`browser_screenshot`): архитектура совпадает. Механику «инструмент опционален и
сам себя отключает при отсутствии Chromium» стоит скопировать буквально.

### OpenUI (Apache-2.0, `wandb/openui`) — образец методики, не рантайма

В рантайме цикл НЕ замыкает: генерирует HTML, рендерит превью **для человека**,
правки идут диалогом. Ценное — офлайн-харнесс `backend/openui/eval/`:
генерация HTML → playwright-скриншоты (light/dark × desktop/mobile) →
vision-модель как судья (`EvaluateQualityModel`) → логирование в W&B Weave,
плюс `promptsearch.py` (подбор промпта по оценкам).

Это ближе к нашему `judge`-гейту, чем к рантайму. Матрица
light/dark × desktop/mobile — прямая подсказка под нашу темизацию.

### WebGen-Agent (arXiv 2509.22644) и ReLook (ACL 2026)

WebGen-Agent: VLM оценивает скриншоты и прогоны GUI-агента, текстовая критика +
числовые оценки уходят обратно в доработку, плюс backtracking и select-best.

ReLook — одно переносимое правило: **нулевая награда за невалидный рендер**
якорит луп и блокирует reward hacking. Для нас: дешёвые детерминированные гейты
(`token_lint`, `template_contract_lint`, `seo_lint`, `a11y_lint`) идут **перед**
любым LLM-судьёй визуала. Оговорка: у ReLook это training-time RL-награда, не
inference-time стадия; распространение на lint-гейты — наша экстраполяция.

---

## 4. Браузерные MCP и вопрос «скриншот vs a11y-снимок»

**Playwright MCP** (Apache-2.0): основной сигнал — текстовый a11y-снимок
(«No vision models needed», «Deterministic tool application»), координатные и
vision-инструменты спрятаны за `--caps=vision` (ровно 6 мышиных инструментов).
`browser_take_screenshot` есть, но помечен «You can't perform actions based on
the screenshot». Даёт: a11y-снимок, скриншот, все console-сообщения, список и
детализацию сетевых запросов. Это a11y-дерево, **не** сырой DOM.

**chrome-devtools-mcp** (Apache-2.0, Google): богаче — ~50 инструментов, включая
скриншоты (png/jpeg/webp), a11y-снимки, консоль со source-mapped стектрейсами,
сеть, перф-трейсы и `lighthouse_audit`. Число инструментов дрейфует от релиза к
релизу — не фиксировать в документации точной цифрой.

**Важно:** тезис «для семантической разметки a11y-снимка достаточно, vision не
нужен» **опровергнут 3-0**. Не переносить как факт.

---

## 5. Отвергнутые и незакрытое

| проект | вердикт |
|---|---|
| Figma MCP официальный | **не брать**: remote требует OAuth и клиента из их каталога; local — GUI Figma Desktop + платное Dev/Full-место; квота 6 вызовов/мес на бесплатных местах. `get_variable_defs` схлопывает алиасы и отдаёт только default-режим → матрицу light/dark токенов не построить. Beta 13 месяцев, инструменты дважды переименовывались |
| Framelink Figma-Context-MCP | MIT, v0.13.2 от 18.06.2026, живой; без seat-гейта, контейнеризуем. Предпочтительнее официального, но тоже только pre-fetch снаружи |
| Lost Pixel | **мёртв**: архивирован 22.04.2026, последний коммит «Lost Pixel team is joining Figma», README открывается баннером про sunset. MIT не менялась — читать код можно, брать в зависимости нельзя |
| BackstopJS | MIT, JSON-репорт (`"report": ["json"]` → `backstop_data/json_report`), официальный образ `backstopjs/backstopjs`. **Заморожен**: npm 6.3.25 от 07.09.2024, ~22 месяца тишины. Требует headless Chrome. Если нужен дифф — `reg-cli` живее |

### НЕ проверено (главная дыра)

`axe-core`, `pa11y`, Lighthouse CI, `html-validate`, валидаторы дизайн-токенов
(Style Dictionary). Это ~три четверти вопроса про детерминированные чекеры.
**Решение build-vs-buy по `a11y_lint` и `seo_lint` остаётся открытым.**
Гипотеза харнесса: axe-core и Lighthouse требуют DOM/браузер, `html-validate` —
чистый Node и, возможно, единственный кандидат в безбраузерный гейт.

---

## 6. Открытые вопросы (порядок = приоритет)

1. Можно ли запечь Chromium в образ песочницы? Переставляет всё остальное.
2. Какие из `axe-core` / `pa11y` / Lighthouse CI / `html-validate` дают чистый
   JSON и работают без браузера? — третий прогон исследования.
3. Как `token_lint` покроет литералы внутри Django-шаблонов?
4. Есть ли open-source прецедент для `template_contract_lint`
   (`djlint`, `curlylint`, `django-template-check`)?

## 7. Оговорки к достоверности

Утверждения по браузерным MCP, Figma и Framelink прошли трёхголосую
адверсариальную верификацию. По BackstopJS, Lost Pixel, OpenUI и
screenshot-to-code — проверка первоисточников (GitHub REST API, npm registry,
сырые README и исходники) **одноголосая**.

У OpenUI и screenshot-to-code нет релизов — заимствовать, пинуя коммит.
Time-sensitivity высокая: Figma MCP в beta и объявлен будущей платной
usage-based фичей; состав инструментов chrome-devtools-mcp дрейфует.
