import pandas as pd
from avg_receipt_by_region import avg_receipt_by_region

def test_avg_receipt_by_region_happy():
    df = pd.DataFrame({
        "region": ["msk", "msk", "spb", "spb"],
        "qty": [2, 1, 1, 3],
        "price": [100, 200, 300, 50],
    })
    result = avg_receipt_by_region(df)
    assert len(result) == 2
    msk_row = result[result["region"] == "msk"]
    spb_row = result[result["region"] == "spb"]
    # msk: total = 2*100 + 1*200 = 400, transactions = 2, avg = 200.0
    assert msk_row["avg_receipt"].iloc[0] == 200.0
    # spb: total = 1*300 + 3*50 = 450, transactions = 2, avg = 225.0
    assert spb_row["avg_receipt"].iloc[0] == 225.0

def test_avg_receipt_by_region_single_transaction():
    df = pd.DataFrame({
        "region": ["ekb"],
        "qty": [5],
        "price": [10],
    })
    result = avg_receipt_by_region(df)
    assert len(result) == 1
    assert result.iloc[0]["avg_receipt"] == 50.0

def test_avg_receipt_by_region_empty():
    df = pd.DataFrame(columns=["region", "qty", "price"])
    result = avg_receipt_by_region(df)
    assert result.empty
    assert list(result.columns) == ["region", "avg_receipt"]

def test_avg_receipt_by_region_missing_columns():
    df = pd.DataFrame({"region": ["a"], "qty": [1]})  # нет price
    result = avg_receipt_by_region(df)
    assert result.empty
