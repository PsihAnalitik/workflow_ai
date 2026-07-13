# wiki: DuckDB — SQL по CSV/Parquet-файлам (v1)

Сценарий прямых запросов к файлам без промежуточной загрузки в БД. Применяется
для разовых аналитических запросов по логам, дампам, обменным форматам.

## Автодетект (для разведочных запросов)
```python
import duckdb
# csv-сниффер определяет разделитель, заголовок и типы
duckdb.sql("SELECT * FROM 'flights.csv' LIMIT 5").show()
```

## Явные параметры (для стабильных пайплайнов)
```python
duckdb.read_csv(
    "sales.csv",
    delim="|",
    header=True,
    columns={"dt": "DATE", "amount": "DECIMAL(10,2)"}
).show()
```

## Глоббинг нескольких файлов
```python
# все csv в директории data/
duckdb.read_csv("data/*.csv").show()
# несколько Parquet-файлов
duckdb.sql("SELECT count(*) FROM read_parquet('logs/2026-06-*.parquet')").show()
```

## Обработка ошибок
```python
# пропускать битые строки (с логом отказа при store_rejects=True)
duckdb.read_csv(
    "messy.csv",
    ignore_errors=True,
    store_rejects=True,
    rejects_limit=100
).show()
```

## Запись результатов
```python
# копирование таблицы в csv
duckdb.sql("COPY (SELECT * FROM 'source.csv') TO 'output.csv'")
# или через write-методы Relation
duckdb.read_csv("source.csv").write_parquet("result.parquet")
```

## Good examples
- **Разведка неизвестного CSV:** `SELECT * FROM 'dump.csv' LIMIT 5` — автодетект
  даёт мгновенный ответ без ручного указания схемы.
- **Ежедневный отчёт по нескольким Parquet-файлам:** `read_parquet('metrics/*.parquet')`
  с оконной функцией напрямую по файлам, без промежуточной таблицы.
- **Очистка грязного лога:** `read_csv('raw.log', delim='\t', ignore_errors=True,
  store_rejects=True)` с последующим ручным просмотром таблицы rejects.

## Bad examples
- **Использовать автодетект в production-пайплайне без проверки схемы:**
  изменение порядка столбцов или разделителя в источнике вызовет неверную
  интерпретацию типов без ошибки → всегда задавайте `columns` в пайплайнах.
- **Загружать файл в pandas, а потом в DuckDB:** `df = pd.read_csv('data.csv');
  duckdb.sql("SELECT * FROM df")` — лишняя прокладка, DuckDB может читать файл
  напрямую (быстрее и без расхода памяти на pandas).
- **Читать потоковый источник через read_csv('pipe')** — DuckDB ожидает
  файловый дескриптор, а не бесконечный поток; для реального времени
  используйте другой инструмент.

related: [index.md](index.md), [Pandas integration](pandas-integration.md)
