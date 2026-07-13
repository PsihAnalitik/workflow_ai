import pandas as pd

def revenue_by_category(cleaned_rows: pd.DataFrame) -> pd.DataFrame:
    """
    Группирует по category и возвращает суммарную выручку (qty*price).

    Ожидаются колонки: category, qty, price.
    Если вход пустой или отсутствуют обязательные колонки, возвращает пустой DataFrame
    с колонками [category, revenue].
    """
    if not isinstance(cleaned_rows, pd.DataFrame):
        return pd.DataFrame(columns=["category", "revenue"])

    required = {"category", "qty", "price"}
    if not required.issubset(cleaned_rows.columns):
        return pd.DataFrame(columns=["category", "revenue"])

    if cleaned_rows.empty:
        return pd.DataFrame(columns=["category", "revenue"])

    df = cleaned_rows.copy()
    df["revenue"] = df["qty"] * df["price"]
    result = df.groupby("category", as_index=False).agg(revenue=("revenue", "sum"))
    return result[["category", "revenue"]]
