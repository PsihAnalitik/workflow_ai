import pandas as pd

def revenue_by_month(cleaned_rows: pd.DataFrame) -> pd.DataFrame:
    """
    Извлекает месяц из date ('YYYY-MM') и группирует по месяцу, вычисляя суммарную выручку.

    Требуются колонки: date, qty, price.
    При пустом входе или отсутствии колонок возвращает пустой DataFrame с [month, revenue].
    """
    if not isinstance(cleaned_rows, pd.DataFrame):
        return pd.DataFrame(columns=["month", "revenue"])

    required = {"date", "qty", "price"}
    if not required.issubset(cleaned_rows.columns):
        return pd.DataFrame(columns=["month", "revenue"])

    if cleaned_rows.empty:
        return pd.DataFrame(columns=["month", "revenue"])

    df = cleaned_rows.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.strftime("%Y-%m")
    df["revenue"] = df["qty"] * df["price"]
    result = df.groupby("month", as_index=False).agg(revenue=("revenue", "sum"))
    return result[["month", "revenue"]]
