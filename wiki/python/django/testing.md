# wiki: Django Testing (v1)

> ⚠ unverified: написано из знаний модели без внешнего материала — проверь факты при приёмке.

## Когда использовать
- Тестирование views: коды ответа, контекст, использованные шаблоны.
- Проверка ORM-запросов на отсутствие N+1 (assertNumQueries).
- Быстрые юнит-тесты с sqlite in-memory.

## Когда НЕ использовать
- E2E-тесты с браузером — используй Playwright/Selenium.
- Тестирование внешних API — мокай HTTP-клиент (responses, httpx-mock).
- Нагрузочное тестирование — отдельный инструмент (Locust).

## Инструменты и фикстуры
- `pytest-django`: фикстуры `client` (анонимный), `admin_client`, `db` (доступ к БД).
- `django.test.Client`: `response = client.get('/url/')`, `client.post('/url/', data)`.
- `assert response.status_code == 200`.
- `assertTemplateUsed(response, 'articles/list.html')`.
- `assertContains(response, 'ожидаемый текст')`.

## Фикстуры данных
- `model_bakery` (бывшая model_mommy): `baker.make(Article, title='Test')`.
- Встроенные фикстуры pytest: `@pytest.fixture` для создания объектов.
- Транзакционная очистка: каждый тест в транзакции, откат после.

## Настройки для тестов
- `DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}`.
- `CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}`.
- `STORAGES = {'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}` (dummy storage для media).

## Проверка запросов (N+1)
- `with assertNumQueries(2): response = client.get('/articles/')` — ожидаемое число запросов.
- Тест ловит лишние запросы из-за отсутствия select_related/prefetch_related.

## Примеры
**Good:**
```python
@pytest.mark.django_db
def test_article_list_performance(client):
    baker.make('app.Article', _quantity=5)
    with assertNumQueries(2):  # 1 на статьи + 1 на авторов (select_related)
        response = client.get('/articles/')
    assert response.status_code == 200
    assertTemplateUsed(response, 'articles/list.html')
```

**Bad:**
```python
def test_article_list(client):
    response = client.get('/articles/')
    assert response.status_code == 200
    # Нет проверки шаблона и количества запросов — N+1 останется незамеченным.
```

related: [Django (обзор)](index.md), [Views и URL](views_urls.md), [FastAPI Testing](../fastapi/testing.md)
