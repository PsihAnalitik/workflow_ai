# wiki: pandas — временные ряды (v1)

## to_datetime — безопасный парсинг
- **GOOD:** `pd.to_datetime(s, format="%d-%m-%Y", errors="coerce")` — невалидные значения превратятся в NaT.
- **BAD:** полагаться на дефолтный `errors="raise"` без обработки неизвестных форматов.
- **Epoch-преобразование:** `pd.to_datetime(vals, unit="s")`.

## resample с новыми алиасами
- Панды 3.0 удалили старые алиасы (M, Q, Y). Используй:
  - `"ME"` — календарный месяц (month end)
  - `"QE"` — квартал
  - `"YE"` — год
- **GOOD:** `ts.resample("ME").sum()`, `ts.resample("5min").mean()`
- **BAD:** `ts.resample("M").sum()` → AttributeError.
- По умолчанию `label="left"`, но для ME/QE/YE — `"right"`.

## rolling с временным окном
- **GOOD:** `ts.rolling(window="5min", min_periods=1).mean()` — окно по времени, не по числу строк.
- `center=True` центрирует окно на точку; уместно при сглаживании.

## Таймзоны через zoneinfo
- **GOOD:**
  ```python
  dti = dti.tz_localize("Europe/Moscow")   # naive → aware
  dti.tz_convert("UTC")                    # aware → aware
  ```
  используется только stdlib zoneinfo; pytz больше не требуется.
- **BAD:** `dti.tz_localize(pytz.timezone("Europe/Moscow"))` — может работать, но избыточно и не рекомендовано.

## Опасное преобразование datetime → int
- Из-за микросекундного разрешения `datetime64[us]` в 3.0 прямой вызов `astype("int64")` даёт микросекундные unixtimestamp вместо наносекундных, как раньше.
- **GOOD:** `ser.dt.as_unit("ns").astype("int64")` — результат не зависит от разрешения.
- **BAD:** `ser.astype("int64")` без предварительного приведения к ns.

related: [карточка pandas](index.md)
