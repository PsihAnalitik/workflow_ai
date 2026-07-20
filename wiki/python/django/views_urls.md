# wiki: Django Views и URL (v1)

> ⚠ unverified: написано из знаний модели без внешнего материала — проверь факты при приёмке.

## Когда использовать
- Обработка HTTP-запросов и рендеринг HTML-шаблонов.
- CRUD-операции над моделями с формами и редиректами.
- Пагинация, фильтрация и поиск через ORM.

## Когда НЕ использовать
- Асинхронная обработка без ASGI — Django async views требуют осторожности.
- Стриминг больших бинарных данных — лучше через nginx/X-Accel.
- Чистый API без шаблонов — предпочтительнее FastAPI.

## Маршрутизация
- `path('articles/<int:pk>/', views.detail, name='article_detail')` — именованный маршрут.
- `re_path(r'^archive/(?P<year>[0-9]{4})/$', views.archive)` — регулярное выражение.
- `include()` для подключения urls.py приложений.
- `reverse('article_detail', args=[pk])` — генерация URL в коде.

## Function-based views (FBV)
- Простая функция: `def my_view(request): return render(request, 'tmpl.html', ctx)`.
- Декораторы: `@login_required`, `@require_http_methods(["GET", "POST"])`.

## Class-based views (CBV)
- `ListView` — список объектов с пагинацией.
- `DetailView` — один объект по pk/slug.
- `CreateView`, `UpdateView`, `DeleteView` — формы с автоматической валидацией.
- Переопределение `get_context_data()` для дополнительного контекста.

## Контекст и безопасность
- `get_object_or_404(Model, pk=...)` — объект или 404.
- Передача контекста: словарь с данными для шаблона.

## Пагинация
- `Paginator(queryset, per_page)` + `page_obj = paginator.get_page(request.GET.get('page'))`.
- В шаблоне: `{% for item in page_obj %}`, `{% if page_obj.has_previous %}`.

## ORM без N+1
- `select_related('author')` — JOIN для ForeignKey/OneToOne.
- `prefetch_related('tags')` — отдельный запрос для ManyToMany/обратных связей.
- `annotate(Count('comments'))` — агрегация на уровне БД.
- Кастомный Manager: `class PublishedManager(models.Manager): def get_queryset(self): return super().get_queryset().filter(is_published=True)`.
- Кастомный QuerySet: цепочки фильтров, переиспользуемые методы.

## Примеры
**Good:**
```python
def article_list(request):
    articles = Article.objects.select_related('author').prefetch_related('tags').all()
    paginator = Paginator(articles, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'articles/list.html', {'page_obj': page_obj})
```

**Bad:**
```python
def bad_view(request):
    articles = Article.objects.all()
    return render(request, 'articles/list.html', {'articles': articles})
# В шаблоне: {% for a in articles %} [[ a.author.name ]] {% endfor %} — N+1 запросов.
```

related: [Django (обзор)](index.md), [Templates](templates.md)
