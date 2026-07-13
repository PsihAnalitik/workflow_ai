import pandas as pd

def avg_receipt_by_region(cleaned_rows: pd.DataFrame) -> pd.DataFrame:
    """
    Рассчитывает средний чек по регионам: общая выручка / количество транзакций в регионе.
    При пустом входе или отсутствии обязательных колонок возвращает пустой DataFrame
    с колонками [region, avg_receipt].
    """
    if not isinstance(cleaned_rows, pd.DataFrame):
        return pd.DataFrame(columns=["region", "avg_receipt"])

    required = {"region", "qty", "price"}
    if not required.issubset(cleaned_rows.columns):
        return pd.DataFrame(columns=["region", "avg_receipt"])

    if cleaned_rows.empty:
        return pd.DataFrame(columns=["region", "avg_receipt"])

    df = cleaned_rows.copy()
    df["revenue"] = df["qty"] * df["price"]
    agg = (
        df.groupby("region")
        .agg(
            total_revenue=("revenue", "sum"),
            transaction_count=("region", "count")
        )
        .reset_index()
    )
    agg["avg_receipt"] = agg["total_revenue"] / agg["transaction_count"]
    return agg[["region", "avg_receipt"]]
