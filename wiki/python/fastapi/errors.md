# wiki: fastapi — обработка ошибок (v1)

Сценарий: централизованная обработка ошибок, кастомные исключения, формат ответа.

Когда использовать:
- нужно вернуть HTTP-ошибку с телом (detail) и заголовками;
- бизнес-логика выбрасывает собственные исключения — требуется единый формат ответа;
- требуется изменить поведение валидационных ошибок (например, статус 400 вместо 422, тело `{code, message}`).

Когда НЕ использовать:
- ошибка обрабатывается локально и не требует HTTP-ответа (просто залогировать);
- нужно вернуть не-HTTP ошибку (например, в фоновом воркере);
- кастомный обработчик не добавляет ценности поверх стандартного (не дублируй http_exception_handler без причины).

## Good

```python
from fastapi import HTTPException

@app.get("/items/{item_id}")
async def read_item(item_id: int):
    if item_id not in db:
        raise HTTPException(status_code=404, detail="Item not found")  # raise, не return
    return db[item_id]
```

```python
from fastapi import Request
from fastapi.responses import JSONResponse

class BusinessError(Exception):
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code

@app.exception_handler(BusinessError)
async def business_exception_handler(request: Request, exc: BusinessError):
    return JSONResponse(
        status_code=409,
        content={"code": exc.code, "message": exc.message},
    )
```

```python
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,                                          # меняем статус
        content={"code": "VALIDATION_ERROR", "message": exc.errors()},
    )
```

## Bad

```python
if item_id not in db:
    return HTTPException(status_code=404, detail="Not found")     # return вместо raise — не работает
```

```python
try:
    process(item)
except ValueError:
    raise HTTPException(status_code=500, detail="Internal error") # маскирует ошибку входа под 500
```

```python
@app.exception_handler(RequestValidationError)
async def handler(request, exc):
    return JSONResponse(status_code=422, content=exc.errors())    # сырой список ошибок Pydantic наружу
```

related: [fastapi](index.md), [модели запроса и ответа](validation.md)
