<!-- stage.openapi.md — карта стадии для artifact_generator.base.md.
     Фрагменты резолвятся в {{NAME}} базы по имени. -->

<!-- @fragment: ARTIFACT -->
openapi.yaml
<!-- @end -->

<!-- @fragment: UPSTREAM_REF -->
contracts.xml@<v>
<!-- @end -->

<!-- @fragment: TECH_MODE -->
PROJECTION
<!-- @end -->

<!-- @fragment: CROSS_LINKS -->
  - каждый path несёт operationId = id операции из contracts.xml
<!-- @end -->

<!-- @fragment: STAGE_RULES -->
- Одна операция → path + метод; WHY для выбора метода (GET/POST) и статусов.
- Абстрактные типы → JSON Schema; ограничения → minLength/minItems/minimum/enum.
- Ошибки → тело {code,message}, code = коды из ERRORS; WHY для маппинга на 4xx/5xx.
<!-- @end -->

<!-- @fragment: PROCESS -->
# детерминированная проекция
3A. Для каждой операции выбери метод/путь, обоснуй WHY.
3B. Спроецируй типы и ограничения в JSON Schema.
3C. Ошибки → HTTP-статусы + тело {code,message}.
<!-- @end -->

<!-- @fragment: SELF_CHECK_EXTRA -->
- Каждая операция contracts.xml имеет endpoint (operationId).
- Каждый код ошибки имеет HTTP-статус.
<!-- @end -->

<!-- @fragment: TRACE_COLUMNS -->
операция → endpoint → статусы
<!-- @end -->
