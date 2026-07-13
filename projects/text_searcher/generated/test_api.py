from fastapi.testclient import TestClient

import matching
import api

client = TestClient(api.app)


def set_test_corpus():
    # Устанавливаем тестовый корпус, удовлетворяющий ожиданиям
    api.corpus = {"doc1": "кот на крыше", "doc2": "кот спит"}


def test_search_exact_ok():
    set_test_corpus()
    resp = client.get("/search", params={"query": "кот", "strategy": "EXACT"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any("doc1" in m["document_id"] for m in data)


def test_search_empty_query():
    set_test_corpus()
    resp = client.get("/search", params={"query": "", "strategy": "EXACT"})
    assert resp.status_code == 400
    assert resp.json()["code"] == "EMPTY_QUERY"


def test_normalize_ok():
    resp = client.get("/normalize", params={"wordform": "кошку"})
    assert resp.status_code == 200
    assert resp.json() == {"lemma": "кошка"}


def test_normalize_empty_wordform():
    resp = client.get("/normalize", params={"wordform": ""})
    assert resp.status_code == 400
    assert resp.json()["code"] == "EMPTY_WORDFORM"


def test_root_search_ok():
    set_test_corpus()
    resp = client.get("/root-search", params={"query": "кот"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # matches both docs


def test_root_search_empty_query():
    set_test_corpus()
    resp = client.get("/root-search", params={"query": ""})
    assert resp.status_code == 400
    assert resp.json()["code"] == "EMPTY_QUERY"
