"""
Модуль поиска по корпусу: точное (EXACT) или пословное (WORD) сопоставление.
Корпус — словарь {document_id: text}.
"""

from typing import List, Dict, Union


def search(
    corpus: Dict[str, str], query: str, strategy: str
) -> Union[List[Dict[str, Union[str, int]]], None]:
    """
    Поиск в корпусе.

    :param corpus: словарь document_id -> текст документа.
    :param query: строка запроса (непустая).
    :param strategy: 'EXACT' или 'WORD'.
    :return: список Match или None при пустом запросе.
    """
    if not query or not query.strip():
        return None

    matches: list[dict] = []

    for doc_id, text in corpus.items():
        if strategy == "EXACT":
            # Поиск всех позиций подстроки
            start = 0
            while True:
                idx = text.find(query, start)
                if idx == -1:
                    break
                matches.append(
                    {"document_id": doc_id, "position": idx, "length": len(query)}
                )
                start = idx + 1
        elif strategy == "WORD":
            # Разбиваем на слова по пробельным символам, игнорируем пунктуацию просто split
            words = text.split()
            pos = 0
            for w in words:
                if w == query:
                    matches.append(
                        {"document_id": doc_id, "position": pos, "length": len(w)}
                    )
                # продвигаем позицию: длина слова + 1 (пробел) – упрощённо
                pos += len(w) + 1
        else:
            return None  # неизвестная стратегия, можно трактовать как ошибку

    return matches
