"""
Корневой поиск: композиция лемматизации и поиска по леммам в корпусе.
"""
from typing import List, Dict

import lemmatizer
import matching


def search(corpus: Dict[str, str], query: str) -> List[Dict] | None:
    """
    Выполнить корневой поиск.

    :param corpus: словарь document_id -> текст.
    :param query: непустой запрос, может содержать несколько слов.
    :return: список уникальных Match или None при пустом запросе.
    """
    if not query or not query.strip():
        return None

    words = query.split()
    all_matches: list[dict] = []
    seen = set()

    for word in words:
        lemma = lemmatizer.normalize(word)
        if lemma is None:
            # слово с пробелом? не должно случиться, но пропускаем
            continue
        res = matching.search(corpus, lemma, "EXACT")
        if res is not None:
            for m in res:
                key = (m["document_id"], m["position"], m["length"])
                if key not in seen:
                    seen.add(key)
                    all_matches.append(m)

    return all_matches
