# wiki: fastapi — модели запроса и ответа (v1)

Сценарий: определение и валидация данных запроса/ответа через Pydantic-модели.

Когда использовать:
- тело запроса — Pydantic-модель (не dict/список примитивов);
- нужно автоматически получить 422 с детализацией по полям при невалидном входе;
- ответ должен фильтровать поля (например, скрыть password) или валидироваться;
- частичное обновление (PATCH) — только переданные поля.

Когда НЕ использовать:
- тело запроса — простой тип (int, str) без вложенной структуры (используй query/body с явным `Body()`);
- ответ не требует фильтрации и схема OpenAPI не важна — можно вернуть dict;
- потоковые ответы или бинарные данные (FileResponse, StreamingResponse).

## Good

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float

@app.post("/items/")
async def create_item(item: Item) -> Item:          # аннотация возврата = валидация + схема
    return item                                      # автоматический 422 при невалидном входе
```

```python
class UserIn(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    username: str

@app.post("/users/", response_model=UserOut)         # response_model фильтрует password
async def create_user(user: UserIn):
    return user                                      # UserOut отбросит password
```

```python
@app.patch("/items/{item_id}", response_model_exclude_unset=True)
async def update_item(item_id: int, item: Item):
    stored = db.get(item_id)
    updated = stored.copy(update=item.model_dump(exclude_unset=True))
    return updated                                  # в ответе только изменённые поля
```

## Bad

```python
@app.post("/items/")
async def create_item(item: dict):                  # нет валидации, ручной разбор
    name = item.get("name")
    ...
```

```python
@app.post("/users/")
async def create_user(user: UserIn) -> dict:        # возврат dict без response_model
    return user.model_dump()                        # password утекает в ответ
```

```python
item.dict()                                         # Pydantic 2: устарело, используй model_dump()
```

related: [fastapi](index.md), [обработка ошибок](errors.md)
