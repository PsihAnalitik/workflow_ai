# wiki: примеры стадии openapi (v1)

Учебный домен примеров — «сервис коротких ссылок». Стадия openapi — PROJECTION:
тех-специфика разрешена, каждый выбор с альтернативой несёт WHY.

## GOOD — эталонная форма

```yaml
openapi: 3.1.0
info:
  title: url_shortener REST binding
  version: "1"
  # ПОЧЕМУ отдельный файл: протокол-проекция контракта; уйдём на gRPC —
  # заменится только этот файл, contract.xml не тронется.

paths:
  /links:
    post:
      # ПОЧЕМУ POST: создание ресурса с телом; идемпотентности нет по контракту
      operationId: OP-shorten          # шов с contract.xml: id операции = трассировка
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [url]
              properties:
                url: { type: string, minLength: 1 }   # проекция constraint "непустой"
      responses:
        '200':
          content:
            application/json:
              schema: { $ref: '#/components/schemas/ShortenResult' }
        '400':
          # ПОЧЕМУ 400: INVALID_URL — ошибка ВХОДА (вина клиента) → 4xx, не 5xx
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }

components:
  schemas:
    ShortenResult:
      type: object
      required: [code]
      properties:
        code: { type: string, minLength: 1 }
    Error:
      # ПОЧЕМУ {code, message}: code зеркалит <errors> контракта (машиночитаемо),
      # message — для человека; потребитель ветвится по code, не парсит текст
      type: object
      required: [code, message]
      properties:
        code:    { type: string, enum: [INVALID_URL] }   # только коды из контракта
        message: { type: string }
```

## BAD — типичные дефекты

```yaml
paths:
  /createLink:                      # глагол в пути вместо ресурса
    post:
      operationId: createLink       # шов с контрактом разорван: не OP-shorten
      responses:
        '500':                      # ошибка ВХОДА замаплена на серверный статус
          content:
            application/json:
              schema:
                type: object
                properties:
                  error: { type: string }   # произвольное тело: нет code из контракта,
                                            # потребитель вынужден парсить текст
```

Дефекты: потерян operationId=OP-id (трассировка слоёв рвётся); ошибка входа → 5xx;
тело ошибки не машиночитаемо; нет WHY у неочевидных выборов.
