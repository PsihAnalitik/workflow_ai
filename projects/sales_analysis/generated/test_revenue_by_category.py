import pandas as pd
from revenue_by_category import revenue_by_category

def test_revenue_by_category_happy():
    df = pd.DataFrame({
        "date": ["2026-01-01"] * 4,
        "category": ["electronics", "electronics", "home", "home"],
        "product": ["phone_x1", "laptop_a3", "vacuum_v8", "mop"],
        "qty": [2, 1, 1, 5],
        "price": [100000, 92000, 18000, 2500],
        "region": ["msk", "spb", "ekb", "msk"]
    })
    result = revenue_by_category(df)
    assert not result.empty
    elec = result[result["category"] == "electronics"]
    home = result[result["category"] == "home"]
    assert elec["revenue"].iloc[0] == 2*100000 + 1*92000
    assert home["revenue"].iloc[0] == 1*18000 + 5*2500

def test_revenue_by_category_empty():
    df = pd.DataFrame(columns=["category", "qty", "price"])
    result = revenue_by_category(df)
    assert result.empty
    assert list(result.columns) == ["category", "revenue"]

def test_revenue_by_category_missing_cols():
    df = pd.DataFrame({"category": ["a"], "qty": [1]})
    result = revenue_by_category(df)
    assert result.empty
