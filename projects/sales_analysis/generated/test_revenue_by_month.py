import pandas as pd
from revenue_by_month import revenue_by_month

def test_revenue_by_month_happy():
    df = pd.DataFrame({
        "date": ["2026-01-15", "2026-02-10", "2026-01-20"],
        "qty": [2, 1, 5],
        "price": [100, 200, 50]
    })
    result = revenue_by_month(df)
    assert len(result) == 2
    jan = result[result["month"] == "2026-01"]
    feb = result[result["month"] == "2026-02"]
    assert jan["revenue"].iloc[0] == 2*100 + 5*50
    assert feb["revenue"].iloc[0] == 1*200

def test_revenue_by_month_empty():
    df = pd.DataFrame(columns=["date", "qty", "price"])
    result = revenue_by_month(df)
    assert result.empty

def test_revenue_by_month_missing_date():
    df = pd.DataFrame({"qty": [1], "price": [10]})
    result = revenue_by_month(df)
    assert result.empty
