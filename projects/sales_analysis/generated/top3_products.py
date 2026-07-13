import pandas as pd

def top3_products(cleaned_rows: pd.DataFrame) -> pd.DataFrame:
    """
    Возвращает до трёх продуктов с наибольшей суммарной выручкой (qty*price).
    При пустом входе или отсутствии обязательных колонок возвращает пустой DataFrame
    с колонками [product, revenue].
    """
    if not isinstance(cleaned_rows, pd.DataFrame):
        return pd.DataFrame(columns=["product", "revenue"])

    required = {"product", "qty", "price"}
    if not required.issubset(cleaned_rows.columns):
        return pd.DataFrame(columns=["product", "revenue"])

    if cleaned_rows.empty:
        return pd.DataFrame(columns=["product", "revenue"])

    df = cleaned_rows.copy()
    df["revenue"] = df["qty"] * df["price"]
    result = (
        df.groupby("product", as_index=False)
        .agg(revenue=("revenue", "sum"))
        .sort_values("revenue", ascending=False)
        .head(3)
    )
    return result[["product", "revenue"]]
