import sys
import pandas as pd
from data_cleaning import clean_data
from revenue_by_category import revenue_by_category
from revenue_by_month import revenue_by_month
from top3_products import top3_products
from avg_receipt_by_region import avg_receipt_by_region

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <path_to_csv>")
        sys.exit(1)

    path = sys.argv[1]
    try:
        raw = pd.read_csv(path, parse_dates=["date"], dtype={"qty": "Int64", "price": "Int64"})
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        sys.exit(1)

    cleaned, discarded = clean_data(raw)
    print(f"Количество исключённых записей (пропуски в qty/price): {discarded}")
    print()

    print("=== Выручка по категориям ===")
    cat_rev = revenue_by_category(cleaned)
    if cat_rev.empty:
        print("Нет данных для расчёта.")
    else:
        print(cat_rev.to_string(index=False))
    print()

    print("=== Выручка по месяцам ===")
    month_rev = revenue_by_month(cleaned)
    if month_rev.empty:
        print("Нет данных для расчёта.")
    else:
        print(month_rev.to_string(index=False))
    print()

    print("=== Топ-3 продукта по выручке ===")
    top3 = top3_products(cleaned)
    if top3.empty:
        print("Нет данных для расчёта.")
    else:
        print(top3.to_string(index=False))
    print()

    print("=== Средний чек по регионам ===")
    region_receipt = avg_receipt_by_region(cleaned)
    if region_receipt.empty:
        print("Нет данных для расчёта.")
    else:
        print(region_receipt.to_string(index=False))

if __name__ == "__main__":
    main()
