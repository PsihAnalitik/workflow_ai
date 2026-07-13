<!-- stage.domains.md — карта стадии для artifact_generator.base.md.
     Фрагменты резолвятся в {{NAME}} базы по имени. -->

<!-- @fragment: ARTIFACT -->
domains.xml
<!-- @end -->

<!-- @fragment: UPSTREAM_REF -->
requirements.xml@<v>
<!-- @end -->

<!-- @fragment: TECH_MODE -->
STRICT
<!-- @end -->

<!-- @fragment: CROSS_LINKS -->
  - каждый <domain> несёт <covers>FR-..</covers> на реальные FR-id из requirements
<!-- @end -->

<!-- @fragment: STAGE_RULES -->
- Элементы домена: responsibility, covers, ubiquitous_language, owns, emits.
- <relationships>: рёбра from→to (from ЗАВИСИТ от контракта to), kind=sync|async,
  via="C-.." (id будущего контракта), data. Один домен → <relationships/>.
<!-- @end -->

<!-- @fragment: PROCESS -->
# отложенный коллапс — декомпозиция это поиск
1A. Перечисли 2–3 варианта разбиения на bounded contexts, НЕ выбирая;
    для каждого укажи признак границы (единый язык / владение данными / независимость).
1B. Выбери разбиение с макс. автономностью и мин. связанностью;
    в WHY у <domains> объясни, почему отвергнуты альтернативы.
1C. Заполни домены (элементы из STAGE_RULES).
1D. Построй <relationships>.
<!-- @end -->

<!-- @fragment: SELF_CHECK_EXTRA -->
- Каждый FR закрыт ≥1 доменом.
- Каждое via="C-.." непротиворечиво зарезервировано под будущий контракт.
<!-- @end -->

<!-- @fragment: TRACE_COLUMNS -->
FR-id → домен
<!-- @end -->
