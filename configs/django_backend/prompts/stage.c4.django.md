<!-- stage.c4.django.md — карта стадии developmentplan цеха «django_backend»
     для artifact_generator.base.md. Вход узла — contracts.xml.
     WHY отдельная карта: стек зафиксирован заказчиком (Django/PostgreSQL), в каталоге
     wiki его нет → узел tech_selection в графе выключен, технология объявлена здесь. -->

<!-- @fragment: ARTIFACT -->
developmentplan.xml
<!-- @end -->

<!-- @fragment: UPSTREAM_REF -->
contracts.xml@<v>
<!-- @end -->

<!-- @fragment: TECH_MODE -->
PROJECTION
<!-- @end -->

<!-- @fragment: CROSS_LINKS -->
  - каждый <module> несёт implements="OP-.." (или implements="model" для слоя моделей)
  - каждое поле <read_model> прослеживается до поля модели из <models>
  - каждая операция контрактов присутствует ровно в одном <module>
<!-- @end -->

<!-- @fragment: STAGE_RULES -->
Структура developmentplan.xml:
- <technology>: Python 3.14, Django 5.x, PostgreSQL 16, django-storages (медиа).
  Никаких иных библиотек. Фоновые задачи, кэш, поиск — вне модуля.
- <models>: на каждую сущность контрактов — модель Django: name, table, поля
  (имя, тип поля Django, null/blank, default, unique, index), связи (FK/M2M + on_delete),
  Meta (ordering, constraints), инварианты (например «ровно одна запись профиля»).
  Медиа-поля — ImageField/FileField через storage по умолчанию; путь ФС не хардкодится.
- <queries>: на каждую операцию выдачи — менеджер/queryset-метод: имя, фильтры,
  сортировка, select_related/prefetch_related (NFR N+1), гарантия status=published.
- <read_model>: КОНТРАКТ С ВИТРИНОЙ. На каждую операцию выдачи — плоский набор полей,
  доступных шаблону: имя ключа, тип, источник (модель.поле или вычисление),
  признак optional. Медиа-поля — только как URL хранилища. Черновики и служебные
  поля (внутренние id, флаги модерации, embedding) в read_model НЕ попадают.
- <modules>: file, responsibility, <io> (INPUTS/OUTPUTS/ERRORS из контракта; ошибки —
  явные возвраты, не исключения), <algorithm> (пронумерованные шаги), <tests>.
- <admin>: какие модели регистрируются в админке, какие поля редактируются,
  какие действия (публикация, изменение порядка).
- <migrations>: порядок создания таблиц и ограничений.
- <run>: команда миграций и команда тестов (pytest-django).
<!-- @end -->

<!-- @fragment: PROCESS -->
# детерминированная проекция контрактов в план реализации Django
4A. Выпиши сущности контрактов → модели, поля и связи; зафиксируй инварианты в Meta/constraints.
4B. Каждой операции выдачи назначь queryset-метод: фильтр публикации, сортировка,
    предзагрузка связей (иначе N+1).
4C. Построй <read_model>: для каждой операции выдачи — ровно те поля, что нужны витрине;
    для каждого поля укажи источник. Ничего сверх — лишнее поле это утечка.
4D. Разверни <modules> и <tests> так, чтобы каждая ошибка каждого контракта была достижима тестом,
    и отдельным тестом проверялось, что draft не попадает в публичную выдачу.
<!-- @end -->

<!-- @fragment: SELF_CHECK_EXTRA -->
- Каждая операция контрактов имеет модуль и тест-требования.
- Каждое поле read_model выводится из поля модели или явного вычисления; висящих полей нет.
- Ни одно поле read_model не раскрывает черновики и служебные данные.
- В <technology> нет библиотек вне разрешённого списка.
<!-- @end -->

<!-- @fragment: TRACE_COLUMNS -->
FR-id → операция (OP-id) → модель/queryset → ключи read_model → тесты
<!-- @end -->
