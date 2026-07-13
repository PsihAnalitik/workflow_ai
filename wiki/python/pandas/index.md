# wiki: pandas (v2)

Стабильная версия: **3.0.3** (PyPI, 11.05.2026). Версия 3.0.4 отозвана (segfaults в datetime).
Документация: https://pandas.pydata.org/docs/
Требования: Python ≥3.11, numpy ≥1.26, pyarrow ≥13.

## Когда использовать
- анализ табличных данных, помещающихся в оперативную память одного узла
- очистка, фильтрация, агрегация CSV/Parquet/SQL-выгрузок в интерактивном режиме
- работа с временными рядами (resample, rolling) на датафреймах до ~2 млн строк
- подготовка данных для визуализации или передачи в микросервисную стадию цеха

## Когда НЕ использовать
- объём данных не влезает в память узла и нет возможности применить chunksize → используй DuckDB
- задача лучше выражается SQL (сложные JOIN, оконные агрегаты, подзапросы) → DuckDB
- требуется строгий контракт схемы (валидация при чтении) → pyarrow / polars
- потоковая/событийная обработка, требующая инкрементального обновления → не pandas
- вычисления на десятках ядер (pandas однопоточный для большинства операций) → polars / Dask

## Ключевые правила pandas 3.x
- **Copy-on-Write всегда активен.** Chained assignment вызывает ChainedAssignmentError;
  всегда используй .loc[]; забытые .copy() для защиты больше не нужны.
  inplace=True на извлечённой колонке не меняет DataFrame — переприсваивай явно.
- **Строковый dtype по умолчанию `str`** (не `object`); проверки `dtype == object` для текста сломаны.
- **to_datetime выдаёт `datetime64[us]`** (не [ns]); перед astype("int64") обязателен .dt.as_unit("ns").
- **Частотные алиасы:** M → ME, Q → QE, Y → YE (старые удалены); час – "h", мин – "min", сек – "s".
- **Параметр `copy=`** в astype/reindex/merge устарел и ничего не делает — убирай.
- **Таймзоны:** zoneinfo (stdlib), pytz больше не обязательная зависимость.

## Пропуски
- **GOOD:** `clean = df.dropna(subset=["qty", "price"]); dropped_rows = len(df) - len(clean)` — явная политика и подсчёт отброшенного.
- **BAD:** `df.fillna(0)` в количественных колонках без анализа — искажает суммы и статистики.

## Каталог сценарных страниц
| Страница | Сценарий |
|---|---|
| [io-csv.md](io-csv.md) | Чтение и запись CSV: управление типами, датами, пропусками, большие файлы |
| [aggregation.md](aggregation.md) | Группировки и агрегаты: именованные агрегаты, transform, filter; избегать apply с UDF |
| [timeseries.md](timeseries.md) | Временные ряды: to_datetime, resample, rolling, таймзоны |

## Тесты модулей
```python
# GOOD: фикстура строится в тесте, краевой случай — отдельным тестом
def test_revenue_by_category() -> None:
    df = pd.DataFrame({
        "category": ["a", "a", "b"],
        "qty": [1, 2, 3],
        "price": [10.0, 10.0, 5.0],
    })
    result = revenue_by_category(df)
    assert result.loc[result["category"] == "a", "revenue"].item() == 30.0

def test_revenue_empty_input() -> None:
    df = pd.DataFrame(columns=["category", "qty", "price"])
    assert revenue_by_category(df).empty

# BAD: тест читает CSV с диска — в песочнице файла нет, тест недетерминирован
```

related: [каталог технологий Python](../index.md), [io-csv](io-csv.md),
[aggregation](aggregation.md), [timeseries](timeseries.md)
