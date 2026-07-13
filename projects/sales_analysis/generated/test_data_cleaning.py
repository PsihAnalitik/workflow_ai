import pandas as pd
from data_cleaning import clean_data

def test_clean_data_happy_path():
    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02"],
        "category": ["a", "b"],
        "product": ["x", "y"],
        "qty": [1, 2],
        "price": [10, 20],
        "region": ["msk", "spb"]
    })
    cleaned, discarded = clean_data(df)
    assert discarded == 0
    assert len(cleaned) == 2
    assert "qty" in cleaned.columns
    assert not cleaned["qty"].isna().any()

def test_clean_data_missing_values():
    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "category": ["a", "b", "c"],
        "product": ["x", "y", "z"],
        "qty": [1, None, 3],
        "price": [10, 20, None],
        "region": ["msk", "spb", "ekb"]
    })
    cleaned, discarded = clean_data(df)
    # Вторая строка: qty=None, третья: price=None → обе удалены
    assert discarded == 2
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["qty"] == 1
    assert cleaned.iloc[0]["price"] == 10

def test_clean_data_empty_input():
    df = pd.DataFrame(columns=["date", "category", "product", "qty", "price", "region"])
    cleaned, discarded = clean_data(df)
    assert cleaned.empty
    assert discarded == 0

def test_clean_data_all_missing():
    df = pd.DataFrame({
        "date": ["2026-01-01", "2026-01-02"],
        "category": ["a", "b"],
        "product": ["x", "y"],
        "qty": [None, None],
        "price": [None, None],
        "region": ["msk", "spb"]
    })
    cleaned, discarded = clean_data(df)
    assert cleaned.empty
    assert discarded == 2

def test_clean_data_missing_columns():
    # Нет колонок qty и price
    df = pd.DataFrame({"date": ["2026-01-01"], "category": ["a"], "product": ["x"], "region": ["msk"]})
    cleaned, discarded = clean_data(df)
    assert cleaned.empty
    assert discarded == 1
