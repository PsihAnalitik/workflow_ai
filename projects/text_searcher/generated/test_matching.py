import matching


def sample_corpus() -> dict:
    return {"doc1": "кот бегемот", "doc2": "кот собака"}


def test_exact_search_found():
    res = matching.search(sample_corpus(), "кот", "EXACT")
    assert isinstance(res, list)
    assert len(res) >= 1
    assert any(
        m["document_id"] == "doc1" and m["length"] == 3 for m in res
    )


def test_exact_search_not_found():
    res = matching.search(sample_corpus(), "олень", "EXACT")
    assert res == []


def test_empty_query_returns_none():
    assert matching.search(sample_corpus(), "", "EXACT") is None
    assert matching.search(sample_corpus(), "   ", "WORD") is None


def test_word_search_found():
    res = matching.search(sample_corpus(), "кот", "WORD")
    assert len(res) == 2  # present as whole word in both docs
    docs = {m["document_id"] for m in res}
    assert docs == {"doc1", "doc2"}


def test_word_search_not_found():
    # "бегемот" не равен "кот"
    res = matching.search(sample_corpus(), "бегемот", "WORD")
    assert len(res) == 1
    assert res[0]["document_id"] == "doc1"
