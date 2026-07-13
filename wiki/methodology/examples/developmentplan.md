# wiki: примеры стадии developmentplan / C4 (v1)

Учебный домен примеров — «сервис коротких ссылок». Стадия PROJECTION: здесь фиксируется
стек, файлы, алгоритмы и тест-требования — это прямой вход кодогенератора.

## GOOD — эталонная форма

```xml
<developmentplan project="url_shortener" version="1"
                 derived_from="contracts.xml@1, openapi.yaml@1">
  <technology>
    <language>Python 3.14</language>
    <allowed_libraries>stdlib, fastapi, httpx (только тесты)</allowed_libraries>
    <!-- WHY: in-memory dict вместо СУБД — персистентность не требуется (NFR), офлайн -->
    <storage>in-memory</storage>
  </technology>

  <modules>
    <module id="MOD-01" implements="OP-shorten" file="shortening.py">
      <responsibility>Создание кода и разрешение кода в URL</responsibility>
      <io>
        <inputs>url: str (непустой, абсолютный)</inputs>
        <outputs>code: str | None</outputs>
        <errors>None при INVALID_URL — вызывающий ветвится по None</errors>
      </io>
      <algorithm>
        1. валидация: пустой или не абсолютный url → None
        2. code = детерминированный хэш от url, усечённый до 8 символов
        3. registry[code] = url; вернуть code
      </algorithm>
      <tests>happy: валидный url → код разрешается обратно; edge: пустой url → None</tests>
    </module>
    <module id="MOD-02" implements="rest" file="api.py">
      <responsibility>FastAPI-биндинг по openapi.yaml</responsibility>
      <io><inputs>HTTP-запросы</inputs><outputs>JSON по схемам openapi</outputs>
          <errors>{code, message} со статусом 400 для ошибок входа</errors></io>
      <algorithm>по одному обработчику на operationId; ошибки ядра → JSONResponse 400</algorithm>
      <tests>TestClient (in-process, без сети): 200 happy; 400 с кодом из контракта</tests>
    </module>
  </modules>

  <rest_binding>
    <endpoint path="/links" method="post" operationId="OP-shorten" module="MOD-02 → MOD-01"/>
  </rest_binding>

  <run>
    <serve>uvicorn api:app</serve>
    <test>python -m pytest -q</test>
  </run>
</developmentplan>
```

Почему это хорошо: у каждого модуля файл, io из контракта, пошаговый алгоритм и
тест-требования — кодогенератору не нужно ничего додумывать; rest_binding сохраняет
шов operationId; WHY только у выбора с альтернативой.

## BAD — типичные дефекты

```xml
<developmentplan project="url_shortener" version="1">   <!-- нет derived_from -->
  <modules>
    <module id="MOD-01">
      <responsibility>Сделать сервис</responsibility>    <!-- не одна ответственность -->
      <algorithm>реализовать логику ссылок</algorithm>   <!-- не алгоритм, а пожелание -->
                                                         <!-- нет io, файла, тестов -->
    </module>
  </modules>
                                                         <!-- нет rest_binding:
                                                              шов с openapi потерян -->
</developmentplan>
```

Дефекты: кодогенератор вынужден проектировать сам (стадия для этого уже прошла);
нет трассировки OP → модуль → endpoint; тест-требования отсутствуют.
