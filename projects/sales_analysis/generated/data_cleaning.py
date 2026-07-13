import pandas as pd

def clean_data(raw_rows: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Фильтрует строки с отсутствующими значениями qty или price, подсчитывает количество отброшенных записей.

    Возвращает:
        cleaned_rows: DataFrame без строк, где qty или price отсутствуют.
        discarded_count: количество исключённых строк.
    Если вход не является DataFrame или отсутствуют ключевые колонки, все строки считаются
    с пропусками, и cleaned_rows будет пустым (с исходными колонками).
    """
    if not isinstance(raw_rows, pd.DataFrame):
        # Неверный тип входа — считаем, что данных нет
        return (pd.DataFrame(), 0)

    if "qty" not in raw_rows.columns or "price" not in raw_rows.columns:
        # Нет необходимых колонок — все строки рассматриваются как с пропусками
        cleaned = pd.DataFrame(columns=raw_rows.columns)
        return (cleaned, len(raw_rows))

    total = len(raw_rows)
    # Удаляем строки, где qty или price равны NaN
    cleaned = raw_rows.dropna(subset=["qty", "price"]).reset_index(drop=True)
    discarded = total - len(cleaned)
    return (cleaned, discarded)
