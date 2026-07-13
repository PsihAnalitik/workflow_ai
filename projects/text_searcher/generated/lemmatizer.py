"""
Лемматизация русских словоформ через pymorphy3.
"""
import pymorphy3

_morph = pymorphy3.MorphAnalyzer()


def normalize(wordform: str) -> str | None:
    """
    Привести слово к лемме.

    :param wordform: строка без пробелов и непустая.
    :return: лемма или None при неверном вводе.
    """
    if not wordform or " " in wordform:
        return None

    parsed = _morph.parse(wordform)
    if parsed:
        return parsed[0].normal_form
    # не-русское слово возвращаем как есть
    return wordform
