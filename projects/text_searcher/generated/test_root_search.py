import root_search


def corpus() -> dict:
    return {"doc1": "кошка", "doc2": "мышка"}


def test_root_search_multiword():
    res = root_search.search(corpus(), "кошку мышку")
    assert isinstance(res, list)
    doc_ids = {m["document_id"] for m in res}
    assert "doc1" in doc_ids
    assert "doc2" in doc_ids


def test_root_search_single_word():
    res = root_search.search(corpus(), "кошка")
    assert len(res) == 1
    assert res[0]["document_id"] == "doc1"


def test_root_search_empty_query():
    assert root_search.search(corpus(), "") is None
    assert root_search.search(corpus(), "   ") is None


def test_root_search_no_matches():
    res = root_search.search(corpus(), "слон")
    assert res == []
