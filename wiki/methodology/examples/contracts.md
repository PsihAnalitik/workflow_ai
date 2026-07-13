# wiki: примеры стадии contracts (v1)

Учебный домен примеров — «сервис коротких ссылок» (показывает ФОРМУ, не текущую задачу).

## GOOD — эталонная форма

```xml
<contract id="C-shortening" module="url_shortener" version="1" derived_from="domains.xml@1">
  <provides>
    <operation id="OP-shorten" kind="sync">
      <purpose>Создать короткий код для URL</purpose>
      <covers>FR-01</covers>
      <inputs>
        <field name="url" type="string" required="true" constraint="непустой, абсолютный URL"/>
      </inputs>
      <outputs>
        <field name="code" type="string" constraint="непустой"/>
      </outputs>
      <errors>
        <error code="INVALID_URL" when="url пуст или не абсолютный"/>
      </errors>
    </operation>
    <operation id="OP-resolve" kind="sync">
      <purpose>Разрешить код в URL</purpose>
      <covers>FR-02</covers>
      <inputs>
        <field name="code" type="string" required="true" constraint="непустой"/>
      </inputs>
      <outputs>
        <field name="url" type="string"/>
      </outputs>
      <errors>
        <error code="EMPTY_CODE"   when="code пустой"/>
        <error code="UNKNOWN_CODE" when="код не зарегистрирован"/>
      </errors>
    </operation>
  </provides>
  <types/>
  <consumes/>
</contract>
```

Почему это хорошо: id контракта совпадает с `via` из domains; каждая операция несёт
covers; каждая ошибка достижима конкретным входом (пустой url; незнакомый код);
типы из абстрактного словаря.

## BAD — типичные дефекты

```xml
<contract id="C-links">                       <!-- id не совпадает с via из domains -->
  <operation id="OP-shorten">
    <inputs>
      <field name="url" type="VARCHAR(255)"/> <!-- тип из СУБД: тех-специфика в STRICT -->
    </inputs>
    <outputs>
      <field name="code" type="string"/>
    </outputs>
    <errors>
      <error code="INTERNAL_ERROR" when="что-то пошло не так"/>
          <!-- недостижима конкретным входом → это не вариант контракта -->
      <error code="DB_TIMEOUT" when="база не ответила"/>
          <!-- инфраструктурный сбой, не ошибка входа; и снова тех-специфика -->
    </errors>
                                              <!-- covers отсутствует: FR потерян -->
  </operation>
</contract>
```

Дефекты: разорван шов via↔contract-id; недостижимые/инфраструктурные «ошибки»;
тип привязан к СУБД; потеряна трассировка на FR.
