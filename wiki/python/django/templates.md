# wiki: Django Templates (v1)

> ⚠ unverified: написано из знаний модели без внешнего материала — проверь факты при приёмке.

## Когда использовать
- Серверный рендеринг HTML с наследованием макетов (extends/block).
- HTMX-партиалы: отдача только фрагмента страницы на hx-get/hx-post.
- Локальное интерактивное состояние через Alpine.js (x-data, x-show).

## Когда НЕ использовать
- Генерация JSON/XML ответов API — используй JsonResponse или DRF.
- Сложная бизнес-логика в шаблоне — выноси в модель или view.
- Рендеринг на клиенте (React/Vue) — шаблоны Django избыточны.

## Наследование и партиалы
- `{% extends "base.html" %}` — наследование базового шаблона.
- `{% block content %}...{% endblock %}` — переопределяемые секции.
- `{% include "partials/_card.html" %}` — вставка переиспользуемого куска.
- Партиалы для HTMX: view возвращает только фрагмент без `<html>`/`<body>`.

## Контекст и вывод
- View передаёт словарь в `render(request, template, context)`.
- В шаблоне переменные доступны по имени: `[[ user.name ]]` (в реальном коде — двойные фигурные скобки; здесь заменены на `[[ ]]` из-за ограничений вики).
- Фильтры: `[[ value|default:"—" ]]`, `[[ date|date:"d.m.Y" ]]`.

## Встроенные теги и фильтры
- `{% for item in list %}...{% endfor %}`, `{% if condition %}...{% endif %}`.
- `{% url 'name' arg %}` — генерация URL по имени маршрута.
- `{% static "css/style.css" %}` — ссылка на статический файл.
- Фильтры: `length`, `truncatechars`, `pluralize`, `safe` (осторожно с XSS).

## Static и media
- Статика: `[[ static('css/style.css') ]]` → `/static/css/style.css`.
- Media (загруженные файлы): `[[ obj.file.url ]]` — только URL, не путь ФС.
- Атрибут `srcset` для адаптивных изображений: `[[ obj.image.url ]]` с разными разрешениями.

## Кастомные template tags и filters
- `simple_tag` — функция, возвращающая строку.
- `inclusion_tag` — рендерит подшаблон с переданным контекстом.
- Регистрируются в `templatetags/` модуле приложения.

## HTMX + Alpine.js поверх шаблонов
- `hx-get="{% url 'partial' %}" hx-target="#result" hx-swap="innerHTML"` — загрузка партиала.
- `hx-post` с CSRF-токеном: `hx-headers='{"X-CSRFToken": "[[ csrf_token ]]"}'.`
- Прогрессивное улучшение: при выключенном JS форма отправляется обычным POST.
- Alpine.js для локального состояния: `x-data="{ open: false }"`, `x-show="open"`, `@click="open = !open"`.

## Примеры
**Good:**
```django
{% extends "base.html" %}
{% block content %}
  <h1>[[ page.title ]]</h1>
  {% include "partials/_gallery.html" %}
  <div hx-get="{% url 'more' %}" hx-trigger="revealed"></div>
{% endblock %}
```

**Bad:**
```django
<!-- логика в шаблоне: подсчёты и запросы -->
{% for order in user.orders.all %}
  [[ order.total ]] ([[ order.items.count ]] позиций)
{% endfor %}
<!-- N+1 запросов, нет select_related в view -->
```

related: [Django (обзор)](index.md), [Views и URL](views_urls.md)
