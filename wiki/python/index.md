# wiki: каталог технологий Python (v2)

Реестр доступных цеху технологий экосистемы Python (FR-19). Стадия
`tech_selection` выбирает стек ОТСЮДА: ссылка технологии = значение
`<tech ref="...">` в `tech_stack.xml`; невыбранные технологии в контекст
исполнителя не попадают.

| Технология | ref | Класс задач | Статус |
|---|---|---|---|
| [pandas](pandas/index.md) | `python/pandas` | анализ табличных данных (CSV, агрегаты, временные ряды) | preferred |
| [fastapi](fastapi/index.md) | `python/fastapi` | HTTP-микросервисы (REST API + офлайн-тесты) | preferred |
| [duckdb](duckdb/index.md) | `python/duckdb` | встраиваемая аналитическая СУБД: SQL по CSV/Parquet, оконные функции, интеграция с pandas | allowed |
| [polars](polars/index.md) | `python/polars` | быстрые DataFrame на Rust (lazy evaluation, streaming, многопоточность) | allowed |
| [httpx](httpx/index.md) | `python/httpx` | современный HTTP-клиент (sync/async, HTTP/1.1, HTTP/2) | allowed |

Статусы: preferred — выбирается по умолчанию для своего класса задач;
allowed — допустима с WHY-обоснованием; deprecated — не выбирать для нового кода.

Правило пополнения: новая технология = поддиректория со страницами
(index.md: когда использовать / когда НЕ + шаблоны и good/bad примеры)
+ строка в этой таблице + запись в CHANGELOG цеха (FR-17).
**Стандарт документации библиотек:** фиксировать стабильную версию (проверка на PyPI, отозванные yanked-версии не брать); фактуру брать из официальной документации; страницы приземлять на пользовательские сценарии — шаблоны + good/bad (когда метод уместен, а когда избыточен или ошибочен).

related: [pandas](pandas/index.md), [fastapi](fastapi/index.md), [duckdb](duckdb/index.md), [методология цеха](../methodology/grace.md)
