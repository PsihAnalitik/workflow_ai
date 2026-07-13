import pandas as pd
from top3_products import top3_products

def test_top3_products_happy():
    df = pd.DataFrame({
        "product": ["phone_x1", "laptop_a3", "vacuum_v8", "mop"],
        "qty": [2, 1, 1, 5],
        "price": [100000, 92000, 18000, 2500],
    })
    result = top3_products(df)
    assert len(result) == 3
    # top1: phone_x1 (200000), top2: laptop_a3 (92000), top3: vacuum_v8 (18000)
    assert result.iloc[0]["product"] == "phone_x1"
    assert result.iloc[0]["revenue"] == 200000
    assert result.iloc[1]["product"] == "laptop_a3"
    assert result.iloc[1]["revenue"] == 92000
    assert result.iloc[2]["product"] == "vacuum_v8"
    assert result.iloc[2]["revenue"] == 18000

def test_top3_products_fewer_than_3():
    df = pd.DataFrame({
        "product": ["a", "b"],
        "qty": [1, 2],
        "price": [10, 5],
    })
    result = top3_products(df)
    assert len(result) == 2
    assert result.iloc[0]["product"] == "a"
    assert result.iloc[0]["revenue"] == 10
    assert result.iloc[1]["product"] == "b"
    assert result.iloc[1]["revenue"] == 10

def test_top3_products_empty():
    df = pd.DataFrame(columns=["product", "qty", "price"])
    result = top3_products(df)
    assert result.empty
    assert list(result.columns) == ["product", "revenue"]

def test_top3_products_missing_columns():
    df = pd.DataFrame({"product": ["a"], "qty": [1]})  # нет price
    result = top3_products(df)
    assert result.empty
