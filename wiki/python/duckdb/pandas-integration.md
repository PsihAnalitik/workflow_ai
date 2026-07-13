# wiki: DuckDB — интеграция с pandas (v1)

Сценарий обмена данными между DuckDB и pandas через replacement scans
и встроенные методы конверсии. Заменяет ручной обход CSV-посредников.

## Replacement scan (DataFrame как таблица SQL)
```python
import pandas as pd, duckdb

df = pd.DataFrame({"region": ["EU","APAC"], "revenue": [150, 210]})
# имя переменной df используется прямо в FROM
top = duckdb.sql("""
    SELECT region, revenue
    FROM df
    WHERE revenue > 100
    ORDER BY revenue DESC
""").df()   # возврат обратно в DataFrame
```

## Другие конверсии результата
```python
res = duckdb.sql("SELECT * FROM 'sales.csv'")
# .fetchall() — list of tuples (Python-объекты)
res.fetchall()
# .pl() — Polars DataFrame
res.pl()
# .arrow() — PyArrow Table
res.arrow()
# .fetchnumpy() — словарь NumPy массивов
res.fetchnumpy()
```

## Шаринг соединений при многопоточности
```python
# Глобальный duckdb.sql() не защищён от гонок — в потоках создавайте свои соединения
def worker():
    with duckdb.connect() as conn:   # открывает изолированное in-memory
        return conn.sql("...").df()
```

## Good examples
- **Объединение DataFrame со справочником из CSV:**
  `duckdb.sql("SELECT * FROM df JOIN read_csv_auto('regions.csv') r ON df.region_id = r.id").df()`
  — Pandas-таблица и файл связаны внутри движка без конвертации.
- **Анализ памяти:** операция `df_A.merge(df_B).groupby(...).sum()` может
  переполнить память → `duckdb.sql("SELECT ... FROM df_A JOIN df_B ON ...
  GROUP BY ...").df()` исполнит запрос потоково и вернёт результат.
- **Быстрая передача NumPy:** `.fetchnumpy()` даёт доступ к колонкам как
  NumPy-массивам без копирования, удобно для ML-пайплайнов.

## Bad examples
- **Ручной круг через CSV:** `df.to_csv('temp.csv', index=False);
  duckdb.sql("SELECT ... FROM 'temp.csv'").df()` — replacement scan
  устраняет промежуточный файл и сериализацию.
- **Шаринг глобального `duckdb.sql` между потоками:**
  гонка за внутреннее состояние сессии → недетерминированные результаты
  или исключения; используйте `duckdb.connect()` на поток.
- **Изменение DataFrame после выполнения запроса:**
  replacement scan копирует данные на момент сканирования, изменения
  в исходном DataFrame после начала запроса не видны результату — не
  рассчитывайте на «живую» связь.

related: [index.md](index.md), [SQL по файлам](files-sql.md), [pandas](../pandas/index.md)
