# wiki: исходник — python/httpx/retries.md

> вербатим-приложение: полный входной текст изменения; материализовано wiki-apply из артефакта спеки (source_request), механические проверки wiki не применяются.

добавь страницу про повторные попытки (retries) в httpx — python/httpx/retries.md. Материал ниже — страница verified.

Материал:

httpx не повторяет запросы сам по себе. Встроенный механизм ограничен транспортом: httpx.HTTPTransport(retries=N) (и httpx.AsyncHTTPTransport) повторяет ТОЛЬКО установку соединения (httpx.ConnectError, httpx.ConnectTimeout). Пример:

transport = httpx.HTTPTransport(retries=3)
client = httpx.Client(transport=transport)

Что transport-retries НЕ делает: не повторяет запрос после получения ответа (5xx/429 не ретраятся), не повторяет при обрыве уже установленного соединения (httpx.ReadTimeout, httpx.ReadError), не делает экспоненциальную задержку между попытками.

Для повторов по статусу ответа или read-ошибкам нужен внешний цикл: библиотека tenacity (декоратор retry с retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout)) и wait_exponential) либо ручной цикл с httpx.Response.raise_for_status() и проверкой кода. Идемпотентность: повторять POST можно только если сервер поддерживает ключи идемпотентности или запрос безопасен по построению; GET/PUT/DELETE обычно безопасны.

Частая ошибка: оборачивать client.get() в try/except Exception и повторять всё подряд — повтор после httpx.HTTPStatusError 400 бессмыслен (запрос не станет валидным), а повтор записи после ReadTimeout может продублировать эффект на сервере.
