"""
FastAPI-биндинг для сервиса текстового поиска.
"""
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

import matching
import lemmatizer
import root_search

app = FastAPI()

# Корпус документов устанавливается пользователем при старте; здесь заглушка
corpus: dict[str, str] = {}


@app.get("/search")
def endpoint_search(query: str = Query(...), strategy: str = Query(...)):
    result = matching.search(corpus, query, strategy)
    if result is None:
        return JSONResponse(
            status_code=400,
            content={"code": "EMPTY_QUERY", "message": "query пуст или состоит только из пробелов"},
        )
    return JSONResponse(status_code=200, content=result)


@app.get("/normalize")
def endpoint_normalize(wordform: str = Query(...)):
    lemma = lemmatizer.normalize(wordform)
    if lemma is None:
        return JSONResponse(
            status_code=400,
            content={"code": "EMPTY_WORDFORM", "message": "wordform пуст или содержит пробелы"},
        )
    return JSONResponse(status_code=200, content={"lemma": lemma})


@app.get("/root-search")
def endpoint_root_search(query: str = Query(...)):
    result = root_search.search(corpus, query)
    if result is None:
        return JSONResponse(
            status_code=400,
            content={"code": "EMPTY_QUERY", "message": "query пуст или состоит только из пробелов"},
        )
    return JSONResponse(status_code=200, content=result)
