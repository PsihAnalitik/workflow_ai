<!-- stage.contracts.md — карта стадии для artifact_generator.base.md.
     Фрагменты резолвятся в {{NAME}} базы по имени. -->

<!-- @fragment: ARTIFACT -->
contracts.xml
<!-- @end -->

<!-- @fragment: UPSTREAM_REF -->
domains.xml@<v>
<!-- @end -->

<!-- @fragment: TECH_MODE -->
STRICT
<!-- @end -->

<!-- @fragment: CROSS_LINKS -->
  - каждый <contract domain="D-.."> ссылается на id домена
  - contract-id совпадает с via="C-.." из рёбер domains.xml
  - каждая <operation> несёт <covers>FR-..</covers>
<!-- @end -->

<!-- @fragment: STAGE_RULES -->
- На каждый домен: <contract> с операциями; операция: purpose, covers,
  INPUTS / OUTPUTS / ERRORS, kind.
- Типы из абстрактного словаря: string,int,bool,list<T>,optional<T>,enum{},record.
- ОШИБКИ = варианты возврата (Result), НЕ исключения; каждая достижима входом.
- <consumes> = контракты входящих рёбер домена.
<!-- @end -->

<!-- @fragment: PROCESS -->
# детерминированная проекция + внутренний мысленный тест
2A. Для каждого домена выпиши операции из его ответственности/covers.
2B. Заполни INPUTS/OUTPUTS/ERRORS + типы.
2C. (черновик) мысленный тест: подбери вход на КАЖДУЮ ошибку из ERRORS; проверь,
    что все выходные поля производятся (нет висящих значений).
    Недостижимая ошибка → удали или поправь контракт.
<!-- @end -->

<!-- @fragment: SELF_CHECK_EXTRA -->
- Каждое via из domains.xml имеет контракт.
- Каждая ошибка ERRORS достижима конкретным входом.
<!-- @end -->

<!-- @fragment: TRACE_COLUMNS -->
FR-id → домен → операция
<!-- @end -->
