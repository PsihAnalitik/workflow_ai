import lemmatizer


def test_normalize_hedgehog():
    assert lemmatizer.normalize("кошка") == "кошка"


def test_normalize_mouse_accusative():
    assert lemmatizer.normalize("мышку") == "мышка"


def test_normalize_non_russian():
    assert lemmatizer.normalize("hello") == "hello"


def test_empty_wordform():
    assert lemmatizer.normalize("") is None


def test_wordform_with_spaces():
    assert lemmatizer.normalize("кошка собака") is None
