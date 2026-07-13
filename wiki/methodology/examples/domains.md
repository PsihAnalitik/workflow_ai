# wiki: примеры стадии domains (v1)

Учебный домен примеров — «сервис коротких ссылок» (не является текущей задачей;
показывает ФОРМУ и типичные дефекты).

Исходные требования примера:
FR-01 создать короткую ссылку из URL; FR-02 редирект по короткому коду;
FR-03 статистика переходов по коду.

## GOOD — эталонная форма

```xml
<domains project="url_shortener" version="1" derived_from="requirements.xml@1">
  <domain id="D-01" name="shortening">
    <responsibility>Создание коротких кодов и разрешение их в URL</responsibility>
    <covers>FR-01, FR-02</covers>
    <ubiquitous_language>
      <term name="код">короткий идентификатор ссылки</term>
    </ubiquitous_language>
    <owns>соответствие код → URL</owns>
    <emits>переход по коду</emits>   <!-- доменное событие, абстрактно -->
  </domain>
  <domain id="D-02" name="stats">
    <responsibility>Подсчёт переходов по кодам</responsibility>
    <covers>FR-03</covers>
    <ubiquitous_language>
      <term name="переход">факт разрешения кода в URL</term>
    </ubiquitous_language>
    <owns>счётчики переходов</owns>
    <emits/>
  </domain>
  <relationships>
    <!-- WHY: статистика не нужна редиректу для работы → async, не sync -->
    <edge from="D-02" to="D-01" kind="async" via="C-transitions" data="событие перехода"/>
  </relationships>
</domains>
```

Почему это хорошо: одна ответственность на домен; каждый FR закрыт ровно там,
где владение данными; `via="C-transitions"` резервирует id будущего контракта;
WHY стоит только у решения с альтернативой (sync vs async).

## BAD — типичные дефекты

```xml
<domains project="url_shortener" version="1">          <!-- нет derived_from -->
  <domain id="D-01" name="service">
    <responsibility>Ссылки, редиректы, статистика и админка</responsibility>
                                  <!-- «и» в ответственности = несколько ответственностей -->
    <owns>таблица links в PostgreSQL, кэш Redis</owns>  <!-- тех-специфика в STRICT -->
  </domain>                                             <!-- covers отсутствует:
                                                             FR не трассируются -->
  <relationships>
    <edge from="D-01" to="D-01" kind="sync"/>           <!-- ребро в себя, нет via -->
  </relationships>
</domains>
```

Дефекты: потеряна трассировка FR → домен; «швейцарский нож» вместо bounded context;
названы PostgreSQL/Redis (провал теста замены стека); ребро без `via` не резервирует контракт.
