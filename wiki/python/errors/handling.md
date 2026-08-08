# wiki: формирование обработки исключений (v2)

Методология для агента, добавляющего обработку исключений в Python-код.
Принцип: обработка исключений — часть контракта функции, а не украшение;
каждая точка перехвата обязана либо ОБРАБОТАТЬ (восстановиться осмысленно),
либо ПЕРЕБРОСИТЬ с контекстом. Всё остальное — проглатывание
(см. [swallowing.md](swallowing.md)).

## Т1 — context manager для ресурсов

Ресурс (файл, соединение, лок) захватывается только через `with` /
собственный context manager. `__exit__` освобождает ресурс и возвращает
`False` — исключения НЕ подавляются молча.

```python
class DatabaseConnection:
    def __enter__(self):
        self.conn = connect(self.connection_string)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
        return False  # не глушить исключения
```

`return True` из `__exit__` легален только для ЯВНО задуманного подавления
узкого класса ошибок — с комментарием намерения (иначе находка S6).

## Т2 — иерархия доменных исключений

Свои исключения — наследованием от доменного базового класса, не от голого
`Exception` россыпью. Вызывающий ловит базовый класс домена, а не `Exception`.
Полезный контекст (id транзакции, имя файла) — атрибутами исключения.

```python
class OrderError(Exception): ...
class PaymentError(OrderError):
    def __init__(self, message, transaction_id=None):
        super().__init__(message)
        self.transaction_id = transaction_id
```

## Т3 — chaining: `raise ... from e`

При преобразовании низкоуровневого исключения в доменное исходная причина
сохраняется через `from e` (доступна как `e.__cause__`). Потеря причины —
находка S4.

```python
except FileNotFoundError as e:
    raise ConfigError("Database configuration file not found") from e
except yaml.YAMLError as e:
    raise ConfigError("Invalid database configuration format") from e
```

## Т4 — декоратор централизованной обработки

Повторяющаяся политика (retry, fallback, логирование) выносится в декоратор,
а не копипастится по функциям. Правила: ловить ТОЛЬКО ожидаемые типы
(`ConnectionError`, `TimeoutError`); неожиданные — логировать и пробрасывать;
fallback возвращать только на последней попытке и только если он объявлен.

```python
def handle_api_errors(retries=3, fallback_value=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError):
                    if attempt == retries - 1:
                        if fallback_value is not None:
                            return fallback_value
                        raise
        return wrapper
    return decorator
```

## Т5 — try-finally для очистки

Очистка временного состояния (temp-файлы, откат частичных изменений) — в
`finally`, когда context manager неприменим. `finally` не должен поднимать
собственное исключение, глушащее исходное (находка S7).

```python
try:
    processed = self.apply_filters(raw_data)
finally:
    for temp_file in self.temp_files:
        os.remove(temp_file)
```

## Порядок работы агента

1. Карта точек риска файла: I/O, сеть, парсинг, преобразования типов,
   работа с ресурсами, внешние вызовы.
2. Для каждой точки выбрать технику Т1–Т5 (или осознанно оставить
   исключение пробрасываться — это тоже решение, зафиксировать).
3. Не менять бизнес-логику и сигнатуры без необходимости; новые исключения —
   в доменную иерархию файла/модуля.
4. Самопроверка по каталогу [swallowing.md](swallowing.md): ни одна правка
   не должна вводить S1–S8.
5. Сверка контрактов возврата: правки обработки ошибок часто добавляют новые
   точки возврата. ЕСЛИ у правленой функции фактический тип возврата разошёлся
   с декларированной аннотацией по любому из путей (включая неявный `None`
   в конце тела и возвраты из `except`/`finally`) → поправь аннотацию
   (пример: явный `return False` в `__exit__` требует `-> bool`, не `-> None`).
   ЕСЛИ у функции аннотации нет → не добавляй её ради сверки (вне скоупа).
   Явный возврат ставь одной точкой после `try/except`, покрывающей и
   успешный путь, и путь с ошибкой, а не только внутри `except`.

related: [каталог области](index.md), [каталог проглатывания](swallowing.md)
