<!-- stage.analysis_spec.md — карта стадии «постановщик ТЗ» цеха data-аналитик
     для artifact_generator.base.md. Фрагменты резолвятся в {{NAME}} базы по имени. -->

<!-- @fragment: ARTIFACT -->
analysis_spec.xml
<!-- @end -->

<!-- @fragment: UPSTREAM_REF -->
input@<v>
<!-- @end -->

<!-- @fragment: TECH_MODE -->
STRICT
<!-- @end -->

<!-- @fragment: CROSS_LINKS -->
  - каждый <fr> несёт covers="G-.." на реальную цель
  - каждый <module> несёт <covers>FR-..</covers>; каждый FR закрыт ≥1 модулем
<!-- @end -->

<!-- @fragment: STAGE_RULES -->
Структура analysis_spec.xml (по порядку):
- <source_request> — запрос пользователя ВЕРБАТИМ из input (ревью и judge читают только артефакт).
- <dataset_summary> — колонки/типы/пропуски из профиля input, только используемые в FR.
- <goals> — цели G-NN: что пользователь получит и как применит.
- <functional> — <fr id="FR-NN" covers="G-.." priority="must|should"> с указанием колонок.
- <modules> — <module id="MOD-NN">: ОДНА ответственность; <io> INPUTS/OUTPUTS с типами;
  ERRORS = варианты возврата (не исключения).
- <acceptance> — на каждый FR один проверяемый критерий (число/условие, не «корректно работает»).
<!-- @end -->

<!-- @fragment: PROCESS -->
# детерминированная проекция запроса в ТЗ
1A. Скопируй запрос в <source_request>; выпиши из профиля колонки в <dataset_summary>.
1B. Сформулируй цели G-NN. ЕСЛИ цель требует данных, которых нет в профиле
    (нет колонки / все значения пусты) → NEEDS_CLARIFICATION (по U5), не выдумывай.
1C. Спроецируй цели в FR-NN, каждому — конкретные колонки датасета.
1D. Разбей на модули MOD-NN: независимо тестируемые, io без глобального состояния.
1E. Заполни <acceptance> на каждый FR.
<!-- @end -->

<!-- @fragment: SELF_CHECK_EXTRA -->
- Каждый FR ссылается только на колонки, присутствующие в <dataset_summary>.
- Каждый MOD закрывает ≥1 FR; нет модуля «на будущее».
- У каждого FR есть acceptance-критерий с числом или проверяемым условием.
<!-- @end -->

<!-- @fragment: TRACE_COLUMNS -->
G-id → FR-id → модуль → колонки датасета
<!-- @end -->
