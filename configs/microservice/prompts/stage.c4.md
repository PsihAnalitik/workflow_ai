<!-- stage.c4.md — карта стадии developmentplan (C4) цеха «микросервис»
     для artifact_generator.base.md. Вход узла — contracts.xml + openapi.yaml (конкатенация). -->

<!-- @fragment: ARTIFACT -->
developmentplan.xml
<!-- @end -->

<!-- @fragment: UPSTREAM_REF -->
contracts.xml@<v>, openapi.yaml@<v>
<!-- @end -->

<!-- @fragment: TECH_MODE -->
PROJECTION
<!-- @end -->

<!-- @fragment: CROSS_LINKS -->
  - каждый <module> несёт implements="OP-.." (или implements="rest" для API-биндинга)
  - каждый endpoint из openapi.yaml присутствует в <rest_binding> с его operationId
<!-- @end -->

<!-- @fragment: STAGE_RULES -->
Структура developmentplan.xml:
- <technology>: Python 3.14; разрешённые библиотеки: stdlib, fastapi,
  pymorphy3 (морфология RU), httpx (только тесты). Никакой сети и внешних хранилищ
  в рантайме — данные in-memory (NFR офлайн/детерминизм).
- <modules>: на каждую операцию контракта — модуль ядра; плюс один модуль
  implements="rest" (FastAPI-биндинг). У каждого модуля: file, responsibility,
  <io> (INPUTS/OUTPUTS/ERRORS из контракта; ошибки — явные возвраты, не исключения),
  <algorithm> (пронумерованные шаги), <tests> (happy + краевые + каждая ошибка контракта).
- <rest_binding>: endpoint → operationId → модуль, ровно по openapi.yaml.
- <run>: команда запуска сервиса и команда тестов.
<!-- @end -->

<!-- @fragment: PROCESS -->
# детерминированная проекция контрактов в план реализации
4A. Выпиши все операции контрактов; каждой назначь модуль ядра и файл.
4B. Для каждого модуля разверни алгоритм по шагам, учитывая NFR старших документов
    (латентность → предвычисление/кэш; детерминизм → без случайности и сети).
4C. Составь <rest_binding> строго по openapi.yaml (каждый operationId ровно один раз).
4D. Заполни <tests> так, чтобы каждая ошибка каждого контракта была достижима тестом.
<!-- @end -->

<!-- @fragment: SELF_CHECK_EXTRA -->
- Каждая операция контрактов имеет модуль ядра и тест-требования.
- Каждый endpoint openapi присутствует в rest_binding; лишних endpoint'ов нет.
- В <technology> нет библиотек вне разрешённого списка.
<!-- @end -->

<!-- @fragment: TRACE_COLUMNS -->
OP-id → модуль (файл) → endpoint → тесты
<!-- @end -->
